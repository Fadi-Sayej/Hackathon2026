"""
mcp_price_adapter.py — MCP price-lookup adapter for YomYom market intelligence.

Queries the latest silver-Parquet price data for a batch of YomYom
barcodes / product names, normalises matches to ExternalProductObservation,
and emits a coverage report.

Supported chains
----------------
  alonit / dor_alon / super_alonit  →  data/external/silver/alonit_prices/

Matching strategy (per product, in priority order)
---------------------------------------------------
  1. Exact barcode match   (identifier is purely numeric, 4-14 digits)
  2. Exact product-name    (case-insensitive, stripped)
  3. Substring match       (identifier appears inside product_name)
  4. Fuzzy ratio match     (difflib SequenceMatcher >= name_threshold, default 0.72)

All matched rows across all stores for that product are returned so the
caller can see every branch price in one pass.

Raw output
----------
Each run saves a JSON snapshot to
  data/external/raw/alonit_mcp/<YYYY/MM/DD>/alonit_mcp_<ts>.json
containing the queried identifiers, chain list, raw matched rows, and
timestamp — the "raw MCP output" for audit / replay.

Coverage report
---------------
  queried_products        list of identifiers sent in
  matched_products        identifiers that got >= 1 result
  unmatched_products      identifiers with no result
  match_rate_pct
  chains_found            distinct store_chain values seen
  branch_level_available  True if any observation has branch_confidence=high
  total_observations
  with_promo_price
  low_confidence_count    obs where branch_confidence in {low, unknown}
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from loguru import logger

# ── project root ──────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import polars as pl

from src.common.paths import EXTERNAL_SILVER_ROOT, get_raw_path
from src.common.raw_storage import save_raw_file
from src.common.schema import ExternalProductObservation


# ── Constants ─────────────────────────────────────────────────────────────────

SOURCE_ID   = "alonit_mcp"
SOURCE_TYPE = "mcp_price_lookup"

# Map user-facing chain names → silver dataset name
CHAIN_DATASET: dict[str, tuple[str, str]] = {
    # chain_key: (dataset_name, parquet_source_id)
    "alonit":       ("alonit_prices", "alonit"),
    "dor_alon":     ("alonit_prices", "alonit"),
    "super_alonit": ("alonit_prices", "alonit"),
}

DEFAULT_CHAINS = ["alonit", "dor_alon", "super_alonit"]

_BARCODE_RE = re.compile(r"^\d{4,14}$")


# ─────────────────────────────────────────────────────────────────────────────
# Parquet loader
# ─────────────────────────────────────────────────────────────────────────────

def _latest_parquet(dataset: str, source_id: str) -> Optional[Path]:
    """Return the newest silver Parquet file for (dataset, source_id), or None."""
    base = EXTERNAL_SILVER_ROOT / dataset / source_id
    if not base.exists():
        # Fallback: dataset-only root (no source_id sub-dir)
        base = EXTERNAL_SILVER_ROOT / dataset
    if not base.exists():
        return None
    files = sorted(base.rglob("*.parquet"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def load_price_dataframe(chains: list[str]) -> pl.DataFrame:
    """
    Load and concatenate the latest silver price Parquet for all requested chains.

    Returns an empty DataFrame if no data is available yet (run the Alonit
    collector first: ``python scripts/run_alonit_collector.py``).
    """
    frames: list[pl.DataFrame] = []
    seen: set[str] = set()

    for chain in chains:
        info = CHAIN_DATASET.get(chain.lower())
        if not info:
            logger.warning("No dataset mapping for chain {!r} — skipped", chain)
            continue
        dataset, src_id = info
        key = f"{dataset}::{src_id}"
        if key in seen:
            continue
        seen.add(key)

        path = _latest_parquet(dataset, src_id)
        if not path:
            logger.warning(
                "No silver Parquet for dataset={!r} source={!r}.  "
                "Run: python scripts/run_alonit_collector.py",
                dataset, src_id,
            )
            continue

        logger.info("Loading price data from {}", path)
        try:
            frames.append(pl.read_parquet(path))
        except Exception as exc:
            logger.error("Failed to read Parquet {}: {}", path, exc)

    if not frames:
        return pl.DataFrame()

    try:
        return pl.concat(frames, how="diagonal_relaxed")
    except Exception as exc:
        logger.warning("Parquet concat error ({}); using first frame only", exc)
        return frames[0]


# ─────────────────────────────────────────────────────────────────────────────
# Matching
# ─────────────────────────────────────────────────────────────────────────────

def _is_barcode(identifier: str) -> bool:
    return bool(_BARCODE_RE.match(identifier.strip()))


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def match_identifier(
    identifier: str,
    df: pl.DataFrame,
    name_threshold: float = 0.72,
) -> list[dict]:
    """
    Return all matching rows from *df* for a single barcode or product name.

    Multiple rows are expected when the same product appears in several stores;
    all are returned so the caller sees full cross-branch coverage.
    """
    if df.is_empty():
        return []

    ident = identifier.strip()

    if _is_barcode(ident):
        # ── Exact barcode / SKU ───────────────────────────────────────────────
        for col in ("barcode", "sku"):
            if col in df.columns:
                hits = df.filter(pl.col(col) == ident)
                if not hits.is_empty():
                    return hits.to_dicts()
        return []

    # ── Product name matching ─────────────────────────────────────────────────
    if "product_name" not in df.columns:
        return []

    ident_lower = ident.lower()

    # Pass 1 — exact case-insensitive
    hits = df.filter(pl.col("product_name").str.to_lowercase() == ident_lower)
    if not hits.is_empty():
        return hits.to_dicts()

    # Pass 2 — substring (ident contained in product_name)
    hits = df.filter(
        pl.col("product_name").str.to_lowercase().str.contains(ident_lower, literal=True)
    )
    if not hits.is_empty():
        return hits.to_dicts()

    # Pass 3 — fuzzy ratio (slow path, works best on small frames)
    rows = df.to_dicts()
    fuzzy = [
        r for r in rows
        if _similarity(ident, r.get("product_name", "")) >= name_threshold
    ]
    return fuzzy


# ─────────────────────────────────────────────────────────────────────────────
# Branch-confidence assessment
# ─────────────────────────────────────────────────────────────────────────────

def _branch_confidence(row: dict) -> str:
    """Derive branch_confidence from the row's store fields."""
    has_id   = bool(row.get("store_id"))
    has_name = bool(row.get("store_name"))
    has_city = bool(row.get("city"))
    if has_id and has_name and has_city:
        return "high"
    if has_id or has_name:
        return "medium"
    if row.get("store_chain"):
        return "low"
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer
# ─────────────────────────────────────────────────────────────────────────────

def _safe_decimal(v) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError):
        return None


def normalize_row(
    row: dict,
    queried_identifier: str,
    observed_at: datetime,
) -> ExternalProductObservation:
    """Convert one matched Parquet row to an MCP-tagged ExternalProductObservation."""
    return ExternalProductObservation(
        # provenance
        source_id    = row.get("source_id") or row.get("_source_id") or "alonit",
        observed_at  = observed_at,
        source_type  = SOURCE_TYPE,
        branch_confidence = _branch_confidence(row),
        # identity
        barcode      = row.get("barcode"),
        sku          = row.get("sku"),
        product_name = row.get("product_name") or queried_identifier,
        brand        = row.get("brand"),
        category     = row.get("category"),
        unit         = row.get("unit"),
        # pricing
        price        = _safe_decimal(row.get("price")),
        sale_price   = _safe_decimal(row.get("sale_price")),
        currency     = row.get("currency") or "ILS",
        # location
        store_id     = row.get("store_id"),
        store_name   = row.get("store_name"),
        store_chain  = row.get("store_chain"),
        city         = row.get("city"),
        # lineage
        raw_file_path          = row.get("raw_file_path"),
        appears_in_price_file  = row.get("appears_in_price_file", True),
        is_online_available    = row.get("is_online_available"),
        is_in_catalog          = row.get("is_in_catalog", True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Coverage report
# ─────────────────────────────────────────────────────────────────────────────

def build_coverage_report(
    queried: list[str],
    results: dict[str, list[ExternalProductObservation]],
    chains_requested: list[str],
    observed_at: datetime,
) -> dict:
    """
    Build the coverage report dict.

    Parameters
    ----------
    queried          : All identifiers originally requested.
    results          : {identifier: [ExternalProductObservation, ...]}
    chains_requested : Chains that were queried.
    observed_at      : Timestamp of this lookup session.
    """
    queried_set  = set(queried)
    matched_set  = {k for k, v in results.items() if v}
    unmatched    = sorted(queried_set - matched_set)

    all_obs = [obs for obs_list in results.values() for obs in obs_list]

    chains_found = sorted({
        obs.store_chain for obs in all_obs if obs.store_chain
    })
    branch_level_available = any(
        obs.branch_confidence == "high" for obs in all_obs
    )
    low_conf = sum(
        1 for obs in all_obs
        if obs.branch_confidence in ("low", "unknown")
    )

    return {
        "observed_at":            observed_at.isoformat(),
        "chains_requested":       sorted(chains_requested),
        "queried_products":       sorted(queried_set),
        "queried_count":          len(queried_set),
        "matched_products":       sorted(matched_set),
        "matched_count":          len(matched_set),
        "unmatched_products":     unmatched,
        "unmatched_count":        len(unmatched),
        "match_rate_pct":         round(len(matched_set) / len(queried_set) * 100, 1)
                                  if queried_set else 0.0,
        "total_observations":     len(all_obs),
        "chains_found":           chains_found,
        "branch_level_available": branch_level_available,
        "with_promo_price":       sum(1 for o in all_obs if o.sale_price is not None),
        "low_confidence_count":   low_conf,
        "per_product": {
            ident: {
                "matched":  bool(results.get(ident)),
                "hit_count": len(results.get(ident, [])),
                "stores":   [
                    {
                        "store_id":   o.store_id,
                        "store_name": o.store_name,
                        "city":       o.city,
                        "chain":      o.store_chain,
                        "price":      float(o.price) if o.price is not None else None,
                        "sale_price": float(o.sale_price) if o.sale_price is not None else None,
                        "branch_confidence": o.branch_confidence,
                    }
                    for o in results.get(ident, [])
                ],
            }
            for ident in queried
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_mcp_price_lookup(
    products: list[str],
    chains: Optional[list[str]] = None,
    save_raw: bool = True,
    name_threshold: float = 0.72,
    observed_at: Optional[datetime] = None,
) -> dict:
    """
    Run a batch MCP price lookup for *products* against *chains*.

    Parameters
    ----------
    products       : Barcodes (numeric) or product name strings from YomYom POS.
    chains         : Target chains to query.  Default: all available (Alonit family).
    save_raw       : Persist raw matched rows as JSON to the raw storage layer.
    name_threshold : Fuzzy-match cutoff for product names (0–1, default 0.72).
    observed_at    : Override timestamp (default: UTC now).

    Returns
    -------
    dict with keys:
      status, coverage_report, observations (list of dicts), raw_output_path
    """
    if not products:
        return {"status": "error", "reason": "products list is empty"}

    if chains is None:
        chains = DEFAULT_CHAINS

    if observed_at is None:
        observed_at = datetime.now(tz=timezone.utc)

    obs_ts = observed_at.isoformat()
    logger.info(
        "=== MCP price lookup: {} products, chains={} ===",
        len(products), chains,
    )

    # ── 1. Load price data ────────────────────────────────────────────────────
    df = load_price_dataframe(chains)
    if df.is_empty():
        logger.warning("No price data available — returning empty results")
        coverage = build_coverage_report(products, {}, chains, observed_at)
        coverage["warning"] = (
            "No price data found.  Run: python scripts/run_alonit_collector.py"
        )
        return {
            "status":           "ok",
            "coverage_report":  coverage,
            "observations":     [],
            "raw_output_path":  None,
        }

    logger.info("Price data loaded: {} rows x {} cols", df.height, df.width)

    # ── 2. Match each product ─────────────────────────────────────────────────
    raw_matches: dict[str, list[dict]] = {}
    results:     dict[str, list[ExternalProductObservation]] = {}

    for product in products:
        matched_rows = match_identifier(product, df, name_threshold=name_threshold)
        raw_matches[product] = matched_rows
        results[product] = [
            normalize_row(row, product, observed_at)
            for row in matched_rows
        ]
        status_str = f"{len(matched_rows)} hit(s)" if matched_rows else "NO MATCH"
        logger.info("  {!r:40s} → {}", product, status_str)

    # ── 3. Save raw MCP output ────────────────────────────────────────────────
    raw_output_path: Optional[str] = None
    if save_raw:
        raw_payload = {
            "source":           SOURCE_ID,
            "observed_at":      obs_ts,
            "chains_requested": chains,
            "queried_products": products,
            "name_threshold":   name_threshold,
            "matches": {
                ident: rows for ident, rows in raw_matches.items()
            },
        }
        try:
            raw_bytes = json.dumps(
                raw_payload, indent=2, ensure_ascii=False, default=str
            ).encode("utf-8")
            data_path, _ = save_raw_file(
                source_id=SOURCE_ID,
                original_filename=f"{SOURCE_ID}_lookup.json",
                file_bytes=raw_bytes,
                observed_at=obs_ts,
                source_url=None,
            )
            raw_output_path = str(data_path)
            logger.info("Raw MCP output saved: {}", raw_output_path)
        except Exception as exc:
            logger.error("Failed to save raw MCP output: {}", exc)

    # ── 4. Coverage report ────────────────────────────────────────────────────
    coverage = build_coverage_report(products, results, chains, observed_at)

    logger.info(
        "=== MCP lookup complete: {}/{} matched  branch_level={} ===",
        coverage["matched_count"],
        coverage["queried_count"],
        coverage["branch_level_available"],
    )

    return {
        "status":          "ok",
        "coverage_report": coverage,
        "observations":    [
            obs.model_dump(mode="json")
            for obs_list in results.values()
            for obs in obs_list
        ],
        "raw_output_path": raw_output_path,
    }
