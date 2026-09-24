"""
Tests for snapshot-derived sales velocity (src/snapshots/velocity.py).

The repo has only one real snapshot with stock data, so every scenario here is built
from synthetic snapshots. That is not a workaround — velocity has no ground truth to
check against even with real data, so the only way to trust it is to prove the method
behaves correctly on cases where we know the right answer.

The two tests that matter most, per PLAN.md §3:
  - a restock must NEVER register as sales
  - a 6-day gap must NOT be read as one day
Both would silently corrupt every number the customer sees.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.snapshots.velocity import (  # noqa: E402
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_NONE,
    apply_to_sales_table,
    build_intervals,
    compute_velocity,
    list_usable_snapshots,
    load_snapshot_stock,
)


def _write_snapshot(root: Path, ts: datetime, stock: dict) -> Path:
    """Create a snapshot dir named like the real pipeline does."""
    name = ts.strftime("%Y%m%dT%H%M%SZ")
    path = root / name
    path.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(
        [{"barcode": bc, "current_stock": qty} for bc, qty in stock.items()],
        schema=pa.schema([("barcode", pa.string()), ("current_stock", pa.int64())]),
    )
    pq.write_table(table, path / "inventory.parquet")
    (path / "meta.json").write_text('{"snapshot_ts": "%s"}' % name, encoding="utf-8")
    return path


def _snapshots(root: Path, spec):
    """spec: list of (datetime, {barcode: stock}) -> list of (ts, dir) pairs."""
    for ts, stock in spec:
        _write_snapshot(root, ts, stock)
    return list_usable_snapshots(root)


BASE = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------
# The two critical correctness properties
# --------------------------------------------------------------------------

def test_restock_never_counts_as_sales(tmp_path):
    """Stock going UP is a delivery. It must produce zero sales, not negative."""
    snaps = _snapshots(tmp_path, [
        (BASE, {"111": 10}),
        (BASE + timedelta(days=1), {"111": 60}),   # +50 delivery
    ])
    velocity = compute_velocity(build_intervals(snaps))

    assert velocity["111"]["units_sold_7d"] == 0
    assert velocity["111"]["units_per_day"] == 0.0
    assert velocity["111"]["total_restocked"] == 50
    assert velocity["111"]["last_sale_date"] is None


def test_restock_then_sales_does_not_cancel_out(tmp_path):
    """A delivery in one interval must not erase real sales in another."""
    snaps = _snapshots(tmp_path, [
        (BASE, {"111": 10}),
        (BASE + timedelta(days=1), {"111": 100}),  # +90 delivery
        (BASE + timedelta(days=2), {"111": 80}),   # -20 sold
    ])
    velocity = compute_velocity(build_intervals(snaps))

    assert velocity["111"]["units_sold_7d"] == 20
    assert velocity["111"]["total_restocked"] == 90


def test_interval_is_normalised_by_elapsed_time(tmp_path):
    """The same 60-unit drop over 6 days is 6x slower than over 1 day.

    Reading a 6-day gap as one day is the single most likely way this engine ships
    confidently wrong numbers.
    """
    fast = _snapshots(tmp_path / "fast", [
        (BASE, {"111": 100}),
        (BASE + timedelta(days=1), {"111": 40}),
    ])
    slow = _snapshots(tmp_path / "slow", [
        (BASE, {"111": 100}),
        (BASE + timedelta(days=6), {"111": 40}),
    ])

    fast_rate = compute_velocity(build_intervals(fast))["111"]["units_per_day"]
    slow_rate = compute_velocity(build_intervals(slow))["111"]["units_per_day"]

    assert fast_rate == pytest.approx(60.0)
    assert slow_rate == pytest.approx(10.0)
    assert fast_rate == pytest.approx(slow_rate * 6)


# --------------------------------------------------------------------------
# Duplicate imports
# --------------------------------------------------------------------------

def test_duplicate_import_is_skipped(tmp_path):
    """Two snapshots hours apart are one export imported twice, not an interval.

    This is the shape of the 5 real snapshots in the repo (all within ~2 hours).
    """
    snaps = _snapshots(tmp_path, [
        (BASE, {"111": 100}),
        (BASE + timedelta(hours=2), {"111": 90}),
    ])
    assert build_intervals(snaps) == []


def test_duplicate_does_not_consume_the_anchor(tmp_path):
    """After skipping a duplicate, the next real snapshot still measures from the original.

    If the anchor advanced, the 100 -> 70 movement would be lost entirely.
    """
    snaps = _snapshots(tmp_path, [
        (BASE, {"111": 100}),
        (BASE + timedelta(hours=2), {"111": 95}),   # duplicate, skipped
        (BASE + timedelta(days=2), {"111": 70}),
    ])
    intervals = build_intervals(snaps)

    assert len(intervals) == 1
    assert intervals[0]["elapsed_days"] == pytest.approx(2.0)
    assert intervals[0]["movement"]["111"]["sold"] == pytest.approx(30.0)


# --------------------------------------------------------------------------
# Confidence
# --------------------------------------------------------------------------

def test_no_history_reports_confidence_none(tmp_path):
    """One snapshot yields no intervals at all — and therefore no velocity rows."""
    snaps = _snapshots(tmp_path, [(BASE, {"111": 10})])
    assert build_intervals(snaps) == []
    assert compute_velocity([]) == {}


def test_confidence_grows_with_observed_history(tmp_path):
    """Daily snapshots: 5 days -> low, 10 days -> medium, 40 days -> high."""
    def confidence_after(days: int) -> str:
        root = tmp_path / ("run%d" % days)
        spec = [(BASE + timedelta(days=i), {"111": 1000 - i}) for i in range(days + 1)]
        snaps = _snapshots(root, spec)
        return compute_velocity(build_intervals(snaps))["111"]["velocity_confidence"]

    assert confidence_after(5) == CONFIDENCE_LOW
    assert confidence_after(10) == CONFIDENCE_MEDIUM
    assert confidence_after(40) == CONFIDENCE_HIGH


def test_long_gap_caps_confidence_regardless_of_span(tmp_path):
    """60 days of history sampled as two 30-day gaps is still LOW confidence.

    Long gaps hide restocks, so the span alone must not buy a high rating.
    """
    snaps = _snapshots(tmp_path, [
        (BASE, {"111": 300}),
        (BASE + timedelta(days=30), {"111": 200}),
        (BASE + timedelta(days=60), {"111": 100}),
    ])
    entry = compute_velocity(build_intervals(snaps))["111"]

    assert entry["observed_days"] == pytest.approx(60.0)
    assert entry["velocity_confidence"] == CONFIDENCE_LOW


def test_moderate_gap_caps_at_medium(tmp_path):
    """Weekly snapshots over a long span cap at medium, not high."""
    spec = [(BASE + timedelta(days=7 * i), {"111": 1000 - 10 * i}) for i in range(8)]
    snaps = _snapshots(tmp_path, spec)
    entry = compute_velocity(build_intervals(snaps))["111"]

    assert entry["observed_days"] == pytest.approx(49.0)
    assert entry["velocity_confidence"] == CONFIDENCE_MEDIUM


# --------------------------------------------------------------------------
# Windowing
# --------------------------------------------------------------------------

def test_units_are_prorated_into_the_window(tmp_path):
    """A 10-day interval overlapping the last 7 days contributes only its share."""
    snaps = _snapshots(tmp_path, [
        (BASE, {"111": 200}),
        (BASE + timedelta(days=10), {"111": 100}),  # 100 sold over 10 days
    ])
    entry = compute_velocity(build_intervals(snaps))["111"]

    assert entry["units_sold_30d"] == 100          # whole interval inside 30d
    assert entry["units_sold_7d"] == 70            # 7 of 10 days -> 70 units


def test_old_movement_does_not_leak_into_recent_window(tmp_path):
    """Sales from 40 days ago must not appear in the 7-day figure."""
    snaps = _snapshots(tmp_path, [
        (BASE, {"111": 500}),
        (BASE + timedelta(days=2), {"111": 400}),    # 100 sold, long ago
        (BASE + timedelta(days=45), {"111": 400}),   # nothing since
    ])
    entry = compute_velocity(build_intervals(snaps), as_of=BASE + timedelta(days=45))["111"]

    assert entry["units_sold_7d"] == 0
    assert entry["units_sold_30d"] == 0
    assert entry["last_sale_date"] == (BASE + timedelta(days=2)).date().isoformat()


# --------------------------------------------------------------------------
# Robustness against real-world snapshot dirs
# --------------------------------------------------------------------------

def test_snapshots_without_parquet_are_ignored(tmp_path):
    """Parquets are gitignored, so a fresh clone has meta-only snapshot dirs.

    Treating those as empty inventories would read as "every product sold out".
    """
    (tmp_path / "20260601T090000Z").mkdir(parents=True)
    (tmp_path / "20260601T090000Z" / "meta.json").write_text("{}", encoding="utf-8")
    _write_snapshot(tmp_path, BASE, {"111": 10})

    usable = list_usable_snapshots(tmp_path)
    assert len(usable) == 1


def test_unparseable_directory_names_are_ignored(tmp_path):
    (tmp_path / "not-a-timestamp").mkdir(parents=True)
    (tmp_path / "not-a-timestamp" / "inventory.parquet").write_bytes(b"garbage")
    _write_snapshot(tmp_path, BASE, {"111": 10})

    assert len(list_usable_snapshots(tmp_path)) == 1


def test_new_product_without_baseline_is_skipped(tmp_path):
    """A product appearing for the first time has no prior stock to measure against."""
    snaps = _snapshots(tmp_path, [
        (BASE, {"111": 50}),
        (BASE + timedelta(days=1), {"111": 40, "222": 99}),
    ])
    velocity = compute_velocity(build_intervals(snaps))

    assert "111" in velocity
    assert "222" not in velocity


def test_snapshots_are_ordered_by_timestamp_not_listing_order(tmp_path):
    """Directory iteration order must not affect the result."""
    _write_snapshot(tmp_path, BASE + timedelta(days=3), {"111": 70})
    _write_snapshot(tmp_path, BASE, {"111": 100})

    snaps = list_usable_snapshots(tmp_path)
    assert [ts for ts, _ in snaps] == sorted(ts for ts, _ in snaps)

    entry = compute_velocity(build_intervals(snaps))["111"]
    assert entry["units_per_day"] == pytest.approx(10.0)


def test_load_snapshot_stock_skips_blank_barcodes(tmp_path):
    path = tmp_path / "20260801T090000Z"
    path.mkdir(parents=True)
    table = pa.Table.from_pylist(
        [
            {"barcode": "111", "current_stock": 5},
            {"barcode": "", "current_stock": 9},
            {"barcode": None, "current_stock": 9},
        ],
        schema=pa.schema([("barcode", pa.string()), ("current_stock", pa.int64())]),
    )
    pq.write_table(table, path / "inventory.parquet")

    assert load_snapshot_stock(path) == {"111": 5.0}


# --------------------------------------------------------------------------
# Writing back into the silver sales table
# --------------------------------------------------------------------------

def _sales_stub(path: Path, barcodes) -> Path:
    """Mimic yomyom_sales.parquet as the importer leaves it: velocity columns all null."""
    rows = [
        {
            "barcode": bc,
            "product_name": "product-%s" % bc,
            "category": "test",
            "units_sold_7d": None,
            "units_sold_30d": None,
            "sales_amount_30d": None,
            "last_sale_date": None,
            "_imported_at": "2026-08-01",
            "_source_file": "test.csv",
            "_source_kind": "pos",
        }
        for bc in barcodes
    ]
    schema = pa.schema(
        [
            ("barcode", pa.string()), ("product_name", pa.string()), ("category", pa.string()),
            ("units_sold_7d", pa.int64()), ("units_sold_30d", pa.int64()),
            ("sales_amount_30d", pa.float64()), ("last_sale_date", pa.string()),
            ("_imported_at", pa.string()), ("_source_file", pa.string()), ("_source_kind", pa.string()),
        ]
    )
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
    return path


def _products_stub(path: Path, prices) -> Path:
    rows = [{"barcode": bc, "selling_price": price} for bc, price in prices.items()]
    schema = pa.schema([("barcode", pa.string()), ("selling_price", pa.float64())])
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)
    return path


def test_apply_writes_velocity_and_preserves_unmatched_as_null(tmp_path):
    """Matched products get numbers; unmatched keep NULL units, never 0.

    'No history for this product' and 'this product sold nothing' are different facts.
    Collapsing them to 0 is what makes every product look 'Slow moving'.
    """
    snaps = _snapshots(tmp_path / "snaps", [
        (BASE, {"111": 100}),
        (BASE + timedelta(days=2), {"111": 80}),
    ])
    velocity = compute_velocity(build_intervals(snaps))

    sales = _sales_stub(tmp_path / "sales.parquet", ["111", "999"])
    products = _products_stub(tmp_path / "products.parquet", {"111": 10.0, "999": 4.0})

    stats = apply_to_sales_table(velocity, sales_path=sales, products_path=products)
    assert stats == {"rows": 2, "matched": 1, "unmatched": 1}

    rows = {r["barcode"]: r for r in pq.read_table(sales).to_pylist()}

    assert rows["111"]["units_sold_7d"] == 20
    assert rows["111"]["velocity_confidence"] in {CONFIDENCE_LOW, CONFIDENCE_MEDIUM, CONFIDENCE_HIGH}
    assert rows["111"]["sales_amount_30d"] == pytest.approx(200.0)
    assert rows["111"]["velocity_source"] == "snapshot_delta"

    assert rows["999"]["units_sold_7d"] is None
    assert rows["999"]["units_sold_30d"] is None
    assert rows["999"]["velocity_confidence"] == CONFIDENCE_NONE


def test_empty_velocity_clears_stale_values(tmp_path):
    """A run that derives nothing must overwrite yesterday's numbers, not keep them.

    Otherwise stale velocity silently ages into the UI as if it were current.
    """
    sales = _sales_stub(tmp_path / "sales.parquet", ["111"])
    products = _products_stub(tmp_path / "products.parquet", {"111": 10.0})

    snaps = _snapshots(tmp_path / "snaps", [
        (BASE, {"111": 100}),
        (BASE + timedelta(days=2), {"111": 80}),
    ])
    apply_to_sales_table(compute_velocity(build_intervals(snaps)), sales_path=sales, products_path=products)
    assert pq.read_table(sales).to_pylist()[0]["units_sold_7d"] == 20

    # A later run with no derivable velocity must reset the row.
    apply_to_sales_table({}, sales_path=sales, products_path=products)
    row = pq.read_table(sales).to_pylist()[0]

    assert row["units_sold_7d"] is None
    assert row["units_sold_30d"] is None
    assert row["velocity_confidence"] == CONFIDENCE_NONE


def test_apply_is_idempotent(tmp_path):
    """The velocity build may run twice in a morning; the second run must not corrupt the table."""
    snaps = _snapshots(tmp_path / "snaps", [
        (BASE, {"111": 100}),
        (BASE + timedelta(days=2), {"111": 80}),
    ])
    velocity = compute_velocity(build_intervals(snaps))
    sales = _sales_stub(tmp_path / "sales.parquet", ["111"])
    products = _products_stub(tmp_path / "products.parquet", {"111": 10.0})

    apply_to_sales_table(velocity, sales_path=sales, products_path=products)
    first = pq.read_table(sales).to_pylist()
    apply_to_sales_table(velocity, sales_path=sales, products_path=products)
    second = pq.read_table(sales).to_pylist()

    assert first == second


def test_rearchiving_the_same_import_is_not_an_interval(tmp_path):
    """Re-running the pipeline without a new export must not manufacture history.

    Archiving happens every run, so re-running two months later with no new CSV
    produces a second snapshot of the SAME import. Counting that as a 60-day interval
    of "zero sales" would make every product look dead AND let confidence grow purely
    from re-runs — confidently wrong, which is the worst outcome available.
    """
    def snap(ts, stock, source, imported_at):
        path = tmp_path / ts.strftime("%Y%m%dT%H%M%SZ")
        path.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pylist(
            [{"barcode": b, "current_stock": q, "_source_file": source, "_imported_at": imported_at}
             for b, q in stock.items()],
            schema=pa.schema([("barcode", pa.string()), ("current_stock", pa.int64()),
                              ("_source_file", pa.string()), ("_imported_at", pa.string())]),
        )
        pq.write_table(table, path / "inventory.parquet")
        pq.write_table(table, path / "products.parquet")

    snap(BASE, {"111": 100}, "export.csv", "2026-08-01T09:00:00")
    snap(BASE + timedelta(days=60), {"111": 100}, "export.csv", "2026-08-01T09:00:00")

    assert build_intervals(list_usable_snapshots(tmp_path)) == []

    # A genuinely new export against the same anchor DOES count.
    snap(BASE + timedelta(days=61), {"111": 70}, "export2.csv", "2026-10-01T09:00:00")
    intervals = build_intervals(list_usable_snapshots(tmp_path))

    assert len(intervals) == 1
    assert intervals[0]["movement"]["111"]["sold"] == pytest.approx(30.0)
    assert intervals[0]["elapsed_days"] == pytest.approx(61.0)


def test_window_sums_are_observed_not_extrapolated(tmp_path):
    """units_sold_30d is an OBSERVED SUM, never extrapolated to a full 30 days.

    With 4 days of history showing 20 units, units_sold_30d is 20 — not 150. We do not
    invent data we never observed. The corollary matters just as much: consumers must
    use units_per_day, because 20/30 would read as 0.67/day when the real rate is 5/day.
    """
    snaps = _snapshots(tmp_path, [
        (BASE, {"111": 100}),
        (BASE + timedelta(days=4), {"111": 80}),
    ])
    entry = compute_velocity(build_intervals(snaps))["111"]

    assert entry["units_sold_30d"] == 20            # observed, not 20/4*30
    assert entry["observed_days"] == pytest.approx(4.0)
    assert entry["units_per_day"] == pytest.approx(5.0)
    # The trap this guards against:
    assert entry["units_sold_30d"] / 30 != pytest.approx(entry["units_per_day"])


def test_negative_stock_still_produces_sane_movement(tmp_path):
    """625 real rows have negative stock (a POS artifact). It must not explode."""
    snaps = _snapshots(tmp_path, [
        (BASE, {"111": 5}),
        (BASE + timedelta(days=1), {"111": -3}),
    ])
    entry = compute_velocity(build_intervals(snaps))["111"]

    assert entry["units_sold_7d"] == 8
    assert entry["velocity_confidence"] in {CONFIDENCE_LOW, CONFIDENCE_MEDIUM, CONFIDENCE_HIGH}
