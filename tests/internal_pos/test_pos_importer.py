# tests/internal_pos/test_pos_importer.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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


def _inventory_lacking(silver: Path, *columns: str) -> None:
    """A silver table written before `columns` existed.

    The column set mirrors configs/pos_schema_mapping.yaml's inventory table, so this
    is a real older table rather than a three-column stand-in. `data/internal/silver_pos/`
    is gitignored, so whatever silver a developer has is whatever they last generated,
    and a parquet older than the commit that added a vintage column is the ordinary
    case on a real clone.
    """
    import pyarrow as pa

    present = {
        "barcode": ["0012"],
        "product_name": ["מים"],
        "category": ["משקאות"],
        "current_stock": [-5],
        "last_purchase_date": [None],
        "_imported_at": ["2026-08-02T00:00:00Z"],
        "_source_file": ["yomyom-inventory.csv"],
        "_source_kind": ["inventory"],
        "_as_of": ["2026-08-02"],
        "_as_of_source": ["declared"],
    }
    for column in columns:
        present.pop(column, None)
    silver.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(present), silver / "yomyom_inventory.parquet")


def test_a_parquet_written_before_as_of_still_loads(tmp_path):
    """read_pos_vintage selects the columns present rather than demanding them.

    Demanding them raises ArrowInvalid, and pyarrow does not degrade. The first caller
    to hit it is _sales_import (run.py), which runs before load_inputs; the exception
    is caught by _step, inputs becomes None, and run_engine's `if inputs is not None:`
    then skips the capability loop. validate_artefact refuses the result — nothing is
    written, the previous artefact survives — but the run is `partial` and the owner's
    file stops being rebuilt. The caller's contract is `read_pos_vintage(...) or {...}`:
    return, do not raise.
    """
    silver = tmp_path / "silver"
    _inventory_lacking(silver, "_as_of", "_as_of_source")
    assert imp.read_pos_vintage(silver) == {
        "file": "yomyom-inventory.csv", "as_of": None, "as_of_source": None}


def test_a_parquet_written_before_as_of_source_keeps_the_vintage(tmp_path):
    """The newer column is the one most likely to be missing, and it must not cost
    the date beside it."""
    silver = tmp_path / "silver"
    _inventory_lacking(silver, "_as_of_source")
    assert imp.read_pos_vintage(silver) == {
        "file": "yomyom-inventory.csv", "as_of": "2026-08-02", "as_of_source": None}


def test_a_parquet_with_no_vintage_columns_at_all_does_not_raise(tmp_path):
    silver = tmp_path / "silver"
    _inventory_lacking(silver, "_source_file", "_as_of", "_as_of_source")
    assert imp.read_pos_vintage(silver) == {
        "file": None, "as_of": None, "as_of_source": None}


def test_the_shape_a_zero_row_import_actually_writes(tmp_path):
    """_records_to_table writes a lone `_empty` column when there are no records
    (pos_importer.py), so this — not a zero-row table carrying the vintage columns —
    is what an empty import leaves on disk. Reading it must not raise and must not
    invent a date."""
    import pyarrow as pa

    silver = tmp_path / "silver"
    silver.mkdir(parents=True)
    pq.write_table(
        pa.table({"_empty": pa.array([], type=pa.bool_())}),
        silver / "yomyom_inventory.parquet",
    )
    assert imp.read_pos_vintage(silver).get("as_of") is None


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
