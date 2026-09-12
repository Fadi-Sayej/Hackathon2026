"""
product_matching.py — YomYom internal product ↔ competitor signal matcher.

Matching passes (in priority order, first hit wins per YomYom product)
----------------------------------------------------------------------
  1. barcode_exact
       confidence = 1.0
       auto_approved = True
       Requires: identical non-null barcode on both sides.

  2. name_normalized
       confidence = f(fields that agree: name, brand, size, unit)
       auto_approved iff confidence >= 0.90
       Fields: normalized product name (size tokens stripped) + brand +
               extracted size token + unit-of-measure.
       Min confidence for this pass = 0.80 (name match is required).

  3. fuzzy_name
       scorer: rapidfuzz WRatio (handles partial/transposed strings)
       score range: 0–100  →  0.0–1.0 after /100
       auto_approved   iff score >= 0.85
       manual_review   iff 0.75 <= score < 0.85
       ignored         iff score < 0.75

Language note
-------------
The fake YomYom POS file uses English product names while the Alonit price-
file corpus is ~100% Hebrew.  Fuzzy scores across languages will be very low
(<0.5 for most pairs), so the manual review queue will be empty and match
rates will be near 0% with this fake dataset.  All counts, methods and
confidence levels are correct; they simply reflect the language mismatch.
When the real YomYom POS file arrives (Hebrew names, real GTINs) the same
pipeline will produce high-confidence barcode and name matches.

Inputs
------
  Prefer:  data/internal/silver_pos/yomyom_products.parquet
  Fallback: data/internal/raw_pos/yomyom/sample_yomyom_pos.csv

  Prefer:  data/signals/competitor_product_signals/**/*.parquet
  Fallback: data/external/silver/alonit_prices/**/*.parquet
            data/external/silver/products/delivery_catalog/**/*.parquet

Outputs
-------
  data/matching/product_matches.parquet
  data/matching/manual_review_queue.parquet
  reports/quality/product_matching_<timestamp>.json
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
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

try:
    from rapidfuzz import process as _rfuzz_proc, fuzz as _rfuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False
    logger.warning("rapidfuzz not installed — fuzzy matching disabled.  pip install rapidfuzz")

from src.common.paths import (
    INTERNAL_ROOT, SIGNALS_ROOT, EXTERNAL_SILVER_ROOT,
    MATCHING_ROOT, QUALITY_ROOT,
)
from src.engine.model import norm_barcode


# ── Constants ─────────────────────────────────────────────────────────────────

# Auto-approval confidence thresholds
_APPROVE_THRESHOLD = {
    "barcode_exact":  0.0,    # always approved
    "name_normalized": 0.90,
    "fuzzy_name":      0.85,
}
# Minimum confidence to even include in output (lower → ignore)
_INCLUDE_THRESHOLD = {
    "name_normalized": 0.75,
    "fuzzy_name":      0.75,
}
# 0.75 – threshold: manual review bucket
_REVIEW_MAX = {
    "fuzzy_name":      0.85,
    "name_normalized": 0.90,
}

# Paths
YOMYOM_PRODUCTS_PARQUET = INTERNAL_ROOT / "silver_pos" / "yomyom_products.parquet"
YOMYOM_POS_CSV          = INTERNAL_ROOT / "raw_pos" / "yomyom" / "sample_yomyom_pos.csv"
COMPETITOR_SIGNALS_DIR  = SIGNALS_ROOT  / "competitor_product_signals"
MATCHES_PATH            = MATCHING_ROOT / "product_matches.parquet"
REVIEW_PATH             = MATCHING_ROOT / "manual_review_queue.parquet"


# ── Text normalisation (shared with competitor_product_signals) ────────────────

_SIZE_RE = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*"
    r"(m[\"']?[Ll]|[Ll]\b|[Kk][Gg]\b|[Gg]\b|[Oo][Zz]\b|[Cc][Ll]\b|[Cc][Cc]\b|"
    r"[Pp][Cc][Ss]?\b|[Pp][Aa][Cc][Kk]?\b|[Uu][Nn][Ii][Tt][Ss]?\b|"
    r'מ["\']?ל|גרם|ג["\']?ר|קג|ליטר|יחידות?|יח["\']?)',
    re.IGNORECASE,
)
_NOISE_RE = re.compile(r"[^\w\s֐-׿]")
_WS_RE    = re.compile(r"\s+")


def _norm(s: str) -> str:
    """Lowercase, strip size tokens and punctuation."""
    if not s:
        return ""
    n = s.lower().strip()
    n = _SIZE_RE.sub(" ", n)
    n = _NOISE_RE.sub(" ", n)
    return _WS_RE.sub(" ", n).strip()


def _extract_size(s: str) -> str:
    m = _SIZE_RE.search(s or "")
    return m.group(0).strip().lower() if m else ""


def _norm_brand(s: str) -> str:
    return (s or "").lower().strip()


def _block_key(normalized_name: str) -> str:
    """Return a small candidate-block key for fuzzy matching."""
    stopwords = {
        "the",
        "a",
        "an",
        "מוצר",
        "מוצרי",
        "יח",
        "יחידה",
        "יחידות",
        "מארז",
    }
    for token in (normalized_name or "").split():
        if len(token) >= 3 and token not in stopwords:
            return token
    return ""


# ── ID helpers ─────────────────────────────────────────────────────────────────

def _internal_id(row: dict) -> str:
    bc = row.get("barcode") or row.get("id")
    if bc:
        return str(bc)
    return hashlib.sha256(
        (row.get("product_name", "") + row.get("category", "")).encode()
    ).hexdigest()[:12]


def _match_id(internal_id: str, external_key: str, method: str) -> str:
    key = f"{internal_id}|{external_key}|{method}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_internal_products() -> pl.DataFrame:
    """Load YomYom internal products (parquet preferred, CSV fallback)."""
    if YOMYOM_PRODUCTS_PARQUET.exists():
        logger.info("Loading internal products from {}", YOMYOM_PRODUCTS_PARQUET)
        return pl.read_parquet(YOMYOM_PRODUCTS_PARQUET)
    if YOMYOM_POS_CSV.exists():
        logger.info("Loading internal products from {}", YOMYOM_POS_CSV)
        return pl.read_csv(YOMYOM_POS_CSV)
    raise FileNotFoundError(
        f"No internal product source found.  Expected:\n"
        f"  {YOMYOM_PRODUCTS_PARQUET}\n"
        f"  {YOMYOM_POS_CSV}"
    )


def load_competitor_signals() -> pl.DataFrame:
    """
    Load competitor product signals.

    Preference order:
      1. data/signals/competitor_product_signals/**/*.parquet
      2. data/external/silver/alonit_prices/**/*.parquet
         + data/external/silver/products/delivery_catalog/**/*.parquet
         (combined with minimal schema remapping)
    """
    sig_files = sorted(COMPETITOR_SIGNALS_DIR.rglob("*.parquet"),
                       key=lambda p: p.stat().st_mtime)
    if sig_files:
        latest = sig_files[-1]
        logger.info(
            "Loading latest competitor signal file ({}/{}): {}",
            1,
            len(sig_files),
            latest,
        )
        df = pl.read_parquet(latest)
        logger.info("  {} competitor signals loaded", len(df))
        return df

    # Fallback: read raw silver Parquet and remap to a minimal signal schema
    logger.warning("No competitor_product_signals found; falling back to silver Parquet")
    frames: list[pl.DataFrame] = []

    for base in (
        EXTERNAL_SILVER_ROOT / "alonit_prices",
        EXTERNAL_SILVER_ROOT / "products" / "delivery_catalog",
    ):
        for f in sorted(base.rglob("*.parquet"), key=lambda p: p.stat().st_mtime):
            try:
                frames.append(pl.read_parquet(f))
            except Exception as exc:
                logger.warning("Skipping {}: {}", f, exc)

    if not frames:
        logger.error("No competitor data found in any location")
        return pl.DataFrame()

    raw = pl.concat(frames, how="diagonal_relaxed")
    # Remap to minimal expected columns
    remap = {
        "external_product_key": raw["barcode"] if "barcode" in raw.columns else pl.Series([None] * len(raw)),
        "barcode":              raw["barcode"] if "barcode" in raw.columns else pl.Series([None] * len(raw)),
        "raw_product_name":     raw["product_name"] if "product_name" in raw.columns else pl.Series([None] * len(raw)),
        "normalized_product_name": pl.Series([_norm(n or "") for n in (raw["product_name"].to_list() if "product_name" in raw.columns else [])]),
        "brand":                raw["brand"] if "brand" in raw.columns else pl.Series([None] * len(raw)),
        "category":             raw["category"] if "category" in raw.columns else pl.Series([None] * len(raw)),
        "size":                 pl.Series([""] * len(raw)),
        "unit":                 raw["unit"] if "unit" in raw.columns else pl.Series([None] * len(raw)),
        "source_types":         pl.Series([["price_file"]] * len(raw)),
    }
    return pl.DataFrame(remap)


def _dedup_competitors(df: pl.DataFrame) -> list[dict]:
    """One row per (product key, store) — every store's price must survive to the
    reference step (SPEC-003 FR-044 needs the cheapest per format)."""
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for row in df.to_dicts():
        key = norm_barcode(row.get("barcode")) or row.get("external_product_key")
        if not key:
            continue
        store = str(row.get("competitor_store_id") or "")
        if (key, store) in seen:
            continue
        seen.add((key, store))
        row["barcode"] = norm_barcode(row.get("barcode"))
        deduped.append(row)
    logger.info("Competitor corpus: {} (product, store) rows (from {} signals)", len(deduped), len(df))
    return deduped


# ── Confidence scoring for name_normalized pass ───────────────────────────────

def _name_norm_confidence(
    yy_name_n: str, yy_brand_n: str, yy_size: str, yy_unit: str,
    cx_name_n: str, cx_brand_n: str, cx_size: str, cx_unit: str,
) -> float:
    """
    Compute confidence for a normalized-name match.

    Base: 0.80 for name-only match.
    +0.05 per additional agreeing field (brand, size, unit).
    Max: 0.95 (name + brand + size + unit all agree).
    """
    if yy_name_n != cx_name_n:
        return 0.0   # names must match exactly at this pass

    conf = 0.80

    if yy_brand_n and cx_brand_n and yy_brand_n == cx_brand_n:
        conf += 0.05
    if yy_size and cx_size and yy_size == cx_size:
        conf += 0.05
    if yy_unit and cx_unit and yy_unit.lower().strip() == cx_unit.lower().strip():
        conf += 0.05

    return min(conf, 0.95)


# ── Match-record factory ───────────────────────────────────────────────────────

def _make_match(
    yy: dict,
    cx: dict,
    method: str,
    confidence: float,
    created_at: str,
) -> dict:
    """Build a fully-populated match record dict."""
    internal_id  = _internal_id(yy)
    external_key = cx.get("external_product_key") or cx.get("barcode") or ""
    approved     = confidence >= _APPROVE_THRESHOLD.get(method, 1.0)
    include_min  = _INCLUDE_THRESHOLD.get(method, 0.0)

    if confidence < include_min:
        return {}   # caller checks for empty dict to skip

    # Review reason
    if method == "barcode_exact":
        review_reason = None
    elif not approved:
        review_reason = (
            f"{method}: confidence {confidence:.2f} below "
            f"auto-approve threshold {_APPROVE_THRESHOLD.get(method)}"
        )
    else:
        review_reason = None

    source_types = cx.get("source_types")
    if source_types is None:
        source_types = []
    elif not isinstance(source_types, list):
        source_types = list(source_types)

    return {
        "match_id":               _match_id(internal_id, external_key, method),
        "internal_product_id":    internal_id,
        "internal_barcode":       yy.get("barcode"),
        "internal_product_name":  yy.get("product_name"),
        "internal_category":      yy.get("category"),
        "external_product_key":   external_key,
        "external_barcode":       cx.get("barcode"),
        "external_product_name":  cx.get("raw_product_name") or cx.get("product_name"),
        "external_category":      cx.get("category"),
        "external_source_types":  source_types,
        "competitor_store_id":    cx.get("competitor_store_id"),
        "match_method":           method,
        "match_confidence":       round(confidence, 4),
        "approved":               approved,
        "review_reason":          review_reason,
        "created_at":             created_at,
    }


# ── Pass 1: barcode_exact ─────────────────────────────────────────────────────

def _pass_barcode_exact(
    yy_rows:  list[dict],
    competitors: list[dict],
    created_at: str,
) -> tuple[list[dict], set[str]]:
    """Return (matches, matched_internal_ids).

    One match per (internal product, competitor store): SPEC-003 FR-044 needs every
    store's price to reach the reference step, so a barcode present in five stores
    yields five rows, not one.
    """
    matches: list[dict] = []
    matched: set[str]   = set()

    by_barcode: dict[str, list[dict]] = {}
    for cx in competitors:
        bc = norm_barcode(cx.get("barcode"))
        if bc:
            by_barcode.setdefault(bc, []).append(cx)

    for yy in yy_rows:
        bc = norm_barcode(yy.get("barcode"))
        if not bc or bc not in by_barcode:
            continue
        for cx in by_barcode[bc]:
            rec = _make_match(yy, cx, "barcode_exact", 1.0, created_at)
            if rec:
                matches.append(rec)
                matched.add(_internal_id(yy))
                logger.debug("barcode_exact: {} ↔ {} @ {}", bc,
                             cx.get("raw_product_name"), cx.get("competitor_store_id"))

    logger.info("Pass 1 barcode_exact:    {} matches", len(matches))
    return matches, matched


# ── Pass 2: name_normalized ────────────────────────────────────────────────────

def _pass_name_normalized(
    yy_rows:    list[dict],
    name_index: dict[str, dict],
    already:    set[str],
    created_at: str,
) -> tuple[list[dict], set[str]]:
    """
    Exact match on normalized product name, then score on brand/size/unit.
    Skips YomYom products already matched in pass 1.
    """
    matches: list[dict] = []
    matched: set[str]   = set()

    for yy in yy_rows:
        iid = _internal_id(yy)
        if iid in already:
            continue

        yy_nn    = _norm(yy.get("product_name", ""))
        yy_brand = _norm_brand(yy.get("brand", ""))
        yy_size  = _extract_size(yy.get("product_name", ""))
        yy_unit  = (yy.get("unit", "") or "").lower().strip()

        cx = name_index.get(yy_nn)
        if cx is None:
            continue

        cx_nn    = cx.get("normalized_product_name", "")
        cx_brand = _norm_brand(cx.get("brand", "") or cx.get("competitor_brand", ""))
        cx_size  = (cx.get("size", "") or "").lower().strip()
        cx_unit  = (cx.get("unit", "") or "").lower().strip()

        conf = _name_norm_confidence(
            yy_nn, yy_brand, yy_size, yy_unit,
            cx_nn, cx_brand, cx_size, cx_unit,
        )

        rec = _make_match(yy, cx, "name_normalized", conf, created_at)
        if rec:
            matches.append(rec)
            matched.add(iid)
            logger.debug(
                "name_normalized (conf={:.2f}): {!r} ↔ {!r}",
                conf, yy.get("product_name"), cx.get("raw_product_name"),
            )

    logger.info("Pass 2 name_normalized:  {} matches", len(matches))
    return matches, matched


# ── Pass 3: fuzzy_name ────────────────────────────────────────────────────────

def _pass_fuzzy_name(
    yy_rows:    list[dict],
    comp_list:  list[dict],
    already:    set[str],
    created_at: str,
) -> list[dict]:
    """
    RapidFuzz WRatio against normalized competitor names.
    Returns all matches with score >= 0.75 (auto-approve >= 0.85).
    """
    if not _HAS_RAPIDFUZZ:
        logger.warning("rapidfuzz not available — skipping fuzzy pass")
        return []

    # Build candidate blocks once. Fuzzy matching is expensive with thousands
    # of POS SKUs, so compare products only against names with a shared leading
    # meaningful token.
    block_choices: dict[str, list[str]] = {}
    choice_map: dict[str, dict] = {}
    for row in comp_list:
        choice = row.get("normalized_product_name", "") or row.get("raw_product_name", "") or ""
        key = _block_key(choice)
        if not key:
            continue
        block_choices.setdefault(key, []).append(choice)
        choice_map.setdefault(choice, row)

    matches: list[dict] = []

    for yy in yy_rows:
        iid = _internal_id(yy)
        if iid in already:
            continue

        yy_nn = _norm(yy.get("product_name", ""))
        if not yy_nn:
            continue
        choices = block_choices.get(_block_key(yy_nn), [])
        if not choices:
            continue

        results = _rfuzz_proc.extract(
            yy_nn,
            choices,
            scorer=_rfuzz.WRatio,
            score_cutoff=75,
            limit=3,
        )

        for matched_str, score, _idx in results:
            conf = round(score / 100, 4)
            if conf < 0.75:
                continue
            cx = choice_map.get(matched_str)
            if cx is None:
                continue
            rec = _make_match(yy, cx, "fuzzy_name", conf, created_at)
            if rec:
                matches.append(rec)
                logger.debug(
                    "fuzzy_name (conf={:.2f}): {!r} ↔ {!r}",
                    conf, yy.get("product_name"), cx.get("raw_product_name"),
                )

    logger.info("Pass 3 fuzzy_name:       {} candidates", len(matches))
    return matches


# ── Manual review queue builder ────────────────────────────────────────────────

_SUSPECTED_REASONS: dict[str, str] = {
    "barcode_exact":   "auto-approved via barcode",
    "name_normalized": "name match but confidence below auto-approve threshold",
    "fuzzy_name":      "fuzzy similarity in review band (0.75–0.85)",
}

_SUGGESTED_ACTIONS: dict[str, str] = {
    "barcode_exact":   "N/A — auto-approved",
    "name_normalized": "verify brand, size and unit agree; approve or reject",
    "fuzzy_name":      "compare product names manually; approve if same SKU",
}


def build_manual_review_queue(all_matches: list[dict]) -> list[dict]:
    """Extract all non-approved matches into a review-friendly format."""
    queue: list[dict] = []
    for m in all_matches:
        if m.get("approved"):
            continue
        queue.append({
            "match_id":             m["match_id"],
            "internal_product_name": m["internal_product_name"],
            "external_product_name": m["external_product_name"],
            "internal_barcode":     m["internal_barcode"],
            "external_barcode":     m["external_barcode"],
            "similarity_score":     m["match_confidence"],
            "match_method":         m["match_method"],
            "suspected_reason":     _SUSPECTED_REASONS.get(m["match_method"], "unknown"),
            "suggested_action":     _SUGGESTED_ACTIONS.get(m["match_method"], "investigate"),
            "review_reason":        m.get("review_reason"),
            "internal_category":    m.get("internal_category"),
            "external_category":    m.get("external_category"),
            "created_at":           m["created_at"],
        })
    return queue


# ── Quality report ─────────────────────────────────────────────────────────────

def build_quality_report(
    internal_count:   int,
    competitor_count: int,
    all_matches:      list[dict],
    review_queue:     list[dict],
    run_at:           datetime,
    matches_path:     Path,
    review_path:      Path,
) -> dict:
    total = len(all_matches)
    by_method: dict[str, int] = {}
    approved = 0
    for m in all_matches:
        by_method[m["match_method"]] = by_method.get(m["match_method"], 0) + 1
        if m.get("approved"):
            approved += 1

    matched_internal = len({m["internal_product_id"] for m in all_matches})
    matched_external = len({m["external_product_key"] for m in all_matches})

    return {
        "run_at":                     run_at.isoformat(),
        "matches_parquet":            str(matches_path),
        "review_queue_parquet":       str(review_path),
        "internal_products_count":    internal_count,
        "competitor_signals_count":   competitor_count,
        "total_matches":              total,
        "matched_internal_products":  matched_internal,
        "unmatched_internal_products": internal_count - matched_internal,
        "matched_competitor_products": matched_external,
        "match_rate_internal_pct":    round(matched_internal / internal_count * 100, 1) if internal_count else 0.0,
        "matches_by_method":          by_method,
        "auto_approved_count":        approved,
        "manual_review_count":        len(review_queue),
        "language_note": (
            "YomYom fake data uses English product names; "
            "Alonit FTP corpus is ~100% Hebrew. "
            "Low match rates are expected with this dataset. "
            "Real POS data (Hebrew names + real GTINs) will produce "
            "high barcode-exact and name match rates."
        ),
    }


# ── Parquet writer ─────────────────────────────────────────────────────────────

def _write_parquet(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Normalise list fields
    for r in records:
        for f in ("external_source_types",):
            v = r.get(f)
            if v is not None and not isinstance(v, list):
                r[f] = list(v)
    table = pa.Table.from_pylist(records) if records else pa.table({})
    pq.write_table(table, str(path), compression="snappy")
    logger.info("{} rows → {}", len(records), path)


def _write_quality_report(report: dict, run_at: datetime) -> Path:
    QUALITY_ROOT.mkdir(parents=True, exist_ok=True)
    ts  = run_at.strftime("%Y%m%dT%H%M%S")
    path = QUALITY_ROOT / f"product_matching_{ts}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Quality report → {}", path)
    return path


# ── Main pipeline ──────────────────────────────────────────────────────────────

def run_product_matching(run_at: Optional[datetime] = None) -> dict:
    """
    Run the full product-matching pipeline.

    Steps
    -----
    1. Load internal (YomYom) products.
    2. Load competitor product signals.
    3. Deduplicate competitor corpus.
    4. Build indices: barcode → row, normalized_name → row.
    5. Pass 1 — barcode_exact.
    6. Pass 2 — name_normalized (unmatched products only).
    7. Pass 3 — fuzzy_name     (still-unmatched products only).
    8. Write product_matches.parquet.
    9. Build manual review queue; write manual_review_queue.parquet.
    10. Write quality report.
    """
    if run_at is None:
        run_at = datetime.now(tz=timezone.utc)
    created_at = run_at.isoformat()

    logger.info("=== Product matching started at {} ===", created_at)

    # ── 1 & 2. Load ───────────────────────────────────────────────────────────
    internal_df  = load_internal_products()
    competitor_df = load_competitor_signals()

    yy_rows  = internal_df.to_dicts()
    comp_raw = len(competitor_df)

    # ── 3. Deduplicate competitor corpus ──────────────────────────────────────
    comp_list = _dedup_competitors(competitor_df)

    # ── 4. Build indices ──────────────────────────────────────────────────────
    bc_index:   dict[str, dict] = {}
    name_index: dict[str, dict] = {}

    for row in comp_list:
        bc  = row.get("barcode")
        nn  = row.get("normalized_product_name", "")
        if bc:
            bc_index.setdefault(bc, row)
        if nn:
            name_index.setdefault(nn, row)

    logger.info(
        "Indices built: {} barcode keys, {} normalized-name keys",
        len(bc_index), len(name_index),
    )

    # ── 5–7. Three-pass matching ───────────────────────────────────────────────
    all_matches: list[dict] = []

    bc_matches, matched_ids = _pass_barcode_exact(yy_rows, comp_list, created_at)
    all_matches.extend(bc_matches)

    nn_matches, nn_ids = _pass_name_normalized(yy_rows, name_index, matched_ids, created_at)
    all_matches.extend(nn_matches)
    matched_ids |= nn_ids

    fz_matches = _pass_fuzzy_name(yy_rows, comp_list, matched_ids, created_at)
    all_matches.extend(fz_matches)

    logger.info(
        "Total match records: {} (bc={} nn={} fuzzy={})",
        len(all_matches), len(bc_matches), len(nn_matches), len(fz_matches),
    )

    # ── 8. Write matches Parquet ──────────────────────────────────────────────
    _write_parquet(all_matches, MATCHES_PATH)

    # ── 9. Manual review queue ────────────────────────────────────────────────
    review_queue = build_manual_review_queue(all_matches)
    _write_parquet(review_queue, REVIEW_PATH)
    logger.info("Manual review queue: {} items", len(review_queue))

    # ── 10. Quality report ────────────────────────────────────────────────────
    qr = build_quality_report(
        internal_count=len(yy_rows),
        competitor_count=comp_raw,
        all_matches=all_matches,
        review_queue=review_queue,
        run_at=run_at,
        matches_path=MATCHES_PATH,
        review_path=REVIEW_PATH,
    )
    qr_path = _write_quality_report(qr, run_at)

    logger.info(
        "=== Matching done: {}/{} internal products matched  review={} ===",
        qr["matched_internal_products"], qr["internal_products_count"],
        qr["manual_review_count"],
    )

    return {
        "status":              "ok",
        "matches_path":        str(MATCHES_PATH),
        "review_queue_path":   str(REVIEW_PATH),
        "quality_report_path": str(qr_path),
        "metrics":             qr,
    }
