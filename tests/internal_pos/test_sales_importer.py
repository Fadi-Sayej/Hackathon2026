# tests/internal_pos/test_sales_importer.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyarrow.parquet as pq

from src.internal_pos.sales_importer import evidence_window, import_sales

HEADER = "תאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n"


def _write(dirpath: Path, name: str, rows: list[str]):
    (dirpath / name).write_text("﻿" + HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")


def test_writes_one_row_per_barcode_per_month_and_a_summary(tmp_path):
    reports = tmp_path / "sales"; reports.mkdir()
    _write(reports, "דוח מכירות חודש ינואר 2026.csv", ["מים,00123,10,2,4,20,12,2,0,1,", "קפה,555,0,1,3,0,0,1,0,1,"])
    _write(reports, "דוח מכירות חודש פברואר 2026.csv", ["מים,123,5,2,4,10,0,2,0,1,"])
    silver = tmp_path / "silver"
    result = import_sales(reports, silver_dir=silver, imported_at="t")

    monthly = pq.read_table(silver / "sales_monthly.parquet").to_pylist()
    assert sorted((r["barcode"], r["month"]) for r in monthly) == [("123", "2026-01"), ("123", "2026-02"), ("555", "2026-01")]
    summary = {r["barcode"]: r for r in pq.read_table(silver / "sales_summary.parquet").to_pylist()}
    assert summary["123"]["units_total"] == 15 and summary["123"]["receipts_total"] == 12
    assert summary["123"]["last_month_with_units"] == "2026-02"
    assert summary["555"]["observed_zero"] is True and summary["555"]["last_month_with_units"] is None
    assert result["window"]["months"] == ["2026-01", "2026-02"]
    assert result["window"]["full_annual_cycle"] is False


def test_evidence_window_requires_consecutive_months():
    w = evidence_window([f"2025-{m:02d}" for m in range(1, 13)], 12)
    assert w.full_annual_cycle is True
    gap = evidence_window(["2025-01", "2025-03"] + [f"2025-{m:02d}" for m in range(4, 14) if m <= 12], 12)
    assert gap.full_annual_cycle is False


def test_no_reports_means_no_window(tmp_path):
    reports = tmp_path / "sales"; reports.mkdir()
    result = import_sales(reports, silver_dir=tmp_path / "silver", imported_at="t")
    assert result["window"] is None and result["monthly_rows"] == 0


# ── A barcode printed twice in one report (#156) ─────────────────────────────
#
# The report is sales per barcode joined to the POS item master, so a barcode with two
# master rows prints its sales once per row. Measured over the seven real reports: 28 pairs
# across 13 barcodes, every pair adjacent, every pair identical in units, cost of sales and
# receipts, and never a month in which one of the 13 printed a single line. Only master
# fields ever differ within a pair: purchase price, net price, discount. Summing both lines
# counted one month's sales twice.

import pytest

ALPRO = "אלפרו 3.5% שומן,5411188134985,15,10.01,13.90,150.15,16,10.01,0.00,16,"


def test_a_barcode_printed_twice_in_one_report_is_one_months_sales(tmp_path):
    reports = tmp_path / "sales"; reports.mkdir()
    _write(reports, "דוח מכירות חודש ינואר 2026.csv", [ALPRO, ALPRO])
    silver = tmp_path / "silver"
    result = import_sales(reports, silver_dir=silver, imported_at="t")

    monthly = pq.read_table(silver / "sales_monthly.parquet").to_pylist()
    assert [(r["barcode"], r["month"], r["units"], r["receipts"], r["cost_price"]) for r in monthly] == [
        ("5411188134985", "2026-01", 15.0, 16.0, 10.01)]
    assert monthly[0]["revenue"] == pytest.approx(15 * 13.90)
    summary = pq.read_table(silver / "sales_summary.parquet").to_pylist()[0]
    assert (summary["units_total"], summary["receipts_total"], summary["months_present"]) == (15.0, 16.0, 1)
    assert (result["reprinted_collapsed"], result["reprinted_kept"]) == (1, 0)


def test_lines_that_differ_only_in_purchase_price_collapse_and_keep_no_price(tmp_path):
    """Two master rows disagreeing on cost: the sales are one month's, the cost is not
    known. ADR-019's rule, at the one field where the lines disagree."""
    reports = tmp_path / "sales"; reports.mkdir()
    _write(reports, "דוח מכירות חודש יוני 2026.csv", [
        "אוריו בטעם וניל,7622300489427,1,20.90,27.90,13.11,10,20.90,0.00,15,",
        "אוריו בטעם וניל,7622300489427,1,13.11,27.90,13.11,10,13.11,0.00,15,"])
    silver = tmp_path / "silver"
    import_sales(reports, silver_dir=silver, imported_at="t")

    monthly = pq.read_table(silver / "sales_monthly.parquet").to_pylist()
    assert [(r["units"], r["receipts"], r["cost_price"]) for r in monthly] == [(1.0, 10.0, None)]
    assert monthly[0]["revenue"] == pytest.approx(27.90)


def test_lines_that_disagree_on_what_sold_are_kept_as_printed_and_said(tmp_path, capsys):
    """Not the mechanism #156 measured, so nothing is inferred from it: the lines stay as
    the report printed them, as before, and the import says so rather than choosing."""
    reports = tmp_path / "sales"; reports.mkdir()
    _write(reports, "דוח מכירות חודש מרץ 2026.csv", [
        "מוצר,7290000000011,3,5.00,9.00,15.00,2,5.00,0.00,1,",
        "מוצר,7290000000011,5,5.00,9.00,25.00,2,5.00,0.00,1,"])
    silver = tmp_path / "silver"
    result = import_sales(reports, silver_dir=silver, imported_at="t")

    monthly = pq.read_table(silver / "sales_monthly.parquet").to_pylist()
    assert sorted(r["units"] for r in monthly) == [3.0, 5.0]
    assert (result["reprinted_collapsed"], result["reprinted_kept"]) == (0, 1)
    assert "WARNING" in capsys.readouterr().err


def test_the_seven_real_reports_hold_each_barcode_once_per_month(tmp_path):
    """Over the committed reports themselves. 3,942 lines are 3,914 barcode-months: the 28
    pairs collapse, and no pair disagrees on what sold."""
    reports = Path(__file__).resolve().parents[2] / "data" / "internal" / "raw_pos" / "yomyom" / "sales"
    silver = tmp_path / "silver"
    result = import_sales(reports, silver_dir=silver, imported_at="t")

    monthly = pq.read_table(silver / "sales_monthly.parquet").to_pylist()
    keys = [(r["barcode"], r["month"]) for r in monthly]
    assert len(keys) == len(set(keys)) == 3914
    assert (result["reprinted_collapsed"], result["reprinted_kept"]) == (28, 0)
