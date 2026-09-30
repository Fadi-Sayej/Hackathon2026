# tests/engine/test_run.py
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

import src.engine.run as run_mod
from src.engine.model import CapabilityOutput
from src.owner_state.model import OwnerState

from helpers import load_inputs_without_market  # noqa: E402


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: OwnerState.unavailable("no_credentials"))
    # accepts the (sales_dir, silver_dir) the orchestrator passes — they stay parameters
    # because Task 1.9 runs the engine over a copy of the data (see run_engine Interfaces)
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "SILVER_DIR", tmp_path / "silver")
    # …and the market half. Isolating only silver left load_inputs reading the real
    # competitor signals and matches — 12 seconds per test, and not the isolation the
    # test claims.
    monkeypatch.setattr(run_mod, "SIGNALS_DIR", tmp_path / "signals")
    monkeypatch.setattr(run_mod, "MATCHES_PATH", tmp_path / "matches.parquet")
    # …and the daily reports (Task 5.2), so no test reads the repository's own.
    monkeypatch.setattr(run_mod, "DAILY_SALES_DIR", tmp_path / "sales_daily")
    # …and the market snapshots F8 and F9 replay, for the same reason: 2.4 s a run.
    monkeypatch.setattr(run_mod, "load_inputs", load_inputs_without_market)


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


def test_adr_020_the_published_population_comes_from_policy(tmp_path, monkeypatch):
    """ADR-020. The cut-over was blocked because the artefact happened to count over the
    living catalogue, which D-14 forbids showing the owner while GAP-009 is open. That was a
    default, not a fact: the population is a policy setting and the artefact states it."""
    _isolate(monkeypatch, tmp_path)
    result = run_mod.run_engine(mode="print", capability_runners={},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    from src.engine.policy import load_policy
    assert result["artefact"]["population"] == load_policy().published_population


def test_an_explicit_population_still_wins(tmp_path, monkeypatch):
    """npm run figures:whole must be able to ask for a population regardless of policy."""
    _isolate(monkeypatch, tmp_path)
    result = run_mod.run_engine(mode="print", capability_runners={}, population="living",
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result["artefact"]["population"] == "living"


def test_skip_market_skips_the_market_context_too():
    """`--skip-market` has to mean it.

    market_context was appended unconditionally, outside the `if not skip` branch, so
    `python3 scripts/figures.py --json --skip-market` — the reproduction command a judge
    is handed, and the one whose own test is named "recomputes nothing" — made a live
    Open-Meteo call and rewrote the committed public/data/market-context.json on every
    run. Verified by running it against a clean tree: exit 0, and market-context.json
    modified.

    Nothing in the engine reads that file. Its consumers were the legacy chain:
    reorderEngine.js and check_signals_live.mjs, removed on 2026-09-24 (ADR-028), and
    product_recommendations.py, deleted the same day (Phase 4 Task 4.2). So skipping it costs no capability
    an input. The nightly runs without --skip-market, so the committed context still
    refreshes there, and ADR-028 keeps it published for V2.
    """
    assert run_mod._market_chain(skip=True) == []
    assert [name for name, _ in run_mod._market_chain(skip=False)] == [
        "market_context", "rehydrate_silver", "competitor_signals", "product_matching"]


def _chain_that_records(monkeypatch, ran):
    steps = [(name, (lambda name=name: ran.append(name)))
             for name in ("market_context", "rehydrate_silver", "competitor_signals", "product_matching")]
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [] if skip else steps)


def test_print_mode_rebuilds_the_market_half_without_rewriting_market_context(tmp_path, monkeypatch):
    """Reproduction changes no committed file, and spends no time on a file no figure reads.

    Measured on a fresh clone on 2026-09-29: `npm run figures`, which a clone must run without
    --skip-market to build its market half, took 133 s against NFR-060's two minutes. 69 s of
    that was market_context calling Open-Meteo to rewrite the committed
    public/data/market-context.json, which nothing in the engine or the browser reads. The
    three steps that build the market half the figures do read still run."""
    _isolate(monkeypatch, tmp_path)
    ran = []
    _chain_that_records(monkeypatch, ran)
    result = run_mod.run_engine(mode="print", capability_runners={},
                                now=datetime(2026, 9, 29, tzinfo=timezone.utc))
    assert ran == ["rehydrate_silver", "competitor_signals", "product_matching"]
    assert "market_context" not in [s["step"] for s in result["steps"]]


def test_the_nightly_still_publishes_market_context(tmp_path, monkeypatch):
    """ADR-028 keeps the file published, and collect-daily.yml commits it: publish mode runs it."""
    _isolate(monkeypatch, tmp_path)
    ran = []
    _chain_that_records(monkeypatch, ran)
    run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json", capability_runners={},
                       now=datetime(2026, 9, 29, tzinfo=timezone.utc))
    assert ran == ["market_context", "rehydrate_silver", "competitor_signals", "product_matching"]


# ── Phase 5 Task 5.2: the daily sales reports in the run (ADR-030 §3, §4) ───────────────

import pytest

DAILY_HEADER = "תאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n"


def _otherwise_ok(monkeypatch, tmp_path):
    """A run with nothing else to degrade it, so the verdict is the daily reports' alone."""
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(run_mod, "_pull_owner_state",
                        lambda: OwnerState.from_dict({"status": "available", "pulled_at": "t"}))
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None, "monthly_rows": 42})


def _reports(tmp_path, days):
    reports = tmp_path / "daily"; reports.mkdir(exist_ok=True)
    for day in days:
        (reports / f"דוח מכירות יום {day}.csv").write_text(
            "\ufeff" + DAILY_HEADER + "מים,123,10,2,4,20,3,2,0,1,\n", encoding="utf-8")
    return reports


def _daily_run(tmp_path, days, now):
    return run_mod.run_engine(mode="print", capability_runners={}, now=now,
                              daily_sales_dir=_reports(tmp_path, days))


def _week(first):
    from datetime import date, timedelta
    start = date.fromisoformat(first)
    return [(start + timedelta(days=i)).isoformat() for i in range(7)]


@pytest.mark.parametrize("days,now,verdict", [
    # Before the first file F8 waits, and the run is not degraded by it.
    ([], datetime(2026, 9, 20, tzinfo=timezone.utc), "ok"),
    (["2026-09-15"], datetime(2026, 9, 20, tzinfo=timezone.utc), "ok"),          # five days old
    (["2026-09-11"], datetime(2026, 9, 20, tzinfo=timezone.utc), "degraded"),    # nine days old
    # A weekly batch (09-06 … 09-12), sent 09-13: every night until the next batch is ok,
    # the last of them seven days after the latest report day.
    *[(_week("2026-09-06"), datetime(2026, 9, d, tzinfo=timezone.utc), "ok") for d in range(13, 20)],
    # …and the night the next batch is late, it is not.
    (_week("2026-09-06"), datetime(2026, 9, 20, tzinfo=timezone.utc), "degraded"),
])
def test_the_run_is_degraded_only_when_the_daily_reports_have_gone_stale(tmp_path, monkeypatch, days, now, verdict):
    _otherwise_ok(monkeypatch, tmp_path)
    result = _daily_run(tmp_path, days, now)
    assert result["status"] == verdict
    step = next(s for s in result["steps"] if s["step"] == "sales_daily_import")
    assert step["status"] == verdict
    if verdict == "degraded":
        assert "stale" in step["error"]


def test_the_daily_step_runs_after_the_monthly_one(tmp_path, monkeypatch):
    _otherwise_ok(monkeypatch, tmp_path)
    names = [s["step"] for s in _daily_run(tmp_path, [], datetime(2026, 9, 20, tzinfo=timezone.utc))["steps"]]
    assert names.index("sales_daily_import") == names.index("sales_import") + 1


def test_a_failed_daily_file_is_named_and_does_not_degrade_the_run(tmp_path, monkeypatch):
    """ADR-030 §3: a failed file is a missing day, named in the steps. §4: only staleness
    degrades the run, so one bad file in a good week does not."""
    _otherwise_ok(monkeypatch, tmp_path)
    reports = _reports(tmp_path, ["2026-09-18"])
    (reports / "דוח מכירות יום 2026-09-19.csv").write_text("﻿" + DAILY_HEADER, encoding="utf-8")
    result = run_mod.run_engine(mode="print", capability_runners={}, daily_sales_dir=reports,
                                now=datetime(2026, 9, 20, tzinfo=timezone.utc))
    step = next(s for s in result["steps"] if s["step"] == "sales_daily_import")
    assert step["status"] == "degraded"
    assert "דוח מכירות יום 2026-09-19.csv" in step["error"] and "no_product_lines" in step["error"]
    assert result["status"] == "ok"
    assert result["artefact"]["vintages"]["sales_daily"]["missing_days"][-1] == "2026-09-19"


def test_the_artefact_publishes_the_daily_vintage(tmp_path, monkeypatch):
    _otherwise_ok(monkeypatch, tmp_path)
    result = _daily_run(tmp_path, ["2026-09-17", "2026-09-19"], datetime(2026, 9, 20, tzinfo=timezone.utc))
    assert result["artefact"]["vintages"]["sales_daily"] == {
        "first_day": "2026-09-17", "last_day": "2026-09-19", "report_days": 2,
        "missing_days": ["2026-09-18"], "deliveries_missing_days": []}
