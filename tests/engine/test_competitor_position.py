# tests/engine/test_competitor_position.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from helpers import RUN_AT, make_inputs, match, observation, product
from src.engine.competitor_position import balanced_reference, measure_format_allowance, run
from src.engine.policy_breach import run as breach_run      # ADR-043: the breaches' own capability

# NOTE: identifiers are >= policy.uncomparable_min_barcode_digits (8) characters.
# A shorter one is structurally uncomparable under FR-052 — which is what "svc"
# (a car-wash service code) exists to exercise, and why it is left short.
FORECOURT = dict(store_format="gas_convenience", affinity=1.0)
SUPER = dict(store_format="supermarket", affinity=0.1)
FRESH = "2026-09-08T00:00:00Z"


def test_measure_format_allowance_is_the_median_of_products_holding_both():
    pct, n = measure_format_allowance([(10.0, 12.0), (10.0, 11.0), (10.0, 13.0)])   # (supermarket, same_format)
    assert pct == 20.0 and n == 3
    assert measure_format_allowance([]) == (None, 0)


def test_balanced_reference_prefers_the_midpoint():
    r = balanced_reference(same_format_min=4.9, supermarket_min=3.9, allowance_pct=20.0)
    assert r["value"] == 4.4 and r["kind"] == "midpoint"


def test_balanced_reference_falls_back_to_supermarket_plus_measured_allowance():
    r = balanced_reference(same_format_min=None, supermarket_min=10.0, allowance_pct=20.0)
    assert r["value"] == 12.0 and r["kind"] == "supermarket_plus_allowance"
    assert balanced_reference(None, 10.0, None) is None          # FR-044c: no invented number
    assert balanced_reference(None, None, 20.0) is None


def _inputs(products, observations, matches, **kw):
    return make_inputs(products=products, observations=observations, matches=matches, **kw)


def test_ac_049_ac_050_cost_floor_blocks_a_losing_recommendation():
    prods = [product("cheese_01", shelf=158.21, cost=147.11)]
    obs = [observation("cheese_01", 54.0, "rami-levy-pt-01", **SUPER, observed_at=FRESH),
           observation("cheese_01", 60.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("cheese_01", "cheese_01", "rami-levy-pt-01"), match("cheese_01", "cheese_01", "dor-alon-kq-01")]))
    kinds = {e.barcode: e.characterisation for e in out.entries}
    assert kinds["cheese_01"] == "purchase_cost"
    assert out.counts["purchase_cost_findings"] == 1
    breaches = breach_run(_inputs(prods, obs, [match("cheese_01", "cheese_01", "rami-levy-pt-01"), match("cheese_01", "cheese_01", "dor-alon-kq-01")]))
    assert breaches.counts["breaches"] == 0 and breaches.entries == []     # FR-043a/b: never both


def test_ac_051_no_cost_means_no_judgement():
    prods = [product("product_x", shelf=100.0, cost=None)]
    obs = [observation("product_x", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("product_x", "product_x", "dor-alon-kq-01")]))
    assert out.entries == [] and out.counts["no_cost_skipped"] == 1


def test_ac_054_a_breach_above_the_attention_threshold_is_same_day():
    # cost must clear the floor (cost x 1.10 = 4.40 < reference 6.75), or AC-049's
    # purchase-cost finding pre-empts the breach this test is about
    prods = [product("bisli_001", shelf=13.90, cost=4.00)]
    obs = [observation("bisli_001", 6.50, "rami-levy-pt-01", **SUPER, observed_at=FRESH),
           observation("bisli_001", 7.00, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = breach_run(_inputs(prods, obs, [match("bisli_001", "bisli_001", "rami-levy-pt-01"), match("bisli_001", "bisli_001", "dor-alon-kq-01")]))
    e = out.entries[0]
    assert e.characterisation == "policy_breach_attention" and e.attention == "today"
    assert e.evidence["reference"]["kind"] == "midpoint" and e.evidence["premium_pct"] > 100
    assert e.value is None and e.action == "review_policy"


def test_a_breach_between_the_two_thresholds_is_unhurried_review():
    prods = [product("product_p", shelf=17.0, cost=5.0)]
    obs = [observation("product_p", 10.0, "rami-levy-pt-01", **SUPER, observed_at=FRESH),
           observation("product_p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = breach_run(_inputs(prods, obs, [match("product_p", "product_p", "rami-levy-pt-01"), match("product_p", "product_p", "dor-alon-kq-01")]))
    assert out.entries[0].characterisation == "policy_breach_review" and out.entries[0].attention == "review"
    assert out.entries[0].evidence["policy_pct"] == 60


def test_ac_047a_a_difference_within_the_allowance_is_not_a_fault():
    prods = [product("product_q", shelf=11.5, cost=5.0)]
    obs = [observation("product_q", 10.0, "rami-levy-pt-01", **SUPER, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("product_q", "product_q", "rami-levy-pt-01")]))
    assert out.entries == []


def test_ac_042_every_entry_names_the_store_and_its_format():
    prods = [product("product_p", shelf=17.0, cost=5.0)]
    obs = [observation("product_p", 10.0, "rami-levy-pt-01", **SUPER, observed_at=FRESH, store_name="Rami Levy PT"),
           observation("product_p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH, store_name="Alonit KQ")]
    e = breach_run(_inputs(prods, obs, [match("product_p", "product_p", "rami-levy-pt-01"), match("product_p", "product_p", "dor-alon-kq-01")])).entries[0]
    sources = e.evidence["sources"]
    assert {s["format"] for s in sources} == {"supermarket", "gas_convenience"}
    assert all(s["store_name"] for s in sources)


def test_ac_045_no_comparison_is_not_a_zero_difference():
    prods = [product("alone_one", shelf=10.0, cost=5.0)]
    out = run(_inputs(prods, [], []))
    assert out.counts["no_comparison"] == 1 and out.entries == []


def test_ac_044_coverage_is_stated_against_the_full_catalogue():
    prods = [product("product_a", shelf=10.0, cost=5.0), product("svc", shelf=30.0, cost=None, name="שטיפת רכב"),
             product("product_b", shelf=10.0, cost=5.0)]
    obs = [observation("product_a", 9.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("product_a", "product_a", "dor-alon-kq-01")]))
    assert out.counts["catalogue"] == 3 and out.counts["matched"] == 1


def test_ac_048_stale_observations_drive_nothing():
    prods = [product("product_p", shelf=17.0, cost=5.0)]
    old = "2026-01-01T00:00:00Z"
    obs = [observation("product_p", 10.0, "rami-levy-pt-01", **SUPER, observed_at=old),
           observation("product_p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=old)]
    out = run(_inputs(prods, obs, [match("product_p", "product_p", "rami-levy-pt-01"), match("product_p", "product_p", "dor-alon-kq-01")]))
    assert out.entries == [] and out.counts["stale_skipped"] == 1


def test_ac_046_position_is_reportable_including_when_cheaper():
    prods = [product("product_a", shelf=9.0, cost=2.0), product("product_b", shelf=8.0, cost=2.0)]
    obs = [observation("product_a", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH),
           observation("product_b", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("product_a", "product_a", "dor-alon-kq-01"), match("product_b", "product_b", "dor-alon-kq-01")]))
    pos = {p["store_id"]: p for p in out.extras["position"]}["dor-alon-kq-01"]
    assert pos["cheaper_here"] == 2 and pos["median_diff_pct"] < 0


def test_no_observations_at_all_is_unavailable():
    out = run(_inputs([product("product_a", shelf=10.0, cost=5.0)], None, None))
    assert out.status == "unavailable" and out.unavailable_reason == "no_competitor_data"


# ── ADR-008's floor, which nothing in Python named until #91 ────────────────────────────
#
# `scripts/audit-store-format.mjs` was the only artefact guarding "no finding rests on a
# store format we are not comparable to". It ran the V2 reorder engine over the demo spine,
# both of which Phase 4 deletes, and it read the spine through a dynamic import() that the
# REMOVE-list grep could not see (#91).
#
# The rule itself is not going anywhere — the engine enforces it (`o["affinity"] >= floor`)
# and publishes `comparability_floor`. It is load-bearing to a degree worth stating: in the
# 2026-09-15 artefact, 161 of 164 observed stores sit BELOW the 0.3 floor. These two tests
# are what the script's guarantee becomes, so deleting it drops no invariant.

BELOW_FLOOR = dict(store_format="supermarket", affinity=0.1)   # 0.1 < min_affinity 0.3


def test_a_store_below_the_affinity_floor_cannot_drive_a_finding():
    """The one thing that must never happen (ADR-008, F3). A price from a format we are not
    comparable to may inform context; it may not produce a judgement about the owner."""
    prods = [product("bisli_001", shelf=13.90, cost=4.00)]
    obs = [observation("bisli_001", 6.50, "rami-levy-pt-01", **BELOW_FLOOR, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("bisli_001", "bisli_001", "rami-levy-pt-01")]))

    assert out.entries == [], "a below-floor store produced a finding"
    assert out.counts["evaluated"] == 0
    assert breach_run(_inputs(prods, obs, [match("bisli_001", "bisli_001", "rami-levy-pt-01")])).counts["breaches"] == 0
    # it is still reported, as context — excluded is not the same as unseen
    roles = {p["store_id"]: p.get("role") for p in out.extras["position"]}
    assert roles.get("rami-levy-pt-01") != "comparable"


def test_the_same_price_from_a_comparable_store_does_produce_one():
    """Guards the test above against passing vacuously: identical numbers, affinity 1.0."""
    prods = [product("bisli_001", shelf=13.90, cost=4.00)]
    obs = [observation("bisli_001", 6.50, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("bisli_001", "bisli_001", "dor-alon-kq-01")]))

    assert out.counts["evaluated"] == 1
    assert [e.characterisation for e in breach_run(_inputs(prods, obs, [match("bisli_001", "bisli_001", "dor-alon-kq-01")])).entries] == ["policy_breach_attention"]


# ── The comparison behind the findings (#137) ────────────────────────────────
#
# Six findings reach the owner from 860 evaluated products. The other 854 were compared
# against a live reference and found acceptably priced, and that comparison was computed and
# dropped at the publish boundary. A page answering "what is this product's position" needs
# the comparison, not the finding — which is why PriceGapPage sat on an awaiting state.
#
# Every MATCHED product gets a row. A row carries either the comparison or the reason there
# is none; never silence. Publishing only the evaluated ones would make the page say nothing
# for a product skipped as stale, which the owner reads as "no competitor sells this" —
# rule 8 and D-3, one layer out.

def test_every_matched_product_gets_a_row():
    prods = [product("prod_0001", shelf=10.0, cost=4.0), product("prod_0002", shelf=12.0, cost=5.0)]
    obs = [observation("prod_0001", 9.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH),
           observation("prod_0002", 11.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match(b, b, "dor-alon-kq-01") for b in ("prod_0001", "prod_0002")]))
    assert len(out.extras["comparison"]) == out.counts["matched"] == 2


def test_a_row_carries_either_a_comparison_or_a_reason_never_neither():
    """The invariant the page depends on. A row with no premium and no reason is the silence
    this exists to remove: the owner cannot tell 'priced fine' from 'we could not check'."""
    codes = ("priced_01", "nocost_01", "noshelf_01")
    prods = [product("priced_01", shelf=10.0, cost=4.0),
             product("nocost_01", shelf=10.0, cost=None),
             product("noshelf_01", shelf=None, cost=4.0)]
    obs = [observation(b, 9.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH) for b in codes]
    out = run(_inputs(prods, obs, [match(b, b, "dor-alon-kq-01") for b in codes]))
    assert len(out.extras["comparison"]) == 3
    for row in out.extras["comparison"]:
        assert (row["premium_pct"] is not None) or (row["uncompared_reason"] is not None), row


def test_no_cost_still_publishes_the_position():
    """FR-043d withholds the JUDGEMENT without a cost, not the comparison. The reference is
    known; only the policy verdict is unsafe. Publishing it lets the page show where he
    stands without claiming he is in breach."""
    prods = [product("nocost_01", shelf=10.0, cost=None)]
    obs = [observation("nocost_01", 8.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("nocost_01", "nocost_01", "dor-alon-kq-01")]))
    row = out.extras["comparison"][0]
    assert row["uncompared_reason"] == "no_cost"
    assert row["reference"] is not None and row["premium_pct"] is not None
    assert out.entries == []                       # and still no finding, which AC-051 requires


def test_no_shelf_price_and_no_reference_are_different_facts():
    """Both leave the product uncompared and they are not the same thing to a reader: one is
    a gap in our own data, the other is that nobody comparable sells it."""
    prods = [product("noshelf_01", shelf=None, cost=4.0)]
    obs = [observation("noshelf_01", 9.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("noshelf_01", "noshelf_01", "dor-alon-kq-01")]))
    assert out.extras["comparison"][0]["uncompared_reason"] == "no_shelf_price"


def test_the_row_carries_no_product_name_or_department():
    """catalogue.json (ADR-024) holds those against the same barcode, and a page rendering
    this needs that file anyway. Measured: carrying them here too costs 39 KB gzipped for a
    second copy of the truth — what §20.1 deleted src/data/*.js for."""
    prods = [product("prod_0001", shelf=10.0, cost=4.0)]
    obs = [observation("prod_0001", 9.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("prod_0001", "prod_0001", "dor-alon-kq-01")]))
    assert set(out.extras["comparison"][0]) == {
        "barcode", "shelf_price", "stores", "observed_at", "reference", "premium_pct",
        "uncompared_reason"}


def test_the_comparison_is_sorted_by_barcode():
    """The nightly commits this file, so the bytes must repeat when the data does — ADR-024's
    reasoning, and ADR-021's before it."""
    codes = ("prod_0003", "prod_0001", "prod_0002")
    prods = [product(b, shelf=10.0, cost=4.0) for b in codes]
    obs = [observation(b, 9.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH) for b in codes]
    out = run(_inputs(prods, obs, [match(b, b, "dor-alon-kq-01") for b in codes]))
    published = [r["barcode"] for r in out.extras["comparison"]]
    assert published == sorted(published) == ["prod_0001", "prod_0002", "prod_0003"]


def test_the_published_premium_matches_the_entry_it_produced():
    """One number, one place. If the row and the finding could disagree, the page and the
    daily surface would disagree about the same product — the failure credibility.js's own
    header warns about."""
    prods = [product("dearone1", shelf=100.0, cost=10.0)]
    obs = [observation("dearone1", 50.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("dearone1", "dearone1", "dor-alon-kq-01")]))
    entry = next(e for e in breach_run(_inputs(prods, obs, [match("dearone1", "dearone1", "dor-alon-kq-01")])).entries
                 if e.barcode == "dearone1")
    row = next(r for r in out.extras["comparison"] if r["barcode"] == "dearone1")
    assert row["premium_pct"] == entry.evidence["premium_pct"]


# ── A product seen only in stale observations (SCN-047) ─────────────────────
#
# F3-S1 SCN-047: GIVEN the newest observation for a product is older than the freshness
# bound, THEN it is not surfaced as a recommendation, AND any display marks the
# observation's age. Such a product used to get no comparison row, so no display could mark
# anything, and the page would have read it as "no competitor sells this". The count beside
# it was wrong in the other direction: `stale_skipped` counted every stale barcode in the
# competitor feed. On 2026-09-23 it read 1,085 where it now reads 53 — 1,028 of them were
# barcodes the store does not sell.

OLD = "2026-08-01T00:00:00Z"               # 38 days before RUN_AT; freshness_days is 14


def test_scn_047_a_product_seen_only_in_stale_observations_gets_a_row_saying_so():
    prods = [product("product_p", shelf=17.0, cost=5.0)]
    obs = [observation("product_p", 10.0, "rami-levy-pt-01", **SUPER, observed_at=OLD),
           observation("product_p", 11.0, "dor-alon-kq-01", **FORECOURT, observed_at="2026-08-20T09:30:00Z")]
    out = run(_inputs(prods, obs, [match("product_p", "product_p", s) for s in ("rami-levy-pt-01", "dor-alon-kq-01")]))
    assert out.entries == []
    # Dated by the NEWEST of the stale prices: the age a display marks is how recent the
    # best evidence is, not how old the worst of it is.
    assert out.extras["comparison"] == [{
        "barcode": "product_p", "shelf_price": 17.0, "stores": 2, "observed_at": "2026-08-20",
        "reference": None, "premium_pct": None, "uncompared_reason": "stale"}]
    assert out.counts["stale_skipped"] == 1 and out.counts["matched"] == 0


@pytest.mark.parametrize("barcode, extra, withdrawn", [
    ("notours_1", [], None),                                                        # the store does not sell it
    ("svc", [product("svc", shelf=30.0, cost=None, name="שטיפת רכב")], None),       # structurally uncomparable, FR-052
    ("gone_0001", [product("gone_0001", shelf=9.0, cost=3.0)], {"gone_0001"}),      # withdrawn, FR-074
], ids=["not-in-catalogue", "structurally-uncomparable", "withdrawn"])
def test_stale_skipped_counts_only_the_stores_comparable_products(barcode, extra, withdrawn):
    """Published with unit 'products', beside the catalogue it is a share of."""
    obs = [observation("product_p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=OLD),
           observation(barcode, 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=OLD)]
    out = run(_inputs([product("product_p", shelf=17.0, cost=5.0)] + extra, obs, [], withdrawn=withdrawn))
    assert out.counts["stale_skipped"] == 1
    assert [r["barcode"] for r in out.extras["comparison"]] == ["product_p"]


def test_a_stale_product_with_no_shelf_price_names_our_own_gap_and_keeps_its_date():
    """Both are true and a row carries one reason. Ours comes first, as it does for a matched
    product (no_shelf_price before no_reference), because it is the one the owner can fix.
    The date stays on the row either way: SCN-047 asks any display to mark the age."""
    prods = [product("noshelf_01", shelf=None, cost=4.0)]
    obs = [observation("noshelf_01", 9.0, "dor-alon-kq-01", **FORECOURT, observed_at=OLD)]
    out = run(_inputs(prods, obs, []))
    row = out.extras["comparison"][0]
    assert (row["uncompared_reason"], row["observed_at"], row["stores"]) == ("no_shelf_price", "2026-08-01", 1)
    assert out.counts["stale_skipped"] == 0 and out.counts["no_comparison"] == 1


def test_one_fresh_price_is_a_comparison_made_on_the_fresh_price_alone():
    """Only a product whose EVERY observation is stale is marked stale. With one fresh price
    it is matched, and a stale price beside it must not reach the reference, the shop count or
    the date. 10.00 against the fresh 9.00 is +11.11%; the stale 1.00 would move all three."""
    prods = [product("product_p", shelf=10.0, cost=4.0)]
    obs = [observation("product_p", 9.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH),
           observation("product_p", 1.0, "rami-levy-pt-01", **SUPER, observed_at=OLD)]
    out = run(_inputs(prods, obs, [match("product_p", "product_p", s) for s in ("dor-alon-kq-01", "rami-levy-pt-01")]))
    row = out.extras["comparison"][0]
    assert (row["uncompared_reason"], row["premium_pct"], row["stores"], row["observed_at"]) == (None, 11.11, 1, "2026-09-08")
    assert out.counts["matched"] == 1 and out.counts["stale_skipped"] == 0


def test_an_undated_observation_is_never_called_stale():
    """`_fresh` refuses an observation with no date, and it should: it cannot drive a finding.
    But "too old" is a claim about its age, and its age is unknown. None of the 526,437
    observations in the 2026-09-23 feed is undated; this is here so the first one is not
    published as a fact about an age nobody measured."""
    prods = [product("product_p", shelf=17.0, cost=5.0)]
    obs = [observation("product_p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=None)]
    out = run(_inputs(prods, obs, []))
    assert out.extras["comparison"] == [] and out.counts["stale_skipped"] == 0


def test_scn_047_the_stale_row_and_its_count_reach_the_published_artefact(tmp_path, monkeypatch):
    """Rule 12. Every test above hands `run` its input; this one runs the engine and the
    publisher and reads what the owner's browser reads: the row, the count, and the figure
    of the same name that the Data page renders."""
    import src.engine.run as run_mod
    inputs = make_inputs(products=[product("product_p", shelf=17.0, cost=5.0)],
                         observations=[observation("product_p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=OLD),
                                       observation("notours_1", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=OLD)],
                         matches=[])
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: inputs.owner)
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: None)
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "load_inputs", lambda **kw: inputs)
    art = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json", now=RUN_AT)["artefact"]
    cp = art["capabilities"]["competitor_position"]
    assert cp["status"] == "available"
    assert [(r["barcode"], r["uncompared_reason"], r["observed_at"]) for r in cp["comparison"]] == [
        ("product_p", "stale", "2026-08-01")]
    assert cp["counts"]["stale_skipped"] == 1
    assert art["figures"]["competitor_position.stale_skipped"]["value"] == 1


# ── ADR-043: the breaches are their own capability, waiting for the owner's rule (D-39) ──

BREACH_KEYS = ("breaches", "attention", "review")


def _one_breach(**kw):
    prods = [product("product_p", shelf=17.0, cost=5.0), product("cheese_01", shelf=158.21, cost=147.11)]
    obs = [observation("product_p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH),
           observation("cheese_01", 54.0, "rami-levy-pt-01", **SUPER, observed_at=FRESH),
           observation("cheese_01", 60.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    return _inputs(prods, obs, [match("product_p", "product_p", "dor-alon-kq-01"),
                                match("cheese_01", "cheese_01", "rami-levy-pt-01"),
                                match("cheese_01", "cheese_01", "dor-alon-kq-01")], **kw)


def test_the_comparison_and_the_purchase_cost_check_need_no_rule():
    out = run(_one_breach(price_rule=None))
    assert out.status == "available"
    assert [e.characterisation for e in out.entries] == ["purchase_cost"]
    assert not set(BREACH_KEYS) & set(out.counts)
    assert "policy_pct" not in out.thresholds and "attention_pct" not in out.thresholds
    assert {r["barcode"] for r in out.extras["comparison"]} == {"product_p", "cheese_01"}


def test_without_the_owners_rule_the_breaches_wait_for_it():
    out = breach_run(_one_breach(price_rule=None))
    assert (out.status, out.unavailable_reason) == ("unavailable", "no_price_rule")


def test_the_breaches_keep_their_family_ids_and_the_rule_they_were_judged_by():
    from helpers import PRICE_RULE
    from src.engine.model import entry_id
    out = breach_run(_one_breach())
    (e,) = out.entries
    assert (e.capability, e.signal_family) == ("policy_breach", "competitor.policy_breach")
    assert e.id == entry_id("competitor.policy_breach", "product_p")     # ADR-009: outcomes still attach
    assert list(out.counts) == list(BREACH_KEYS) and out.counts["breaches"] == 1
    assert out.thresholds == {"policy_pct": 60.0, "attention_pct": 100.0}
    assert out.extras["rule"] == PRICE_RULE


def test_the_breaches_are_judged_by_the_owners_rule_not_a_default():
    from helpers import PRICE_RULE
    looser = {**PRICE_RULE, "max_premium_pct": 80.0}                     # product_p is +70%
    assert breach_run(_one_breach(price_rule=looser)).entries == []
