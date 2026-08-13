"""
T1 / #46 Step 3 — the manifest, and the short-run check on top of it.

Everything the manifest previously asked was "did files arrive?". On 11 Aug 2026
a run arrived cleanly with 31 of 156 branches and was recorded `ok`. A day like
that, trusted, is 125 branches dropping their entire assortment overnight.

So the manifest now records branch coverage and downgrades a run that is short
against the history it already accepted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import polars as pl
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.write_snapshot_manifest as wsm  # noqa: E402


@pytest.fixture
def snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr(wsm, "EXTERNAL_SNAPSHOTS_ROOT", tmp_path)
    return tmp_path


def write_source(root: Path, day: str, branches: int, source="price_transparency"):
    d = root / day / source / "01"
    d.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [{"barcode": f"729{p}", "store_id": str(b)} for b in range(branches) for p in range(3)]
    ).write_parquet(d / "alonit_prices_silver.parquet")
    return root / day


def seal(root: Path, day: str, sources: dict):
    (root / day).mkdir(parents=True, exist_ok=True)
    (root / day / "_manifest.json").write_text(
        json.dumps({"date": day, "status": "ok", "sources": sources})
    )


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------

def test_branches_are_counted_from_silver(snapshots):
    day_dir = write_source(snapshots, "2026-08-11", branches=156)
    assert wsm.count_branches(day_dir / "price_transparency") == 156


def test_a_source_without_store_ids_reports_no_count(snapshots):
    """None, not 0. Zero would read as "every branch vanished" and downgrade a
    source that simply does not carry a branch column."""
    d = snapshots / "2026-08-11" / "other_source" / "01"
    d.mkdir(parents=True)
    pl.DataFrame([{"barcode": "729", "product_name": "x"}]).write_parquet(
        d / "products_silver.parquet"
    )
    assert wsm.count_branches(snapshots / "2026-08-11" / "other_source") is None


def test_a_single_venue_source_counts_as_one(snapshots):
    """The delivery catalogue does carry store_id — one venue today. It is
    compared against its own history, so 1 against a median of 1 never trips."""
    d = snapshots / "2026-08-11" / "delivery_catalog" / "01"
    d.mkdir(parents=True)
    pl.DataFrame([{"barcode": "729", "store_id": "689d9d1e"}]).write_parquet(
        d / "products_silver.parquet"
    )
    assert wsm.count_branches(snapshots / "2026-08-11" / "delivery_catalog") == 1

    seal(snapshots, "2026-08-10", {"delivery_catalog": {"status": "ok", "venues": 1}})
    entry = wsm.describe_source(snapshots / "2026-08-11", "delivery_catalog")
    # Short against the 9 declared targets, which is correct and is exactly what
    # the daily run looked like before the config was wired in.
    assert entry["status"] == "partial"
    assert entry["venues"] == 1


def test_bronze_files_are_not_counted(snapshots):
    d = snapshots / "2026-08-11" / "price_transparency" / "01"
    d.mkdir(parents=True)
    pl.DataFrame([{"barcode": "1", "store_id": str(b)} for b in range(9)]).write_parquet(
        d / "alonit_bronze.parquet"
    )
    assert wsm.count_branches(snapshots / "2026-08-11" / "price_transparency") is None


# ---------------------------------------------------------------------------
# The downgrade
# ---------------------------------------------------------------------------

def test_the_first_day_is_not_downgraded(snapshots):
    """Nothing to compare against. Guessing an expected size would make the very
    first collection fail on a chain we have never measured."""
    write_source(snapshots, "2026-08-11", branches=31)
    entry = wsm.describe_source(snapshots / "2026-08-11", "price_transparency")
    assert entry["status"] == "ok"
    assert entry["stores"] == 31


def test_the_manifest_uses_the_field_names_from_the_spec(snapshots):
    """#46 Step 3 names them `stores` and `venues`, with `rows`. The concept is
    the same; the names are what anyone reading a manifest will look for."""
    write_source(snapshots, "2026-08-11", branches=3)
    entry = wsm.describe_source(snapshots / "2026-08-11", "price_transparency")
    assert entry["stores"] == 3
    assert entry["rows"] == 9              # 3 branches x 3 products
    assert "branches" not in entry


def test_a_short_delivery_run_is_measured_against_the_declared_targets(snapshots):
    """The delivery catalogue is the one source that DECLARES how many places it
    should reach, so it does not have to wait for a median to notice a shortfall."""
    write_source(snapshots, "2026-08-11", branches=4, source="delivery_catalog")
    entry = wsm.describe_source(snapshots / "2026-08-11", "delivery_catalog")
    assert entry["venues"] == 4
    assert entry["expected"] == wsm.expected_units("delivery_catalog")
    assert entry["status"] == "partial"
    assert "4 of" in entry["note"]


def test_a_complete_delivery_run_is_ok(snapshots):
    expected = wsm.expected_units("delivery_catalog")
    write_source(snapshots, "2026-08-11", branches=expected, source="delivery_catalog")
    entry = wsm.describe_source(snapshots / "2026-08-11", "delivery_catalog")
    assert entry["status"] == "ok"
    assert entry["venues"] == expected


def test_a_short_run_is_downgraded_against_the_history(snapshots):
    seal(snapshots, "2026-08-11", {"price_transparency": {"status": "ok", "stores": 156}})
    seal(snapshots, "2026-08-12", {"price_transparency": {"status": "ok", "stores": 156}})
    write_source(snapshots, "2026-08-13", branches=31)          # the 11 Aug shape

    entry = wsm.describe_source(snapshots / "2026-08-13", "price_transparency")
    assert entry["status"] == "partial"
    assert entry["stores"] == 31
    assert "short run" in entry["note"]


def test_an_ordinary_day_survives_the_check(snapshots):
    seal(snapshots, "2026-08-11", {"price_transparency": {"status": "ok", "stores": 156}})
    seal(snapshots, "2026-08-12", {"price_transparency": {"status": "ok", "stores": 154}})
    write_source(snapshots, "2026-08-13", branches=155)

    entry = wsm.describe_source(snapshots / "2026-08-13", "price_transparency")
    assert entry["status"] == "ok"
    assert "note" not in entry


def test_the_pre_spec_field_name_still_counts_toward_the_median(snapshots):
    """Manifests written before the rename say `branches`. Ignoring them would
    reset the median to nothing and disarm the check for days."""
    seal(snapshots, "2026-08-11", {"price_transparency": {"status": "ok", "branches": 156}})
    assert wsm.median_branches_before("2026-08-12", "price_transparency") == 156


def test_the_median_ignores_later_days(snapshots):
    """A day is judged against what came before it, so re-sealing an old day
    cannot be swayed by days collected after it."""
    seal(snapshots, "2026-08-10", {"price_transparency": {"status": "ok", "stores": 30}})
    seal(snapshots, "2026-08-20", {"price_transparency": {"status": "ok", "stores": 156}})
    assert wsm.median_branches_before("2026-08-15", "price_transparency") == 30


def test_a_corrupt_earlier_manifest_does_not_break_the_comparison(snapshots):
    (snapshots / "2026-08-11").mkdir(parents=True)
    (snapshots / "2026-08-11" / "_manifest.json").write_text("{ not json")
    seal(snapshots, "2026-08-12", {"price_transparency": {"status": "ok", "stores": 156}})
    assert wsm.median_branches_before("2026-08-13", "price_transparency") == 156


def test_the_whole_manifest_reflects_a_short_run(snapshots):
    seal(snapshots, "2026-08-11", {"price_transparency": {"status": "ok", "stores": 156}})
    write_source(snapshots, "2026-08-12", branches=31)
    write_source(snapshots, "2026-08-12", branches=1, source="delivery_catalog")

    manifest = wsm.build_manifest("2026-08-12", "test@1")
    assert manifest["status"] == "partial"
    assert manifest["sources"]["price_transparency"]["status"] == "partial"
