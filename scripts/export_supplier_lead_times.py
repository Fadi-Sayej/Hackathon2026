#!/usr/bin/env python3
"""
export_supplier_lead_times.py — publish measured lead times to the frontend pipeline.

scripts/normalize-datasets.mjs hardcoded `leadTimeDays: 3` for all 7,674 products
because no real delivery interval had ever been observed. This writes what the
receiving ledger now knows so that script can stop guessing.

Usage:
    python3 scripts/export_supplier_lead_times.py
    python3 scripts/export_supplier_lead_times.py --receipts path.csv --output out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.paths import RECEIPTS_CSV, SUPPLIER_LEAD_TIMES_JSON  # noqa: E402
from src.internal.receiving import (  # noqa: E402
    DEFAULT_LEAD_TIME_DAYS,
    MIN_DELIVERIES_FOR_LEAD_TIME,
    barcode_supplier_map,
    load_receipts,
    supplier_lead_times,
)


def build_lead_time_export(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    lead_times = supplier_lead_times(receipts)
    by_barcode = barcode_supplier_map(receipts)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "defaultLeadTimeDays": DEFAULT_LEAD_TIME_DAYS,
        "minDeliveriesForLeadTime": MIN_DELIVERIES_FOR_LEAD_TIME,
        "leadTimes": lead_times,
        "supplierByBarcode": by_barcode,
        "totals": {
            "receipts": len(receipts),
            "suppliers": len(lead_times),
            "barcodes": len(by_barcode),
        },
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export measured supplier lead times.")
    parser.add_argument("--receipts", default=str(RECEIPTS_CSV))
    parser.add_argument("--output", default=str(SUPPLIER_LEAD_TIMES_JSON))
    args = parser.parse_args(argv)

    payload = build_lead_time_export(load_receipts(Path(args.receipts)))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    measured = [s for s, v in payload["leadTimes"].items() if v["median_days"] is not None]
    print(
        f"Wrote {out} — {payload['totals']['receipts']} receipts, "
        f"{payload['totals']['suppliers']} suppliers, "
        f"{len(measured)} with a measured lead time."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
