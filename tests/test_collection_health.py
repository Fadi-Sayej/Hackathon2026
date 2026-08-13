"""
T1 / #46 Step 5 — does the collector notice when it stops collecting?

The issue: *"A collector that dies silently in week 3 and is noticed in week 8
has cost five weeks of irreplaceable history. This is the single most likely way
this track fails."*

Every case below is a way the collection can be broken while every job stays
green, which is why "the workflow didn't fail" is not evidence of health.
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

from scripts.check_collection_health import assess  # noqa: E402

TODAY = date(2026, 8, 13)


def write_day(root: Path, day: date, stores: int = 156, status: str = "ok"):
    day_dir = root / day.isoformat()
    src = day_dir / "price_transparency" / "01"
    src.mkdir(parents=True, exist_ok=True)
    pl.DataFrame([
        {"barcode": f"729000{p}", "store_id": str(b), "product_name": f"p{p}"}
        for b in range(stores) for p in range(3)
    ]).write_parquet(src / "alonit_prices_silver.parquet")
    (day_dir / "_manifest.json").write_text(json.dumps({
        "date": day.isoformat(),
        "status": status,
        "sources": {"price_transparency": {"status": status, "files": 1, "stores": stores}},
    }))


def days_back(n):
    return [TODAY - timedelta(days=i) for i in range(n - 1, -1, -1)]


# ---------------------------------------------------------------------------
# Healthy
# ---------------------------------------------------------------------------

def test_an_unbroken_run_is_healthy(tmp_path):
    for day in days_back(5):
        write_day(tmp_path, day)
    report = assess(today=TODAY, root=tmp_path)
    assert report["healthy"] is True
    assert report["usable_days"] == 5
    assert report["consecutive_days_to_date"] == 5
    assert report["problems"] == []


def test_yesterday_is_fresh_enough(tmp_path):
    """The collector runs overnight; demanding today would fail every morning
    before it fires."""
    for day in days_back(4)[:-1]:
        write_day(tmp_path, day)
    assert assess(today=TODAY, root=tmp_path)["healthy"] is True


# ---------------------------------------------------------------------------
# The silent failures
# ---------------------------------------------------------------------------

def test_a_stalled_collector_is_caught(tmp_path):
    """The schedule stopped firing. No run, no failure, no email — and every day
    that passes is permanently unrecoverable."""
    for day in days_back(10)[:5]:
        write_day(tmp_path, day)
    report = assess(today=TODAY, root=tmp_path)
    assert report["healthy"] is False
    assert any("stopped accumulating" in p for p in report["problems"])
    assert report["latest_age_days"] == 5


def test_no_snapshots_at_all_is_caught(tmp_path):
    report = assess(today=TODAY, root=tmp_path)
    assert report["healthy"] is False
    assert any("no usable snapshot" in p for p in report["problems"])
    assert report["latest_day"] is None


def test_a_hole_in_the_middle_is_caught(tmp_path):
    """#46 asks for 30 CONSECUTIVE days. A missing day resets the run rather
    than delaying it by one, so it has to be visible immediately."""
    for day in days_back(5):
        if day == TODAY - timedelta(days=2):
            continue
        write_day(tmp_path, day)
    report = assess(today=TODAY, root=tmp_path)
    assert report["healthy"] is False
    assert report["missing_days"] == [(TODAY - timedelta(days=2)).isoformat()]
    assert report["consecutive_days_to_date"] == 2      # the run restarted


def test_a_green_job_that_produced_an_unusable_day_is_caught(tmp_path):
    """The quietest failure of all: files arrived, the job passed, and the day
    covers 31 of 156 branches."""
    for day in days_back(5)[:-1]:
        write_day(tmp_path, day)
    write_day(tmp_path, TODAY, stores=20)              # short run
    report = assess(today=TODAY, root=tmp_path)
    assert report["healthy"] is False
    assert any("unusable" in p for p in report["problems"])
    assert TODAY.isoformat() in report["unusable_days"]


def test_a_failed_manifest_day_counts_as_a_gap(tmp_path):
    for day in days_back(4)[:-1]:
        write_day(tmp_path, day)
    write_day(tmp_path, TODAY, status="failed")
    report = assess(today=TODAY, root=tmp_path)
    assert report["healthy"] is False


# ---------------------------------------------------------------------------
# Not gaps
# ---------------------------------------------------------------------------

def test_days_before_the_project_started_are_not_missing(tmp_path):
    """The window is 30 days; collection began 3 days ago. Reporting 27 missing
    days would make the check cry wolf from day one and be ignored by week two."""
    for day in days_back(3):
        write_day(tmp_path, day)
    report = assess(today=TODAY, root=tmp_path, window=30)
    assert report["missing_days"] == []
    assert report["healthy"] is True


def test_today_is_not_yet_missing(tmp_path):
    """Tonight's run has not happened. Counting today as a hole would fail every
    day until the collector fires."""
    for day in days_back(4)[:-1]:
        write_day(tmp_path, day)
    report = assess(today=TODAY, root=tmp_path)
    assert TODAY.isoformat() not in report["missing_days"]
