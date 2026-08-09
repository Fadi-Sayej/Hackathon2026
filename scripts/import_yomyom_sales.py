"""
import_yomyom_sales.py — load YomYom's monthly sales reports (task A-3).

    python3 scripts/import_yomyom_sales.py
    python3 scripts/import_yomyom_sales.py --dir path/to/reports --dry-run

This is the real thing the snapshot proxy was standing in for. YomYom sends one
CSV per month ("דוח מכירות חודש <month> 2026") with, per product:

    תאור פריט          product name
    ברקוד/קוד          barcode
    מכר                UNITS SOLD that month      ← the number we never had
    מחיר קניה          cost price
    מחיר מכירה         selling price
    עלות המכר (חנות)   cost of goods sold (= מכר x מחיר קניה)
    כניסות מלאי        STOCK RECEIPTS that month  ← deliveries, for D-7

WHAT IS MEASURED AND WHAT IS DERIVED
------------------------------------
Measured: units sold per calendar month, and receipts per month. That is all.

Derived: `units_per_day` (month units / days in that month) and `units_sold_7d`
(the daily rate x 7). There is no weekly breakdown in the source, so a 7-day
figure cannot be observed — only inferred from a monthly average. That inference
is wrong for anything seasonal or promotional, which is why the daily rate is the
authoritative field and `units_sold_7d` exists purely because the frontend's
product shape has that slot.

`units_sold_30d` is the LATEST COMPLETE MONTH, not a sum across months. Summing
seven months into a "30-day" field would inflate every downstream number sevenfold.

Coverage is partial by design: the reports list products that moved, so about 21%
of the catalog gets real velocity. Everything else keeps `velocity_confidence:
'none'` — it is not zero sales, it is no data, and the UI must keep saying so.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pyarrow as pa
import pyarrow.parquet as pq

from src.common.paths import SILVER_POS_ROOT
from src.snapshots.velocity import POS_EXPORT_SOURCE

DEFAULT_DIR = ROOT / "data" / "internal" / "raw_pos" / "yomyom" / "sales"

HEBREW_MONTHS = {
    "ינואר": 1, "פברואר": 2, "מרץ": 3, "אפריל": 4, "מאי": 5, "יוני": 6,
    "יולי": 7, "אוגוסט": 8, "ספטמבר": 9, "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12,
}

COL_NAME = "תאור פריט"
COL_BARCODE = "ברקוד/קוד"
COL_SOLD = "מכר"
COL_COST = "מחיר קניה"
COL_PRICE = "מחיר מכירה"
COL_COGS = "עלות המכר (חנות)"
COL_RECEIPTS = "כניסות מלאי"


def normalise_barcode(value) -> str:
    return str(value or "").strip().lstrip("0")


def to_number(value) -> float:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def month_from_filename(path: Path):
    """('יולי 2026') -> date(2026, 7, 1). Returns None when unrecognised."""
    name = path.stem
    year_match = re.search(r"(20\d{2})", name)
    year = int(year_match.group(1)) if year_match else None
    for hebrew, number in HEBREW_MONTHS.items():
        if hebrew in name:
            return date(year or date.today().year, number, 1)
    return None


def read_month(path: Path):
    period = month_from_filename(path)
    if period is None:
        return None, []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return period, []
    keys = {str(k).strip(): k for k in rows[0]}
    if COL_SOLD not in keys or COL_BARCODE not in keys:
        return period, []

    out = []
    for row in rows:
        barcode = normalise_barcode(row.get(keys[COL_BARCODE]))
        if not barcode:
            continue
        out.append({
            "barcode": barcode,
            "product_name": str(row.get(keys.get(COL_NAME, ""), "") or "").strip(),
            "units_sold": to_number(row.get(keys[COL_SOLD])),
            "receipts": to_number(row.get(keys[COL_RECEIPTS])) if COL_RECEIPTS in keys else 0.0,
            "cost_price": to_number(row.get(keys[COL_COST])) if COL_COST in keys else 0.0,
            "selling_price": to_number(row.get(keys[COL_PRICE])) if COL_PRICE in keys else 0.0,
            "cogs": to_number(row.get(keys[COL_COGS])) if COL_COGS in keys else 0.0,
        })
    return period, out


def load_all(directory: Path):
    """barcode -> {period: row}, plus the ordered list of periods found."""
    by_barcode = defaultdict(dict)
    periods = []
    for path in sorted(directory.glob("*.csv")):
        period, rows = read_month(path)
        if period is None or not rows:
            print("  skipped %s (no month in filename, or no sales columns)" % path.name)
            continue
        periods.append(period)
        for row in rows:
            by_barcode[row["barcode"]][period] = row
    return by_barcode, sorted(set(periods))


def _inventory_snapshot_month(inventory_path: Path):
    """First day of the month in which the stock count was taken, or None.

    D-7 reconciles stock_now = opening + received - sold. Sales from AFTER the
    count obviously cannot have affected it, so including them inflates every
    shortfall. With a 2026-06-06 count and reports through July, two extra months
    of sales were being charged against the figure.
    """
    if not inventory_path.exists():
        return None
    try:
        rows = pq.read_table(inventory_path, columns=["_imported_at"]).to_pylist()
    except Exception:
        return None
    if not rows or not rows[0].get("_imported_at"):
        return None
    try:
        stamp = datetime.fromisoformat(str(rows[0]["_imported_at"]).replace("Z", "+00:00"))
    except ValueError:
        return None
    return date(stamp.year, stamp.month, 1)


def build_velocity(by_barcode, periods, reconcile_before=None):
    if not periods:
        return {}, None

    latest = periods[-1]
    days_in_latest = calendar.monthrange(latest.year, latest.month)[1]

    velocity = {}
    for barcode, months in by_barcode.items():
        latest_row = months.get(latest)
        # A product absent from the latest month sold nothing that month. That IS
        # an observation (the report lists movers), so it is 0, not unknown.
        units_latest = latest_row["units_sold"] if latest_row else 0.0

        per_day = units_latest / days_in_latest if days_in_latest else 0.0
        observed_days = sum(
            calendar.monthrange(p.year, p.month)[1] for p in periods if p in months
        )

        last_sale = None
        for period in sorted(months, reverse=True):
            if months[period]["units_sold"] > 0:
                last_month_days = calendar.monthrange(period.year, period.month)[1]
                last_sale = date(period.year, period.month, last_month_days).isoformat()
                break

        # Months that closed strictly before the stock count. Only these can be
        # reconciled against it.
        if reconcile_before is not None:
            window = [p for p in months if p < reconcile_before]
        else:
            window = list(months)
        reconcile_units = sum(months[p]["units_sold"] for p in window)
        reconcile_receipts = sum(months[p]["receipts"] for p in window)

        any_row = latest_row or months[max(months)]
        velocity[barcode] = {
            "units_sold_30d": int(round(units_latest)),
            # Derived from the monthly average — the source has no weekly detail.
            "units_sold_7d": int(round(per_day * 7)),
            "units_per_day": round(per_day, 4),
            "observed_days": float(observed_days),
            "max_gap_days": float(days_in_latest),
            "last_sale_date": last_sale,
            # Real measured sales across months of history: the strongest we have.
            "velocity_confidence": "high" if len(months) >= 3 else "medium",
            "months_observed": len(months),
            "total_units_all_months": int(round(sum(m["units_sold"] for m in months.values()))),
            "total_receipts_all_months": int(round(sum(m["receipts"] for m in months.values()))),
            # Sales but never a single delivery across every month on record means
            # the shop does not stock this: a car wash, an espresso pulled to order,
            # staff consumption. Velocity is real and useful for margin work, but
            # "you are running out, reorder" is nonsense for a car wash. 683 of 1,778
            # products are in this category.
            "is_stocked": sum(m["receipts"] for m in months.values()) > 0,
            "reconcile_units": int(round(reconcile_units)),
            "reconcile_receipts": int(round(reconcile_receipts)),
            "reconcile_months": len(window),
            # Does the stock figure survive its own arithmetic? Filled in below,
            # once we can see the inventory count. See D-7.
            "stock_reconciles": None,
            "product_name": any_row["product_name"],
        }
    return velocity, latest


def annotate_stock_trust(velocity, inventory_path: Path):
    """Mark whether each product's stock figure survives its own arithmetic.

    Same identity as D-7: implied_opening = stock - received + sold. Negative is
    impossible, so the stock number cannot be right. The reorder engine uses this
    to avoid stating an exact order quantity computed from a figure we have just
    proven wrong — 59% of REORDER suggestions were in that position.
    """
    if not inventory_path.exists():
        return
    try:
        rows = pq.read_table(inventory_path, columns=["barcode", "current_stock"]).to_pylist()
    except Exception:
        return
    stock = {
        normalise_barcode(r.get("barcode")): r.get("current_stock")
        for r in rows if r.get("barcode")
    }
    for barcode, entry in velocity.items():
        current = stock.get(barcode)
        if current is None or entry["reconcile_receipts"] <= 0:
            entry["stock_reconciles"] = None      # nothing to check against
            continue
        implied = current - entry["reconcile_receipts"] + entry["reconcile_units"]
        entry["stock_reconciles"] = implied >= 0


def write_sales_table(velocity, sales_path: Path, dry_run: bool):
    if not sales_path.exists():
        raise FileNotFoundError("sales table not found: %s" % sales_path)

    rows = pq.read_table(sales_path).to_pylist()
    matched = 0
    for row in rows:
        entry = velocity.get(normalise_barcode(row.get("barcode")))
        if entry is None:
            # No data is not zero sales. Leave it null so the UI keeps saying so.
            row["units_sold_7d"] = None
            row["units_sold_30d"] = None
            row["sales_amount_30d"] = None
            row["last_sale_date"] = None
            row["units_per_day"] = None
            row["observed_days"] = None
            row["max_gap_days"] = None
            row["velocity_confidence"] = "none"
            row["velocity_source"] = POS_EXPORT_SOURCE
            # Unknown, not false: absent from the sales reports tells us nothing
            # about whether the shop stocks it.
            row["is_stocked"] = None
            row["total_units_all_months"] = None
            row["total_receipts_all_months"] = None
            row["reconcile_units"] = None
            row["reconcile_receipts"] = None
            row["stock_reconciles"] = None
            continue

        matched += 1
        row["units_sold_7d"] = entry["units_sold_7d"]
        row["units_sold_30d"] = entry["units_sold_30d"]
        row["units_per_day"] = entry["units_per_day"]
        row["observed_days"] = entry["observed_days"]
        row["max_gap_days"] = entry["max_gap_days"]
        row["last_sale_date"] = entry["last_sale_date"]
        row["velocity_confidence"] = entry["velocity_confidence"]
        row["velocity_source"] = POS_EXPORT_SOURCE
        row["sales_amount_30d"] = None
        row["is_stocked"] = entry["is_stocked"]
        # Persisted for D-7: the stock-accuracy check reconciles
        # stock_now = opening + received - sold and needs both totals.
        row["total_units_all_months"] = entry["total_units_all_months"]
        row["total_receipts_all_months"] = entry["total_receipts_all_months"]
        row["reconcile_units"] = entry["reconcile_units"]
        row["reconcile_receipts"] = entry["reconcile_receipts"]
        row["stock_reconciles"] = entry["stock_reconciles"]

    schema = pa.schema([
        ("barcode", pa.string()), ("product_name", pa.string()), ("category", pa.string()),
        ("units_sold_7d", pa.int64()), ("units_sold_30d", pa.int64()),
        ("sales_amount_30d", pa.float64()), ("last_sale_date", pa.string()),
        ("units_per_day", pa.float64()), ("observed_days", pa.float64()),
        ("max_gap_days", pa.float64()), ("velocity_confidence", pa.string()),
        ("velocity_source", pa.string()), ("is_stocked", pa.bool_()),
        ("total_units_all_months", pa.int64()), ("total_receipts_all_months", pa.int64()),
        ("reconcile_units", pa.int64()), ("reconcile_receipts", pa.int64()),
        ("stock_reconciles", pa.bool_()),
        ("_imported_at", pa.string()),
        ("_source_file", pa.string()), ("_source_kind", pa.string()),
    ])
    ordered = [{name: row.get(name) for name in schema.names} for row in rows]
    if not dry_run:
        pq.write_table(pa.Table.from_pylist(ordered, schema=schema), sales_path)
    return {"rows": len(rows), "matched": matched, "unmatched": len(rows) - matched}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.dir.exists():
        print("Sales report directory not found: %s" % args.dir, file=sys.stderr)
        return 1

    print("Reading monthly sales reports from %s" % args.dir)
    by_barcode, periods = load_all(args.dir)
    if not periods:
        print("No usable monthly reports found.", file=sys.stderr)
        return 1

    reconcile_before = _inventory_snapshot_month(SILVER_POS_ROOT / "yomyom_inventory.parquet")
    velocity, latest = build_velocity(by_barcode, periods, reconcile_before)
    annotate_stock_trust(velocity, SILVER_POS_ROOT / "yomyom_inventory.parquet")
    stats = write_sales_table(velocity, SILVER_POS_ROOT / "yomyom_sales.parquet", args.dry_run)

    movers = sum(1 for v in velocity.values() if v["units_sold_30d"] > 0)
    result = {
        "months": [p.isoformat() for p in periods],
        "latest_month": latest.isoformat(),
        "products_in_reports": len(velocity),
        "matched_into_catalog": stats["matched"],
        "sold_in_latest_month": movers,
        "rows_written": stats["rows"],
        "dry_run": args.dry_run,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("  months            : %d (%s → %s)" % (len(periods), periods[0], periods[-1]))
        print("  products in report: %d" % len(velocity))
        print("  matched to catalog: %d of %d rows" % (stats["matched"], stats["rows"]))
        print("  sold in %s : %d" % (latest.strftime("%b %Y"), movers))
        print("  velocity_source   : %s" % POS_EXPORT_SOURCE)
        print("  reconcile window  : months before %s (stock count date)" % (
            reconcile_before.isoformat() if reconcile_before else "unknown"))
        if args.dry_run:
            print("  (dry run — nothing written)")
        else:
            print("\nReal sales are now the velocity source. The snapshot proxy will")
            print("stand down automatically (see velocity.has_real_sales).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
