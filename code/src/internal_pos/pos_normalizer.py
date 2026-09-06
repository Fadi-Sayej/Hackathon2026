from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any

import yaml


IMPORTANT_FIELDS = [
    "product_name",
    "selling_price",
    "barcode",
    "category",
    "cost_price",
    "current_stock",
    "units_sold_30d",
]

ENCODING_CANDIDATES = [
    "utf-8-sig",
    "utf-8",
    "utf-16",
    "utf-16-le",
    "utf-16-be",
    "cp1255",
    "cp1252",
    "latin-1",
]

DELIMITER_CANDIDATES = [",", ";", "\t", "|"]


def load_schema_config(config_path: Path) -> dict[str, Any]:
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def _read_sample_bytes(path: Path, size: int = 65536) -> bytes:
    return path.read_bytes()[:size]


def guess_encoding(path: Path) -> str:
    sample = _read_sample_bytes(path)
    best_encoding = "utf-8-sig"
    best_score = -1
    for encoding in ENCODING_CANDIDATES:
        try:
            text = sample.decode(encoding)
        except UnicodeDecodeError:
            continue
        score = 0
        if "\ufffd" not in text:
            score += 3
        if "\x00" not in text:
            score += 3
        # Prefer the real Hebrew decode over permissive single-byte fallbacks
        # such as latin-1, which can decode anything into mojibake.
        hebrew_chars = sum(1 for char in text if "\u0590" <= char <= "\u05ff")
        mojibake_markers = text.count("×") + text.count("ï»¿")
        score += min(hebrew_chars, 50)
        score -= min(mojibake_markers, 50)
        score += min(text.count("\n"), 10)
        score += min(sum(text.count(d) for d in DELIMITER_CANDIDATES), 10)
        if score > best_score:
            best_score = score
            best_encoding = encoding
    return best_encoding


def guess_delimiter(path: Path, encoding: str) -> str:
    sample = path.read_text(encoding=encoding, errors="ignore")[:65536]
    try:
        sniffed = csv.Sniffer().sniff(sample, delimiters="".join(DELIMITER_CANDIDATES))
        return sniffed.delimiter
    except csv.Error:
        counts = {d: sample.count(d) for d in DELIMITER_CANDIDATES}
        return max(counts, key=counts.get)


def load_raw_rows(path: Path, encoding: str, delimiter: str) -> list[dict[str, str]]:
    with path.open("r", encoding=encoding, errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        return [dict(row) for row in reader]


def _normalize_header(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).casefold()


def resolve_column_mapping(headers: list[str], config: dict[str, Any]) -> dict[str, Any]:
    header_lookup = {_normalize_header(header): header for header in headers}
    consumed: set[str] = set()
    matches: list[dict[str, Any]] = []
    mapped_headers: dict[str, str] = {}

    for spec in config.get("columns", []):
        canonical = spec["canonical_name"]
        candidates = [spec.get("raw_name", "")] + list(spec.get("candidate_names") or [])
        matched_header = None
        matched_via = None
        for candidate in candidates:
            key = _normalize_header(candidate)
            original = header_lookup.get(key)
            if original and original not in consumed:
                matched_header = original
                matched_via = candidate
                break
        if matched_header:
            consumed.add(matched_header)
            mapped_headers[canonical] = matched_header
            matches.append(
                {
                    "canonical_name": canonical,
                    "raw_header": matched_header,
                    "matched_via": matched_via,
                    "required": bool(spec.get("required")),
                    "status": "mapped",
                }
            )
        else:
            matches.append(
                {
                    "canonical_name": canonical,
                    "raw_header": None,
                    "matched_via": None,
                    "required": bool(spec.get("required")),
                    "status": "missing",
                }
            )

    missing_required = [
        spec["canonical_name"]
        for spec in config.get("columns", [])
        if spec.get("required") and spec["canonical_name"] not in mapped_headers
    ]
    missing_important = [field for field in IMPORTANT_FIELDS if field not in mapped_headers]
    unmapped_columns = [header for header in headers if header not in consumed]

    return {
        "mapped_headers": mapped_headers,
        "matches": matches,
        "missing_required_fields": missing_required,
        "missing_important_fields": missing_important,
        "unmapped_columns": unmapped_columns,
    }


def _apply_normalizers(value: str | None, normalizers: list[str]) -> str | None:
    current = value
    for normalizer in normalizers:
        if current is None:
            break
        if normalizer == "strip_whitespace":
            current = current.strip()
        elif normalizer == "null_if_empty":
            current = None if current == "" else current
        elif normalizer == "lowercase":
            current = current.lower()
        elif normalizer == "uppercase":
            current = current.upper()
    return current


def _cast_value(value: str | None, dtype: str) -> Any:
    if value is None:
        return None
    try:
        if dtype == "string":
            return value
        if dtype == "decimal":
            return float(Decimal(value.replace(",", ".")))
        if dtype == "integer":
            return int(float(value.replace(",", ".")))
        if dtype == "date":
            return date.fromisoformat(value).isoformat()
        if dtype == "boolean":
            return value.strip().lower() in {"1", "true", "yes", "y"}
    except (ValueError, InvalidOperation, AttributeError):
        return None
    return value


def normalize_rows(
    raw_rows: list[dict[str, str]],
    config: dict[str, Any],
    mapping: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    normalized_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    spec_by_canonical = {
        spec["canonical_name"]: spec
        for spec in config.get("columns", [])
    }
    required_fields = set(config.get("validation", {}).get("required_fields", []))
    positive_fields = set(config.get("validation", {}).get("positive_fields", []))
    non_negative_fields = set(config.get("validation", {}).get("non_negative_fields", []))
    range_rules = {rule["field"]: rule for rule in config.get("validation", {}).get("range_checks", [])}

    for row_number, raw_row in enumerate(raw_rows, start=2):
        normalized: dict[str, Any] = {}
        row_errors: list[str] = []
        row_warnings: list[str] = []

        for canonical, header in mapping["mapped_headers"].items():
            spec = spec_by_canonical[canonical]
            raw_value = raw_row.get(header)
            cooked = _apply_normalizers(raw_value, spec.get("normalizers") or [])
            normalized[canonical] = _cast_value(cooked, spec.get("dtype", "string"))

        for field in required_fields:
            if normalized.get(field) in (None, ""):
                row_errors.append(f"missing required field: {field}")

        for field in positive_fields:
            value = normalized.get(field)
            if value is not None and value <= 0:
                row_errors.append(f"{field} must be > 0")

        for field in non_negative_fields:
            value = normalized.get(field)
            if value is not None and value < 0:
                row_errors.append(f"{field} must be >= 0")

        for field, rule in range_rules.items():
            value = normalized.get(field)
            if value is None:
                continue
            min_value = rule.get("min")
            max_value = rule.get("max")
            if min_value is not None and value < min_value:
                row_errors.append(f"{field} below minimum {min_value}")
            if max_value is not None and value > max_value:
                row_errors.append(f"{field} above maximum {max_value}")

        sold_7d = normalized.get("units_sold_7d")
        sold_30d = normalized.get("units_sold_30d")
        if sold_7d is not None and sold_30d is not None and sold_7d > sold_30d:
            row_warnings.append("units_sold_7d should be <= units_sold_30d")

        sell = normalized.get("selling_price")
        cost = normalized.get("cost_price")
        if sell is not None and cost is not None and cost >= sell:
            row_warnings.append("cost_price should be < selling_price")

        margin = normalized.get("margin_pct")
        if sell is not None and cost is not None and sell > 0 and margin is not None:
            recomputed = round(((sell - cost) / sell) * 100, 2)
            if abs(recomputed - margin) > 2.0:
                row_warnings.append("margin_pct differs from recomputed margin by more than 2 points")

        normalized["_row_number"] = row_number

        if row_errors:
            rejected_rows.append(
                {
                    "row_number": row_number,
                    "errors": row_errors,
                    "raw_row": raw_row,
                }
            )
        else:
            normalized_rows.append(normalized)

        warnings.extend(f"row {row_number}: {message}" for message in row_warnings)

    return normalized_rows, rejected_rows, warnings


def inspect_pos_file(
    input_path: Path,
    config_path: Path,
    sample_size: int = 5,
) -> dict[str, Any]:
    config = load_schema_config(config_path)
    encoding = guess_encoding(input_path)
    delimiter = guess_delimiter(input_path, encoding)
    raw_rows = load_raw_rows(input_path, encoding, delimiter)
    headers = list(raw_rows[0].keys()) if raw_rows else []
    mapping = resolve_column_mapping(headers, config)
    sample_rows = raw_rows[:sample_size]

    warnings: list[str] = []
    if not raw_rows:
        warnings.append("File contains no data rows.")
    if mapping["missing_required_fields"]:
        warnings.append("Missing required fields prevent import until the schema mapping is updated.")
    if len(headers) <= 1:
        warnings.append("Only one column detected; delimiter guess may be wrong.")

    return {
        "input_path": str(input_path),
        "encoding_guess": encoding,
        "delimiter_guess": delimiter,
        "row_count": len(raw_rows),
        "column_names": headers,
        "sample_rows": sample_rows,
        "guessed_mapping": mapping["matches"],
        "missing_important_fields": mapping["missing_important_fields"],
        "missing_required_fields": mapping["missing_required_fields"],
        "unmapped_columns": mapping["unmapped_columns"],
        "warnings": warnings,
    }
