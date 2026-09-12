# src/engine/catalogue_lifecycle.py
"""SPEC-004 — living / withdrawable / idle, recomputed every run (ADR-004, ADR-011).

No stored lifecycle state: withdrawn = f(evidence window, recorded stock, owner
revivals). Idle entries are ranked by UNIT cost and carry no stock quantity (D-11)."""
from __future__ import annotations

from typing import Optional

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, entry_id
from src.engine.registry import derive_status
from src.owner_state.model import revival_active

CAP, SPEC = "catalogue_lifecycle", "SPEC-004"
PROVISIONAL_STATEMENT = ("Withdrawn on {count} months of evidence ({window}), less than a full annual cycle: "
                         "the evidence cannot separate a seasonal product from a dead one, so this withdrawal "
                         "may be wrong and will be re-examined when longer evidence arrives.")
SETTLED_STATEMENT = "Withdrawn on a full annual cycle of evidence ({window})."


def classify_evidence(row: Optional[dict]) -> str:
    if row is None:
        return "no_row"
    return "observed_units" if float(row.get("units_total") or 0) > 0 else "observed_zero"


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if status == "unavailable":
        empty = CapabilityOutput.unavailable(CAP, SPEC, reason)
        empty.withdrawn_barcodes, empty.idle_barcodes = set(), set()
        return empty
    policy, window, owner = inputs.policy, inputs.window, inputs.owner
    assert not policy.withdraw_with_stock, "OQ-409: stock-carrying withdrawal is not authorised"
    provisional = not window.full_annual_cycle
    revenue_total = sum(float(r.get("revenue") or 0) for r in (inputs.sales_monthly or []))

    counts = {k: 0 for k in ("living", "withdrawable", "idle", "excluded_negative_stock", "excluded_no_identifier",
                             "excluded_stock_absent", "revived_manually", "implausible")}
    withdrawn: list[dict] = []
    idle: list[Entry] = []
    questions: list[Entry] = []
    for p in inputs.products:
        b = p["barcode"]
        if not p["has_identifier"]:
            counts["excluded_no_identifier"] += 1; continue
        stock = p["recorded_stock"]
        if stock is None:
            counts["excluded_stock_absent"] += 1; continue
        if stock < 0:
            counts["excluded_negative_stock"] += 1; continue          # FR-062: hygiene, never withdrawable
        state = classify_evidence(inputs.sales_summary.get(b))
        if state == "observed_units" or revival_active(owner, b, window.window_id):
            counts["living"] += 1
            if state != "observed_units":
                counts["revived_manually"] += 1
            continue
        if stock == 0:
            counts["withdrawable"] += 1
            withdrawn.append({"barcode": b, "product_name": p["product_name"], "department": p["department"],
                              "evidence_state": state, "recorded_stock": 0, "window_id": window.window_id,
                              "months": window.count, "provisional": provisional,
                              "statement": (PROVISIONAL_STATEMENT if provisional else SETTLED_STATEMENT)
                                            .format(count=window.count, window=window.window_id)})
            continue
        counts["idle"] += 1
        cost = p["cost_price"]
        idle.append(Entry(id=entry_id("catalogue.idle", b), signal_family="catalogue.idle",
                          capability=CAP, barcode=b, product_name=p["product_name"],
                          department=p["department"], action="decide_idle", characterisation="idle",
                          evidence={"unit_cost": cost, "cost_source": p["cost_source"], "evidence_state": state,
                                    "window_id": window.window_id},
                          value=None, ordering_key={"name": "unit_cost", "value": cost}))
        # FR-072: the implausibility TEST may use a valuation; the question never states it.
        if cost is not None and revenue_total > 0 and stock * cost > policy.implausible_revenue_share * revenue_total:
            counts["implausible"] += 1
            questions.append(Entry(id=entry_id("catalogue.implausible_quantity", b),
                                   signal_family="catalogue.implausible_quantity", capability=CAP, barcode=b,
                                   product_name=p["product_name"], department=p["department"], action="decide_idle",
                                   characterisation="implausible_quantity",
                                   evidence={"recorded_stock": stock, "unit_cost": cost, "evidence_state": state,
                                             "window_id": window.window_id, "question": "is_this_quantity_right"},
                                   value=None, ordering_key={"name": "unit_cost", "value": cost}))

    assert counts["living"] + counts["withdrawable"] + counts["idle"] == \
        len(inputs.products) - counts["excluded_no_identifier"] - counts["excluded_stock_absent"] - counts["excluded_negative_stock"], "INV-034"
    idle.sort(key=lambda e: (e.ordering_key["value"] is None, -(e.ordering_key["value"] or 0), e.barcode))
    questions.sort(key=lambda e: (-(e.ordering_key["value"] or 0), e.barcode))
    withdrawn.sort(key=lambda w: w["barcode"])

    notes = ["window:" + window.window_id]
    if provisional:
        notes += ["provisional_window", "seasonal_misclassification_possible"]
    statement = ("Classified on {n} months ({w}). Seasonal products may be misclassified as dead; every "
                 "withdrawal is provisional until a full annual cycle of evidence exists.").format(n=window.count, w=window.window_id) \
        if provisional else "Classified on a full annual cycle ({w}).".format(w=window.window_id)
    figures = [Figure(k, v, "products", ["pos", "sales"], {"window": window.window_id}) for k, v in counts.items()]
    out = CapabilityOutput(id=CAP, spec=SPEC, status="available", window=window,
                           thresholds={"implausible_revenue_share": policy.implausible_revenue_share,
                                       "full_annual_cycle_months": policy.full_annual_cycle_months,
                                       "withdraw_with_stock": policy.withdraw_with_stock},
                           counts=counts, entries=questions + idle, figures=figures, notes=notes)
    out.withdrawn_barcodes = {w["barcode"] for w in withdrawn}      # hand-off, not published
    out.idle_barcodes = {e.barcode for e in idle}
    out.extras = {"provisional": provisional, "withdrawn": withdrawn, "statement": statement}
    return out
