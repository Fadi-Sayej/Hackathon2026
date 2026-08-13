"""
The velocity engine INFERS a restock from any rise in stock between snapshots.
The receiving ledger records what actually arrived. Where the two disagree by
more than a unit, one of them is wrong, and the manager needs to know which.

Every interval here is synthetic — src/snapshots/velocity.py's own tests take the
same approach, because velocity has no ground truth to check against even with
real snapshots.

`_interval()` below builds intervals in the shape build_intervals() actually
emits: one dict per snapshot pair, carrying a `movement` map of
`barcode -> {"sold": ..., "restocked": ...}` (see src/snapshots/velocity.py:237
and compute_velocity's own reads of `item["movement"]`). It does NOT put
`barcode`/`restocked` at the top level of the interval dict — an earlier draft
of this test assumed that shape, and it does not match the real producer.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.internal.restock_reconcile import (  # noqa: E402
    RECONCILE_TOLERANCE_UNITS,
    received_by_barcode,
    reconcile_restocks,
)


def _receipt(barcode: str, day: str, quantity: int, supplier: str = "Tempo") -> dict:
    return {
        "barcode": barcode,
        "supplier": supplier,
        "received_at": day,
        "quantity": str(quantity),
    }


def _interval(barcode: str, restocked: float) -> dict:
    """One synthetic snapshot-pair interval carrying a single barcode's movement."""
    return {"movement": {barcode: {"restocked": restocked, "sold": 0.0}}}


class TestReceivedByBarcode:
    def test_sums_quantities_per_barcode(self) -> None:
        result = received_by_barcode([
            _receipt("111", "2026-08-01", 12),
            _receipt("111", "2026-08-08", 6),
            _receipt("222", "2026-08-01", 4),
        ])
        assert result == {"111": 18.0, "222": 4.0}

    def test_window_excludes_deliveries_outside_it(self) -> None:
        receipts = [
            _receipt("111", "2026-07-01", 10),
            _receipt("111", "2026-08-05", 5),
            _receipt("111", "2026-09-01", 7),
        ]
        assert received_by_barcode(receipts, start="2026-08-01", end="2026-08-31") == {"111": 5.0}

    def test_unparseable_rows_are_skipped_not_counted_as_zero(self) -> None:
        result = received_by_barcode([
            _receipt("111", "not-a-date", 10),
            _receipt("", "2026-08-01", 10),
            _receipt("111", "2026-08-01", 3),
        ])
        assert result == {"111": 3.0}

    def test_empty_ledger_yields_empty_map(self) -> None:
        assert received_by_barcode([]) == {}


class TestReconcileRestocks:
    def test_agreement_within_tolerance_reads_as_a_match(self) -> None:
        result = reconcile_restocks([_receipt("111", "2026-08-01", 12)], [_interval("111", 12.0)])
        assert result["111"]["verdict"] == "matches"
        assert result["111"]["delta"] == 0.0

    def test_tolerance_boundary_is_inclusive(self) -> None:
        result = reconcile_restocks(
            [_receipt("111", "2026-08-01", 12)],
            [_interval("111", 12.0 + RECONCILE_TOLERANCE_UNITS)],
        )
        assert result["111"]["verdict"] == "matches"

    def test_stock_rose_more_than_was_recorded(self) -> None:
        result = reconcile_restocks([_receipt("111", "2026-08-01", 5)], [_interval("111", 20.0)])
        assert result["111"]["verdict"] == "under_recorded"
        assert result["111"]["delta"] == 15.0

    def test_more_was_recorded_than_the_stock_ever_rose(self) -> None:
        result = reconcile_restocks([_receipt("111", "2026-08-01", 30)], [_interval("111", 4.0)])
        assert result["111"]["verdict"] == "over_recorded"
        assert result["111"]["delta"] == -26.0

    def test_stock_rose_with_no_receipt_recorded_at_all(self) -> None:
        result = reconcile_restocks([], [_interval("111", 9.0)])
        assert result["111"]["verdict"] == "no_receipts"
        assert result["111"]["recorded_received"] == 0.0

    def test_receipt_recorded_but_no_snapshot_ever_saw_the_product(self) -> None:
        result = reconcile_restocks([_receipt("111", "2026-08-01", 9)], [])
        assert result["111"]["verdict"] == "unobserved"
        assert result["111"]["inferred_restocked"] == 0.0

    def test_multiple_intervals_for_one_barcode_are_summed(self) -> None:
        result = reconcile_restocks(
            [_receipt("111", "2026-08-01", 20)],
            [_interval("111", 8.0), _interval("111", 12.0)],
        )
        assert result["111"]["verdict"] == "matches"

    def test_barcodes_are_reconciled_independently(self) -> None:
        result = reconcile_restocks(
            [_receipt("111", "2026-08-01", 10), _receipt("222", "2026-08-01", 10)],
            [_interval("111", 10.0), _interval("222", 40.0)],
        )
        assert result["111"]["verdict"] == "matches"
        assert result["222"]["verdict"] == "under_recorded"

    def test_nothing_anywhere_yields_nothing(self) -> None:
        assert reconcile_restocks([], []) == {}
