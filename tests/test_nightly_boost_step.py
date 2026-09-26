# tests/test_nightly_boost_step.py
"""Phase 5 Task 5.10: the nightly seals tonight's boost picks (ADR-035 Decision 2).

The picks are paid for, and a pick cannot be asked for again and get the same answer. So they
are committed in their own step, right after the engine and before the blocking probes: a
probe that fails must not throw away what was bought. data/external/ is gitignored, so the add
is forced, and it names only the picks, because the engine also rewrites silver/ (rule 9).

Read from the workflow file itself, and the step's own script is run against a scratch
repository with a local remote, so what is tested is what the nightly will execute.
"""
from pathlib import Path
import os
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "collect-daily.yml"


def _steps():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    (job,) = doc["jobs"].values()
    return job["steps"]


def _index(steps, predicate):
    matches = [i for i, s in enumerate(steps) if predicate(s)]
    assert len(matches) == 1, matches
    return matches[0]


def _boost_step(steps):
    return steps[_index(steps, lambda s: "boost picks" in (s.get("name") or "").lower())]


def test_the_picks_are_committed_after_the_engine_and_before_the_probes():
    steps = _steps()
    engine = _index(steps, lambda s: s.get("id") == "engine")
    boost = _index(steps, lambda s: "boost picks" in (s.get("name") or "").lower())
    probe = _index(steps, lambda s: "check_v1_signals.py" in (s.get("run") or ""))
    independence = _index(steps, lambda s: "check_independence.py" in (s.get("run") or ""))
    assert engine < boost < probe < independence


def test_it_runs_whether_or_not_the_engine_step_succeeded():
    """A pick paid for in a run that later errored is still paid for."""
    step = _boost_step(_steps())
    assert "always()" in step.get("if", "")


def test_it_force_adds_only_the_picks():
    script = _boost_step(_steps())["run"]
    adds = [line.strip() for line in script.splitlines() if line.strip().startswith("git add")]
    assert adds and all("-f" in a.split() and "boost_picks" in a for a in adds)
    assert "silver" not in script


def test_the_engine_gets_the_key_from_secrets_under_the_engines_own_name():
    """ADR-032: the secret is ANTHROPIC_API_KEY. The engine reads SMARTSHELF_ANTHROPIC_API_KEY,
    so a developer's own ANTHROPIC_API_KEY is never spent by a local data:refresh."""
    from src.engine.market_boost import KEY_ENV
    engine = _steps()[_index(_steps(), lambda s: s.get("id") == "engine")]
    assert engine["env"][KEY_ENV] == "${{ secrets.ANTHROPIC_API_KEY }}"


def _git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout


def _scratch(tmp_path):
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True, capture_output=True)
    (work / ".gitignore").write_text("data/external/\n", encoding="utf-8")
    _git(work, "checkout", "-q", "-b", "main")
    _git(work, "add", ".gitignore")
    _git(work, "commit", "-qm", "base")
    _git(work, "push", "-q", "origin", "main")
    return remote, work


def _run_step(work):
    script = _boost_step(_steps())["run"]
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid"}
    return subprocess.run(["bash", "-e", "-c", script], cwd=work, env=env, capture_output=True, text=True)


def test_the_step_commits_the_picks_and_nothing_else(tmp_path):
    remote, work = _scratch(tmp_path)
    picks = work / "data" / "external" / "snapshots" / "2026-09-27" / "boost_picks"
    picks.mkdir(parents=True)
    (picks / "picks.json").write_text("{}", encoding="utf-8")
    (picks / "_manifest.json").write_text('{"runs": []}', encoding="utf-8")
    silver = work / "data" / "external" / "silver"
    silver.mkdir(parents=True)
    (silver / "derived.parquet").write_bytes(b"x")
    done = _run_step(work)
    assert done.returncode == 0, done.stderr
    committed = _git(remote, "show", "--name-only", "--format=", "main").split()
    assert sorted(committed) == ["data/external/snapshots/2026-09-27/boost_picks/_manifest.json",
                                 "data/external/snapshots/2026-09-27/boost_picks/picks.json"]


def test_with_no_picks_it_commits_nothing_and_succeeds(tmp_path):
    """Tonight's case, with no key: the engine writes no picks, and the step is a no-op."""
    remote, work = _scratch(tmp_path)
    before = _git(remote, "rev-parse", "main")
    done = _run_step(work)
    assert done.returncode == 0, done.stderr
    assert _git(remote, "rev-parse", "main") == before
