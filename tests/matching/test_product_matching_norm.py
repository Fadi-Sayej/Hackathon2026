# tests/matching/test_product_matching_norm.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import polars as pl

from src.matching.product_matching import _dedup_competitors, _pass_barcode_exact


def test_dedup_keeps_one_row_per_store_not_per_product():
    df = pl.DataFrame({
        "barcode": ["1", "1", "2"], "external_product_key": ["1", "1", "2"],
        "competitor_store_id": ["s1", "s2", "s1"], "raw_product_name": ["a", "a", "b"],
        "normalized_product_name": ["a", "a", "b"], "brand": [None, None, None],
        "category": [None, None, None], "size": ["", "", ""], "unit": [None, None, None],
        "source_types": [["price_file"], ["delivery"], ["price_file"]],
    })
    rows = _dedup_competitors(df)
    assert sorted((r["barcode"], r["competitor_store_id"]) for r in rows) == [("1", "s1"), ("1", "s2"), ("2", "s1")]


def test_barcode_exact_ignores_leading_zeros():
    internal = [{"internal_product_id": "p1", "barcode": "0000123", "product_name": "x", "category": "c",
                 "brand": None, "size": "", "unit": None}]
    competitors = [{"barcode": "123", "external_product_key": "123", "competitor_store_id": "s1",
                    "raw_product_name": "x", "normalized_product_name": "x", "brand": None, "category": None,
                    "size": "", "unit": None, "source_types": ["price_file"]}]
    matches, unmatched = _pass_barcode_exact(internal, competitors, "2026-09-08T00:00:00+00:00")
    assert len(matches) == 1 and matches[0]["match_method"] == "barcode_exact"
    assert matches[0]["competitor_store_id"] == "s1"
