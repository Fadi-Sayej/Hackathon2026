from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from src.internal_pos.pos_normalizer import inspect_pos_file, load_schema_config, load_raw_rows, normalize_rows
from src.internal_pos.pos_quality import build_quality_report, classify_source_file, write_quality_report


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "pos_schema_mapping.yaml"
SILVER_POS_DIR = PROJECT_ROOT / "data" / "internal" / "silver_pos"
QUALITY_REPORT_DIR = PROJECT_ROOT / "reports" / "quality"


def _records_to_table(records: list[dict[str, Any]]) -> pa.Table:
    if not records:
        return pa.table({"_empty": pa.array([], type=pa.bool_())})
    return pa.Table.from_pylist(records)


def _write_fixed_parquet(records: list[dict[str, Any]], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(_records_to_table(records), path, compression="snappy")
    return path


def _build_table_rows(
    normalized_rows: list[dict[str, Any]],
    columns: list[str],
    imported_at: str,
    source_file: str,
    source_kind: str,
    as_of: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in normalized_rows:
        subset = {column: row.get(column) for column in columns}
        subset["_imported_at"] = imported_at
        subset["_source_file"] = source_file
        subset["_source_kind"] = source_kind
        subset["_as_of"] = as_of
        rows.append(subset)
    return rows


def import_pos_file(
    input_path: Path,
    config_path: Path = CONFIG_PATH,
    imported_at: str | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    imported_at = imported_at or datetime.now(timezone.utc).isoformat()
    # The POS vintage is the day the export was taken, not the day we imported it
    # (SPEC-007 FR-120). Default: the file's modification date.
    as_of = as_of or date.fromtimestamp(input_path.stat().st_mtime).isoformat()
    config = load_schema_config(config_path)
    inspection = inspect_pos_file(input_path, config_path)
    source_kind = classify_source_file(input_path)

    if inspection["missing_required_fields"]:
        report = build_quality_report(
            input_path=input_path,
            inspection=inspection,
            normalized_rows=[],
            rejected_rows=[],
            warnings=inspection["warnings"],
            output_paths={},
            status="not_ready",
        )
        quality_path = write_quality_report(report, QUALITY_REPORT_DIR)
        return {
            "status": "not_ready",
            "reason": "missing_required_fields",
            "quality_report_path": str(quality_path),
            "inspection": inspection,
        }

    raw_rows = load_raw_rows(
        input_path,
        inspection["encoding_guess"],
        inspection["delimiter_guess"],
    )
    mapping = {
        "mapped_headers": {
            entry["canonical_name"]: entry["raw_header"]
            for entry in inspection["guessed_mapping"]
            if entry["status"] == "mapped"
        }
    }
    normalized_rows, rejected_rows, warnings = normalize_rows(raw_rows, config, mapping)

    silver_tables = config.get("silver_tables", {})
    output_paths: dict[str, str] = {}
    for table_name, table_spec in silver_tables.items():
        rows = _build_table_rows(
            normalized_rows,
            table_spec.get("columns", []),
            imported_at,
            input_path.name,
            source_kind,
            as_of,
        )
        path = _write_fixed_parquet(rows, SILVER_POS_DIR / table_spec["filename"])
        output_paths[table_name] = str(path)

    report = build_quality_report(
        input_path=input_path,
        inspection=inspection,
        normalized_rows=normalized_rows,
        rejected_rows=rejected_rows,
        warnings=inspection["warnings"] + warnings,
        output_paths=output_paths,
        status="ok",
    )
    quality_path = write_quality_report(report, QUALITY_REPORT_DIR)

    # public/data/sources.json is retired (ADR-005, design §20.2 "stops immediately").
    # The update_source("yomyom_pos", …) call that used to sit here is gone with it.

    try:
        from src.snapshots.pos_snapshots import archive_current_silver

        archive_current_silver(imported_at)
    except Exception:  # snapshotting must never break the import
        pass

    return {
        "status": "ok",
        "imported_at": imported_at,
        "source_kind": source_kind,
        "accepted_rows": len(normalized_rows),
        "rejected_rows": len(rejected_rows),
        "outputs": output_paths,
        "quality_report_path": str(quality_path),
        "inspection": inspection,
    }



def read_pos_vintage(silver_dir: Path = SILVER_POS_DIR) -> dict[str, Any] | None:
    path = silver_dir / "yomyom_inventory.parquet"
    if not path.exists():
        return None
    rows = pq.read_table(path, columns=["_source_file", "_as_of"]).slice(0, 1).to_pylist()
    if not rows:
        return None
    return {"file": rows[0].get("_source_file"), "as_of": rows[0].get("_as_of")}
