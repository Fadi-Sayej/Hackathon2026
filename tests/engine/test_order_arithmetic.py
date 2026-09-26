# tests/engine/test_order_arithmetic.py
"""Phase 5 Task 5.7: the quantity arithmetic, FR-146 … FR-153, as pure functions."""
from datetime import date, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from src.engine.order_arithmetic import (cycle_days, next_order_day, quantity, stock_at_order_day,
                                         stock_now)
from src.engine.policy import load_policy

POLICY = load_policy()
THU = date(2026, 10, 29)                                    # a Thursday
SUNDAYS = {"form": "weekdays", "weekdays": ["sun"]}
SUN_WED = {"form": "weekdays", "weekdays": ["sun", "wed"]}
EVERY_DAY = {"form": "weekdays", "weekdays": ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]}


def rows(start: date, n: int, units=2.0, receipts=1.0):
    return [{"day": (start + timedelta(days=i)).isoformat(), "units": units, "receipts": receipts} for i in range(n)]


def reported(start: date, n: int, value=True):
    return {(start + timedelta(days=i)).isoformat(): value for i in range(n)}


# ── The schedule (FR-146) ────────────────────────────────────────────────────

def test_a_thursday_run_orders_for_sunday_and_covers_seven_days():
    """SCN-133."""
    assert THU.weekday() == 3
    assert next_order_day(SUNDAYS, THU) == date(2026, 11, 1)
    assert cycle_days(SUNDAYS, date(2026, 11, 1)) == 7


def test_an_order_day_is_on_or_after_the_run():
    sunday = date(2026, 11, 1)
    assert next_order_day(SUNDAYS, sunday) == sunday


def test_sundays_and_wednesdays_give_cycles_of_three_and_four_days():
    monday, thursday = date(2026, 10, 26), THU
    assert next_order_day(SUN_WED, monday) == date(2026, 10, 28)       # Wednesday
    assert cycle_days(SUN_WED, date(2026, 10, 28)) == 4                # Wednesday to Sunday
    assert next_order_day(SUN_WED, thursday) == date(2026, 11, 1)      # Sunday
    assert cycle_days(SUN_WED, date(2026, 11, 1)) == 3                 # Sunday to Wednesday


def test_every_day_is_a_one_day_cycle():
    assert next_order_day(EVERY_DAY, THU) == THU and cycle_days(EVERY_DAY, THU) == 1


def test_an_interval_from_a_stated_first_day():
    every_14 = {"form": "every_days", "every_days": 14, "from": "2026-10-04"}
    assert next_order_day(every_14, date(2026, 10, 1)) == date(2026, 10, 4)     # before the first
    assert next_order_day(every_14, date(2026, 10, 18)) == date(2026, 10, 18)   # on one
    assert next_order_day(every_14, THU) == date(2026, 11, 1)                   # between two
    assert cycle_days(every_14, date(2026, 11, 1)) == 14


def test_no_fixed_days_and_no_schedule_give_no_order_day():
    assert next_order_day({"form": "no_fixed_days"}, THU) is None
    assert cycle_days({"form": "no_fixed_days"}, THU) is None
    assert next_order_day(None, THU) is None


# ── Stock now (FR-149) ───────────────────────────────────────────────────────

MON = THU - timedelta(days=3)


def test_a_recent_unflagged_count_with_every_day_reported_is_used():
    """SCN-134: the count plus the three days' deliveries, less their sales."""
    out = stock_now(20.0, MON, False, rows(MON, 3, units=2.0, receipts=1.0), reported(MON, 3), THU, POLICY)
    assert out == {"stock_now": 17.0, "not_used_because": None}


def test_an_old_count_is_not_used():
    """SCN-133: the recorded stock is dated 6 June."""
    out = stock_now(20.0, date(2026, 6, 6), False, [], {}, THU, POLICY)
    assert out == {"stock_now": None, "not_used_because": "count_too_old"}


def test_a_count_seven_days_old_is_still_used_and_eight_is_not():
    week = THU - timedelta(days=7)
    assert stock_now(50.0, week, False, rows(week, 7), reported(week, 7), THU, POLICY)["stock_now"] == 43.0
    old = THU - timedelta(days=8)
    assert stock_now(50.0, old, False, rows(old, 8), reported(old, 8), THU, POLICY)["not_used_because"] == "count_too_old"


def test_a_flagged_count_is_not_used():
    """SCN-135."""
    out = stock_now(20.0, MON, True, rows(MON, 3), reported(MON, 3), THU, POLICY)
    assert out == {"stock_now": None, "not_used_because": "count_flagged"}


def test_a_day_since_the_count_without_a_report_is_not_crossed():
    missing = {k: v for k, v in reported(MON, 3).items() if k != (MON + timedelta(days=1)).isoformat()}
    out = stock_now(20.0, MON, False, rows(MON, 3), missing, THU, POLICY)
    assert out["not_used_because"] == "day_without_report"


def test_a_day_with_deliveries_unreported_is_not_crossed():
    out = stock_now(20.0, MON, False, rows(MON, 3),
                    {**reported(MON, 3), (MON + timedelta(days=1)).isoformat(): False}, THU, POLICY)
    assert out == {"stock_now": None, "not_used_because": "deliveries_not_reported"}


def test_a_day_the_product_has_no_row_is_not_crossed():
    """ADR-030 §2: a product-day with no row has unknown deliveries, not zero."""
    out = stock_now(20.0, MON, False, rows(MON, 3)[::2], reported(MON, 3), THU, POLICY)
    assert out == {"stock_now": None, "not_used_because": "no_row_since_count"}


def test_a_blank_figure_since_the_count_is_not_crossed():
    blank = rows(MON, 3)
    blank[1]["receipts"] = None
    assert stock_now(20.0, MON, False, blank, reported(MON, 3), THU, POLICY)["not_used_because"] == "no_row_since_count"


def test_a_stock_now_below_zero_means_the_evidence_is_inconsistent():
    """SCN-147: 20 counted, 100 sold, nothing delivered."""
    five = THU - timedelta(days=5)
    out = stock_now(20.0, five, False, rows(five, 5, units=20.0, receipts=0.0), reported(five, 5), THU, POLICY)
    assert out == {"stock_now": None, "not_used_because": "stock_inconsistent"}


def test_no_count_is_not_used():
    assert stock_now(None, MON, False, [], {}, THU, POLICY)["not_used_because"] == "no_count"
    assert stock_now(5.0, None, False, [], {}, THU, POLICY)["not_used_because"] == "no_count_date"


def test_the_stock_at_the_order_day_deducts_the_days_before_it_and_never_goes_below_zero():
    """SCN-134: a Thursday run deducts Thursday to Saturday before Sunday's order."""
    assert stock_at_order_day(17.0, 2.0, THU, date(2026, 11, 1)) == 11.0
    assert stock_at_order_day(4.0, 2.0, THU, date(2026, 11, 1)) == 0.0


# ── The quantity (FR-150 … FR-153) ───────────────────────────────────────────

def test_a_gross_quantity_is_the_expected_sales_rounded_to_the_nearest_unit():
    """SCN-133: gross, seven days at the daily mean."""
    out = quantity(daily_mean=2.1, cycle=7, shelf_life={"days": 90}, stock_at_order=None)
    assert out["quantity"] == 15 and out["kind"] == "gross" and out["capped"] is False   # 14.7 → 15
    assert out["expected_sales"] == pytest.approx(14.7)


def test_a_net_quantity_deducts_the_stock_at_the_order_day():
    """SCN-134."""
    out = quantity(daily_mean=2.0, cycle=7, shelf_life={"days": 90}, stock_at_order=11.0)
    assert (out["quantity"], out["kind"]) == (3, "net")


def test_1_14_a_day_stays_1_rather_than_becoming_2():
    """FR-153: always rounding up would turn 1.14 a day into 2 a day."""
    assert quantity(daily_mean=1.14, cycle=1, shelf_life={"days": 90}, stock_at_order=None)["quantity"] == 1


def test_halves_round_up():
    assert quantity(daily_mean=2.5, cycle=1, shelf_life={"days": 90}, stock_at_order=None)["quantity"] == 3


def test_the_shelf_life_caps_the_quantity_rounding_down():
    """SCN-138: at most two days at the daily mean, less the stock at the order day."""
    gross = quantity(daily_mean=3.0, cycle=7, shelf_life={"days": 2}, stock_at_order=None)
    assert (gross["quantity"], gross["capped"]) == (6, True)
    net = quantity(daily_mean=3.0, cycle=7, shelf_life={"days": 2}, stock_at_order=1.5)
    assert (net["quantity"], net["capped"]) == (4, True)                # cap 4.5 rounds down


def test_a_cap_that_rounds_to_zero_gives_none():
    out = quantity(daily_mean=0.5, cycle=7, shelf_life={"days": 1}, stock_at_order=None)
    assert out["quantity"] is None and out["reason"] == "cap_rounds_to_zero"


def test_does_not_spoil_means_no_cap():
    out = quantity(daily_mean=3.0, cycle=7, shelf_life={"does_not_spoil": True}, stock_at_order=None)
    assert (out["quantity"], out["capped"]) == (21, False)


def test_a_shelf_life_under_a_day_gives_none():
    """SCN-139."""
    out = quantity(daily_mean=30.0, cycle=7, shelf_life={"days": 0}, stock_at_order=None)
    assert out["quantity"] is None and out["reason"] == "shelf_life_under_a_day"


def test_below_one_unit_per_cycle_gives_none():
    """SCN-149: every day, about two a week."""
    out = quantity(daily_mean=2 / 7, cycle=1, shelf_life={"days": 90}, stock_at_order=None)
    assert out["quantity"] is None and out["reason"] == "below_one_per_cycle"


def test_a_net_need_of_zero_is_covered_not_a_zero_quantity():
    """FR-150: not suggested; Reorder counts it as covered by stock."""
    out = quantity(daily_mean=2.0, cycle=7, shelf_life={"days": 90}, stock_at_order=30.0)
    assert out["quantity"] is None and out["reason"] == "covered" and out["kind"] == "net"
    tiny = quantity(daily_mean=2.0, cycle=7, shelf_life={"days": 90}, stock_at_order=13.8)
    assert tiny["quantity"] is None and tiny["reason"] == "covered"                  # 0.2 rounds to 0


def test_the_published_workings_can_be_recomputed():
    """FR-154, NFR-067: expected sales, need and cap travel with the quantity."""
    out = quantity(daily_mean=3.0, cycle=7, shelf_life={"days": 2}, stock_at_order=1.5)
    assert out["expected_sales"] == 21.0 and out["need"] == 19.5 and out["cap"] == 4.5
