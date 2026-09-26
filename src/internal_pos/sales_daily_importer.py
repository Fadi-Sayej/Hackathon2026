# src/internal_pos/sales_daily_importer.py
"""Daily sales reports → day-grained evidence for F8 (ADR-030, F8-S1 FR-143).

The same POS sales report as the monthly one, «דוח מכירות», run for a single day. The day
comes from the FILE NAME, `דוח מכירות יום YYYY-MM-DD.csv`, because the report carries no date.

Three things differ from the monthly importer, each on purpose:

- **A blank or unparseable cell is null, never 0.** The monthly `_num` reads both as 0.0.
  Here that would be a day of no sales, or of no deliveries, that nobody reported (INV-071).
- **A file without `כניסות מלאי` has null receipts throughout,** and its day is recorded as
  `deliveries_reported: false`. A stock count cannot be carried across such a day (FR-149).
- **A file that yields nothing is a failed file, and its day is missing** (INV-072): a name
  with no ISO day, bytes that are not UTF-8, a missing column, or no product line at all. A
  header with no lines is how a closed day would arrive, and a closed day is a missing day
  (F8-S1 §12), not a day on which nothing sold.

A product absent from a day's file gets no row (ADR-011). The report lists only products
that sold, so for such a product-day the deliveries are unknown, not zero (ADR-030 §2).
"""
from __future__ import annotations

import csv
import math
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

from src.common.paths import SILVER_POS_ROOT
from src.engine.model import norm_barcode
from src.internal_pos.sales_importer import COL, _collapse_reprinted

DAY_NAME = re.compile(r"דוח מכירות יום\s+(\d{4}-\d{2}-\d{2})")
OUTPUT = "sales_daily.parquet"

DAILY_SCHEMA = pa.schema([("barcode", pa.string()), ("day", pa.string()),
                          ("units", pa.float64()), ("receipts", pa.float64())])


def _cell(value) -> Optional[float]:
    """A number as printed, or None. Never a 0 standing in for a blank."""
    text = str(value if value is not None else "").replace(",", "").strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def day_from_filename(path: Path) -> Optional[str]:
    """The ISO day in `דוח מכירות יום YYYY-MM-DD.csv`, or None if the name does not give one."""
    match = DAY_NAME.fullmatch(unicodedata.normalize("NFC", path.stem).strip())
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1)).isoformat()
    except ValueError:
        return None


class _Failed(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def read_daily_report(path: Path, day: str) -> tuple[list[dict], bool]:
    """One day's lines, and whether the file reports deliveries. Raises _Failed."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames or []
            lines = list(reader)
    except (UnicodeDecodeError, csv.Error):
        raise _Failed("unreadable")
    keys = {str(k).strip(): k for k in header if k is not None}
    if COL["units"] not in keys or COL["barcode"] not in keys:
        raise _Failed("missing_columns")
    deliveries_reported = COL["receipts"] in keys
    rows = []
    for line in lines:
        barcode = norm_barcode(line.get(keys[COL["barcode"]]))
        if not barcode:
            continue
        rows.append({
            "barcode": barcode, "day": day,
            "units": _cell(line.get(keys[COL["units"]])),
            "receipts": _cell(line.get(keys[COL["receipts"]])) if deliveries_reported else None,
            # Read only so the monthly importer's reprint rule can compare lines (#156).
            "selling_price": _cell(line.get(keys[COL["price"]])) if COL["price"] in keys else None,
            "cost_price": _cell(line.get(keys[COL["cost"]])) if COL["cost"] in keys else None,
        })
    if not rows:
        raise _Failed("no_product_lines")
    return rows, deliveries_reported


def import_sales_daily(directory: Path, *, silver_dir: Path = SILVER_POS_ROOT) -> dict:
    """Every daily report in `directory`, as printed, to `silver_dir/sales_daily.parquet`.

    Returns what arrived: the report days, the files that failed and why, whether each report
    day carries deliveries, and how many reprinted barcodes were collapsed or kept as printed.
    It knows nothing of the evidence window or freshness: those are policy (ADR-030 §6).

    When no report day parsed, no table is written and an older one is removed. A table left
    from an earlier run would read as evidence that arrived.
    """
    directory, silver_dir = Path(directory), Path(silver_dir)
    rows: list[dict] = []
    report_days: list[str] = []
    failed: list[dict] = []
    deliveries: dict[str, bool] = {}
    collapsed = kept = 0
    for path in sorted(directory.glob("*.csv")) if directory.is_dir() else []:
        day = day_from_filename(path)
        if day is None:
            failed.append({"file": path.name, "reason": "no_day_in_name"})
            continue
        try:
            lines, deliveries_reported = read_daily_report(path, day)
        except _Failed as err:
            failed.append({"file": path.name, "reason": err.reason})
            continue
        lines, n_collapsed, n_kept = _collapse_reprinted(lines)
        collapsed += n_collapsed
        kept += n_kept
        report_days.append(day)
        deliveries[day] = deliveries_reported
        rows.extend(lines)

    target = silver_dir / OUTPUT
    if report_days:
        silver_dir.mkdir(parents=True, exist_ok=True)
        table = [{k: r[k] for k in DAILY_SCHEMA.names} for r in sorted(rows, key=lambda r: (r["barcode"], r["day"]))]
        pq.write_table(pa.Table.from_pylist(table, schema=DAILY_SCHEMA), target, compression="snappy")
    elif target.exists():
        target.unlink()

    report_days.sort()
    return {"report_days": report_days, "failed_files": failed,
            "deliveries_reported": {d: deliveries[d] for d in report_days},
            "reprinted": {"collapsed": collapsed, "kept": kept}}
