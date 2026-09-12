# src/engine/run.py
"""The one orchestrator (design.md §7.3, §9.1). Steps are isolated; the verdict is honest."""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from src.common.paths import SILVER_POS_ROOT
from src.engine.inputs import load_inputs
from src.engine.model import CapabilityOutput
from src.engine.policy import load_policy
from src.engine.publish import ARTEFACT_PATH, PublishRefused, build_artefact, validate_artefact, write_atomic
from src.engine.registry import CAPABILITIES
from src.owner_state.model import OwnerState
from src.owner_state.pull import MIRROR_PATH, pull, read_mirror, write_mirror

SILVER_DIR = SILVER_POS_ROOT
SALES_DIR = Path(__file__).resolve().parents[2] / "data" / "internal" / "raw_pos" / "yomyom" / "sales"

# Filled by Phase 1: capability id -> callable(inputs) -> CapabilityOutput
DEFAULT_RUNNERS: dict[str, Callable] = {}


def _pull_owner_state() -> OwnerState:
    project = os.environ.get("FIREBASE_PROJECT_ID") or os.environ.get("VITE_FIREBASE_PROJECT_ID") or ""
    store = os.environ.get("VITE_STORE_ID", "yomyom-kafr-qasim")
    cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or None
    cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH") or None
    if not (cred_json or cred_path):
        state = read_mirror(MIRROR_PATH)          # reproduction on a laptop: the committed replica, flagged
        state.reason = state.reason or "no_credentials"
        return state
    state = pull(project_id=project, store_id=store, credentials_json=cred_json, credentials_path=cred_path)
    if state.status == "available":
        write_mirror(state, MIRROR_PATH)
    return state


def _sales_import(sales_dir: Optional[Path] = None, silver_dir: Optional[Path] = None) -> dict:
    sales_dir = sales_dir or SALES_DIR
    silver_dir = silver_dir or SILVER_DIR
    from datetime import date
    from src.internal_pos.pos_importer import read_pos_vintage
    from src.internal_pos.sales_importer import import_sales
    vintage = read_pos_vintage(silver_dir)
    as_of = date.fromisoformat(vintage["as_of"][:10]) if vintage and vintage.get("as_of") else None
    return import_sales(sales_dir, inventory_as_of=as_of, silver_dir=silver_dir)


def _market_chain(skip: bool) -> list:
    steps = []
    from src.context.build import write_market_context
    steps.append(("market_context", write_market_context))
    if not skip:
        from scripts.rehydrate_silver import rehydrate
        from src.signals.competitor_product_signals import build_competitor_product_signals
        from src.matching.product_matching import run_product_matching
        steps += [("rehydrate_silver", rehydrate), ("competitor_signals", build_competitor_product_signals),
                  ("product_matching", run_product_matching)]
    return steps


def _step(steps: list, name: str, fn: Callable):
    t0 = time.monotonic()
    try:
        result = fn()
        steps.append({"step": name, "status": "ok", "ms": int((time.monotonic() - t0) * 1000), "error": None})
        return result
    except Exception as exc:  # noqa: BLE001 — isolate, record, continue
        steps.append({"step": name, "status": "error", "ms": int((time.monotonic() - t0) * 1000),
                      "error": f"{type(exc).__name__}: {exc}"})
        return None


def run_engine(*, mode: str = "publish", input_csv: Optional[Path] = None, skip_market: bool = False,
               artefact_path: Path = ARTEFACT_PATH, capability_runners: Optional[dict] = None,
               now: Optional[datetime] = None, silver_dir: Optional[Path] = None,
               sales_dir: Optional[Path] = None) -> dict:
    silver_dir = silver_dir or SILVER_DIR
    sales_dir = sales_dir or SALES_DIR
    now = now or datetime.now(timezone.utc)
    runners = DEFAULT_RUNNERS if capability_runners is None else capability_runners
    steps: list = []
    policy = load_policy()

    owner = _step(steps, "owner_state_pull", _pull_owner_state) or OwnerState.unavailable("pull_step_failed")
    if input_csv:
        from src.internal_pos.pos_importer import import_pos_file
        _step(steps, "pos_import", lambda: import_pos_file(Path(input_csv)))
    _step(steps, "sales_import", lambda: _sales_import(sales_dir, silver_dir))
    for name, fn in _market_chain(skip_market):
        _step(steps, name, fn)

    inputs = _step(steps, "load_inputs", lambda: load_inputs(policy=policy, owner=owner, run_at=now, silver_dir=silver_dir))
    outputs: list[CapabilityOutput] = []
    if inputs is not None:
        # catalogue_lifecycle runs first so its withdrawn set reaches the others (FR-074).
        order = ["catalogue_lifecycle"] + [c for c in runners if c != "catalogue_lifecycle"]
        for cap_id in order:
            if cap_id not in runners:
                continue
            spec = CAPABILITIES[cap_id].spec
            out = _step(steps, f"capability:{cap_id}", lambda cap_id=cap_id: runners[cap_id](inputs))
            if out is None:
                out = CapabilityOutput.unavailable(cap_id, spec, "capability_error")
            outputs.append(out)
            if cap_id == "catalogue_lifecycle" and out.status == "available":
                inputs.withdrawn = set(out.counts.get("_withdrawn_barcodes", []) or [])

    status = "ok"
    if any(s["status"] == "error" for s in steps):
        status = "partial"
    elif owner.status != "available" or any(o.unavailable_reason == "capability_error" for o in outputs):
        status = "degraded"

    artefact = build_artefact(outputs, vintages=inputs.vintages if inputs else _no_inputs_vintages(owner),
                              thresholds=policy.as_dict(), run={"status": status, "steps": steps},
                              generated_at=now.isoformat(), run_id=uuid.uuid4().hex[:12])
    # Completeness is asserted for a real run only: a test that injects two capabilities is
    # not a broken artefact, but a production run missing one is. Turns itself on in Phase 1.8
    # when DEFAULT_RUNNERS stops being empty — nobody has to remember to flip it.
    complete = capability_runners is None and bool(runners)
    published = False
    if mode == "publish":
        try:
            if outputs and all(o.status == "unavailable" for o in outputs):
                raise PublishRefused("every capability is unavailable — refusing to overwrite the last good artefact")
            write_atomic(artefact_path, artefact, require_complete_registry=complete)
            published = True
        except PublishRefused as exc:
            steps.append({"step": "publish", "status": "error", "ms": 0, "error": str(exc)})
            status = "partial"
    else:
        validate_artefact(artefact, require_complete_registry=complete)
    artefact["run"]["status"] = status
    return {"status": status, "steps": steps, "artefact": artefact, "published": published}


def _no_inputs_vintages(owner: OwnerState) -> dict:
    return {"pos": {"file": None, "as_of": None},
            "sales": {"months": [], "first": None, "last": None, "full_annual_cycle": False},
            "competitor": {"snapshot_date": None, "sources": []},
            "owner_state": {"pulled_at": owner.pulled_at, "status": owner.status}}
