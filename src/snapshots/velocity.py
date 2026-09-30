"""
velocity.py — derive sales velocity from POS stock snapshots (task A-1).

The YomYom POS export is an inventory snapshot: it has current stock, but no sales
history at all. Every velocity column in yomyom_sales.parquet is null, which makes
100% of products classify as "Slow moving" downstream.

This module reconstructs velocity from what we *do* have: how stock changed between
two point-in-time snapshots. If a product had 40 units on Monday and 33 on Thursday,
roughly 7 units moved over 3 days.

Three things make that harder than it sounds, and all three are handled here:

  1. IRREGULAR INTERVALS. The manager sends the CSV when they remember, not daily.
     Every delta is divided by the ACTUAL elapsed time. Treating a 6-day gap as one
     day would overstate velocity 6x — the single most likely way this engine ships
     confidently wrong numbers.

  2. RESTOCKS. A stock INCREASE is a delivery, not negative sales. Increases are
     clamped to zero and recorded separately as restock events. Note the asymmetry
     this creates: a delivery that lands mid-interval hides the sales before it, so
     we systematically UNDERSTATE velocity. We under-promise rather than over-promise.

  3. WHAT WE CANNOT SEE. Between two snapshots stock may fall, be restocked, and fall
     again — we only see the endpoints. The longer the gap, the more this hides, so
     gap length feeds directly into the confidence rating.

The output is a PROXY, not measured sales. Shrinkage, damage, returns and manual
corrections all look identical to a sale from here. `velocity_confidence` exists so
the UI can be honest about that, and must never be dropped on the way to the user.

---------------------------------------------------------------------------
READ THIS BEFORE CONSUMING units_sold_7d / units_sold_30d
---------------------------------------------------------------------------
These are OBSERVED SUMS over however much history exists — not full-window totals.
Early in the pilot, `units_sold_30d` may cover only 4 days.

    DO NOT compute a daily rate as `units_sold_30d / 30`.

Doing that understates velocity by however much history is missing (4 days of data
divided by 30 is a 7x understatement, which reads as "dead stock" for a product
selling several units a day). Use `units_per_day`, which is already normalised by
`observed_days`, and check `velocity_confidence` before showing anything at all.

The alternative — extrapolating a 4-day rate out to a 30-day total — would invent
data we never observed, so we deliberately do not do it. The honest number is a
small one plus the context needed to interpret it.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

from src.common.paths import SILVER_POS_ROOT, SNAPSHOTS_ROOT
from src.common.store import PRODUCTS_TABLE

# Two snapshots closer together than this are the same export imported twice, not a
# real interval. Dividing a delta by a two-hour gap produces a wild daily rate.
MIN_INTERVAL_HOURS = 12.0

# A gap longer than this hides too many intra-interval restocks to trust precisely.
SUSPECT_GAP_DAYS = 10.0
LOOSE_GAP_DAYS = 3.0

CONFIDENCE_NONE = "none"
CONFIDENCE_LOW = "low"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_HIGH = "high"

_CONFIDENCE_RANK = {
    CONFIDENCE_NONE: 0,
    CONFIDENCE_LOW: 1,
    CONFIDENCE_MEDIUM: 2,
    CONFIDENCE_HIGH: 3,
}


def _parse_snapshot_ts(name: str) -> Optional[datetime]:
    """Snapshot dirs are named like 20260606T153300Z."""
    try:
        return datetime.strptime(name, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _read_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return pq.read_table(path).to_pylist()


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def load_snapshot_stock(snapshot_dir: Path) -> Dict[str, float]:
    """barcode -> current_stock for one snapshot.

    Stock lives in inventory.parquet; products.parquet has no stock column. Falls
    back to products.parquet in case a future snapshot carries stock there.
    """
    stock: Dict[str, float] = {}

    for row in _read_rows(snapshot_dir / "inventory.parquet"):
        barcode = str(row.get("barcode") or "").strip()
        if not barcode:
            continue
        value = _num(row.get("current_stock"))
        if value is not None:
            stock[barcode] = value

    if not stock:
        for row in _read_rows(snapshot_dir / "products.parquet"):
            barcode = str(row.get("barcode") or "").strip()
            if not barcode:
                continue
            value = _num(row.get("current_stock"))
            if value is not None:
                stock[barcode] = value

    return stock


def snapshot_import_id(snapshot_dir: Path) -> Optional[str]:
    """Which import produced this snapshot, as `_source_file@_imported_at`.

    Archiving happens on every pipeline run, so re-running without a new export
    produces a second snapshot of the SAME import. Those two are not two observations
    of the shop — nothing was measured in between. Treating them as an interval would
    manufacture a fake stretch of "zero sales" and, worse, let confidence grow over
    time purely from re-runs. That is the confidently-wrong failure mode this whole
    module exists to avoid.
    """
    for name in ("products.parquet", "inventory.parquet"):
        path = snapshot_dir / name
        if not path.exists():
            continue
        try:
            schema = pq.read_schema(path)
            wanted = [c for c in ("_source_file", "_imported_at") if c in schema.names]
            if not wanted:
                continue
            rows = pq.read_table(path, columns=wanted).to_pylist()
        except Exception:  # unreadable/legacy snapshot — fall through to meta.json
            continue
        if rows:
            return "%s@%s" % (rows[0].get("_source_file"), rows[0].get("_imported_at"))

    meta = snapshot_dir / "meta.json"
    if meta.exists():
        try:
            value = json.loads(meta.read_text(encoding="utf-8")).get("imported_at")
        except (ValueError, OSError):
            return None
        # None means "provenance unknown". It must NOT collapse to the string "None",
        # or every provenance-less snapshot would look like the same import and every
        # interval would be silently discarded.
        return str(value) if value is not None else None
    return None


def list_usable_snapshots(root: Optional[Path] = None) -> List[Tuple[datetime, Path]]:
    """Timestamped snapshot dirs that actually contain stock data, oldest first.

    Snapshot parquets are gitignored, so a freshly cloned repo may have snapshot
    directories holding nothing but meta.json. Those are skipped rather than
    treated as empty inventories, which would read as "everything sold out".
    """
    root = root or SNAPSHOTS_ROOT
    if not root.exists():
        return []

    found: List[Tuple[datetime, Path]] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        ts = _parse_snapshot_ts(path.name)
        if ts is None:
            continue
        if not (path / "inventory.parquet").exists() and not (path / "products.parquet").exists():
            continue
        found.append((ts, path))

    found.sort(key=lambda pair: pair[0])
    return found


def build_intervals(
    snapshots: List[Tuple[datetime, Path]],
    min_interval_hours: float = MIN_INTERVAL_HOURS,
) -> List[Dict[str, Any]]:
    """Consecutive snapshot pairs, with per-barcode movement.

    Pairs closer together than `min_interval_hours` are skipped as duplicate imports.
    When a pair is skipped the earlier snapshot is kept as the anchor, so the next
    real snapshot still measures against it rather than losing the interval entirely.
    """
    intervals: List[Dict[str, Any]] = []
    if len(snapshots) < 2:
        return intervals

    prev_ts, prev_dir = snapshots[0]
    prev_stock = load_snapshot_stock(prev_dir)
    prev_import = snapshot_import_id(prev_dir)

    for curr_ts, curr_dir in snapshots[1:]:
        elapsed_days = (curr_ts - prev_ts).total_seconds() / 86400.0
        if elapsed_days * 24.0 < min_interval_hours:
            # Same export imported twice within hours — do not advance the anchor.
            continue

        curr_import = snapshot_import_id(curr_dir)
        if curr_import is not None and curr_import == prev_import:
            # Re-archive of the same import. No new observation of the shop happened,
            # so this is not an interval however many days separate the two files.
            continue

        curr_stock = load_snapshot_stock(curr_dir)
        movement: Dict[str, Dict[str, float]] = {}

        for barcode, curr_value in curr_stock.items():
            prev_value = prev_stock.get(barcode)
            if prev_value is None:
                continue  # new product, no baseline to measure against
            delta = prev_value - curr_value
            movement[barcode] = {
                "sold": delta if delta > 0 else 0.0,
                "restocked": -delta if delta < 0 else 0.0,
            }

        intervals.append(
            {
                "start": prev_ts,
                "end": curr_ts,
                "elapsed_days": elapsed_days,
                "movement": movement,
            }
        )

        prev_ts, prev_dir, prev_stock, prev_import = curr_ts, curr_dir, curr_stock, curr_import

    return intervals


def _overlap_days(
    interval_start: datetime,
    interval_end: datetime,
    window_start: datetime,
    window_end: datetime,
) -> float:
    latest_start = max(interval_start, window_start)
    earliest_end = min(interval_end, window_end)
    seconds = (earliest_end - latest_start).total_seconds()
    return max(0.0, seconds / 86400.0)


def _rate_confidence(covered_days: float, max_gap_days: float, interval_count: int) -> str:
    """How much do we trust this product's velocity?

    Driven by how much history we have AND how coarse it is. Thirty days made of one
    30-day gap is not the same evidence as thirty days of daily snapshots, and must
    not be presented as though it were.
    """
    if interval_count == 0 or covered_days <= 0:
        return CONFIDENCE_NONE

    if covered_days >= 30:
        level = CONFIDENCE_HIGH
    elif covered_days >= 7:
        level = CONFIDENCE_MEDIUM
    else:
        level = CONFIDENCE_LOW

    # Coarse sampling caps the ceiling regardless of total span.
    if max_gap_days > SUSPECT_GAP_DAYS:
        cap = CONFIDENCE_LOW
    elif max_gap_days > LOOSE_GAP_DAYS:
        cap = CONFIDENCE_MEDIUM
    else:
        cap = CONFIDENCE_HIGH

    return level if _CONFIDENCE_RANK[level] <= _CONFIDENCE_RANK[cap] else cap


def compute_velocity(
    intervals: List[Dict[str, Any]],
    as_of: Optional[datetime] = None,
    windows: Tuple[int, ...] = (7, 30),
) -> Dict[str, Dict[str, Any]]:
    """barcode -> velocity metrics, from the interval list.

    Units in a window are PRORATED by how much of each interval falls inside it, so
    a 10-day interval overlapping the last 7 days contributes only its overlapping
    share. Summing whole intervals would let old movement leak into a short window.
    """
    if not intervals:
        return {}

    as_of = as_of or max(item["end"] for item in intervals)
    barcodes = {bc for item in intervals for bc in item["movement"]}
    results: Dict[str, Dict[str, Any]] = {}

    for barcode in barcodes:
        entry: Dict[str, Any] = {}
        total_sold = 0.0
        total_restocked = 0.0
        covered_days = 0.0
        max_gap_days = 0.0
        interval_count = 0
        last_movement: Optional[datetime] = None

        for item in intervals:
            move = item["movement"].get(barcode)
            if move is None:
                continue
            interval_count += 1
            covered_days += item["elapsed_days"]
            max_gap_days = max(max_gap_days, item["elapsed_days"])
            total_sold += move["sold"]
            total_restocked += move["restocked"]
            if move["sold"] > 0:
                last_movement = item["end"] if last_movement is None else max(last_movement, item["end"])

        for window in windows:
            window_start = as_of - timedelta(days=window)
            units = 0.0
            for item in intervals:
                move = item["movement"].get(barcode)
                if move is None or move["sold"] <= 0:
                    continue
                overlap = _overlap_days(item["start"], item["end"], window_start, as_of)
                if overlap <= 0:
                    continue
                # Movement is assumed spread evenly across its interval.
                units += move["sold"] * (overlap / item["elapsed_days"])
            entry["units_sold_%dd" % window] = int(round(units))

        entry["units_per_day"] = round(total_sold / covered_days, 4) if covered_days > 0 else 0.0
        entry["observed_days"] = round(covered_days, 2)
        entry["max_gap_days"] = round(max_gap_days, 2)
        entry["interval_count"] = interval_count
        entry["total_restocked"] = int(round(total_restocked))
        entry["last_sale_date"] = last_movement.date().isoformat() if last_movement else None
        entry["velocity_confidence"] = _rate_confidence(covered_days, max_gap_days, interval_count)
        results[barcode] = entry

    return results


def apply_to_sales_table(
    velocity: Dict[str, Dict[str, Any]],
    sales_path: Optional[Path] = None,
    products_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Write derived velocity into yomyom_sales.parquet.

    Products with no derived velocity keep null units and get confidence 'none'.
    A null unit count and a zero unit count are DIFFERENT FACTS — "we have no history
    for this product" is not "this product did not sell" — and the distinction has to
    survive all the way to the UI or the whole thing becomes dishonest.
    """
    sales_path = sales_path or (SILVER_POS_ROOT / "yomyom_sales.parquet")
    products_path = products_path or (SILVER_POS_ROOT / PRODUCTS_TABLE)

    if not sales_path.exists():
        raise FileNotFoundError("sales table not found: %s" % sales_path)

    rows = _read_rows(sales_path)
    prices: Dict[str, float] = {}
    for row in _read_rows(products_path):
        barcode = str(row.get("barcode") or "").strip()
        price = _num(row.get("selling_price"))
        if barcode and price is not None:
            prices[barcode] = price

    matched = 0
    for row in rows:
        barcode = str(row.get("barcode") or "").strip()
        entry = velocity.get(barcode) if barcode else None

        if entry is None:
            row["units_sold_7d"] = None
            row["units_sold_30d"] = None
            row["sales_amount_30d"] = None
            row["last_sale_date"] = None
            row["units_per_day"] = None
            row["observed_days"] = None
            row["max_gap_days"] = None
            row["velocity_confidence"] = CONFIDENCE_NONE
            row["velocity_source"] = SNAPSHOT_SOURCE
            continue

        matched += 1
        units_30 = entry.get("units_sold_30d")
        row["units_sold_7d"] = entry.get("units_sold_7d")
        row["units_sold_30d"] = units_30
        row["last_sale_date"] = entry.get("last_sale_date")
        row["units_per_day"] = entry.get("units_per_day")
        row["observed_days"] = entry.get("observed_days")
        row["max_gap_days"] = entry.get("max_gap_days")
        row["velocity_confidence"] = entry.get("velocity_confidence")
        row["velocity_source"] = SNAPSHOT_SOURCE

        price = prices.get(barcode)
        row["sales_amount_30d"] = round(units_30 * price, 2) if (price is not None and units_30) else None

    schema = pa.schema(
        [
            ("barcode", pa.string()),
            ("product_name", pa.string()),
            ("category", pa.string()),
            ("units_sold_7d", pa.int64()),
            ("units_sold_30d", pa.int64()),
            ("sales_amount_30d", pa.float64()),
            ("last_sale_date", pa.string()),
            ("units_per_day", pa.float64()),
            ("observed_days", pa.float64()),
            ("max_gap_days", pa.float64()),
            ("velocity_confidence", pa.string()),
            ("velocity_source", pa.string()),
            ("_imported_at", pa.string()),
            ("_source_file", pa.string()),
            ("_source_kind", pa.string()),
        ]
    )
    ordered = [{name: row.get(name) for name in schema.names} for row in rows]
    pq.write_table(pa.Table.from_pylist(ordered, schema=schema), sales_path)

    return {"rows": len(rows), "matched": matched, "unmatched": len(rows) - matched}


SNAPSHOT_SOURCE = "snapshot_delta"
POS_EXPORT_SOURCE = "pos_export"


def has_real_sales(sales_path: Optional[Path] = None) -> bool:
    """Does the sales table already hold sales the POS actually reported?

    The snapshot proxy is a fallback for having no sales data. Real sales beat it
    on every axis, so the proxy must never overwrite them — and it would: this
    module rewrites the whole table, so importing YomYom's sales report and then
    running the daily pipeline would replace measured sales with nulls, silently,
    the same day we finally got the data. (A-3.)

    Detection: every row this module writes is stamped with velocity_source. Rows
    carrying units without that stamp therefore came from the importer, i.e. from
    the POS export itself.
    """
    sales_path = sales_path or (SILVER_POS_ROOT / "yomyom_sales.parquet")
    if not sales_path.exists():
        return False

    try:
        schema = pq.read_schema(sales_path)
    except Exception:
        return False
    if "units_sold_30d" not in schema.names:
        return False

    columns = ["units_sold_30d"]
    has_source = "velocity_source" in schema.names
    if has_source:
        columns.append("velocity_source")

    try:
        rows = pq.read_table(sales_path, columns=columns).to_pylist()
    except Exception:
        return False

    for row in rows:
        if row.get("units_sold_30d") is None:
            continue
        source = row.get("velocity_source") if has_source else None
        if source != SNAPSHOT_SOURCE:
            return True
    return False


def build_velocity(as_of: Optional[datetime] = None, write: bool = True) -> Dict[str, Any]:
    """Full pipeline: snapshots -> intervals -> velocity -> sales table."""
    if has_real_sales():
        return {
            "snapshots_found": len(list_usable_snapshots()),
            "snapshot_range": None,
            "usable_intervals": 0,
            "products_with_velocity": 0,
            "confidence_breakdown": {},
            "written": False,
            "skipped_reason": "real_sales_present",
            "warnings": [
                "The sales table already holds sales reported by the POS. The snapshot "
                "proxy is a substitute for exactly that, so it was NOT run — overwriting "
                "measured sales with an estimate would be a straight downgrade."
            ],
        }

    snapshots = list_usable_snapshots()
    result: Dict[str, Any] = {
        "snapshots_found": len(snapshots),
        "snapshot_range": None,
        "usable_intervals": 0,
        "products_with_velocity": 0,
        "confidence_breakdown": {},
        "written": False,
        "warnings": [],
    }

    def _reset_if_writing() -> None:
        """Clear any velocity a previous run left behind.

        Without this, a run that derives nothing leaves yesterday's numbers in place
        and they silently age into the UI as if current. Absence of evidence has to
        overwrite the previous evidence.
        """
        if write:
            result["write"] = apply_to_sales_table({})
            result["written"] = True

    if len(snapshots) < 2:
        result["warnings"].append(
            "Need at least 2 snapshots with stock data to derive velocity; found %d. "
            "Velocity stays null and every product reports confidence 'none'." % len(snapshots)
        )
        _reset_if_writing()
        return result

    result["snapshot_range"] = [snapshots[0][0].isoformat(), snapshots[-1][0].isoformat()]

    intervals = build_intervals(snapshots)
    result["usable_intervals"] = len(intervals)
    if not intervals:
        import_ids = {snapshot_import_id(path) for _, path in snapshots}
        if len(import_ids) == 1:
            result["warnings"].append(
                "All %d snapshots come from the SAME import — no new POS export has been "
                "loaded since. Velocity needs a genuinely new export, not another pipeline "
                "run." % len(snapshots)
            )
        else:
            result["warnings"].append(
                "All snapshot pairs were closer together than %.0fh and treated as duplicate "
                "imports. Velocity needs snapshots taken on different days." % MIN_INTERVAL_HOURS
            )
        _reset_if_writing()
        return result

    velocity = compute_velocity(intervals, as_of=as_of)
    result["products_with_velocity"] = len(velocity)

    breakdown: Dict[str, int] = {}
    for entry in velocity.values():
        level = entry["velocity_confidence"]
        breakdown[level] = breakdown.get(level, 0) + 1
    result["confidence_breakdown"] = breakdown

    max_gap = max((item["elapsed_days"] for item in intervals), default=0.0)
    if max_gap > SUSPECT_GAP_DAYS:
        result["warnings"].append(
            "Largest snapshot gap is %.1f days. Long gaps hide restocks, so velocity is "
            "understated and confidence is capped at 'low'." % max_gap
        )

    total_span = (intervals[-1]["end"] - intervals[0]["start"]).total_seconds() / 86400.0
    result["observed_span_days"] = round(total_span, 2)
    if total_span < 30:
        result["warnings"].append(
            "Only %.1f days of history: units_sold_30d is an OBSERVED SUM over that span, "
            "not a 30-day total. Consumers must use units_per_day — dividing units_sold_30d "
            "by 30 understates velocity by ~%.1fx." % (total_span, 30.0 / max(total_span, 0.1))
        )

    if write:
        result["write"] = apply_to_sales_table(velocity)
        result["written"] = True

    return result


def format_report(result: Dict[str, Any]) -> str:
    lines = [
        "Velocity from snapshot deltas",
        "  snapshots found      : %s" % result["snapshots_found"],
        "  usable intervals     : %s" % result["usable_intervals"],
        "  products w/ velocity : %s" % result["products_with_velocity"],
    ]
    if result.get("snapshot_range"):
        lines.append("  range                : %s -> %s" % tuple(result["snapshot_range"]))
    if result.get("confidence_breakdown"):
        parts = ", ".join("%s=%d" % kv for kv in sorted(result["confidence_breakdown"].items()))
        lines.append("  confidence           : %s" % parts)
    if result.get("write"):
        w = result["write"]
        lines.append("  sales table          : %d rows, %d matched, %d unmatched" % (w["rows"], w["matched"], w["unmatched"]))
    for warning in result.get("warnings", []):
        lines.append("  WARNING: %s" % warning)
    return "\n".join(lines)


__all__ = [
    "build_velocity",
    "build_intervals",
    "compute_velocity",
    "apply_to_sales_table",
    "list_usable_snapshots",
    "load_snapshot_stock",
    "format_report",
]
