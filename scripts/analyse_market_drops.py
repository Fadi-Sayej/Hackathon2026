"""
analyse_market_drops.py — stockout or delisting? (T4 / #49, Step 1)

    python3 scripts/analyse_market_drops.py
    python3 scripts/analyse_market_drops.py --json --limit 50

Reads the dated snapshots collected by T1 and classifies every product that
stopped being listed at one or more branches:

    STOCKOUT   scattered drops    → their customer wants it today. OPPORTUNITY.
    DELISTING  synchronised drops → the chain is walking away. DO NOT BULK BUY.
    UNCERTAIN  too few branches to tell the two apart.

Needs at least two usable snapshot days. History cannot be backfilled, so the
answer improves only with elapsed time — see #46.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.market.concentration import (
    MIN_STORES_FOR_INFERENCE,
    STATE_DELISTING,
    STATE_STOCKOUT,
    detect_drops,
    estimate_base_rate,
    summarise,
)
from src.market.presence import load_presence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--base-rate",
        type=float,
        default=None,
        help="override the measured per-branch stockout rate (mainly for testing)",
    )
    args = parser.parse_args()

    series = load_presence()

    if len(series.days) < 2:
        print("Not enough history yet: %d usable snapshot day(s)." % len(series.days))
        if series.skipped:
            print("Skipped days:")
            for day, why in sorted(series.skipped.items()):
                print("   %s — %s" % (day, why))
        print("\nTwo usable days are the minimum; the charter's target is 30.")
        print("This cannot be rushed — the price server keeps only the current day.")
        return 0

    base_rate = args.base_rate if args.base_rate is not None else estimate_base_rate(series)
    events = detect_drops(series, base_rate=base_rate)
    stats = summarise(events)

    if args.json:
        print(json.dumps({
            "days": [d.isoformat() for d in series.days],
            "base_rate": base_rate,
            "summary": stats,
            "events": [vars(e) | {"day": e.day.isoformat(), "previous_day": e.previous_day.isoformat()}
                       for e in events[:args.limit]],
        }, ensure_ascii=False, indent=2, default=str))
        return 0

    print("Market drop analysis")
    print("  usable days     : %d (%s → %s)" % (len(series.days), series.days[0], series.days[-1]))
    print("  branches        : %d" % len(series.all_stores()))
    print("  products tracked: %d" % len(series.all_barcodes()))
    print("  base stockout   : %.4f per branch per day (measured)" % base_rate)
    print("  drop events     : %d" % stats["events"])
    print("  by state        : %s" % stats["by_state"])

    if len(series.all_stores()) < MIN_STORES_FOR_INFERENCE:
        print("\n  ⚠️  Fewer than %d branches: every drop reports UNCERTAIN, because"
              % MIN_STORES_FOR_INFERENCE)
        print("      coordination cannot be told apart from coincidence.")

    warnings = [e for e in events if e.state == STATE_DELISTING]
    if warnings:
        print("\n⚠️  LIKELY DELISTINGS — do not bulk-buy these:")
        for e in warnings[:args.limit]:
            print("   %-30s %d/%d branches, p=%.5f  (%s)"
                  % ((e.product_name or e.barcode)[:30], e.stores_dropped,
                     e.stores_carrying, e.p_value, e.day))

    chances = [e for e in events if e.state == STATE_STOCKOUT]
    if chances:
        print("\n✅ LIKELY STOCKOUTS — their customer is looking for these today:")
        for e in chances[:args.limit]:
            print("   %-30s %d/%d branches            (%s)"
                  % ((e.product_name or e.barcode)[:30], e.stores_dropped,
                     e.stores_carrying, e.day))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
