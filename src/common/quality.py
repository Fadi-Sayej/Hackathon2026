"""
quality.py — generate a basic data-quality report for a batch of records.

The report is written as a JSON file under reports/quality/ via the path
resolver in paths.py.  Collectors call this after writing bronze or silver
parquet so every pipeline run leaves an auditable quality snapshot.

Usage
-----
    from src.common.quality import generate_basic_quality_report

    report_path = generate_basic_quality_report(records, "wolt", "2025-05-25T14:00:00")
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from loguru import logger

from src.common.paths import get_quality_report_path


# ── Core metric computation ────────────────────────────────────────────────────

def _pct_missing(records: list[dict], field: str) -> float:
    """Return the fraction of records where *field* is None / empty string."""
    if not records:
        return 0.0
    missing = sum(
        1 for r in records
        if r.get(field) is None or r.get(field) == ""
    )
    return round(missing / len(records), 4)


def _count_duplicates(records: list[dict]) -> int:
    """
    Count duplicate rows.

    A 'duplicate' is defined as any record that shares the same (barcode,
    store_id, observed_at) triple with another record.  If those fields are
    absent the raw dict repr is used as the dedup key.
    """
    def _key(r: dict) -> tuple:
        bc = r.get("barcode") or r.get("sku") or ""
        store = r.get("store_id") or r.get("store_name") or ""
        ts = str(r.get("observed_at") or r.get("_ingested_at") or "")
        if bc or store:
            return (bc, store, ts)
        return (json.dumps(r, sort_keys=True, default=str),)

    seen: dict[tuple, int] = {}
    for r in records:
        k = _key(r)
        seen[k] = seen.get(k, 0) + 1

    return sum(v - 1 for v in seen.values() if v > 1)


def _unique_values(records: list[dict], field: str) -> int:
    """Return the number of distinct non-null values for *field*."""
    vals = {r.get(field) for r in records if r.get(field) not in (None, "")}
    return len(vals)


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_basic_quality_report(
    records: list[dict],
    source_id: str,
    observed_at: str | datetime,
) -> Path:
    """
    Compute basic quality metrics for *records* and write a JSON report.

    Metrics computed
    ----------------
    row_count              — total number of records.
    missing_barcode_pct    — fraction with no barcode / sku.
    missing_price_pct      — fraction with no price / selling_price.
    missing_category_pct   — fraction with no category.
    duplicate_count        — number of duplicate rows (excess copies).
    unique_products        — distinct (barcode or sku) values.
    unique_stores          — distinct store_id values.

    Parameters
    ----------
    records     : List of plain dicts (same dicts passed to the parquet writer).
    source_id   : Collector identifier, e.g. "wolt".
    observed_at : ISO-8601 string or datetime of the collection moment.

    Returns
    -------
    pathlib.Path — absolute path of the written quality report JSON.
    """
    if isinstance(observed_at, datetime):
        observed_at_str = observed_at.isoformat()
    else:
        observed_at_str = observed_at

    # ---- metrics -----
    row_count = len(records)

    # Barcode: try both "barcode" and "sku" — if either is present it's fine
    missing_barcode = sum(
        1 for r in records
        if not (r.get("barcode") or r.get("sku"))
    )
    missing_barcode_pct = round(missing_barcode / row_count, 4) if row_count else 0.0

    # Price: accept "price", "selling_price", or "sale_price"
    missing_price = sum(
        1 for r in records
        if not (r.get("price") or r.get("selling_price") or r.get("sale_price"))
    )
    missing_price_pct = round(missing_price / row_count, 4) if row_count else 0.0

    missing_category_pct = _pct_missing(records, "category")
    duplicate_count = _count_duplicates(records)

    # Unique products: prefer barcode, fall back to sku
    unique_products = len({
        r.get("barcode") or r.get("sku")
        for r in records
        if r.get("barcode") or r.get("sku")
    })

    unique_stores = _unique_values(records, "store_id")

    # ---- assemble report -----
    report: dict = {
        "source_id": source_id,
        "observed_at": observed_at_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "row_count": row_count,
            "missing_barcode_pct": missing_barcode_pct,
            "missing_price_pct": missing_price_pct,
            "missing_category_pct": missing_category_pct,
            "duplicate_count": duplicate_count,
            "unique_products": unique_products,
            "unique_stores": unique_stores,
        },
    }

    # ---- write -----
    report_path = get_quality_report_path(source_id, observed_at_str)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info(
        "Quality report written ({} rows, {:.1%} missing barcode): {}",
        row_count,
        missing_barcode_pct,
        report_path,
    )
    return report_path
