# tests/internal_pos/test_pos_importer.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

import pyarrow.parquet as pq

import src.common.source_status as source_status
import src.internal_pos.pos_importer as imp

HEADER = "קוד פריט ,ברקוד ,תאור פריט ,סוג פריט ,מלאי נוכחי ,מחיר קניה ,מחיר מכירה ,WOLT,שם מחלקה ,יחידת מידה ,שם מחלקה ,\n"


def test_import_preserves_negative_stock_and_records_vintage(tmp_path, monkeypatch):
    csv = tmp_path / "yomyom-inventory.csv"
    csv.write_text("﻿" + HEADER + "1,0012,מים,רגיל,-5,2.00,4.00,4.00,משקאות,יח',משקאות,\n", encoding="utf-8")
    silver = tmp_path / "silver"
    monkeypatch.setattr(imp, "SILVER_POS_DIR", silver)
    monkeypatch.setattr(imp, "QUALITY_REPORT_DIR", tmp_path / "q")
    # import_pos_file calls update_source(), which writes public/data/sources.json —
    # a COMMITTED artefact. Without this the one-row fixture rewrites the real file's
    # yomyom_pos row_count from 7,674 to 1.
    monkeypatch.setattr(source_status, "SOURCES_JSON", tmp_path / "sources.json")
    result = imp.import_pos_file(csv, as_of="2026-08-02")
    assert result["status"] == "ok"
    inv = pq.read_table(silver / "yomyom_inventory.parquet").to_pylist()[0]
    assert inv["current_stock"] == -5
    assert inv["_as_of"] == "2026-08-02"
    assert not (silver / "yomyom_sales.parquet").exists()
    # This test declares as_of explicitly, which is the only source that is certainly
    # the export date — hence "declared". See resolve_as_of for the other two.
    assert imp.read_pos_vintage(silver) == {"file": "yomyom-inventory.csv",
                                            "as_of": "2026-08-02",
                                            "as_of_source": "declared"}


def test_missing_silver_has_no_vintage(tmp_path):
    assert imp.read_pos_vintage(tmp_path) is None


# ── The POS vintage must be the day the export was taken ──────────────────────
# SPEC-007 FR-120, and the comment in import_pos_file has always said so. The
# default did not honour it: `date.fromtimestamp(path.stat().st_mtime)`.
#
# `git clone` sets every file's mtime to checkout time, so on a CI runner that
# resolved to TODAY — every day, for ever. The artefact published
# `pos.as_of: 2026-09-13` while yomyom-inventory.csv had not changed in git since
# 2026-06-06, three months earlier. On a laptop the same import said 2026-08-02,
# because that was that machine's mtime. Two machines, one commit, two vintages.
#
# The file carries no date column — headers are item code, barcode, description,
# type, stock, prices, department — so there is nothing in the data to read. The
# honest ladder is: what a human declared, then what git records as the file's
# last change (machine-independent and true), then mtime, each labelled.

def test_a_declared_vintage_wins_and_says_so():
    when, source = imp.resolve_as_of(Path("whatever.csv"), declared="2026-06-01")
    assert (when, source) == ("2026-06-01", "declared")


def test_a_tracked_file_takes_its_vintage_from_git_not_the_filesystem(tmp_path, monkeypatch):
    """The case that was wrong. On a runner mtime is checkout time; git is not."""
    monkeypatch.setattr(imp, "_git_committed_date", lambda p: "2026-06-06")
    csv = tmp_path / "inv.csv"
    csv.write_text("x", encoding="utf-8")

    when, source = imp.resolve_as_of(csv)

    assert source == "git_commit"
    assert when == "2026-06-06", "a clone's mtime must not become the vintage"


def test_an_untracked_file_falls_back_to_mtime_and_admits_it(tmp_path, monkeypatch):
    """A customer's export will not be in our git history. mtime is then the best
    available, and the artefact has to say that is what it is."""
    monkeypatch.setattr(imp, "_git_committed_date", lambda p: None)
    csv = tmp_path / "inv.csv"
    csv.write_text("x", encoding="utf-8")

    when, source = imp.resolve_as_of(csv)

    from datetime import date
    assert source == "file_mtime"
    assert when == date.fromtimestamp(csv.stat().st_mtime).isoformat()


def test_the_vintage_source_reaches_the_reader(tmp_path, monkeypatch):
    """read_pos_vintage is what the engine publishes. A source nobody can read is
    the flag-that-moves-nothing failure this repo keeps finding."""
    monkeypatch.setattr(imp, "_git_committed_date", lambda p: "2026-06-06")
    csv = tmp_path / "yomyom-inventory.csv"
    csv.write_text("﻿" + HEADER + "1,0012,מים,רגיל,-5,2.00,4.00,4.00,משקאות,יח',משקאות,\n",
                   encoding="utf-8")
    silver = tmp_path / "silver"
    monkeypatch.setattr(imp, "SILVER_POS_DIR", silver)
    monkeypatch.setattr(imp, "QUALITY_REPORT_DIR", tmp_path / "q")

    assert imp.import_pos_file(csv)["status"] == "ok"

    vintage = imp.read_pos_vintage(silver)
    assert vintage["as_of"] == "2026-06-06"
    assert vintage["as_of_source"] == "git_commit"


# ── A shallow clone cannot answer "when did this file last change" ────────────
# Shipped 2026-09-13 and wrong by 2026-09-15. `actions/checkout@v4` defaults to
# fetch-depth 1, so the runner holds ONE commit and `git log -1 -- <file>` has
# nothing to diff against — it attributes the file to the checkout commit and
# returns that commit's date.
#
#   09-14 nightly  checked out 7d8f65a (dated 09-14)  published as_of 2026-09-14
#   09-15 nightly  checked out 4645cd5 (dated 09-14)  published as_of 2026-09-14
#
# The CSV has not changed since 2026-06-06. So the git route reproduced exactly
# the defect it replaced — a date that tracks the checkout, not the data — and
# labelled it `git_commit`, which reads as verified. That is worse than the mtime
# version, because mtime at least announced itself as a filesystem timestamp.
#
# Two changes. A declared sidecar beside the export is consulted first, because a
# date someone wrote down is the only kind that is actually the export date. And
# the git route refuses to answer in a shallow repository rather than guessing.

def test_a_shallow_repository_cannot_supply_a_vintage(tmp_path, monkeypatch):
    monkeypatch.setattr(imp, "_is_shallow", lambda p: True)
    monkeypatch.setattr(imp, "_git_log_date", lambda p: "2026-09-14")  # what a runner returns
    csv = tmp_path / "inv.csv"
    csv.write_text("x", encoding="utf-8")

    assert imp._git_committed_date(csv) is None, (
        "in a one-commit clone git log reports the checkout, not the file's history"
    )
    when, source = imp.resolve_as_of(csv)
    assert source == "file_mtime", "with git unusable it must fall back and say so"
    assert when != "2026-09-14"


def test_a_declared_sidecar_beats_git(tmp_path, monkeypatch):
    """The only source that is actually the export date is one a human wrote down.

    It also survives a shallow clone, a fresh checkout and a customer's zip, none of
    which carry our git history.
    """
    monkeypatch.setattr(imp, "_git_committed_date", lambda p: "2026-09-14")
    csv = tmp_path / "yomyom-inventory.csv"
    csv.write_text("x", encoding="utf-8")
    (tmp_path / "yomyom-inventory.vintage.json").write_text(
        json.dumps({"as_of": "2026-06-06", "note": "export taken by the owner"}), encoding="utf-8")

    assert imp.resolve_as_of(csv) == ("2026-06-06", "declared_sidecar")


def test_an_explicit_as_of_still_beats_the_sidecar(tmp_path, monkeypatch):
    csv = tmp_path / "inv.csv"
    csv.write_text("x", encoding="utf-8")
    (tmp_path / "inv.vintage.json").write_text(json.dumps({"as_of": "2026-06-06"}), encoding="utf-8")
    assert imp.resolve_as_of(csv, declared="2026-01-01") == ("2026-01-01", "declared")


def test_a_malformed_sidecar_is_ignored_not_fatal(tmp_path, monkeypatch):
    """A broken sidecar must not take the import down; it must decline to answer."""
    monkeypatch.setattr(imp, "_git_committed_date", lambda p: None)
    csv = tmp_path / "inv.csv"
    csv.write_text("x", encoding="utf-8")
    (tmp_path / "inv.vintage.json").write_text("{not json", encoding="utf-8")
    when, source = imp.resolve_as_of(csv)
    assert source == "file_mtime"
    assert when
