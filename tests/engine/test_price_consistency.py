# tests/engine/test_price_consistency.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product
from src.engine.price_consistency import classify, derive_ceiling, run

P = dict(band_pct=2, drop_ratio=0.75, min_band_count=20)


def _dist():
    # 81 in 16–18, 8 in 18–20, then a small tail: the pilot's shape
    return [1.0] * 30 + [5.0] * 40 + [10.0] * 60 + [15.0] * 50 + [17.0] * 81 + [19.0] * 8 + [25.0] * 5 + [40.0] * 3


def test_ceiling_is_the_densest_density_collapse():
    r = derive_ceiling(_dist(), **P)
    assert r.pct == 18.0 and r.method == "densest_density_collapse"
    assert any(b["from"] == 16.0 and b["count"] == 81 for b in r.bands)


def test_ceiling_undetermined_on_a_flat_distribution():
    assert derive_ceiling([float(x) for x in range(0, 60)] * 2, **P).pct is None


def test_ceiling_undetermined_when_the_collapse_band_is_too_small():
    assert derive_ceiling([1.0] * 10 + [3.0] * 1, **P).pct is None


def test_classify_states():
    assert classify(10.0, 10.0, 18.0) == "identical"
    assert classify(10.0, 9.0, 18.0) == "inverted"
    assert classify(10.0, 11.0, 18.0) == "within"
    assert classify(10.0, 13.0, 18.0) == "above"
    assert classify(10.0, 13.0, None) == "undetermined"


def _inputs(extra=None):
    prods = [product(str(i), shelf=10.0, delivery=10.0) for i in range(100)]            # identical
    prods += [product(f"w{i}", shelf=10.0, delivery=11.0) for i in range(81)]           # 10 % markup
    prods += [product(f"x{i}", shelf=10.0, delivery=11.7) for i in range(81)]           # 17 %
    prods += [product(f"y{i}", shelf=10.0, delivery=11.9) for i in range(8)]            # 19 %  → above
    prods += [product("inv", shelf=37.9, delivery=21.9, cost=20.0)]                     # inverted
    prods += [product("art", shelf=0.01, delivery=0.02, cost=2.28)]                     # D-4 artefact
    prods += [product("nod", shelf=5.0, delivery=None)]                                 # no delivery price
    return make_inputs(products=prods + (extra or []))


def test_ac_001_identical_never_surfaces_and_ac_002_states_are_distinguishable():
    out = run(_inputs())
    ids = {e.barcode for e in out.entries}
    assert "0" not in ids and out.counts["identical"] == 100
    kinds = {e.barcode: e.characterisation for e in out.entries}
    assert kinds["inv"] == "confirmed_loss" and kinds["y0"] == "question"


def test_ac_003_above_ceiling_is_never_a_loss_and_carries_no_value():
    out = run(_inputs())
    above = [e for e in out.entries if e.characterisation == "question"]
    assert above and all(e.value is None for e in above)


def test_ac_004_ceiling_reported_with_counts():
    out = run(_inputs())
    assert out.thresholds["ceiling_pct"] == 18.0
    assert out.counts["above"] == 8 and out.counts["inverted"] == 1


def test_inverted_carries_a_recurring_confirmed_value_and_evidence():
    e = next(e for e in run(_inputs()).entries if e.barcode == "inv")
    assert e.value.kind == "per_sale" and e.value.certainty == "confirmed" and e.value.amount == 16.0
    assert e.evidence["shelf_price"] == 37.9 and e.evidence["delivery_price"] == 21.9 and e.evidence["commission_compounds"] is True
    assert e.action == "verify_price"


def test_ac_005_undetermined_ceiling_suppresses_above_keeps_inverted():
    prods = [product(f"f{i}", shelf=10.0, delivery=10.0 + i * 0.1) for i in range(1, 60)]   # flat
    prods.append(product("inv", shelf=10.0, delivery=8.0))
    out = run(make_inputs(products=prods))
    assert out.thresholds["ceiling_pct"] is None and out.counts["above"] is None
    assert [e.barcode for e in out.entries] == ["inv"]
    assert "ceiling_undetermined" in out.notes


def test_ac_006_artefacts_are_excluded_and_counted():
    out = run(_inputs())
    assert "art" not in {e.barcode for e in out.entries} and out.counts["excluded_artefact"] == 1


def test_ac_007_no_velocity_keys_in_evidence():
    for e in run(_inputs()).entries:
        assert not {"units_per_day", "days_to_stockout", "projected_revenue"} & set(e.evidence)


def test_ac_008_signal_density_guard():
    prods = [product(f"a{i}", shelf=10.0, delivery=15.0) for i in range(50)] + [product("b", shelf=10.0, delivery=10.0)]
    out = run(make_inputs(products=prods))
    assert out.counts["above"] is None and "ceiling_degenerate" in out.notes


def test_missing_delivery_prices_everywhere_is_unavailable():
    out = run(make_inputs(products=[product("1", shelf=5.0, delivery=None)]))
    assert out.status == "unavailable" and out.unavailable_reason == "no_delivery_prices"


def test_withdrawn_products_leave_the_population():
    out = run(_inputs(), ) if False else run(make_inputs(products=[product("inv", shelf=10.0, delivery=8.0), product("k", shelf=10.0, delivery=10.0)], withdrawn={"inv"}))
    assert out.counts["population"] == 1 and out.entries == []


import csv
import pytest
from src.engine.model import norm_barcode

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not (ROOT / "yomyom-inventory.csv").exists(), reason="pilot export not present")
def test_pilot_ceiling_reproduces_18_percent():
    with (ROOT / "yomyom-inventory.csv").open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    keys = {k.strip(): k for k in rows[0]}
    markups = []
    for r in rows:
        try:
            shelf, wolt = float(r[keys["מחיר מכירה"]] or 0), float(r[keys["WOLT"]] or 0)
        except ValueError:
            continue
        if shelf >= 0.5 and wolt > shelf + 0.005:
            markups.append((wolt / shelf - 1) * 100)
    assert derive_ceiling(markups, **P).pct == 18.0
