"""
diff_snapshots.py — what changed between any two collected days (T1 / #46).

    python3 scripts/diff_snapshots.py --from 2026-08-11 --to 2026-08-13
    python3 scripts/diff_snapshots.py --from 2026-08-11 --to 2026-08-12 --json
    python3 scripts/diff_snapshots.py --latest                  # the two most recent
    python3 scripts/diff_snapshots.py --source delivery_catalog --latest

Satisfies two things #46 asks for by name:

  * Acceptance — "A diff between any two dates can be produced by a script."
  * Step 6 — "write an explicit daily delta with `appeared` / `disappeared`
    arrays". We keep full snapshots as the issue prefers, so this derives the
    delta on demand instead of storing it. Re-derivation is free; a stored delta
    can disagree with the snapshots it came from.

REFUSING IS A FEATURE
---------------------
A day whose manifest is missing, `failed`, or records a short run is not a day
of market history — it is an absence of information. Diffing against one would
report thousands of disappearances that never happened. This script refuses such
a day and says which, rather than producing a plausible answer.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import EXTERNAL_SNAPSHOTS_ROOT
from src.market.presence import (
    DELIVERY_CATALOG,
    PRICE_TRANSPARENCY,
    USABLE_STATUSES,
    load_presence,
)

Pair = Tuple[str, str]


def usable_days(source_id: str, root: Optional[Path] = None) -> list[str]:
    """Days this source can be read from, in order. Uses the same rules as the
    presence series, so a diff can never be built on a day the analysis rejects.

    The root is passed on. load_presence() used to be called without one, so it read the
    repository's snapshots whatever root the caller had meant, while why_unusable() read the
    manifest under that root: two roots for one question."""
    series = load_presence(root=root or EXTERNAL_SNAPSHOTS_ROOT, source_id=source_id)
    return [d.isoformat() for d in series.days]


def why_unusable(day: str, source_id: str, root: Optional[Path] = None) -> Optional[str]:
    """None when the day is usable, otherwise the reason it is not."""
    root = root or EXTERNAL_SNAPSHOTS_ROOT
    day_dir = root / day
    if not day_dir.exists():
        return "no snapshot folder for that date"
    manifest_path = day_dir / "_manifest.json"
    if not manifest_path.exists():
        return "no manifest — a failed scrape cannot be told from a real absence"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError:
        return "manifest is not readable JSON"
    entry = manifest.get("sources", {}).get(source_id)
    if entry is None:
        return f"manifest records no {source_id} for that day"
    if entry.get("status") not in USABLE_STATUSES:
        return f"{source_id} status is {entry.get('status')!r}"
    if day not in usable_days(source_id, root):
        # Covers the short-run case, which the manifest may still call `ok` if
        # it was written before the coverage check existed.
        return "excluded from the series (short run or no listings)"
    return None


def read_day(day: str, source_id: str,
             root: Optional[Path] = None) -> Tuple[Set[Pair], Dict[Pair, float], Dict[str, str]]:
    """(listings, prices, names) for one day.

    Prices are read here rather than in presence.py, which is deliberately
    presence-only — mixing prices into the series would make the statistics in
    #49 harder to check.
    """
    listings: Set[Pair] = set()
    prices: Dict[Pair, float] = {}
    names: Dict[str, str] = {}

    source_dir = (root or EXTERNAL_SNAPSHOTS_ROOT) / day / source_id
    if not source_dir.exists():
        return listings, prices, names

    for path in sorted(source_dir.rglob("*.parquet")):
        if "silver" not in path.name:
            continue
        try:
            frame = pl.read_parquet(path)
        except Exception:
            continue
        if "barcode" not in frame.columns or "store_id" not in frame.columns:
            continue
        columns = ["barcode", "store_id"]
        for optional in ("price", "product_name"):
            if optional in frame.columns:
                columns.append(optional)
        for row in frame.select(columns).iter_rows(named=True):
            # lstrip("0") matches src/market/presence.py — leading zeros differ
            # between sources for the same physical barcode.
            barcode = str(row.get("barcode") or "").strip().lstrip("0")
            store = str(row.get("store_id") or "").strip()
            if not barcode or not store:
                continue
            pair = (barcode, store)
            listings.add(pair)
            price = row.get("price")
            if price is not None:
                try:
                    prices[pair] = float(price)
                except (TypeError, ValueError):
                    pass
            name = row.get("product_name")
            if name and barcode not in names:
                names[barcode] = str(name)
    return listings, prices, names


def diff(day_from: str, day_to: str, source_id: str, price_epsilon: float = 0.005,
         root: Optional[Path] = None) -> dict:
    before, prices_before, names_before = read_day(day_from, source_id, root)
    after, prices_after, names_after = read_day(day_to, source_id, root)
    names = {**names_before, **names_after}

    appeared = sorted(after - before)
    disappeared = sorted(before - after)

    repriced = []
    for pair in sorted(before & after):
        old = prices_before.get(pair)
        new = prices_after.get(pair)
        if old is None or new is None:
            continue
        if abs(new - old) > price_epsilon:
            repriced.append({
                "barcode": pair[0],
                "store_id": pair[1],
                "product_name": names.get(pair[0]),
                "price_from": round(old, 2),
                "price_to": round(new, 2),
                "delta": round(new - old, 2),
            })

    def label(pairs):
        return [
            {"barcode": b, "store_id": s, "product_name": names.get(b)}
            for b, s in pairs
        ]

    barcodes_before = {b for b, _s in before}
    barcodes_after = {b for b, _s in after}

    return {
        "from": day_from,
        "to": day_to,
        "source": source_id,
        "summary": {
            "listings_from": len(before),
            "listings_to": len(after),
            "appeared": len(appeared),
            "disappeared": len(disappeared),
            "repriced": len(repriced),
            "stores_from": len({s for _b, s in before}),
            "stores_to": len({s for _b, s in after}),
            # Barcode-level: gone from EVERY branch, which is the shape #49
            # reads as a possible delisting.
            "barcodes_gone_everywhere": len(barcodes_before - barcodes_after),
            "barcodes_new_everywhere": len(barcodes_after - barcodes_before),
        },
        "appeared": label(appeared),
        "disappeared": label(disappeared),
        "repriced": repriced,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="day_from", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="day_to", help="YYYY-MM-DD")
    parser.add_argument("--latest", action="store_true",
                        help="diff the two most recent usable days")
    parser.add_argument("--source", default=PRICE_TRANSPARENCY,
                        choices=[PRICE_TRANSPARENCY, DELIVERY_CATALOG])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.latest:
        days = usable_days(args.source)
        if len(days) < 2:
            print("Need two usable days; have %d." % len(days))
            return 1
        args.day_from, args.day_to = days[-2], days[-1]

    if not args.day_from or not args.day_to:
        parser.error("give --from and --to, or --latest")

    for day in (args.day_from, args.day_to):
        try:
            date.fromisoformat(day)
        except ValueError:
            print("Not a date: %s (expected YYYY-MM-DD)" % day)
            return 1

    problems = {day: why_unusable(day, args.source)
                for day in (args.day_from, args.day_to)}
    if any(problems.values()):
        print("Refusing to diff — a day without usable data is not a day of history:")
        for day, reason in problems.items():
            print("   %s : %s" % (day, reason or "ok"))
        print("\nDiffing against it would report disappearances that never happened.")
        return 1

    result = diff(args.day_from, args.day_to, args.source)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    s = result["summary"]
    print("Snapshot diff — %s → %s  (%s)" % (result["from"], result["to"], result["source"]))
    print("  listings      : %d → %d" % (s["listings_from"], s["listings_to"]))
    print("  stores        : %d → %d" % (s["stores_from"], s["stores_to"]))
    print("  appeared      : %d" % s["appeared"])
    print("  disappeared   : %d" % s["disappeared"])
    print("  repriced      : %d" % s["repriced"])
    print("  gone from ALL branches : %d" % s["barcodes_gone_everywhere"])
    print("  new  at  ANY branch    : %d" % s["barcodes_new_everywhere"])

    for title, rows in (("DISAPPEARED", result["disappeared"]),
                        ("APPEARED", result["appeared"])):
        if not rows:
            continue
        print("\n%s (first %d of %d):" % (title, min(args.limit, len(rows)), len(rows)))
        for row in rows[:args.limit]:
            print("   %-14s store %-6s %s"
                  % (row["barcode"], row["store_id"], (row["product_name"] or "")[:34]))

    if result["repriced"]:
        print("\nREPRICED (first %d of %d):"
              % (min(args.limit, len(result["repriced"])), len(result["repriced"])))
        for row in result["repriced"][:args.limit]:
            print("   %-14s store %-6s %7.2f → %7.2f  (%+.2f)  %s"
                  % (row["barcode"], row["store_id"], row["price_from"],
                     row["price_to"], row["delta"], (row["product_name"] or "")[:26]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
