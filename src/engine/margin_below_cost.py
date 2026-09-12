# src/engine/margin_below_cost.py
"""Selling below cost — retained from the current product, admitted by nothing.

No specification produces this signal (design.md §22, SPEC-GAP-A): SPEC-001 §3
scopes it out and no SPEC-008 exists yet. FR-103 admits an entry only when its
producing capability states it is actionable today, and an unspecified capability
cannot. So every entry here is published, browsable, and NOT actionable."""
from __future__ import annotations

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, Value, entry_id
from src.engine.registry import derive_status

CAP, SPEC = "margin_below_cost", "UNSPECIFIED"
THIN_MARGIN_PCT = 10.0
REASON = "no_producing_specification"


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    policy, withdrawn = inputs.policy, inputs.withdrawn or set()
    counts = {"below_cost": 0, "thin_margin": 0, "excluded_artefact": 0}
    entries = []
    for p in inputs.products:
        b, shelf, cost = p["barcode"], p["shelf_price"], p["cost_price"]
        if not b or b in withdrawn or shelf is None or cost is None:
            continue
        if shelf < policy.artefact_min_price or cost > policy.artefact_cost_ratio * shelf:
            counts["excluded_artefact"] += 1
            continue
        margin_pct = (shelf - cost) / shelf * 100.0
        if margin_pct >= THIN_MARGIN_PCT:
            continue
        below = cost > shelf
        counts["below_cost" if below else "thin_margin"] += 1
        entries.append(Entry(
            id=entry_id("margin.below_cost", b, "below_cost" if below else "thin_margin"),
            signal_family="margin.below_cost", capability=CAP, barcode=b,
            product_name=p["product_name"], department=p["department"], action="verify_price",
            characterisation="below_cost" if below else "thin_margin",
            evidence={"shelf_price": shelf, "cost_price": cost, "margin_pct": round(margin_pct, 2),
                      "cost_source": p["cost_source"]},
            value=Value(round(cost - shelf, 2), "per_sale", "confirmed") if below else None,
            ordering_key={"name": "loss_per_sale", "value": round(cost - shelf, 2) if below else round(margin_pct, 2)},
            actionable=False, not_actionable_reason=REASON))
    entries.sort(key=lambda e: (0 if e.characterisation == "below_cost" else 1, -e.ordering_key["value"], e.barcode))
    figures = [Figure(k, v, "products", ["pos"]) for k, v in counts.items()]
    return CapabilityOutput(id=CAP, spec=SPEC, status="available",
                            thresholds={"thin_margin_pct": THIN_MARGIN_PCT}, counts=counts,
                            entries=entries, figures=figures, notes=[f"not_admitted:{REASON}"])
