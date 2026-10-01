# tests/test_import_scripts.py
"""ADR-036: the importers read the store's files from configs/store.yaml.

They were import_yomyom_pos.py (with --input yomyom-inventory.csv in every instruction) and
import_yomyom_sales.py (with YomYom's folder as its default). A second store would have run
scripts named after another store, pointed at that store's files.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.store import get_store  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_pos_importer_takes_the_export_from_the_settings():
    args = _load("import_pos").parse_args([])
    assert args.input == get_store().pos_export


def test_the_sales_importer_takes_its_folder_from_the_settings():
    assert _load("import_sales").DEFAULT_DIR == get_store().sales_monthly_dir


def test_no_importer_is_named_after_a_store():
    names = {p.name for p in (ROOT / "scripts").glob("*.py")}
    assert not {n for n in names if "yomyom" in n}, "an entry point still carries a store's name"


def test_a_missing_export_is_named_and_imports_nothing(tmp_path):
    result = subprocess.run([sys.executable, "scripts/import_pos.py", "--input", str(tmp_path / "none.csv")],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 1
    assert "none.csv" in result.stderr
