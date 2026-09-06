from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from src.common.paths import EXPIRY_SCANS_CSV, PROJECT_ROOT, SIGNALS_ROOT, SILVER_POS_ROOT


EXPIRY_SIGNALS_DIR = SIGNALS_ROOT / "expiry"
EXPIRY_REPORTS_DIR = PROJECT_ROOT / "reports" / "expiry"

CSV_COLUMNS = ["scan_id", "barcode", "expiry_date", "scanned_at", "source", "notes"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_barcode(value: str) -> str:
    return str(value or "").strip()


def parse_expiry_date(value: str) -> date:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("expiry_date is required")

    formats = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y")
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    raise ValueError(
        f"Unsupported expiry date {value!r}. Use YYYY-MM-DD or DD/MM/YYYY."
    )


def _parse_scanned_at(value: str | None) -> datetime:
    if not value:
        return _now()
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _scan_id(barcode: str, expiry_date: date, scanned_at: datetime) -> str:
    key = f"{barcode}|{expiry_date.isoformat()}|{scanned_at.isoformat()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def ensure_expiry_csv(path: Path = EXPIRY_SCANS_CSV) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            writer.writeheader()
    return path


def add_expiry_scan(
    *,
    barcode: str,
    expiry_date: str,
    scanned_at: str | None = None,
    source: str = "manual_expiry_scan",
    notes: str = "",
    path: Path = EXPIRY_SCANS_CSV,
) -> dict[str, Any]:
    clean_barcode = _normalize_barcode(barcode)
    if not clean_barcode:
        raise ValueError("barcode is required")

    expiry = parse_expiry_date(expiry_date)
    scanned_dt = _parse_scanned_at(scanned_at)
    record = {
        "scan_id": _scan_id(clean_barcode, expiry, scanned_dt),
        "barcode": clean_barcode,
        "expiry_date": expiry.isoformat(),
        "scanned_at": scanned_dt.isoformat(),
        "source": source,
        "notes": notes or "",
    }

    ensure_expiry_csv(path)
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writerow(record)
    return record


def import_expiry_csv(
    input_path: Path,
    path: Path = EXPIRY_SCANS_CSV,
    source: str = "manual_expiry_csv",
) -> dict[str, Any]:
    ensure_expiry_csv(path)
    imported = 0
    rejected: list[dict[str, Any]] = []

    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            try:
                add_expiry_scan(
                    barcode=row.get("barcode", ""),
                    expiry_date=row.get("expiry_date", ""),
                    scanned_at=row.get("scanned_at") or None,
                    source=row.get("source") or source,
                    notes=row.get("notes") or "",
                    path=path,
                )
                imported += 1
            except Exception as exc:
                rejected.append(
                    {
                        "row_number": row_number,
                        "error": str(exc),
                        "row": row,
                    }
                )

    return {
        "status": "ok",
        "input_path": str(input_path),
        "expiry_csv": str(path),
        "imported_rows": imported,
        "rejected_rows": len(rejected),
        "rejected_preview": rejected[:20],
    }


def load_expiry_scans(path: Path = EXPIRY_SCANS_CSV) -> list[dict[str, Any]]:
    ensure_expiry_csv(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _read_parquet_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return pq.read_table(path).to_pylist()


def _pos_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    products = _read_parquet_rows(SILVER_POS_ROOT / "yomyom_products.parquet")
    inventory = _read_parquet_rows(SILVER_POS_ROOT / "yomyom_inventory.parquet")

    product_by_barcode: dict[str, dict[str, Any]] = {}
    inventory_by_barcode: dict[str, dict[str, Any]] = {}

    for row in products:
        barcode = _normalize_barcode(row.get("barcode"))
        if barcode:
            product_by_barcode.setdefault(barcode, row)
    for row in inventory:
        barcode = _normalize_barcode(row.get("barcode"))
        if barcode:
            inventory_by_barcode.setdefault(barcode, row)

    return product_by_barcode, inventory_by_barcode


def _severity(days_to_expiry: int) -> str:
    if days_to_expiry < 0:
        return "expired"
    if days_to_expiry <= 7:
        return "critical_7d"
    if days_to_expiry <= 14:
        return "warning_14d"
    if days_to_expiry <= 30:
        return "upcoming_30d"
    return "later"


def _recommended_action(severity: str, current_stock: Any) -> str:
    stock = current_stock if isinstance(current_stock, int | float) else None
    if severity == "expired":
        return "Remove from shelf and verify disposal/return."
    if severity == "critical_7d":
        if stock is not None and stock > 0:
            return "Move forward, discount, or bundle this week."
        return "Verify stock count before action."
    if severity == "warning_14d":
        return "Prioritize shelf placement and monitor."
    if severity == "upcoming_30d":
        return "Keep visible and avoid over-ordering."
    return "No urgent expiry action."


def build_expiry_report(
    *,
    as_of: str | None = None,
    path: Path = EXPIRY_SCANS_CSV,
) -> dict[str, Any]:
    as_of_date = parse_expiry_date(as_of) if as_of else _now().date()
    generated_at = _now()
    ts = generated_at.strftime("%Y%m%dT%H%M%SZ")

    product_by_barcode, inventory_by_barcode = _pos_indexes()
    scans = load_expiry_scans(path)

    alerts: list[dict[str, Any]] = []
    for scan in scans:
        barcode = _normalize_barcode(scan.get("barcode"))
        if not barcode:
            continue

        expiry = parse_expiry_date(scan.get("expiry_date", ""))
        days = (expiry - as_of_date).days
        product = product_by_barcode.get(barcode, {})
        inventory = inventory_by_barcode.get(barcode, {})
        current_stock = inventory.get("current_stock")
        severity = _severity(days)

        alerts.append(
            {
                "scan_id": scan.get("scan_id"),
                "barcode": barcode,
                "expiry_date": expiry.isoformat(),
                "scanned_at": scan.get("scanned_at"),
                "days_to_expiry": days,
                "severity": severity,
                "known_in_pos": bool(product),
                "product_name": product.get("product_name"),
                "category": product.get("category"),
                "current_stock": current_stock,
                "selling_price": product.get("selling_price"),
                "wolt_price": product.get("wolt_price"),
                "cost_price": product.get("cost_price"),
                "recommended_action": _recommended_action(severity, current_stock),
                "notes": scan.get("notes") or "",
            }
        )

    severity_order = {
        "expired": 0,
        "critical_7d": 1,
        "warning_14d": 2,
        "upcoming_30d": 3,
        "later": 4,
    }
    alerts.sort(key=lambda row: (severity_order[row["severity"]], row["days_to_expiry"], row["barcode"]))

    summary = {
        "total_scans": len(scans),
        "total_alerts": len(alerts),
        "known_in_pos": sum(1 for row in alerts if row["known_in_pos"]),
        "unknown_in_pos": sum(1 for row in alerts if not row["known_in_pos"]),
        "expired": sum(1 for row in alerts if row["severity"] == "expired"),
        "critical_7d": sum(1 for row in alerts if row["severity"] == "critical_7d"),
        "warning_14d": sum(1 for row in alerts if row["severity"] == "warning_14d"),
        "upcoming_30d": sum(1 for row in alerts if row["severity"] == "upcoming_30d"),
        "later": sum(1 for row in alerts if row["severity"] == "later"),
    }

    EXPIRY_SIGNALS_DIR.mkdir(parents=True, exist_ok=True)
    EXPIRY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    parquet_path = EXPIRY_SIGNALS_DIR / f"expiry_alerts_{ts}.parquet"
    json_path = EXPIRY_REPORTS_DIR / f"expiry_report_{ts}.json"
    md_path = EXPIRY_REPORTS_DIR / f"expiry_report_{ts}.md"

    table = pa.Table.from_pylist(alerts) if alerts else pa.table({})
    pq.write_table(table, parquet_path, compression="snappy")

    report = {
        "status": "ok",
        "generated_at": generated_at.isoformat(),
        "as_of": as_of_date.isoformat(),
        "expiry_csv": str(path),
        "parquet_path": str(parquet_path),
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "summary": summary,
        "alerts_preview": alerts[:20],
    }
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_markdown_report(report, alerts), encoding="utf-8")

    try:
        from src.common.source_status import update_source

        update_source(
            "expiry_scans",
            status="complete" if scans else "not_started",
            row_count=len(scans),
        )
    except Exception:  # status tracking must never break the report
        pass

    return report


def _build_markdown_report(report: dict[str, Any], alerts: list[dict[str, Any]]) -> str:
    summary = report["summary"]
    lines = [
        "# Expiry Tracking Report",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- As of: {report['as_of']}",
        f"- Total scans: {summary['total_scans']}",
        f"- Known in POS: {summary['known_in_pos']}",
        f"- Unknown in POS: {summary['unknown_in_pos']}",
        "",
        "## Buckets",
        "",
        f"- Expired: {summary['expired']}",
        f"- Critical 0-7 days: {summary['critical_7d']}",
        f"- Warning 8-14 days: {summary['warning_14d']}",
        f"- Upcoming 15-30 days: {summary['upcoming_30d']}",
        f"- Later: {summary['later']}",
        "",
        "## Priority Items",
        "",
    ]

    priority = [row for row in alerts if row["severity"] != "later"][:30]
    if not priority:
        lines.append("- No urgent expiry items recorded yet.")
    for row in priority:
        name = row["product_name"] or "UNKNOWN POS PRODUCT"
        lines.append(
            "- "
            f"{row['severity']} | {row['barcode']} | {name} | "
            f"expiry={row['expiry_date']} | days={row['days_to_expiry']} | "
            f"stock={row['current_stock']} | action={row['recommended_action']}"
        )

    unknown = [row for row in alerts if not row["known_in_pos"]]
    if unknown:
        lines.extend(["", "## Unknown Barcodes", ""])
        for row in unknown[:30]:
            lines.append(f"- {row['barcode']} | expiry={row['expiry_date']}")

    return "\n".join(lines) + "\n"
