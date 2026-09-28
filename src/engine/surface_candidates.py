# src/engine/surface_candidates.py
"""FR-103 conditions (1), (2) and (4), stamped by the producing side.

Condition (3) — no owner outcome still stands — is applied in the browser, where
an outcome recorded a minute ago is known (ADR-006)."""
from __future__ import annotations

from src.engine.registry import CAPABILITIES

REQUIRED_EVIDENCE = {
    "price_consistency": ("shelf_price", "delivery_price", "difference", "markup_pct"),
    "reconciliation": ("recorded_stock", "receipts", "units_sold", "unaccounted", "window_id"),
    "hygiene": ("reason",),          # the record is wrong on its own evidence; nothing else is needed
    "competitor_position": ("shelf_price", "reference", "premium_pct", "sources"),
    "catalogue_lifecycle": ("evidence_state", "window_id"),
    "margin_below_cost": ("shelf_price", "cost_price", "margin_pct"),
    # F9-S1 FR-168: what the market was seen doing. No value, by design (FR-169).
    "assortment_gap": ("stores_ran_out", "nights_ran_out", "last_ran_out", "window"),
}


def stamp(outputs, inputs):
    for out in outputs:
        spec = CAPABILITIES.get(out.id)
        required = REQUIRED_EVIDENCE.get(out.id, ())
        for e in out.entries:
            if e.not_actionable_reason == "no_producing_specification" or (spec and not spec.admitted):
                e.actionable = False
                e.not_actionable_reason = e.not_actionable_reason or "not_admitted"
                continue
            if out.status != "available":
                e.actionable, e.not_actionable_reason = False, "capability_unavailable"
                continue
            if any(k not in e.evidence or e.evidence[k] is None for k in required):
                e.actionable, e.not_actionable_reason = False, "evidence_incomplete"
                continue
            e.actionable, e.not_actionable_reason = True, None
    return outputs
