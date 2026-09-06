"""
compare_pos_snapshots.py — compare the two most recent POS snapshots.

Reports added/removed products, price + WOLT changes, and an inventory movement
proxy derived from stock deltas. Gracefully reports when fewer than two snapshots
exist yet (you need a second POS import to compare against the first).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.snapshots.pos_snapshots import build_snapshot_comparison_report


def main() -> int:
    result = build_snapshot_comparison_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
