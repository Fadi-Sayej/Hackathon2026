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
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl
import yaml

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

# A run covering less than this share of the median branch count of previous days
# is recorded as `partial`, however cleanly it finished.
#
# On 11 Aug one run reached 31 of 156 branches and was recorded `ok`, because
# every check here asked whether files arrived, not whether they were complete.
# A short run that is trusted looks exactly like 125 branches dropping their
# entire assortment overnight. src/market/presence.py refuses such a day
# independently; this is the half that makes the collector say so out loud.
MIN_BRANCH_COVERAGE_RATIO = 0.5

# What one "unit of coverage" is called per source, matching the manifest shape
# specified in #46 Step 3: `stores` for the price file, `venues` for delivery.
# The concept is identical — how many distinct places did we actually reach.
UNIT_FIELD = {
    "price_transparency": "stores",
    "delivery_catalog": "venues",
}
DEFAULT_UNIT_FIELD = "stores"

DELIVERY_TARGETS_PATH = ROOT / "configs" / "delivery_targets.yaml"


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


def unit_field(source_id: str) -> str:
    return UNIT_FIELD.get(source_id, DEFAULT_UNIT_FIELD)


def expected_units(source_id: str) -> int | None:
    """How many places this source was SUPPOSED to reach, where that is declared.

    Only the delivery catalogue declares its targets. The price file publishes
    whatever branches the chain chooses to publish, so there is no honest fixed
    expectation — the median check below is what covers it.
    """
    if source_id != "delivery_catalog":
        return None
    if not DELIVERY_TARGETS_PATH.exists():
        return None
    try:
        config = yaml.safe_load(DELIVERY_TARGETS_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    targets = config.get("targets") or []
    return sum(
        1 for t in targets
        if isinstance(t, dict) and t.get("url") and t.get("enabled", True)
    ) or None


def count_rows(source_dir: Path) -> int | None:
    """Total rows across a source's silver files."""
    total = 0
    found = False
    for path in sorted(source_dir.rglob("*.parquet")):
        if "silver" not in path.name:
            continue
        try:
            total += pl.read_parquet(path).height
        except Exception:
            continue
        found = True
    return total if found else None


def count_branches(source_dir: Path) -> int | None:
    """Distinct store_ids across a source's silver files, or None if not applicable.

    Only silver carries a normalised `store_id`; the delivery catalogue is a
    single venue and has no branch count worth checking.
    """
    stores: set[str] = set()
    found = False
    for path in sorted(source_dir.rglob("*.parquet")):
        if "silver" not in path.name:
            continue
        try:
            frame = pl.read_parquet(path, columns=["store_id"])
        except Exception:
            continue
        found = True
        stores.update(str(v) for v in frame["store_id"].unique() if v is not None)
    return len(stores) if found else None


def median_branches_before(day: str, source_id: str) -> float | None:
    """Median branch count recorded for this source on earlier days.

    Read from the manifests rather than recomputed, so the comparison is against
    what was actually accepted, not against files that may since have changed.
    """
    counts = []
    for manifest_path in sorted(EXTERNAL_SNAPSHOTS_ROOT.glob("*/_manifest.json")):
        if manifest_path.parent.name >= day:
            continue
        try:
            entry = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        source = entry.get("sources", {}).get(source_id, {})
        # `branches` is the pre-spec name, kept readable so history written
        # before the rename still counts toward the median.
        branches = source.get(unit_field(source_id), source.get("branches"))
        if isinstance(branches, int) and branches > 0:
            counts.append(branches)
    return statistics.median(counts) if counts else None


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
    entry = {
        "status": STATUS_OK if files else STATUS_FAILED,
        "files": len(files),
        "bytes": total_bytes,
        "sha256": _sha256_of_dir(source_dir) if files else None,
    }

    if not files:
        return entry

    field = unit_field(source_id)
    rows = count_rows(source_dir)
    if rows is not None:
        entry["rows"] = rows

    branches = count_branches(source_dir)
    if branches is None:
        return entry

    entry[field] = branches

    expected = expected_units(source_id)
    if expected is not None:
        entry["expected"] = expected
        if branches < expected:
            entry["status"] = STATUS_PARTIAL
            entry["note"] = (
                "reached %d of %d declared %s" % (branches, expected, field)
            )

    median = median_branches_before(day_dir.name, source_id)
    if median and branches < median * MIN_BRANCH_COVERAGE_RATIO:
        entry["status"] = STATUS_PARTIAL
        entry["note"] = (
            "short run: %d %s against a %d-%s median — files arrived but the "
            "collection is incomplete" % (branches, field, int(median), field[:-1])
        )
    return entry


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
