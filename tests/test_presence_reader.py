# tests/test_presence_reader.py
"""The presence reader returns exactly what the row-by-row loop it replaced returned.

`_read_listings` walked every row in Python and every caller replays the whole history, so the
nightly's health checks and market context grew by minutes. On 2026-10-03 it was rewritten to
normalise in polars. When it changed, the old and new readers agreed on all 108 day-sources
committed then (54 days, both sources), at 24.6 s against 8.4 s. Here: the rules on synthetic
files built to break them, and the three latest committed days against the reference loop.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Set, Tuple

import polars as pl
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.paths import EXTERNAL_SNAPSHOTS_ROOT  # noqa: E402
from src.market.presence import _read_listings  # noqa: E402


def reference(source_dir: Path) -> Tuple[Set[Tuple[str, str]], Dict[str, str], Set[Tuple[str, str]]]:
    """The loop as it was before 2026-10-03, verbatim apart from its name."""
    pairs, names, not_orderable, orderable = set(), {}, set(), set()
    if not source_dir.exists():
        return pairs, names, not_orderable
    for path in sorted(source_dir.rglob("*.parquet")):
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
    return pairs, names, not_orderable - orderable


def _write(directory: Path, name: str, rows: dict, schema=None):
    directory.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows, schema=schema).write_parquet(directory / name)


def test_the_rules_hold_on_files_built_to_break_them(tmp_path):
    day = tmp_path / "delivery_catalog"
    _write(day / "a", "x_silver.parquet", {
        "barcode": [" 00729001 ", "729001", "0", None, "", "729002", "729002", "729003", "  "],
        "store_id": ["s1", " s1 ", "s1", "s1", "s1", "s2", "s2", None, "s3"],
        "product_name": [None, "first name", "zero", "n", "n", "", "late", "nostore", "blank"],
        "is_online_available": [None, True, False, False, False, False, True, False, False],
    })
    _write(day / "b", "y_silver.parquet", {        # a later file: names never overwrite
        "barcode": ["729001", "729004"], "store_id": ["s9", "s4"],
        "product_name": ["second name", "  "], "is_online_available": [False, None],
    })
    _write(day / "c", "z_silver.parquet", {"barcode": [None, None], "store_id": ["s5", "s6"]},
           schema={"barcode": pl.Null, "store_id": pl.String})
    _write(day / "d", "w_silver.parquet", {"barcode": ["729005"], "store_id": ["s7"],
                                           "is_online_available": ["false"]})   # not a real bool
    _write(day / "e", "v_bronze.parquet", {"barcode": ["729006"], "store_id": ["s8"]})  # bronze: skipped
    _write(day / "f", "u_silver.parquet", {"sku": ["1"], "store_id": ["s1"]})            # no barcode: skipped
    got, want = _read_listings(day), reference(day)
    assert got == want
    pairs, names, not_orderable = got
    assert ("729001", "s1") in pairs and ("729001", "s9") in pairs
    assert names["729001"] == "first name" and names["729004"] == "  "
    # 729002 at s2 was marked both ways, so it stays orderable; only s9's False stands.
    assert not_orderable == {("729001", "s9")}


def test_a_missing_directory_reads_as_nothing(tmp_path):
    assert _read_listings(tmp_path / "absent") == reference(tmp_path / "absent") == (set(), {}, set())


@pytest.mark.parametrize("source", ["price_transparency", "delivery_catalog"])
def test_the_latest_committed_days_read_as_they_always_did(source):
    days = sorted(d for d in EXTERNAL_SNAPSHOTS_ROOT.iterdir() if d.is_dir())[-3:] \
        if EXTERNAL_SNAPSHOTS_ROOT.exists() else []
    if not days:
        pytest.skip("no committed snapshots in this checkout")
    for day in days:
        assert _read_listings(day / source) == reference(day / source), day.name
