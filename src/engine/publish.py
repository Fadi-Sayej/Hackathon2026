# src/engine/publish.py
"""Build, validate and atomically write the artefact (design.md §7.3, §11.4, ADR-005)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import jsonschema

from src.engine.model import CapabilityOutput
from src.engine.registry import CAPABILITIES

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "dashboard.schema.json"
ARTEFACT_PATH = ROOT / "public" / "data" / "dashboard.json"


class PublishRefused(RuntimeError):
    """Raised BEFORE any write. The previous artefact survives."""


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def value_kinds_present(outputs: list[CapabilityOutput]) -> list[str]:
    kinds = set()
    for out in outputs:
        for e in out.entries:
            if e.value is not None:
                kinds.add(e.value.kind)
    return sorted(kinds)


def build_artefact(outputs, *, vintages, thresholds, run, generated_at, run_id, extra_figures=None,
                   inputs_digest: str = "", population: str = "living") -> dict:
    figures = {}
    for out in outputs:
        for f in out.figures:
            figures[f"{out.id}.{f.name}"] = f.to_dict()
    for f in extra_figures or []:                 # provenance vintages: figures, not a capability
        figures[f"provenance.{f.name}"] = f.to_dict()
    return {
        "schema_version": 2,
        "inputs_digest": inputs_digest,
        "population": population,
        "generated_at": generated_at,
        "run_id": run_id,
        "run": run,
        "vintages": vintages,
        "thresholds": thresholds,
        "value_kinds_present": value_kinds_present(outputs),
        "capabilities": {out.id: out.to_dict() for out in outputs},
        "figures": figures,
    }


def validate_artefact(artefact: dict, *, require_complete_registry: bool = False) -> None:
    try:
        jsonschema.validate(artefact, _schema())
    except jsonschema.ValidationError as err:
        raise PublishRefused(f"artefact violates schema: {err.message} at {list(err.absolute_path)}") from err
    if require_complete_registry:
        missing = sorted(set(CAPABILITIES) - set(artefact["capabilities"]))
        if missing:
            raise PublishRefused(
                f"capabilities{{}} must be exactly the registry (ADR-014); missing {missing}. "
                "An absent capability renders as 'nothing to act on', not as 'unavailable'."
            )
    for cap_id, cap in artefact["capabilities"].items():
        if cap.get("status") not in ("available", "unavailable"):
            raise PublishRefused(f"capability {cap_id} has no status")
        spec = CAPABILITIES.get(cap_id)
        if spec is None:
            raise PublishRefused(f"unregistered capability {cap_id}")
        if spec.value_policy == "none":
            for e in cap["entries"]:
                if e.get("value") is not None:
                    raise PublishRefused(f"value_policy none: {cap_id} entry {e['id']} carries a value (D-1)")
    # FR-105: the single-kind premise is derived, and V1 permits at most one kind.
    if len(artefact["value_kinds_present"]) > 1:
        raise PublishRefused("more than one value kind present; FR-106 allocation must be re-derived (GAP-002)")


def write_atomic(path: Path, artefact: dict, *, require_complete_registry: bool = False) -> Path:
    validate_artefact(artefact, require_complete_registry=require_complete_registry)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(artefact, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    return path
