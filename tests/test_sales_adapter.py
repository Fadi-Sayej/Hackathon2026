"""
A-3: when a store sends a sales report, we can tell in seconds whether it is usable.

`scripts/detect_sales_columns.py` is run on the file before anything is imported: it rejects an
inventory-only export, accepts a mapped sales header, and names any sales column the mapping
does not know yet.

Until 2026-10-06 this file also guarded the snapshot-velocity writer against overwriting real
sales in `yomyom_sales.parquet`. That writer, and `npm run data:velocity`, were removed: Task 0.6
deleted the table, because its rate was synthesised (CLAUDE.md rules 5 and 13), and nothing may
recreate it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DETECTOR = ROOT / "scripts" / "detect_sales_columns.py"



# ---------------------------------------------------------------------------
# Real sales must be recognised and protected
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# The on-ramp: tell us in seconds whether their file is usable
# ---------------------------------------------------------------------------

def _detect(path: Path):
    return subprocess.run(
        [sys.executable, str(DETECTOR), "--input", str(path)],
        capture_output=True, text=True, cwd=ROOT,
    )


def test_detector_rejects_an_inventory_only_export(tmp_path):
    csv_path = tmp_path / "inv.csv"
    csv_path.write_text("ברקוד,תאור פריט,מלאי נוכחי,מחיר מכירה\n1,קפה,5,10\n", encoding="utf-8")
    result = _detect(csv_path)
    assert result.returncode == 1
    assert "No sales data" in result.stdout


def test_detector_accepts_a_mapped_sales_header(tmp_path):
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("ברקוד,תאור פריט,כמות נמכרת\n1,קפה,180\n", encoding="utf-8")
    result = _detect(csv_path)
    assert result.returncode == 0
    assert "units_sold_30d" in result.stdout


def test_detector_flags_unmapped_sales_columns_as_a_config_fix(tmp_path):
    """Exit 2 means: real sales are in there, you just need a YAML line."""
    csv_path = tmp_path / "arabic.csv"
    csv_path.write_text("ברקוד,صنف,الكمية المباعة\n1,قهوة,180\n", encoding="utf-8")
    result = _detect(csv_path)
    assert result.returncode == 2
    assert "not mapped yet" in result.stdout
    assert "الكمية المباعة" in result.stdout


def test_detector_handles_semicolon_delimited_exports(tmp_path):
    """Israeli POS tools commonly export semicolon-separated CSV."""
    csv_path = tmp_path / "semi.csv"
    csv_path.write_text("ברקוד;תאור פריט;כמות נמכרת\n1;קפה;180\n", encoding="utf-8")
    result = _detect(csv_path)
    assert result.returncode == 0


def test_detector_rejects_excel_with_an_instruction(tmp_path):
    xlsx = tmp_path / "report.xlsx"
    xlsx.write_bytes(b"PK\x03\x04not-a-real-xlsx")
    result = _detect(xlsx)
    assert result.returncode != 0
    assert "Save it as CSV" in (result.stdout + result.stderr)


def test_detector_reports_missing_file_clearly(tmp_path):
    result = _detect(tmp_path / "nope.csv")
    assert result.returncode == 1
    assert "not found" in (result.stdout + result.stderr)
