# tests/test_new_store_copy.py
"""ADR-036 §3, D-28: a new store's copy carries the code and none of this store's data.

The copy is written into a new directory with one commit and no history, so nothing this store
ever committed travels with it. Its store settings start empty. `--update` brings code across
later and never touches the other store's data or settings.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.store import STARTS_EMPTY, StoreSettingsError, get_store, is_store_data, load_store  # noqa: E402

ENV = {**os.environ, "GIT_AUTHOR_NAME": "copy-test", "GIT_AUTHOR_EMAIL": "copy-test@localhost",
       "GIT_COMMITTER_NAME": "copy-test", "GIT_COMMITTER_EMAIL": "copy-test@localhost"}
STORE_B = {"id": "store-b", "name": "Store B", "site_title": "SmartShelf AI — Store B",
           "location": {"lat": 31.25, "lon": 34.79}, "format": "urban_minimarket",
           "pos": {"export": "store-b-inventory.csv"},
           "sales": {"monthly_dir": "data/internal/raw_pos/store-b/sales",
                     "daily_dir": "data/internal/raw_pos/store-b/sales_daily"},
           "market": {"radius_km": 5}, "firebase": {"project_id": "store-b-project"},
           "site": {"address": "store-b.example.app"}}


def _run(*args, cwd=ROOT):
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, env=ENV)


def _module():
    spec = importlib.util.spec_from_file_location("new_store_copy", ROOT / "scripts" / "new_store_copy.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def copy(tmp_path_factory):
    dest = tmp_path_factory.mktemp("copies") / "store-b"
    result = _run("scripts/new_store_copy.py", str(dest))
    assert result.returncode == 0, result.stderr
    return dest


def _files(dest: Path) -> set:
    return {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file() and ".git" not in p.parts}


def test_no_data_of_this_store_is_copied(copy):
    store = get_store()
    inherited = {rel for rel in _files(copy) if is_store_data(rel, store) and rel not in STARTS_EMPTY}
    assert inherited == set()
    assert not (copy / store.pos_export.name).exists()
    assert not (copy / "public" / "data" / "dashboard.json").exists()
    assert not (copy / "data" / "owner").exists()
    assert (copy / "docs" / "pilot" / "next-store.md").exists()


def test_every_setting_starts_empty_and_names_nothing_of_this_store(copy):
    module = _module()
    assert module.leaks(copy, get_store()) == []
    for rel in STARTS_EMPTY:
        assert (copy / rel).exists(), rel
    with pytest.raises(StoreSettingsError, match="`id`"):
        load_store(copy / "configs" / "store.yaml")
    types = yaml.safe_load((copy / "configs" / "store_types.yaml").read_text(encoding="utf-8"))
    assert types["stores"] == {} and types["formats"] and types["affinity"]


def test_the_copy_has_one_commit_and_no_history(copy):
    log = subprocess.run(["git", "log", "--oneline"], cwd=copy, capture_output=True, text=True).stdout
    assert len(log.strip().splitlines()) == 1


def test_the_copy_runs_its_nightly_but_not_this_repositorys_ci(copy):
    assert (copy / ".github" / "workflows" / "collect-daily.yml").exists()
    assert not (copy / ".github" / "workflows" / "ci.yml").exists()


def test_a_filled_copy_says_every_input_is_still_to_supply(copy):
    (copy / "configs" / "store.yaml").write_text(yaml.safe_dump(STORE_B, allow_unicode=True), encoding="utf-8")
    result = _run("scripts/check_store.py", "--no-github", cwd=copy)
    assert result.returncode == 0, result.stderr
    assert "Store: Store B (store-b)" in result.stdout
    for label in ("POS inventory export", "Monthly sales reports", "Daily sales reports",
                  "Department order days", "The store's own entries", "Nearby venues collected"):
        assert f"✗ {label}" in result.stdout, label


def test_an_update_carries_code_and_leaves_the_stores_data(copy):
    (copy / "src" / "engine" / "run.py").write_text("# stale\n", encoding="utf-8")
    facts = copy / "configs" / "store_facts.yaml"
    facts.write_text("departments: {bakery: {shelf_life_days: 2}}\n", encoding="utf-8")
    gone = copy / "scripts" / "removed_upstream.py"
    gone.write_text("print('old')\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=copy, check=True, env=ENV)
    subprocess.run(["git", "commit", "-q", "-m", "store b's own changes"], cwd=copy, check=True, env=ENV)

    result = _run("scripts/new_store_copy.py", "--update", str(copy))
    assert result.returncode == 0, result.stderr
    assert (copy / "src" / "engine" / "run.py").read_bytes() == (ROOT / "src" / "engine" / "run.py").read_bytes()
    assert facts.read_text(encoding="utf-8") == "departments: {bakery: {shelf_life_days: 2}}\n"
    assert not gone.exists()


def test_a_directory_that_is_not_empty_is_refused(tmp_path):
    (tmp_path / "something").write_text("x", encoding="utf-8")
    assert _run("scripts/new_store_copy.py", str(tmp_path)).returncode == 1


def test_a_template_holding_this_stores_name_is_refused(tmp_path, monkeypatch):
    module = _module()
    store = get_store()
    real = module.templates
    monkeypatch.setattr(module, "templates", lambda s: {**real(s), "configs/store_facts.yaml": f"# {store.name}\n"})
    monkeypatch.setattr(module.subprocess, "run", subprocess.run)
    assert module.make_copy(tmp_path / "leaky", store) == 1
