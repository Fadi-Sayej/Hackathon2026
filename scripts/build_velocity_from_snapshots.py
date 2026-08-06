"""
build_velocity_from_snapshots.py — derive sales velocity from POS stock snapshots.

The POS export has no sales history, so velocity is reconstructed from how stock
changed between snapshots. Run this after every import, once at least two snapshots
taken on different days exist.

    python3 scripts/build_velocity_from_snapshots.py
    python3 scripts/build_velocity_from_snapshots.py --dry-run
    python3 scripts/build_velocity_from_snapshots.py --json

See src/snapshots/velocity.py for what this proxy can and cannot prove.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.snapshots.velocity import build_velocity, format_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="compute and report without writing yomyom_sales.parquet",
    )
    parser.add_argument("--json", action="store_true", help="emit raw JSON instead of a summary")
    args = parser.parse_args()

    result = build_velocity(write=not args.dry_run)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))
        if args.dry_run:
            print("  (dry run — nothing written)")

    # Not enough history is a normal early-pilot state, not a failure: the pipeline
    # should keep going and the UI reports confidence 'none'.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
