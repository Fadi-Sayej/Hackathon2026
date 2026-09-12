"""
competitor_product_signals.py — unified competitor-product signal builder.

Reads existing silver Parquet from two source families:

  Alonit price-transparency   data/external/silver/alonit_prices/**/*.parquet
  Wolt delivery catalog       data/external/silver/products/delivery_catalog/**/*.parquet

Produces:

  data/signals/competitor_product_signals/
    competitor_product_signals_<timestamp>.parquet

  reports/quality/
    competitor_product_signals_<timestamp>.json

Signal semantics (see docs/sources/alonit_signal_source.md for full detail)
---------------------------------------------------------------------------
  price_file only:
    appears_in_price_file        = True
    appears_in_delivery_catalog  = False
    explicit_online_available    = None   ← never inferred
    availability_confidence      = "low"
    price_signal_confidence      = "official"

  delivery_catalog only:
    appears_in_price_file        = False
    appears_in_delivery_catalog  = True
    explicit_online_available    = source value if present, else None
    availability_confidence      = "high" if explicit availability, else "medium"
    price_signal_confidence      = "platform"

  merged (both sources):
    appears_in_price_file        = True
    appears_in_delivery_catalog  = True
    explicit_online_available    = source value from delivery catalog
    availability_confidence      = "medium"  (unless explicit → "high")
    price_signal_confidence      = "official"  (FTP file takes precedence)

Merge strategy
--------------
  Pass 1: exact barcode + normalized_chain
  Pass 2: normalized_product_name + category + normalized_chain
  Unmatched records from both sources kept as standalone signals.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from loguru import logger

# ── project root ──────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

from src.common.paths import EXTERNAL_SILVER_ROOT, SIGNALS_ROOT, QUALITY_ROOT
from src.engine.model import norm_barcode


# ── Paths ─────────────────────────────────────────────────────────────────────

ALONIT_SILVER_DIR  = EXTERNAL_SILVER_ROOT / "alonit_prices"
WOLT_SILVER_DIR    = EXTERNAL_SILVER_ROOT / "products" / "delivery_catalog"
OUTPUT_DIR         = SIGNALS_ROOT / "competitor_product_signals"


# ── Size / unit extraction ────────────────────────────────────────────────────

_SIZE_RE = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*"
    r"(m[\"']?[Ll]|[Ll]\b|[Kk][Gg]\b|[Gg]\b|[Oo][Zz]\b|[Cc][Ll]\b|"
    r"[Cc][Cc]\b|[Pp][Cc][Ss]?\b|[Pp][Aa][Cc][Kk]?\b|[Uu][Nn][Ii][Tt][Ss]?\b|"
    r'מ["\']?ל|ג["\']?ר|גרם|קג|ליטר|יח["\']?|יחידות?)',
    re.IGNORECASE,
)

_NOISE_RE = re.compile(r"[^\w\s֐-׿]")  # strip punctuation, keep Hebrew


def _extract_size(name: str) -> str:
    """Pull the first size token (e.g. '250ml', '1.5L', '100 גרם') from a name."""
    m = _SIZE_RE.search(name or "")
    return m.group(0).strip() if m else ""


def _normalize_name(name: str) -> str:
    """
    Lowercase, strip size tokens and punctuation for fuzzy matching.
    Hebrew characters are preserved.
    """
    if not name:
        return ""
    n = name.lower().strip()
    n = _SIZE_RE.sub(" ", n)            # remove size tokens
    n = _NOISE_RE.sub(" ", n)           # remove punctuation
    n = re.sub(r"\s+", " ", n).strip()
    return n


# ── Chain normalization ───────────────────────────────────────────────────────

_CHAIN_MAP: dict[str, str] = {
    "alonit":        "alonit",
    "super alonit":  "super_alonit",
    "super-alonit":  "super_alonit",
    "superalonit":   "super_alonit",
    "super_alonit":  "super_alonit",
    "dor alon":      "dor_alon",
    "doralon":       "dor_alon",
    "dor-alon":      "dor_alon",
}

# Sub-chain → parent family group.
# Used during merge so that "Alonit" (FTP price file) and "super alonit"
# (Wolt delivery catalog) are treated as the same family when matching
# by barcode.  The merged record preserves the individual chain names.
_CHAIN_FAMILY: dict[str, str] = {
    "alonit":       "dor_alon",
    "super_alonit": "dor_alon",
    "dor_alon":     "dor_alon",
}


def _normalize_chain(chain: str) -> str:
    s = (chain or "").lower().strip()
    return _CHAIN_MAP.get(s, s.replace(" ", "_"))


def _chain_family(chain: str) -> str:
    """Return the broad family group for cross-sub-chain merging."""
    cn = _normalize_chain(chain)
    return _CHAIN_FAMILY.get(cn, cn)


# ── Signal ID ─────────────────────────────────────────────────────────────────

def _signal_id(
    barcode: Optional[str],
    normalized_chain: str,
    normalized_name: str,
    source_type: str,
) -> str:
    """Deterministic 16-hex-char signal ID."""
    key = f"{barcode or ''}|{normalized_chain}|{normalized_name}|{source_type}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return None


# ── Parquet loader ────────────────────────────────────────────────────────────

def _load_all_parquets(base_dir: Path, label: str) -> pl.DataFrame:
    """
    Load and concatenate all Parquet files under *base_dir*.

    Deduplicates by (barcode, store_id) keeping the most recently ingested row
    for each pair, so re-runs of the same collection don't double-count products.
    """
    if not base_dir.exists():
        logger.warning("{} dir not found: {}", label, base_dir)
        return pl.DataFrame()

    files = sorted(base_dir.rglob("*.parquet"), key=lambda p: p.stat().st_mtime)
    if not files:
        logger.warning("No Parquet files found in {}", base_dir)
        return pl.DataFrame()

    logger.info("Loading {} Parquet files for {}", len(files), label)

    # Dedup incrementally instead of concatenating everything first.
    #
    # The result keeps only the most recent row per (barcode, store_id), so the
    # older days contribute almost nothing — but holding all of them in memory at
    # once is what actually decided whether this runs. On a GitHub runner the
    # all-at-once concat of 31 days was killed with SIGTERM (exit 143) before it
    # ever reached the dedup. Folding each file in and deduping immediately keeps
    # peak memory at roughly one file plus the deduped frame, and grows with the
    # catalogue rather than with the length of history.
    #
    # Semantics are unchanged: the same sort-by-ingestion and unique-by-pair runs,
    # just repeatedly rather than once at the end.
    def _dedup(frame: pl.DataFrame) -> pl.DataFrame:
        ts_col = "_ingested_at" if "_ingested_at" in frame.columns else None
        if ts_col and "barcode" in frame.columns and "store_id" in frame.columns:
            return (
                frame.sort(ts_col, descending=True)
                     .unique(subset=["barcode", "store_id"], keep="first", maintain_order=True)
            )
        return frame

    df: pl.DataFrame | None = None
    for f in files:
        try:
            chunk = pl.read_parquet(f)
        except Exception as exc:
            logger.warning("Skipping unreadable Parquet {}: {}", f, exc)
            continue
        if df is None:
            df = _dedup(chunk)
            continue
        try:
            df = _dedup(pl.concat([df, chunk], how="diagonal_relaxed"))
        except Exception as exc:
            logger.warning("concat failed for {} ({}); keeping what we have", f, exc)

    if df is None:
        return pl.DataFrame()

    logger.info("  {} rows after dedup for {}", len(df), label)
    return df


# ── Row mappers ───────────────────────────────────────────────────────────────

def _col(row: dict, *keys, default=None):
    """First non-None value from *keys* in *row*, or *default*."""
    for k in keys:
        v = row.get(k)
        if v is not None and v != "":
            return v
    return default


def _map_alonit_row(row: dict, created_at: str) -> dict:
    """Map one Alonit price-file row to the signal schema."""
    barcode   = norm_barcode(_col(row, "barcode", "sku"))
    chain_raw = _col(row, "store_chain", default="")
    chain_n   = _normalize_chain(chain_raw)
    name_raw  = _col(row, "product_name", default="")
    name_n    = _normalize_name(name_raw)
    size      = _extract_size(name_raw)

    price_raw = _safe_float(_col(row, "price"))
    promo_raw = _safe_float(_col(row, "sale_price"))

    source_path = _col(row, "raw_file_path", "_ingested_at", default="")

    return {
        "signal_id":                 _signal_id(barcode, chain_n, name_n, "price_file"),
        "observed_at":               _col(row, "_ingested_at", "observed_at", default=created_at),
        "competitor_chain":          chain_raw,
        "competitor_brand":          _col(row, "brand"),
        "competitor_store_name":     _col(row, "store_name"),
        "competitor_store_id":       _col(row, "store_id"),
        "competitor_store_type":     "supermarket",
        "source_ids":                [_col(row, "source_id", default="alonit")],
        "source_types":              ["price_file"],
        "barcode":                   barcode,
        "external_product_key":      barcode or _signal_id(None, chain_n, name_n, "price_file"),
        "raw_product_name":          name_raw,
        "normalized_product_name":   name_n,
        "brand":                     _col(row, "brand"),
        "category":                  _col(row, "category"),
        "size":                      size,
        "unit":                      _col(row, "unit"),
        "price_file_price":          price_raw,
        "delivery_catalog_price":    None,
        "promo_price":               promo_raw,
        "appears_in_price_file":     True,
        "appears_in_delivery_catalog": False,
        "explicit_online_available": None,   # price files carry no availability signal
        "availability_confidence":   "low",
        "price_signal_confidence":   "official",
        "rank_in_category":          None,
        "is_most_ordered":           None,
        "raw_source_paths":          [str(source_path)] if source_path else [],
        "created_at":                created_at,
    }


def _map_wolt_row(row: dict, created_at: str) -> dict:
    """Map one Wolt delivery-catalog row to the signal schema."""
    barcode   = norm_barcode(_col(row, "barcode"))
    sku       = _col(row, "sku")
    chain_raw = _col(row, "store_chain", default="")
    chain_n   = _normalize_chain(chain_raw)
    name_raw  = _col(row, "product_name", default="")
    name_n    = _normalize_name(name_raw)
    size      = _extract_size(name_raw)

    # Wolt prices are stored as strings
    price_raw = _safe_float(_col(row, "price"))
    promo_raw = _safe_float(_col(row, "sale_price"))

    # Wolt is_online_available is Boolean (explicit when True)
    is_online = row.get("is_online_available")
    avail_conf = "high" if is_online is True else "medium"

    rank = row.get("rank_in_category")
    if isinstance(rank, float):
        rank = int(rank)

    source_path = _col(row, "raw_file_path", "source_product_url", default="")

    return {
        "signal_id":                 _signal_id(barcode, chain_n, name_n, "delivery_catalog"),
        "observed_at":               _col(row, "observed_at", "_ingested_at", default=created_at),
        "competitor_chain":          chain_raw,
        "competitor_brand":          _col(row, "brand"),
        "competitor_store_name":     _col(row, "store_name"),
        "competitor_store_id":       _col(row, "store_id"),
        "competitor_store_type":     "supermarket_delivery",
        "source_ids":                [_col(row, "source_id", default="delivery_catalog")],
        "source_types":              ["delivery_catalog"],
        "barcode":                   barcode,
        "external_product_key":      barcode or sku or _signal_id(None, chain_n, name_n, "delivery_catalog"),
        "raw_product_name":          name_raw,
        "normalized_product_name":   name_n,
        "brand":                     _col(row, "brand"),
        "category":                  _col(row, "category"),
        "size":                      size,
        "unit":                      _col(row, "unit"),
        "price_file_price":          None,
        "delivery_catalog_price":    price_raw,
        "promo_price":               promo_raw,
        "appears_in_price_file":     False,
        "appears_in_delivery_catalog": True,
        "explicit_online_available": is_online,
        "availability_confidence":   avail_conf,
        "price_signal_confidence":   "platform",
        "rank_in_category":          rank,
        "is_most_ordered":           row.get("most_ordered"),
        "raw_source_paths":          [str(source_path)] if source_path else [],
        "created_at":                created_at,
    }


# ── Merger ────────────────────────────────────────────────────────────────────

def _merge_two(alonit: dict, wolt: dict) -> dict:
    """
    Produce a merged signal record from a matching (alonit, wolt) pair.

    The merged record:
    - carries prices from both sources
    - sets both appears_in_* flags to True
    - uses the delivery-catalog's explicit_online_available (when present)
    - availability_confidence → "high" if explicit, else "medium"
    - price_signal_confidence → "official" (FTP price takes precedence)
    - competitor_store_type → "supermarket" (physical store confirmed)
    """
    is_online = wolt.get("explicit_online_available")
    avail_conf = "high" if is_online is True else "medium"

    barcode = alonit.get("barcode") or wolt.get("barcode")
    chain_n = _normalize_chain(
        alonit.get("competitor_chain") or wolt.get("competitor_chain") or ""
    )
    name_n  = alonit.get("normalized_product_name") or wolt.get("normalized_product_name") or ""

    merged_sources  = sorted(set(alonit.get("source_ids", []) + wolt.get("source_ids", [])))
    merged_types    = sorted({"price_file", "delivery_catalog"})
    merged_paths    = list({
        p for p in (alonit.get("raw_source_paths", []) + wolt.get("raw_source_paths", []))
        if p
    })

    return {
        "signal_id":                 _signal_id(barcode, chain_n, name_n, "merged"),
        "observed_at":               max(
            alonit.get("observed_at", ""),
            wolt.get("observed_at", ""),
        ),
        "competitor_chain":          alonit.get("competitor_chain") or wolt.get("competitor_chain"),
        "competitor_brand":          wolt.get("competitor_brand") or alonit.get("competitor_brand"),
        "competitor_store_name":     alonit.get("competitor_store_name") or wolt.get("competitor_store_name"),
        "competitor_store_id":       alonit.get("competitor_store_id") or wolt.get("competitor_store_id"),
        "competitor_store_type":     "supermarket",
        "source_ids":                merged_sources,
        "source_types":              merged_types,
        "barcode":                   barcode,
        "external_product_key":      barcode or alonit.get("external_product_key"),
        "raw_product_name":          alonit.get("raw_product_name") or wolt.get("raw_product_name"),
        "normalized_product_name":   name_n,
        "brand":                     wolt.get("brand") or alonit.get("brand"),
        "category":                  wolt.get("category") or alonit.get("category"),
        "size":                      wolt.get("size") or alonit.get("size"),
        "unit":                      wolt.get("unit") or alonit.get("unit"),
        "price_file_price":          alonit.get("price_file_price"),
        "delivery_catalog_price":    wolt.get("delivery_catalog_price"),
        "promo_price":               wolt.get("promo_price") or alonit.get("promo_price"),
        "appears_in_price_file":     True,
        "appears_in_delivery_catalog": True,
        "explicit_online_available": is_online,
        "availability_confidence":   avail_conf,
        "price_signal_confidence":   "official",
        "rank_in_category":          wolt.get("rank_in_category"),
        "is_most_ordered":           wolt.get("is_most_ordered"),
        "raw_source_paths":          merged_paths,
        "created_at":                alonit.get("created_at"),
    }


# ── Merge pipeline ────────────────────────────────────────────────────────────

def merge_signals(
    alonit_signals: list[dict],
    wolt_signals:   list[dict],
) -> list[dict]:
    """
    Merge Alonit and Wolt signal lists.

    Pass 1: barcode + normalized_chain (exact)
    Pass 2: normalized_product_name + category + normalized_chain (name match)
    Unmatched records from both sources are appended as standalone signals.

    Returns the unified list (merged + standalone).
    """
    # ── Build Alonit indexes ──────────────────────────────────────────────────
    # Two tiers of chain key:
    #   exact  = normalised sub-chain ("alonit", "super_alonit")
    #   family = broad parent group   ("dor_alon")
    # Pass 1 prefers exact chain match; if that misses, falls back to family so
    # that Alonit FTP data (chain="Alonit") can join with Wolt data
    # (chain="super alonit") when they share a barcode — they are both Dor Alon
    # sub-chains, and the barcode proves they are the same product.
    alonit_by_bc_exact:   dict[tuple, dict] = {}  # (barcode, exact_chain)
    alonit_by_bc_family:  dict[tuple, dict] = {}  # (barcode, family_group)
    alonit_by_name_exact: dict[tuple, dict] = {}  # (name, cat, exact_chain)
    alonit_by_name_family: dict[tuple, dict] = {} # (name, cat, family_group)

    for sig in alonit_signals:
        bc     = sig.get("barcode")
        chain  = _normalize_chain(sig.get("competitor_chain", ""))
        family = _chain_family(sig.get("competitor_chain", ""))
        nn     = sig.get("normalized_product_name", "")
        cat    = sig.get("category", "") or ""

        if bc:
            alonit_by_bc_exact.setdefault((bc, chain), sig)
            alonit_by_bc_family.setdefault((bc, family), sig)
        if nn:
            alonit_by_name_exact.setdefault((nn, cat, chain), sig)
            alonit_by_name_family.setdefault((nn, cat, family), sig)

    merged_alonit_ids: set[str] = set()   # signal_ids that have been merged
    output: list[dict] = []

    # ── Process Wolt signals ──────────────────────────────────────────────────
    for wsig in wolt_signals:
        bc     = wsig.get("barcode")
        chain  = _normalize_chain(wsig.get("competitor_chain", ""))
        family = _chain_family(wsig.get("competitor_chain", ""))
        nn     = wsig.get("normalized_product_name", "")
        cat    = wsig.get("category", "") or ""

        match: Optional[dict] = None

        # Pass 1a: barcode + exact chain
        if bc:
            match = alonit_by_bc_exact.get((bc, chain))
        # Pass 1b: barcode + family group (cross-sub-chain: e.g. Alonit ↔ Super Alonit)
        if match is None and bc:
            match = alonit_by_bc_family.get((bc, family))
        # Pass 2a: name + category + exact chain
        if match is None and nn:
            match = alonit_by_name_exact.get((nn, cat, chain))
        # Pass 2b: name + category + family group
        if match is None and nn:
            match = alonit_by_name_family.get((nn, cat, family))

        if match is not None and match["signal_id"] not in merged_alonit_ids:
            merged_alonit_ids.add(match["signal_id"])
            output.append(_merge_two(match, wsig))
            logger.debug(
                "Merged  bc={!r}  name={!r}  chain={}",
                bc, wsig.get("raw_product_name"), chain,
            )
        else:
            output.append(wsig)

    # ── Append unmatched Alonit signals ───────────────────────────────────────
    for asig in alonit_signals:
        if asig["signal_id"] not in merged_alonit_ids:
            output.append(asig)

    merged_count = len(merged_alonit_ids)
    logger.info(
        "merge_signals: alonit={} wolt={} merged={} total_output={}",
        len(alonit_signals), len(wolt_signals), merged_count, len(output),
    )
    return output


# ── Quality report ────────────────────────────────────────────────────────────

def build_quality_report(
    signals: list[dict],
    run_ts:  datetime,
    output_parquet: Path,
) -> dict:
    """Build the quality-report dict for a competitor_product_signals run."""
    total = len(signals)

    barcodes       = {s["barcode"] for s in signals if s.get("barcode")}
    names          = {s["normalized_product_name"] for s in signals if s.get("normalized_product_name")}
    categories     = {s["category"] for s in signals if s.get("category")}

    pf_only   = sum(1 for s in signals if s["appears_in_price_file"] and not s["appears_in_delivery_catalog"])
    dc_only   = sum(1 for s in signals if s["appears_in_delivery_catalog"] and not s["appears_in_price_file"])
    both      = sum(1 for s in signals if s["appears_in_price_file"] and s["appears_in_delivery_catalog"])

    miss_bc   = sum(1 for s in signals if not s.get("barcode"))
    miss_p    = sum(1 for s in signals if s.get("price_file_price") is None and s.get("delivery_catalog_price") is None)
    explicit  = sum(1 for s in signals if s.get("explicit_online_available") is not None)

    avail_dist: dict[str, int] = {}
    for s in signals:
        k = s.get("availability_confidence", "unknown")
        avail_dist[k] = avail_dist.get(k, 0) + 1

    price_dist: dict[str, int] = {}
    for s in signals:
        k = s.get("price_signal_confidence", "unknown")
        price_dist[k] = price_dist.get(k, 0) + 1

    return {
        "run_at":                      run_ts.isoformat(),
        "output_parquet":              str(output_parquet),
        "total_signals":               total,
        "unique_barcodes":             len(barcodes),
        "unique_products":             len(names),
        "categories_count":            len(categories),
        "price_file_only_count":       pf_only,
        "delivery_catalog_only_count": dc_only,
        "both_sources_count":          both,
        "missing_barcode_count":       miss_bc,
        "missing_barcode_pct":         round(miss_bc / total * 100, 2) if total else 0.0,
        "missing_price_count":         miss_p,
        "missing_price_pct":           round(miss_p / total * 100, 2) if total else 0.0,
        "explicit_availability_count": explicit,
        "availability_confidence_dist": avail_dist,
        "price_signal_confidence_dist": price_dist,
    }


# ── Output writer ─────────────────────────────────────────────────────────────

def _write_output_parquet(signals: list[dict], ts_str: str) -> Path:
    """Write the signal list to a date-partitioned Parquet file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"competitor_product_signals_{ts_str}.parquet"

    # Normalise list fields to plain Python lists (not sets, etc.)
    for sig in signals:
        for f in ("source_ids", "source_types", "raw_source_paths"):
            v = sig.get(f)
            if v is None:
                sig[f] = []
            elif not isinstance(v, list):
                sig[f] = list(v)

    table = pa.Table.from_pylist(signals) if signals else pa.table({})
    pq.write_table(table, str(path), compression="snappy")
    logger.info("Signal Parquet written ({} rows): {}", len(signals), path)
    return path


def _write_quality_report(report: dict, ts_str: str) -> Path:
    QUALITY_ROOT.mkdir(parents=True, exist_ok=True)
    path = QUALITY_ROOT / f"competitor_product_signals_{ts_str}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Quality report: {}", path)
    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def build_competitor_product_signals(
    run_at: Optional[datetime] = None,
) -> dict:
    """
    Run the full competitor-product signal build pipeline.

    Steps
    -----
    1. Load all Alonit price-transparency silver Parquet.
    2. Load all Wolt delivery-catalog silver Parquet.
    3. Map each source to the unified signal schema.
    4. Merge by barcode+chain, then by name+category+chain.
    5. Write output Parquet.
    6. Write quality report.

    Returns
    -------
    dict with keys: status, output_parquet, quality_report, metrics
    """
    if run_at is None:
        run_at = datetime.now(tz=timezone.utc)

    ts_str = run_at.strftime("%Y%m%dT%H%M%S")
    created_at = run_at.isoformat()

    logger.info("=== Building competitor_product_signals at {} ===", created_at)

    # ── 1. Load sources ───────────────────────────────────────────────────────
    alonit_df = _load_all_parquets(ALONIT_SILVER_DIR, "alonit_prices")
    wolt_df   = _load_all_parquets(WOLT_SILVER_DIR,   "wolt_delivery_catalog")

    if alonit_df.is_empty() and wolt_df.is_empty():
        logger.warning("No source data found — writing empty output")

    # ── 2. Map to signal schema ───────────────────────────────────────────────
    alonit_signals = [_map_alonit_row(r, created_at) for r in alonit_df.to_dicts()] if not alonit_df.is_empty() else []
    wolt_signals   = [_map_wolt_row(r,   created_at) for r in wolt_df.to_dicts()]   if not wolt_df.is_empty()   else []

    logger.info(
        "Mapped: {} alonit signals, {} wolt signals",
        len(alonit_signals), len(wolt_signals),
    )

    # ── 3. Merge ──────────────────────────────────────────────────────────────
    signals = merge_signals(alonit_signals, wolt_signals)

    # ── 4. Write Parquet ──────────────────────────────────────────────────────
    out_path = _write_output_parquet(signals, ts_str)

    # ── 5. Quality report ─────────────────────────────────────────────────────
    qr = build_quality_report(signals, run_at, out_path)
    qr_path = _write_quality_report(qr, ts_str)

    # ── 5b. Source status contract ────────────────────────────────────────────
    try:
        from src.common.source_status import update_source

        update_source(
            "wolt_delivery",
            status="complete" if not wolt_df.is_empty() else "not_started",
            row_count=len(wolt_signals),
        )
        update_source(
            "alonit_prices",
            status="complete" if not alonit_df.is_empty() else "not_started",
            row_count=len(alonit_signals),
        )
    except Exception:  # status tracking must never break the build
        pass

    logger.info(
        "=== Done: {} signals  "
        "(pf_only={} dc_only={} both={})  "
        "match_rate={}% ===",
        qr["total_signals"],
        qr["price_file_only_count"],
        qr["delivery_catalog_only_count"],
        qr["both_sources_count"],
        round(
            qr["both_sources_count"] / max(qr["price_file_only_count"] + qr["both_sources_count"], 1) * 100,
            1,
        ),
    )

    return {
        "status":          "ok",
        "output_parquet":  str(out_path),
        "quality_report":  str(qr_path),
        "metrics":         qr,
    }
