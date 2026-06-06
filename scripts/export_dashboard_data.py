"""
export_dashboard_data.py — bridge the Python pipeline outputs into the React dashboard.

Reads the latest operational recommendations + POS silver tables and writes a single
JSON file the static Vite frontend can `fetch()` from `public/data/operational.json`.

Designed to be re-run safely at any time, including while competitor scraping is still
in progress: every input is optional and missing data degrades to empty arrays / zero
counts rather than failing. Re-run after each pipeline refresh to update the dashboard.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pyarrow.parquet as pq

from src.common.paths import (
    EXTERNAL_SILVER_ROOT,
    RECOMMENDATIONS_ROOT,
    SIGNALS_ROOT,
    SILVER_POS_ROOT,
)
from src.common.source_status import load_sources, update_source, write_summary
from src.recommendations.operational_recommendations import generate_operational_recommendations

PUBLIC_DATA_DIR = ROOT / "public" / "data"
OPERATIONAL_DIR = RECOMMENDATIONS_ROOT / "operational_recommendations"
COMPETITOR_DIR = SIGNALS_ROOT / "competitor_product_signals"
KAGGLE_SILVER_DIR = EXTERNAL_SILVER_ROOT / "products"
PRODUCT_RECS_DIR = RECOMMENDATIONS_ROOT / "product_recommendations"
EXPIRY_SIGNALS_DIR = SIGNALS_ROOT / "expiry"

EXPIRY_BUCKETS = ("expired", "critical_7d", "warning_14d", "upcoming_30d", "later")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    return pq.read_table(path).to_pylist()


def _latest(root: Path, pattern: str) -> Path | None:
    if not root.exists():
        return None
    files = sorted(root.rglob(pattern), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _pos_health(products: list[dict], inventory: list[dict], margins: list[dict]) -> dict[str, Any]:
    total = len(products)
    missing_barcode = sum(1 for p in products if not p.get("barcode"))
    zero_price = sum(1 for p in products if not p.get("selling_price"))
    zero_cost = sum(1 for p in products if not p.get("cost_price"))
    negative_stock = sum(1 for r in inventory if (_num(r.get("current_stock")) or 0) < 0)

    wolt_gap = 0
    for p in products:
        sell = _num(p.get("selling_price"))
        wolt = _num(p.get("wolt_price"))
        if sell and wolt and sell > 0 and abs(wolt - sell) / sell * 100.0 >= 5.0:
            wolt_gap += 1

    margin_risk = 0
    for m in margins:
        sell = _num(m.get("selling_price"))
        cost = _num(m.get("cost_price"))
        if sell and sell > 0 and cost is not None and (sell - cost) / sell * 100.0 <= 10.0:
            margin_risk += 1

    source_file = products[0].get("_source_file") if products else None
    return {
        "totalProducts": total,
        "missingBarcode": missing_barcode,
        "zeroPrice": zero_price,
        "zeroCost": zero_cost,
        "negativeStock": negative_stock,
        "woltPriceGaps": wolt_gap,
        "marginRisks": margin_risk,
        "sourceFile": source_file,
    }


def _map_recommendation(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("recommendation_id"),
        "family": row.get("recommendation_family"),
        "type": row.get("recommendation_type"),
        "barcode": row.get("barcode"),
        "productName": row.get("product_name"),
        "category": row.get("category"),
        "confidence": row.get("confidence"),
        "reason": row.get("reason"),
        "severity": row.get("severity"),
        "metricValue": row.get("metric_value"),
        "sellingPrice": row.get("selling_price"),
        "woltPrice": row.get("wolt_price"),
        "costPrice": row.get("cost_price"),
        "currentStock": row.get("current_stock"),
        "marginPct": row.get("margin_pct"),
        "daysToExpiry": row.get("days_to_expiry"),
        "expiryDate": row.get("expiry_date"),
    }


def _map_competitor_recommendation(row: dict[str, Any]) -> dict[str, Any]:
    """Map a competitor (product_recommendations.py) row to the shared UI schema."""
    return {
        "id": row.get("recommendation_id"),
        "family": "competitor",
        "type": row.get("recommendation_type"),
        "barcode": row.get("barcode"),
        "productName": row.get("product_name"),
        "category": row.get("category"),
        "confidence": row.get("confidence"),
        "reason": row.get("reason"),
        "severity": None,
        "metricValue": row.get("competitor_price"),
        "sellingPrice": row.get("local_price"),
        "woltPrice": None,
        "costPrice": None,
        "currentStock": row.get("current_stock"),
        "marginPct": row.get("margin_pct"),
        "daysToExpiry": None,
        "expiryDate": None,
        "competitorPrice": row.get("competitor_price"),
        "competitorBarcode": row.get("competitor_barcode"),
    }


def _count_parquet_rows(files: list[Path]) -> int:
    rows = 0
    for f in files:
        try:
            rows += pq.read_table(f).num_rows
        except Exception:
            pass
    return rows


def _reconcile_sources_from_disk(products: list[dict]) -> None:
    """Keep sources.json honest by inspecting on-disk artifacts for each source.

    Producers update their own status when they run (POS import, expiry, competitor
    signals), but this disk reconcile reflects data that already exists even before
    those producers re-run — and covers Person B's Kaggle output, which we don't edit.
    """
    disk_sources: dict[str, list[Path]] = {
        "kaggle_dor_alon": list((KAGGLE_SILVER_DIR / "kaggle_dor_alon").rglob("*.parquet")),
        "kaggle_rami_levy": list((KAGGLE_SILVER_DIR / "kaggle_rami_levy").rglob("*.parquet")),
        "kaggle_shufersal": list((KAGGLE_SILVER_DIR / "kaggle_shufersal").rglob("*.parquet")),
        "wolt_delivery": list((KAGGLE_SILVER_DIR / "delivery_catalog").rglob("*.parquet")),
        "alonit_prices": list((EXTERNAL_SILVER_ROOT / "alonit_prices").rglob("*.parquet")),
    }
    for source_id, files in disk_sources.items():
        try:
            update_source(
                source_id,
                status="complete" if files else "not_started",
                row_count=_count_parquet_rows(files),
            )
        except Exception:
            pass

    # Internal POS: reflect the already-imported silver catalog.
    if products:
        try:
            update_source("yomyom_pos", status="complete", row_count=len(products))
        except Exception:
            pass


def _expiry_summary() -> dict[str, Any]:
    """Bucket counts + a few alerts from the latest expiry signal parquet."""
    path = _latest(EXPIRY_SIGNALS_DIR, "expiry_alerts_*.parquet")
    rows = _read_rows(path) if path else []
    buckets = {b: 0 for b in EXPIRY_BUCKETS}
    for r in rows:
        sev = r.get("severity")
        if sev in buckets:
            buckets[sev] += 1
    actionable = [r for r in rows if r.get("severity") in EXPIRY_BUCKETS[:-1]]
    actionable.sort(key=lambda r: (r.get("days_to_expiry") if r.get("days_to_expiry") is not None else 9999))
    alerts = [
        {
            "barcode": r.get("barcode"),
            "productName": r.get("product_name"),
            "expiryDate": r.get("expiry_date"),
            "daysToExpiry": r.get("days_to_expiry"),
            "severity": r.get("severity"),
            "currentStock": r.get("current_stock"),
            "knownInPos": r.get("known_in_pos"),
        }
        for r in actionable[:30]
    ]
    return {
        "totalScans": len(rows),
        "buckets": buckets,
        "actionable": len(actionable),
        "alerts": alerts,
    }


def export() -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc)

    # Refresh operational recommendations so the export always reflects current POS data.
    gen = generate_operational_recommendations()

    products = _read_rows(SILVER_POS_ROOT / "yomyom_products.parquet")
    inventory = _read_rows(SILVER_POS_ROOT / "yomyom_inventory.parquet")
    margins = _read_rows(SILVER_POS_ROOT / "yomyom_margins.parquet")

    rec_rows = _read_rows(_latest(OPERATIONAL_DIR, "operational_recommendations_*.parquet"))
    recommendations = [_map_recommendation(r) for r in rec_rows]

    # Competitor recommendations (product_recommendations.py) — appended as family=competitor.
    competitor_recs_path = _latest(PRODUCT_RECS_DIR, "product_recommendations_*.parquet")
    competitor_recs = [_map_competitor_recommendation(r) for r in _read_rows(competitor_recs_path)]
    recommendations += competitor_recs

    by_type: dict[str, int] = {}
    by_family: dict[str, int] = {}
    for r in recommendations:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
        by_family[r["family"]] = by_family.get(r["family"], 0) + 1

    competitor_path = _latest(COMPETITOR_DIR, "*.parquet")
    competitor_signals = len(_read_rows(competitor_path)) if competitor_path else 0

    # Refresh the source-status contract, then read the aggregate scraping status.
    _reconcile_sources_from_disk(products)
    summary = write_summary()
    scraping_status = summary.get("scraping_status", "not_started")

    payload = {
        "meta": {
            "generatedAt": generated_at.isoformat(),
            "status": gen.get("status", "unknown"),
            "competitorSignals": competitor_signals,
            "scrapingStatus": scraping_status,
            "competitorRecommendations": len(competitor_recs),
        },
        "posHealth": _pos_health(products, inventory, margins),
        "expiry": _expiry_summary(),
        "byType": by_type,
        "byFamily": by_family,
        "sources": list(load_sources().values()),
        "recommendations": recommendations,
    }

    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PUBLIC_DATA_DIR / "operational.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "ok",
        "output": str(out_path),
        "recommendation_count": len(recommendations),
        "by_type": by_type,
        "by_family": by_family,
        "scraping_status": scraping_status,
        "pos_products": len(products),
    }


def main() -> int:
    result = export()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
