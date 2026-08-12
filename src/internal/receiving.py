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
id is a grouping key, not a uniqueness constraint, and both rows are kept.
Re-import protection is a whole-row comparison instead (see _row_identity);
deduplicating on receipt_id would throw away one of those two real deliveries.
"""

from __future__ import annotations

import csv
import hashlib
import statistics
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


def build_receipt_record(
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
) -> dict[str, Any]:
    """Validate and normalize one delivery line without writing it.

    Split out of add_receipt so import_receiving_csv can decide whether a row is
    already in the ledger BEFORE appending it. The comparison has to happen on
    the normalized record, not on the raw CSV text: '10/08/2026' and
    '2026-08-10' are the same delivery day, and only this function knows that.
    """
    clean_barcode = _require_barcode(barcode)
    clean_quantity = _require_quantity(quantity)
    clean_supplier = _require_supplier(supplier)
    cost = _optional_cost(unit_cost)
    expiry = _optional_date(expiry_date)

    received = _optional_date(received_at) or _now().date()
    recorded = _clean(recorded_at) or _now().isoformat()

    return {
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


def append_receipt_record(record: dict[str, Any], path: Path = RECEIPTS_CSV) -> dict[str, Any]:
    """Write one already-validated record to the end of the ledger."""
    ensure_receipts_csv(path)
    with path.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=RECEIVING_COLUMNS).writerow(record)
    return record


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
    record = build_receipt_record(
        barcode=barcode,
        quantity=quantity,
        supplier=supplier,
        received_at=received_at,
        unit_cost=unit_cost,
        expiry_date=expiry_date,
        product_name=product_name,
        source=source,
        recorded_at=recorded_at,
    )
    return append_receipt_record(record, path)


def _row_identity(row: dict[str, Any], with_recorded_at: bool = True) -> tuple:
    """Every column of a row as written, for duplicate detection.

    NOT receipt_id: that hashes only (barcode, received_at, supplier) and
    deliberately collides for two genuine same-day deliveries of the same
    barcode from the same supplier. Those differ in quantity, in cost, or at
    minimum in recorded_at — the per-line timestamp the capture form stamps —
    so the whole row is what tells a real second delivery apart from the same
    delivery imported twice.
    """
    columns = [column for column in RECEIVING_COLUMNS if column != "recorded_at"]
    if with_recorded_at:
        columns.append("recorded_at")
    return tuple(_clean(row.get(column)) for column in columns)


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
    """Load a CSV exported by the capture form, skipping rows already in the ledger.

    The ledger is append-only and git-ignored, so a CSV imported twice used to
    double every quantity it contained with nothing to undo it. A row is skipped
    when the whole normalized row already exists (see _row_identity) — not when
    receipt_id matches, because receipt_id collides for two genuine same-day
    deliveries and skipping on it would silently drop a real one.

    One case cannot be resolved by the data: a row whose recorded_at is blank
    has no per-line timestamp to tell it apart, so it is compared on its other
    columns. Two truly identical, same-day, same-quantity deliveries hand-typed
    into a CSV with no recorded_at will therefore see the second skipped. It is
    reported in skipped_preview rather than dropped quietly, and every CSV the
    capture form exports carries recorded_at.

    Bad rows are still reported, never silently dropped.
    """
    ensure_receipts_csv(path)
    imported = 0
    rejected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    existing = load_receipts(path)
    seen_full = {_row_identity(row) for row in existing}
    seen_loose = {_row_identity(row, with_recorded_at=False) for row in existing}

    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            try:
                record = build_receipt_record(
                    barcode=row.get("barcode", ""),
                    quantity=row.get("quantity", ""),
                    supplier=row.get("supplier", ""),
                    received_at=row.get("received_at") or None,
                    unit_cost=row.get("unit_cost") or None,
                    expiry_date=row.get("expiry_date") or None,
                    product_name=row.get("product_name") or None,
                    source=row.get("source") or source,
                    recorded_at=row.get("recorded_at") or None,
                )
            except Exception as exc:
                rejected.append({"row_number": row_number, "error": str(exc), "row": row})
                continue

            has_recorded_at = bool(_clean(row.get("recorded_at")))
            identity = _row_identity(record, with_recorded_at=has_recorded_at)
            if identity in (seen_full if has_recorded_at else seen_loose):
                skipped.append(
                    {
                        "row_number": row_number,
                        "receipt_id": record["receipt_id"],
                        "reason": "already in the ledger",
                        "row": row,
                    }
                )
                continue

            append_receipt_record(record, path)
            seen_full.add(_row_identity(record))
            seen_loose.add(_row_identity(record, with_recorded_at=False))
            imported += 1

    return {
        "status": "ok",
        "input_path": str(input_path),
        "receipts_csv": str(path),
        "imported_rows": imported,
        "rejected_rows": len(rejected),
        "rejected_preview": rejected[:20],
        "skipped_duplicates": len(skipped),
        "skipped_preview": skipped[:20],
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


def _parse_delivery_row(
    row: dict[str, Any], require_barcode: bool = False
) -> tuple[str, str, date] | None:
    """Clean and parse one receipt row into (barcode, supplier, received date).

    Shared by supplier_lead_times and barcode_supplier_map so the skip rules —
    which fields are required, and what counts as an unparseable date — live
    in exactly one place. A blank barcode still counts as a delivery for
    lead-time purposes (a supplier and a date are enough to place it in the
    calendar), but barcode_supplier_map has nothing to key on without one;
    require_barcode lets each caller ask for the guard it actually needs
    instead of duplicating the parsing around it.
    """
    barcode = _clean(row.get("barcode"))
    supplier = _clean(row.get("supplier"))
    raw_day = _clean(row.get("received_at"))
    if not supplier or not raw_day:
        return None
    if require_barcode and not barcode:
        return None
    try:
        day = _parse_date(raw_day)
    except ValueError:
        return None
    return barcode, supplier, day


def supplier_lead_times(receipts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Median days between consecutive deliveries, per supplier.

    Returns {supplier: {median_days, n_observations, confidence}}.

    n_observations counts distinct delivery DATES, not receipt lines: twenty
    items off one delivery note is one delivery. Below
    MIN_DELIVERIES_FOR_LEAD_TIME, median_days is None and the caller must keep
    its default — a median of two observations is not a measurement.
    """
    days_by_supplier: dict[str, set] = {}
    for row in receipts:
        parsed = _parse_delivery_row(row)
        if parsed is None:
            continue
        _, supplier, day = parsed
        days_by_supplier.setdefault(supplier, set()).add(day)

    result: dict[str, dict[str, Any]] = {}
    for supplier, days in days_by_supplier.items():
        ordered = sorted(days)
        count = len(ordered)
        if count < MIN_DELIVERIES_FOR_LEAD_TIME:
            result[supplier] = {
                "median_days": None,
                "n_observations": count,
                "confidence": "low",
            }
            continue
        gaps = [(later - earlier).days for earlier, later in zip(ordered, ordered[1:])]
        result[supplier] = {
            "median_days": statistics.median(gaps),
            "n_observations": count,
            "confidence": "high" if count >= 6 else "medium",
        }
    return result


def barcode_supplier_map(receipts: list[dict[str, Any]]) -> dict[str, str]:
    """Barcode -> the supplier of that barcode's most recent delivery.

    Products carry supplier 'YomYom' for all 7,674 rows because the POS export
    has no supplier column. The ledger is the first place a real supplier per
    product is ever observed.
    """
    latest: dict[str, tuple] = {}
    for row in receipts:
        parsed = _parse_delivery_row(row, require_barcode=True)
        if parsed is None:
            continue
        barcode, supplier, day = parsed
        # Ties go to the later ledger row: the ledger is append-only, so when
        # two deliveries for the same barcode land on the same date, the one
        # that appears later in the file is the more recent entry.
        if barcode not in latest or day >= latest[barcode][0]:
            latest[barcode] = (day, supplier)
    return {barcode: supplier for barcode, (_, supplier) in latest.items()}
