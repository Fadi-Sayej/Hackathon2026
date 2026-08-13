"""
seal_snapshot.py — copy a day's collected files into the dated snapshot (T1 / #46, Steps 3 & 4).

    python3 scripts/seal_snapshot.py --date 2026-08-13

The collectors write into their own bronze/silver lakehouse trees. The snapshot
is a separate, immutable copy keyed by day: it is the time axis #49 reads, and it
must not move when the lakehouse layout changes.

THIS FILE EXISTS BECAUSE IT ONCE DELETED DATA
---------------------------------------------
It used to live inside a heredoc in collect_daily.sh, where nothing could test
it, and it rebuilt each day's folder from the local lakehouse after `rmtree`-ing
whatever was there.

That is fine on the machine that collected the day. It is destructive anywhere
else: the scheduled runner collects into ITS lakehouse and commits only
`data/external/snapshots/` — the bronze/silver trees are gitignored and never
travel. So retrying a day on a second machine rebuilt the folder from a lakehouse
that had never seen the runner's files, and removed them.

Two rules follow, and both are tested:

  1. **Merge, never replace.** The temp dir is seeded from the existing snapshot
     before new files are added. Filenames carry a collection timestamp, so a
     collision means identical content.
  2. **A source already marked `ok` is never touched at all.** Immutability is
     per source, not per day: one failed venue must not put a complete
     156-branch price file at risk.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import (
    EXTERNAL_BRONZE_ROOT,
    EXTERNAL_SILVER_ROOT,
    get_snapshot_manifest_path,
    get_snapshot_path,
)


def source_is_complete(day: str, source_id: str) -> bool:
    """True when today's manifest already records this source as `ok`."""
    path = get_snapshot_manifest_path(day)
    if not path.exists():
        return False
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return False
    return manifest.get("sources", {}).get(source_id, {}).get("status") == "ok"


def materialise(day: str, source_id: str, candidates: Iterable[Path],
                dest: Optional[Path] = None) -> dict:
    """Merge freshly collected files into the day's snapshot folder, atomically."""
    if source_is_complete(day, source_id):
        return {"source": source_id, "skipped": "already complete", "total": None}

    dest = dest or get_snapshot_path(source_id, day)
    present = [c for c in candidates if c.exists() and any(c.rglob("*"))]
    if not present and not dest.exists():
        return {"source": source_id, "skipped": "nothing collected", "total": 0}

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=dest.parent, prefix=f".{source_id}.tmp."))
    try:
        kept = 0
        if dest.exists():
            for path in dest.rglob("*"):
                if not path.is_file():
                    continue
                target = tmp / path.relative_to(dest)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                kept += 1

        collected = 0
        for src in present:
            for path in src.rglob("*"):
                if not path.is_file():
                    continue
                target = tmp / src.name / path.relative_to(src)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                collected += 1

        if dest.exists():
            shutil.rmtree(dest)
        tmp.replace(dest)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    return {
        "source": source_id,
        "collected": collected,
        "already_present": kept,
        "total": sum(1 for p in dest.rglob("*") if p.is_file()),
    }


def seal(day: str) -> list[dict]:
    year, month, daynum = day.split("-")
    plan = {
        "price_transparency": [
            EXTERNAL_BRONZE_ROOT / "alonit" / year / month / daynum,
            EXTERNAL_SILVER_ROOT / "alonit_prices" / "alonit" / year / month / daynum,
        ],
        "delivery_catalog": [
            EXTERNAL_BRONZE_ROOT / "delivery_catalog" / year / month / daynum,
            EXTERNAL_SILVER_ROOT / "products" / "delivery_catalog" / year / month / daynum,
        ],
    }
    return [materialise(day, source_id, candidates) for source_id, candidates in plan.items()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    for result in seal(args.date):
        if result.get("skipped"):
            print("  %s: %s — left untouched" % (result["source"], result["skipped"]))
        else:
            print("  %s: %d collected, %d already present, %d total"
                  % (result["source"], result["collected"],
                     result["already_present"], result["total"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
