"""The deploy preflight checks the data the owner's app actually reads.

Until 2026-09-24 scripts/preflight_deploy.sh section 2 checked only
public/data/operational.json, which no owner page has read since the 2026-09-12
cut-over. A deploy with dashboard.json missing, uncommitted or refused by the engine's
own validator passed the preflight. These tests drive scripts/check_deploy_data.py
over a throwaway git repository holding trimmed copies of the real committed files.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.check_deploy_data import check  # noqa: E402

DATA = ROOT / "public" / "data"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   cwd=repo, check=True, capture_output=True)


def _trimmed_artefact() -> dict:
    doc = json.loads((DATA / "dashboard.json").read_text(encoding="utf-8"))
    for cap in doc["capabilities"].values():
        if isinstance(cap.get("entries"), list):
            cap["entries"] = cap["entries"][:3]
    return doc


def _trimmed_catalogue() -> dict:
    doc = json.loads((DATA / "catalogue.json").read_text(encoding="utf-8"))
    doc["products"] = doc["products"][:5]
    doc["count"] = len(doc["products"])
    return doc


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A committed, deployable data set: the three files the deploy serves."""
    data = tmp_path / "public" / "data"
    data.mkdir(parents=True)
    (data / "dashboard.json").write_text(json.dumps(_trimmed_artefact()), encoding="utf-8")
    (data / "catalogue.json").write_text(json.dumps(_trimmed_catalogue()), encoding="utf-8")
    (data / "operational.json").write_text(json.dumps({"recommendations": [{"id": "r1"}, {"id": "r2"}]}),
                                           encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "public/data")
    _git(tmp_path, "commit", "-qm", "data")
    return tmp_path


def _generated_at(repo: Path) -> datetime:
    doc = json.loads((repo / "public/data/dashboard.json").read_text(encoding="utf-8"))
    return datetime.fromisoformat(doc["generated_at"].replace("Z", "+00:00"))


def _levels(findings, needle: str) -> set[str]:
    return {level for level, message in findings if needle in message}


def test_a_committed_deployable_set_passes(repo):
    findings = check(repo, now=_generated_at(repo) + timedelta(hours=6))
    assert not [f for f in findings if f[0] == "BAD"], findings
    for name in ("dashboard.json", "catalogue.json", "operational.json"):
        assert "OK" in _levels(findings, name), (name, findings)


def test_a_missing_artefact_blocks_the_deploy(repo):
    (repo / "public/data/dashboard.json").unlink()
    assert "BAD" in _levels(check(repo, now=datetime.now(timezone.utc)), "dashboard.json")


def test_an_artefact_that_is_not_committed_blocks_the_deploy(repo):
    _git(repo, "rm", "-q", "--cached", "public/data/dashboard.json")
    findings = check(repo, now=_generated_at(repo))
    assert any(level == "BAD" and "NOT COMMITTED" in message for level, message in findings), findings


def test_local_edits_to_a_committed_artefact_warn(repo):
    path = repo / "public/data/dashboard.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    findings = check(repo, now=_generated_at(repo))
    assert any(level == "WARN" and "uncommitted changes" in message for level, message in findings), findings


def test_an_artefact_the_publisher_would_refuse_blocks_the_deploy(repo):
    """ADR-014: the shipped artefact carries the whole registry. One missing capability
    would render as 'nothing to act on' instead of 'unavailable'."""
    path = repo / "public/data/dashboard.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["capabilities"].pop(next(iter(doc["capabilities"])))
    path.write_text(json.dumps(doc), encoding="utf-8")
    _git(repo, "commit", "-qam", "drop a capability")
    assert "BAD" in _levels(check(repo, now=_generated_at(repo)), "dashboard.json")


def test_an_empty_catalogue_blocks_the_deploy(repo):
    path = repo / "public/data/catalogue.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["products"], doc["count"] = [], 0
    path.write_text(json.dumps(doc), encoding="utf-8")
    _git(repo, "commit", "-qam", "empty catalogue")
    assert "BAD" in _levels(check(repo, now=_generated_at(repo)), "catalogue.json")


def test_an_artefact_older_than_two_nightlies_warns(repo):
    findings = check(repo, now=_generated_at(repo) + timedelta(days=3))
    assert "WARN" in _levels(findings, "dashboard.json"), findings
    assert not [f for f in findings if f[0] == "BAD"], findings


def test_the_telemetry_input_is_still_checked_until_f13(repo):
    _git(repo, "rm", "-q", "public/data/operational.json")
    _git(repo, "commit", "-qm", "lose the telemetry input")
    assert "BAD" in _levels(check(repo, now=_generated_at(repo)), "operational.json")


def test_the_real_committed_data_passes():
    """What the repository holds today must pass, or the preflight blocks every deploy."""
    if shutil.which("git") is None:
        pytest.skip("git not on PATH")
    findings = check(ROOT, now=datetime.now(timezone.utc))
    assert not [f for f in findings if f[0] == "BAD"], findings
