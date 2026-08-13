"""
T1 / #46 — diffing two collected days, and Step 6's disappearance guarantee.

Two things the issue asks for by name:

  Acceptance  "A diff between any two dates can be produced by a script."
  Step 6      "Record disappearances as carefully as appearances… Do not let it
               vanish by only storing what is present."

We took the issue's preferred option — keep full daily snapshots — so the delta
is derived rather than stored. That only satisfies Step 6 if the derivation
actually recovers a disappearance, which is what
`test_a_disappearance_is_recoverable_from_stored_snapshots` proves. The rest
guard the ways a diff can look right and be meaningless.
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

import scripts.diff_snapshots as ds  # noqa: E402


@pytest.fixture
def snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr(ds, "EXTERNAL_SNAPSHOTS_ROOT", tmp_path)
    return tmp_path


def write_day(root: Path, day: str, rows, status="ok", source="price_transparency"):
    """rows: list of (barcode, store_id, price, name)."""
    src = root / day / source / "01"
    src.mkdir(parents=True, exist_ok=True)
    pl.DataFrame([
        {"barcode": b, "store_id": s, "price": p, "product_name": n}
        for b, s, p, n in rows
    ]).write_parquet(src / "alonit_prices_silver.parquet")
    (root / day / "_manifest.json").write_text(json.dumps({
        "date": day, "status": status,
        "sources": {source: {"status": status, "files": 1, "stores": len({r[1] for r in rows})}},
    }))


# ---------------------------------------------------------------------------
# Step 6 — the guarantee
# ---------------------------------------------------------------------------

def test_a_disappearance_is_recoverable_from_stored_snapshots(snapshots):
    """Step 6's requirement, tested as a round trip.

    An item present yesterday and missing today IS the signal #49 consumes. We
    store no explicit delta, so the guarantee is only real if it can be derived
    back out of the snapshots on demand.
    """
    write_day(snapshots, "2026-08-11", [
        ("729001", "401", 5.0, "stays"),
        ("729002", "401", 9.9, "vanishes"),
    ])
    write_day(snapshots, "2026-08-12", [
        ("729001", "401", 5.0, "stays"),
    ])

    result = ds.diff("2026-08-11", "2026-08-12", "price_transparency")

    assert result["summary"]["disappeared"] == 1
    assert result["disappeared"] == [
        {"barcode": "729002", "store_id": "401", "product_name": "vanishes"}
    ]
    assert result["summary"]["barcodes_gone_everywhere"] == 1


def test_appearances_are_recovered_too(snapshots):
    write_day(snapshots, "2026-08-11", [("729001", "401", 5.0, "old")])
    write_day(snapshots, "2026-08-12", [
        ("729001", "401", 5.0, "old"),
        ("729003", "401", 3.0, "new"),
    ])
    result = ds.diff("2026-08-11", "2026-08-12", "price_transparency")
    assert result["summary"]["appeared"] == 1
    assert result["summary"]["barcodes_new_everywhere"] == 1


def test_a_product_gone_from_one_branch_only_is_not_gone_everywhere(snapshots):
    """The distinction #49 Step 1 rests on. Collapsing the two would turn every
    single-branch stockout into a delisting warning."""
    write_day(snapshots, "2026-08-11", [
        ("729001", "401", 5.0, "x"), ("729001", "402", 5.0, "x"),
    ])
    write_day(snapshots, "2026-08-12", [("729001", "402", 5.0, "x")])

    result = ds.diff("2026-08-11", "2026-08-12", "price_transparency")
    assert result["summary"]["disappeared"] == 1
    assert result["summary"]["barcodes_gone_everywhere"] == 0


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------

def test_price_changes_are_reported_with_direction(snapshots):
    write_day(snapshots, "2026-08-11", [("40349", "415", 9.90, "עגבנייה")])
    write_day(snapshots, "2026-08-12", [("40349", "415", 8.90, "עגבנייה")])

    result = ds.diff("2026-08-11", "2026-08-12", "price_transparency")
    assert result["summary"]["repriced"] == 1
    assert result["repriced"][0]["delta"] == pytest.approx(-1.0)
    assert result["repriced"][0]["product_name"] == "עגבנייה"


def test_an_unchanged_price_is_not_reported_as_a_change(snapshots):
    """Float noise would otherwise report every product every day and bury the
    real moves."""
    write_day(snapshots, "2026-08-11", [("40349", "415", 9.90, "x")])
    write_day(snapshots, "2026-08-12", [("40349", "415", 9.9000001, "x")])
    assert ds.diff("2026-08-11", "2026-08-12", "price_transparency")["summary"]["repriced"] == 0


# ---------------------------------------------------------------------------
# Refusing
# ---------------------------------------------------------------------------

def test_a_day_with_no_manifest_is_refused(snapshots):
    write_day(snapshots, "2026-08-11", [("729001", "401", 5.0, "x")])
    (snapshots / "2026-08-11" / "_manifest.json").unlink()
    reason = ds.why_unusable("2026-08-11", "price_transparency")
    assert reason and "manifest" in reason


def test_a_failed_day_is_refused(snapshots):
    write_day(snapshots, "2026-08-11", [("729001", "401", 5.0, "x")], status="failed")
    assert ds.why_unusable("2026-08-11", "price_transparency") is not None


def test_a_date_with_no_snapshot_is_refused(snapshots):
    reason = ds.why_unusable("2026-01-01", "price_transparency")
    assert reason and "no snapshot folder" in reason


def test_a_usable_day_is_not_refused(snapshots):
    for day in ("2026-08-11", "2026-08-12", "2026-08-13"):
        write_day(snapshots, day, [
            ("729001", str(400 + i), 5.0, "x") for i in range(20)
        ])
    assert ds.why_unusable("2026-08-12", "price_transparency") is None


def test_barcodes_are_normalised_the_same_way_as_the_presence_series(snapshots):
    """A leading zero on one day and not the next would read as a product
    disappearing and an identical one appearing, on every single day."""
    write_day(snapshots, "2026-08-11", [("0729001", "401", 5.0, "x")])
    write_day(snapshots, "2026-08-12", [("729001", "401", 5.0, "x")])

    summary = ds.diff("2026-08-11", "2026-08-12", "price_transparency")["summary"]
    assert summary["appeared"] == 0
    assert summary["disappeared"] == 0
