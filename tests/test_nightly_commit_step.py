# tests/test_nightly_commit_step.py
"""The nightly must commit the owner's artefact even when the catalogue is absent.

`run_engine` isolates the catalogue deliberately: it is written after the artefact, as its
own recorded step, and it does not raise, because the artefact is the owner's daily screen
and the catalogue serves three secondary pages (ADR-024).

The workflow can undo that in one line. `git add` with a missing pathspec exits 128 and
stages **nothing** — not even the paths that did exist — and the step runs under `bash -e`,
so the commit never happens and the nightly publishes an artefact it then throws away.
That is rule 12 at the top of the pipeline, and it fires on precisely the case the Python
isolation was written to survive.

So this runs the workflow's OWN `git add` lines, extracted from the YAML rather than
retyped, against a repository where `catalogue.json` does not exist. Retyping them would
test a copy; someone tidying the real block onto one line is the regression, and a copy
would stay green through it.
"""
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "collect-daily.yml"
STEP = "Commit the owner's artefact"


def _staging_script() -> str:
    """The `git add` half of the commit step, verbatim, up to the staged-empty check."""
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.index(f"- name: {STEP}")
    body = text[text.index("run: |", start) + len("run: |"):]
    lines = []
    for raw in body.splitlines():
        if raw.strip().startswith("if git diff --cached --quiet"):
            break
        lines.append(raw[10:] if raw.startswith(" " * 10) else raw.strip())
    script = "\n".join(lines)
    assert "git add" in script, "did not find the staging lines in the workflow"
    # `git config` in the extracted block would set identity on the temp repo, which is
    # what we want; nothing else in it touches the network.
    assert "git push" not in script and "git commit" not in script, (
        "extraction reached past the staging lines — this test must never push or commit")
    return script


def _repo(tmp_path: Path, *, with_catalogue: bool) -> Path:
    subprocess.run(["git", "init", "-q", "."], cwd=tmp_path, check=True)
    data = tmp_path / "public" / "data"
    data.mkdir(parents=True)
    (data / "dashboard.json").write_text('{"schema_version":2}', encoding="utf-8")
    (data / "market-context.json").write_text("{}", encoding="utf-8")
    if with_catalogue:
        (data / "catalogue.json").write_text('{"schema_version":1}', encoding="utf-8")
    return tmp_path


def _staged(repo: Path) -> set:
    out = subprocess.run(["git", "diff", "--cached", "--name-only"],
                         cwd=repo, capture_output=True, text=True, check=True)
    return {line for line in out.stdout.split() if line}


def _run(repo: Path):
    # `bash -e` is what GitHub Actions gives a `run: |` block, and the -e is the whole
    # point: without it a failed `git add` would merely print and carry on.
    return subprocess.run(["bash", "-e", "-c", _staging_script()],
                          cwd=repo, capture_output=True, text=True)


def test_the_artefact_is_staged_when_the_catalogue_was_never_written(tmp_path):
    """The case ADR-024's isolation exists for: the catalogue step failed, the artefact is
    fine. The owner's screen must still update."""
    repo = _repo(tmp_path, with_catalogue=False)
    result = _run(repo)
    assert result.returncode == 0, f"staging aborted: {result.stderr}"
    assert "public/data/dashboard.json" in _staged(repo)
    assert "public/data/market-context.json" in _staged(repo)


def test_the_catalogue_is_staged_when_it_is_there(tmp_path):
    repo = _repo(tmp_path, with_catalogue=True)
    assert _run(repo).returncode == 0
    assert "public/data/catalogue.json" in _staged(repo)


def test_a_single_git_add_over_all_three_would_fail_this(tmp_path):
    """The regression this file exists to catch, demonstrated rather than described: the
    one-line form someone will tidy the block back into stages NOTHING when a path is
    missing, so the guard above is not stylistic."""
    repo = _repo(tmp_path, with_catalogue=False)
    naive = ("git add public/data/dashboard.json public/data/market-context.json "
             "public/data/catalogue.json")
    result = subprocess.run(["bash", "-e", "-c", naive], cwd=repo,
                            capture_output=True, text=True)
    assert result.returncode == 128
    assert _staged(repo) == set(), (
        "git add is expected to stage nothing at all when one pathspec is missing; "
        "if this ever changes, the workflow guard can be simplified")
