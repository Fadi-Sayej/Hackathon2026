"""
censored_demand.py — availability-corrected demand from the monthly sales reports.

THE BUG THIS FIXES
------------------
A product selling 30/month that runs out on the 5th records ~4 units. The reorder
rule asks for `units_sold_30d >= 20`, so it never fires. The products most urgently
needing a reorder are systematically invisible, and stay invisible: they cannot sell
what is not on the shelf. Raw units over a calendar period measure *supply*, not
demand, whenever supply ran out.

WHY NOT SNAPSHOT HISTORY
------------------------
The obvious source is daily inventory snapshots, and src/snapshots/velocity.py
already reads them. It cannot help here: on 2026-09-05 the repo held exactly two POS
snapshots, 66 days apart, whose `current_stock` values are identical for all 7,320
common barcodes — both are re-imports of the same yomyom-inventory.csv. Zero of 7,318
products show any movement between them, so there is no stockout history to read.
That is a data-collection gap, not something to model around.

WHAT WE USE INSTEAD
-------------------
The monthly reports carry `receipts` (כניסות מלאי) as well as units sold. Receipts are
a direct observation of supply, which is exactly the variable that censors demand. For
each month we can therefore ask "was this product on the shelf at all?" and measure the
rate only over months where the answer is yes:

    month has sold > 0 or receipts > 0   → AVAILABLE   (counts toward the rate)
    month has neither, inside the carried span → CENSORED (excluded from the denominator)
    months after the carried span         → possible delisting, not a stockout
    months before it                      → not yet carried; ignored

Excluding censored months from the *denominator* is the whole correction. Counting them
as zero-demand days is what understates the rate today.

HONESTY
-------
This deliberately does not extrapolate. A product available in one month out of seven
gets a rate from that one month and a confidence of "low", not a confident number with
a wide invisible error bar. Callers must read `demand_confidence` before showing a
figure, exactly as they already do for velocity_confidence. Resolution is monthly:
the finest true statement available is "this month it was on the shelf".
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any, Dict, Iterable, List, Optional

from src.snapshots.velocity import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_NONE,
)

# Availability states. Named to match src/market/concentration.py's vocabulary, which
# draws the same stockout-vs-delisting line for competitor branches.
STATE_AVAILABLE = "AVAILABLE"
STATE_STOCKOUT_SUSPECTED = "STOCKOUT_SUSPECTED"
STATE_DELISTED = "DELISTED"
STATE_NEVER_STOCKED = "NEVER_STOCKED"

# Consecutive trailing months with neither a sale nor a delivery before we stop
# calling it a stockout and call it walking away. Two months is deliberately
# conservative: recommending a reorder for something the shop has dropped is a worse
# error than staying quiet about one it has not.
DELISTING_TRAILING_MONTHS = 2


def _days_in(period: date) -> int:
    return calendar.monthrange(period.year, period.month)[1]


def _confidence(available_months: int, censored_months: int) -> str:
    """How much of the product's carried life did we actually observe?

    Mirrors velocity._rate_confidence: history buys confidence, and coarse or
    heavily-censored history caps it. A rate from one month is never "high" no
    matter how clean that month looked.
    """
    if available_months <= 0:
        return CONFIDENCE_NONE

    if available_months >= 3:
        level = CONFIDENCE_HIGH
    elif available_months >= 2:
        level = CONFIDENCE_MEDIUM
    else:
        level = CONFIDENCE_LOW

    # More of the span unobserved than observed: the rate rests on a minority of
    # the product's life and must not present as well-evidenced.
    if censored_months > available_months:
        return CONFIDENCE_LOW
    if censored_months > 0 and level == CONFIDENCE_HIGH:
        return CONFIDENCE_MEDIUM
    return level


def correct_for_censoring(
    months: Dict[date, Dict[str, Any]],
    all_periods: Iterable[date],
) -> Dict[str, Any]:
    """Demand rate over in-stock months only, with the uncertainty that implies.

    `months` maps period -> {"units_sold": float, "receipts": float} for the months
    this product appeared in. `all_periods` is every month covered by the reports, so
    a product's absence from one is itself an observation.
    """
    periods: List[date] = sorted(all_periods)
    empty = {
        "availability_state": STATE_NEVER_STOCKED,
        "available_months": 0,
        "censored_months": 0,
        "available_days": 0.0,
        "censored_days": 0.0,
        "demand_per_day_corrected": None,
        "demand_per_day_naive": None,
        "demand_confidence": CONFIDENCE_NONE,
    }
    if not periods:
        return empty

    def sold_in(p: date) -> float:
        return float((months.get(p) or {}).get("units_sold") or 0.0)

    def recv_in(p: date) -> float:
        return float((months.get(p) or {}).get("receipts") or 0.0)

    available = [p for p in periods if sold_in(p) > 0 or recv_in(p) > 0]
    total_receipts = sum(recv_in(p) for p in periods)

    if not available:
        return empty

    first_av, last_av = available[0], available[-1]
    # Inside the carried span but showing nothing: it was on the shelf either side,
    # so the silence is absence of stock, not absence of demand.
    censored = [p for p in periods if first_av < p < last_av and p not in available]
    trailing = [p for p in periods if p > last_av]

    available_days = float(sum(_days_in(p) for p in available))
    censored_days = float(sum(_days_in(p) for p in censored))
    units_available = sum(sold_in(p) for p in available)

    corrected = units_available / available_days if available_days else None

    # What the current code computes, kept alongside so the difference is auditable.
    latest = periods[-1]
    naive = sold_in(latest) / _days_in(latest)

    if total_receipts <= 0:
        # Sales but never a single delivery on record: a car wash, an espresso pulled
        # to order, staff consumption. Velocity is real; "you are running out" is not.
        state = STATE_NEVER_STOCKED
    elif len(trailing) >= DELISTING_TRAILING_MONTHS:
        state = STATE_DELISTED
    elif censored or trailing:
        state = STATE_STOCKOUT_SUSPECTED
    else:
        state = STATE_AVAILABLE

    return {
        "availability_state": state,
        "available_months": len(available),
        "censored_months": len(censored) + len(trailing),
        "available_days": available_days,
        "censored_days": censored_days + float(sum(_days_in(p) for p in trailing)),
        "demand_per_day_corrected": round(corrected, 4) if corrected is not None else None,
        "demand_per_day_naive": round(naive, 4),
        "demand_confidence": _confidence(len(available), len(censored) + len(trailing)),
    }


def corrected_monthly_demand(entry: Optional[Dict[str, Any]]) -> Optional[float]:
    """The corrected rate expressed as units per 30 days, or None if unknown."""
    if not entry:
        return None
    rate = entry.get("demand_per_day_corrected")
    return None if rate is None else rate * 30.0
