"""Which of a fixture's products the plan places, and why each other one is not (F12-S1 §5).

One definition, read by `layout_facts` (the lists it publishes, FR-190, FR-196 … FR-199) and by
`shelf_plan` (the products it packs, FR-182). Two moments deciding the same fact would drift
apart, so neither computes it on its own.

"He stocks" is F8's own test (F8-S1 §5, `order_evidence.stocks`) over F8's own window, and
"itemised" is F8's own definition (`order_quantity.itemised_departments`). Nothing here
re-derives either (INV-085).

A fixture's products are the catalogue products of the departments it holds, as the layout's
"keep on" and "keep off" rules adjust them:
- a "keep on" rule brings a product onto its fixture, whatever its department, and takes it off
  the fixture its department would put it on;
- a "keep off" rule takes it off that fixture, listed there as kept off by his rule.

Each product of a fixture then has one status:
- `planned`: he stocks it, or a "keep on" rule names it (FR-198: planned all the same);
- `no_sale_in_window`: an itemised department, and F8's window records no sale or delivery;
- `count_zero_or_below` / `stock_unknown`: a department the evidence does not itemise, whose
  latest count is not above zero, or is unknown (FR-197);
- `waiting_for_window`: an itemised department while F8's window does not exist. Whether he
  stocks it is not known yet, so it is neither planned nor said to be unstocked;
- `kept_off`: a "keep off" rule (FR-188);
- `rejected`: its department is split across fixtures and no rule names it (FR-199).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from src.engine.order_evidence import Window, stocks

PLANNED = "planned"
REASONS = ("no_sale_in_window", "count_zero_or_below", "stock_unknown", "waiting_for_window",
           "kept_off", "rejected")


def _status(p: dict, rows: list, window: Optional[Window], itemised: bool) -> str:
    if itemised:
        if window is None:
            return "waiting_for_window"
        return PLANNED if stocks(rows, window, p.get("recorded_stock"), itemised=True) else "no_sale_in_window"
    count = p.get("recorded_stock")
    if count is None:
        return "stock_unknown"
    return PLANNED if stocks(rows, window, count, itemised=False) else "count_zero_or_below"


def population(layout: dict, products: list, sales_daily: Optional[list], window: Optional[Window],
               itemised_departments: set) -> dict:
    """`{fixture: {barcode: {status, kept_on}}}` for every fixture the layout holds.

    `kept_on` is True where a "keep on" rule is the only reason the product is planned: he does not
    stock it. Such a product gets one facing only (FR-198), which the plan reads from this flag.
    """
    rows = defaultdict(list)
    for r in sales_daily or []:
        rows[r["barcode"]].append(r)
    by_barcode = {p["barcode"]: p for p in products or [] if p.get("barcode")}
    rejected = {r["key"] for r in layout.get("rejected") or [] if r["kind"] == "product"}
    keep_on = {r["barcode"]: r["fixture"] for r in layout.get("rules") or [] if r["kind"] == "keep_on"}
    keep_off = {(r["barcode"], r["fixture"]) for r in layout.get("rules") or [] if r["kind"] == "keep_off"}

    out: dict = {name: {} for name in layout.get("fixtures") or {}}
    for name, fixture in (layout.get("fixtures") or {}).items():
        held = set(fixture["departments"])
        for barcode, p in by_barcode.items():
            on_rule = keep_on.get(barcode)
            if on_rule is not None:
                if on_rule != name:
                    continue                      # the rule puts it on another fixture
            elif p.get("department") not in held:
                continue
            if (barcode, name) in keep_off:
                out[name][barcode] = {"status": "kept_off", "kept_on": False}
                continue
            if barcode in rejected and on_rule is None:
                out[name][barcode] = {"status": "rejected", "kept_on": False}
                continue
            status = _status(p, rows.get(barcode, []), window, p.get("department") in itemised_departments)
            # FR-198: a product he does not stock is planned all the same, with one facing, when a
            # "keep on" rule names it. A stocked product a rule merely places (FR-199's split
            # departments) is planned like any other, and earns its facings like any other.
            forced = on_rule is not None and status != PLANNED
            out[name][barcode] = {"status": PLANNED if forced else status, "kept_on": forced}
    return out


def departments_on_no_fixture(layout: dict, products: list) -> list:
    held = {d for f in (layout.get("fixtures") or {}).values() for d in f["departments"]}
    return sorted({p["department"] for p in products or [] if p.get("department")} - held)
