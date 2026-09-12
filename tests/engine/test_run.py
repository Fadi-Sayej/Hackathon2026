# tests/engine/test_run.py
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

import src.engine.run as run_mod
from src.engine.model import CapabilityOutput
from src.owner_state.model import OwnerState


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: OwnerState.unavailable("no_credentials"))
    # accepts the (sales_dir, silver_dir) the orchestrator passes — they stay parameters
    # because Task 1.9 runs the engine over a copy of the data (see run_engine Interfaces)
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "SILVER_DIR", tmp_path / "silver")


def test_empty_capability_set_publishes_a_valid_artefact(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    target = tmp_path / "dashboard.json"
    result = run_mod.run_engine(mode="publish", artefact_path=target, capability_runners={},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result["published"] is True
    art = json.loads(target.read_text())
    assert art["schema_version"] == 2 and art["capabilities"] == {}
    assert result["status"] == "degraded"          # owner state unavailable is visible, not hidden


def test_a_raising_capability_is_unavailable_not_fatal(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    def boom(inputs): raise RuntimeError("bug")
    def fine(inputs): return CapabilityOutput(id="reconciliation", spec="SPEC-002", status="available")
    result = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json",
                                capability_runners={"price_consistency": boom, "reconciliation": fine},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    caps = result["artefact"]["capabilities"]
    assert caps["price_consistency"]["status"] == "unavailable"
    assert caps["price_consistency"]["unavailable_reason"] == "capability_error"
    assert caps["reconciliation"]["status"] == "available"
    assert any(s["step"] == "capability:price_consistency" and s["status"] == "error" for s in result["steps"])


def test_print_mode_writes_nothing(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    target = tmp_path / "dashboard.json"
    result = run_mod.run_engine(mode="print", artefact_path=target, capability_runners={},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result["published"] is False and not target.exists() and result["artefact"] is not None


def test_adr_017_a_run_with_no_reports_says_so(tmp_path, monkeypatch):
    """ADR-017. Measured behaviour before this: import_sales writes nothing, the previous
    silver tables survive, and the run published 460 flagged products with the sales_import
    step reporting 'ok' and vintages.sales listing all seven months as this run's. The
    artefact was indistinguishable from a run where the reports arrived."""
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None, "monthly_rows": 0})
    result = run_mod.run_engine(mode="print", capability_runners={},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    sales_step = next(s for s in result["steps"] if s["step"] == "sales_import")
    assert sales_step["status"] == "degraded"
    assert result["status"] == "degraded"
    assert result["artefact"]["vintages"]["sales"]["imported_this_run"] is False


def test_adr_017_a_run_whose_reports_arrived_is_not_degraded_for_that(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None, "monthly_rows": 42})
    result = run_mod.run_engine(mode="print", capability_runners={},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    sales_step = next(s for s in result["steps"] if s["step"] == "sales_import")
    assert sales_step["status"] == "ok"
    assert result["artefact"]["vintages"]["sales"]["imported_this_run"] is True
