from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def classify_source_file(path: Path) -> str:
    lowered = path.name.lower()
    if any(token in lowered for token in ("sample", "fake", "demo", "test")):
        return "sample"
    return "real_candidate"


def build_quality_report(
    *,
    input_path: Path,
    inspection: dict[str, Any],
    normalized_rows: list[dict[str, Any]],
    rejected_rows: list[dict[str, Any]],
    warnings: list[str],
    output_paths: dict[str, str],
    status: str,
) -> dict[str, Any]:
    row_count = inspection["row_count"]
    normalized_count = len(normalized_rows)
    rejected_count = len(rejected_rows)
    accepted_pct = round((normalized_count / row_count), 4) if row_count else 0.0

    def pct_missing(field: str) -> float:
        if not normalized_rows:
            return 0.0
        missing = sum(1 for row in normalized_rows if row.get(field) in (None, ""))
        return round(missing / len(normalized_rows), 4)

    return {
        "pipeline": "yomyom_pos_import",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source_file": str(input_path),
        "source_kind": classify_source_file(input_path),
        "inspection": {
            "encoding_guess": inspection["encoding_guess"],
            "delimiter_guess": inspection["delimiter_guess"],
            "column_names": inspection["column_names"],
            "missing_required_fields": inspection["missing_required_fields"],
            "missing_important_fields": inspection["missing_important_fields"],
            "unmapped_columns": inspection["unmapped_columns"],
        },
        "metrics": {
            "row_count": row_count,
            "accepted_row_count": normalized_count,
            "rejected_row_count": rejected_count,
            "accepted_row_pct": accepted_pct,
            "missing_barcode_pct": pct_missing("barcode"),
            "missing_category_pct": pct_missing("category"),
            "missing_cost_price_pct": pct_missing("cost_price"),
            "missing_current_stock_pct": pct_missing("current_stock"),
            "missing_units_sold_30d_pct": pct_missing("units_sold_30d"),
        },
        "warnings": warnings[:200],
        "rejected_rows_preview": rejected_rows[:20],
        "outputs": output_paths,
    }


def write_quality_report(report: dict[str, Any], report_root: Path) -> Path:
    report_root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = report_root / f"yomyom_pos_quality_{ts}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

