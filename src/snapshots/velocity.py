"""
velocity.py — derive sales velocity from POS stock snapshots (task A-1).

What is still used (2026-10-06): the snapshot helpers the POS importer, the import-quality
check and the restock reconciliation read (`list_usable_snapshots`, `snapshot_import_id`,
`build_intervals`, `load_snapshot_stock`), and the confidence names censored_demand.py uses.
The writer that put a derived rate into `yomyom_sales.parquet`, with
`scripts/build_velocity_from_snapshots.py` and `npm run data:velocity`, was removed. Task 0.6
deleted that table because its rate was synthesised (CLAUDE.md rules 5 and 13), and nothing
may recreate it. `compute_velocity` stays as the proxy's tested arithmetic; nothing ships it.

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



__all__ = [
    "build_intervals",
    "compute_velocity",
    "list_usable_snapshots",
    "load_snapshot_stock",
    "snapshot_import_id",
]
