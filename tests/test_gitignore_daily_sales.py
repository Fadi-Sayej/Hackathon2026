# tests/test_gitignore_daily_sales.py
"""ADR-030: the daily sales reports are committed with a plain `git add`; their siblings are not.

Git cannot re-include a path under an ignored directory, so `!…/sales_daily/` alone would do
nothing while `data/internal/raw_pos/` stays ignored. A forgotten `-f` on one file in a
weekly batch of seven would leave that day missing, and the engine would read it as missing.

Asked of git itself, on a scratch repository with this repository's .gitignore: which of
these files does `git add --all` take?
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

DAILY = "data/internal/raw_pos/yomyom/sales_daily/דוח מכירות יום 2026-09-20.csv"
STILL_IGNORED = [
    "data/internal/raw_pos/yomyom/inventory.csv",
    "data/internal/raw_pos/yomyom/sales/דוח מכירות חודש אוגוסט 2026.csv",
    "data/internal/raw_pos/other/x.csv",
    "data/internal/raw_pos/x.csv",
]


def _added(tmp_path: Path, paths: list[str]) -> set[str]:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    shutil.copy(ROOT / ".gitignore", tmp_path / ".gitignore")
    for rel in paths:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "--all"], check=True)
    listed = subprocess.run(["git", "-C", str(tmp_path), "-c", "core.quotepath=off", "ls-files", "-z"],
                            check=True, capture_output=True).stdout.decode("utf-8")
    return {p for p in listed.split("\0") if p}


def test_a_daily_report_is_taken_by_a_plain_add(tmp_path):
    assert DAILY in _added(tmp_path, [DAILY])


def test_another_stores_daily_report_is_taken_too(tmp_path):
    """ADR-036: a new store's copy commits its reports under its own folder, not YomYom's."""
    other = "data/internal/raw_pos/store-b/sales_daily/דוח מכירות יום 2026-10-01.csv"
    assert other in _added(tmp_path, [other])


def test_everything_else_under_raw_pos_stays_ignored(tmp_path):
    added = _added(tmp_path, [DAILY, *STILL_IGNORED])
    assert [p for p in STILL_IGNORED if p in added] == []
