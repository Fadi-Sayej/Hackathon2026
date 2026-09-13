"""Retired artefacts stay retired.

ADR-005 (Accepted) retires `public/data/sources.json` at the browser cut-over, and
design §20.2 is more specific still: it "stops immediately", End of Phase 2. The
cut-over shipped on 2026-09-12 and the file kept being written anyway, by three
separate code paths, for a day — because nothing anywhere asserted the decision.

That is the defect this file exists to prevent, and it is not really about
sources.json. An Accepted ADR that no test enforces is a comment. The cost here was
a committed artefact whose `row_count` meant two different things depending on which
writer ran last: 560,596 alonit signals after dedup from the engine, 17,165,316 raw
parquet rows across 33 snapshot days from the legacy exporter. Both were true, which
is exactly why neither could be published.

Add a line to RETIRED when an artefact is retired. That is the whole maintenance cost.
"""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# path relative to the repo root -> the decision that retired it
RETIRED = {
    "public/data/sources.json": "ADR-005 / design §20.2 — retires at the browser cut-over",
}


@pytest.mark.parametrize("relpath,authority", sorted(RETIRED.items()))
def test_a_retired_artefact_is_not_in_the_repository(relpath, authority):
    path = ROOT / relpath
    assert not path.exists(), (
        f"{relpath} is retired by {authority} but exists at {path}.\n"
        "Something is writing it again. Find the writer, do not delete the file and "
        "leave the writer in place — that is how it came back the first time."
    )


def test_importing_pos_does_not_resurrect_a_retired_artefact(tmp_path, monkeypatch):
    """The POS importer is the path that runs every night, so it is the one that would
    bring the file back. It called update_source() until 2026-09-13.

    Deliberately does NOT patch a sources path: the point is that no such write happens
    at all any more. Patching one would hide exactly the regression this catches.
    """
    import src.internal_pos.pos_importer as imp

    header = ("index,ברקוד,תאור פריט,סוג,מלאי נוכחי,מחיר עלות,מחיר מכירה,מחיר מכירה 2,"
              "קבוצה,יחידת מידה,מחלקה,ספק")
    csv = tmp_path / "pos.csv"
    csv.write_text("﻿" + header + "\n1,0012,מים,רגיל,-5,2.00,4.00,4.00,משקאות,יח',משקאות,\n",
                   encoding="utf-8")
    monkeypatch.setattr(imp, "SILVER_POS_DIR", tmp_path / "silver")
    monkeypatch.setattr(imp, "QUALITY_REPORT_DIR", tmp_path / "q")

    result = imp.import_pos_file(csv, as_of="2026-08-02")

    assert result["status"] == "ok"
    for relpath in RETIRED:
        assert not (ROOT / relpath).exists(), f"import_pos_file() recreated {relpath}"
