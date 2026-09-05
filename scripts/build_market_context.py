"""build_market_context.py — write public/data/market-context.json.

    python3 scripts/build_market_context.py
    python3 scripts/build_market_context.py --date 2027-02-10 --use-islamic-api
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.context.build import write_market_context  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument(
        "--use-islamic-api", action="store_true",
        help="Try Aladhan before falling back to the offline tabular calendar.",
    )
    args = parser.parse_args()
    day = date.fromisoformat(args.date) if args.date else None
    print(json.dumps(write_market_context(day, use_islamic_api=args.use_islamic_api), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
