"""
T1 / #46 Steps 3 & 4 — sealing a day's snapshot without destroying it.

The first test here is a regression test for real data loss, not a hypothetical.

On 2026-08-13 the scheduled runner collected the delivery catalogue at 01:26 and
committed `data/external/snapshots/`. The bronze/silver lakehouse trees are
gitignored, so they never reached any other machine. Retrying that day locally
rebuilt the snapshot folder from a lakehouse that had never seen the runner's
files — and `rmtree` removed them. Both files were recoverable from git; the
point is that nothing in the code stopped it.

Immutability in #46 is not a property of the folder. It is a property of the
copy step, and it has to be tested there.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.seal_snapshot as seal  # noqa: E402


@pytest.fixture
def snap(tmp_path, monkeypatch):
    """A snapshot root whose manifest path helper points inside tmp_path."""
    def manifest_path(day):
        return tmp_path / "snapshots" / str(day) / "_manifest.json"
    monkeypatch.setattr(seal, "get_snapshot_manifest_path", manifest_path)
    return tmp_path


def make_files(directory: Path, names):
    directory.mkdir(parents=True, exist_ok=True)
    for name in names:
        (directory / name).write_text(name, encoding="utf-8")
    return directory


def seal_manifest(snap: Path, day: str, sources: dict):
    path = snap / "snapshots" / day / "_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"date": day, "sources": sources}))


# ---------------------------------------------------------------------------
# The regression
# ---------------------------------------------------------------------------

def test_a_retry_does_not_delete_files_it_did_not_collect(snap):
    """The 2026-08-13 incident, reproduced.

    `existing` stands for the runner's committed file, which this machine's
    lakehouse has never contained. It must survive a local retry.
    """
    dest = snap / "snapshots" / "2026-08-13" / "delivery_catalog"
    make_files(dest / "13", ["products_20260813T012626_silver.parquet"])
    lakehouse = make_files(snap / "lake" / "13", ["products_20260813T120118_silver.parquet"])

    result = seal.materialise("2026-08-13", "delivery_catalog", [lakehouse], dest=dest)

    survivors = {p.name for p in dest.rglob("*") if p.is_file()}
    assert "products_20260813T012626_silver.parquet" in survivors, "runner's file was destroyed"
    assert "products_20260813T120118_silver.parquet" in survivors
    assert result["already_present"] == 1
    assert result["collected"] == 1
    assert result["total"] == 2


def test_repeated_sealing_is_idempotent(snap):
    """Step 4: "Re-running the same day must not corrupt or duplicate.\""""
    dest = snap / "snapshots" / "2026-08-13" / "price_transparency"
    lakehouse = make_files(snap / "lake" / "13", ["a_silver.parquet", "a_bronze.parquet"])

    first = seal.materialise("2026-08-13", "price_transparency", [lakehouse], dest=dest)
    second = seal.materialise("2026-08-13", "price_transparency", [lakehouse], dest=dest)

    assert first["total"] == second["total"] == 2


def test_content_is_preserved_not_just_filenames(snap):
    dest = snap / "snapshots" / "2026-08-13" / "delivery_catalog"
    make_files(dest / "13", ["old.parquet"])
    lakehouse = make_files(snap / "lake" / "13", ["new.parquet"])

    seal.materialise("2026-08-13", "delivery_catalog", [lakehouse], dest=dest)
    assert (dest / "13" / "old.parquet").read_text() == "old.parquet"


# ---------------------------------------------------------------------------
# Per-source immutability
# ---------------------------------------------------------------------------

def test_a_source_already_marked_ok_is_never_touched(snap):
    """One dead venue must not put a complete 156-branch price file at risk."""
    seal_manifest(snap, "2026-08-13", {"price_transparency": {"status": "ok"}})
    dest = snap / "snapshots" / "2026-08-13" / "price_transparency"
    make_files(dest / "13", ["the_good_one.parquet"])
    lakehouse = make_files(snap / "lake" / "13", ["a_short_repull.parquet"])

    result = seal.materialise("2026-08-13", "price_transparency", [lakehouse], dest=dest)

    assert result["skipped"] == "already complete"
    assert {p.name for p in dest.rglob("*") if p.is_file()} == {"the_good_one.parquet"}


def test_a_partial_source_may_be_retried(snap):
    """Step 4: "A partial run may be retried; a successful run may not be
    replaced.\""""
    seal_manifest(snap, "2026-08-13", {"delivery_catalog": {"status": "partial"}})
    dest = snap / "snapshots" / "2026-08-13" / "delivery_catalog"
    make_files(dest / "13", ["one_venue.parquet"])
    lakehouse = make_files(snap / "lake" / "13", ["nine_venues.parquet"])

    result = seal.materialise("2026-08-13", "delivery_catalog", [lakehouse], dest=dest)
    assert result["total"] == 2


def test_a_missing_manifest_does_not_block_a_first_seal(snap):
    dest = snap / "snapshots" / "2026-08-13" / "price_transparency"
    lakehouse = make_files(snap / "lake" / "13", ["first.parquet"])
    assert seal.materialise("2026-08-13", "price_transparency", [lakehouse], dest=dest)["total"] == 1


def test_a_corrupt_manifest_is_treated_as_not_complete(snap):
    """Refusing to seal because the manifest is unreadable would lose today's
    collection over a file we are about to rewrite anyway."""
    path = snap / "snapshots" / "2026-08-13" / "_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ not json")
    dest = snap / "snapshots" / "2026-08-13" / "price_transparency"
    lakehouse = make_files(snap / "lake" / "13", ["x.parquet"])
    assert seal.materialise("2026-08-13", "price_transparency", [lakehouse], dest=dest)["total"] == 1


# ---------------------------------------------------------------------------
# Nothing collected
# ---------------------------------------------------------------------------

def test_an_empty_collection_leaves_an_existing_snapshot_alone(snap):
    """A source that fails today must not blank yesterday's copy of itself."""
    dest = snap / "snapshots" / "2026-08-13" / "delivery_catalog"
    make_files(dest / "13", ["already_here.parquet"])

    result = seal.materialise("2026-08-13", "delivery_catalog", [snap / "lake" / "missing"], dest=dest)

    assert result["total"] == 1
    assert (dest / "13" / "already_here.parquet").exists()


def test_nothing_collected_and_nothing_present_is_reported_not_crashed(snap):
    dest = snap / "snapshots" / "2026-08-13" / "delivery_catalog"
    result = seal.materialise("2026-08-13", "delivery_catalog", [snap / "lake" / "missing"], dest=dest)
    assert result["skipped"] == "nothing collected"


def test_no_temp_directory_is_left_behind(snap):
    dest = snap / "snapshots" / "2026-08-13" / "price_transparency"
    lakehouse = make_files(snap / "lake" / "13", ["x.parquet"])
    seal.materialise("2026-08-13", "price_transparency", [lakehouse], dest=dest)

    leftovers = [p for p in dest.parent.iterdir() if p.name.startswith(".")]
    assert leftovers == []
