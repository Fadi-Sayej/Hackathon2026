# tests/test_vercelignore.py
"""Vercel uploads only what .vercelignore lets through, then builds. The build must find its inputs.

ADR-036 made the build read configs/store.yaml through scripts/store_settings.mjs (the tab
title), and .vercelignore excluded both folders whole. The first production deploy after
#268 failed on it, while every local build, which has the whole tree, passed. So the rules are
asked here the way Vercel reads them: .vercelignore uses .gitignore's syntax, and git answers.

The other half matters as much: the store's own export at the root never goes to Vercel.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BUILD_NEEDS = ["vite.config.js", "index.html", "telemetry.html", "package.json",
               "scripts/store_settings.mjs", "configs/store.yaml", "src/main.jsx"]
NEVER_UPLOADED = ["yomyom-inventory.csv", "store-b-inventory.csv", "configs/policy.yaml",
                  "scripts/check_store.py", "docs/README.md", "data/internal/x.csv", ".env"]


def _ignored(tmp_path: Path, paths: list) -> set:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    shutil.copy(ROOT / ".vercelignore", tmp_path / ".gitignore")
    for rel in paths:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
    result = subprocess.run(["git", "-C", str(tmp_path), "check-ignore", "--no-index", *paths],
                            capture_output=True, text=True)
    return set(result.stdout.split())


def test_everything_the_build_reads_is_uploaded(tmp_path):
    assert _ignored(tmp_path, BUILD_NEEDS) == set()


def test_store_data_and_tooling_stay_off_vercel(tmp_path):
    assert _ignored(tmp_path, NEVER_UPLOADED) == set(NEVER_UPLOADED)
