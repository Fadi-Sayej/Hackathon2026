"""
T1 / #46 + T4 / #49 — the presence series, and the coverage guard on top of it.

The guard exists because of a real incident on 11 Aug 2026: one collection run
reached 31 of 156 branches and was recorded `ok`, because the manifest checks
that files arrived, not that they are complete. Had that been the only run of
the day, 125 branches would have vanished on one morning, and every product in
them would have read as a synchronised chain-wide delisting — the single most
damaging output this system can produce, and indistinguishable from a real event
without a coverage check.

So the tests below assert the consequence, not just the bookkeeping: a truncated
day must not generate delisting warnings.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.market.concentration import STATE_DELISTING, detect_drops  # noqa: E402
from src.market.presence import (  # noqa: E402
    PresenceSeries,
    _drop_undercovered_days,
    load_presence,
)

DAY0 = date(2026, 8, 1)


def series_with(branch_counts, products_per_branch=4):
    """A series where day i covers `branch_counts[i]` branches, all carrying the
    same products — so any difference in output comes from coverage alone."""
    s = PresenceSeries()
    for offset, branches in enumerate(branch_counts):
        day = DAY0 + timedelta(days=offset)
        s.days.append(day)
        s.listings[day] = {
            (f"p{p}", str(b))
            for b in range(branches)
            for p in range(products_per_branch)
        }
    return s


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------

def test_a_truncated_day_is_dropped_and_the_reason_recorded():
    s = series_with([156, 31, 156, 156])          # day 2 is the partial run
    _drop_undercovered_days(s)

    assert DAY0 + timedelta(days=1) not in s.days
    assert DAY0 + timedelta(days=1) in s.skipped
    assert "partial collection" in s.skipped[DAY0 + timedelta(days=1)]
    assert len(s.days) == 3


def test_a_full_series_is_left_alone():
    s = series_with([156, 154, 156, 155])         # ordinary branch-level noise
    _drop_undercovered_days(s)
    assert len(s.days) == 4
    assert s.skipped == {}


def test_the_guard_stays_out_of_the_way_below_three_days():
    """Two points is not a series. Skipping on that evidence would throw away
    half the history the moment collection starts."""
    s = series_with([156, 31])
    _drop_undercovered_days(s)
    assert len(s.days) == 2


def test_a_uniformly_small_series_is_not_punished_for_being_small():
    """A three-branch chain is not a partial collection of a large one."""
    s = series_with([3, 3, 3])
    _drop_undercovered_days(s)
    assert len(s.days) == 3


def test_the_median_resists_a_single_huge_day():
    """Mean would let one outlier drag the floor up and evict good days."""
    s = series_with([156, 156, 156, 5000])
    _drop_undercovered_days(s)
    assert len(s.days) == 4          # nothing dropped; 156 > 0.5 * median(156)


# ---------------------------------------------------------------------------
# The consequence — what the guard is actually for
# ---------------------------------------------------------------------------

def test_a_truncated_day_manufactures_drops_across_every_missing_branch():
    """The 11 Aug incident, run forward.

    Worth being precise about what survives without the guard. Step 1's
    persistence rule already catches the worst of it: the products reappear the
    next morning, so the synchronised drop is demoted from DELISTING to
    STOCKOUT and never reaches the manager as a warning.

    What is left is still harmful in the other direction — every product at
    every missing branch becomes a competitor-stockout *opportunity*, which is
    how a manager ends up bulk-buying against 125 branches that were never out
    of anything. The guard is what removes it.
    """
    unguarded = series_with([156, 31, 156])
    events = detect_drops(unguarded, base_rate=0.005)

    assert events, "fixture is wrong: a truncated day should produce drops"
    assert all(e.state != STATE_DELISTING for e in events), (
        "persistence rule should have demoted these — see test_concentration.py"
    )
    assert all(e.is_opportunity for e in events)
    assert max(e.stores_dropped for e in events) == 125   # every missing branch

    guarded = series_with([156, 31, 156])
    _drop_undercovered_days(guarded)
    assert detect_drops(guarded, base_rate=0.005) == []


def test_a_truncated_day_at_the_end_of_the_series_is_still_removed():
    """The most dangerous shape: nothing follows it, so nothing can demote it.

    A drop on the final day has no future evidence, so Step 1 reports
    DELISTING_PROVISIONAL rather than STOCKOUT. That is correctly not a warning,
    but it should not be in the output at all when the cause is a short download.
    """
    unguarded = series_with([156, 156, 31])
    assert detect_drops(unguarded, base_rate=0.005), "fixture is wrong"

    guarded = series_with([156, 156, 31])
    _drop_undercovered_days(guarded)
    assert detect_drops(guarded, base_rate=0.005) == []


# ---------------------------------------------------------------------------
# Wiring — the guard is one call, which is exactly the kind of line that rots
# ---------------------------------------------------------------------------

def write_day(root: Path, day: date, branches: int, status: str = "ok"):
    day_dir = root / day.isoformat()
    src = day_dir / "price_transparency" / "01"
    src.mkdir(parents=True, exist_ok=True)
    rows = [
        {"barcode": f"729000000{p}", "store_id": str(b), "product_name": f"product {p}"}
        for b in range(branches)
        for p in range(4)
    ]
    pl.DataFrame(rows).write_parquet(src / "alonit_prices_silver.parquet")
    (day_dir / "_manifest.json").write_text(json.dumps({
        "date": day.isoformat(),
        "status": status,
        "sources": {"price_transparency": {"status": status, "files": 1}},
    }))


def test_load_presence_applies_the_guard(tmp_path):
    for offset, branches in enumerate((156, 31, 156)):
        write_day(tmp_path, DAY0 + timedelta(days=offset), branches)

    series = load_presence(root=tmp_path)

    assert len(series.days) == 2
    assert DAY0 + timedelta(days=1) in series.skipped
    # And the surviving days pair with each other rather than across a void.
    assert list(series.consecutive_pairs()) == [(DAY0, DAY0 + timedelta(days=2))]


def test_load_presence_still_skips_a_failed_manifest(tmp_path):
    """The older guard must survive the new one."""
    write_day(tmp_path, DAY0, 156)
    write_day(tmp_path, DAY0 + timedelta(days=1), 156, status="failed")
    write_day(tmp_path, DAY0 + timedelta(days=2), 156)

    series = load_presence(root=tmp_path)
    assert len(series.days) == 2
    assert "failed" in series.skipped[DAY0 + timedelta(days=1)]


# ---------------------------------------------------------------------------
# Phase 5 Task 5.4: not orderable (ADR-031 Decision 1)
# ---------------------------------------------------------------------------

def write_delivery_day(root, day, rows):
    day_dir = root / day.isoformat()
    src = day_dir / "delivery_catalog" / "01"
    src.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(src / "products_silver.parquet")
    (day_dir / "_manifest.json").write_text(json.dumps({
        "date": day.isoformat(), "status": "ok",
        "sources": {"delivery_catalog": {"status": "ok", "files": 1}},
    }))


def test_a_listed_item_marked_not_orderable_is_recorded_and_still_listed(tmp_path):
    """The stores mostly drop a sold-out item, but a few mark it instead. Running out reads
    those as absent; every existing reader of `listings` still sees them listed."""
    write_delivery_day(tmp_path, DAY0, [
        {"barcode": "0072900001", "store_id": "w", "is_online_available": True},
        {"barcode": "72900002", "store_id": "w", "is_online_available": False},
        {"barcode": "72900003", "store_id": "w", "is_online_available": None},   # unknown, not absent
    ])
    series = load_presence(root=tmp_path, source_id="delivery_catalog")
    assert series.listings[DAY0] == {("72900001", "w"), ("72900002", "w"), ("72900003", "w")}
    assert series.unavailable[DAY0] == {("72900002", "w")}


def test_a_source_without_the_flag_marks_nothing_unavailable(tmp_path):
    write_delivery_day(tmp_path, DAY0, [{"barcode": "72900001", "store_id": "w"}])
    series = load_presence(root=tmp_path, source_id="delivery_catalog")
    assert series.unavailable[DAY0] == set()


def test_a_pair_any_line_calls_orderable_is_not_unavailable(tmp_path):
    """Two collection runs in one day can print one pair twice. One "not orderable" beside
    one "orderable" is not a stockout."""
    write_delivery_day(tmp_path, DAY0, [
        {"barcode": "72900001", "store_id": "w", "is_online_available": False},
        {"barcode": "72900001", "store_id": "w", "is_online_available": True},
    ])
    series = load_presence(root=tmp_path, source_id="delivery_catalog")
    assert series.unavailable[DAY0] == set()
