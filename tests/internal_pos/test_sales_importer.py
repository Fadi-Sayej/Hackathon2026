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
