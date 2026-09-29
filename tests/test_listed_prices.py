"""D-27: the delivery app's listed price, read as presence.py reads listings (F9-S1 FR-168)."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.market.listed_prices import snapshot_price_reader  # noqa: E402

DAY = date(2026, 9, 28)


def _day(root: Path, rows, name="products_20260928T035045_silver.parquet", folder="29"):
    d = root / DAY.isoformat() / "delivery_catalog" / folder
    d.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(d / name)


def test_it_reads_the_price_with_presence_s_barcode_normalisation(tmp_path):
    _day(tmp_path, [{"barcode": "0007290001", "store_id": "w", "price": "12.90", "sale_price": None},
                    {"barcode": "7290002", "store_id": "w", "price": "5.5", "sale_price": "4.90"}])
    price_of = snapshot_price_reader(tmp_path)
    assert price_of(DAY, "7290001", "w") == {"price": 12.9, "sale_price": None}
    assert price_of(DAY, "7290002", "w") == {"price": 5.5, "sale_price": 4.9}


def test_bronze_files_are_not_read(tmp_path):
    _day(tmp_path, [{"barcode": "7290001", "store_id": "w", "price": "99"}], name="delivery_catalog_x_bronze.parquet")
    assert snapshot_price_reader(tmp_path)(DAY, "7290001", "w") is None


def test_no_price_is_none_never_zero(tmp_path):
    _day(tmp_path, [{"barcode": "7290001", "store_id": "w", "price": None, "sale_price": None},
                    {"barcode": "7290002", "store_id": "w", "price": "0", "sale_price": None},
                    {"barcode": "7290003", "store_id": "w", "price": "n/a", "sale_price": None}])
    price_of = snapshot_price_reader(tmp_path)
    for barcode in ("7290001", "7290002", "7290003", "7290404"):
        assert price_of(DAY, barcode, "w") is None
    assert price_of(date(2026, 9, 1), "7290001", "w") is None          # no snapshot that day
