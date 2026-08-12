"""
Tests for the receiving ledger (src/internal/receiving.py).

Every test writes to tmp_path. The real data/internal/receiving/ tree is never
touched — it is git-ignored and absent in a fresh clone.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.internal.receiving import (  # noqa: E402
    RECEIVING_COLUMNS,
    add_receipt,
    ensure_receipts_csv,
    import_receiving_csv,
    load_receipts,
    make_receipt_id,
)


@pytest.fixture()
def ledger(tmp_path: Path) -> Path:
    return tmp_path / "receipts.csv"


def test_ensure_creates_file_with_exact_header(ledger: Path) -> None:
    ensure_receipts_csv(ledger)
    with ledger.open(encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert header == RECEIVING_COLUMNS


def test_add_receipt_writes_every_column(ledger: Path) -> None:
    record = add_receipt(
        barcode="7290000066318",
        quantity=24,
        supplier="Tempo",
        received_at="2026-08-10",
        unit_cost=4.5,
        expiry_date="2026-12-31",
        product_name="קוקה קולה 1.5 ליטר",
        path=ledger,
    )
    assert set(record) == set(RECEIVING_COLUMNS)
    assert record["quantity"] == 24
    assert record["supplier"] == "Tempo"
    assert record["received_at"] == "2026-08-10"
    assert record["expiry_date"] == "2026-12-31"
    assert record["unit_cost"] == 4.5
    assert record["source"] == "manual_ui"

    rows = load_receipts(ledger)
    assert len(rows) == 1
    assert rows[0]["product_name"] == "קוקה קולה 1.5 ליטר"


def test_received_at_defaults_to_today(ledger: Path) -> None:
    record = add_receipt(barcode="123", quantity=1, supplier="Osem", path=ledger)
    assert record["received_at"] == datetime.now(timezone.utc).date().isoformat()


def test_expiry_date_is_optional_and_empty_when_absent(ledger: Path) -> None:
    record = add_receipt(barcode="123", quantity=1, supplier="Osem", path=ledger)
    assert record["expiry_date"] == ""
    assert record["unit_cost"] == ""


def test_receipt_id_is_stable_across_calls(ledger: Path) -> None:
    first = make_receipt_id("123", date(2026, 8, 10), "Tempo")
    second = make_receipt_id("123", date(2026, 8, 10), "Tempo")
    assert first == second
    assert len(first) == 16
    assert make_receipt_id("123", date(2026, 8, 11), "Tempo") != first
    assert make_receipt_id("123", date(2026, 8, 10), "Osem") != first


def test_ledger_is_append_only_and_keeps_same_day_repeat_deliveries(ledger: Path) -> None:
    add_receipt(barcode="123", quantity=6, supplier="Tempo", received_at="2026-08-10", path=ledger)
    add_receipt(barcode="123", quantity=4, supplier="Tempo", received_at="2026-08-10", path=ledger)
    rows = load_receipts(ledger)
    assert [row["quantity"] for row in rows] == ["6", "4"]
    assert rows[0]["receipt_id"] == rows[1]["receipt_id"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"barcode": "", "quantity": 1, "supplier": "Tempo"},
        {"barcode": "   ", "quantity": 1, "supplier": "Tempo"},
        {"barcode": "123", "quantity": 0, "supplier": "Tempo"},
        {"barcode": "123", "quantity": -5, "supplier": "Tempo"},
        {"barcode": "123", "quantity": "abc", "supplier": "Tempo"},
        {"barcode": "123", "quantity": 1, "supplier": ""},
        {"barcode": "123", "quantity": 1, "supplier": "  "},
    ],
)
def test_add_receipt_rejects_invalid_required_fields(ledger: Path, kwargs: dict) -> None:
    with pytest.raises(ValueError):
        add_receipt(path=ledger, **kwargs)


def test_add_receipt_rejects_negative_unit_cost(ledger: Path) -> None:
    with pytest.raises(ValueError):
        add_receipt(barcode="123", quantity=1, supplier="Tempo", unit_cost=-1, path=ledger)


def test_add_receipt_accepts_dd_mm_yyyy_dates(ledger: Path) -> None:
    record = add_receipt(
        barcode="123", quantity=1, supplier="Tempo", received_at="10/08/2026", path=ledger
    )
    assert record["received_at"] == "2026-08-10"


def test_load_receipts_on_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_receipts(tmp_path / "nothing.csv") == []


def test_import_receiving_csv_counts_good_and_rejected_rows(tmp_path: Path) -> None:
    source = tmp_path / "upload.csv"
    source.write_text(
        "barcode,product_name,quantity,supplier,unit_cost,received_at,expiry_date\n"
        "111,במבה,12,Osem,2.10,2026-08-10,2026-11-01\n"
        "222,ביסלי,6,Osem,,2026-08-10,\n"
        ",broken,3,Osem,,2026-08-10,\n"
        "333,bad qty,0,Osem,,2026-08-10,\n",
        encoding="utf-8",
    )
    ledger = tmp_path / "receipts.csv"
    result = import_receiving_csv(source, path=ledger)

    assert result["imported_rows"] == 2
    assert result["rejected_rows"] == 2
    assert {row["row_number"] for row in result["rejected_preview"]} == {4, 5}
    assert all(row["source"] == "csv_import" for row in load_receipts(ledger))
