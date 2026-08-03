"""
check_import_quality.py — gate a POS import before it reaches the customer (task A-4).

A broken or truncated export must never be served to YomYom silently. Half a catalog
looks exactly like "we sold out of everything" to the analytics downstream, and the
store manager would be looking at nonsense with no way to tell.

Exit codes:
    0  clean, or advisory warnings only
    1  FAILED a hard gate — do not publish this import

    python3 scripts/check_import_quality.py
    python3 scripts/check_import_quality.py --json
    python3 scripts/check_import_quality.py --baseline 7674
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pyarrow.parquet as pq

from src.common.paths import SILVER_POS_ROOT
from src.snapshots.velocity import list_usable_snapshots

# A drop larger than this versus the previous import means a broken export, not a
# quiet week of delistings.
MAX_ROW_DROP_PCT = 20.0

QUALITY_DIR = ROOT / "reports" / "quality"


def _rows(path: Path):
    if not path.exists():
        return []
    return pq.read_table(path).to_pylist()


def _previous_row_count() -> int | None:
    """Row count of the most recent snapshot, used as the baseline."""
    snapshots = list_usable_snapshots()
    if not snapshots:
        return None
    _, latest = snapshots[-1]
    for name in ("products.parquet", "inventory.parquet"):
        path = latest / name
        if path.exists():
            return pq.read_table(path).num_rows
    return None


def run_checks(baseline: int | None = None) -> dict:
    products = _rows(SILVER_POS_ROOT / "yomyom_products.parquet")
    inventory = _rows(SILVER_POS_ROOT / "yomyom_inventory.parquet")

    total = len(products)

    def _f(value):
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    missing_barcode = sum(1 for r in products if not str(r.get("barcode") or "").strip())
    zero_price = sum(1 for r in products if (_f(r.get("selling_price")) or 0) <= 0)
    zero_cost = sum(1 for r in products if (_f(r.get("cost_price")) or 0) <= 0)
    missing_name = sum(1 for r in products if not str(r.get("product_name") or "").strip())

    # Count over inventory ROWS, not a barcode-keyed dict: 307 rows have no barcode and
    # would collapse into a single bucket, undercounting.
    negative_stock = sum(1 for r in inventory if (_f(r.get("current_stock")) or 0) < 0)

    if baseline is None:
        baseline = _previous_row_count()

    failures: list[str] = []
    warnings: list[str] = []

    if total == 0:
        failures.append("Silver products table is EMPTY — the import produced nothing.")

    drop_pct = None
    if baseline and total:
        drop_pct = round((baseline - total) / baseline * 100.0, 2)
        if drop_pct > MAX_ROW_DROP_PCT:
            failures.append(
                "Row count fell %.1f%% (%d -> %d), over the %.0f%% limit. This usually means a "
                "truncated or partial export, not real delistings. DO NOT PUBLISH." % (
                    drop_pct, baseline, total, MAX_ROW_DROP_PCT)
            )
        elif drop_pct > 5:
            warnings.append("Row count fell %.1f%% (%d -> %d) — worth a look." % (drop_pct, baseline, total))

    if total and missing_name / total > 0.05:
        failures.append(
            "%d of %d rows have no product name (%.1f%%). Likely a column-mapping break." % (
                missing_name, total, missing_name / total * 100)
        )

    if total and zero_price / total > 0.5:
        failures.append(
            "%d of %d rows have no selling price (%.1f%%). Margin and price-gap features "
            "would be meaningless." % (zero_price, total, zero_price / total * 100)
        )

    # Known, accepted characteristics of this customer's export — reported, not fatal.
    if missing_barcode:
        warnings.append("%d rows have no barcode; they cannot be matched to competitors or velocity." % missing_barcode)
    if negative_stock:
        warnings.append("%d rows have negative stock (POS artifact; clamped downstream)." % negative_stock)
    if zero_cost:
        warnings.append("%d rows have no cost price; margin is unavailable for those." % zero_cost)

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_products": total,
        "baseline_products": baseline,
        "row_drop_pct": drop_pct,
        "missing_barcode": missing_barcode,
        "missing_name": missing_name,
        "zero_price": zero_price,
        "zero_cost": zero_cost,
        "negative_stock": negative_stock,
        "failures": failures,
        "warnings": warnings,
        "passed": not failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--baseline", type=int, default=None, help="override the previous row count")
    args = parser.parse_args()

    report = run_checks(baseline=args.baseline)

    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (QUALITY_DIR / ("import_quality_%s.json" % stamp)).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Import quality: %s" % ("PASS" if report["passed"] else "FAIL"))
        print("  products      : %s (baseline %s)" % (report["total_products"], report["baseline_products"]))
        if report["row_drop_pct"] is not None:
            print("  row change    : %+.1f%%" % -report["row_drop_pct"])
        print("  no barcode    : %s" % report["missing_barcode"])
        print("  no price      : %s" % report["zero_price"])
        print("  no cost       : %s" % report["zero_cost"])
        print("  negative stock: %s" % report["negative_stock"])
        for w in report["warnings"]:
            print("  WARNING: %s" % w)
        for f in report["failures"]:
            print("  FAILED : %s" % f)

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
