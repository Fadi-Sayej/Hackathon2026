"""Demand must be measured over the months a product was actually on the shelf.

The failure this guards against: a product that sells 30/month and runs out early
records ~4 units, falls under the reorder threshold, and is never reordered — so it
stays out of stock and stays invisible. Raw units over a calendar period measure
supply, not demand, once supply has run out.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.snapshots.censored_demand import (  # noqa: E402
    STATE_AVAILABLE,
    STATE_DELISTED,
    STATE_NEVER_STOCKED,
    STATE_STOCKOUT_SUSPECTED,
    correct_for_censoring,
    corrected_monthly_demand,
)

PERIODS = [date(2026, m, 1) for m in range(1, 8)]  # Jan..Jul 2026


def m(sold: float, receipts: float) -> dict:
    return {"units_sold": sold, "receipts": receipts}


def test_stockout_month_is_excluded_from_the_denominator():
    """The core correction: an empty middle month must not dilute the rate."""
    months = {
        date(2026, 1, 1): m(90, 100),   # 31 days, on shelf
        date(2026, 2, 1): m(0, 0),      # out of stock — censored
        date(2026, 3, 1): m(93, 100),   # 31 days, on shelf
    }
    out = correct_for_censoring(months, PERIODS[:3])

    assert out["available_months"] == 2
    assert out["censored_months"] == 1
    assert out["available_days"] == 62.0        # Jan 31 + Mar 31, NOT Feb
    # 183 units over 62 in-stock days, not over the 90 calendar days Jan-Mar.
    assert out["demand_per_day_corrected"] == round(183 / 62, 4)
    assert out["availability_state"] == STATE_STOCKOUT_SUSPECTED


def test_the_censored_product_clears_a_threshold_the_raw_figure_misses():
    """The regression that motivated this, at the resolution the data supports.

    Sold well while stocked, then a whole month absent. The naive rate reads the
    latest month (empty) and sees nothing; the corrected rate reads the months it
    was actually on the shelf.
    """
    months = {
        date(2026, 5, 1): m(60, 60),
        date(2026, 6, 1): m(60, 60),
        date(2026, 7, 1): m(0, 0),   # absent all month
    }
    out = correct_for_censoring(months, PERIODS)

    assert out["demand_per_day_naive"] * 30 < 20   # invisible to the old rule
    assert corrected_monthly_demand(out) >= 20     # visible to the new one
    assert out["availability_state"] == STATE_STOCKOUT_SUSPECTED


def test_within_month_stockouts_are_not_detectable_and_are_not_faked():
    """A documented limit, asserted so nobody later assumes otherwise.

    Monthly aggregates cannot say WHEN inside a month the shelf emptied. A product
    that ran out on the 5th still reports sales that month, so the month counts as
    available and the rate is still understated. Correcting it would mean inventing
    a within-month stockout date the data does not contain. The fix is finer POS
    snapshots, not a cleverer estimator.
    """
    ran_out_early = {date(2026, 6, 1): m(30, 30), date(2026, 7, 1): m(4, 0)}
    out = correct_for_censoring(ran_out_early, PERIODS)

    assert out["available_months"] == 2          # July counts as available: it sold
    assert out["censored_months"] == 0
    # Understated, and honestly so — no hidden inflation to paper over the gap.
    assert corrected_monthly_demand(out) < 20


def test_zero_sales_with_deliveries_is_real_zero_demand_not_censoring():
    """It was on the shelf and nobody bought it. That must not be inflated away."""
    months = {p: m(0, 50) for p in PERIODS[:3]}
    out = correct_for_censoring(months, PERIODS[:3])

    assert out["available_months"] == 3
    assert out["censored_months"] == 0
    assert out["demand_per_day_corrected"] == 0.0


def test_never_delivered_is_not_a_stockout():
    """A car wash or an espresso sells without ever being delivered."""
    months = {p: m(40, 0) for p in PERIODS[:3]}
    assert correct_for_censoring(months, PERIODS[:3])["availability_state"] == STATE_NEVER_STOCKED


def test_dropped_line_reads_as_delisted_not_stockout():
    """Sold and stocked early, silent for the rest: the shop walked away."""
    months = {date(2026, 1, 1): m(50, 60), date(2026, 2, 1): m(40, 40)}
    assert correct_for_censoring(months, PERIODS)["availability_state"] == STATE_DELISTED


def test_continuous_availability_reads_as_available():
    months = {p: m(30, 30) for p in PERIODS}
    out = correct_for_censoring(months, PERIODS)
    assert out["availability_state"] == STATE_AVAILABLE
    assert out["censored_months"] == 0


def test_confidence_never_high_on_a_single_month():
    """One month of evidence is a rate, not a confident rate."""
    months = {date(2026, 7, 1): m(60, 60)}
    assert correct_for_censoring(months, PERIODS[-1:])["demand_confidence"] == "low"


def test_heavier_censoring_than_evidence_caps_confidence_low():
    months = {
        date(2026, 1, 1): m(30, 30),
        date(2026, 2, 1): m(0, 0),
        date(2026, 3, 1): m(0, 0),
        date(2026, 4, 1): m(0, 0),
        date(2026, 5, 1): m(30, 30),
    }
    out = correct_for_censoring(months, PERIODS[:5])
    assert out["censored_months"] > out["available_months"]
    assert out["demand_confidence"] == "low"


def test_no_observations_yields_no_rate_rather_than_zero():
    out = correct_for_censoring({}, PERIODS)
    assert out["demand_per_day_corrected"] is None
    assert out["demand_confidence"] == "none"
    assert corrected_monthly_demand(out) is None
