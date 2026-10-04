# tests/test_check_order_signals.py
"""Phase 5 Task 5.11: the F8 boundary probe catches what it exists to catch.

A probe that passes whatever the engine does is worse than none: it reads as proof. So each
check is handed an artefact in which its expectation is broken, and must report it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import check_order_signals as probe  # noqa: E402


def _entry(barcode, kind="gross", applied=False):
    return {"id": "0" * 16, "barcode": barcode,
            "evidence": {"kind": kind, "boost": {"applied": applied, "pct": 10 if applied else None}}}


def _art(*, oq_status="available", oq_reason=None, entries=(), boost_status="available", disagreements=(),
         gap_status="available", gap_entries=(), layout_status="available", layout_reason=None, fixtures=None,
         plan_status="available", plan_reason=None, plans=()):
    return {"capabilities": {
        # F12-S1 §20 (Phase 8 Task 8.2): the layout, which needs no sales.
        "layout_facts": {"status": layout_status, "unavailable_reason": layout_reason, "fixtures": fixtures},
        "shelf_plan": {"status": plan_status, "unavailable_reason": plan_reason, "entries": list(plans)},
        "shelf_explanation": {"status": "available", "explanations": [{"text": {"en": "why"}}]},
        "order_quantity": {"status": oq_status, "unavailable_reason": oq_reason, "entries": list(entries)},
        # F9-S1: withheld with the market snapshots it is replayed from (AC-165).
        "assortment_gap": {"status": gap_status, "entries": list(gap_entries)},
        "market_boost": {"status": boost_status},
        "owner_questions": {"items": [{"fact": "cost_price", "barcode": "c"}]
                            + [{"fact": "market_disagreement", "barcode": b} for b in disagreements]}}}


def _plan(placed=(), no_width=()):
    return {"evidence": {"shelves": [{"products": [{"barcode": b} for b in placed]}],
                         "unplaced": {"no_width": list(no_width)}}}


GOOD = _art(entries=[_entry("a", "net", applied=True), _entry("b")], disagreements=["s"], gap_entries=[{"id": "g"}],
            fixtures={"F1": {}}, plans=[_plan(placed=["7290001"])])


def test_a_baseline_with_nothing_to_withhold_is_refused():
    assert probe.baseline_problems(GOOD) == []
    assert len(probe.baseline_problems(_art())) == 7
    # F9: a baseline with no assortment-gap finding proves nothing when the market is withheld.
    no_gap = _art(entries=[_entry("a", "net", applied=True)], disagreements=["s"])
    assert [m for m in probe.baseline_problems(no_gap) if "assortment gap" in m]
    assert probe.baseline_problems(_art(entries=[_entry("a", "gross", applied=True)], disagreements=["s"]))


def test_report_days_withheld_must_leave_no_quantity():
    assert probe.withheld_daily_problems(_art(oq_status="unavailable", oq_reason="no_daily_sales")) == []
    # A monthly report standing in for the missing days: available, with entries.
    assert probe.withheld_daily_problems(_art(entries=[_entry("a")]))
    # Unavailable for some other reason is not the honest one.
    assert probe.withheld_daily_problems(_art(oq_status="unavailable", oq_reason="capability_error"))


def test_deliveries_withheld_must_leave_nothing_net():
    assert probe.withheld_deliveries_problems(_art(entries=[_entry("a", "gross")])) == []
    assert probe.withheld_deliveries_problems(_art(entries=[_entry("a", "net")]))


def test_store_facts_withheld_must_leave_no_quantity():
    assert probe.withheld_facts_problems(_art(oq_status="unavailable", oq_reason="no_store_facts")) == []
    assert probe.withheld_facts_problems(_art(entries=[_entry("a")]))


def test_market_withheld_must_leave_suggestions_unadjusted_and_no_question():
    assert probe.withheld_market_problems(_art(entries=[_entry("a")], gap_status="unavailable")) == []
    # F9-S1 AC-165: findings with no market behind them.
    assert probe.withheld_market_problems(_art(entries=[_entry("a")], gap_entries=[{"id": "g"}]))
    assert probe.withheld_market_problems(_art(entries=[_entry("a")]))                    # still available
    assert probe.withheld_market_problems(_art(entries=[], gap_status="unavailable"))     # vanished
    assert probe.withheld_market_problems(_art(entries=[_entry("a", applied=True)], gap_status="unavailable"))
    assert probe.withheld_market_problems(_art(entries=[_entry("a")], disagreements=["s"], gap_status="unavailable"))


def test_picks_withheld_must_leave_no_boost_and_no_call():
    assert probe.withheld_picks_problems(_art(entries=[_entry("a")]), calls=0) == []
    assert probe.withheld_picks_problems(_art(entries=[_entry("a", applied=True)]), calls=0)
    assert probe.withheld_picks_problems(_art(entries=[_entry("a")]), calls=1)
    assert probe.withheld_picks_problems(_art(entries=[]), calls=0)


def test_an_answered_disagreement_must_not_come_back():
    assert probe.answered_problems(_art(disagreements=["t"]), "s") == []
    assert probe.answered_problems(_art(disagreements=["s"]), "s")


def test_the_quantity_and_the_boost_must_fail_apart():
    no_picks = _art(entries=[_entry("a")], boost_status="unavailable")
    # F12: the layout needs no sales and stays; the plan waits for them and goes (D-30).
    no_daily = _art(oq_status="unavailable", oq_reason="no_daily_sales", plan_status="unavailable",
                    plan_reason="no_daily_sales")
    assert probe.independence_problems(no_picks, no_daily) == []
    assert probe.independence_problems(no_picks, _art(oq_status="unavailable", oq_reason="no_daily_sales",
                                                      layout_status="unavailable", plan_status="unavailable",
                                                      plan_reason="no_daily_sales"))
    # F12: a plan published with no daily report came from nothing (D-30).
    assert probe.independence_problems(no_picks, _art(oq_status="unavailable", oq_reason="no_daily_sales"))
    assert probe.independence_problems(_art(entries=[], boost_status="unavailable"), no_daily)
    assert probe.independence_problems(no_picks, _art(oq_status="unavailable", boost_status="unavailable"))


def test_the_probe_passes_over_its_world_and_reaches_the_engine(tmp_path):
    """The whole probe, over the built world: every case holds, and the baseline is real."""
    problems, done = probe.probe(tmp_path)
    assert problems == []
    assert done[0].startswith("baseline:") and "0 suggestions" not in done[0]


def test_it_blocks_once_the_real_artefact_carries_the_quantity(tmp_path, monkeypatch):
    art = tmp_path / "dashboard.json"
    monkeypatch.setattr(probe, "ARTEFACT", art)
    assert probe.blocking() is False                                    # no artefact
    art.write_text(json.dumps({"capabilities": {"order_quantity": {"status": "unavailable"}}}))
    assert probe.blocking() is False                                    # today: no_daily_sales
    art.write_text(json.dumps({"capabilities": {"order_quantity": {"status": "available"}}}))
    assert probe.blocking() is True


def test_it_blocks_once_any_capability_it_probes_is_live(tmp_path, monkeypatch):
    """F9's assortment gap is live on real data with no daily report at all (since the 2026-09-29
    nightly), and the probe covers it, as it covers the boost. Waiting for order_quantity alone
    would warn forever: after D-23 no daily report is coming."""
    art = tmp_path / "dashboard.json"
    monkeypatch.setattr(probe, "ARTEFACT", art)

    def publish(**status):
        art.write_text(json.dumps({"capabilities": {k: {"status": v} for k, v in status.items()}}))

    publish(order_quantity="unavailable", market_boost="unavailable", assortment_gap="unavailable",
            owner_questions="available")
    assert probe.blocking() is False            # F5's questions are live, but not because of F8
    publish(order_quantity="unavailable", market_boost="unavailable", assortment_gap="available")
    assert probe.blocking() is True             # today, 2026-09-29
    publish(order_quantity="unavailable", market_boost="available", assortment_gap="unavailable")
    assert probe.blocking() is True


def test_the_layout_file_withheld_must_say_no_store_layout():
    gone = dict(layout_status="unavailable", layout_reason="no_store_layout", plan_status="unavailable",
                plan_reason="no_store_layout")
    assert probe.withheld_layout_problems(_art(**gone)) == []
    assert probe.withheld_layout_problems(_art(**{**gone, "plan_status": "available", "plan_reason": None}))
    assert probe.withheld_layout_problems(_art(fixtures={"F1": {}}))
    assert probe.withheld_layout_problems(_art(layout_status="unavailable", layout_reason="capability_error"))


def test_a_withheld_width_must_leave_its_product_unplaced_and_named():
    assert probe.withheld_width_problems(_art(plans=[_plan(no_width=["x"])]), "x") == []
    assert probe.withheld_width_problems(_art(plans=[_plan(placed=["x"])]), "x")
    assert probe.withheld_width_problems(_art(plans=[_plan()]), "x")


# ── F12-S1 §20 over the planogram world (Phase 8 Task 8.6) ───────────────────

def _shelf(m_status="available", m_reason=None, arrangements=(), plan_uses=None, plan_status="available",
           elasticity=None):
    return {"capabilities": {
        "shelf_measurement": {"status": m_status, "unavailable_reason": m_reason, "arrangements": list(arrangements),
                              "plan_uses": plan_uses},
        "shelf_plan": {"status": plan_status, "elasticity": elasticity}}}


def test_the_planogram_baseline_must_measure_and_reach_his_value():
    measured = [{"status": "measured"}]
    assert probe.shelf_baseline_problems(_shelf(arrangements=measured, plan_uses={"source": "his_store"})) == []
    assert probe.shelf_baseline_problems(_shelf(arrangements=measured, plan_uses={"source": "research"}))
    assert probe.shelf_baseline_problems(_shelf(m_status="unavailable"))


def test_a_withheld_measurement_keeps_the_plan_on_017_and_names_why():
    research = {"source": "research", "measurement_reason": "owner_state_unavailable"}
    good = _shelf(m_status="unavailable", m_reason="owner_state_unavailable", elasticity=research)
    assert probe.withheld_measurement_problems(good, "owner_state_unavailable") == []
    # Owner state that could not be read, taken for "no arrangements": rule 10's silent failure.
    assert probe.withheld_measurement_problems(_shelf(m_status="unavailable", m_reason="no_arrangement_recorded",
                                                      elasticity=research), "owner_state_unavailable")
    # The plan taken down with it, or silent about why.
    assert probe.withheld_measurement_problems(_shelf(m_status="unavailable", m_reason="owner_state_unavailable",
                                                      plan_status="unavailable"), "owner_state_unavailable")


def test_every_fixture_arranged_must_publish_no_net_change():
    assert probe.all_arranged_problems(_shelf(arrangements=[{"reason": "no_unchanged_fixture", "products": []}])) == []
    assert probe.all_arranged_problems(_shelf(arrangements=[{"reason": None, "products": [{"net_change": 1.1}]}]))



def test_the_planogram_world_on_disk_is_the_world_in_memory(tmp_path):
    """The probe reads the world through the importer. Every unit must arrive as the world drew it,
    or the probe would be testing another world."""
    import pyarrow.parquet as pq
    import src.engine.run as run_mod
    paths, w = probe.shelf_world.write(tmp_path / "shelf")
    run_mod._sales_daily_import(paths["daily_sales_dir"], paths["silver_dir"])
    rows = pq.read_table(paths["silver_dir"] / "sales_daily.parquet").to_pylist()
    got = sorted((r["barcode"], str(r["day"])[:10], float(r["units"]), r["receipts"]) for r in rows)
    want = sorted((r["barcode"], r["day"], r["units"], r["receipts"]) for r in w["sales_daily"])
    assert got == want


def test_withheld_inputs_over_the_planogram_world_must_take_both_down():
    gone = {"capabilities": {c: {"status": "unavailable", "unavailable_reason": "no_daily_sales"}
                             for c in ("shelf_plan", "shelf_measurement")}}
    assert probe.shelf_withheld_problems(gone, "no_daily_sales") == []
    half = {"capabilities": {**gone["capabilities"], "shelf_measurement": {"status": "unavailable",
                                                                         "unavailable_reason": "capability_error"}}}
    assert probe.shelf_withheld_problems(half, "no_daily_sales")


def test_withheld_explanations_say_no_model_key_and_leave_every_plan_alone():
    rest = {"layout_facts": {"status": "available"}, "shelf_measurement": {"status": "unavailable"}}
    base = {"capabilities": {**rest, "shelf_plan": {"entries": [{"id": "p"}]},
                             "shelf_explanation": {"status": "available", "unavailable_reason": None}}}
    gone = {"capabilities": {**rest, "shelf_plan": {"entries": [{"id": "p"}]},
                             "shelf_explanation": {"status": "unavailable", "unavailable_reason": "no_model_key"}}}
    assert probe.withheld_explanations_problems(gone, base) == []
    changed = {"capabilities": {**gone["capabilities"], "shelf_plan": {"entries": [{"id": "q"}]}}}
    assert probe.withheld_explanations_problems(changed, base)          # INV-096, the plan
    moved = {"capabilities": {**gone["capabilities"], "shelf_measurement": {"status": "available"}}}
    assert probe.withheld_explanations_problems(moved, base)            # INV-096, the measurement
    assert probe.withheld_explanations_problems(base, base)             # an explanation from no model
