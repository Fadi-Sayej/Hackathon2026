"""import_yomyom_sales.py — monthly sales reports → silver evidence tables.

Thin wrapper over src/internal_pos/sales_importer.py so CI keeps its script name.
The old per-product velocity table (units_sold_7d synthesised from a monthly mean)
is gone: V1 reads sales_monthly / sales_summary (design.md §7.1)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import SILVER_POS_ROOT  # noqa: E402
from src.internal_pos.pos_importer import read_pos_vintage  # noqa: E402
from src.internal_pos.sales_importer import import_sales  # noqa: E402

DEFAULT_DIR = ROOT / "data" / "internal" / "raw_pos" / "yomyom" / "sales"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.dir.exists():
        print(f"Sales report directory not found: {args.dir}", file=sys.stderr)
        return 1
    vintage = read_pos_vintage(SILVER_POS_ROOT)
    as_of = date.fromisoformat(vintage["as_of"][:10]) if vintage and vintage.get("as_of") else None
    result = import_sales(args.dir, inventory_as_of=as_of)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    return 0 if result["window"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
