from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.expiry.expiry_tracking import build_expiry_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build expiry alerts by joining manual expiry scans with POS silver tables."
    )
    parser.add_argument("--as-of", default=None, help="Optional date: YYYY-MM-DD or DD/MM/YYYY.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_expiry_report(as_of=args.as_of)
    except Exception as exc:
        print(f"Expiry report failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
