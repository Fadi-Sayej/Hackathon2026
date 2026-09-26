# tests/internal_pos/test_sales_daily_importer.py
"""Phase 5 Task 5.1: the per-day sales reports (ADR-030, F8-S1 FR-143, INV-072)."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyarrow.parquet as pq

from src.internal_pos.sales_daily_importer import day_from_filename, import_sales_daily

# The monthly report's own header (data/internal/raw_pos/yomyom/sales/), run for one day.
HEADER = "תאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n"
NO_DELIVERIES = "תאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),מחיר קניה נטו,הנחה,קוד מחלקה,\n"

ALPRO = "אלפרו 3.5% שומן,5411188134985,15,10.01,13.90,150.15,16,10.01,0.00,16,"


def _name(day: str) -> str:
    return f"דוח מכירות יום {day}.csv"


def _write(dirpath: Path, name: str, rows: list[str], header: str = HEADER):
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / name).write_text("﻿" + header + "".join(r + "\n" for r in rows), encoding="utf-8")


def _rows(silver: Path) -> list[dict]:
    return pq.read_table(silver / "sales_daily.parquet").to_pylist()


# ── The day ──────────────────────────────────────────────────────────────────

def test_the_day_is_read_from_the_file_name(tmp_path):
    reports, silver = tmp_path / "sales_daily", tmp_path / "silver"
    _write(reports, _name("2026-09-20"), ["מים,00123,10,2,4,20,12,2,0,1,"])
    _write(reports, _name("2026-09-21"), ["מים,123,5,2,4,10,0,2,0,1,"])

    result = import_sales_daily(reports, silver_dir=silver)

    assert result["report_days"] == ["2026-09-20", "2026-09-21"]
    assert sorted((r["barcode"], r["day"], r["units"]) for r in _rows(silver)) == [
        ("123", "2026-09-20", 10.0), ("123", "2026-09-21", 5.0)]
    assert set(_rows(silver)[0]) == {"barcode", "day", "units", "receipts"}


def test_a_name_without_one_iso_day_is_a_failed_file(tmp_path):
    """The report carries no date, so a name that does not give one gives nothing."""
    reports, silver = tmp_path / "sales_daily", tmp_path / "silver"
    good = _name("2026-09-20")
    bad = [_name("2026-9-21"), _name("2026-02-30"), "דוח מכירות חודש ספטמבר 2026.csv",
           "דוח מכירות יום 2026-09-22 (1).csv"]
    for name in [good, *bad]:
        _write(reports, name, ["מים,123,5,2,4,10,0,2,0,1,"])

    result = import_sales_daily(reports, silver_dir=silver)

    assert result["report_days"] == ["2026-09-20"]
    assert sorted(f["file"] for f in result["failed_files"]) == sorted(bad)
    assert {f["reason"] for f in result["failed_files"]} == {"no_day_in_name"}
    assert {r["day"] for r in _rows(silver)} == {"2026-09-20"}


def test_day_from_filename_reads_only_the_iso_day():
    assert day_from_filename(Path(_name("2026-09-20"))) == "2026-09-20"
    assert day_from_filename(Path(_name("2026-13-01"))) is None
    assert day_from_filename(Path("דוח מכירות חודש ינואר 2026.csv")) is None


# ── Absence and blanks (ADR-011, INV-071, INV-072) ───────────────────────────

def test_an_absent_product_gets_no_row(tmp_path):
    reports, silver = tmp_path / "sales_daily", tmp_path / "silver"
    _write(reports, _name("2026-09-20"), ["מים,123,10,2,4,20,12,2,0,1,", "קפה,555,3,1,3,3,0,1,0,1,"])
    _write(reports, _name("2026-09-21"), ["מים,123,5,2,4,10,0,2,0,1,"])

    import_sales_daily(reports, silver_dir=silver)

    assert [(r["barcode"], r["day"]) for r in _rows(silver) if r["barcode"] == "555"] == [("555", "2026-09-20")]


def test_a_blank_or_unparseable_cell_is_null_never_zero(tmp_path):
    """Unlike the monthly importer's _num: a blank there reads as 0, and here it would be a
    day of no sales or no deliveries that nobody reported."""
    reports, silver = tmp_path / "sales_daily", tmp_path / "silver"
    _write(reports, _name("2026-09-20"), [
        "מים,123,,2,4,20,,2,0,1,",          # both blank
        "קפה,555,abc,1,3,3,x,1,0,1,",        # both unparseable
        "תה,777,2,1,3,3,0,1,0,1,",           # a real zero delivery stays zero
    ])

    import_sales_daily(reports, silver_dir=silver)

    by = {r["barcode"]: r for r in _rows(silver)}
    assert by["123"]["units"] is None and by["123"]["receipts"] is None
    assert by["555"]["units"] is None and by["555"]["receipts"] is None
    assert by["777"]["units"] == 2.0 and by["777"]["receipts"] == 0.0


def test_a_file_without_the_deliveries_column_has_null_receipts_throughout(tmp_path):
    reports, silver = tmp_path / "sales_daily", tmp_path / "silver"
    _write(reports, _name("2026-09-20"), ["מים,123,10,2,4,20,12,2,0,1,"])
    _write(reports, _name("2026-09-21"), ["מים,123,5,2,4,10,2,0,1,", "קפה,555,1,1,3,3,1,0,1,"],
           header=NO_DELIVERIES)

    result = import_sales_daily(reports, silver_dir=silver)

    assert result["deliveries_reported"] == {"2026-09-20": True, "2026-09-21": False}
    day2 = [r for r in _rows(silver) if r["day"] == "2026-09-21"]
    assert len(day2) == 2 and all(r["receipts"] is None for r in day2)
    assert all(r["units"] is not None for r in day2)


# ── Reprinted lines (#156, ADR-019) ──────────────────────────────────────────

def test_identical_reprinted_lines_collapse(tmp_path):
    reports, silver = tmp_path / "sales_daily", tmp_path / "silver"
    # Only master fields differ (purchase price), exactly as in the 28 measured monthly pairs.
    _write(reports, _name("2026-09-20"), [ALPRO, ALPRO.replace(",10.01,13.90", ",9.50,13.90")])

    result = import_sales_daily(reports, silver_dir=silver)

    assert [(r["barcode"], r["units"], r["receipts"]) for r in _rows(silver)] == [("5411188134985", 15.0, 16.0)]
    assert result["reprinted"] == {"collapsed": 1, "kept": 0}


def test_conflicting_reprinted_lines_stay_as_printed_and_are_counted(tmp_path):
    reports, silver = tmp_path / "sales_daily", tmp_path / "silver"
    _write(reports, _name("2026-09-20"), [ALPRO, ALPRO.replace(",15,", ",4,", 1)])

    result = import_sales_daily(reports, silver_dir=silver)

    assert sorted(r["units"] for r in _rows(silver)) == [4.0, 15.0]
    assert result["reprinted"] == {"collapsed": 0, "kept": 1}


# ── A failed file is a missing day, never a zero day (INV-072) ───────────────

def test_a_failed_file_is_never_a_zero_day(tmp_path):
    reports, silver = tmp_path / "sales_daily", tmp_path / "silver"
    _write(reports, _name("2026-09-20"), ["מים,123,10,2,4,20,12,2,0,1,"])
    # No units column.
    _write(reports, _name("2026-09-21"), ["מים,123,2,4,20,12,2,0,1,"],
           header="תאור פריט,ברקוד/קוד,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n")
    # A header and nothing else: a closed day is a missing day (F8-S1 §12), not a day of no sales.
    _write(reports, _name("2026-09-22"), [])
    # Lines, none of them a product.
    _write(reports, _name("2026-09-23"), ['סה"כ,,40,,,,,,,,'])
    # Not UTF-8.
    reports.joinpath(_name("2026-09-24")).write_bytes(b"\xff\xfe\x00\xd7" + "מים".encode("cp1255"))
    # Empty.
    reports.joinpath(_name("2026-09-25")).write_bytes(b"")

    result = import_sales_daily(reports, silver_dir=silver)

    assert result["report_days"] == ["2026-09-20"]
    assert list(result["deliveries_reported"]) == ["2026-09-20"]
    failed = {f["file"]: f["reason"] for f in result["failed_files"]}
    assert failed == {
        _name("2026-09-21"): "missing_columns",
        _name("2026-09-22"): "no_product_lines",
        _name("2026-09-23"): "no_product_lines",
        _name("2026-09-24"): "unreadable",
        _name("2026-09-25"): "missing_columns",
    }
    assert {r["day"] for r in _rows(silver)} == {"2026-09-20"}


def test_no_report_day_writes_no_table_and_leaves_no_stale_one(tmp_path):
    """No table is the honest state: an older table left in silver would read as evidence
    that arrived (CLAUDE.md rule 6's orphans)."""
    reports, silver = tmp_path / "sales_daily", tmp_path / "silver"
    silver.mkdir()
    (silver / "sales_daily.parquet").write_bytes(b"from an earlier run")
    _write(reports, _name("2026-09-22"), [])

    result = import_sales_daily(reports, silver_dir=silver)

    assert result["report_days"] == [] and result["deliveries_reported"] == {}
    assert not (silver / "sales_daily.parquet").exists()


def test_a_missing_directory_is_no_report_days(tmp_path):
    result = import_sales_daily(tmp_path / "absent", silver_dir=tmp_path / "silver")
    assert result == {"report_days": [], "failed_files": [], "deliveries_reported": {},
                      "reprinted": {"collapsed": 0, "kept": 0}}
    assert not (tmp_path / "silver" / "sales_daily.parquet").exists()
