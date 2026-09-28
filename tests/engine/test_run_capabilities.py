# tests/engine/test_run_capabilities.py
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import src.engine.run as run_mod
from helpers import make_inputs, product, summary, window_of
from src.owner_state.model import OwnerState

W = window_of(["2026-01", "2026-02"])


def _stub_inputs(monkeypatch):
    inputs = make_inputs(
        products=[product("live", shelf=10.0, delivery=10.0, cost=4.0, stock=2.0),
                  # cost=None so it IS a cost question — otherwise withdrawal has nothing
                  # to suppress and suppressed["withdrawn"] can never be 1
                  product("dead", shelf=5.0, cost=None, stock=0.0),
                  product("idle", shelf=5.0, cost=None, stock=7.0)],
        sales_summary=[summary("live", units=10, receipts=5)], sales_monthly=[{"barcode": "live", "month": "2026-01",
                                                                              "units": 10, "receipts": 5, "revenue": 100.0}],
        window=W, owner=OwnerState.from_dict({"status": "available", "pulled_at": "t"}))
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: inputs.owner)
    monkeypatch.setattr(run_mod, "_sales_import", lambda: {"window": W.to_dict()})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "load_inputs", lambda **kw: inputs)
    return inputs


def test_the_withdrawn_set_reaches_the_other_capabilities(tmp_path, monkeypatch):
    """FR-074's hand-off is a `living` behaviour, so the population is pinned rather than
    left to policy. ADR-020 makes the published population a setting, and it is `whole`
    while GAP-009 is open — this test is about the mechanism, not about today's default."""
    _stub_inputs(monkeypatch)
    result = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json",
                                population="living",
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    caps = result["artefact"]["capabilities"]
    assert caps["catalogue_lifecycle"]["counts"]["withdrawable"] == 1
    # 'dead' is withdrawn, so it is absent from the question suppression population…
    assert caps["owner_questions"]["suppressed"]["withdrawn"] == 1
    # …and from the idle set, which suppresses the other cost question.
    assert caps["owner_questions"]["suppressed"]["idle"] == 1


def test_the_artefact_carries_every_capability_with_its_extras_and_vintages(tmp_path, monkeypatch):
    _stub_inputs(monkeypatch)
    art = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json",
                             now=datetime(2026, 9, 8, tzinfo=timezone.utc))["artefact"]
    caps = art["capabilities"]
    assert caps["catalogue_lifecycle"]["window"]["window_id"] == "2026-01..2026-02"
    assert caps["owner_questions"]["limit"] == 3
    assert "provenance.sales_months" in art["figures"]
    # Exactly the registry: catalogue and questions are capabilities like any other (ADR-014),
    # and hygiene is its own — so the publisher's status rule runs over all ten. The last three
    # are F8's market signal (Task 5.4), boost (Task 5.6) and quantity (Task 5.8), each
    # registered with its runner in the same change.
    assert set(caps) == {"catalogue_lifecycle", "price_consistency", "reconciliation", "hygiene",
                         "competitor_position", "margin_below_cost", "owner_questions",
                         "market_running_out", "market_boost", "order_quantity"}
    assert all(c["status"] in ("available", "unavailable") for c in caps.values())


def test_adr_020_the_whole_population_hands_nothing_off(tmp_path, monkeypatch):
    """The other half of the same mechanism, and the one D-14 depends on: under `whole` no
    capability is given a withdrawn set, so no published figure can depend on withdrawal."""
    _stub_inputs(monkeypatch)
    art = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json",
                             population="whole",
                             now=datetime(2026, 9, 8, tzinfo=timezone.utc))["artefact"]
    assert art["population"] == "whole"
    assert art["capabilities"]["owner_questions"]["suppressed"]["withdrawn"] == 0
    assert art["capabilities"]["price_consistency"]["thresholds"]["ceiling_population_excludes_withdrawn"] is False



def test_the_measurement_is_its_own_file_beside_the_artefact(tmp_path, monkeypatch):
    """F13-S1, ADR-023 (revised 2026-09-27), ADR-029 Decision 6: it is published beside
    dashboard.json and never inside it, because the edge gate can keep a file from the owner
    but not a field inside a file his app downloads. "Shown" is every entry this run publishes."""
    import json
    inputs = _stub_inputs(monkeypatch)
    inputs.owner = OwnerState.from_dict({"status": "available", "pulled_at": "t", "outcomes": {
        "gone": {"status": "acted", "at": 1790000000000,
                 "snapshot": {"signal_family": "price.inverted", "value": 2.5, "kind": "per_sale",
                              "certainty": "confirmed"}}}})
    result = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json",
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    art = result["artefact"]
    assert "measurement" not in art
    m = json.loads((tmp_path / "measurement.json").read_text(encoding="utf-8"))
    assert m == result["measurement"]
    assert m["inputs_digest"] == art["inputs_digest"] and m["run_id"] == art["run_id"]
    shown = sum(len(c.get("entries") or []) for c in art["capabilities"].values())
    assert m["status"] == "available"
    assert m["totals"]["shown"] == shown
    assert m["totals"]["decided"] == 1 and m["totals"]["not_in_this_run"] == 1
    assert m["money"] == [{"kind": "per_sale", "certainty": "confirmed", "amount": 2.5, "decisions": 1}]
    assert next(s for s in result["steps"] if s["step"] == "measurement")["status"] == "ok"
