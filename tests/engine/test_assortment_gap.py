# tests/engine/test_assortment_gap.py
"""Phase 6 Task 6.2: the `assortment_gap` capability (F9-S1 FR-165 … FR-170, FR-172, FR-174).

The inputs are what Task 6.1's replay publishes, written out by hand so each §5 term is
visible in the fixture: which nights flagged a product, which stores, and whether a market
store listed it recently or tonight.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product
from src.engine import assortment_gap
from src.engine.registry import CAPABILITIES, INPUT_REASONS, UNVALUED_CAPABILITIES
from src.engine.surface_candidates import REQUIRED_EVIDENCE

TONIGHT = "2026-09-28"
SIGNAL = {"on_day": TONIGHT, "stores": ["w", "r"], "excluded": [], "products": {
    "7290001": {"stores_out": ["w"], "days_absent": {"w": 3}},     # running out tonight
    "7290009": {"stores_out": ["w"], "days_absent": {"w": 2}},     # in his catalogue
}}


def recent(**flagged_over):
    flagged = {
        # running out tonight, not listed anywhere tonight, listed three days ago
        "7290001": {"nights": ["2026-09-27", TONIGHT], "stores": ["w"]},
        # ran out on four nights last week at two stores, back on both
        "7290002": {"nights": ["2026-09-20", "2026-09-21", "2026-09-22", "2026-09-23"], "stores": ["r", "w"]},
        # ran out once, back
        "7290003": {"nights": ["2026-09-24"], "stores": ["r"]},
        # ran out ten days ago and gone from every store since: dropped (SCN-153)
        "7290004": {"nights": ["2026-09-18"], "stores": ["r"]},
        # gone exactly max_absent days: running out tonight, listed on none of the last seven
        "7290005": {"nights": [TONIGHT], "stores": ["r"]},
        # he stocks it (INV-080)
        "7290009": {"nights": ["2026-09-27", TONIGHT], "stores": ["w"]},
    }
    flagged.update(flagged_over)
    return {
        "on_day": TONIGHT,
        "window": {"first": "2026-09-15", "last": TONIGHT, "days": 14, "usable_nights": 13},
        "flagged": flagged,
        "listed_recent": {"7290001": ["w"], "7290002": ["r", "w"], "7290003": ["r"], "7290009": ["w"]},
        "listed_tonight": {"7290002": ["r", "w"], "7290003": ["r"], "7290009": ["w"]},
        "names": {"7290001": "ביסלי גריל", "7290002": "במבה נוגט", "7290003": "תפוצ'יפס",
                  "7290004": "חטיף", "7290005": "שוקולד"},
    }


CATALOGUE = [product("7290009"), product("7290100")]


def _run(products=CATALOGUE, running_out=SIGNAL, market_recent=None, run_day="2026-09-28"):
    run_at = datetime.fromisoformat(run_day).replace(hour=3, tzinfo=timezone.utc)
    mr = recent() if market_recent is None else market_recent
    return assortment_gap.run(make_inputs(products=products, running_out=running_out,
                                          market_recent=mr, run_at=run_at)).to_dict()


def _ids(out):
    return [e["barcode"] for e in out["entries"]]


def test_it_is_registered_admitted_and_valueless_and_ranked_among_the_unvalued():
    spec = CAPABILITIES["assortment_gap"]
    assert (spec.spec, spec.value_policy, spec.admitted) == ("F9-S1", "none", True)
    assert spec.requires == ("products", "running_out", "market_recent")
    assert INPUT_REASONS["market_recent"] == "market_signal_thin"
    assert "assortment_gap" in UNVALUED_CAPABILITIES


def test_the_findings_are_exactly_the_not_stocked_still_sold_products_that_ran_out():
    """§5: not in his catalogue, flagged on a recent night, listed recently or out tonight."""
    out = _run()
    assert out["status"] == "available"
    assert set(_ids(out)) == {"7290001", "7290002", "7290003", "7290005"}
    assert "7290004" not in _ids(out)                     # dropped (SCN-153)
    assert "7290009" not in _ids(out)                     # he stocks it (INV-080)


def test_the_order_is_nights_then_stores_then_latest_night_then_barcode():
    """FR-172. 7290002 ran out on four nights; 7290001 on two; 7290003 and 7290005 on one
    each, where 7290005's night is later."""
    assert _ids(_run()) == ["7290002", "7290001", "7290005", "7290003"]
    tie = recent(**{"7290006": {"nights": [TONIGHT], "stores": ["r"]}})
    tie["listed_recent"]["7290006"] = ["r"]
    order = _ids(_run(market_recent=tie))
    assert order.index("7290005") < order.index("7290006")          # same keys: by barcode
    wider = recent(**{"7290007": {"nights": ["2026-09-24"], "stores": ["r", "w"]}})
    wider["listed_recent"]["7290007"] = ["r"]
    order = _ids(_run(market_recent=wider))
    assert order.index("7290007") < order.index("7290005")          # one night, two stores
    assert order.index("7290001") < order.index("7290007")          # nights before stores


def test_an_entry_carries_its_evidence_and_no_value():
    """FR-168, FR-169, INV-081."""
    entry = next(e for e in _run()["entries"] if e["barcode"] == "7290001")
    assert entry["value"] is None
    ev = entry["evidence"]
    assert ev["stores_ran_out"] == ["w"]
    assert ev["nights_ran_out"] == 2 and ev["last_ran_out"] == TONIGHT
    assert ev["listed_at"] == []
    assert ev["window"] == {"first": "2026-09-15", "last": TONIGHT, "days": 14, "usable_nights": 13}
    assert ev["market_name"] == "ביסלי גריל" and entry["product_name"] == "ביסלי גריל"
    for key in REQUIRED_EVIDENCE["assortment_gap"]:
        assert ev[key] is not None
    text = json.dumps(entry["evidence"])
    for word in ("price", "amount", "₪", "cost"):
        assert word not in text


def test_the_identity_is_the_barcode_alone():
    """FR-170, ADR-009: an answer keeps applying on later nights."""
    first = next(e for e in _run()["entries"] if e["barcode"] == "7290002")
    later = recent(**{"7290002": {"nights": ["2026-09-25"], "stores": ["r"]}})
    second = next(e for e in _run(market_recent=later)["entries"] if e["barcode"] == "7290002")
    assert first["id"] == second["id"]
    assert first["signal_family"] == "assortment.market_ran_out" and first["capability"] == "assortment_gap"


def test_tonights_not_stocked_running_out_products_are_all_entries_flagged_tonight():
    """INV-082: every product market_running_out lists tonight that he does not stock."""
    out = _run()
    tonight = {e["barcode"] for e in out["entries"] if e["evidence"]["last_ran_out"] == TONIGHT}
    not_stocked_tonight = {b for b in SIGNAL["products"] if b not in {p["barcode"] for p in CATALOGUE}}
    assert not_stocked_tonight <= tonight


def test_no_market_signal_is_unavailable_with_the_input_reason():
    out = assortment_gap.run(make_inputs(products=CATALOGUE, running_out=None, market_recent=None)).to_dict()
    assert (out["status"], out["unavailable_reason"]) == ("unavailable", "market_signal_thin")


def test_no_catalogue_is_unavailable_and_never_every_product():
    """Without his catalogue, every market product would look "not stocked"."""
    out = _run(products=None)
    assert (out["status"], out["unavailable_reason"]) == ("unavailable", "no_pos_data")
    assert out["entries"] == []


def test_a_stale_signal_is_unavailable_by_the_same_judgement_as_market_running_out():
    """FR-174: two days old is usable, three is stale, exactly as market_running_out."""
    from src.engine import market_running_out
    for day, status in (("2026-09-30", "available"), ("2026-10-01", "unavailable")):
        mine = _run(run_day=day)
        theirs = market_running_out.run(make_inputs(
            running_out=SIGNAL, run_at=datetime.fromisoformat(day).replace(hour=3, tzinfo=timezone.utc))).to_dict()
        assert mine["status"] == theirs["status"] == status
    assert _run(run_day="2026-10-01")["unavailable_reason"] == "market_signal_stale"


def test_nothing_found_is_available_and_empty():
    out = _run(market_recent={**recent(), "flagged": {}, "listed_recent": {}, "listed_tonight": {}, "names": {}})
    assert out["status"] == "available" and out["entries"] == [] and out["counts"]["findings"] == 0


def test_it_publishes_its_window_and_thresholds_and_counts():
    out = _run()
    assert out["thresholds"]["window_days"] == 14
    assert out["thresholds"]["max_absent"] == 7
    assert out["counts"] == {"findings": 4, "stores": 2, "usable_nights": 13}


def test_the_stores_are_named_as_the_store_config_names_them():
    """FR-175: the card says which stores ran out of it, by name. An id the config does not
    know is published as it is, never dropped."""
    wolt, rami = "65daeb8779ca7f0a9bf964f3", "6315c7a3f00f9e43ec812476"
    named = recent(**{"7290008": {"nights": [TONIGHT], "stores": [rami, wolt, "unknown"]}})
    named["listed_tonight"]["7290008"] = [wolt]
    entry = next(e for e in _run(market_recent=named)["entries"] if e["barcode"] == "7290008")
    assert entry["evidence"]["stores_ran_out"] == ["Rami Levy In The Neighborhood", "Wolt Market | Lev Haaretz", "unknown"]
    assert entry["evidence"]["listed_at"] == ["Wolt Market | Lev Haaretz"]

