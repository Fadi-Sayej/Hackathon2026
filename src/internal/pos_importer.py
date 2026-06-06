"""
pos_importer.py — YomYom POS CSV → Silver Parquet + signals pipeline.

Pipeline stages
───────────────
1. load_csv()            Read raw CSV rows (list of string dicts).
2. apply_schema_mapping  Rename columns, run normalizers, cast types.
3. validate_rows         Reject invalid rows; collect warnings.
4. write_silver_tables   Write 4 Parquet files to data/internal/silver_pos/.
5. generate_pos_quality  Write enriched quality report (POS-aware metrics).
6. generate_signals      Compute 6 business signals; write JSON.

All configuration (column names, thresholds) lives in
configs/pos_schema_mapping.yaml — no hard-coded field names here.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from loguru import logger

# ── project paths ─────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve()
PROJECT_ROOT = _HERE.parents[2]

SILVER_POS_DIR  = PROJECT_ROOT / "data" / "internal" / "silver_pos"
SIGNALS_DIR     = PROJECT_ROOT / "data" / "signals" / "yomyom"
QUALITY_DIR     = PROJECT_ROOT / "reports" / "quality" / "yomyom_pos"
CONFIG_PATH     = PROJECT_ROOT / "configs" / "pos_schema_mapping.yaml"


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD CONFIG
# ─────────────────────────────────────────────────────────────────────────────

def load_config(config_path: Path = CONFIG_PATH) -> dict:
    """Load and return the YAML schema-mapping config."""
    with config_path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    logger.debug("Config loaded from {}", config_path)
    return cfg


# ─────────────────────────────────────────────────────────────────────────────
# 2. LOAD CSV
# ─────────────────────────────────────────────────────────────────────────────

def load_csv(path: Path, encoding: str = "utf-8-sig") -> list[dict[str, str]]:
    """
    Read a POS CSV file and return rows as a list of raw string dicts.

    Parameters
    ----------
    path     : Path to the CSV file.
    encoding : File encoding; utf-8-sig strips the BOM that Excel adds.

    Returns
    -------
    List of {column_header: raw_string_value} dicts.
    """
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding=encoding) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(dict(row))
    logger.info("Loaded {} raw rows from {}", len(rows), path.name)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 3. SCHEMA MAPPING  (rename + normalize + type-cast)
# ─────────────────────────────────────────────────────────────────────────────

def _apply_normalizers(value: str, normalizers: list[str]) -> Optional[str]:
    """Apply a list of named string transforms; return None if null_if_empty fires."""
    v: Optional[str] = value
    for norm in normalizers:
        if v is None:
            break
        if norm == "strip_whitespace":
            v = v.strip()
        elif norm == "null_if_empty":
            v = None if v == "" else v
        elif norm == "lowercase":
            v = v.lower()
        elif norm == "uppercase":
            v = v.upper()
        # future: add more normalizers here
    return v


def _cast(value: Optional[str], dtype: str) -> Any:
    """
    Cast a normalised string value to the target Python type.

    Returns None if value is None or unparseable (with debug log).
    """
    if value is None:
        return None
    try:
        if dtype == "string":
            return value
        elif dtype == "decimal":
            return float(Decimal(value))
        elif dtype == "integer":
            return int(float(value))     # float first handles "5.0" strings
        elif dtype == "date":
            return date.fromisoformat(value).isoformat()   # keep as ISO string
        elif dtype == "boolean":
            return value.lower() in ("1", "true", "yes")
    except (ValueError, InvalidOperation, AttributeError) as exc:
        logger.debug("Cast failed ({} → {}): {} — {}", value, dtype, type(exc).__name__, exc)
        return None
    return value


# ── Column resolution ─────────────────────────────────────────────────────────

def _resolve_column_map(
    csv_headers: list[str],
    col_specs: list[dict],
) -> tuple[dict[str, str], list[dict], list[str], list[str]]:
    """
    Match every CSV header to a canonical column name using a 4-tier strategy:

      Tier 1  raw_name         exact match          (highest priority)
      Tier 2  raw_name         case-insensitive
      Tier 3  candidate_names  exact match, in order
      Tier 4  candidate_names  case-insensitive, in order

    Each CSV column is "consumed" by the first canonical field that claims it —
    it cannot be matched again.  The function never mutates its inputs.

    Returns
    -------
    col_map          : {csv_header → canonical_name} for every matched pair.
    match_log        : One dict per canonical field describing the outcome.
    unmapped_csv     : CSV headers that no canonical field claimed.
    missing_required : canonical_names of required fields with no CSV match.
    """
    headers_set     = set(csv_headers)
    headers_lower   = {h.lower(): h for h in csv_headers}  # lower → original
    consumed        = set()                                 # csv headers taken

    col_map:   dict[str, str] = {}    # csv_header  → canonical_name
    match_log: list[dict]     = []

    for spec in col_specs:
        canon      = spec["canonical_name"]
        raw_name   = spec["raw_name"]
        candidates = spec.get("candidate_names") or []
        required   = spec.get("required", False)

        # Build the ordered probe list: (name, tier_label)
        probes: list[tuple[str, str]] = (
            [(raw_name, "raw_name")]
            + [(c, "candidate") for c in candidates]
        )

        matched_csv: str | None = None
        match_via:   str | None = None

        for probe, tier in probes:
            if matched_csv:
                break
            # ── Tier 1 / 3: exact ───────────────────────────────────────────
            if probe in headers_set and probe not in consumed:
                matched_csv = probe
                match_via   = f"{tier}:exact:{probe!r}"
                break
            # ── Tier 2 / 4: case-insensitive ────────────────────────────────
            lower_probe = probe.lower()
            if lower_probe in headers_lower:
                original = headers_lower[lower_probe]
                if original not in consumed:
                    matched_csv = original
                    match_via   = f"{tier}:icase:{probe!r}"
                    break

        if matched_csv:
            consumed.add(matched_csv)
            col_map[matched_csv] = canon
            match_log.append({
                "canonical": canon,
                "csv_col":   matched_csv,
                "via":       match_via,
                "required":  required,
                "status":    "matched",
            })
        else:
            match_log.append({
                "canonical": canon,
                "csv_col":   None,
                "via":       None,
                "required":  required,
                "status":    "not_found",
            })

    unmapped_csv     = [h for h in csv_headers if h not in consumed]
    mapped_canonicals = set(col_map.values())
    missing_required = [
        spec["canonical_name"]
        for spec in col_specs
        if spec.get("required") and spec["canonical_name"] not in mapped_canonicals
    ]

    return col_map, match_log, unmapped_csv, missing_required


def _print_column_resolution(
    match_log: list[dict],
    unmapped_csv: list[str],
    missing_required: list[str],
    csv_filename: str,
) -> None:
    """
    Print a human-readable column-resolution table to the log.

    ✔  matched       — green SUCCESS
    ~  optional miss — yellow WARNING
    ✘  required miss — red ERROR
    """
    logger.info("─" * 60)
    logger.info("Column resolution  |  {}", csv_filename)
    logger.info("─" * 60)

    for entry in match_log:
        canon    = entry["canonical"]
        csv_col  = entry["csv_col"]
        via      = entry["via"] or ""
        required = entry["required"]

        if entry["status"] == "matched":
            if csv_col == canon:
                via_label = "(exact primary name)"
            else:
                # shorten "raw_name:exact:'cost_price'" → "alias 'cost_price'"
                parts = via.split(":", 2)
                kind  = parts[0]          # raw_name | candidate
                how   = parts[1]          # exact | icase
                alias = parts[2] if len(parts) > 2 else csv_col
                via_label = f"via {kind} {how}: {alias}"
            logger.success("  ✔  {:<22}← {!r:<28} {}", canon, csv_col, via_label)
        elif required:
            logger.error(  "  ✘  {:<22}← MISSING (required field — rows will be rejected)", canon)
        else:
            logger.warning("  ~  {:<22}← not found (optional — will be null)", canon)

    if unmapped_csv:
        logger.warning("─" * 60)
        logger.warning(
            "Unmapped CSV columns ({}) — present in file but not in schema:",
            len(unmapped_csv),
        )
        for col in unmapped_csv:
            logger.warning("  ?  {!r}", col)
        logger.warning(
            "  → Add these to configs/pos_schema_mapping.yaml if they contain useful data."
        )

    if missing_required:
        logger.error("─" * 60)
        logger.error(
            "Missing REQUIRED fields ({}) — every row will fail validation:",
            len(missing_required),
        )
        for f in missing_required:
            logger.error("  ✘  {}", f)
        logger.error(
            "  → Add a matching raw_name or candidate_name to configs/pos_schema_mapping.yaml."
        )

    logger.info("─" * 60)


def apply_schema_mapping(
    raw_rows: list[dict[str, str]],
    config: dict,
) -> tuple[list[dict[str, Any]], dict]:
    """
    Resolve CSV columns → canonical names, apply normalizers, and cast types.

    Resolution uses a 4-tier strategy (see _resolve_column_map).
    Prints a full column-resolution table before processing any rows.

    Parameters
    ----------
    raw_rows : Output of load_csv().
    config   : Parsed YAML config dict.

    Returns
    -------
    canonical_rows   : List of canonical-column dicts with Python-typed values.
    resolution_report: Dict with match_log, unmapped_csv, missing_required.
    """
    col_specs = config["columns"]

    # ── 1. resolve columns once against the first row's headers ───────────────
    # Strip whitespace from all headers — Excel/POS exports often add trailing spaces
    raw_rows     = [{k.strip(): v for k, v in row.items() if k is not None} for row in raw_rows]
    csv_headers  = list(raw_rows[0].keys()) if raw_rows else []
    csv_filename = config.get("source_name", "unknown")

    col_map, match_log, unmapped_csv, missing_required = _resolve_column_map(
        csv_headers, col_specs
    )

    # ── 2. print resolution table ─────────────────────────────────────────────
    _print_column_resolution(match_log, unmapped_csv, missing_required, csv_filename)

    # ── 3. build reverse lookup: canonical_name → spec ────────────────────────
    canon_to_spec: dict[str, dict] = {s["canonical_name"]: s for s in col_specs}

    # ── 4. apply mapping row-by-row ───────────────────────────────────────────
    canonical_rows: list[dict[str, Any]] = []

    for raw_row in raw_rows:
        canonical: dict[str, Any] = {}

        for csv_col, canon_name in col_map.items():
            raw_value = raw_row.get(csv_col, "")
            spec      = canon_to_spec[canon_name]
            normalised = _apply_normalizers(raw_value, spec.get("normalizers", []))
            canonical[canon_name] = _cast(normalised, spec["dtype"])

        # Ensure every canonical column is present (None if unmapped)
        for spec in col_specs:
            canonical.setdefault(spec["canonical_name"], None)

        # Clamp negative stock to 0 — POS artifact in yomyom-inventory.csv
        if canonical.get("current_stock") is not None and canonical["current_stock"] < 0:
            canonical["current_stock"] = 0

        canonical_rows.append(canonical)

    logger.info(
        "Schema mapping: {} rows, {} canonical cols ({} unmapped CSV cols, {} missing fields)",
        len(canonical_rows),
        len(col_map),
        len(unmapped_csv),
        len([e for e in match_log if e["status"] == "not_found"]),
    )

    resolution_report = {
        "match_log":        match_log,
        "unmapped_csv":     unmapped_csv,
        "missing_required": missing_required,
        "col_map":          {k: v for k, v in col_map.items()},
    }
    return canonical_rows, resolution_report


# ─────────────────────────────────────────────────────────────────────────────
# 4. VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_rows(
    rows: list[dict[str, Any]],
    config: dict,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Validate canonical rows against the rules in config["validation"].

    Returns
    -------
    valid_rows   : Rows that passed all hard checks.
    invalid_rows : Rows rejected (with "validation_errors" key added).
    warnings     : List of {row_index, product_name, warning} dicts.
    """
    vcfg = config.get("validation", {})

    required_fields:    list[str]  = vcfg.get("required_fields", [])
    positive_fields:    list[str]  = vcfg.get("positive_fields", [])
    non_negative_fields: list[str] = vcfg.get("non_negative_fields", [])
    range_checks:       list[dict] = vcfg.get("range_checks", [])
    warn_rules:         list[dict] = vcfg.get("warnings", [])

    valid: list[dict]   = []
    invalid: list[dict] = []
    warnings: list[dict] = []

    for idx, row in enumerate(rows):
        errors: list[str] = []

        # ── hard checks ──────────────────────────────────────────────────────

        for field in required_fields:
            if row.get(field) is None:
                errors.append(f"required field '{field}' is null")

        for field in positive_fields:
            v = row.get(field)
            if v is not None and v <= 0:
                errors.append(f"'{field}' must be > 0 (got {v})")

        for field in non_negative_fields:
            v = row.get(field)
            if v is not None and v < 0:
                errors.append(f"'{field}' must be >= 0 (got {v})")

        for rchk in range_checks:
            field = rchk["field"]
            v = row.get(field)
            if v is not None:
                lo, hi = rchk.get("min"), rchk.get("max")
                if lo is not None and v < lo:
                    errors.append(f"'{field}' = {v} is below minimum {lo}")
                if hi is not None and v > hi:
                    errors.append(f"'{field}' = {v} exceeds maximum {hi}")

        if errors:
            invalid.append({**row, "validation_errors": errors})
            continue

        valid.append(row)

        # ── soft warnings (only for valid rows) ──────────────────────────────

        name = row.get("product_name", f"row_{idx}")

        for wrule in warn_rules:
            rule = wrule["rule"]
            msg  = wrule["message"]

            if rule == "units_sold_7d_le_30d":
                d7, d30 = row.get("units_sold_7d"), row.get("units_sold_30d")
                if d7 is not None and d30 is not None and d7 > d30:
                    warnings.append({"row": idx, "product": name, "warning": msg,
                                     "detail": f"7d={d7} > 30d={d30}"})

            elif rule == "cost_lt_sell":
                cost, sell = row.get("cost_price"), row.get("selling_price")
                if cost is not None and sell is not None and cost >= sell:
                    warnings.append({"row": idx, "product": name, "warning": msg,
                                     "detail": f"cost={cost} >= sell={sell}"})

            elif rule == "margin_consistency":
                tol  = wrule.get("tolerance_pct", 2.0)
                sell = row.get("selling_price")
                cost = row.get("cost_price")
                margin_csv = row.get("margin_pct")
                if None not in (sell, cost, margin_csv) and sell > 0:
                    computed = (sell - cost) / sell * 100
                    if abs(computed - margin_csv) > tol:
                        warnings.append({
                            "row": idx, "product": name, "warning": msg,
                            "detail": f"csv={margin_csv:.2f}% vs computed={computed:.2f}%",
                        })

    logger.info(
        "Validation: {} valid, {} rejected, {} warnings",
        len(valid), len(invalid), len(warnings),
    )
    return valid, invalid, warnings


# ─────────────────────────────────────────────────────────────────────────────
# 5. WRITE SILVER PARQUET FILES
# ─────────────────────────────────────────────────────────────────────────────

def _stamp(rows: list[dict], source_file: str, imported_at: str) -> list[dict]:
    """Add pipeline metadata columns to every row."""
    return [{**r, "_imported_at": imported_at, "_source_file": source_file} for r in rows]


def _write_parquet(rows: list[dict], columns: list[str], path: Path) -> None:
    """Project *rows* to *columns* and write as Parquet (overwrite if exists)."""
    # Include metadata columns automatically
    meta_cols = ["_imported_at", "_source_file"]
    full_cols = columns + [c for c in meta_cols if c in (rows[0] if rows else {})]

    projected = [{col: r.get(col) for col in full_cols} for r in rows]
    table = pa.Table.from_pylist(projected)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, str(path), compression="snappy")
    logger.info("Parquet: {} rows → {}", len(rows), path)


def write_silver_tables(
    valid_rows: list[dict],
    config: dict,
    source_file: str,
    imported_at: str,
) -> dict[str, Path]:
    """
    Write the four silver Parquet files defined in config["silver_tables"].

    Parameters
    ----------
    valid_rows  : Validated canonical rows.
    config      : Parsed YAML config.
    source_file : Original CSV filename (recorded as metadata).
    imported_at : ISO-8601 timestamp of this import run.

    Returns
    -------
    dict mapping table name → absolute Path.
    """
    stamped = _stamp(valid_rows, source_file, imported_at)
    paths: dict[str, Path] = {}

    for table_name, tdef in config["silver_tables"].items():
        filename = tdef["filename"]
        columns  = tdef["columns"]
        out_path = SILVER_POS_DIR / filename
        _write_parquet(stamped, columns, out_path)
        paths[table_name] = out_path

    return paths


# ─────────────────────────────────────────────────────────────────────────────
# 6. POS QUALITY REPORT
# ─────────────────────────────────────────────────────────────────────────────

def generate_pos_quality_report(
    valid_rows: list[dict],
    invalid_rows: list[dict],
    warnings: list[dict],
    source_file: str,
    imported_at: str,
) -> Path:
    """
    Write a POS-specific quality report with enriched metrics.

    Saved to: reports/quality/yomyom_pos/yomyom_pos_<YYYYMMDDTHHMMSS>_quality.json
    """
    total   = len(valid_rows) + len(invalid_rows)
    n_valid = len(valid_rows)

    def _pct(n: int) -> float:
        return round(n / total * 100, 2) if total else 0.0

    def _missing_pct(field: str) -> float:
        m = sum(1 for r in valid_rows if r.get(field) is None)
        return round(m / n_valid * 100, 2) if n_valid else 0.0

    # duplicate product names
    from collections import Counter
    name_counts = Counter(r["product_name"] for r in valid_rows)
    dup_names   = {n: c for n, c in name_counts.items() if c > 1}

    # price stats
    prices  = [r["selling_price"] for r in valid_rows if r.get("selling_price")]
    margins = [r["margin_pct"]    for r in valid_rows if r.get("margin_pct") is not None]

    def _safe(lst, fn):
        return round(fn(lst), 2) if lst else None

    # category breakdown
    cat_counts: dict[str, int] = {}
    for r in valid_rows:
        cat = r.get("category") or "unknown"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    ts  = datetime.fromisoformat(imported_at.replace("Z", "+00:00"))
    stamp = ts.strftime("%Y%m%dT%H%M%S")
    out_path = QUALITY_DIR / f"yomyom_pos_{stamp}_quality.json"

    report = {
        "source":      "yomyom_pos",
        "source_file": source_file,
        "imported_at": imported_at,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "row_counts": {
            "total_raw":   total,
            "valid":       n_valid,
            "rejected":    len(invalid_rows),
            "rejection_pct": _pct(len(invalid_rows)),
            "warnings":    len(warnings),
        },
        "completeness": {
            "missing_barcode_pct":    _missing_pct("barcode"),
            "missing_supplier_pct":   _missing_pct("supplier"),
            "missing_cost_pct":       _missing_pct("cost_price"),
            "missing_stock_pct":      _missing_pct("current_stock"),
            "missing_sales_30d_pct":  _missing_pct("units_sold_30d"),
            "missing_margin_pct":     _missing_pct("margin_pct"),
        },
        "duplicates": {
            "duplicate_product_names": len(dup_names),
            "names_with_duplicates":   dup_names,
        },
        "price_stats": {
            "min_selling_price": _safe(prices, min),
            "max_selling_price": _safe(prices, max),
            "avg_selling_price": _safe(prices, lambda x: sum(x) / len(x)),
        },
        "margin_stats": {
            "min_margin_pct": _safe(margins, min),
            "max_margin_pct": _safe(margins, max),
            "avg_margin_pct": _safe(margins, lambda x: sum(x) / len(x)),
        },
        "category_distribution": dict(sorted(cat_counts.items(), key=lambda x: -x[1])),
        "rejected_rows":  [
            {"product_name": r.get("product_name"), "errors": r.get("validation_errors")}
            for r in invalid_rows
        ],
        "warnings_sample": warnings[:20],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Quality report → {}", out_path)
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# 7. SIGNALS
# ─────────────────────────────────────────────────────────────────────────────

def _pick(row: dict, fields: list[str]) -> dict:
    """Return a sub-dict of *row* containing only *fields* that are not None."""
    return {f: row[f] for f in fields if row.get(f) is not None}


SIGNAL_FIELDS = {
    "top_sellers":              ["barcode", "product_name", "category", "units_sold_30d", "sales_amount_30d"],
    "top_profit_products":      ["barcode", "product_name", "category", "gross_profit_30d", "margin_pct"],
    "low_stock_fast_movers":    ["barcode", "product_name", "category", "current_stock", "units_sold_30d", "last_purchase_date"],
    "slow_movers":              ["barcode", "product_name", "category", "current_stock", "units_sold_30d", "last_sale_date"],
    "high_margin_impulse_candidates": ["barcode", "product_name", "category", "margin_pct", "selling_price", "units_sold_30d"],
    "category_sales_summary":   ["category"],          # aggregated below
}


def generate_signals(
    valid_rows: list[dict],
    config: dict,
    imported_at: str,
) -> Path:
    """
    Compute 6 business signals from valid POS rows and write a JSON file.

    Signal definitions (all driven by config["signals"])
    ──────────────────────────────────────────────────────
    top_sellers              : top N by units_sold_30d.
    top_profit_products      : top N by gross_profit_30d.
    low_stock_fast_movers    : current_stock ≤ threshold AND units_sold_30d ≥ threshold.
    slow_movers              : units_sold_30d ≤ slow threshold.
    high_margin_impulse_candidates : margin_pct ≥ threshold AND category in list.
    category_sales_summary   : SUM of units, revenue, profit per category.

    Saved to: data/signals/yomyom/pos_signals_<YYYYMMDDTHHMMSS>.json
    Also overwrites: data/signals/yomyom/pos_signals_latest.json
    """
    scfg  = config.get("signals", {})
    top_n = scfg.get("top_n", 10)

    lsfm_cfg  = scfg.get("low_stock_fast_movers", {})
    slow_cfg  = scfg.get("slow_movers", {})
    hm_cfg    = scfg.get("high_margin_impulse", {})

    lsfm_stock  = lsfm_cfg.get("max_stock", 15)
    lsfm_sold   = lsfm_cfg.get("min_sold_30d", 30)
    slow_max    = slow_cfg.get("max_sold_30d", 10)
    hm_min_marg = hm_cfg.get("min_margin_pct", 35.0)
    hm_cats     = set(hm_cfg.get("categories", []))

    # helpers
    def _sort_desc(rows, key):
        return sorted((r for r in rows if r.get(key) is not None), key=lambda r: r[key], reverse=True)

    # ── 1. top sellers ────────────────────────────────────────────────────────
    top_sellers = [
        _pick(r, SIGNAL_FIELDS["top_sellers"])
        for r in _sort_desc(valid_rows, "units_sold_30d")[:top_n]
    ]

    # ── 2. top profit ─────────────────────────────────────────────────────────
    top_profit = [
        _pick(r, SIGNAL_FIELDS["top_profit_products"])
        for r in _sort_desc(valid_rows, "gross_profit_30d")[:top_n]
    ]

    # ── 3. low-stock fast movers ──────────────────────────────────────────────
    lsfm = [
        _pick(r, SIGNAL_FIELDS["low_stock_fast_movers"])
        for r in valid_rows
        if (
            r.get("current_stock") is not None and r["current_stock"] <= lsfm_stock
            and r.get("units_sold_30d") is not None and r["units_sold_30d"] >= lsfm_sold
        )
    ]
    lsfm.sort(key=lambda r: r.get("units_sold_30d", 0), reverse=True)

    # ── 4. slow movers ────────────────────────────────────────────────────────
    slow = [
        _pick(r, SIGNAL_FIELDS["slow_movers"])
        for r in valid_rows
        if r.get("units_sold_30d") is not None and r["units_sold_30d"] <= slow_max
    ]
    slow.sort(key=lambda r: r.get("units_sold_30d", 0))

    # ── 5. high-margin impulse candidates ─────────────────────────────────────
    hm = [
        _pick(r, SIGNAL_FIELDS["high_margin_impulse_candidates"])
        for r in valid_rows
        if (
            r.get("margin_pct") is not None and r["margin_pct"] >= hm_min_marg
            and r.get("category") in hm_cats
        )
    ]
    hm.sort(key=lambda r: r.get("margin_pct", 0), reverse=True)

    # ── 6. category sales summary ─────────────────────────────────────────────
    cat_agg: dict[str, dict] = {}
    for r in valid_rows:
        cat = r.get("category") or "unknown"
        if cat not in cat_agg:
            cat_agg[cat] = {
                "category":        cat,
                "product_count":   0,
                "total_units_30d": 0,
                "total_revenue":   0.0,
                "total_profit":    0.0,
                "avg_margin_pct":  [],
            }
        agg = cat_agg[cat]
        agg["product_count"]   += 1
        agg["total_units_30d"] += r.get("units_sold_30d") or 0
        agg["total_revenue"]   += r.get("sales_amount_30d") or 0.0
        agg["total_profit"]    += r.get("gross_profit_30d") or 0.0
        if r.get("margin_pct") is not None:
            agg["avg_margin_pct"].append(r["margin_pct"])

    cat_summary = []
    for agg in sorted(cat_agg.values(), key=lambda x: -x["total_revenue"]):
        mlist = agg.pop("avg_margin_pct")
        agg["avg_margin_pct"]   = round(sum(mlist) / len(mlist), 2) if mlist else None
        agg["total_revenue"]    = round(agg["total_revenue"], 2)
        agg["total_profit"]     = round(agg["total_profit"], 2)
        cat_summary.append(agg)

    # ── assemble & write ──────────────────────────────────────────────────────
    ts    = datetime.fromisoformat(imported_at.replace("Z", "+00:00"))
    stamp = ts.strftime("%Y%m%dT%H%M%S")

    payload = {
        "source":      "yomyom_pos",
        "imported_at": imported_at,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "top_n":                top_n,
            "low_stock_max_stock":  lsfm_stock,
            "low_stock_min_sold30d": lsfm_sold,
            "slow_mover_max_sold30d": slow_max,
            "high_margin_min_pct":  hm_min_marg,
            "high_margin_categories": sorted(hm_cats),
        },
        "signals": {
            "top_sellers":                   top_sellers,
            "top_profit_products":           top_profit,
            "low_stock_fast_movers":         lsfm,
            "slow_movers":                   slow,
            "high_margin_impulse_candidates": hm,
            "category_sales_summary":        cat_summary,
        },
    }

    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

    # timestamped copy
    ts_path = SIGNALS_DIR / f"pos_signals_{stamp}.json"
    ts_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # latest copy (always overwritten)
    latest_path = SIGNALS_DIR / "pos_signals_latest.json"
    latest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(
        "Signals written ({} low-stock, {} slow, {} high-margin) → {}",
        len(lsfm), len(slow), len(hm), ts_path,
    )
    return ts_path


# ─────────────────────────────────────────────────────────────────────────────
# 8. MAIN ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

def run_import(
    input_path: Path,
    config_path: Path = CONFIG_PATH,
    imported_at: Optional[str] = None,
) -> dict:
    """
    Run the full YomYom POS import pipeline.

    Parameters
    ----------
    input_path  : Path to the raw CSV file.
    config_path : Path to the YAML schema-mapping config.
    imported_at : ISO-8601 timestamp; defaults to now (UTC).

    Returns
    -------
    Summary dict with paths to all written files.
    """
    if imported_at is None:
        imported_at = datetime.now(timezone.utc).isoformat()

    logger.info("═" * 60)
    logger.info("YomYom POS Import  |  {}", input_path.name)
    logger.info("═" * 60)

    # load config
    cfg = load_config(config_path)

    # stage 1: load CSV
    raw_rows = load_csv(input_path, encoding=cfg.get("encoding", "utf-8-sig"))

    # stage 2: schema mapping + column resolution
    canonical_rows, resolution = apply_schema_mapping(raw_rows, cfg)

    # early-exit if required fields are completely absent
    if resolution["missing_required"]:
        logger.error(
            "Required field(s) {} not found in CSV — aborting.",
            resolution["missing_required"],
        )
        return {
            "status":           "error",
            "reason":           "missing_required_columns",
            "missing_required": resolution["missing_required"],
            "unmapped_csv":     resolution["unmapped_csv"],
        }

    # stage 3: validate
    valid_rows, invalid_rows, warnings = validate_rows(canonical_rows, cfg)

    if not valid_rows:
        logger.error("No valid rows after validation — aborting write stage.")
        return {"status": "error", "reason": "no_valid_rows"}

    # stage 4: write silver Parquet files
    parquet_paths = write_silver_tables(
        valid_rows, cfg,
        source_file=input_path.name,
        imported_at=imported_at,
    )

    # stage 5: quality report
    quality_path = generate_pos_quality_report(
        valid_rows, invalid_rows, warnings,
        source_file=input_path.name,
        imported_at=imported_at,
    )

    # stage 6: signals
    signals_path = generate_signals(valid_rows, cfg, imported_at)

    # ── print summary ─────────────────────────────────────────────────────────
    logger.success("═" * 60)
    logger.success("Import complete")
    logger.success("  Valid rows      : {}", len(valid_rows))
    logger.success("  Rejected rows   : {}", len(invalid_rows))
    logger.success("  Warnings        : {}", len(warnings))
    logger.success("  Unmapped cols   : {}", len(resolution["unmapped_csv"]))
    logger.success("  Parquet files   :")
    for name, p in parquet_paths.items():
        logger.success("    [{}]  {}", name, p)
    logger.success("  Quality report  : {}", quality_path)
    logger.success("  Signals         : {}", signals_path)
    logger.success("═" * 60)

    return {
        "status":           "ok",
        "imported_at":      imported_at,
        "valid_rows":       len(valid_rows),
        "invalid_rows":     len(invalid_rows),
        "warnings":         len(warnings),
        "parquet_paths":    {k: str(v) for k, v in parquet_paths.items()},
        "quality_path":     str(quality_path),
        "signals_path":     str(signals_path),
        # column resolution metadata — useful for callers / tests
        "unmapped_csv":     resolution["unmapped_csv"],
        "missing_optional": [
            e["canonical"] for e in resolution["match_log"]
            if e["status"] == "not_found" and not e["required"]
        ],
        "col_map":          resolution["col_map"],
    }
