# tests/test_nightly_deploy_step.py
"""The nightly must hand what it committed to Vercel itself (#167).

Vercel's Hobby plan blocks a Git-triggered deployment of any commit whose author is not on
the team, and the nightly's commits are authored by `smartshelf-collector`. Measured on
2026-09-24 over 100 production deployments: 0 of 22 collector commits deployed, 78 of 78
human ones did. So a nightly artefact reached the owner only when a human happened to merge
something, 6.7 to 88.8 hours late.

The workflow now calls a Deploy Hook after the artefact commit. Like
test_nightly_commit_step.py, this runs the workflow's OWN script, extracted from the YAML,
against a stand-in `curl` on PATH. A copy retyped here would stay green while the real step
drifted.
"""
from pathlib import Path
import os
import stat
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "collect-daily.yml"
COMMIT_STEP = "Commit the owner's artefact"
DEPLOY_STEP = "Deploy what was just committed"


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


def _fake_curl(tmp_path: Path, *, prints: str, exit_code: int = 0) -> Path:
    """A `curl` that records its arguments and answers like the hook would."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    exe = bin_dir / "curl"
    exe.write_text("#!/bin/bash\n"
                   f'printf "%s\\n" "$@" > "{tmp_path}/curl-args"\n'
                   f"printf '%s' '{prints}'\n"
                   f"exit {exit_code}\n", encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    return bin_dir


def _run(tmp_path: Path, *, hook: str, prints: str = "", exit_code: int = 0):
    bin_dir = _fake_curl(tmp_path, prints=prints, exit_code=exit_code)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "VERCEL_DEPLOY_HOOK_URL": hook}
    return subprocess.run(["bash", "-e", "-c", _run_script(DEPLOY_STEP)],
                          cwd=tmp_path, env=env, capture_output=True, text=True)


def test_it_runs_only_when_the_artefact_was_committed():
    """No new artefact, nothing for the owner: the step keys on the commit step's output,
    which the commit step sets only after its push."""
    assert "if: steps.artefact.outputs.committed == 'true'" in _step_block(DEPLOY_STEP)
    commit = _run_script(COMMIT_STEP)
    assert "id: artefact" in _step_block(COMMIT_STEP)
    assert commit.index('echo "committed=true" >> "$GITHUB_OUTPUT"') > commit.index("git push origin HEAD:main"), \
        "the output must be set after the push, or a failed push would still deploy"


def test_a_queued_job_passes(tmp_path):
    out = _run(tmp_path, hook="https://api.vercel.com/v1/integrations/deploy/prj_x/y",
               prints='{"job":{"id":"G0K1","state":"PENDING"}}')
    assert out.returncode == 0, out.stderr


def test_it_sends_the_json_body_vercel_requires(tmp_path):
    """Measured 2026-09-24: a bare POST is refused with 415 Unsupported Media Type."""
    _run(tmp_path, hook="https://api.vercel.com/v1/integrations/deploy/prj_x/y", prints='{"job":{}}')
    args = (tmp_path / "curl-args").read_text().split("\n")
    assert "Content-Type: application/json" in args
    assert args[args.index("-d") + 1] == "{}"
    assert "-f" in "".join(a for a in args if a.startswith("-") and not a.startswith("--")), \
        "without -f an HTTP error would exit 0 and read as deployed"


def test_an_answer_without_a_job_fails_the_night(tmp_path):
    """Vercel answering, but not with a job, is not a deploy. Red, not green."""
    out = _run(tmp_path, hook="https://api.vercel.com/v1/integrations/deploy/prj_x/y",
               prints='{"error":{"code":"not_found","message":"Not Found"}}')
    assert out.returncode != 0
    assert "did not queue a job" in out.stdout + out.stderr


def test_an_http_error_fails_the_night(tmp_path):
    out = _run(tmp_path, hook="https://api.vercel.com/v1/integrations/deploy/prj_x/y", exit_code=22)
    assert out.returncode != 0


def test_a_missing_secret_warns_and_does_not_call_anything(tmp_path):
    """Warned, not silent: tonight's artefact would reach the owner only with the next human
    merge, and the run must say so."""
    out = _run(tmp_path, hook="", prints='{"job":{}}')
    assert out.returncode == 0
    assert "::warning::" in out.stdout and "#167" in out.stdout
    assert not (tmp_path / "curl-args").exists(), "no hook call without a hook"
