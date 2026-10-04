# src/engine/publish.py
"""Build, validate and atomically write the artefact (design.md §7.3, §11.4, ADR-005)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import jsonschema

from src.engine.model import CapabilityOutput
from src.engine.policy import D21_MAX_BOOST_PCT
from src.engine.registry import CAPABILITIES

# INV-069: no order suggestion carries a ₪ figure. Checked by name at every depth of its
# evidence, because a nested `unit_cost` is exactly what a schema written for the top level
# would let through, and a suggestion is the one place a total would tempt someone.
MONEY_FIELD = re.compile(r"price|cost|revenue|margin|shekel|money|amount|₪", re.IGNORECASE)


def _money_fields(obj, path=""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = f"{path}.{key}" if path else str(key)
            if MONEY_FIELD.search(str(key)):
                yield here
            yield from _money_fields(value, here)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from _money_fields(value, f"{path}[{i}]")


# D-27 (F9-S1 INV-081 as amended): an assortment-gap entry's one ₪ figure is what each nearby
# store lists it at, `market_prices[*].price` and `.sale_price`. Any other money-named field, at
# any depth, is refused as INV-069 refuses them on an order suggestion.
_LISTED_PRICE = re.compile(r"^market_prices(\[\d+\](\.(price|sale_price))?)?$")


def check_assortment_gap_entry(entry: dict) -> None:
    fields = [f for f in _money_fields(entry.get("evidence") or {}) if not _LISTED_PRICE.match(f)]
    if fields:
        raise PublishRefused(f"assortment_gap entry {entry['id']} carries money-named fields {fields} (INV-081)")


# F12-S1 INV-087: a placed product's margin per sale is the one ₪ figure any F12 capability may
# publish, a unit figure in its evidence, never summed. Earnings per centimetre, a ₪ rate, is
# used for the order and never published; any other money-named field, at any depth, is refused.
_MARGIN_PER_SALE = re.compile(r"^shelves\[\d+\]\.products\[\d+\]\.margin_per_sale$")
# A rate of money over shelf space is the "margin per metre" figure INV-087 names, whatever it is
# called, so it is refused by its shape as well as by the money words.
_SPACE_RATE = re.compile(r"per_(cm|metre|meter)|earnings_per", re.IGNORECASE)
F12_CAPABILITIES = ("layout_facts", "shelf_plan", "shelf_measurement", "shelf_explanation")
_CONTRACT = {"id", "spec", "requires", "status", "unavailable_reason", "window", "thresholds", "counts",
             "entries", "notes"}


def _rate_fields(obj, path=""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = f"{path}.{key}" if path else str(key)
            if _SPACE_RATE.search(str(key)):
                yield here
            yield from _rate_fields(value, here)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from _rate_fields(value, f"{path}[{i}]")


def check_f12_capability(cap_id: str, cap: dict) -> None:
    extras = {k: v for k, v in cap.items() if k not in _CONTRACT}
    fields = list(_money_fields(extras)) + list(_rate_fields(extras))
    for e in cap.get("entries") or []:
        evidence = e.get("evidence") or {}
        fields += [f"{e['id']}.{f}" for f in _money_fields(evidence) if not _MARGIN_PER_SALE.match(f)]
        fields += [f"{e['id']}.{f}" for f in _rate_fields(evidence)]
    if fields:
        raise PublishRefused(f"{cap_id} carries money-named fields {fields} (F12-S1 INV-087)")


def _check_order_suggestion(entry: dict, max_pct: float) -> None:
    fields = list(_money_fields(entry.get("evidence") or {}))
    if fields:
        raise PublishRefused(f"order_quantity entry {entry['id']} carries money-named fields {fields} (INV-069)")
    boost = (entry.get("evidence") or {}).get("boost") or {}
    if boost.get("applied"):
        pct = boost.get("pct")
        # Only an APPLIED boost is checked. A rejected pick is published as the fact it is,
        # "the model said 40", and applying nothing is exactly what FR-147 asks for.
        if not isinstance(pct, (int, float)) or isinstance(pct, bool) or not 0 <= pct <= max_pct:
            raise PublishRefused(f"order_quantity entry {entry['id']} applies a boost of {pct!r}, outside "
                                 f"0–{max_pct} (D-21, FR-147)")

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
        if cap_id == "assortment_gap":
            for e in cap["entries"]:
                check_assortment_gap_entry(e)
        if cap_id in F12_CAPABILITIES:
            check_f12_capability(cap_id, cap)
        if cap_id == "order_quantity":
            declared = ((artefact.get("thresholds") or {}).get("market_boost") or {}).get("max_pct")
            max_pct = min(D21_MAX_BOOST_PCT, declared) if isinstance(declared, (int, float)) else D21_MAX_BOOST_PCT
            for e in cap["entries"]:
                _check_order_suggestion(e, max_pct)
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
