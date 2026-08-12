"""
receiving.py — the receiving ledger.

The POS records what was sold. It never records what arrived, which leaves the
inventory identity missing a whole term:

    stock_now = opening + received - sold
                          ^^^^^^^^

This module is the only place that term is captured. The file is append-only:
a delivery that happened is a fact, and facts are not edited in place.

`receipt_id` is a stable hash of (barcode, received_at, supplier) exactly as
specified in issue #52. Two separate deliveries of the same barcode from the
same supplier on the same day therefore share an id. That is intentional — the
id is a stable key for re-import, not a uniqueness constraint, and both rows
are kept.
"""

from __future__ import annotations

import csv
import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.common.paths import RECEIPTS_CSV
# parse_expiry_date is a general date parser (ISO, DD/MM/YYYY, DD-MM-YYYY,
# DD.MM.YYYY) that happens to live in the expiry module. Reused rather than
# duplicated. The dependency runs one way only: expiry_tracking must never
# import this module at module scope.
from src.expiry.expiry_tracking import parse_expiry_date as _parse_date

RECEIVING_COLUMNS = [
    "receipt_id",
    "barcode",
    "product_name",
    "quantity",
    "supplier",
    "unit_cost",
    "received_at",
    "expiry_date",
    "recorded_at",
    "source",
]

# A median over fewer than three deliveries is not a measurement, it is a guess
# with a decimal point. Below this we keep the default and say so.
MIN_DELIVERIES_FOR_LEAD_TIME = 3
DEFAULT_LEAD_TIME_DAYS = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _require_barcode(value: Any) -> str:
    barcode = _clean(value)
    if not barcode:
        raise ValueError("barcode is required")
    return barcode


def _require_quantity(value: Any) -> int:
    try:
        quantity = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"quantity must be a whole number, got {value!r}") from None
    if quantity <= 0:
        raise ValueError(f"quantity must be greater than zero, got {quantity}")
    return quantity


def _require_supplier(value: Any) -> str:
    supplier = _clean(value)
    if not supplier:
        raise ValueError("supplier is required")
    return supplier


def _optional_cost(value: Any) -> Optional[float]:
    text = _clean(value)
    if not text:
        return None
    try:
        cost = float(text)
    except ValueError:
        raise ValueError(f"unit_cost must be a number, got {value!r}") from None
    if cost < 0:
        raise ValueError(f"unit_cost must not be negative, got {cost}")
    return cost


def _optional_date(value: Any) -> Optional[date]:
    text = _clean(value)
    if not text:
        return None
    return _parse_date(text)


def make_receipt_id(barcode: str, received_at: date, supplier: str) -> str:
    key = f"{barcode}|{received_at.isoformat()}|{supplier}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def ensure_receipts_csv(path: Path = RECEIPTS_CSV) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=RECEIVING_COLUMNS).writeheader()
    return path


def add_receipt(
    *,
    barcode: str,
    quantity: Any,
    supplier: str,
    received_at: Any = None,
    unit_cost: Any = None,
    expiry_date: Any = None,
    product_name: Any = None,
    source: str = "manual_ui",
    recorded_at: Any = None,
    path: Path = RECEIPTS_CSV,
) -> dict[str, Any]:
    """Append one delivery line. Raises ValueError on any invalid required field."""
    clean_barcode = _require_barcode(barcode)
    clean_quantity = _require_quantity(quantity)
    clean_supplier = _require_supplier(supplier)
    cost = _optional_cost(unit_cost)
    expiry = _optional_date(expiry_date)

    received = _optional_date(received_at) or _now().date()
    recorded = _clean(recorded_at) or _now().isoformat()

    record = {
        "receipt_id": make_receipt_id(clean_barcode, received, clean_supplier),
        "barcode": clean_barcode,
        "product_name": _clean(product_name),
        "quantity": clean_quantity,
        "supplier": clean_supplier,
        "unit_cost": cost if cost is not None else "",
        "received_at": received.isoformat(),
        "expiry_date": expiry.isoformat() if expiry else "",
        "recorded_at": recorded,
        "source": source,
    }

    ensure_receipts_csv(path)
    with path.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=RECEIVING_COLUMNS).writerow(record)
    return record


def load_receipts(path: Path = RECEIPTS_CSV) -> list[dict[str, Any]]:
    """Every ledger row as written. Missing file reads as an empty ledger."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def import_receiving_csv(
    input_path: Path,
    path: Path = RECEIPTS_CSV,
    source: str = "csv_import",
) -> dict[str, Any]:
    """Load a CSV exported by the capture form. Bad rows are reported, not silently dropped."""
    ensure_receipts_csv(path)
    imported = 0
    rejected: list[dict[str, Any]] = []

    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            try:
                add_receipt(
                    barcode=row.get("barcode", ""),
                    quantity=row.get("quantity", ""),
                    supplier=row.get("supplier", ""),
                    received_at=row.get("received_at") or None,
                    unit_cost=row.get("unit_cost") or None,
                    expiry_date=row.get("expiry_date") or None,
                    product_name=row.get("product_name") or None,
                    source=row.get("source") or source,
                    recorded_at=row.get("recorded_at") or None,
                    path=path,
                )
                imported += 1
            except Exception as exc:
                rejected.append({"row_number": row_number, "error": str(exc), "row": row})

    return {
        "status": "ok",
        "input_path": str(input_path),
        "receipts_csv": str(path),
        "imported_rows": imported,
        "rejected_rows": len(rejected),
        "rejected_preview": rejected[:20],
    }


def receipts_as_expiry_scans(path: Path = RECEIPTS_CSV) -> list[dict[str, Any]]:
    """Receipts that carry an expiry date, in the expiry-scan shape.

    A delivery with a date on the package is an expiry observation. Rather than
    forking the bucketing and severity logic in expiry_tracking, we translate
    into the shape that module already reads.
    """
    scans: list[dict[str, Any]] = []
    for row in load_receipts(path):
        expiry = _clean(row.get("expiry_date"))
        barcode = _clean(row.get("barcode"))
        if not expiry or not barcode:
            continue
        scans.append(
            {
                "scan_id": _clean(row.get("receipt_id")),
                "barcode": barcode,
                "expiry_date": expiry,
                "scanned_at": _clean(row.get("recorded_at")),
                "source": f"receiving:{_clean(row.get('source')) or 'unknown'}",
                "notes": (
                    f"received {_clean(row.get('quantity'))} units "
                    f"from {_clean(row.get('supplier'))} "
                    f"on {_clean(row.get('received_at'))}"
                ),
            }
        )
    return scans
