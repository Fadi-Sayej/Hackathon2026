# src/engine/run.py
"""The one orchestrator (design.md §7.3, §9.1). Steps are isolated; the verdict is honest."""
from __future__ import annotations

import os
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from src.common.paths import SILVER_POS_ROOT
from src.engine.inputs import load_inputs
from src.engine.model import CapabilityOutput
from src.engine.policy import load_policy
from src.engine.catalogue import build_catalogue, write_catalogue
from src.engine.publish import ARTEFACT_PATH, PublishRefused, build_artefact, validate_artefact, write_atomic
from src.engine.registry import CAPABILITIES
from src.owner_state.model import OwnerState
from src.owner_state.pull import MIRROR_PATH, pull, read_mirror, write_mirror

SILVER_DIR = SILVER_POS_ROOT
SALES_DIR = Path(__file__).resolve().parents[2] / "data" / "internal" / "raw_pos" / "yomyom" / "sales"
# ADR-030: the same report, one file per day, committed beside the monthly ones.
DAILY_SALES_DIR = SALES_DIR.parent / "sales_daily"
# The market half, named here for the same reason the two above are: a caller must be
# able to run the whole engine over a copy of the data with an input withheld. Without
# them, a run that isolates silver still reads production signals and matches — which is
# both slower and less isolated than it claims to be.
from src.common.paths import MATCHING_ROOT, SIGNALS_ROOT  # noqa: E402
SIGNALS_DIR = SIGNALS_ROOT / "competitor_product_signals"
MATCHES_PATH = MATCHING_ROOT / "product_matches.parquet"

# Filled by Phase 1: capability id -> callable(inputs) -> CapabilityOutput
def _runners() -> dict:
    from src.engine import (catalogue_lifecycle, competitor_position, margin_below_cost,
                            owner_questions, price_consistency, reconciliation)
    return {"catalogue_lifecycle": catalogue_lifecycle.run, "price_consistency": price_consistency.run,
            "reconciliation": reconciliation.run, "hygiene": reconciliation.run_hygiene,
            "competitor_position": competitor_position.run,
            "margin_below_cost": margin_below_cost.run, "owner_questions": owner_questions.run}


DEFAULT_RUNNERS: dict = {}          # populated lazily by run_engine


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
    from src.internal_pos.sales_importer import import_sales
    # No stock date: ADR-026 cuts the reconcile window once per run, in load_inputs. This
    # step used to ask for the date and cut the summary with it, which made the boundary a
    # fact decided at import and decided again at load — and the two disagreed on the day
    # no report parsed after a new stock count.
    return import_sales(sales_dir, silver_dir=silver_dir)


def _sales_daily_import(daily_dir: Optional[Path] = None, silver_dir: Optional[Path] = None) -> dict:
    from src.internal_pos.sales_daily_importer import import_sales_daily
    return import_sales_daily(daily_dir or DAILY_SALES_DIR, silver_dir=silver_dir or SILVER_DIR)


def _daily_age(result, now: datetime) -> Optional[int]:
    """Days between the latest daily report day and the run, or None before the first one.

    The one place this is derived: the step's verdict and the run's status both read it, so
    the step can never say "stale" on a run that is not degraded, or the reverse.
    """
    days = (result or {}).get("report_days") or []
    return (now.date() - date.fromisoformat(days[-1])).days if days else None


def _sales_daily_verdict(result, *, now: datetime, freshness_days: int) -> tuple:
    """ADR-030. A failed file is a missing day, and is named. Staleness is the run's concern
    too: once daily reports have started to arrive, a latest one older than the freshness
    limit degrades the run (§4). Before the first report there is nothing to be stale."""
    problems = []
    failed = (result or {}).get("failed_files") or []
    if failed:
        problems.append("failed_files: " + "; ".join(f"{f['file']} ({f['reason']})" for f in failed)
                        + ". Those days are missing, never zero")
    age = _daily_age(result, now)
    if age is not None and age > freshness_days:
        problems.append(f"stale: the latest report day, {result['report_days'][-1]}, is {age} days "
                        f"before the run, and the limit is {freshness_days}")
    return ("degraded", "; ".join(problems)) if problems else ("ok", None)


def _market_chain(skip: bool) -> list:
    """The market half of a run, or nothing when the caller asked to skip it.

    market_context used to sit outside the branch and ran even under `skip`. That made
    `scripts/figures.py --json --skip-market` — the reproduction command, whose own test
    is named "recomputes nothing" — call Open-Meteo and rewrite the committed
    public/data/market-context.json every time a judge ran it. Nothing in the engine
    reads that file; only the legacy chain does. The nightly runs without the flag, so
    the committed context still refreshes where it is meant to.
    """
    if skip:
        return []
    from scripts.rehydrate_silver import rehydrate
    from src.context.build import write_market_context
    from src.signals.competitor_product_signals import build_competitor_product_signals
    from src.matching.product_matching import run_product_matching
    return [("market_context", write_market_context), ("rehydrate_silver", rehydrate),
            ("competitor_signals", build_competitor_product_signals),
            ("product_matching", run_product_matching)]


def _step(steps: list, name: str, fn: Callable, verdict: Optional[Callable] = None):
    """`verdict` lets a step that succeeded still report that it did nothing.

    ADR-017: a sales import that contributes no rows has not failed — it has nothing to
    import — but calling that 'ok' makes a day the reports never arrived indistinguishable
    from a day they did.
    """
    t0 = time.monotonic()
    try:
        result = fn()
        status, error = ("ok", None) if verdict is None else verdict(result)
        steps.append({"step": name, "status": status, "ms": int((time.monotonic() - t0) * 1000),
                      "error": error})
        return result
    except Exception as exc:  # noqa: BLE001 — isolate, record, continue
        steps.append({"step": name, "status": "error", "ms": int((time.monotonic() - t0) * 1000),
                      "error": f"{type(exc).__name__}: {exc}"})
        return None


def _sales_verdict(result) -> tuple:
    """ADR-017. Contributing no rows is not an error and is not ok either: import_sales
    writes nothing and the previous silver tables survive, so the run continues on older
    evidence. Detection keeps publishing — a July discrepancy is still a discrepancy in
    September — and the run says the evidence is older."""
    if result and result.get("monthly_rows"):
        return "ok", None
    return "degraded", "no_rows_imported: the run continued on evidence already on disk"


def run_engine(*, mode: str = "publish", input_csv: Optional[Path] = None, skip_market: bool = False,
               artefact_path: Path = ARTEFACT_PATH, capability_runners: Optional[dict] = None,
               now: Optional[datetime] = None, silver_dir: Optional[Path] = None,
               sales_dir: Optional[Path] = None, population: Optional[str] = None,
               signals_dir: Optional[Path] = None, matches_path: Optional[Path] = None,
               catalogue_path: Optional[Path] = None, daily_sales_dir: Optional[Path] = None) -> dict:
    # Resolved here, not in the signature: a default bound at import time cannot be
    # redirected by a caller that patches the module global, which is how Task 1.9
    # runs the engine over a copy of the data with an input withheld.
    silver_dir = silver_dir or SILVER_DIR
    sales_dir = sales_dir or SALES_DIR
    daily_sales_dir = daily_sales_dir or DAILY_SALES_DIR
    signals_dir = signals_dir or SIGNALS_DIR
    matches_path = matches_path or MATCHES_PATH
    now = now or datetime.now(timezone.utc)
    runners = _runners() if capability_runners is None else capability_runners
    steps: list = []
    policy = load_policy()
    # ADR-020: which catalogue the published artefact counts over is a policy setting,
    # not a constant. GAP-009 is open, so it is 'whole' — no published figure depends
    # on automatic withdrawal, which is what D-14 requires.
    population = population or policy.published_population

    owner = _step(steps, "owner_state_pull", _pull_owner_state) or OwnerState.unavailable("pull_step_failed")
    if input_csv:
        from src.internal_pos.pos_importer import import_pos_file
        _step(steps, "pos_import", lambda: import_pos_file(Path(input_csv)))
    sales = _step(steps, "sales_import", lambda: _sales_import(sales_dir, silver_dir),
                  verdict=_sales_verdict)
    # ADR-017: None when the step raised — unknown, not false. A failed import is already
    # reported as an error; asserting the reports did not arrive would add a claim.
    imported_this_run = None if sales is None else bool(sales.get("monthly_rows"))
    daily = _step(steps, "sales_daily_import", lambda: _sales_daily_import(daily_sales_dir, silver_dir),
                  verdict=lambda r: _sales_daily_verdict(r, now=now, freshness_days=policy.order_freshness_days))
    daily_age = _daily_age(daily, now)
    daily_stale = daily_age is not None and daily_age > policy.order_freshness_days
    for name, fn in _market_chain(skip_market):
        _step(steps, name, fn)

    inputs = _step(steps, "load_inputs", lambda: load_inputs(policy=policy, owner=owner, run_at=now, silver_dir=silver_dir,
                                                           signals_dir=signals_dir, matches_path=matches_path))
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
                # population='whole' suppresses the hand-off, so every other capability
                # counts over the entire catalogue. D-14 forbids putting a figure that
                # depends on automatic withdrawal in front of the owner until GAP-009
                # closes, and those figures must come from THIS implementation under a
                # different population — not from a second script that computes them its
                # own way, which is the defect Phase 3 exists to remove.
                if population != "whole":
                    inputs.withdrawn = getattr(out, "withdrawn_barcodes", set())
                    inputs.idle = getattr(out, "idle_barcodes", set())

    status = "ok"
    if any(s["status"] == "error" for s in steps):
        status = "partial"
    elif (owner.status != "available"
          or imported_this_run is False
          or daily_stale
          or any(o.unavailable_reason == "capability_error" for o in outputs)):
        status = "degraded"

    extra_figures = []
    if inputs is not None:
        from src.engine.provenance import vintage_figures
        from src.engine.surface_candidates import stamp
        stamp(outputs, inputs)
        extra_figures = vintage_figures(inputs)      # figures, NOT a capability

    vintages = inputs.vintages if inputs else _no_inputs_vintages(owner)
    if isinstance(vintages.get("sales"), dict):
        vintages["sales"] = {**vintages["sales"], "imported_this_run": imported_this_run}

    artefact = build_artefact(outputs, vintages=vintages, population=population,
                              thresholds=policy.as_dict(), run={"status": status, "steps": steps},
                              extra_figures=extra_figures, generated_at=now.isoformat(),
                              run_id=uuid.uuid4().hex[:12],
                              inputs_digest=getattr(inputs, "inputs_digest", "") if inputs else "")
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
        # ADR-024, and deliberately AFTER the artefact is out. The catalogue serves three
        # secondary pages; the artefact is the owner's daily screen. If publishing the
        # catalogue can fail, it must fail without taking the artefact with it — so it is
        # its own step, recorded, and it does not raise.
        #
        # A failure leaves the PREVIOUS catalogue.json in place beside a fresh
        # dashboard.json, which is why build_catalogue carries `inputs_digest`: the two
        # files disagreeing is detectable by a reader rather than invisible.
        if published:
            # Derived from artefact_path rather than defaulted to the real location, so a
            # test that redirects the artefact redirects this too and cannot write into
            # public/data/ by omission. The two files are published side by side, and
            # that is now true of every caller rather than of the production one only.
            _step(steps, "catalogue", lambda: write_catalogue(build_catalogue(
                inputs.products if inputs else None,
                generated_at=artefact["generated_at"],
                inputs_digest=artefact["inputs_digest"],
                vintages=artefact["vintages"],
                population=population,
            ), path=catalogue_path or (Path(artefact_path).parent / "catalogue.json")))
    else:
        validate_artefact(artefact, require_complete_registry=complete)
    artefact["run"]["status"] = status
    return {"status": status, "steps": steps, "artefact": artefact, "published": published}


def _no_inputs_vintages(owner: OwnerState) -> dict:
    return {"pos": {"file": None, "as_of": None},
            "sales": {"months": [], "first": None, "last": None, "full_annual_cycle": False},
            # Unknown, not zero: the inputs did not load, so nothing says what arrived.
            "sales_daily": {"first_day": None, "last_day": None, "report_days": None,
                            "missing_days": [], "deliveries_missing_days": []},
            "competitor": {"snapshot_date": None, "sources": []},
            "owner_state": {"pulled_at": owner.pulled_at, "status": owner.status}}
