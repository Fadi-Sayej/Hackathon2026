#!/usr/bin/env python3
"""
reconcile_restocks.py — compare recorded deliveries against inferred restocks.

src/snapshots/velocity.py infers a restock from any rise in stock between two
POS snapshots, because until the receiving ledger existed nothing recorded what
actually arrived. This script is where that inference gets checked against the
ledger, and it prints the disagreements — a stock rise nobody recorded, or a
recorded delivery no snapshot ever saw.

It answers a question, it does not write anything. Nothing downstream consumes
its output; run it when you want to know whether the two sources agree.

Usage:
    python3 scripts/reconcile_restocks.py
    python3 scripts/reconcile_restocks.py --limit 20
    python3 scripts/reconcile_restocks.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import RECEIPTS_CSV, SNAPSHOTS_ROOT  # noqa: E402
from src.internal.receiving import load_receipts  # noqa: E402
from src.internal.restock_reconcile import (  # noqa: E402
    RECONCILE_TOLERANCE_UNITS,
    reconcile_restocks,
)
from src.snapshots.velocity import build_intervals, list_usable_snapshots  # noqa: E402

# Ordered worst-first: a delivery that happened and was never recorded is the
# finding that costs something, an exact match is the finding that costs nothing.
VERDICT_ORDER = ["no_receipts", "under_recorded", "over_recorded", "unobserved", "matches"]

VERDICT_LABEL = {
    "no_receipts": "stock rose, nothing recorded",
    "under_recorded": "stock rose more than was recorded",
    "over_recorded": "more recorded than stock ever rose",
    # Deliberately not "no snapshot saw the product": the product is usually in
    # the snapshots, it just never rose. Either the goods sold through before
    # the next snapshot, or no snapshot straddles the delivery date.
    "unobserved": "recorded, but no stock rise was ever observed",
    "matches": "agree (within tolerance)",
}


def group_by_verdict(report: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Reconciliation rows bucketed by verdict, each bucket worst-gap first."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for barcode, row in report.items():
        grouped.setdefault(row["verdict"], []).append({"barcode": barcode, **row})
    for rows in grouped.values():
        rows.sort(key=lambda row: abs(row["delta"]), reverse=True)
    return grouped


def format_report(
    report: dict[str, dict[str, Any]],
    receipt_count: int,
    interval_count: int,
    limit: int = 10,
) -> str:
    """A readable summary. Says plainly when there is simply nothing to compare."""
    lines = [
        f"Receiving ledger: {receipt_count} receipt lines",
        f"Snapshot intervals: {interval_count}",
    ]

    # Neither of these is a fault. An empty ledger on day one of the pilot and a
    # single snapshot are both the normal early state, and reporting them as a
    # problem would train whoever runs this to ignore it.
    if receipt_count == 0 and interval_count == 0:
        lines.append("")
        lines.append(
            "Nothing to reconcile yet: no deliveries have been recorded and there are "
            "not two comparable POS snapshots. This is the expected state before the "
            "pilot has run — record deliveries in the app and import a second snapshot."
        )
        return "\n".join(lines)
    if interval_count == 0:
        lines.append("")
        lines.append(
            "Nothing to reconcile yet: fewer than two comparable POS snapshots, so no "
            "stock movement has been observed to check the ledger against."
        )
        return "\n".join(lines)
    if receipt_count == 0:
        lines.append("")
        lines.append(
            "Nothing to reconcile yet: no deliveries have been recorded, so there is "
            "nothing to check the inferred restocks against — every one of them would "
            "trivially read as unrecorded. Record deliveries in the app first."
        )
        return "\n".join(lines)

    # A barcode that neither moved nor was delivered is not an agreement, it is
    # an absence of evidence — and there are thousands of them, because every
    # barcode present in two snapshots gets a zero row. Counting those as
    # "matches" would report several thousand successful reconciliations off a
    # ledger holding one delivery.
    active = {
        barcode: row
        for barcode, row in report.items()
        if row["inferred_restocked"] != 0.0 or row["recorded_received"] != 0.0
    }
    idle = len(report) - len(active)

    grouped = group_by_verdict(active)
    lines.append(
        f"Barcodes compared: {len(active)} with movement on at least one side "
        f"(tolerance ±{RECONCILE_TOLERANCE_UNITS:g} units); "
        f"{idle} with no restock and no delivery either way"
    )

    for verdict in VERDICT_ORDER:
        rows = grouped.get(verdict, [])
        if not rows:
            continue
        lines.append("")
        lines.append(f"{verdict} — {VERDICT_LABEL[verdict]} ({len(rows)})")
        for row in rows[:limit]:
            lines.append(
                f"  {row['barcode']:>16}  inferred {row['inferred_restocked']:>8.1f}"
                f"  recorded {row['recorded_received']:>8.1f}"
                f"  delta {row['delta']:>+8.1f}"
            )
        if len(rows) > limit:
            lines.append(f"  ... and {len(rows) - limit} more")

    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile recorded deliveries against snapshots.")
    parser.add_argument("--receipts", default=str(RECEIPTS_CSV))
    parser.add_argument("--snapshots", default=str(SNAPSHOTS_ROOT))
    parser.add_argument("--limit", type=int, default=10, help="rows shown per verdict")
    parser.add_argument("--json", action="store_true", help="emit the raw report as JSON")
    args = parser.parse_args(argv)

    receipts = load_receipts(Path(args.receipts))
    intervals = build_intervals(list_usable_snapshots(Path(args.snapshots)))
    report = reconcile_restocks(receipts, intervals)

    if args.json:
        print(json.dumps(
            {
                "receipts": len(receipts),
                "intervals": len(intervals),
                "report": report,
            },
            ensure_ascii=False,
            indent=2,
        ))
    else:
        print(format_report(report, len(receipts), len(intervals), limit=args.limit))

    # A disagreement is information, not a build failure. Nothing gates on this.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
