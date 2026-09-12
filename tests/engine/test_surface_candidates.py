# tests/engine/test_surface_candidates.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product
from src.engine.model import CapabilityOutput, Entry
from src.engine.surface_candidates import stamp


def _entry(cap, evidence, **kw):
    return Entry(id="i", signal_family=kw.get("family", "price.inverted"), capability=cap,
                 barcode="1", product_name="p", department="d",
                 action=kw.get("action", "verify_price"), characterisation=kw.get("ch", "question"),
                 evidence=evidence, value=None, ordering_key={"name": "k", "value": 1.0})


def test_ac_110a_an_entry_missing_required_evidence_is_not_actionable():
    complete = _entry("price_consistency", {"shelf_price": 1.0, "delivery_price": 2.0, "difference": 1.0, "markup_pct": 100.0})
    incomplete = _entry("price_consistency", {"shelf_price": 1.0})
    out = CapabilityOutput(id="price_consistency", spec="SPEC-001", status="available", entries=[complete, incomplete])
    stamp([out], make_inputs(products=[product("1")]))
    assert complete.actionable is True
    assert incomplete.actionable is False and incomplete.not_actionable_reason == "evidence_incomplete"


def test_entries_of_an_unavailable_capability_are_never_actionable():
    e = _entry("reconciliation", {"recorded_stock": 1, "receipts": 1, "units_sold": 1, "unaccounted": 1, "window_id": "w"},
               family="recon.impossible_opening")
    out = CapabilityOutput(id="reconciliation", spec="SPEC-002", status="unavailable",
                           unavailable_reason="no_sales_evidence", entries=[e])
    stamp([out], make_inputs(products=[product("1")]))
    assert e.actionable is False and e.not_actionable_reason == "capability_unavailable"


def test_hygiene_entries_are_admitted_on_their_own_evidence():
    """Hygiene needs one key — the reason. It must not inherit reconciliation's evidence
    list, or every hygiene record would be stamped evidence_incomplete and never surface."""
    e = _entry("hygiene", {"reason": "negative_stock", "recorded_stock": -3.0},
               family="hygiene.negative_stock", action="fix_record", ch="hygiene")
    out = CapabilityOutput(id="hygiene", spec="SPEC-002", status="available", entries=[e])
    stamp([out], make_inputs(products=[product("1")]))
    assert e.actionable is True


def test_margin_below_cost_stays_unadmitted():
    e = _entry("margin_below_cost", {"shelf_price": 1.0, "cost_price": 2.0, "margin_pct": -100.0},
               family="margin.below_cost")
    e.actionable, e.not_actionable_reason = False, "no_producing_specification"
    out = CapabilityOutput(id="margin_below_cost", spec="UNSPECIFIED", status="available", entries=[e])
    stamp([out], make_inputs(products=[product("1")]))
    assert e.actionable is False and e.not_actionable_reason == "no_producing_specification"
