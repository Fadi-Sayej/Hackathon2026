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
    barcode_supplier_map,
    ensure_receipts_csv,
    import_receiving_csv,
    load_receipts,
    make_receipt_id,
    supplier_lead_times,
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
    assert result["skipped_duplicates"] == 0
    assert {row["row_number"] for row in result["rejected_preview"]} == {4, 5}
    assert all(row["source"] == "csv_import" for row in load_receipts(ledger))


# The ledger is append-only and git-ignored, and its only backup is out-of-band.
# Importing the same file twice used to double every quantity in it, silently.
class TestImportIsIdempotent:
    def test_reimporting_the_same_file_changes_nothing(self, tmp_path: Path) -> None:
        source = tmp_path / "upload.csv"
        source.write_text(
            "barcode,product_name,quantity,supplier,unit_cost,received_at,"
            "expiry_date,recorded_at,source\n"
            "111,במבה,12,Osem,2.10,2026-08-10,2026-11-01,2026-08-10T09:00:00Z,manual_ui\n"
            "222,ביסלי,6,Osem,,2026-08-10,,2026-08-10T09:01:00Z,manual_ui\n",
            encoding="utf-8",
        )
        ledger = tmp_path / "receipts.csv"

        first = import_receiving_csv(source, path=ledger)
        assert first["imported_rows"] == 2
        assert first["skipped_duplicates"] == 0

        second = import_receiving_csv(source, path=ledger)
        assert second["imported_rows"] == 0
        assert second["skipped_duplicates"] == 2
        assert {row["row_number"] for row in second["skipped_preview"]} == {2, 3}

        rows = load_receipts(ledger)
        assert len(rows) == 2
        assert sum(int(row["quantity"]) for row in rows) == 18

    def test_two_genuine_same_day_deliveries_both_land(self, tmp_path: Path) -> None:
        # Same barcode, same supplier, same day: receipt_id is identical for
        # both by design. Skipping on it would throw away a real delivery.
        source = tmp_path / "upload.csv"
        source.write_text(
            "barcode,product_name,quantity,supplier,unit_cost,received_at,"
            "expiry_date,recorded_at,source\n"
            "111,במבה,12,Osem,,2026-08-10,,2026-08-10T08:00:00Z,manual_ui\n"
            "111,במבה,12,Osem,,2026-08-10,,2026-08-10T17:30:00Z,manual_ui\n",
            encoding="utf-8",
        )
        ledger = tmp_path / "receipts.csv"

        result = import_receiving_csv(source, path=ledger)
        assert result["imported_rows"] == 2
        assert result["skipped_duplicates"] == 0

        rows = load_receipts(ledger)
        assert len(rows) == 2
        assert rows[0]["receipt_id"] == rows[1]["receipt_id"]
        assert sum(int(row["quantity"]) for row in rows) == 24

        # And re-importing that file still adds nothing.
        assert import_receiving_csv(source, path=ledger)["imported_rows"] == 0
        assert len(load_receipts(ledger)) == 2

    def test_a_second_delivery_that_differs_in_any_field_is_not_a_duplicate(
        self, tmp_path: Path
    ) -> None:
        ledger = tmp_path / "receipts.csv"
        add_receipt(barcode="111", quantity=12, supplier="Osem", received_at="2026-08-10",
                    recorded_at="2026-08-10T08:00:00Z", source="csv_import", path=ledger)

        source = tmp_path / "upload.csv"
        source.write_text(
            "barcode,product_name,quantity,supplier,unit_cost,received_at,"
            "expiry_date,recorded_at,source\n"
            # identical except the quantity — a genuinely different delivery
            "111,,18,Osem,,2026-08-10,,2026-08-10T08:00:00Z,csv_import\n",
            encoding="utf-8",
        )
        assert import_receiving_csv(source, path=ledger)["imported_rows"] == 1
        assert len(load_receipts(ledger)) == 2

    def test_date_written_differently_is_still_the_same_row(self, tmp_path: Path) -> None:
        # The comparison runs on the normalized record, so 10/08/2026 does not
        # sneak past as a new delivery day.
        ledger = tmp_path / "receipts.csv"
        add_receipt(barcode="111", quantity=12, supplier="Osem", received_at="2026-08-10",
                    recorded_at="2026-08-10T08:00:00Z", source="csv_import", path=ledger)

        source = tmp_path / "upload.csv"
        source.write_text(
            "barcode,product_name,quantity,supplier,unit_cost,received_at,"
            "expiry_date,recorded_at,source\n"
            "111,,12,Osem,,10/08/2026,,2026-08-10T08:00:00Z,csv_import\n",
            encoding="utf-8",
        )
        result = import_receiving_csv(source, path=ledger)
        assert result["imported_rows"] == 0
        assert result["skipped_duplicates"] == 1

    def test_a_hand_made_csv_without_recorded_at_is_still_recognized(
        self, tmp_path: Path
    ) -> None:
        # No per-line timestamp to compare, so the remaining columns decide.
        # Without this, every re-import of a hand-typed file would double it,
        # because add_receipt stamps a fresh recorded_at each run.
        source = tmp_path / "upload.csv"
        source.write_text(
            "barcode,quantity,supplier,received_at\n"
            "111,12,Osem,2026-08-10\n",
            encoding="utf-8",
        )
        ledger = tmp_path / "receipts.csv"
        assert import_receiving_csv(source, path=ledger)["imported_rows"] == 1
        second = import_receiving_csv(source, path=ledger)
        assert second["imported_rows"] == 0
        assert second["skipped_duplicates"] == 1
        assert len(load_receipts(ledger)) == 1


def _delivery(barcode: str, supplier: str, day: str, quantity: int = 1) -> dict:
    return {
        "barcode": barcode,
        "supplier": supplier,
        "received_at": day,
        "quantity": str(quantity),
    }


class TestSupplierLeadTimes:
    def test_empty_ledger_yields_no_suppliers(self) -> None:
        assert supplier_lead_times([]) == {}

    def test_two_deliveries_are_not_enough_to_claim_a_median(self) -> None:
        result = supplier_lead_times([
            _delivery("111", "Tempo", "2026-08-01"),
            _delivery("111", "Tempo", "2026-08-08"),
        ])
        assert result["Tempo"]["median_days"] is None
        assert result["Tempo"]["n_observations"] == 2
        assert result["Tempo"]["confidence"] == "low"

    def test_three_deliveries_give_a_medium_confidence_median(self) -> None:
        result = supplier_lead_times([
            _delivery("111", "Tempo", "2026-08-01"),
            _delivery("111", "Tempo", "2026-08-08"),
            _delivery("111", "Tempo", "2026-08-15"),
        ])
        assert result["Tempo"]["median_days"] == 7
        assert result["Tempo"]["n_observations"] == 3
        assert result["Tempo"]["confidence"] == "medium"

    def test_six_deliveries_give_high_confidence(self) -> None:
        days = ["2026-08-01", "2026-08-04", "2026-08-07", "2026-08-10", "2026-08-13", "2026-08-16"]
        result = supplier_lead_times([_delivery("111", "Osem", day) for day in days])
        assert result["Osem"]["median_days"] == 3
        assert result["Osem"]["n_observations"] == 6
        assert result["Osem"]["confidence"] == "high"

    def test_many_lines_on_one_delivery_note_count_as_one_delivery(self) -> None:
        result = supplier_lead_times([
            _delivery(str(n), "Tempo", "2026-08-01") for n in range(20)
        ])
        assert result["Tempo"]["n_observations"] == 1
        assert result["Tempo"]["median_days"] is None

    def test_median_ignores_a_single_outlying_gap(self) -> None:
        result = supplier_lead_times([
            _delivery("111", "Tempo", "2026-01-01"),
            _delivery("111", "Tempo", "2026-01-08"),
            _delivery("111", "Tempo", "2026-01-15"),
            _delivery("111", "Tempo", "2026-06-15"),
        ])
        assert result["Tempo"]["median_days"] == 7

    def test_suppliers_are_tracked_independently(self) -> None:
        rows = [_delivery("111", "Tempo", d) for d in ("2026-08-01", "2026-08-08", "2026-08-15")]
        rows += [_delivery("222", "Osem", d) for d in ("2026-08-01", "2026-08-03", "2026-08-05")]
        result = supplier_lead_times(rows)
        assert result["Tempo"]["median_days"] == 7
        assert result["Osem"]["median_days"] == 2

    def test_rows_with_no_supplier_or_unparseable_date_are_skipped(self) -> None:
        result = supplier_lead_times([
            _delivery("111", "", "2026-08-01"),
            _delivery("111", "Tempo", "not-a-date"),
            _delivery("111", "Tempo", "2026-08-01"),
        ])
        assert list(result) == ["Tempo"]
        assert result["Tempo"]["n_observations"] == 1


class TestBarcodeSupplierMap:
    def test_barcode_maps_to_its_most_recent_supplier(self) -> None:
        result = barcode_supplier_map([
            _delivery("111", "Tempo", "2026-08-01"),
            _delivery("111", "Osem", "2026-08-20"),
            _delivery("222", "Tempo", "2026-08-05"),
        ])
        assert result == {"111": "Osem", "222": "Tempo"}

    def test_rows_missing_a_barcode_or_supplier_are_skipped(self) -> None:
        result = barcode_supplier_map([
            _delivery("", "Tempo", "2026-08-01"),
            _delivery("111", "", "2026-08-01"),
        ])
        assert result == {}

    def test_same_day_tie_for_a_barcode_goes_to_the_later_ledger_row(self) -> None:
        result = barcode_supplier_map([
            _delivery("111", "Tempo", "2026-08-01"),
            _delivery("111", "Osem", "2026-08-01"),
        ])
        assert result == {"111": "Osem"}
