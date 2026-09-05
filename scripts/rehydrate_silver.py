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


def rehydrate(force: bool = False) -> dict:
    """Copy every committed snapshot's silver parquet back into the silver tree."""
    copied = skipped = 0
    days: set[str] = set()

    if not EXTERNAL_SNAPSHOTS_ROOT.exists():
        return {"status": "ok", "copied": 0, "skipped": 0, "days": 0,
                "note": "no snapshots directory"}

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

    return {"status": "ok", "copied": copied, "skipped": skipped, "days": len(days)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="Re-copy even when a same-sized target already exists.")
    args = parser.parse_args()
    print(json.dumps(rehydrate(force=args.force), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
