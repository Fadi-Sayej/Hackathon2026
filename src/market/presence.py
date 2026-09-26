"""
presence.py — turn dated market snapshots into a presence time series (T4 / #49).

Reads `data/external/snapshots/<YYYY-MM-DD>/price_transparency/` and answers one
question per (product, store, day): **was it listed that day?**

That series is the raw material for everything in #49. It is deliberately thin —
presence only, no prices, no modelling — because every later step reasons about
appearance and disappearance, and mixing concerns here makes the statistics
harder to check.

TWO RULES THAT MATTER MORE THAN THE CODE
----------------------------------------
1. **A day with no snapshot is not a day of absence.** If the collector failed,
   every product looks delisted. Days whose manifest is missing or `failed` are
   excluded entirely rather than read as empty — this is exactly why
   `_manifest.json` exists (#46 Step 3).

2. **Presence in the price file is not presence on the shelf.** The mandated file
   is what the chain *says* it stocks; items linger there for weeks after selling
   out. This module reports listing, never availability. Anything that needs
   availability has to combine it with the delivery catalog, which is the whole
   premise of #49.

   The one exception is the delivery catalog's own flag. A store there mostly drops a
   sold-out item, but occasionally lists it marked not orderable
   (`is_online_available` false). Those pairs are recorded in `unavailable`, beside
   `listings` and not instead of it, so every existing reader still sees them listed
   and only a reader that asks for availability (ADR-031) reads them as absent.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import polars as pl

from src.common.paths import EXTERNAL_SNAPSHOTS_ROOT

PRICE_TRANSPARENCY = "price_transparency"
DELIVERY_CATALOG = "delivery_catalog"

# Manifest statuses whose day may be trusted as a real observation of the market.
USABLE_STATUSES = {"ok", "partial"}

# A day covering less than this share of the median branch count is treated as a
# partial collection, not as a market in which branches vanished.
#
# This exists because a partial run SUCCEEDS. On 11 Aug one run reached 31 of 156
# branches and was recorded `ok` — the manifest checks that files arrived, not
# that they are complete. Had that been the only run, 125 branches would have
# disappeared on one morning and every product in them would have read as a
# synchronised, chain-wide delisting. That is the single worst failure this
# series can produce, and it is indistinguishable from a real event without a
# coverage check.
#
# Half is deliberately loose. A chain does not shed half its branches overnight,
# so a day below this is far more likely to be a truncated download than news.
MIN_BRANCH_COVERAGE_RATIO = 0.5

# Below this many days a median is not robust enough to judge against, so the
# guard stays out of the way rather than skipping on two points of evidence.
MIN_DAYS_FOR_COVERAGE_GUARD = 3


@dataclass
class PresenceSeries:
    """Which (product, store) pairs were listed on each usable day."""

    days: List[date] = field(default_factory=list)
    # day -> set of (barcode, store_id)
    listings: Dict[date, Set[Tuple[str, str]]] = field(default_factory=dict)
    # day -> the listed pairs the source marked NOT orderable (ADR-031). A subset of that
    # day's listings. A missing or null flag is not "unavailable": unknown is not absent.
    unavailable: Dict[date, Set[Tuple[str, str]]] = field(default_factory=dict)
    # day -> why it was skipped, for days that exist but are not usable
    skipped: Dict[date, str] = field(default_factory=dict)
    product_names: Dict[str, str] = field(default_factory=dict)

    def stores_carrying(self, barcode: str, day: date) -> Set[str]:
        return {s for (b, s) in self.listings.get(day, ()) if b == barcode}

    def all_stores(self) -> Set[str]:
        return {s for day in self.listings.values() for (_b, s) in day}

    def all_barcodes(self) -> Set[str]:
        return {b for day in self.listings.values() for (b, _s) in day}

    def consecutive_pairs(self) -> Iterable[Tuple[date, date]]:
        """Adjacent USABLE days.

        Deliberately not "calendar-adjacent": if 12 August is missing, the pair is
        (11 Aug, 13 Aug). Treating a gap as adjacency would attribute two days of
        market movement to one, and treating it as absence would invent a mass
        delisting.
        """
        for earlier, later in zip(self.days, self.days[1:]):
            yield earlier, later


def _parse_day(name: str) -> Optional[date]:
    try:
        return datetime.strptime(name, "%Y-%m-%d").date()
    except ValueError:
        return None


def _manifest_status(day_dir: Path) -> Optional[str]:
    manifest = day_dir / "_manifest.json"
    if not manifest.exists():
        return None
    try:
        return json.loads(manifest.read_text(encoding="utf-8")).get("status")
    except (ValueError, OSError):
        return None


def _read_listings(source_dir: Path) -> Tuple[Set[Tuple[str, str]], Dict[str, str], Set[Tuple[str, str]]]:
    """(barcode, store_id) pairs, barcode -> name, and the pairs marked not orderable,
    from one day's silver files."""
    pairs: Set[Tuple[str, str]] = set()
    names: Dict[str, str] = {}
    not_orderable: Set[Tuple[str, str]] = set()
    orderable: Set[Tuple[str, str]] = set()
    if not source_dir.exists():
        return pairs, names, not_orderable

    for path in sorted(source_dir.rglob("*.parquet")):
        # Bronze is the raw shape; silver is normalised. Only read silver so the
        # same rows are not counted twice.
        if "silver" not in path.name:
            continue
        try:
            frame = pl.read_parquet(path)
        except Exception:
            continue
        if "barcode" not in frame.columns or "store_id" not in frame.columns:
            continue
        cols = (["barcode", "store_id"] + (["product_name"] if "product_name" in frame.columns else [])
                + (["is_online_available"] if "is_online_available" in frame.columns else []))
        for row in frame.select(cols).iter_rows(named=True):
            barcode = str(row.get("barcode") or "").strip().lstrip("0")
            store = str(row.get("store_id") or "").strip()
            if not barcode or not store:
                continue
            pairs.add((barcode, store))
            flag = row.get("is_online_available")
            if flag is False:
                not_orderable.add((barcode, store))
            elif flag is True:
                orderable.add((barcode, store))
            name = row.get("product_name")
            if name and barcode not in names:
                names[barcode] = str(name)
    # A day's files can list one pair twice. Absent only if no line said it was orderable.
    return pairs, names, not_orderable - orderable


# One day's reading, kept while its files are unchanged. The engine now reads the delivery
# catalogue on every run (ADR-031), and a test session runs the engine a hundred times over
# the same committed snapshots: re-reading ~400 parquet files each time cost the suite 90
# seconds. The key is every file's name, size and nanosecond mtime, so a rewritten file is
# read again; callers get copies, so nothing they do reaches the cache.
_DAY_CACHE: Dict[Tuple[str, str], Tuple[tuple, tuple]] = {}


def _signature(day_dir: Path, source_id: str) -> tuple:
    files = [day_dir / "_manifest.json"]
    source = day_dir / source_id
    if source.exists():
        files += sorted(source.rglob("*.parquet"))
    out = []
    for path in files:
        try:
            st = path.stat()
        except OSError:
            continue
        out.append((str(path), st.st_size, st.st_mtime_ns))
    return tuple(out)


def _read_day(day_dir: Path, source_id: str):
    """(manifest status, pairs, names, not orderable) for one day directory, cached."""
    key = (str(day_dir), source_id)
    signature = _signature(day_dir, source_id)
    cached = _DAY_CACHE.get(key)
    if cached is None or cached[0] != signature:
        status = _manifest_status(day_dir)
        read = _read_listings(day_dir / source_id) if status in USABLE_STATUSES else (set(), {}, set())
        cached = (signature, (status,) + read)
        _DAY_CACHE[key] = cached
    status, pairs, names, not_orderable = cached[1]
    return status, set(pairs), dict(names), set(not_orderable)


def load_presence(
    root: Optional[Path] = None,
    source_id: str = PRICE_TRANSPARENCY,
) -> PresenceSeries:
    """Build the presence series from every usable snapshot day."""
    root = root or EXTERNAL_SNAPSHOTS_ROOT
    series = PresenceSeries()
    if not root.exists():
        return series

    for day_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        day = _parse_day(day_dir.name)
        if day is None:
            continue

        status, pairs, names, not_orderable = _read_day(day_dir, source_id)
        if status is None:
            # No manifest means we cannot tell a real absence from a failed
            # scrape, so the day is unusable regardless of what files exist.
            series.skipped[day] = "no manifest"
            continue
        if status not in USABLE_STATUSES:
            series.skipped[day] = f"manifest status {status!r}"
            continue

        if not pairs:
            series.skipped[day] = "no listings in snapshot"
            continue

        series.days.append(day)
        series.listings[day] = pairs
        series.unavailable[day] = not_orderable
        for barcode, name in names.items():
            series.product_names.setdefault(barcode, name)

    series.days.sort()
    _drop_undercovered_days(series)
    return series


def _drop_undercovered_days(
    series: PresenceSeries,
    ratio: float = MIN_BRANCH_COVERAGE_RATIO,
    min_days: int = MIN_DAYS_FOR_COVERAGE_GUARD,
) -> None:
    """Remove days whose branch coverage is far below the run of the series.

    Mutates `series` in place and records the reason in `skipped`, so a dropped
    day is reported rather than silently missing — the same contract as a failed
    manifest.
    """
    if len(series.days) < min_days:
        return

    counts = {day: len({store for (_b, store) in series.listings[day]}) for day in series.days}
    floor = statistics.median(counts.values()) * ratio

    for day in list(series.days):
        if counts[day] < floor:
            series.skipped[day] = (
                "partial collection: %d branches, below %.0f%% of the %d-branch median"
                % (counts[day], ratio * 100, int(statistics.median(counts.values())))
            )
            series.days.remove(day)
            del series.listings[day]
            series.unavailable.pop(day, None)
