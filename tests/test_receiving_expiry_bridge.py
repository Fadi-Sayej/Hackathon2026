"""
The receiving ledger and the expiry report must not fork.

A receipt that carries an expiry date IS an expiry observation, and has to reach
the existing report through the existing bucketing/severity logic — not through a
second copy of it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.expiry.expiry_tracking import build_expiry_report  # noqa: E402
from src.internal.receiving import add_receipt, receipts_as_expiry_scans  # noqa: E402


@pytest.fixture()
def ledger(tmp_path: Path) -> Path:
    return tmp_path / "receipts.csv"


@pytest.fixture()
def isolated_report_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect build_expiry_report's real-path side effects into tmp_path.

    build_expiry_report writes Parquet/JSON/Markdown under the module-level
    EXPIRY_SIGNALS_DIR/EXPIRY_REPORTS_DIR constants. Neither is parameterized by
    build_expiry_report's own arguments, so any test that calls it must redirect
    them itself or it both dirties the working tree and leaves stray timestamped
    files behind on every run.

    It also used to call update_source(), which wrote public/data/sources.json. That
    call went with the file (ADR-005, 2026-09-13), so there is nothing left to
    redirect, and tests/test_retired_artefacts.py fails while the file exists.
    """
    import src.expiry.expiry_tracking as expiry_tracking

    monkeypatch.setattr(expiry_tracking, "EXPIRY_SIGNALS_DIR", tmp_path / "signals" / "expiry")
    monkeypatch.setattr(expiry_tracking, "EXPIRY_REPORTS_DIR", tmp_path / "reports" / "expiry")


def test_only_receipts_with_an_expiry_date_become_scans(ledger: Path) -> None:
    add_receipt(barcode="111", quantity=6, supplier="Osem", expiry_date="2026-09-01", path=ledger)
    add_receipt(barcode="222", quantity=6, supplier="Osem", path=ledger)

    scans = receipts_as_expiry_scans(ledger)
    assert [scan["barcode"] for scan in scans] == ["111"]


def test_scan_shape_matches_what_the_report_consumes(ledger: Path) -> None:
    add_receipt(
        barcode="111", quantity=6, supplier="Osem", expiry_date="2026-09-01",
        received_at="2026-08-10", path=ledger,
    )
    scan = receipts_as_expiry_scans(ledger)[0]
    assert set(scan) == {"scan_id", "barcode", "expiry_date", "scanned_at", "source", "notes"}
    assert scan["expiry_date"] == "2026-09-01"
    assert scan["source"] == "receiving:manual_ui"
    assert "6" in scan["notes"] and "Osem" in scan["notes"]


def test_missing_ledger_yields_no_scans(tmp_path: Path) -> None:
    assert receipts_as_expiry_scans(tmp_path / "absent.csv") == []


def test_report_includes_receipt_borne_expiry_dates(
    tmp_path: Path, isolated_report_output: None
) -> None:
    ledger = tmp_path / "receipts.csv"
    scans_csv = tmp_path / "expiry_scans.csv"
    add_receipt(
        barcode="7290000066318", quantity=12, supplier="Tempo",
        expiry_date="2026-08-15", received_at="2026-08-10", path=ledger,
    )

    report = build_expiry_report(as_of="2026-08-13", path=scans_csv, receipts_path=ledger)

    barcodes = [row["barcode"] for row in report["alerts_preview"]]
    assert "7290000066318" in barcodes
    assert report["summary"]["total_scans"] == 1
    severity = next(r["severity"] for r in report["alerts_preview"] if r["barcode"] == "7290000066318")
    assert severity == "critical_7d"


def test_report_still_works_with_no_receipts_at_all(
    tmp_path: Path, isolated_report_output: None
) -> None:
    report = build_expiry_report(
        as_of="2026-08-13",
        path=tmp_path / "expiry_scans.csv",
        receipts_path=tmp_path / "absent.csv",
    )
    assert report["status"] == "ok"
    assert report["summary"]["total_scans"] == 0
