"""
rehydrate_silver.py — rebuild data/external/silver/ from the committed snapshots.

Why this exists
---------------
The daily collector writes bronze/ and silver/, but .github/workflows/collect-daily.yml
commits ONLY `data/external/snapshots/`. Everything under data/** is gitignored, so on a
fresh clone — and in CI — data/external/silver/ holds whatever was force-added months ago
and nothing since. src/signals/competitor_product_signals.py reads silver/, so the market
half of the product silently collapses: verified on a clean clone on 2026-09-05, the whole
export came back with 0 recommendations and exit code 0.

Committing silver/ separately would store the same bytes twice: seal_snapshot.py copies the
very same *_silver.parquet files into the snapshot, so the data is already in git. This
reverses that copy instead, which adds no committed bytes and leaves the collector — whose
history cannot be re-collected — untouched.

Exact inverse of seal_snapshot.py's plan:

    snapshots/<YYYY-MM-DD>/price_transparency/**/*_silver.parquet
        -> silver/alonit_prices/alonit/<YYYY>/<MM>/<DD>/
    snapshots/<YYYY-MM-DD>/delivery_catalog/**/*_silver.parquet
        -> silver/products/delivery_catalog/<YYYY>/<MM>/<DD>/

Bronze is deliberately not rehydrated: nothing downstream reads it.

Usage:
  python scripts/rehydrate_silver.py
  python scripts/rehydrate_silver.py --force   # re-copy even when the target exists
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import EXTERNAL_SILVER_ROOT, EXTERNAL_SNAPSHOTS_ROOT

DAY_DIR = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# source_id in the snapshot -> its home in the silver tree (see seal_snapshot.seal)
SOURCE_TO_SILVER = {
    "price_transparency": ("alonit_prices", "alonit"),
    "delivery_catalog": ("products", "delivery_catalog"),
}


def _orphans(sourced: set[str]) -> list[str]:
    """Silver files, in the two trees this script owns, that no committed snapshot holds.

    Rehydrate only ever copies. On a runner that is fine — it starts empty. On a working
    tree alive for months it is not: competitor_product_signals reads *everything* under
    silver, so a laptop can carry files no clean checkout has and quietly produce different
    numbers from CI. Measured at 462d604 on 2026-09-13 — same commit, same snapshots, a
    fresh clone against a working tree that had been alive for months:

        fresh clone   341 delivery_catalog parquet -> 7,448 wolt rows -> 190,426 matches
        working tree  343 delivery_catalog parquet -> 7,455 wolt rows -> 189,562 matches

    On that tree, 44 of the 343 parquet under products/delivery_catalog carried a filename
    no committed snapshot holds — the oldest from May 2026, before the collector existed.

    Reported, never deleted. They are real observations and the snapshots behind them
    cannot be re-collected, so removing them to tidy a count is not this script's call.
    Only the two trees in SOURCE_TO_SILVER are examined: silver/products/kaggle_* comes
    from a different pipeline and has no snapshots by design, and counting it would make
    this fire on every run until everyone ignored it.

    Globs `*.parquet`, not `*_silver.parquet`, because that is what the consumer globs.
    Checking only the files this script copies missed 36 of 44 on the real tree — the
    suffixed shards the collector writes alongside each sealed file. A guard has to look
    at what the reader reads, not at what the writer wrote.
    """
    found: list[str] = []
    for parts in SOURCE_TO_SILVER.values():
        root = EXTERNAL_SILVER_ROOT.joinpath(*parts)
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.parquet")):
            if p.name not in sourced:
                found.append(str(p.relative_to(EXTERNAL_SILVER_ROOT)))
    return sorted(found)


def rehydrate(force: bool = False) -> dict:
    """Copy every committed snapshot's silver parquet back into the silver tree."""
    copied = skipped = 0
    days: set[str] = set()
    sourced: set[str] = set()

    if not EXTERNAL_SNAPSHOTS_ROOT.exists():
        return {"status": "ok", "copied": 0, "skipped": 0, "days": 0,
                "orphans": 0, "orphan_paths": [], "note": "no snapshots directory"}

    for day_dir in sorted(EXTERNAL_SNAPSHOTS_ROOT.iterdir()):
        if not day_dir.is_dir() or not DAY_DIR.match(day_dir.name):
            continue
        year, month, dayn = day_dir.name.split("-")

        for source_id, parts in SOURCE_TO_SILVER.items():
            src_dir = day_dir / source_id
            if not src_dir.is_dir():
                continue
            dest_dir = EXTERNAL_SILVER_ROOT.joinpath(*parts) / year / month / dayn

            for src in sorted(src_dir.rglob("*_silver.parquet")):
                sourced.add(src.name)
                dest = dest_dir / src.name
                # Size is enough to detect an interrupted copy; these files are
                # immutable once sealed, so equal size means equal content.
                if not force and dest.exists() and dest.stat().st_size == src.stat().st_size:
                    skipped += 1
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                copied += 1
                days.add(day_dir.name)

    orphans = _orphans(sourced)
    if orphans:
        print(f"WARNING  {len(orphans)} silver file(s) under this tree match no committed "
              f"snapshot, so a clean clone will not read them and its figures will differ.",
              file=sys.stderr)
        for path in orphans[:5]:
            print(f"           {path}", file=sys.stderr)
        if len(orphans) > 5:
            print(f"           … and {len(orphans) - 5} more", file=sys.stderr)
        print("         Left in place: they are real observations and the snapshots behind "
              "them cannot be re-collected. Removing them is a human's call.", file=sys.stderr)

    return {"status": "ok", "copied": copied, "skipped": skipped, "days": len(days),
            "orphans": len(orphans), "orphan_paths": orphans}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="Re-copy even when a same-sized target already exists.")
    args = parser.parse_args()
    print(json.dumps(rehydrate(force=args.force), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
