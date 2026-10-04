# tests/test_shelf_example.py
"""D-31: Shelf plan's example is the engine's output over a test shop, and nothing else reads it.

As with Reorder's (tests/test_order_example.py), the example is the one place example data may
appear (CLAUDE.md rule 7). So it must be what the engine says about the test shop today, show the
kinds of plan the page can show, come from the source the owner approved (Reorder's shop with a
layout added, 2026-10-04), and stay where only the preview reads it.
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

EXAMPLE = ROOT / "public" / "examples" / "shelf-plan-example.json"


def _builder(name="build_shelf_example"):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_the_committed_example_is_what_the_engine_builds_today():
    builder = _builder()
    assert EXAMPLE.read_text(encoding="utf-8") == builder.render(builder.build()), \
        "public/examples/shelf-plan-example.json is stale: run python3 scripts/build_shelf_example.py"


def test_it_says_it_is_an_example(example):
    assert "not any store's data" in example["_example"]


def test_it_is_reorders_shop_as_the_owner_approved(example):
    order = json.loads((ROOT / "public" / "examples" / "order-example.json").read_text(encoding="utf-8"))
    assert {p["barcode"] for p in example["catalogue"]["products"]} == \
        {p["barcode"] for p in order["catalogue"]["products"]}


def test_it_shows_the_kinds_of_plan_the_page_can_show(example):
    caps = example["artefact"]["capabilities"]
    assert caps["layout_facts"]["status"] == "available"
    plans = [e["evidence"] for e in caps["shelf_plan"]["entries"]]
    assert {p["extra_facings"] for p in plans} == {"given", "no_width"}            # FR-185, FR-186
    assert any(p["unplaced"]["no_width"] for p in plans) and any(p["unplaced"]["no_sale_in_window"] for p in plans)
    assert any(prod["facings"] > 1 for p in plans for s in p["shelves"] for prod in s["products"])
    # FR-185 where it matters: spare length on a shared shelf goes to some products and not others.
    assert any(len(s["products"]) > 1 and len({prod["facings"] for prod in s["products"]}) > 1
               for p in plans for s in p["shelves"])
    assert caps["layout_facts"]["rejected"]                                       # FR-178, named
    assert caps["shelf_plan"]["elasticity"]["source"] == "research"
    # No arrangement yet, as at a new store: the measurement waits, and says why.
    assert caps["shelf_measurement"]["unavailable_reason"] == "no_arrangement_recorded"
    # FR-215: until the team seals its explanation by hand with the key, each plan says it has
    # not been written, never "no model key".
    explanation = caps["shelf_explanation"]
    assert explanation["status"] == "available"
    assert {e["why_none"] for e in explanation["explanations"]} <= {"not_written_tonight", None}


def test_nothing_but_the_preview_reads_it():
    listed = subprocess.run(["git", "grep", "-l", "shelf-plan-example.json", "--", "src", "scripts", ".github",
                             "api", "middleware.ts"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert set(listed) <= {"src/lib/dataAdapters/loadShelfExample.js", "scripts/build_shelf_example.py",
                           "src/pages/ShelfPlanPage.jsx", "src/lib/dataAdapters/__tests__/loadShelfExample.test.js",
                           "src/pages/__tests__/shelfPlanPreview.test.jsx"}, listed


def test_every_store_copy_keeps_it():
    """It is a test shop, nobody's data, so it is code to the store-data manifest (ADR-036)."""
    from src.common.store import get_store, is_store_data
    assert not is_store_data("public/examples/shelf-plan-example.json", get_store())
