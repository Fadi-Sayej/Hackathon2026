# tests/test_nightly_deploy_step.py
"""The nightly's artefact must reach the owner, and the run must say whether it did (#167).

Vercel's Hobby plan builds a commit only when its AUTHOR is the account owner. The nightly
committed as `smartshelf-collector`, and 0 of 22 of its commits deployed (measured
2026-09-24). The Deploy Hook tried next was blocked too, because a hook builds the head of
main and the block looks at that head's author (seen on Vercel's Deployments page,
2026-09-26). A probe that day settled the fix: pushed from Actions, an empty commit authored
by the owner deployed and one authored by the collector was blocked. The committer and the
pusher do not matter.

So the artefact commit is authored by the owner and committed by the collector, and a last
step reads GitHub's deployment record for that exact commit. Like
test_nightly_commit_step.py, this runs the workflow's OWN scripts, extracted from the YAML.
A copy retyped here would stay green while the real steps drifted.
"""
from pathlib import Path
import os
import stat
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "collect-daily.yml"
SNAPSHOT_STEP = "Commit the snapshot"
COMMIT_STEP = "Commit the owner's artefact"
CHECK_STEP = "Did Vercel deploy tonight's artefact?"

OWNER = "Fadi-Sayej <sayejfadi2004@gmail.com>"
COLLECTOR = "smartshelf-collector <41898282+github-actions[bot]@users.noreply.github.com>"
STRANGER = "collector@users.noreply.github.com"


def _step_block(name: str) -> str:
    """The YAML of one step: from its `- name:` line up to the next step."""
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.index(f"- name: {name}")
    nxt = text.find("\n      - name:", start + 1)
    return text[start:nxt if nxt != -1 else len(text)]


def _run_script(name: str) -> str:
    block = _step_block(name)
    body = block[block.index("run: |") + len("run: |"):]
    return "\n".join(raw[10:] if raw.startswith(" " * 10) else raw.strip()
                     for raw in body.splitlines())


def _steps() -> list:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["collect"]["steps"]


# ── The artefact commit ──────────────────────────────────────────────────────

def _git(cwd: Path, *args: str, env=None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True,
                          text=True, check=True).stdout.strip()


def _hermetic_env(tmp_path: Path) -> dict:
    """No global or system git config, and no GIT_* variable from the caller: a signing key
    or identity on the machine running the suite must not decide what the commit says, and a
    GIT_DIR exported by a git hook would point these commands at the real repository."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return {**env, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
            "GITHUB_OUTPUT": str(tmp_path / "github-output")}


def _remote_and_clone(tmp_path: Path, env: dict) -> tuple:
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, env=env)
    _git(remote, "symbolic-ref", "HEAD", "refs/heads/main", env=env)
    seed.mkdir()
    _git(seed, "init", "-q", env=env)
    _git(seed, "symbolic-ref", "HEAD", "refs/heads/main", env=env)
    data = seed / "public" / "data"
    data.mkdir(parents=True)
    (data / "dashboard.json").write_text('{"day":1}', encoding="utf-8")
    (data / "market-context.json").write_text("{}", encoding="utf-8")
    _git(seed, "add", ".", env=env)
    _git(seed, "-c", "user.name=seed", "-c", "user.email=seed@example.com",
         "commit", "-q", "-m", "seed", env=env)
    _git(seed, "push", "-q", str(remote), "main", env=env)
    subprocess.run(["git", "clone", "-q", str(remote), str(work)], check=True, env=env)
    (work / "public" / "data" / "dashboard.json").write_text('{"day":2}', encoding="utf-8")
    return remote, seed, work


def _run_commit_step(work: Path, env: dict):
    return subprocess.run(["bash", "-e", "-c", _run_script(COMMIT_STEP)],
                          cwd=work, env=env, capture_output=True, text=True)


def test_the_artefact_commit_is_authored_by_the_owner_and_committed_by_the_collector(tmp_path):
    """The author is what Vercel's Hobby block reads. The committer still says the nightly
    made it."""
    env = _hermetic_env(tmp_path)
    remote, _, work = _remote_and_clone(tmp_path, env)
    out = _run_commit_step(work, env)
    assert out.returncode == 0, out.stderr
    assert _git(remote, "log", "-1", "--format=%an <%ae>", "main", env=env) == OWNER
    assert _git(remote, "log", "-1", "--format=%cn <%ce>", "main", env=env) == COLLECTOR


def test_the_step_hands_the_check_the_sha_that_landed(tmp_path):
    """The check reads the record for this sha, so it must be the one on main, and it must be
    written after the push: a failed push has no deployment to wait for."""
    env = _hermetic_env(tmp_path)
    remote, _, work = _remote_and_clone(tmp_path, env)
    assert _run_commit_step(work, env).returncode == 0
    outputs = (tmp_path / "github-output").read_text().split()
    assert f"sha={_git(remote, 'rev-parse', 'main', env=env)}" in outputs
    assert "committed=true" in outputs
    script = _run_script(COMMIT_STEP)
    assert script.index('echo "sha=') > script.index("git push origin HEAD:main")


def test_a_rebase_onto_a_newer_main_keeps_the_owner_as_author(tmp_path):
    """Another commit can land on main while the engine runs. The step rebases onto it, and
    the commit that reaches main must still be the owner's, or it is blocked again."""
    env = _hermetic_env(tmp_path)
    remote, seed, work = _remote_and_clone(tmp_path, env)
    (seed / "unrelated.txt").write_text("landed meanwhile", encoding="utf-8")
    _git(seed, "add", "unrelated.txt", env=env)
    _git(seed, "-c", "user.name=someone", "-c", "user.email=someone@example.com",
         "commit", "-q", "-m", "meanwhile", env=env)
    _git(seed, "push", "-q", str(remote), "main", env=env)

    out = _run_commit_step(work, env)
    assert out.returncode == 0, out.stderr
    assert _git(remote, "log", "-1", "--format=%s", "main~1", env=env) == "meanwhile"
    assert _git(remote, "log", "-1", "--format=%an <%ae>", "main", env=env) == OWNER
    assert _git(remote, "log", "-1", "--format=%cn <%ce>", "main", env=env) == COLLECTOR
    outputs = (tmp_path / "github-output").read_text().split()
    assert f"sha={_git(remote, 'rev-parse', 'main', env=env)}" in outputs


def test_a_conflicting_commit_on_main_fails_the_step_and_hands_over_nothing(tmp_path):
    """A human commit to dashboard.json during the run stops the rebase on a conflict. The
    step used to push nothing and still say committed=true, and the check would then have
    read that human commit, which deployed, as tonight's artefact."""
    env = _hermetic_env(tmp_path)
    remote, seed, work = _remote_and_clone(tmp_path, env)
    (seed / "public" / "data" / "dashboard.json").write_text('{"day":"human"}', encoding="utf-8")
    _git(seed, "add", "public/data/dashboard.json", env=env)
    _git(seed, "-c", "user.name=someone", "-c", "user.email=someone@example.com",
         "commit", "-q", "-m", "hand edit", env=env)
    _git(seed, "push", "-q", str(remote), "main", env=env)
    human = _git(remote, "rev-parse", "main", env=env)

    out = _run_commit_step(work, env)
    assert out.returncode != 0
    assert "could not be rebased" in out.stdout
    assert _git(remote, "rev-parse", "main", env=env) == human
    output = tmp_path / "github-output"
    assert not output.exists() or "committed=true" not in output.read_text()
    assert not output.exists() or "sha=" not in output.read_text()


def test_neither_commit_step_uses_the_strangers_address():
    """collector@users.noreply.github.com is GitHub's old no-reply form for the account
    `collector` (id 1460107), which is not ours. Every nightly commit until 2026-09-26 was
    attributed to it."""
    for name in (SNAPSHOT_STEP, COMMIT_STEP):
        script = _run_script(name)
        assert STRANGER not in script
        assert 'git config user.email "41898282+github-actions[bot]@users.noreply.github.com"' in script


def test_the_snapshot_commit_stays_the_collectors():
    """Nothing under data/ is in the built site, so the snapshot has nothing to deploy and
    carries no one's name but the collector's."""
    assert "--author" not in _run_script(SNAPSHOT_STEP)


def test_the_hook_is_gone():
    """It queued builds that were then blocked, and it was green while it did."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "VERCEL_DEPLOY_HOOK_URL" not in text
    assert "Deploy what was just committed" not in text


# ── The deployment check ─────────────────────────────────────────────────────

def _fakes(tmp_path: Path, answers: list) -> Path:
    """A `gh` that gives the next queued answer on each call (none left = empty, which is
    what the real one prints when there is no deployment yet), and a `sleep` that only
    counts. Answers use \\t between a status's state and its description; `!fail` makes
    that call fail the way an API error does."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (tmp_path / "answers").write_text("".join(f"{a}\n" for a in answers), encoding="utf-8")
    gh = bin_dir / "gh"
    gh.write_text("#!/bin/bash\n"
                  f'printf "%s\\n" "$*" >> "{tmp_path}/gh-calls"\n'
                  f'n=$(( $(cat "{tmp_path}/gh-count" 2>/dev/null || echo 0) + 1 ))\n'
                  f'echo "$n" > "{tmp_path}/gh-count"\n'
                  f'answer=$(sed -n "${{n}}p" "{tmp_path}/answers")\n'
                  'if [ "$answer" = "!fail" ]; then echo "HTTP 502" >&2; exit 1; fi\n'
                  'printf "%b" "$answer"\n',
                  encoding="utf-8")
    sleep = bin_dir / "sleep"
    sleep.write_text(f'#!/bin/bash\necho "$1" >> "{tmp_path}/sleeps"\n', encoding="utf-8")
    for exe in (gh, sleep):
        exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return bin_dir


def _check(tmp_path: Path, answers: list, sha: str = "abc1234def"):
    bin_dir = _fakes(tmp_path, answers)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
           "REPO": "Fadi-Sayej/Hackathon2026", "SHA": sha, "GH_TOKEN": "t"}
    return subprocess.run(["bash", "-e", "-c", _run_script(CHECK_STEP)],
                          cwd=tmp_path, env=env, capture_output=True, text=True)


def _sleeps(tmp_path: Path) -> int:
    f = tmp_path / "sleeps"
    return len(f.read_text().split()) if f.exists() else 0


def test_a_completed_deployment_passes(tmp_path):
    out = _check(tmp_path, ["4242", "success\\tDeployment has completed"])
    assert out.returncode == 0, out.stderr
    assert "Deployment has completed" in out.stdout


def test_a_blocked_deployment_fails_the_night(tmp_path):
    """The case #167 is about: 0 of 22 collector commits deployed, and every run was green."""
    out = _check(tmp_path, ["4242", "failure\\tDeployment was blocked"])
    assert out.returncode != 0
    assert "::error::" in out.stdout and "Deployment was blocked" in out.stdout
    assert "#167" in out.stdout


def test_an_errored_build_fails_the_night(tmp_path):
    out = _check(tmp_path, ["4242", "error\\tDeployment has failed"])
    assert out.returncode != 0
    assert "Deployment has failed" in out.stdout


def test_it_waits_while_the_record_is_missing_or_pending(tmp_path):
    """Vercel writes the record some time after the push. A missing record or a pending
    status is a reason to look again, not a verdict."""
    out = _check(tmp_path, ["", "", "4242", "pending\\t", "4242", "success\\tDeployment has completed"])
    assert out.returncode == 0, out.stderr
    assert _sleeps(tmp_path) == 3


def test_a_failed_api_call_is_one_more_look_not_a_verdict(tmp_path):
    """One 502 from GitHub used to end the step red under bash -e, with nothing lost."""
    out = _check(tmp_path, ["!fail", "4242", "!fail", "4242", "success\\tDeployment has completed"])
    assert out.returncode == 0, out.stderr
    assert _sleeps(tmp_path) == 2


def test_an_empty_sha_is_refused_before_any_lookup(tmp_path):
    """An empty sha would match every production deployment, and the newest may be a success
    from another day."""
    out = _check(tmp_path, ["4242", "success\\tDeployment has completed"], sha="")
    assert out.returncode != 0
    assert "no sha" in out.stdout
    assert not (tmp_path / "gh-calls").exists()


def test_no_deployment_at_all_fails_after_thirty_looks(tmp_path):
    """No record at all is not a pass: the owner may still be on yesterday's artefact."""
    out = _check(tmp_path, [])
    assert out.returncode != 0
    assert "No finished production deployment" in out.stdout
    assert _sleeps(tmp_path) == 30
    assert (tmp_path / "gh-count").read_text().strip() == "30"


def test_it_reads_the_production_record_for_exactly_this_sha(tmp_path):
    _check(tmp_path, ["4242", "success\\tDeployment has completed"], sha="0123abcd")
    calls = (tmp_path / "gh-calls").read_text().splitlines()
    assert calls[0].startswith("api repos/Fadi-Sayej/Hackathon2026/deployments?sha=0123abcd&environment=Production")
    assert calls[1].startswith("api repos/Fadi-Sayej/Hackathon2026/deployments/4242/statuses")


def test_it_runs_after_a_commit_even_when_an_earlier_check_failed():
    """A failed health check does not stop the push from deploying; the run should still say
    whether it did. It stays off when nothing was committed or the run was cancelled."""
    step = next(s for s in _steps() if s.get("name", "").startswith(CHECK_STEP))
    assert "steps.artefact.outputs.committed == 'true'" in step["if"]
    assert "!cancelled()" in step["if"]
    assert step["env"]["SHA"] == "${{ steps.artefact.outputs.sha }}"


def test_it_comes_after_the_checks_that_do_not_wait_on_it():
    names = [s.get("name", "") for s in _steps()]
    check = next(i for i, n in enumerate(names) if n.startswith(CHECK_STEP))
    assert check > names.index("Health check after collecting")
    assert check > names.index("Are the deployed Firestore rules the ones in this repository?")


def test_the_job_may_read_deployments_and_nothing_more_than_before():
    perms = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["permissions"]
    assert perms == {"contents": "write", "deployments": "read"}
