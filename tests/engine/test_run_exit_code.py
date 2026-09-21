# tests/engine/test_run_exit_code.py
"""`run_engine.py`'s exit code decides whether the owner's artefact gets committed.

`collect-daily.yml` runs the engine as a step with no `continue-on-error`, and the commit
step comes after it. So a non-zero exit does not merely mark the run — it aborts the job
before `git add`, and the artefact the engine just published into the runner's workspace is
thrown away. That is rule 12 at the top of the pipeline, and the workflow's own comment
describes the 2026-09-13 instance of it: *"the gate that followed exited 1, so this step
never ran and the owner's artefact was never rebuilt — for a failure in a chain it does not
use."*

`degraded` and `partial` are honest states of a **published** artefact, not failures to
publish one:

  - owner state unavailable — any Firestore exception, including a transient one
  - `imported_this_run is False` — sales continued on evidence already on disk, which
    ADR-017 calls a normal day and which the workflow's next step promises "does NOT fail
    the build"
  - a capability that raised, which is recorded as `capability_error` and published

Each is reported four ways already. None of them means "there is no artefact". So the exit
code answers the one question the workflow actually asks of it.
"""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import src.engine.run as run_mod
from src.engine.model import CapabilityOutput
from src.owner_state.model import OwnerState

ROOT = Path(__file__).resolve().parents[2]


def _isolate(monkeypatch, tmp_path, owner):
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: owner)
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "SILVER_DIR", tmp_path / "silver")
    monkeypatch.setattr(run_mod, "SIGNALS_DIR", tmp_path / "signals")
    monkeypatch.setattr(run_mod, "MATCHES_PATH", tmp_path / "matches.parquet")


def test_a_degraded_run_still_publishes(tmp_path, monkeypatch):
    """The precondition for the exit-code rule: degraded is a state of a published
    artefact, not a failure to publish one. If this ever stops being true the rule below
    needs revisiting rather than the test being updated."""
    _isolate(monkeypatch, tmp_path, OwnerState.unavailable("pull_failed: ConnectionError"))
    target = tmp_path / "dashboard.json"
    result = run_mod.run_engine(mode="publish", artefact_path=target, capability_runners={},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result["status"] == "degraded"
    assert result["published"] is True and target.exists()


def test_a_capability_error_is_partial_and_still_publishes(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path, OwnerState.from_dict({"status": "available", "pulled_at": "t"}))

    def boom(inputs):
        raise RuntimeError("bug")

    def fine(inputs):
        return CapabilityOutput(id="reconciliation", spec="SPEC-002", status="available")

    # One that raises BESIDE one that works. With only the raising one, every capability is
    # unavailable and publish refuses outright — which is correct, and which the CLI test
    # below covers as the case that genuinely means "no fresh artefact".
    result = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json",
                                capability_runners={"price_consistency": boom,
                                                    "reconciliation": fine},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result["status"] in ("partial", "degraded")
    assert result["published"] is True
    assert result["artefact"]["capabilities"]["price_consistency"]["unavailable_reason"] == "capability_error"


def _main_with(monkeypatch, *, status, published, argv=("run_engine.py",)):
    """Drive the CLI's own exit decision with a canned run result.

    Through `main()` rather than through `run_engine()`, because the exit code is a fact
    about the CLI and nothing else reads it. Canned rather than real, because the rule must
    be asserted for combinations a real run cannot easily be forced into — and because a
    test that can only reach one branch is how the first version of this file passed with
    the rule reverted.
    """
    import importlib
    cli = importlib.import_module("scripts.run_engine")
    monkeypatch.setattr(cli, "run_engine",
                        lambda **kw: {"status": status, "published": published,
                                      "steps": [], "artefact": {}})
    monkeypatch.setattr(sys, "argv", list(argv))
    return cli.main()


def test_a_published_artefact_exits_zero_however_degraded(monkeypatch):
    """THE rule. Under the old one — `0 if status == "ok" else 1` — every line here exits 1,
    the nightly step fails, and the job aborts before the artefact is committed."""
    for status in ("ok", "degraded", "partial"):
        assert _main_with(monkeypatch, status=status, published=True) == 0, status


def test_no_artefact_still_exits_non_zero(monkeypatch):
    """The case that genuinely means the nightly has nothing to commit, and must stay loud:
    publish refused, so the last good artefact is what the owner keeps."""
    for status in ("ok", "degraded", "partial"):
        assert _main_with(monkeypatch, status=status, published=False) == 1, status


def test_print_mode_keeps_judging_by_status(monkeypatch):
    """Print mode publishes nothing by design, so `published` cannot be the question there.
    A reproduction that degrades must still say so."""
    assert _main_with(monkeypatch, status="ok", published=False, argv=("run_engine.py", "--print")) == 0
    assert _main_with(monkeypatch, status="degraded", published=False, argv=("run_engine.py", "--print")) == 1


def test_the_workflow_has_no_continue_on_error_on_the_engine_step():
    """Why the exit code matters at all. If someone adds `continue-on-error: true` here,
    this rule becomes belt-and-braces rather than load-bearing — worth knowing deliberately
    rather than discovering that two mechanisms guard the same thing."""
    workflow = (ROOT / ".github" / "workflows" / "collect-daily.yml").read_text(encoding="utf-8")
    step = workflow[workflow.index("- name: Run the engine and publish the artefact"):]
    step = step[:step.index("- name: Say plainly")]
    assert "continue-on-error" not in step
    assert "run_engine.py" in step
