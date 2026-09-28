"""What `npm run figures` counts as a reproduction failure (System Design §11.6, NFR-062).

§11.6: exit 1 "when any registered figure is unavailable". F8's capabilities (Phase 5)
register no figure, and on every machine without the model key and the daily reports they
are unavailable, as designed. Counting them made the command exit 1 everywhere, telling a
reader the figures do not reproduce when every one of them does.

These drive figures.main over a synthetic artefact, so they need no pilot data and run in
CI; test_figures_cli.py drives the real engine and skips there.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scripts.figures as figures  # noqa: E402
from src.engine.registry import CAPABILITIES  # noqa: E402

FIGURE = {"value": 3, "unit": "products", "inputs": ["pos"], "thresholds": {}}


def _run(monkeypatch, capsys, capabilities):
    artefact = {"figures": {"price_consistency.inverted": FIGURE}, "capabilities": capabilities}
    monkeypatch.setattr(figures, "run_engine", lambda **_: {"artefact": artefact})
    monkeypatch.setattr(sys, "argv", ["figures.py", "--json"])
    code = figures.main()
    out, err = capsys.readouterr()
    return code, json.loads(out), err


def _unavailable(reason):
    return {"status": "unavailable", "unavailable_reason": reason}


def test_a_capability_that_registers_no_figure_is_not_a_reproduction_failure(monkeypatch, capsys):
    code, payload, err = _run(monkeypatch, capsys, {
        "price_consistency": {"status": "available"},
        "market_running_out": _unavailable("market_signal_thin"),
        "market_boost": _unavailable("no_boost_key"),
        "order_quantity": _unavailable("no_daily_sales"),
    })
    assert code == 0, err
    assert payload["unavailable"] == []
    assert payload["registers_no_figure"] == [
        "market_boost: no_boost_key", "market_running_out: market_signal_thin",
        "order_quantity: no_daily_sales"]
    # Said, not hidden: a reader still learns why F8 published nothing.
    assert "NOTE  order_quantity: no_daily_sales" in err


def test_a_capability_with_registered_figures_that_is_unavailable_still_fails(monkeypatch, capsys):
    code, payload, err = _run(monkeypatch, capsys, {
        "reconciliation": _unavailable("no_sales_evidence"),
        "order_quantity": _unavailable("no_daily_sales"),
    })
    assert code == 1
    assert payload["unavailable"] == ["reconciliation: no_sales_evidence"]
    assert "FAIL  reconciliation: no_sales_evidence" in err


def test_a_missing_credential_is_still_a_note(monkeypatch, capsys):
    code, payload, _ = _run(monkeypatch, capsys, {"owner_questions": _unavailable("answer_storage_unavailable")})
    assert code == 0
    assert payload["needs_credentials"] == ["owner_questions: answer_storage_unavailable"]


def test_the_list_names_registered_capabilities_only():
    assert figures._REGISTERS_NO_FIGURE <= set(CAPABILITIES)


def test_the_list_agrees_with_what_the_committed_artefact_publishes():
    """The list is a claim about the engine, so it is checked against the engine's output.
    A capability on it that published a figure would hide that figure's loss; one missing
    from it that publishes none would make the command exit 1 for nothing. Only capabilities
    the artefact shows available can be judged: an unavailable one publishes nothing either
    way, and one registered since the last nightly is not in it yet."""
    artefact = json.loads((ROOT / "public" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    published = {key.split(".", 1)[0] for key in artefact["figures"]}
    for cap_id, cap in artefact["capabilities"].items():
        if cap.get("status") != "available":
            continue
        assert (cap_id in figures._REGISTERS_NO_FIGURE) == (cap_id not in published), cap_id


# ── "The same data" (AC-127) ─────────────────────────────────────────────────
#
# The market half is rebuilt on each machine from the committed snapshots, so a laptop's can
# be older than the artefact it is compared with. Then every figure that reads it differs and
# nothing says why: 15 of 47 on 2026-09-28, until the market half was rebuilt from the same
# day's snapshot (F7 validation record). A NOTE, never a FAIL: the engine is not wrong, the
# comparison is, so the exit code is what it would have been without it.

COMPETITOR_FIGURE = {"value": 5, "unit": "products", "inputs": ["pos", "competitor"], "thresholds": {}}


def _run_dated(monkeypatch, capsys, tmp_path, *, ours, committed, capabilities=None, committed_text=None):
    artefact = {"figures": {"price_consistency.inverted": FIGURE,
                            "competitor_position.matched": COMPETITOR_FIGURE,
                            "provenance.competitor_snapshot_age_days": {**FIGURE, "inputs": ["competitor"]}},
                "capabilities": capabilities or {"price_consistency": {"status": "available"}},
                "vintages": {"competitor": {"snapshot_date": ours}}}
    path = tmp_path / "dashboard.json"
    path.write_text(committed_text if committed_text is not None else
                    json.dumps({"vintages": {"competitor": {"snapshot_date": committed}}}), encoding="utf-8")
    monkeypatch.setattr(figures, "COMMITTED_ARTEFACT", path)
    monkeypatch.setattr(figures, "run_engine", lambda **_: {"artefact": artefact})
    monkeypatch.setattr(sys, "argv", ["figures.py", "--json"])
    code = figures.main()
    out, err = capsys.readouterr()
    return code, json.loads(out), err


def test_the_same_market_snapshot_says_nothing(monkeypatch, capsys, tmp_path):
    code, payload, err = _run_dated(monkeypatch, capsys, tmp_path, ours="2026-09-28", committed="2026-09-28")
    assert code == 0
    assert "market snapshot" not in err
    assert payload["market_snapshot"] == {"this_run": "2026-09-28", "committed": "2026-09-28"}


def test_an_older_local_market_half_is_named_with_the_figures_it_moves(monkeypatch, capsys, tmp_path):
    code, payload, err = _run_dated(monkeypatch, capsys, tmp_path, ours="2026-09-27", committed="2026-09-28")
    assert code == 0, "a NOTE must not change the exit code"
    note = next(line for line in err.splitlines() if "market snapshot" in line)
    assert note.startswith("NOTE")
    assert "2026-09-27" in note and "2026-09-28" in note
    # Exactly the figures that read the market: the POS-only one is not named.
    assert "competitor_position.matched" in note
    assert "provenance.competitor_snapshot_age_days" in note
    assert "price_consistency.inverted" not in note
    # How to get the same data, and the one way not to.
    assert "scripts/rehydrate_silver.py" in note
    assert "scripts/build_competitor_product_signals.py" in note
    assert "scripts/build_product_matches.py" in note
    assert "--skip-market" in note and "market-context.json" in note
    assert payload["market_snapshot"] == {"this_run": "2026-09-27", "committed": "2026-09-28"}


def test_no_local_market_half_at_all_is_named_too(monkeypatch, capsys, tmp_path):
    _, _, err = _run_dated(monkeypatch, capsys, tmp_path, ours=None, committed="2026-09-28")
    assert any("market snapshot" in line and "none" in line for line in err.splitlines())


def test_the_note_does_not_turn_a_failure_into_a_pass(monkeypatch, capsys, tmp_path):
    code, _, err = _run_dated(monkeypatch, capsys, tmp_path, ours="2026-09-27", committed="2026-09-28",
                              capabilities={"reconciliation": _unavailable("no_sales_evidence")})
    assert code == 1
    assert "FAIL  reconciliation: no_sales_evidence" in err
    assert any(line.startswith("NOTE") and "market snapshot" in line for line in err.splitlines())


def test_an_unreadable_committed_artefact_says_the_comparison_is_unknown(monkeypatch, capsys, tmp_path):
    code, payload, err = _run_dated(monkeypatch, capsys, tmp_path, ours="2026-09-28", committed=None,
                                    committed_text="{not json")
    assert code == 0
    assert any(line.startswith("NOTE") and "unknown" in line for line in err.splitlines())
    assert payload["market_snapshot"] == {"this_run": "2026-09-28", "committed": None}


def test_the_default_comparison_is_the_committed_artefact():
    assert figures.COMMITTED_ARTEFACT == ROOT / "public" / "data" / "dashboard.json"
