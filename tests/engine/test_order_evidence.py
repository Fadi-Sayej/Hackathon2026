# tests/engine/test_order_evidence.py
"""Phase 5 Task 5.5: the evidence math, FR-143 … FR-146, as pure functions."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from src.engine.order_evidence import evidence_window, product_evidence, stocks
from src.engine.policy import load_policy

POLICY = load_policy()
LAST = date(2026, 10, 28)                          # the latest report day in these tests
RUN = datetime(2026, 10, 29, 3, tzinfo=timezone.utc)


def days_back(n: int, *, skip=()) -> list:
    """The `n` calendar days ending on LAST, less `skip` (offsets back from LAST)."""
    return [(LAST - timedelta(days=i)).isoformat() for i in range(n) if i not in skip]


def row(day, units, receipts=0.0, barcode="p"):
    return {"barcode": barcode, "day": day, "units": units, "receipts": receipts}


# ── The window (FR-144) ──────────────────────────────────────────────────────

def test_the_window_is_the_28_days_ending_on_the_latest_report_day():
    w = evidence_window(days_back(40), POLICY, RUN)
    assert (w.first_day, w.last_day) == ((LAST - timedelta(days=27)).isoformat(), LAST.isoformat())
    assert len(w.report_days) == 28
    # Its weeks are the four 7-day blocks counted back from the last day, oldest first.
    assert w.weeks[-1] == ((LAST - timedelta(days=6)).isoformat(), LAST.isoformat())
    assert w.weeks[0] == ((LAST - timedelta(days=27)).isoformat(), (LAST - timedelta(days=21)).isoformat())


def test_21_report_days_with_one_in_every_week_is_a_window():
    missing = (1, 2, 3, 9, 10, 17, 24)                  # 21 of 28 remain, each week keeps days
    assert evidence_window(days_back(28, skip=missing), POLICY, RUN) is not None


def test_20_report_days_is_no_window():
    missing = (1, 2, 3, 9, 10, 17, 24, 25)
    assert len(days_back(28, skip=missing)) == 20
    assert evidence_window(days_back(28, skip=missing), POLICY, RUN) is None


def test_a_week_with_no_report_day_is_no_window():
    """One late or missing export thins the evidence; a whole silent week voids it."""
    days = days_back(35, skip=range(7, 14))             # the second week back is empty
    assert len([d for d in days if d >= (LAST - timedelta(days=27)).isoformat()]) == 21
    assert evidence_window(days, POLICY, RUN) is None


def test_a_latest_report_day_eight_days_before_the_run_is_no_window():
    assert evidence_window(days_back(28), POLICY, datetime(2026, 11, 4, 3, tzinfo=timezone.utc)) is not None  # 7
    assert evidence_window(days_back(28), POLICY, datetime(2026, 11, 5, 3, tzinfo=timezone.utc)) is None      # 8


def test_no_report_day_is_no_window():
    assert evidence_window([], POLICY, RUN) is None


def test_a_report_day_after_the_run_is_not_read():
    """A misnamed future file cannot become the window's last day."""
    w = evidence_window(days_back(28) + ["2027-01-01"], POLICY, RUN)
    assert w.last_day == LAST.isoformat()


# ── One product's evidence (FR-145, FR-146) ──────────────────────────────────

def test_a_missing_day_is_left_out_of_the_mean_not_counted_as_zero():
    days = days_back(28, skip=(3, 4))                   # 26 report days
    w = evidence_window(days, POLICY, RUN)
    ev = product_evidence([row(d, 2.0) for d in days], w)
    assert ev["report_days"] == 26
    assert ev["daily_mean"] == 2.0                      # 52 / 26, not 52 / 28


def test_a_report_day_without_the_product_is_a_day_it_sold_nothing():
    """ASM-065: inside an itemised department, no row on a report day is no sale that day."""
    days = days_back(28)
    w = evidence_window(days, POLICY, RUN)
    ev = product_evidence([row(d, 4.0) for d in days[::2]], w)          # every other day
    assert ev["units_in_window"] == 56.0 and ev["report_days"] == 28
    assert ev["daily_mean"] == 2.0


def test_moving_needs_a_sale_in_every_week():
    days = days_back(28)
    w = evidence_window(days, POLICY, RUN)
    every_week = [row(days[i], 1.0) for i in (0, 7, 14, 21)]
    assert product_evidence(every_week, w)["moving"] is True
    assert product_evidence(every_week, w)["weekly_units"] == [1.0, 1.0, 1.0, 1.0]
    three_weeks = [row(days[i], 5.0) for i in (0, 7, 14)]
    ev = product_evidence(three_weeks, w)
    assert ev["moving"] is False and ev["weekly_units"] == [0.0, 5.0, 5.0, 5.0]


def test_a_blank_units_cell_is_unknown_for_that_day_not_zero():
    days = days_back(28)
    w = evidence_window(days, POLICY, RUN)
    rows = [row(d, 3.0) for d in days[1:]] + [row(days[0], None)]
    ev = product_evidence(rows, w)
    assert ev["report_days"] == 27 and ev["daily_mean"] == 3.0


def test_reprinted_lines_that_disagree_make_the_day_unknown_for_that_product():
    """#156 kept them as printed because nothing can be inferred from them: summing would
    count one day twice, and picking one is a guess."""
    days = days_back(28)
    w = evidence_window(days, POLICY, RUN)
    rows = [row(d, 1.0) for d in days[1:]] + [row(days[0], 4.0), row(days[0], 9.0)]
    ev = product_evidence(rows, w)
    assert ev["report_days"] == 27 and ev["units_in_window"] == 27.0


def test_rows_outside_the_window_do_not_count():
    days = days_back(40)
    w = evidence_window(days, POLICY, RUN)
    ev = product_evidence([row(d, 1.0) for d in days], w)
    assert ev["units_in_window"] == 28.0


def test_a_product_with_no_known_day_has_no_mean():
    days = days_back(28)
    w = evidence_window(days, POLICY, RUN)
    ev = product_evidence([row(d, None) for d in days], w)
    assert ev["daily_mean"] is None and ev["moving"] is False


def test_no_monthly_row_can_enter():
    """INV-070: a report longer than a day is never divided into days. A monthly row that
    reached this function would be exactly that, so it is refused, not read."""
    w = evidence_window(days_back(28), POLICY, RUN)
    with pytest.raises(ValueError, match="INV-070"):
        product_evidence([{"barcode": "p", "month": "2026-10", "units": 60.0, "receipts": 10.0}], w)


# ── "He stocks" (F8-S1 §5) ───────────────────────────────────────────────────

def test_he_stocks_what_the_window_records_a_sale_or_a_delivery_of():
    days = days_back(28)
    w = evidence_window(days, POLICY, RUN)
    assert stocks([row(days[3], 1.0)], w, None, itemised=True) is True
    assert stocks([row(days[3], 0.0, receipts=6.0)], w, None, itemised=True) is True
    assert stocks([row(days[3], None, receipts=None)], w, None, itemised=True) is False
    assert stocks([row((LAST - timedelta(days=40)).isoformat(), 5.0)], w, 12.0, itemised=True) is False
    assert stocks([], w, 12.0, itemised=True) is False          # a count is not a sale


def test_in_a_department_the_evidence_does_not_itemise_it_is_his_latest_count():
    w = evidence_window(days_back(28), POLICY, RUN)
    assert stocks([], w, 3.0, itemised=False) is True
    assert stocks([], w, 0.0, itemised=False) is False
    assert stocks([], w, -2.0, itemised=False) is False
    assert stocks([], w, None, itemised=False) is False         # unknown is not "stocks"


def test_he_stocks_needs_no_window_in_a_department_not_itemised():
    assert stocks([], None, 3.0, itemised=False) is True
    assert stocks([row("2026-10-20", 1.0)], None, None, itemised=True) is False
