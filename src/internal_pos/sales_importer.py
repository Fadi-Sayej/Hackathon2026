# src/internal_pos/sales_importer.py
"""Monthly sales reports → month-grained evidence (design.md §7.1, ADR-011).

Measured: units and receipts per product per calendar month. The month comes
from the FILENAME — the reports carry no date column (CLAUDE.md rule 13).
A product absent from a report gets NO row: absence is `none`, never zero."""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

from src.common.paths import SILVER_POS_ROOT
from src.engine.model import EvidenceWindow, norm_barcode

HEBREW_MONTHS = {"ינואר": 1, "פברואר": 2, "מרץ": 3, "אפריל": 4, "מאי": 5, "יוני": 6,
                 "יולי": 7, "אוגוסט": 8, "ספטמבר": 9, "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12}
COL = {"name": "תאור פריט", "barcode": "ברקוד/קוד", "units": "מכר", "cost": "מחיר קניה",
       "price": "מחיר מכירה", "receipts": "כניסות מלאי"}


def _num(value) -> float:
    text = str(value or "").replace(",", "").strip()
    try:
        return float(text) if text else 0.0
    except ValueError:
        return 0.0


def month_from_filename(path: Path) -> Optional[str]:
    year = re.search(r"(20\d{2})", path.stem)
    for hebrew, number in HEBREW_MONTHS.items():
        if hebrew in path.stem and year:
            return f"{year.group(1)}-{number:02d}"
    return None


def _consecutive(months: list[str]) -> bool:
    for a, b in zip(months, months[1:]):
        ya, ma = map(int, a.split("-")); yb, mb = map(int, b.split("-"))
        if (yb * 12 + mb) - (ya * 12 + ma) != 1:
            return False
    return True


def evidence_window(months: list[str], full_cycle_months: int) -> EvidenceWindow:
    months = sorted(set(months))
    full = len(months) >= full_cycle_months and _consecutive(months)
    return EvidenceWindow(months=months, first=months[0] if months else None,
                         last=months[-1] if months else None, count=len(months), full_annual_cycle=full)


def read_report(path: Path) -> tuple[Optional[str], list[dict]]:
    month = month_from_filename(path)
    if month is None:
        return None, []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return month, []
    keys = {str(k).strip(): k for k in rows[0]}
    if COL["units"] not in keys or COL["barcode"] not in keys:
        return month, []
    out = []
    for row in rows:
        barcode = norm_barcode(row.get(keys[COL["barcode"]]))
        if not barcode:
            continue
        units = _num(row.get(keys[COL["units"]]))
        price = _num(row.get(keys.get(COL["price"], "")))
        out.append({"barcode": barcode, "month": month,
                    "product_name": str(row.get(keys.get(COL["name"], ""), "") or "").strip(),
                    "units": units, "receipts": _num(row.get(keys.get(COL["receipts"], ""))),
                    "revenue": units * price, "cost_price": _num(row.get(keys.get(COL["cost"], ""))),
                    "selling_price": price, "_source_file": path.name})
    return month, out


MONTHLY_SCHEMA = pa.schema([("barcode", pa.string()), ("month", pa.string()), ("product_name", pa.string()),
                            ("units", pa.float64()), ("receipts", pa.float64()), ("revenue", pa.float64()),
                            ("cost_price", pa.float64()), ("selling_price", pa.float64()),
                            ("_imported_at", pa.string()), ("_source_file", pa.string())])
SUMMARY_SCHEMA = pa.schema([("barcode", pa.string()), ("product_name", pa.string()), ("months_present", pa.int64()),
                            ("units_total", pa.float64()), ("receipts_total", pa.float64()),
                            ("last_month_with_units", pa.string()), ("observed_zero", pa.bool_()),
                            ("reconcile_units", pa.float64()), ("reconcile_receipts", pa.float64()),
                            ("reconcile_months", pa.int64()), ("_imported_at", pa.string())])


def import_sales(directory: Path, *, inventory_as_of: Optional[date], full_cycle_months: int = 12,
                 silver_dir: Path = SILVER_POS_ROOT, imported_at: Optional[str] = None) -> dict:
    imported_at = imported_at or datetime.now(timezone.utc).isoformat()
    monthly: list[dict] = []
    months: list[str] = []
    for path in sorted(directory.glob("*.csv")):
        month, rows = read_report(path)
        if month is None or not rows:
            continue
        months.append(month)
        monthly.extend(rows)
    if not months:
        return {"window": None, "monthly_rows": 0, "products": 0, "reconcile_before": None}

    window = evidence_window(months, full_cycle_months)
    reconcile_before = f"{inventory_as_of.year}-{inventory_as_of.month:02d}" if inventory_as_of else None
    windowed = reconcile_before is not None

    by_barcode: dict[str, list[dict]] = defaultdict(list)
    for row in monthly:
        by_barcode[row["barcode"]].append(row)
    summary = []
    for barcode in sorted(by_barcode):
        rows = sorted(by_barcode[barcode], key=lambda r: r["month"])
        with_units = [r["month"] for r in rows if r["units"] > 0]
        in_window = [r for r in rows if reconcile_before is None or r["month"] < reconcile_before]
        summary.append({
            "barcode": barcode, "product_name": rows[-1]["product_name"], "months_present": len(rows),
            "units_total": sum(r["units"] for r in rows), "receipts_total": sum(r["receipts"] for r in rows),
            "last_month_with_units": max(with_units) if with_units else None,
            "observed_zero": any(r["units"] == 0 for r in rows),
            # None, not a full-history sum. `reconcile_before is None` means the stock
            # count's date is unknown, and a window nobody chose is not a window: sales
            # after the count cannot explain a shortfall observed at the count, so
            # including them answers a different question than the one reconciliation
            # asks. Measured against the real seven reports, treating unknown as "every
            # month" flagged 443 products where the true vintage flags 360 — 117
            # invented, 34 genuine ones lost, 100 more carrying a different figure.
            # Rule 8, in the engine: a number that cannot be stated honestly is not
            # stated. The fields are nullable in SUMMARY_SCHEMA already.
            "reconcile_units": sum(r["units"] for r in in_window) if windowed else None,
            "reconcile_receipts": sum(r["receipts"] for r in in_window) if windowed else None,
            "reconcile_months": len(in_window) if windowed else None,
            "_imported_at": imported_at,
        })

    silver_dir.mkdir(parents=True, exist_ok=True)
    for row in monthly:
        row["_imported_at"] = imported_at
    pq.write_table(pa.Table.from_pylist(sorted(monthly, key=lambda r: (r["barcode"], r["month"])), schema=MONTHLY_SCHEMA),
                   silver_dir / "sales_monthly.parquet", compression="snappy")
    pq.write_table(pa.Table.from_pylist(summary, schema=SUMMARY_SCHEMA),
                   silver_dir / "sales_summary.parquet", compression="snappy")
    return {"window": window.to_dict(), "monthly_rows": len(monthly), "products": len(summary),
            "reconcile_before": reconcile_before}
