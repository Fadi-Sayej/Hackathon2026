# src/engine/order_arithmetic.py
"""The arithmetic of one order suggestion (F8-S1 FR-146 … FR-153). Pure functions.

Every figure it produces is recomputable from the facts it was given (NFR-067), and every
refusal carries its reason, because a suggestion that is not made must still say why (D-3):
- a count that is not used says why (FR-149): too old, flagged, a day it cannot be carried
  across, or evidence that puts the stock below zero;
- a quantity that is not given says why (FR-150, FR-151, FR-153, FR-155).

Rounding is deliberate. A need rounds to the nearest whole unit, halves up, so that over many
cycles the units ordered match the units expected: always rounding up would turn 1.14 a day
into 2 a day. A quantity the shelf-life cap sets rounds down, so rounding never orders past
what sells before it spoils. Both first settle float noise at nine decimals, so 4.5 computed
as 4.4999999999 is still 4.5.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Iterable, Optional

WEEKDAY = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _day(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _settled(x: float) -> float:
    return round(x, 9)


def _nearest(x: float) -> int:
    return math.floor(_settled(x) + 0.5)


def _down(x: float) -> int:
    return math.floor(_settled(x))


# ── The schedule (FR-146) ────────────────────────────────────────────────────

def next_order_day(schedule: Optional[dict], run_date) -> Optional[date]:
    """The department's first scheduled order day on or after the run's date (F8-S1 §5).

    None for "no fixed days", or when no schedule was stated: nothing is inferred (INV-071).
    """
    if not schedule:
        return None
    run_date = _day(run_date)
    if schedule["form"] == "weekdays":
        days = {WEEKDAY[d] for d in schedule["weekdays"]}
        return next(run_date + timedelta(days=k) for k in range(7) if (run_date + timedelta(days=k)).weekday() in days)
    if schedule["form"] == "every_days":
        first, step = _day(schedule["from"]), schedule["every_days"]
        if run_date <= first:
            return first
        return first + timedelta(days=math.ceil((run_date - first).days / step) * step)
    return None


def cycle_days(schedule: Optional[dict], order_day) -> Optional[int]:
    """The days from an order day up to, not including, the scheduled day after it.

    Sundays and Wednesdays give three days from Sunday and four from Wednesday; each
    suggestion covers its own (FR-146).
    """
    if not schedule or order_day is None:
        return None
    order_day = _day(order_day)
    if schedule["form"] == "weekdays":
        days = {WEEKDAY[d] for d in schedule["weekdays"]}
        return next(k for k in range(1, 8) if (order_day + timedelta(days=k)).weekday() in days)
    if schedule["form"] == "every_days":
        return schedule["every_days"]
    return None


# ── Stock (FR-149) ───────────────────────────────────────────────────────────

def stock_now(count: Optional[float], count_date, flagged: bool, rows: Iterable[dict],
              deliveries_reported: dict, run_date, policy) -> dict:
    """`{stock_now, not_used_because}`: the stock now, or why the count cannot give it.

    A count is carried across every day from the day it was taken to the day before the run
    (SCN-134: a count three days before a Thursday run carries three days' deliveries and
    sales). Each of those days must be a report day with deliveries reported, and the product
    must have a row on it with both figures: the report lists only products that sold, so a
    day without its row has unknown deliveries, not zero (ADR-030 §2). A result below zero
    means the evidence is inconsistent, and the count is not used.
    """
    def refused(reason):
        return {"stock_now": None, "not_used_because": reason}

    if count is None:
        return refused("no_count")
    if count_date is None:
        return refused("no_count_date")
    count_date, run_date = _day(count_date), _day(run_date)
    age = (run_date - count_date).days
    if age < 0:
        return refused("count_after_run")
    if age > policy.order_max_count_age_days:
        return refused("count_too_old")
    if flagged:
        return refused("count_flagged")
    lines = defaultdict(list)
    for r in rows:
        lines[r["day"]].append(r)
    moved = 0.0
    for i in range(age):
        day = (count_date + timedelta(days=i)).isoformat()
        if day not in deliveries_reported:
            return refused("day_without_report")
        if deliveries_reported[day] is not True:
            return refused("deliveries_not_reported")
        printed = lines.get(day)
        if (not printed or any(r.get("units") is None or r.get("receipts") is None for r in printed)
                or len({(r["units"], r["receipts"]) for r in printed}) > 1):
            return refused("no_row_since_count")
        moved += printed[0]["receipts"] - printed[0]["units"]
    value = count + moved
    if _settled(value) < 0:
        return refused("stock_inconsistent")
    return {"stock_now": value, "not_used_because": None}


def stock_at_order_day(stock: float, daily_mean: float, run_date, order_day) -> float:
    """The stock now less what sells before the order day, never below zero (F8-S1 §5)."""
    days = (_day(order_day) - _day(run_date)).days
    return max(0.0, stock - daily_mean * days)


# ── The quantity (FR-150 … FR-153) ───────────────────────────────────────────

def quantity(*, daily_mean: float, cycle: int, shelf_life: Optional[dict],
             stock_at_order: Optional[float]) -> dict:
    """`{quantity, kind, capped, reason, expected_sales, need, cap}` for one suggestion.

    `daily_mean` is the adjusted daily mean: the boost, when one applies, is already in it
    (FR-147). `stock_at_order` is None without a usable count, which makes the suggestion
    gross: "you'll sell about X before your next order" (OQ-902).

    No quantity, never a zero or a small number (FR-155), when: the expected sales for the
    cycle are below one unit; the shelf life is under a day or not stated; the stock already
    covers the need (FR-150, `covered`); or the shelf-life cap rounds down to nothing.
    """
    net = stock_at_order is not None
    expected = daily_mean * cycle
    out = {"quantity": None, "kind": "net" if net else "gross", "capped": False, "reason": None,
           "expected_sales": expected, "need": None, "cap": None}
    if _settled(expected) < 1:
        return {**out, "reason": "below_one_per_cycle"}
    if not shelf_life:
        return {**out, "reason": "no_shelf_life"}
    spoils = not shelf_life.get("does_not_spoil")
    if spoils and (shelf_life.get("days") or 0) < 1:
        return {**out, "reason": "shelf_life_under_a_day"}
    need = max(0.0, expected - stock_at_order) if net else expected
    out["need"] = need
    need_units = _nearest(need)
    if need_units <= 0:
        return {**out, "reason": "covered"}
    if spoils:
        cap = daily_mean * shelf_life["days"] - (stock_at_order or 0.0)
        out["cap"] = cap
        cap_units = _down(cap)
        if cap_units < need_units:
            if cap_units <= 0:
                return {**out, "reason": "cap_rounds_to_zero"}
            return {**out, "quantity": cap_units, "capped": True}
    return {**out, "quantity": need_units}
