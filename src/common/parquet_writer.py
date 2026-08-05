"""
parquet_writer.py — write bronze and silver Parquet files.

Uses PyArrow for writing so the output is compatible with DuckDB, Spark,
Polars, and pandas without any additional dependencies.

Bronze: raw-ish records, minimal transformation, one file per collection run.
Silver: cleaned, typed, possibly cross-source unified records.

Usage
-----
    from src.common.parquet_writer import write_bronze_parquet, write_silver_parquet

    bronze_path = write_bronze_parquet(records, "wolt", "2025-05-25T14:00:00")
    silver_path = write_silver_parquet(records, "products", "2025-05-25T14:00:00", source_id="wolt")
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger

from src.common.paths import get_bronze_path, get_silver_path

# ── Helpers ───────────────────────────────────────────────────────────────────

def _records_to_table(records: list[dict]) -> pa.Table:
    """Convert a list of plain dicts to a PyArrow Table.

    All values are inferred; None columns become null(). This keeps the writer
    schema-agnostic so any collector can call it without pre-defining fields.
    """
    if not records:
        # Return a valid empty table with a single dummy column so Parquet
        # doesn't refuse to write.
        return pa.table({"_empty": pa.array([], type=pa.bool_())})
    return pa.Table.from_pylist(records)


def _safe_parquet_write(path: Path, table: pa.Table) -> Path:
    """Write *table* to *path*, creating parents, never overwriting."""
    if path.exists():
        logger.warning(
            "Parquet file already exists, appending timestamp suffix: {}", path
        )
        ts = datetime.now(timezone.utc).strftime("%H%M%S%f")
        path = path.with_stem(f"{path.stem}_{ts}")

    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(path), compression="snappy")
    logger.info(
        "Parquet written ({} rows, {} cols): {}",
        table.num_rows,
        table.num_columns,
        path,
    )
    return path


# ── Public API ─────────────────────────────────────────────────────────────────

def write_bronze_parquet(
    records: list[dict],
    source_id: str,
    observed_at: str | datetime,
) -> Path:
    """
    Write a list of dicts as a bronze Parquet file.

    Bronze = raw records with minimal cleaning; one file per collection run.
    An _ingested_at column is automatically added.

    Parameters
    ----------
    records     : List of plain dicts. Keys become column names.
    source_id   : Collector identifier, e.g. "wolt".
    observed_at : ISO-8601 string or datetime of the collection moment.

    Returns
    -------
    pathlib.Path — absolute path of the written Parquet file.
    """
    if isinstance(observed_at, datetime):
        observed_at_str = observed_at.isoformat()
    else:
        observed_at_str = observed_at

    # Stamp every bronze record with ingestion time and source
    stamped = [
        {**r, "_source_id": source_id, "_ingested_at": observed_at_str}
        for r in records
    ]

    table = _records_to_table(stamped)
    path = get_bronze_path(source_id, observed_at_str)
    return _safe_parquet_write(path, table)


def write_silver_parquet(
    records: list[dict],
    dataset_name: str,
    observed_at: str | datetime,
    source_id: Optional[str] = None,
) -> Path:
    """
    Write a list of dicts as a silver Parquet file.

    Silver = cleaned, typed, cross-source-ready records.
    An _ingested_at column is automatically added.

    Parameters
    ----------
    records      : List of plain dicts.
    dataset_name : Logical dataset name, e.g. "products", "prices".
    observed_at  : ISO-8601 string or datetime.
    source_id    : Optional source; used for sub-partitioning.

    Returns
    -------
    pathlib.Path — absolute path of the written Parquet file.
    """
    if isinstance(observed_at, datetime):
        observed_at_str = observed_at.isoformat()
    else:
        observed_at_str = observed_at

    stamped = [
        {
            **r,
            "_dataset": dataset_name,
            "_source_id": source_id,
            "_ingested_at": observed_at_str,
        }
        for r in records
    ]

    table = _records_to_table(stamped)
    path = get_silver_path(dataset_name, observed_at_str, source_id=source_id)
    return _safe_parquet_write(path, table)
