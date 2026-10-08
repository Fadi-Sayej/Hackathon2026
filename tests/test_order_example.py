# tests/test_order_example.py
"""D-29: the order pages' example is the engine's output over a test shop, and nothing else reads it.

The example is the one place example data may appear (CLAUDE.md rule 7). So:
- it must be what the engine says about the test shop today, never a hand-edited file that
  drifts from the real page;
- it must show every kind of line the pages can show, or the preview would mislead;
- it must stay where only the preview reads it.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EXAMPLE = ROOT / "public" / "examples" / "order-example.json"


def _builder():
    spec = importlib.util.spec_from_file_location("build_order_example", ROOT / "scripts" / "build_order_example.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_the_committed_example_is_what_the_engine_builds_today():
    builder = _builder()
    assert EXAMPLE.read_text(encoding="utf-8") == builder.render(builder.build()), \
        "public/examples/order-example.json is stale: run python3 scripts/build_order_example.py"



def test_every_stores_copy_builds_the_same_example(monkeypatch):
    """ADR-036: every copy ships this file. Its shop names its own format and nearby store, so a
    copy's settings, another format and none of YomYom's venues, build it byte for byte."""
    from tests.fixtures.another_store import serve_another_store
    serve_another_store(monkeypatch)
    builder = _builder()
    assert EXAMPLE.read_text(encoding="utf-8") == builder.render(builder.build())


def test_it_says_it_is_an_example(example):
    assert "not any store's data" in example["_example"]


def test_it_shows_every_kind_of_line(example):
    oq = example["artefact"]["capabilities"]["order_quantity"]
    entries = oq["entries"]
    assert oq["status"] == "available"
    assert any(e["evidence"]["boost"]["applied"] for e in entries)                      # boosted
    assert any(e["evidence"]["capped"] for e in entries)                                # shelf life caps it
    assert any(e["evidence"]["kind"] == "gross" for e in entries)                       # a count not used
    assert any(d["covered_by_stock"] for d in oq["departments"].values())               # stock covers it
    reasons = {r for d in oq["departments"].values() for r in d["reasons"]}
    assert {"not_moving", "no_shelf_life", "no_order_schedule"} <= reasons
    approved = example["owner_state"]["outcomes"].values()
    assert len(approved) == 3 and any("approved_quantity" in o["snapshot"] for o in approved)


def test_nothing_but_the_preview_reads_it():
    listed = subprocess.run(["git", "grep", "-l", "order-example.json", "--", "src", "scripts", ".github", "api",
                             "middleware.ts"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert set(listed) <= {"src/lib/dataAdapters/loadOrderExample.js", "scripts/build_order_example.py",
                           "src/pages/OrderExample.jsx", "src/lib/dataAdapters/__tests__/loadOrderExample.test.js",
                           "src/pages/__tests__/orderExamplePreview.test.jsx"}, listed


def test_every_store_copy_keeps_it():
    """It is a test shop, nobody's data, so it is code to the store-data manifest (ADR-036)."""
    from src.common.store import get_store, is_store_data
    assert not is_store_data("public/examples/order-example.json", get_store())
