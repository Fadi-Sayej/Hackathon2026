"""rehydrate_silver.py — and the silver files no snapshot accounts for.

Rehydrate copies committed snapshots into the silver tree and never removes anything. That
is safe on a runner, which starts empty, and wrong on a working tree that has been alive
for months: `competitor_product_signals` reads *everything* under silver, so a laptop can
carry files no clean checkout has and quietly produce different numbers from CI.

Measured on 2026-09-13 at commit 462d604. Same commit, same snapshots:

    fresh clone   341 delivery_catalog parquet → 7,448 wolt rows → 190,426 match records
    working tree  343 delivery_catalog parquet → 7,455 wolt rows → 189,562 match records

On that tree, 44 of the 343 parquet under `products/delivery_catalog` carry a filename no
committed snapshot holds — the oldest from May 2026, before the collector existed. Nobody
else can reproduce a run that reads them, and the run said nothing about it.

The guard globs `*.parquet`, matching the consumer, not `*_silver.parquet`, matching the
writer. The first version of it checked the writer's pattern and found 8 of the 44.

Reported, never deleted. These are real market observations and the snapshots cannot be
re-collected (see collect-daily.yml); throwing them away to make a count tidy is exactly
the trade this project does not make. The run states the discrepancy and a human decides.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.rehydrate_silver as rehyd


def _snapshot(root: Path, day: str, source_id: str, name: str) -> Path:
    p = root / day / source_id / f"{name}_silver.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"snapshot-bytes")
    return p


def _point_at(monkeypatch, snapshots: Path, silver: Path) -> None:
    monkeypatch.setattr(rehyd, "EXTERNAL_SNAPSHOTS_ROOT", snapshots)
    monkeypatch.setattr(rehyd, "EXTERNAL_SILVER_ROOT", silver)


def test_rehydrate_copies_what_the_snapshots_hold(tmp_path, monkeypatch):
    snapshots, silver = tmp_path / "snapshots", tmp_path / "silver"
    _snapshot(snapshots, "2026-09-13", "delivery_catalog", "products_20260913T020000")
    _snapshot(snapshots, "2026-09-13", "price_transparency", "prices_20260913T020000")
    _point_at(monkeypatch, snapshots, silver)

    result = rehyd.rehydrate()

    assert result["status"] == "ok"
    assert result["copied"] == 2
    assert (silver / "products/delivery_catalog/2026/09/13/products_20260913T020000_silver.parquet").exists()
    assert (silver / "alonit_prices/alonit/2026/09/13/prices_20260913T020000_silver.parquet").exists()
    assert result["orphans"] == 0


def test_a_silver_file_no_snapshot_accounts_for_is_counted_and_named(tmp_path, monkeypatch):
    """The 44 May files, in miniature.

    The orphan is left on disk on purpose: it is real collected data that predates the
    retention window and cannot be re-collected. What must not happen is a run reading it
    and reporting nothing.
    """
    snapshots, silver = tmp_path / "snapshots", tmp_path / "silver"
    _snapshot(snapshots, "2026-09-13", "delivery_catalog", "products_20260913T020000")

    stale = silver / "products/delivery_catalog/2026/05/25/products_20260525T144710_silver.parquet"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_bytes(b"collected-before-the-window")

    _point_at(monkeypatch, snapshots, silver)
    result = rehyd.rehydrate()

    assert result["orphans"] == 1
    assert result["orphan_paths"] == [
        "products/delivery_catalog/2026/05/25/products_20260525T144710_silver.parquet"
    ]
    assert stale.exists(), "an orphan is reported, never deleted"


def test_a_suffixed_shard_counts_too_because_the_consumer_reads_it(tmp_path, monkeypatch):
    """The 36 the first version of this guard missed.

    The collector writes shards beside each sealed file —
    `products_<ts>_silver_<n>.parquet` — and `competitor_product_signals` globs
    `*.parquet`, so it reads them. A guard that matched only `*_silver.parquet` saw 8 of
    44 real orphans and would have reported a tree as clean while the reader diverged.
    """
    snapshots, silver = tmp_path / "snapshots", tmp_path / "silver"
    _snapshot(snapshots, "2026-09-13", "delivery_catalog", "products_20260913T020000")

    shard = (silver / "products/delivery_catalog/2026/05/25"
             / "products_20260525T144710_silver_144718787348.parquet")
    shard.parent.mkdir(parents=True, exist_ok=True)
    shard.write_bytes(b"a shard no snapshot holds")

    _point_at(monkeypatch, snapshots, silver)
    result = rehyd.rehydrate()

    assert result["orphans"] == 1, "a shard the consumer globs must be counted"
    assert shard.exists()


def test_other_sources_under_silver_are_not_called_orphans(tmp_path, monkeypatch):
    """Only the two trees rehydrate owns are its business.

    silver/products/kaggle_* comes from a different pipeline and has no snapshots by
    design. Counting it would make the warning fire on every run and be ignored — which
    is how a real signal gets lost.
    """
    snapshots, silver = tmp_path / "snapshots", tmp_path / "silver"
    _snapshot(snapshots, "2026-09-13", "delivery_catalog", "products_20260913T020000")

    kaggle = silver / "products/kaggle_shufersal/2026/01/01/whatever_silver.parquet"
    kaggle.parent.mkdir(parents=True, exist_ok=True)
    kaggle.write_bytes(b"different pipeline")

    _point_at(monkeypatch, snapshots, silver)
    assert rehyd.rehydrate()["orphans"] == 0
