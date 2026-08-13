"""
paths.py — canonical path resolver for the YomYom storage layer.

All collectors, writers, and quality modules import from here so that
folder layout is defined in exactly one place.

Usage
-----
    from src.common.paths import get_raw_path, get_bronze_path

    raw = get_raw_path("wolt", "2025-05-25T14:00:00", "json")
    bronze = get_bronze_path("wolt", "2025-05-25T14:00:00")
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

# ── Root ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

# ── Top-level data roots ───────────────────────────────────────────────────────
DATA_ROOT         = PROJECT_ROOT / "data"
INTERNAL_ROOT     = DATA_ROOT / "internal"
EXTERNAL_ROOT     = DATA_ROOT / "external"
MATCHING_ROOT     = DATA_ROOT / "matching"
SIGNALS_ROOT      = DATA_ROOT / "signals"
RECOMMENDATIONS_ROOT = DATA_ROOT / "recommendations"
EXPIRY_ROOT       = INTERNAL_ROOT / "expiry"
RECEIVING_ROOT    = INTERNAL_ROOT / "receiving"

# ── Internal sub-folders ───────────────────────────────────────────────────────
RAW_POS_ROOT      = INTERNAL_ROOT / "raw_pos"
SILVER_POS_ROOT   = INTERNAL_ROOT / "silver_pos"
SNAPSHOTS_ROOT    = INTERNAL_ROOT / "snapshots"
EXPIRY_SCANS_CSV  = EXPIRY_ROOT / "expiry_scans.csv"

# The receiving ledger (T7 / #52). Append-only: the POS records what was sold and
# never what arrived, so this file is the only record of the `received` term in
# stock_now = opening + received - sold.
RECEIPTS_CSV             = RECEIVING_ROOT / "receipts.csv"
SUPPLIER_LEAD_TIMES_JSON = RECEIVING_ROOT / "supplier_lead_times.json"

# ── External sub-folders ──────────────────────────────────────────────────────
EXTERNAL_RAW_ROOT    = EXTERNAL_ROOT / "raw"
EXTERNAL_BRONZE_ROOT = EXTERNAL_ROOT / "bronze"
EXTERNAL_SILVER_ROOT = EXTERNAL_ROOT / "silver"

# Immutable dated market snapshots (T1 / #46). One folder per calendar day, never
# rewritten. The price-transparency server keeps only the current day, so a day
# lost here is lost permanently — see docs/SNAPSHOT_DURABILITY.md.
EXTERNAL_SNAPSHOTS_ROOT = EXTERNAL_ROOT / "snapshots"

# ── Reports / logs ────────────────────────────────────────────────────────────
QUALITY_ROOT      = PROJECT_ROOT / "reports" / "quality"
LOGS_ROOT         = PROJECT_ROOT / "logs"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _date_partition(observed_at: str | datetime) -> str:
    """Return a YYYY/MM/DD partition string from an ISO-8601 string or datetime."""
    if isinstance(observed_at, str):
        observed_at = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    return observed_at.strftime("%Y/%m/%d")


def _source_root(source_id: str) -> Path:
    """External raw root for a given source, e.g. data/external/raw/wolt/."""
    return EXTERNAL_RAW_ROOT / source_id


def _snapshot_day(collected_on: "str | date | datetime") -> str:
    """YYYY-MM-DD for a snapshot folder, from a date, datetime or ISO string."""
    if isinstance(collected_on, str):
        text = collected_on.replace("Z", "+00:00")
        try:
            collected_on = datetime.fromisoformat(text)
        except ValueError:
            # Already a plain YYYY-MM-DD.
            return collected_on[:10]
    return collected_on.strftime("%Y-%m-%d")


# ── Public path functions ──────────────────────────────────────────────────────

def get_snapshot_path(source_id: str, collected_on: "str | date | datetime") -> Path:
    """Directory for one source's contribution to one day's market snapshot.

        data/external/snapshots/<YYYY-MM-DD>/<source_id>/

    Dated rather than partitioned as YYYY/MM/DD because a snapshot is a single
    atomic unit: the whole day either succeeded or it did not, and #49 reasons
    about days as points on a time axis. Flat dates also make "diff any two
    dates" a one-liner.
    """
    return EXTERNAL_SNAPSHOTS_ROOT / _snapshot_day(collected_on) / source_id


def get_snapshot_manifest_path(collected_on: "str | date | datetime") -> Path:
    """data/external/snapshots/<YYYY-MM-DD>/_manifest.json

    Not optional. Without it there is no way to distinguish a product that was
    genuinely absent from the market on a given day from one that a failed
    scrape simply never saw — and that distinction is the entire basis of the
    latent-state inference in #49.
    """
    return EXTERNAL_SNAPSHOTS_ROOT / _snapshot_day(collected_on) / "_manifest.json"

def get_raw_path(source_id: str, observed_at: str | datetime, extension: str) -> Path:
    """
    Return the path where a raw response body should be written.

    Structure: data/external/raw/<source_id>/<YYYY/MM/DD>/<source_id>_<YYYYMMDDTHHMMSS>.<ext>

    Parameters
    ----------
    source_id   : Collector identifier, e.g. "wolt", "shufersal", "price_transparency".
    observed_at : ISO-8601 string or datetime of when the data was fetched.
    extension   : File extension without leading dot, e.g. "json", "html", "csv".

    Returns
    -------
    pathlib.Path (parent directories are NOT created here; raw_storage handles that).
    """
    ext = extension.lstrip(".")
    if isinstance(observed_at, str):
        dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    else:
        dt = observed_at
    ts = dt.strftime("%Y%m%dT%H%M%S")
    partition = _date_partition(dt)
    return _source_root(source_id) / partition / f"{source_id}_{ts}.{ext}"


def get_raw_metadata_path(source_id: str, observed_at: str | datetime) -> Path:
    """
    Return the path for the companion metadata.json of a raw file.

    Structure mirrors get_raw_path but ends with _metadata.json.
    """
    base = get_raw_path(source_id, observed_at, "json")
    return base.parent / base.name.replace(".json", "_metadata.json").replace(
        f".{base.suffix.lstrip('.')}", "_metadata.json"
    )


def get_bronze_path(source_id: str, observed_at: str | datetime) -> Path:
    """
    Return the path for a bronze Parquet file.

    Structure: data/external/bronze/<source_id>/<YYYY/MM/DD>/<source_id>_<YYYYMMDDTHHMMSS>_bronze.parquet
    """
    if isinstance(observed_at, str):
        dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    else:
        dt = observed_at
    ts = dt.strftime("%Y%m%dT%H%M%S")
    partition = _date_partition(dt)
    return EXTERNAL_BRONZE_ROOT / source_id / partition / f"{source_id}_{ts}_bronze.parquet"


def get_silver_path(
    dataset_name: str,
    observed_at: str | datetime,
    source_id: Optional[str] = None,
) -> Path:
    """
    Return the path for a silver Parquet file.

    Structure:
      - With source_id : data/external/silver/<dataset_name>/<source_id>/<YYYY/MM/DD>/…_silver.parquet
      - Without        : data/external/silver/<dataset_name>/<YYYY/MM/DD>/…_silver.parquet

    Parameters
    ----------
    dataset_name : Logical name of the dataset, e.g. "products", "prices".
    observed_at  : ISO-8601 string or datetime.
    source_id    : Optional collector identifier for partitioning by source.
    """
    if isinstance(observed_at, str):
        dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    else:
        dt = observed_at
    ts = dt.strftime("%Y%m%dT%H%M%S")
    partition = _date_partition(dt)

    if source_id:
        base = EXTERNAL_SILVER_ROOT / dataset_name / source_id / partition
    else:
        base = EXTERNAL_SILVER_ROOT / dataset_name / partition

    return base / f"{dataset_name}_{ts}_silver.parquet"


def get_quality_report_path(source_id: str, observed_at: str | datetime) -> Path:
    """
    Return the path for a JSON quality report.

    Structure: reports/quality/<source_id>/<YYYY/MM/DD>/<source_id>_<YYYYMMDDTHHMMSS>_quality.json
    """
    if isinstance(observed_at, str):
        dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    else:
        dt = observed_at
    ts = dt.strftime("%Y%m%dT%H%M%S")
    partition = _date_partition(dt)
    return QUALITY_ROOT / source_id / partition / f"{source_id}_{ts}_quality.json"
