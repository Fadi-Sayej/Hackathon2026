# tests/engine/test_competitor_position.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, match, observation, product
from src.engine.competitor_position import balanced_reference, measure_format_allowance, run

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
    assert out.counts["purchase_cost_findings"] == 1 and out.counts["breaches"] == 0


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
    out = run(_inputs(prods, obs, [match("bisli_001", "bisli_001", "rami-levy-pt-01"), match("bisli_001", "bisli_001", "dor-alon-kq-01")]))
    e = out.entries[0]
    assert e.characterisation == "policy_breach_attention" and e.attention == "today"
    assert e.evidence["reference"]["kind"] == "midpoint" and e.evidence["premium_pct"] > 100
    assert e.value is None and e.action == "review_policy"


def test_a_breach_between_the_two_thresholds_is_unhurried_review():
    prods = [product("product_p", shelf=17.0, cost=5.0)]
    obs = [observation("product_p", 10.0, "rami-levy-pt-01", **SUPER, observed_at=FRESH),
           observation("product_p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("product_p", "product_p", "rami-levy-pt-01"), match("product_p", "product_p", "dor-alon-kq-01")]))
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
    e = run(_inputs(prods, obs, [match("product_p", "product_p", "rami-levy-pt-01"), match("product_p", "product_p", "dor-alon-kq-01")])).entries[0]
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
