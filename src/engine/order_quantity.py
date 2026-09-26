# src/engine/order_quantity.py
"""How much to order of each product, for its department's next order day (F8-S1, ADR-034).

One entry per moving product that gets a quantity. Every figure is computed from the day's
evidence by the pure functions in `order_evidence` and `order_arithmetic`, and every entry
publishes the facts it came from, so the page computes nothing and a print-mode run over the
same committed inputs reproduces it (FR-154, NFR-067).

What reaches a quantity, in order:
1. the department must be itemised by some evidence (FR-156), have a schedule with fixed days
   (FR-146) and a stated shelf life (FR-152), all stated by the owner (ADR-033);
2. an evidence window must exist (FR-144);
3. the product must be moving: a sale in every week of the window (FR-145);
4. the boost, when the market runs out of it and a checked pick exists, raises its daily mean
   once (FR-147). The boost's own capability decides that, and this reads its answer, so the
   two can never disagree about a product's boost;
5. the count is used only when usable (FR-149), and flagged is what reconciliation and hygiene
   publish, from `reconciliation.flagged_barcodes`, the same derivation;
6. `order_arithmetic.quantity` gives the quantity or the reason there is none.

Anything that stops a product short is counted per department, so Reorder can say which of
FR-155's reasons holds (D-3). A product whose stock covers the need is counted as covered,
never shown as a zero (FR-150). No entry carries a value or any money field (INV-069).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta

from src.engine import market_boost, reconciliation
from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Entry, entry_id
from src.engine.order_arithmetic import cycle_days, next_order_day, quantity, stock_at_order_day, stock_now
from src.engine.order_evidence import evidence_window, product_evidence
from src.engine.registry import derive_status
from src.engine.stock_date import usable_stock_date

CAP, SPEC = "order_quantity", "F8-S1"
FAMILY, ACTION = "order.suggestion", "place_order"


def _itemised_departments(inputs: EngineInputs) -> set:
    """Departments with a sales row in any evidence, monthly reports included (FR-156)."""
    dept_of = {p["barcode"]: p["department"] for p in inputs.products if p["barcode"]}
    seen = {r.get("barcode") for r in (inputs.sales_monthly or [])} | {r["barcode"] for r in inputs.sales_daily}
    return {dept_of[b] for b in seen if b in dept_of}


def _boost_for(inputs: EngineInputs, boost_out: CapabilityOutput, barcode: str) -> dict:
    """What the boost is for one product tonight, with why when there is none (FR-147, FR-148)."""
    none = {"applied": False, "pct": None, "model_pick_pct": None, "reason": None,
            "reason_withheld_because": None, "model": None, "label": None, "not_applied_because": None}
    signal = inputs.running_out
    if signal is None or boost_out.unavailable_reason in ("market_signal_thin", "market_signal_stale"):
        return {**none, "not_applied_because": boost_out.unavailable_reason or "market_signal_thin"}
    if barcode not in signal["products"]:
        return {**none, "not_applied_because": "market_not_running_out"}
    if boost_out.status != "available":
        return {**none, "not_applied_because": boost_out.unavailable_reason}
    pick = boost_out.extras["picks"].get(barcode)
    if pick is None:
        # Running out, but not asked: its department lacks a stated fact, or it is not moving.
        return {**none, "not_applied_because": "not_asked"}
    return {"applied": pick["applied"], "pct": pick["boost_pct"], "model_pick_pct": pick["model_pick_pct"],
            "reason": pick["reason"], "reason_withheld_because": pick["reason_withheld_because"],
            "model": pick["model"], "label": "model_estimate" if pick["model"] else None,
            "not_applied_because": pick["not_applied_because"]}


def _schedule_changed(inputs: EngineInputs, barcode: str, order_day: str, run_day: str) -> bool:
    """ADR-034 Decision 4: an approval recorded for a pending order day that is no longer the
    department's next one. It never carries to the new day; the engine says so."""
    for rec in (inputs.owner.outcomes or {}).values():
        snap = (rec or {}).get("snapshot") or {}
        if (rec.get("status") == "acted" and snap.get("signal_family") == FAMILY
                and snap.get("barcode") == barcode and snap.get("order_day")
                and run_day <= snap["order_day"] != order_day):
            return True
    return False


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    policy, run_day = inputs.policy, inputs.run_at.date()
    report_days = sorted({r["day"] for r in inputs.sales_daily})
    last_day = report_days[-1] if report_days else None
    if last_day and (run_day - date.fromisoformat(last_day)).days > policy.order_freshness_days:
        # ADR-030 §4: daily reports have started and then stopped. Not "no window": nothing
        # this old describes tonight's orders.
        return CapabilityOutput.unavailable(CAP, SPEC, "stale_daily_sales")

    window = evidence_window(report_days, policy, inputs.run_at)
    facts_by_dept = inputs.store_facts.get("facts") or {}
    itemised = _itemised_departments(inputs)
    rows = defaultdict(list)
    delivered_on = defaultdict(bool)
    for r in inputs.sales_daily:
        rows[r["barcode"]].append(r)
        delivered_on[r["day"]] |= r.get("receipts") is not None
    deliveries_reported = {d: delivered_on[d] for d in report_days}
    withdrawn = inputs.withdrawn or set()
    flags = reconciliation.flagged_barcodes(inputs)
    boost_out = market_boost.run(inputs)
    pos = (inputs.vintages or {}).get("pos") or {}
    count_date = usable_stock_date(pos.get("as_of"), source=pos.get("as_of_source"), today=run_day)

    departments = defaultdict(lambda: {"reasons": Counter(), "suggested": 0, "covered_by_stock": 0})
    entries = []
    for p in inputs.products:
        barcode, dept_name = p["barcode"], p["department"]
        if not barcode or barcode in withdrawn:
            continue
        dept = departments[dept_name]
        stated = facts_by_dept.get(dept_name) or {}
        schedule, shelf = stated.get("order_schedule"), stated.get("shelf_life")
        stop = ("not_itemised" if dept_name not in itemised else
                "no_order_schedule" if not schedule else
                "no_fixed_days" if schedule["form"] == "no_fixed_days" else
                "no_shelf_life" if not shelf else
                "no_window" if window is None else None)
        if stop:
            dept["reasons"][stop] += 1
            continue
        evidence = product_evidence(rows.get(barcode, []), window)
        if not evidence["moving"]:
            dept["reasons"]["not_moving"] += 1
            continue
        boost = _boost_for(inputs, boost_out, barcode)
        mean = evidence["daily_mean"] * (1 + boost["pct"] / 100) if boost["applied"] else evidence["daily_mean"]
        order_day = next_order_day(schedule, run_day)
        cycle = cycle_days(schedule, order_day)
        count = stock_now(p["recorded_stock"], count_date, barcode in flags, rows.get(barcode, []),
                          deliveries_reported, run_day, policy)
        at_order = (stock_at_order_day(count["stock_now"], mean, run_day, order_day)
                    if count["stock_now"] is not None else None)
        q = quantity(daily_mean=mean, cycle=cycle, shelf_life=shelf, stock_at_order=at_order)
        if q["quantity"] is None:
            if q["reason"] == "covered":
                dept["covered_by_stock"] += 1
            else:
                dept["reasons"][q["reason"]] += 1
            continue
        dept["suggested"] += 1
        entries.append(Entry(
            id=entry_id(FAMILY, barcode, order_day.isoformat()), signal_family=FAMILY, capability=CAP,
            barcode=barcode, product_name=p["product_name"], department=dept_name, action=ACTION,
            characterisation="order_suggestion", value=None,
            ordering_key={"name": "units_in_window", "value": evidence["units_in_window"]},
            evidence={
                "order_day": order_day.isoformat(),
                "cycle": {"first_day": order_day.isoformat(),
                          "last_day": (order_day + timedelta(days=cycle - 1)).isoformat(), "days": cycle},
                "schedule": {**schedule, "stated_on": stated["stated_on"]},
                "schedule_changed": _schedule_changed(inputs, barcode, order_day.isoformat(), run_day.isoformat()),
                "window": window.to_dict(), "weekly_units": evidence["weekly_units"],
                "report_days": evidence["report_days"], "units_in_window": evidence["units_in_window"],
                "daily_mean": evidence["daily_mean"], "boost": boost, "adjusted_daily_mean": mean,
                "expected_sales": q["expected_sales"],
                "count": {"recorded_stock": p["recorded_stock"], "as_of": pos.get("as_of"),
                          "used": count["stock_now"] is not None, "not_used_because": count["not_used_because"],
                          "flags": flags.get(barcode, [])},
                "since_count": ({"deliveries": count["deliveries_since"], "sales": count["sales_since"]}
                                if count["stock_now"] is not None else None),
                "stock_now": count["stock_now"], "stock_at_order_day": at_order,
                "shelf_life": {**shelf, "stated_on": stated["stated_on"]},
                "need": q["need"], "cap": q["cap"], "capped": q["capped"],
                "kind": q["kind"], "quantity": q["quantity"],
            }))

    entries.sort(key=lambda e: (e.department or "", -e.ordering_key["value"], e.barcode))
    published = {name: {"reasons": dict(sorted(d["reasons"].items())), "suggested": d["suggested"],
                        "covered_by_stock": d["covered_by_stock"]} for name, d in sorted(departments.items(), key=lambda kv: str(kv[0]))}
    counts = {"suggested": len(entries),
              "covered_by_stock": sum(d["covered_by_stock"] for d in published.values()),
              "no_quantity": sum(sum(d["reasons"].values()) for d in published.values())}
    return CapabilityOutput(
        id=CAP, spec=SPEC, status="available", thresholds=policy.as_dict()["order_quantity"],
        counts=counts, entries=entries,
        extras={"departments": published, "evidence_window": window.to_dict() if window else None,
                "rejected_store_facts": list(inputs.store_facts.get("rejected") or [])})

