# tests/engine/test_catalogue.py
"""The product catalogue published beside the artefact (ADR-024).

The artefact answers "what needs your decision today". Five of the restored pages need
the other thing — every product, not only the ones with a finding against them. That is
a different question and it is answered in a different file, for a measured reason:
folding 182 KB gzipped into `dashboard.json` would charge it to the daily surface, which
needs none of it, on every load.

What this file guards is mostly what the catalogue must NOT say. It carries no computed
figure, so the ways it can be wrong are all ways of overstating what is known: an empty
list where the engine failed to load, a zero price where the export had none, a count
that disagrees with the list beside it, and — the one with the measurable cost — an order
that changes between two runs over identical data.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

import src.engine.run as run_mod
from src.engine.catalogue import build_catalogue, validate_catalogue, write_catalogue
from src.engine.publish import PublishRefused
from src.owner_state.model import OwnerState

VINTAGES = {"pos": {"file": "yomyom-inventory.csv", "as_of": "2026-06-06",
                    "as_of_source": "declared_sidecar"}}


def row(barcode, name, **over):
    base = {"barcode": barcode, "product_name": name, "department": "מכולת",
            "shelf_price": 9.9, "delivery_price": None, "cost_price": 5.0,
            "cost_source": "pos", "recorded_stock": 3.0, "has_identifier": barcode is not None}
    base.update(over)
    return base


def built(products, **over):
    kwargs = {"generated_at": "2026-09-16T02:00:00+00:00", "inputs_digest": "abc123",
              "vintages": VINTAGES, "population": "whole"}
    kwargs.update(over)
    return build_catalogue(products, **kwargs)


# ── Absence ──────────────────────────────────────────────────────────────────

def test_products_that_could_not_be_loaded_are_absent_not_empty():
    """`[]` is a claim — "the store has no products". `None` is what actually happened."""
    cat = built(None)
    assert cat["products"] is None and cat["count"] is None
    validate_catalogue(cat)


def test_an_empty_store_is_allowed_to_say_so():
    """The mirror of the above, and the reason `count` has no `minimum: 1` unlike the
    device register: here the engine DID load the population and it was empty. That is a
    fact it is entitled to state."""
    cat = built([])
    assert cat["products"] == [] and cat["count"] == 0
    validate_catalogue(cat)


def test_a_count_without_a_list_is_refused():
    cat = built([row("1", "a")])
    cat["count"] = None
    with pytest.raises(PublishRefused, match="absent together"):
        validate_catalogue(cat)


def test_a_list_without_a_count_is_refused():
    cat = built(None)
    cat["products"] = [row("1", "a")]
    with pytest.raises(PublishRefused, match="absent together"):
        validate_catalogue(cat)


# ── Determinism: the argument the "git stores it once" claim rests on ────────

def test_the_order_is_total_so_two_runs_cannot_disagree():
    """Sorting is not cosmetic here. The nightly COMMITS this file; if the order varied
    between runs over identical data, every commit would carry the whole 1.73 MB.

    A sort is only deterministic if its key is unique — `sorted` is stable, so equal keys
    keep INPUT order, and input order is whatever the parquet reader produced. ADR-022
    makes the key unique by grouping barcode-less rows by name, so there is exactly one
    row per (barcode, name). This asserts the property rather than the sort call.
    """
    products = [row("3", "c"), row(None, "z"), row("1", "a"), row(None, "b")]
    keys = [(str(p["barcode"] or ""), p["product_name"]) for p in built(products)["products"]]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys), "sort key is not unique; order would depend on input order"


def test_the_same_products_in_a_different_order_serialise_identically():
    forward = built([row("1", "a"), row("2", "b"), row("3", "c")])
    backward = built([row("3", "c"), row("2", "b"), row("1", "a")])
    assert json.dumps(forward["products"], sort_keys=True) == json.dumps(backward["products"], sort_keys=True)


# ── What it may not overstate ────────────────────────────────────────────────

def test_a_missing_price_stays_null_and_never_becomes_zero():
    """D-3. A zero shelf price reads as free, which is a claim about the product rather
    than about the export."""
    cat = built([row("1", "a", shelf_price=None, cost_price=None, delivery_price=None)])
    p = cat["products"][0]
    assert p["shelf_price"] is None and p["cost_price"] is None and p["delivery_price"] is None
    validate_catalogue(cat)


def test_negative_stock_is_published_raw():
    """F2's whole subject. Clamping it to zero here would hide the thing the reconciliation
    and hygiene capabilities exist to report."""
    cat = built([row("1", "a", recorded_stock=-716.0)])
    assert cat["products"][0]["recorded_stock"] == -716.0


def test_no_product_row_carries_a_money_figure_derived_from_stock():
    """D-1, and CLAUDE.md rule 8: signals derived from stock quantities carry no shekel
    figure. Prices are the product's own attributes; a value computed FROM the count is not,
    and this file must not become the place one appears."""
    p = built([row("1", "a")])["products"][0]
    assert set(p) <= {"barcode", "product_name", "department", "shelf_price", "delivery_price",
                      "cost_price", "cost_source", "recorded_stock", "has_identifier"}


def test_a_row_the_schema_rejects_is_refused_before_anything_is_written(tmp_path):
    """ADR-005's rule applied to this file: the previous catalogue survives a bad run.
    The three pages would rather show yesterday's list than a broken one."""
    target = tmp_path / "catalogue.json"
    target.write_text('{"kept": true}', encoding="utf-8")
    bad = built([row("1", "a", shelf_price="free")])
    with pytest.raises(PublishRefused, match="violates schema"):
        write_catalogue(bad, path=target)
    assert json.loads(target.read_text()) == {"kept": True}


# ── The seam: one run, two files ─────────────────────────────────────────────

def test_the_digest_ties_the_catalogue_to_the_artefact_that_shipped_with_it():
    """The pages fetch the two files separately, and a failed catalogue write leaves a
    stale one beside a fresh artefact. Carrying the digest is what makes that detectable
    by a reader instead of invisible."""
    cat = built([row("1", "a")], inputs_digest="deadbeef")
    assert cat["inputs_digest"] == "deadbeef"
    assert cat["pos"] == VINTAGES["pos"]


def test_a_full_run_publishes_both_files_from_one_run(tmp_path, monkeypatch):
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: OwnerState.unavailable("no_credentials"))
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "SILVER_DIR", tmp_path / "silver")
    monkeypatch.setattr(run_mod, "SIGNALS_DIR", tmp_path / "signals")
    monkeypatch.setattr(run_mod, "MATCHES_PATH", tmp_path / "matches.parquet")

    target = tmp_path / "dashboard.json"
    result = run_mod.run_engine(mode="publish", artefact_path=target, capability_runners={},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))

    assert result["published"] is True
    catalogue_path = tmp_path / "catalogue.json"
    assert catalogue_path.exists(), "the catalogue must land beside the artefact, not in public/data/"
    artefact = json.loads(target.read_text())
    catalogue = json.loads(catalogue_path.read_text())
    assert catalogue["inputs_digest"] == artefact["inputs_digest"]
    assert catalogue["generated_at"] == artefact["generated_at"]
    assert catalogue["population"] == artefact["population"]
    assert any(s["step"] == "catalogue" and s["status"] == "ok" for s in result["steps"])


def test_print_mode_writes_no_catalogue(tmp_path, monkeypatch):
    """Reproduction must write nothing at all — ADR-002. The artefact half is already
    asserted in test_run.py; this is the other file."""
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: OwnerState.unavailable("no_credentials"))
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "SILVER_DIR", tmp_path / "silver")
    monkeypatch.setattr(run_mod, "SIGNALS_DIR", tmp_path / "signals")
    monkeypatch.setattr(run_mod, "MATCHES_PATH", tmp_path / "matches.parquet")

    run_mod.run_engine(mode="print", artefact_path=tmp_path / "dashboard.json",
                       capability_runners={}, now=datetime(2026, 9, 8, tzinfo=timezone.utc))

    assert not (tmp_path / "catalogue.json").exists()


def test_a_failing_catalogue_does_not_unpublish_the_artefact(tmp_path, monkeypatch):
    """The artefact is the owner's daily screen; the catalogue serves three secondary
    pages. A run that cannot write the second must still have delivered the first, and
    must say so rather than swallow it."""
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: OwnerState.unavailable("no_credentials"))
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "SILVER_DIR", tmp_path / "silver")
    monkeypatch.setattr(run_mod, "SIGNALS_DIR", tmp_path / "signals")
    monkeypatch.setattr(run_mod, "MATCHES_PATH", tmp_path / "matches.parquet")

    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(run_mod, "write_catalogue", boom)

    target = tmp_path / "dashboard.json"
    result = run_mod.run_engine(mode="publish", artefact_path=target, capability_runners={},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))

    assert result["published"] is True and target.exists()
    step = next(s for s in result["steps"] if s["step"] == "catalogue")
    assert step["status"] == "error" and "disk full" in step["error"]


def test_the_catalogue_carries_no_competitor_price():
    """Both prices in this file are the STORE'S OWN: `shelf_price` is its shelf,
    `delivery_price` is its own Wolt listing (`wolt_price` from its POS export). F1 exists
    because those two disagree; F3 compares against rivals and is computed from scraped
    `observations`, which never reach this file.

    Asserted at the contract rather than left to each reader, because the mistake is cheap
    to make and expensive to see: mapping `delivery_price` onto a competitor field lights a
    price-comparison page instantly and tells the owner a rival is undercutting him with his
    own price. Caught in review of the first adapter written against this schema.
    """
    p = built([row("1", "a", delivery_price=7.5)])["products"][0]
    assert p["delivery_price"] == 7.5
    banned = {"competitor", "competitor_price", "cheapestCompetitorPrice",
              "cheapest_competitor_price", "rival_price", "market_price"}
    assert not (set(p) & banned)
    # and the schema says so where an adapter author will read it
    schema = json.loads(Path("schemas/catalogue.schema.json").read_text(encoding="utf-8"))
    described = schema["properties"]["products"]["items"]["properties"]["delivery_price"]["description"]
    assert "STORE'S OWN" in described and "competitor_position" in described
