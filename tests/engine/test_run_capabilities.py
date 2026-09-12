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
    _stub_inputs(monkeypatch)
    result = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json",
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
    # and hygiene is its own — so the publisher's status rule runs over all seven.
    assert set(caps) == {"catalogue_lifecycle", "price_consistency", "reconciliation", "hygiene",
                         "competitor_position", "margin_below_cost", "owner_questions"}
    assert all(c["status"] in ("available", "unavailable") for c in caps.values())
