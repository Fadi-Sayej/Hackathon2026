from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.expiry.expiry_tracking import add_expiry_scan, import_expiry_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record barcode + expiry-date scans for POS products."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--barcode", help="Product barcode scanned at receiving.")
    mode.add_argument("--input-csv", type=Path, help="CSV with barcode,expiry_date rows.")
    parser.add_argument("--expiry-date", help="Expiry date: YYYY-MM-DD or DD/MM/YYYY.")
    parser.add_argument("--scanned-at", default=None, help="Optional ISO timestamp override.")
    parser.add_argument("--notes", default="", help="Optional operator note.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.input_csv:
            if not args.input_csv.exists():
                print(f"Input CSV not found: {args.input_csv}", file=sys.stderr)
                return 1
            result = import_expiry_csv(args.input_csv)
        else:
            if not args.expiry_date:
                print("--expiry-date is required with --barcode", file=sys.stderr)
                return 1
            result = add_expiry_scan(
                barcode=args.barcode,
                expiry_date=args.expiry_date,
                scanned_at=args.scanned_at,
                notes=args.notes,
            )
    except Exception as exc:
        print(f"Expiry scan failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
