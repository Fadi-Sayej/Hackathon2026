"""
T4 / #49 Step 5 — validation against a store whose truth we own.

This is the number the project would quote to an outsider ("we infer competitor
availability at X%, measured against a store whose truth we know"), so the ways
it can be quietly wrong matter more than the happy path:

  * an empty universe scores 1.000 over nothing
  * a barcode join that silently misses reduces the test to a handful of rows
  * a single day makes the rule predict everything, which reads as perfect recall
  * stale ground truth produces a confident number about a shelf from June
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import polars as pl  # noqa: E402

from src.market.labelled_store import (  # noqa: E402
    _is_our_venue,
    load_pos_stock,
    normalise_barcode,
    validate,
)


def write_inventory(tmp_path, rows, imported_at="2026-06-06T15:32:59+00:00"):
    pl.DataFrame([
        {"barcode": b, "current_stock": q, "_imported_at": imported_at}
        for b, q in rows
    ]).write_parquet(tmp_path / "inventory.parquet")
    return tmp_path


# ---------------------------------------------------------------------------
# Reading the POS truth
# ---------------------------------------------------------------------------

def test_a_duplicate_barcode_counts_as_in_stock_if_any_row_has_stock(tmp_path):
    """The same item sold from two tills appears twice. One row reading zero does
    not mean the shelf is empty, and treating it that way would invent a stockout
    for every dual-till product in the store."""
    write_inventory(tmp_path, [("729001", 0), ("729001", 4)])
    stock, _ = load_pos_stock(tmp_path)
    assert stock["729001"] is True


def test_negative_stock_is_not_read_as_in_stock(tmp_path):
    """625 rows read negative — a POS artefact. It is not evidence of stock."""
    write_inventory(tmp_path, [("729002", -3)])
    stock, _ = load_pos_stock(tmp_path)
    assert stock["729002"] is False


def test_pos_barcodes_are_normalised_on_the_way_in(tmp_path):
    write_inventory(tmp_path, [("0729003", 5)])
    stock, _ = load_pos_stock(tmp_path)
    assert "729003" in stock


def test_the_import_date_travels_with_the_stock(tmp_path):
    write_inventory(tmp_path, [("729004", 1)])
    _, imported_at = load_pos_stock(tmp_path)
    assert str(imported_at).startswith("2026-06-06")


# ---------------------------------------------------------------------------
# Identifying our own venue
# ---------------------------------------------------------------------------

# ADR-036: our venue is the store's own entry in configs/store_types.yaml (`role: client`),
# matched by the delivery platform's venue id. It used to be matched by the name "Yom Yom",
# which would have made every other store's copy validate against a venue it does not own.
OURS = {"68e64a15ddc7ae17b6279458"}


@pytest.mark.parametrize("store_id", ["68e64a15ddc7ae17b6279458", " 68e64a15ddc7ae17b6279458 "])
def test_our_venue_is_recognised_by_its_id(store_id):
    assert _is_our_venue(store_id, OURS) is True


@pytest.mark.parametrize("store_id", [
    "689d9d1ea1357c9968d6850f",   # Super Alonit | Kibbutz Einat
    "65af9c58e895c470fe3eb763",   # Victory | Rosh Ha'ayin Park Afek
    "",
    None,
])
def test_other_venues_are_not_mistaken_for_ours(store_id):
    """A competitor counted as our store would validate inference against stock
    we do not own — a number that is wrong and looks fine."""
    assert _is_our_venue(store_id, OURS) is False


def test_a_venue_named_like_ours_is_not_ours_without_its_id():
    """Another store's copy may sit next to a venue called anything at all."""
    assert _is_our_venue("somebody-elses-id", OURS) is False


# ---------------------------------------------------------------------------
# Joining
# ---------------------------------------------------------------------------

def test_leading_zeros_do_not_break_the_join():
    """The POS and the delivery catalogue pad the same physical barcode
    differently. An unnormalised join drops most rows and the smaller sample
    still reports a confident score."""
    assert normalise_barcode("0729000012345") == normalise_barcode("729000012345")


def test_blank_barcodes_normalise_to_empty_and_are_droppable():
    for value in (None, "", "   ", "000"):
        assert normalise_barcode(value) == ""


def test_barcodes_the_pos_has_never_heard_of_are_reported_not_dropped_silently():
    result = validate(
        orderability={"2026-08-13": {"known", "mystery"}},
        stock={"known": True},
    )
    assert result.universe == 2
    assert result.matched_to_pos == 1
    assert result.unmatched_barcodes == ["mystery"]
    assert result.score.total == 1


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def test_precision_counts_products_offered_online_that_had_no_stock():
    result = validate(
        orderability={"2026-08-13": {"a", "b", "c", "d"}},
        stock={"a": True, "b": True, "c": True, "d": False},
    )
    assert result.score.precision == pytest.approx(0.75)
    assert result.score.false_positive == 1


def test_a_product_that_drops_off_and_was_out_of_stock_is_a_true_negative():
    """The case the whole harness exists for: the external signal disappeared,
    and the internal truth says it should have."""
    result = validate(
        orderability={
            "2026-08-12": {"a", "gone"},
            "2026-08-13": {"a"},              # `gone` stops being orderable
        },
        stock={"a": True, "gone": False},
    )
    assert result.score.true_negative == 1     # day 13: not offered, not in stock
    assert result.predicts_everything is False
    assert result.emission_orderable_given_out_of_stock == pytest.approx(0.5)


def test_a_single_day_is_flagged_as_not_a_test_of_inference():
    """With one day the universe IS that day's orderable set, so recall is 1.0
    by construction and both emissions collapse. Reporting that as accuracy
    would be the most flattering number in the project and the least true."""
    result = validate(
        orderability={"2026-08-13": {"a", "b"}},
        stock={"a": True, "b": False},
    )
    assert result.predicts_everything is True
    assert result.score.recall == 1.0
    assert result.emission_orderable_given_in_stock == 1.0
    assert result.emission_orderable_given_out_of_stock == 1.0
    assert result.to_dict()["predicts_everything"] is True


def test_an_empty_universe_reports_nothing_rather_than_a_perfect_score():
    result = validate(orderability={}, stock={"a": True})
    assert result.score is None
    assert result.universe == 0

    # And a universe the POS knows nothing about must not score either.
    result = validate(orderability={"2026-08-13": {"unknown"}}, stock={"a": True})
    assert result.score is None
    assert result.matched_to_pos == 0


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------

def test_staleness_of_the_ground_truth_is_computed_and_carried():
    result = validate(
        orderability={"2026-08-13": {"a"}},
        stock={"a": True},
        pos_imported_at="2026-06-06T15:32:59.781662+00:00",
        today=date(2026, 8, 13),
    )
    assert result.staleness_days == 68
    assert result.to_dict()["staleness_days"] == 68


def test_an_unparseable_import_date_leaves_staleness_unknown_not_zero():
    """Zero would read as "the truth is current", which is the one wrong answer."""
    result = validate(
        orderability={"2026-08-13": {"a"}},
        stock={"a": True},
        pos_imported_at="not a date",
    )
    assert result.staleness_days is None
