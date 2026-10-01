from __future__ import annotations

import json
import re
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from src.internal_pos.pos_normalizer import inspect_pos_file, load_schema_config, load_raw_rows, normalize_rows
from src.internal_pos.pos_quality import build_quality_report, classify_source_file, write_quality_report
from src.common.store import INVENTORY_TABLE


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "pos_schema_mapping.yaml"
SILVER_POS_DIR = PROJECT_ROOT / "data" / "internal" / "silver_pos"
SNAPSHOTS_DIR = PROJECT_ROOT / "data" / "internal" / "snapshots"
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
    as_of_source: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in normalized_rows:
        subset = {column: row.get(column) for column in columns}
        subset["_imported_at"] = imported_at
        subset["_source_file"] = source_file
        subset["_source_kind"] = source_kind
        subset["_as_of"] = as_of
        # How the vintage was arrived at, beside the vintage itself. Without it a
        # checkout timestamp is indistinguishable from a declared export date.
        subset["_as_of_source"] = as_of_source
        rows.append(subset)
    return rows


_ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                             timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _is_shallow(path: Path) -> bool:
    """True when this checkout does not hold enough history to answer a `git log`.

    `actions/checkout@v4` defaults to `fetch-depth: 1`. A repository with one commit
    cannot say when a file last changed — there is no parent to diff against — so
    `git log -1 -- <file>` attributes it to the checkout commit and returns THAT date.
    Unknown, not false: a shallow repository must decline rather than answer.
    """
    return _git(["rev-parse", "--is-shallow-repository"], path.parent) == "true"


def _git_log_date(path: Path) -> str | None:
    day = _git(["log", "-1", "--format=%ad", "--date=short", "--", path.name], path.parent)
    return day if day and _ISO_DAY.match(day) else None


def _git_committed_date(path: Path) -> str | None:
    """The day this file last changed in git, or None when git cannot know.

    Machine-independent, unlike an mtime — but only in a repository deep enough to
    answer. Shipped 2026-09-13 without the shallow check and was wrong within a day:

        09-14 nightly  checked out 7d8f65a (dated 09-14)  published as_of 2026-09-14
        09-15 nightly  checked out 4645cd5 (dated 09-14)  published as_of 2026-09-14

    while `yomyom-inventory.csv` had not changed since 2026-06-06. That is the same
    defect the git route replaced — a date tracking the checkout rather than the data —
    wearing a `git_commit` label that reads as verified. Worse than the mtime it
    replaced, because mtime at least announced itself as a filesystem timestamp.
    """
    if _is_shallow(path):
        return None
    return _git_log_date(path)


def _declared_sidecar(path: Path) -> str | None:
    """`<export>.vintage.json` beside the export: `{"as_of": "YYYY-MM-DD"}`.

    The only source that is actually the export date is one a human wrote down, and
    unlike git it survives a shallow clone, a fresh checkout and a customer emailing a
    zip — none of which carry our history. Whoever replaces the export knows when it was
    taken; this is where that goes.

    A malformed or dateless sidecar declines rather than raises. A broken note about the
    data must not stop the data being imported.
    """
    sidecar = path.with_suffix(path.suffix + ".vintage.json")
    if not sidecar.exists():
        sidecar = path.with_suffix(".vintage.json")
    if not sidecar.exists():
        return None
    try:
        day = (json.loads(sidecar.read_text(encoding="utf-8")) or {}).get("as_of")
    except (OSError, ValueError):
        return None
    return day if isinstance(day, str) and _ISO_DAY.match(day) else None


def resolve_as_of(input_path: Path, declared: str | None = None) -> tuple[str, str]:
    """The day this export was taken, and how we know — `(as_of, as_of_source)`.

    SPEC-007 FR-120: the POS vintage is the day the export was TAKEN, not the day we
    imported it. The default was `date.fromtimestamp(path.stat().st_mtime)`, which does
    not honour that anywhere it matters. `git clone` stamps every file's mtime with the
    checkout time, so on a CI runner this resolved to **today, every day, for ever**: the
    published artefact said `pos.as_of: 2026-09-13` while `yomyom-inventory.csv` had not
    changed in git since 2026-06-06. The same import on a laptop said 2026-08-02, because
    that was that machine's mtime. One commit, two machines, two vintages — and the one
    the owner saw claimed his stock counts were from this morning.

    The file itself carries no date: the export's columns are item code, barcode,
    description, type, stock, prices and department. So there is nothing to read out of
    the data, and the answer has to be sourced honestly instead of guessed:

      declared         a human passed --as-of. Always wins.
      declared_sidecar `<export>.vintage.json` beside the file. Also written down by a
                       human, and it survives a shallow clone and a customer's zip.
      git_commit       the file's last change in git — only in a repository deep enough
                       to answer. See _git_committed_date for what a shallow one does.
      file_mtime       last resort. Still published, but labelled, so nobody reads a
                       checkout timestamp as a vintage.

    The first two are the only ones that are certainly the export date. The other two are
    proxies, and both have now been wrong in production for the same underlying reason —
    they measure the checkout rather than the data — which is why the ladder starts with
    something a person wrote down.
    """
    if declared:
        return declared, "declared"
    sidecar = _declared_sidecar(input_path)
    if sidecar:
        return sidecar, "declared_sidecar"
    committed = _git_committed_date(input_path)
    if committed:
        return committed, "git_commit"
    return date.fromtimestamp(input_path.stat().st_mtime).isoformat(), "file_mtime"


def import_pos_file(
    input_path: Path,
    config_path: Path = CONFIG_PATH,
    imported_at: str | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    imported_at = imported_at or datetime.now(timezone.utc).isoformat()
    as_of, as_of_source = resolve_as_of(input_path, declared=as_of)
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
            as_of_source,
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

        # What this import wrote, into the snapshots this module was given: a caller that
        # redirects SILVER_POS_DIR must not have the real silver archived under its name.
        archive_current_silver(imported_at, silver_dir=SILVER_POS_DIR, snapshots_root=SNAPSHOTS_DIR)
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
    path = silver_dir / INVENTORY_TABLE
    if not path.exists():
        return None
    columns = set(pq.read_schema(path).names)
    wanted = [c for c in ("_source_file", "_as_of", "_as_of_source") if c in columns]
    rows = pq.read_table(path, columns=wanted).slice(0, 1).to_pylist()
    if not rows:
        return None
    return {"file": rows[0].get("_source_file"), "as_of": rows[0].get("_as_of"),
            # Absent in tables written before this column existed; `None` reads as
            # "we do not know how this vintage was arrived at", which is the truth.
            "as_of_source": rows[0].get("_as_of_source")}
