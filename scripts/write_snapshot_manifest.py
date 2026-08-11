"""
write_snapshot_manifest.py — seal one day's market snapshot (T1 / #46, Step 3).

    python3 scripts/write_snapshot_manifest.py --date 2026-08-11

Writes `data/external/snapshots/<date>/_manifest.json` describing what was
collected, what failed, and what was expected but missing.

WHY THIS FILE MATTERS MORE THAN IT LOOKS
----------------------------------------
Six weeks from now, an item that is absent from a day's snapshot has two
completely different explanations:

    a) the market genuinely stopped carrying it   → a real signal (#49 DELISTING)
    b) our scrape failed that day                 → no information whatsoever

Nothing in the collected files distinguishes these. Only the manifest does. Get
this wrong and the latent-state inference in #49 learns from noise and produces
confident nonsense — which is worse than producing nothing.

IMMUTABILITY
------------
A day that already completed successfully is never rewritten. Overwriting erases
history that cannot be re-collected: the price-transparency server keeps only the
current day (verified 2026-08-11, #46 Step 1). A partial day may be retried and
upgraded; a good day may not be replaced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import EXTERNAL_SNAPSHOTS_ROOT, get_snapshot_manifest_path

STATUS_OK = "ok"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"
STATUS_MISSING = "missing"

# Sources a complete day is expected to contain. A source absent from the folder
# is recorded as `missing` rather than silently omitted — an omission would read
# as "nothing to collect" later.
EXPECTED_SOURCES = ("price_transparency", "delivery_catalog")


def _sha256_of_dir(directory: Path) -> str:
    """Stable digest over a directory's file contents.

    Lets a later run tell "the same data re-collected" from "the data changed",
    without diffing gigabytes.
    """
    digest = hashlib.sha256()
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        digest.update(path.relative_to(directory).as_posix().encode())
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def describe_source(day_dir: Path, source_id: str) -> dict:
    source_dir = day_dir / source_id
    if not source_dir.exists():
        return {
            "status": STATUS_MISSING,
            "files": 0,
            "bytes": 0,
            "note": "collector did not run or produced nothing",
        }

    files = [p for p in source_dir.rglob("*") if p.is_file()]
    total_bytes = sum(p.stat().st_size for p in files)
    return {
        "status": STATUS_OK if files else STATUS_FAILED,
        "files": len(files),
        "bytes": total_bytes,
        "sha256": _sha256_of_dir(source_dir) if files else None,
    }


def build_manifest(day: str, collector_version: str, errors: dict | None = None) -> dict:
    day_dir = EXTERNAL_SNAPSHOTS_ROOT / day
    errors = errors or {}

    sources = {}
    for source_id in EXPECTED_SOURCES:
        entry = describe_source(day_dir, source_id)
        if source_id in errors:
            entry["errors"] = errors[source_id]
            if entry["status"] == STATUS_OK:
                entry["status"] = STATUS_PARTIAL
        sources[source_id] = entry

    statuses = {s["status"] for s in sources.values()}
    if statuses == {STATUS_OK}:
        overall = STATUS_OK
    elif statuses <= {STATUS_MISSING, STATUS_FAILED}:
        overall = STATUS_FAILED
    else:
        overall = STATUS_PARTIAL

    return {
        "date": day,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "collector_version": collector_version,
        "status": overall,
        "sources": sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD")
    parser.add_argument("--collector-version", default="smartshelf@1.0.0")
    parser.add_argument(
        "--errors",
        default=None,
        help='JSON map of source_id -> ["error", …], recorded as partial failures',
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="rewrite a manifest whose status is already ok (refuses by default)",
    )
    args = parser.parse_args()

    manifest_path = get_snapshot_manifest_path(args.date)

    if manifest_path.exists() and not args.force:
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            existing = {}
        if existing.get("status") == STATUS_OK:
            # A good day is immutable. Re-running the collector must be a no-op,
            # not a quiet overwrite of history we cannot re-fetch.
            print("%s already complete (status ok) — leaving it untouched." % manifest_path.name)
            print(json.dumps(existing, ensure_ascii=False, indent=2))
            return 0
        print("Existing manifest is %s; retrying is allowed." % existing.get("status", "unknown"))

    errors = json.loads(args.errors) if args.errors else {}
    manifest = build_manifest(args.date, args.collector_version, errors)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic: a half-written manifest is indistinguishable from a corrupt day.
    tmp = manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(manifest_path)

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    # A wholly failed day is worth a non-zero exit so the schedule alerts.
    return 1 if manifest["status"] == STATUS_FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
