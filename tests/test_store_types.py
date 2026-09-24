"""
Store identity / format affinity — the guarantees that keep a hypermarket price
from being presented to a forecourt shop as if it were comparable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.store_types import UNKNOWN, load_store_types

CONFIG = load_store_types()


# ── The config itself ─────────────────────────────────────────────────────────

def test_our_store_is_classified_and_human_verified():
    """Every affinity lookup starts here. A guess at this anchor poisons everything."""
    record = CONFIG.store("yomyom-kq-01")
    assert record is not None
    assert record.store_type == "gas_convenience"
    assert record.is_verified


def test_affinity_matrix_covers_every_format_in_both_directions():
    for our_type in CONFIG.formats:
        for their_type in CONFIG.formats:
            value = CONFIG.affinity(our_type, their_type)
            assert 0.0 <= value <= 1.0, f"{our_type}->{their_type} = {value}"


def test_same_format_is_always_a_perfect_match():
    for fmt in CONFIG.formats:
        assert CONFIG.affinity(fmt, fmt) == 1.0


def test_sku_ranges_do_not_overlap():
    bounds = sorted(
        (meta["typical_sku_range"][0], meta["typical_sku_range"][1], name)
        for name, meta in CONFIG.formats.items()
    )
    for (_, prev_hi, prev_name), (next_lo, _, next_name) in zip(bounds, bounds[1:]):
        assert prev_hi < next_lo, f"{prev_name} and {next_name} overlap — inference would be ambiguous"


# ── The rule the whole track exists for ───────────────────────────────────────

def test_a_hypermarket_is_never_comparable_to_a_forecourt_shop():
    assert CONFIG.affinity("gas_convenience", "hypermarket") == 0.0


def test_shufersal_deal_is_excluded_for_our_store():
    excluded = CONFIG.excluded_stores(CONFIG.store_type("yomyom-kq-01"))
    assert "shufersal-pt-01" in excluded


def test_comparable_stores_never_includes_a_zero_affinity_branch():
    our_type = CONFIG.store_type("yomyom-kq-01")
    for store_id in CONFIG.comparable_stores(our_type):
        assert CONFIG.affinity(our_type, CONFIG.store_type(store_id)) > 0.0


def test_comparable_stores_is_ordered_most_comparable_first():
    our_type = "gas_convenience"
    ordered = CONFIG.comparable_stores(our_type)
    affinities = [CONFIG.affinity(our_type, CONFIG.store_type(s)) for s in ordered]
    assert affinities == sorted(affinities, reverse=True)


def test_comparable_stores_respects_min_affinity():
    our_type = "gas_convenience"
    strict = CONFIG.comparable_stores(our_type, min_affinity=1.0)
    for store_id in strict:
        assert CONFIG.store_type(store_id) == "gas_convenience"
    assert set(strict) <= set(CONFIG.comparable_stores(our_type))


def test_the_nearest_forecourt_shop_outranks_the_supermarket():
    """Distance is not comparability. Alonit is 1.4 km away and Rami Levy 2.1 km,
    but the point is the format, not the metres."""
    our_type = "gas_convenience"
    assert CONFIG.store_affinity("yomyom-kq-01", "dor-alon-kq-01") > CONFIG.store_affinity(
        "yomyom-kq-01", "rami-levy-pt-01"
    )
    assert CONFIG.affinity(our_type, "gas_convenience") == 1.0


# ── Unknown must never read as comparable ─────────────────────────────────────

def test_unclassified_branch_resolves_to_unknown_not_to_a_match():
    assert CONFIG.store_type("no-such-branch-99") == UNKNOWN
    assert CONFIG.affinity("gas_convenience", UNKNOWN) < CONFIG.min_affinity


def test_unknown_cannot_drive_a_recommendation():
    """Below min_affinity, so it is context at most — never the basis of an action."""
    assert CONFIG.affinity("gas_convenience", UNKNOWN) < CONFIG.min_affinity


def test_unrecognised_format_falls_back_to_unknown_rather_than_one():
    assert CONFIG.affinity("gas_convenience", "pop_up_stall") < 1.0
    assert CONFIG.affinity("not_a_format", "hypermarket") < 1.0


# ── Inference (Step 3) ────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "skus,expected",
    [
        (800, "gas_convenience"),
        (2500, "urban_minimarket"),
        (7000, "midsize_grocery"),
        (16547, "supermarket"),   # kaggle_dor_alon
        (21849, "supermarket"),   # kaggle_rami_levy
        (22759, "supermarket"),   # kaggle_shufersal
        (40000, "hypermarket"),
    ],
)
def test_infer_store_type_maps_sku_count_to_format(skus, expected):
    fmt, confidence = CONFIG.infer_store_type(skus)
    assert fmt == expected
    assert 0.0 < confidence < 1.0, "an inference is never as good as a verified fact"


def test_inference_refuses_a_partial_scrape():
    """A 27-SKU Wolt scrape of a Shufersal branch must NOT come back as a forecourt
    shop. That single mistake reintroduces the exact bug this module prevents."""
    fmt, confidence = CONFIG.infer_store_type(27)
    assert fmt == UNKNOWN
    assert confidence == 0.0


def test_inference_never_returns_a_verified_classification():
    for skus in (500, 3000, 8000, 15000, 30000, 5, None):
        _, confidence = CONFIG.infer_store_type(skus)
        assert confidence < 1.0


# ── Manual vs machine must stay distinguishable ───────────────────────────────

def test_every_store_records_how_it_was_classified():
    for store_id, record in CONFIG.stores.items():
        assert record.verified in ("manual", "proposed", "inferred"), store_id


def test_manual_and_machine_classifications_stay_distinguishable():
    """Asserted on constructed records, not on the live config: every branch there
    happens to be decided today, and that must not be what makes this pass."""
    from src.common.store_types import StoreRecord

    decided = StoreRecord("a", "gas_convenience", verified="manual", basis="branch_known")
    guessed = StoreRecord("b", "gas_convenience", verified="inferred", basis="sku_count")
    assert decided.is_verified and not guessed.is_verified


def test_a_decided_classification_still_records_whether_it_is_first_hand():
    """`manual` means nobody may overwrite it. It does not mean anyone visited the
    branch, and conflating the two is how desk knowledge becomes false certainty."""
    from src.common.store_types import StoreRecord

    desk = StoreRecord("c", "supermarket", verified="manual", basis="chain_format")
    assert desk.is_verified
    assert not desk.is_first_hand


def test_our_own_two_forecourt_shops_are_known_first_hand():
    """Everything hangs off these two: our store, and the only source at affinity
    1.0. A chain-format guess at either would tilt the whole product."""
    for store_id in ("yomyom-kq-01", "dor-alon-kq-01"):
        assert CONFIG.store(store_id).is_first_hand, store_id


def test_every_decided_store_records_what_the_decision_rests_on():
    for store_id, record in CONFIG.stores.items():
        if record.is_verified:
            assert record.basis in ("branch_known", "chain_format"), store_id


def test_the_static_store_ids_stay_classified():
    """Our store and the three static chains keep their classification. The Kaggle chain and
    the exporter that first defined these ids were removed on 2026-09-24; the ids live on in
    this config and src/common/store_types.py, so losing one would make a chain `unknown`."""
    for store_id in ("yomyom-kq-01", "dor-alon-kq-01", "rami-levy-pt-01", "shufersal-pt-01"):
        assert CONFIG.store(store_id) is not None, f"{store_id} lost its classification"
        assert CONFIG.store(store_id).is_verified


def test_client_stores_are_never_references():
    cfg = load_store_types()
    assert set(cfg.client_store_ids()) == {"yomyom-kq-01", "68e64a15ddc7ae17b6279458"}


def test_einat_venue_is_classified_same_format():
    cfg = load_store_types()
    assert cfg.store_type("689d9d1ea1357c9968d6850f") == "gas_convenience"


def test_context_only_and_comparable_partition_the_non_excluded():
    cfg = load_store_types()
    ctx = set(cfg.context_only_stores("gas_convenience"))
    comp = set(cfg.comparable_stores("gas_convenience"))
    assert ctx.isdisjoint(comp)
    assert "rami-levy-pt-01" in ctx and "dor-alon-kq-01" in comp
