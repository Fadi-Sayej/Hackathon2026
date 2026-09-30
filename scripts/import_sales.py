"""import_sales.py — the store's monthly sales reports → silver evidence tables.

Thin wrapper over src/internal_pos/sales_importer.py so CI keeps its script name.
The old per-product velocity table (units_sold_7d synthesised from a monthly mean)
is gone: V1 reads sales_monthly / sales_summary (design.md §7.1)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.store import get_store  # noqa: E402
from src.internal_pos.sales_importer import import_sales  # noqa: E402

DEFAULT_DIR = get_store().sales_monthly_dir          # ADR-036: the store's settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.dir.exists():
        print(f"Sales report directory not found: {args.dir}", file=sys.stderr)
        return 1
    # No stock date (ADR-026): the reconcile window is cut in the engine, at load. This used
    # to cut it here with a bare date.fromisoformat, a looser rule than the engine's own.
    result = import_sales(args.dir)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    return 0 if result["window"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
