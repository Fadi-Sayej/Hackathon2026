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


def _art(*, oq_status="available", oq_reason=None, entries=(), boost_status="available", disagreements=()):
    return {"capabilities": {
        "order_quantity": {"status": oq_status, "unavailable_reason": oq_reason, "entries": list(entries)},
        "market_boost": {"status": boost_status},
        "owner_questions": {"items": [{"fact": "cost_price", "barcode": "c"}]
                            + [{"fact": "market_disagreement", "barcode": b} for b in disagreements]}}}


GOOD = _art(entries=[_entry("a", "net", applied=True), _entry("b")], disagreements=["s"])


def test_a_baseline_with_nothing_to_withhold_is_refused():
    assert probe.baseline_problems(GOOD) == []
    assert len(probe.baseline_problems(_art())) == 4
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
    assert probe.withheld_market_problems(_art(entries=[_entry("a")])) == []
    assert probe.withheld_market_problems(_art(entries=[]))                               # vanished
    assert probe.withheld_market_problems(_art(entries=[_entry("a", applied=True)]))      # boosted from nothing
    assert probe.withheld_market_problems(_art(entries=[_entry("a")], disagreements=["s"]))


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
    no_daily = _art(oq_status="unavailable", oq_reason="no_daily_sales", boost_status="available")
    assert probe.independence_problems(no_picks, no_daily) == []
    assert probe.independence_problems(_art(entries=[], boost_status="unavailable"), no_daily)
    assert probe.independence_problems(no_picks, _art(oq_status="unavailable", boost_status="unavailable"))


def test_the_probe_passes_over_its_world_and_reaches_the_engine(tmp_path):
    """The whole probe, over the built world: every case holds, and the baseline is real."""
    problems, done = probe.probe(tmp_path)
    assert problems == []
    assert done[0].startswith("baseline:") and "0 suggestions" not in done[0]


def test_it_blocks_only_once_the_real_artefact_carries_the_quantity(tmp_path, monkeypatch):
    art = tmp_path / "dashboard.json"
    monkeypatch.setattr(probe, "ARTEFACT", art)
    assert probe.blocking() is False                                    # no artefact
    art.write_text(json.dumps({"capabilities": {"order_quantity": {"status": "unavailable"}}}))
    assert probe.blocking() is False                                    # today: no_daily_sales
    art.write_text(json.dumps({"capabilities": {"order_quantity": {"status": "available"}}}))
    assert probe.blocking() is True
