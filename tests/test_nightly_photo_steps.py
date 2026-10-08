# tests/test_nightly_photo_steps.py
"""The nightly's shelf-photo steps (ADR-042, F12-S1 FR-226): what they commit, and when they delete.

As tests/test_nightly_commit_step.py does, this runs the workflow's OWN `git add` lines, read
from the YAML, in a scratch repository. A night with no photo must stage nothing and not fail;
a night with photos must stage the photos, the readings, the pictures and the sealed answers,
which sit under the ignored data/external/.
"""
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "collect-daily.yml"
COMMIT = "Commit the shelf photos, the owner's units and what the reader read"
DELETE = "Remove the collected photos from Firestore"


def _steps() -> list:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["collect"]["steps"]


def _step(name: str) -> dict:
    return next(s for s in _steps() if s.get("name") == name)


def _staging_script() -> str:
    lines = []
    for line in _step(COMMIT)["run"].splitlines():
        if line.strip().startswith("if git diff --cached --quiet"):
            break
        lines.append(line)
    script = "\n".join(lines)
    assert "git add" in script and "git push" not in script and "git commit" not in script
    return script


def _repo(tmp_path: Path, *, with_photos: bool) -> Path:
    subprocess.run(["git", "init", "-q", "."], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("data/external/\n", encoding="utf-8")
    if with_photos:
        files = {
            "data/internal/shelf_photos/2026-10-10/מקרר 1/p1.jpg": b"\xff\xd8\xff",
            "configs/shelf_readings.yaml": b"reading: {day: '2026-10-10'}\n",
            "configs/store_layout.yaml": b"fixtures: {}\n",
            "public/store/shelf-pictures/7290001.jpg": b"\xff\xd8\xff",
            "data/external/snapshots/2026-10-10/shelf_readings/answers.json": b"{}",
        }
        for rel, data in files.items():
            (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / rel).write_bytes(data)
    return tmp_path


def _staged(repo: Path) -> set:
    out = subprocess.run(["git", "-c", "core.quotepath=off", "diff", "--cached", "--name-only"],
                         cwd=repo, capture_output=True, text=True, check=True)
    return set(out.stdout.splitlines())


def _run(repo: Path):
    return subprocess.run(["bash", "-e", "-c", _staging_script()], cwd=repo, capture_output=True, text=True)


def test_a_night_with_no_photo_stages_nothing_and_does_not_fail(tmp_path):
    repo = _repo(tmp_path, with_photos=False)
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    assert _staged(repo) == set()


def test_a_night_with_photos_stages_them_with_what_was_read(tmp_path):
    repo = _repo(tmp_path, with_photos=True)
    assert _run(repo).returncode == 0
    assert _staged(repo) == {
        "data/internal/shelf_photos/2026-10-10/מקרר 1/p1.jpg",
        "configs/shelf_readings.yaml",
        "configs/store_layout.yaml",
        "public/store/shelf-pictures/7290001.jpg",
        "data/external/snapshots/2026-10-10/shelf_readings/answers.json",
    }


def test_the_photos_are_deleted_only_after_their_push_succeeded():
    names = [s.get("name") for s in _steps()]
    collect, read = names.index("Collect what the owner sent from the app"), names.index("Read the shelf photos not read yet")
    commit, delete, engine = names.index(COMMIT), names.index(DELETE), names.index("Run the engine and publish the artefact")
    assert collect < read < commit < delete < engine
    assert _step(DELETE)["if"] == "steps.photos_commit.outcome == 'success'"
    assert _step(COMMIT)["id"] == "photos_commit"
    # None of the four can stop the night: the engine still runs.
    assert all(_step(n).get("continue-on-error") is True for n in names[collect:delete + 1])
