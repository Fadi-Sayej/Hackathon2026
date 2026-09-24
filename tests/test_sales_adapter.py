"""
A-3: real sales must beat the snapshot proxy, and never be destroyed by it.

The snapshot-delta engine exists only because the POS export has no sales history.
The moment YomYom sends a real sales report, two things must hold:

  1. the proxy stands down rather than overwriting measured sales, and
  2. we can tell in seconds whether the file they sent is usable.

The first is the dangerous one. This module rewrites the whole sales table, so
without a guard the first velocity rebuild (`npm run data:velocity`) after importing a real sales report
would replace measured units with nulls — silently, on the day the data finally
arrived.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.snapshots.velocity import (  # noqa: E402
    POS_EXPORT_SOURCE,
    SNAPSHOT_SOURCE,
    apply_to_sales_table,
    has_real_sales,
)

DETECTOR = ROOT / "scripts" / "detect_sales_columns.py"


def _sales_table(path: Path, rows, with_source: bool):
    fields = [
        ("barcode", pa.string()),
        ("product_name", pa.string()),
        ("units_sold_30d", pa.int64()),
    ]
    if with_source:
        fields.append(("velocity_source", pa.string()))
    pq.write_table(pa.Table.from_pylist(rows, schema=pa.schema(fields)), path)
    return path


# ---------------------------------------------------------------------------
# Real sales must be recognised and protected
# ---------------------------------------------------------------------------

def test_real_sales_detected_when_importer_wrote_them(tmp_path):
    """Rows with units but no velocity_source stamp came from the POS export."""
    path = _sales_table(
        tmp_path / "s.parquet",
        [{"barcode": "1", "product_name": "p", "units_sold_30d": 180}],
        with_source=False,
    )
    assert has_real_sales(path) is True


def test_snapshot_derived_sales_are_not_mistaken_for_real(tmp_path):
    path = _sales_table(
        tmp_path / "s.parquet",
        [{"barcode": "1", "product_name": "p", "units_sold_30d": 12,
          "velocity_source": SNAPSHOT_SOURCE}],
        with_source=True,
    )
    assert has_real_sales(path) is False


def test_explicit_pos_export_stamp_is_real(tmp_path):
    path = _sales_table(
        tmp_path / "s.parquet",
        [{"barcode": "1", "product_name": "p", "units_sold_30d": 180,
          "velocity_source": POS_EXPORT_SOURCE}],
        with_source=True,
    )
    assert has_real_sales(path) is True


def test_empty_velocity_is_not_real_sales(tmp_path):
    path = _sales_table(
        tmp_path / "s.parquet",
        [{"barcode": "1", "product_name": "p", "units_sold_30d": None,
          "velocity_source": SNAPSHOT_SOURCE}],
        with_source=True,
    )
    assert has_real_sales(path) is False


def test_missing_table_is_not_real_sales(tmp_path):
    assert has_real_sales(tmp_path / "absent.parquet") is False


def test_build_velocity_refuses_to_overwrite_real_sales(monkeypatch, tmp_path):
    """The regression that would have destroyed the data on arrival."""
    import src.snapshots.velocity as velocity

    real = _sales_table(
        tmp_path / "s.parquet",
        [{"barcode": "1", "product_name": "p", "units_sold_30d": 180}],
        with_source=False,
    )
    # has_real_sales() and apply_to_sales_table() both default to
    # SILVER_POS_ROOT/yomyom_sales.parquet, so point that at the fixture.
    monkeypatch.setattr(velocity, "SILVER_POS_ROOT", tmp_path)
    (tmp_path / "yomyom_sales.parquet").write_bytes(real.read_bytes())

    result = velocity.build_velocity(write=True)

    assert result["written"] is False
    assert result["skipped_reason"] == "real_sales_present"
    after = pq.read_table(tmp_path / "yomyom_sales.parquet").to_pylist()[0]
    assert after["units_sold_30d"] == 180  # untouched


def test_apply_still_writes_when_only_proxy_data_exists(tmp_path):
    """The guard must not disable the proxy in the situation it was built for."""
    sales = _sales_table(
        tmp_path / "s.parquet",
        [{"barcode": "1", "product_name": "p", "units_sold_30d": None,
          "velocity_source": SNAPSHOT_SOURCE}],
        with_source=True,
    )
    products = tmp_path / "p.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [{"barcode": "1", "selling_price": 5.0}],
            schema=pa.schema([("barcode", pa.string()), ("selling_price", pa.float64())]),
        ),
        products,
    )
    velocity = {"1": {"units_sold_7d": 7, "units_sold_30d": 30, "units_per_day": 1.0,
                      "observed_days": 30.0, "max_gap_days": 1.0,
                      "velocity_confidence": "high", "last_sale_date": "2026-08-01"}}

    stats = apply_to_sales_table(velocity, sales_path=sales, products_path=products)

    assert stats["matched"] == 1
    assert pq.read_table(sales).to_pylist()[0]["units_sold_30d"] == 30


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
