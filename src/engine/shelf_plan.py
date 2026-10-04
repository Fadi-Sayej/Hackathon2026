"""shelf_plan — each fixture's dated plan: which products go on which shelf, with how many facings
(F12-S1 FR-181 … FR-189, FR-192, FR-193).

The plan waits for daily sales the way F8 does (D-30). It requires the catalogue, the layout file
and the daily reports, and stops by F8's own rules: `stale_daily_sales` past F8's freshness limit,
`no_evidence_window` when the reports hold no window. Demand is F8's `daily_mean` over F8's
window, computed by F8's own function and never a second time (INV-085). Which products are
planned comes from `shelf_population`, the one definition `layout_facts` lists from.

Per fixture:
1. **First facings** (FR-182, FR-183). Every planned product with a width gets one, packed shelf
   by shelf: eye level first, then the other shelves in the order recorded. Products whose
   earnings per centimetre are known go first, highest first. Those whose earnings are unknown
   follow, by barcode, and never take a place in the earnings order (INV-090).
2. **Over-full** (FR-184). If the first facings cannot all be packed in that order, the fixture
   gets no plan. Its plan says how much width did not fit. Which product leaves is his decision.
3. **His rules** (FR-188). "At least N" asks for N first facings. "Together" packs its products on
   one shelf. A rule that cannot be met stops the fixture's plan, which names it.
4. **Extra facings** (FR-185, FR-186, FR-187). Only on a fixture with no product of unknown size
   ("no width", "too wide"). On each shelf, the remaining length goes one facing at a time to the
   product whose next facing earns the most per centimetre. The k-th facing counts for
   k^e − (k−1)^e of the first, at the policy elasticity e, up to the facings cap. A product of
   unknown, zero or negative earnings gets no extra facing.

Published: one `shelf.plan` entry per fixture (ADR-038), never a value. The only ₪ figure is a
placed product's margin per sale, a unit figure (INV-087). Earnings per centimetre is a ₪ rate,
so it is used for the order and never published. The publisher refuses it.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Optional

from src.engine.model import CapabilityOutput, Entry, entry_id
from src.engine.order_evidence import evidence_window, product_evidence
from src.engine.order_quantity import itemised_departments
from src.engine.registry import derive_status
from src.engine.shelf_measurement import plan_elasticity
from src.engine.shelf_population import PLANNED, population

CAP, SPEC = "shelf_plan", "F12-S1"
FAMILY, ACTION = "shelf.plan", "arrange_shelf"
UNPLACED_FROM_POPULATION = ("no_sale_in_window", "count_zero_or_below", "stock_unknown", "kept_off", "rejected")


def _earnings(p: dict, rows: list, window, itemised: bool, width_mm: int) -> dict:
    """Margin per sale × demand ÷ width (§5), or which part of it is unknown (FR-187, D-3)."""
    shelf, cost = p.get("shelf_price"), p.get("cost_price")
    margin = round(shelf - cost, 4) if shelf is not None and cost is not None else None
    demand = product_evidence(rows, window)["daily_mean"] if itemised else None
    unknown = [part for part, v in (("margin", margin), ("demand", demand)) if v is None]
    per_cm = margin * demand / (width_mm / 10) if not unknown else None
    because = [why for why, v in (("no_shelf_price", shelf), ("no_unit_cost", cost), ("demand_unknown", demand))
               if v is None]
    return {"margin_per_sale": margin, "daily_mean": demand, "unknown": unknown, "per_cm": per_cm,
            "because": because}


def _groups(candidates: list, rules: list, dept_of: dict) -> list:
    """Units to pack: each "together" set is one unit, overlapping sets merged; others alone."""
    parent = {b: b for b in candidates}

    def find(b):
        while parent[b] != b:
            parent[b] = parent[parent[b]]
            b = parent[b]
        return b

    for r in rules:
        if r["kind"] != "together":
            continue
        members = ([b for b in candidates if dept_of.get(b) == r["department"]] if "department" in r
                   else [b for b in r["barcodes"] if b in parent])
        for b in members[1:]:
            parent[find(b)] = find(members[0])
    units = defaultdict(list)
    for b in candidates:
        units[find(b)].append(b)
    return [sorted(u) for u in units.values()]


def plan_fixture(name: str, fixture: dict, members: dict, products: dict, widths: dict, rules: list,
                 rows: dict, window, itemised: set, policy, elasticity: dict, planned_elsewhere: dict) -> dict:
    eye = fixture.get("eye_level_shelf")
    shelves = fixture["shelves"]
    order = ([eye] if eye else []) + [s["shelf"] for s in shelves if s["shelf"] != eye]
    length_mm = {s["shelf"]: s["length_cm"] * 10 for s in shelves}
    longest = max(length_mm.values())

    planned = sorted(b for b, m in members.items() if m["status"] == PLANNED)
    no_width = [b for b in planned if b not in widths]
    too_wide = [b for b in planned if b in widths and widths[b]["width_mm"] > longest]
    candidates = [b for b in planned if b in widths and b not in too_wide]
    width = {b: widths[b]["width_mm"] for b in candidates}
    earn = {b: _earnings(products[b], rows.get(b, []), window, products[b].get("department") in itemised, width[b])
            for b in candidates}
    kept_on = {b for b in candidates if members[b]["kept_on"]}
    here = [r for r in rules if _applies(r, name, fixture, members)]
    at_least_any = {r["barcode"]: r for r in here if r["kind"] == "at_least"}
    at_least = {b: r for b, r in at_least_any.items() if b in width}
    at_most = {r["barcode"]: r for r in here if r["kind"] == "at_most" and r["barcode"] in width}
    unplaced = {reason: sorted(b for b, m in members.items() if m["status"] == reason)
                for reason in UNPLACED_FROM_POPULATION}
    unplaced["no_width"] = no_width
    unplaced["too_wide"] = [{"barcode": b, "width_mm": widths[b]["width_mm"]} for b in too_wide]
    base = {"unplaced": unplaced, "elasticity": elasticity, "rules": here}

    def stopped(rule: dict, why: str) -> dict:
        return {**base, "state": "stopped_by_rule", "stopped_by": {**rule, "why": why}, "shelves": None,
                "planned": planned}

    if not planned:
        return {**base, "state": "no_planned_products", "shelves": None, "planned": []}   # §12: no plan
    if not candidates:
        return {**base, "state": "nothing_placeable", "shelves": None, "planned": planned}

    # FR-188: a rule that cannot be met stops the plan and is named, never dropped. "At least N" on a
    # product the plan does not place (not stocked, kept off, no width, too wide) cannot be met.
    for b, r in sorted(at_least_any.items()):
        if b not in width:
            status = members[b]["status"]
            why = ("no_width" if b in no_width else "too_wide" if b in too_wide else
                   "product_not_planned" if status != PLANNED else "product_not_placed")
            return stopped(r, why)
    # A rule that contradicts itself, or a "together" set split across fixtures, cannot be met.
    for b, low in at_least.items():
        if b in at_most and at_most[b]["facings"] < low["facings"]:
            return stopped(low, "conflicts_with_at_most")
    for r in here:
        if r["kind"] == "together" and "barcodes" in r:
            present = [b for b in r["barcodes"] if b in width]
            away = [b for b in r["barcodes"] if b in planned_elsewhere and planned_elsewhere[b] != name]
            if present and away:
                return stopped(r, "products_on_another_fixture")

    need = {b: max(1, at_least[b]["facings"]) if b in at_least else 1 for b in candidates}
    unknown_sizes = bool(no_width or too_wide)
    dept_of = {b: products[b].get("department") for b in candidates}
    units = _groups(candidates, here, dept_of)

    def key(unit):
        known = [earn[b]["per_cm"] for b in unit if not earn[b]["unknown"]]
        if len(known) == len(unit):       # INV-090: a unit with any unknown member waits its turn
            return (0, -max(known), unit[0])
        return (1, 0.0, unit[0])

    # FR-183, FR-184: one facing each, packed in the earnings order. Whether the fixture is over-full
    # is decided here, on first facings alone, before any rule asks for more.
    free = dict(length_mm)
    facings, shelf_of, did_not_fit = {}, {}, []
    for unit in sorted(units, key=key):
        single = sum(width[b] for b in unit)
        if len(unit) > 1 and single > longest:
            rule = next(r for r in here if r["kind"] == "together" and (
                ("department" in r and dept_of[unit[0]] == r["department"]) or set(unit) & set(r.get("barcodes", []))))
            return stopped(rule, "longer_than_any_shelf")
        spot = next((s for s in order if free[s] >= single), None)
        if spot is None:
            did_not_fit.append(unit)
            continue
        for b in unit:
            facings[b], shelf_of[b] = 1, spot
        free[spot] -= single
    if did_not_fit:
        return {**base, "state": "over_full", "shelves": None, "planned": planned,
                "did_not_fit_cm": round(sum(width[b] for u in did_not_fit for b in u) / 10, 1)}

    # FR-188: his "at least N", on the shelf that holds the product's first facing (FR-185). Where a
    # size is unknown, no spare length is known to be free (FR-186, INV-091), so it cannot be met.
    # It is obeyed for a product of unknown earnings too: INV-086 keeps the plan from giving such a
    # product facings from a guess, and these are facings he stated, not facings the plan chose.
    for b in sorted(at_least, key=lambda b: (order.index(shelf_of[b]), b)):
        more = need[b] - 1
        if more <= 0:
            continue
        if unknown_sizes:
            return stopped(at_least[b], "sizes_unknown")
        if free[shelf_of[b]] < more * width[b]:
            return stopped(at_least[b], "does_not_fit")
        facings[b] += more
        free[shelf_of[b]] -= more * width[b]

    # FR-186: only where every size is known is any spare length known to be free.
    extras = "given" if not unknown_sizes else ("no_width" if no_width else "too_wide")
    if extras == "given":
        e = elasticity["value"]
        limit = {b: min(at_most[b]["facings"] if b in at_most else float("inf"),
                        max(policy.shelf_facings_cap, need[b]) if b not in kept_on else need[b])
                 for b in candidates}
        for s in order:
            while True:
                best = None
                for b in sorted(b for b in candidates if shelf_of[b] == s):
                    per_cm = earn[b]["per_cm"]
                    if per_cm is None or per_cm <= 0 or facings[b] >= limit[b] or width[b] > free[s]:
                        continue
                    k = facings[b]
                    gain = per_cm * ((k + 1) ** e - k ** e)
                    if best is None or gain > best[0]:
                        best = (gain, b)
                if best is None:
                    break
                facings[best[1]] += 1
                free[s] -= width[best[1]]

    known = sorted((b for b in candidates if not earn[b]["unknown"]), key=lambda b: (-earn[b]["per_cm"], b))
    rank = {b: i + 1 for i, b in enumerate(known)}
    out_shelves = []
    for s in shelves:
        here_products = sorted((b for b in candidates if shelf_of[b] == s["shelf"]),
                               key=lambda b: (rank.get(b, len(rank) + 1), b))
        out_shelves.append({
            "shelf": s["shelf"], "length_cm": s["length_cm"], "measured_on": s["measured_on"],
            "eye_level": s["shelf"] == eye,
            "used_cm": round((length_mm[s["shelf"]] - free[s["shelf"]]) / 10, 1),
            "free_cm": round(free[s["shelf"]] / 10, 1),
            "products": [{
                "barcode": b, "product_name": products[b].get("product_name"),
                "department": products[b].get("department"), "facings": facings[b],
                "width_mm": width[b], "width_measured_on": widths[b]["measured_on"],
                "rank": rank.get(b), "unknown_parts": earn[b]["unknown"],
                "unknown_because": earn[b]["because"],
                "margin_per_sale": earn[b]["margin_per_sale"], "daily_mean": earn[b]["daily_mean"],
                "kept_on_by_his_rule": b in kept_on,
                "rules": [r["kind"] for r in (at_least.get(b), at_most.get(b)) if r],
            } for b in here_products]})
    return {**base, "state": "planned", "shelves": out_shelves, "extra_facings": extras,
            "placed": len(candidates)}


def _applies(rule: dict, name: str, fixture: dict, members: dict) -> bool:
    if rule["kind"] in ("keep_on", "keep_off"):
        return rule["fixture"] == name
    if rule["kind"] == "together":
        if "department" in rule:
            return rule["department"] in fixture["departments"]
        return any(b in members for b in rule["barcodes"])
    return rule["barcode"] in members


def run(inputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    layout, policy, run_day = inputs.store_layout, inputs.policy, inputs.run_at.date()
    if not layout.get("fixtures"):
        return CapabilityOutput.unavailable(CAP, SPEC, "layout_all_rejected")
    report_days = sorted({r["day"] for r in inputs.sales_daily})
    if report_days and (run_day - date.fromisoformat(report_days[-1])).days > policy.order_freshness_days:
        return CapabilityOutput.unavailable(CAP, SPEC, "stale_daily_sales")   # F8's own rule (ADR-030 §4)
    window = evidence_window(report_days, policy, inputs.run_at)
    if window is None:
        return CapabilityOutput.unavailable(CAP, SPEC, "no_evidence_window")  # F8-S1 FR-144

    itemised = itemised_departments(inputs)
    pop = population(layout, inputs.products, inputs.sales_daily, window, itemised)
    products = {p["barcode"]: p for p in inputs.products if p.get("barcode")}
    rows = defaultdict(list)
    for r in inputs.sales_daily:
        rows[r["barcode"]].append(r)
    elasticity = plan_elasticity(inputs)   # FR-206: his own only on its three conditions
    planned_on = {b: name for name, members in pop.items() for b, m in members.items() if m["status"] == PLANNED}
    plan_day = run_day.isoformat()
    plan_window = {"first_day": window.first_day, "last_day": window.last_day}

    entries = []
    for index, (name, fixture) in enumerate(layout["fixtures"].items()):
        plan = plan_fixture(name, fixture, pop[name], products, layout.get("widths") or {}, layout.get("rules") or [],
                            rows, window, itemised, policy, elasticity, planned_on)
        evidence = {"fixture": name, "plan_date": plan_day, "plan_window": plan_window,
                    "departments": fixture["departments"], "chilled": fixture["chilled"],
                    "stated_on": fixture["stated_on"], **plan}
        entries.append(Entry(
            id=entry_id(FAMILY, None, f"{name}|{plan_day}"), signal_family=FAMILY, capability=CAP,
            barcode=None, product_name=None, department=None, action=ACTION, characterisation="shelf_plan",
            evidence=evidence, value=None, ordering_key={"name": "fixture_order", "value": index},
            actionable=plan["state"] == "planned",
            not_actionable_reason=None if plan["state"] == "planned" else plan["state"]))
    states = [e.evidence["state"] for e in entries]
    counts = {"fixtures": len(entries), "planned": states.count("planned"), "over_full": states.count("over_full"),
              "stopped_by_rule": states.count("stopped_by_rule"),
              "no_planned_products": states.count("no_planned_products"),
              "nothing_placeable": states.count("nothing_placeable"),
              "placed": sum(e.evidence.get("placed") or 0 for e in entries),
              "no_width": sum(len(e.evidence["unplaced"]["no_width"]) for e in entries),
              "too_wide": sum(len(e.evidence["unplaced"]["too_wide"]) for e in entries)}
    return CapabilityOutput(
        id=CAP, spec=SPEC, status="available", thresholds=policy.as_dict()["shelf_plan"], counts=counts,
        entries=entries, extras={"plan_date": plan_day, "evidence_window": window.to_dict(),
                                 "elasticity": elasticity, "rejected_layout": list(layout.get("rejected") or [])})
