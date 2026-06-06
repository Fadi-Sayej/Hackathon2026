from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from src.common.paths import MATCHING_ROOT, RECOMMENDATIONS_ROOT, SIGNALS_ROOT, SILVER_POS_ROOT


REPORTS_ROOT = Path(__file__).resolve().parents[2] / "reports" / "recommendations"
PRODUCT_RECOMMENDATION_DIR = RECOMMENDATIONS_ROOT / "product_recommendations"

POS_FILES = {
    "products": SILVER_POS_ROOT / "yomyom_products.parquet",
    "sales": SILVER_POS_ROOT / "yomyom_sales.parquet",
    "inventory": SILVER_POS_ROOT / "yomyom_inventory.parquet",
    "margins": SILVER_POS_ROOT / "yomyom_margins.parquet",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _latest_file(root: Path, pattern: str) -> Path | None:
    if not root.exists():
        return None
    files = sorted(root.rglob(pattern), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def _product_matches_file() -> Path | None:
    path = MATCHING_ROOT / "product_matches.parquet"
    if path.exists():
        return path
    return _latest_file(MATCHING_ROOT, "product_matches*.parquet")


def _read_parquet_rows(path: Path) -> list[dict[str, Any]]:
    return pq.read_table(path).to_pylist()


def _is_sample_pos(rows: list[dict[str, Any]]) -> bool:
    return all("sample" in str(row.get("_source_file", "")).lower() for row in rows[:20]) if rows else True


def _detect_matching_columns(rows: list[dict[str, Any]]) -> dict[str, str] | None:
    if not rows:
        return None
    keys = set(rows[0].keys())
    options = [
        {
            "internal_barcode": "internal_barcode",
            "competitor_barcode": "competitor_barcode",
            "competitor_signal_id": "competitor_signal_id",
        },
        {
            "internal_barcode": "internal_barcode",
            "competitor_barcode": "external_barcode",
            "competitor_signal_id": "external_product_key",
        },
        {
            "internal_barcode": "barcode",
            "competitor_barcode": "external_barcode",
            "competitor_signal_id": "signal_id",
        },
    ]
    for option in options:
        if all(value in keys for value in option.values()):
            return option
    return None


def _confidence(score: float) -> float:
    return max(0.0, min(1.0, round(score, 2)))


def _recommendation_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def generate_product_recommendations() -> dict[str, Any]:
    observed_at = _now()
    ts = observed_at.strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORTS_ROOT / f"product_recommendations_{ts}.md"

    missing_inputs: list[str] = []
    pos_rows: dict[str, list[dict[str, Any]]] = {}
    for label, path in POS_FILES.items():
        if not path.exists():
            missing_inputs.append(f"missing POS table: {path.name}")
        else:
            pos_rows[label] = _read_parquet_rows(path)
    if pos_rows and _is_sample_pos(pos_rows.get("products", [])):
        missing_inputs.append("POS inputs are sample/demo only; waiting for real YomYom export")

    competitor_path = _latest_file(SIGNALS_ROOT / "competitor_product_signals", "*.parquet")
    if competitor_path is None:
        missing_inputs.append("missing competitor product signals parquet")

    matching_path = _product_matches_file()
    if matching_path is None:
        missing_inputs.append("missing matching parquet")

    if missing_inputs:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "\n".join(
                [
                    "# Product Recommendation Readiness",
                    "",
                    f"- Generated at: {observed_at.isoformat()}",
                    "- Status: readiness_only",
                    "- Real recommendations were not generated.",
                    "",
                    "## Missing prerequisites",
                    "",
                    *[f"- {item}" for item in missing_inputs],
                    "",
                    "## Required inputs",
                    "",
                    "- Real YomYom POS silver tables with non-sample `_source_file` metadata",
                    "- Competitor product signals parquet",
                    "- Matching output that links internal products to competitor signals",
                    "",
                    "## Recommendation guardrails",
                    "",
                    "- No recommendation is emitted from one signal only",
                    "- Evidence must include at least two independent inputs",
                    "- Planogram recommendations are intentionally out of scope here",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "status": "readiness_only",
            "report_path": str(report_path),
            "missing_inputs": missing_inputs,
        }

    competitor_rows = _read_parquet_rows(competitor_path)
    matching_rows = _read_parquet_rows(matching_path)
    matching_columns = _detect_matching_columns(matching_rows)
    if matching_columns is None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "\n".join(
                [
                    "# Product Recommendation Readiness",
                    "",
                    f"- Generated at: {observed_at.isoformat()}",
                    "- Status: readiness_only",
                    "- Matching parquet exists but does not expose recognizable linkage columns yet.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "status": "readiness_only",
            "report_path": str(report_path),
            "missing_inputs": ["matching parquet schema is not recognized"],
        }

    products_by_barcode = {
        str(row.get("barcode")): row
        for row in pos_rows["products"]
        if row.get("barcode")
    }
    sales_by_barcode = {
        str(row.get("barcode")): row
        for row in pos_rows["sales"]
        if row.get("barcode")
    }
    inventory_by_barcode = {
        str(row.get("barcode")): row
        for row in pos_rows["inventory"]
        if row.get("barcode")
    }
    margins_by_barcode = {
        str(row.get("barcode")): row
        for row in pos_rows["margins"]
        if row.get("barcode")
    }
    competitor_by_signal: dict[str, dict[str, Any]] = {}
    for row in competitor_rows:
        for key in ("signal_id", "external_product_key", "barcode"):
            value = row.get(key)
            if value:
                competitor_by_signal.setdefault(str(value), row)

    recommendations: list[dict[str, Any]] = []
    for match in matching_rows:
        internal_barcode = str(match.get(matching_columns["internal_barcode"]) or "")
        competitor_barcode = str(match.get(matching_columns["competitor_barcode"]) or "")
        signal_id = str(match.get(matching_columns["competitor_signal_id"]) or "")
        if not internal_barcode:
            continue

        product = products_by_barcode.get(internal_barcode)
        sales = sales_by_barcode.get(internal_barcode)
        inventory = inventory_by_barcode.get(internal_barcode)
        margin = margins_by_barcode.get(internal_barcode)
        competitor = competitor_by_signal.get(signal_id)
        if not product or not competitor:
            continue

        evidence: list[str] = []
        if competitor.get("appears_in_price_file") or competitor.get("appears_in_delivery_catalog"):
            evidence.append("competitor presence")
        if competitor.get("appears_in_delivery_catalog"):
            evidence.append("delivery catalog presence")
        if sales and sales.get("units_sold_30d") not in (None, 0):
            evidence.append("YomYom sales")
        if inventory and inventory.get("current_stock") is not None:
            evidence.append("stock level")
        if margin and margin.get("margin_pct") is not None:
            evidence.append("margin")
        if competitor.get("is_online_available") is True:
            evidence.append("explicit online availability")
        if competitor.get("promo_price") is not None or competitor.get("sale_price") is not None:
            evidence.append("promo signal")

        evidence = list(dict.fromkeys(evidence))
        if len(evidence) < 2:
            continue

        local_price = float(product.get("selling_price") or 0)
        competitor_price = float(
            competitor.get("delivery_catalog_price")
            or competitor.get("price_file_price")
            or 0
        )
        stock = inventory.get("current_stock") if inventory else None
        sold_30d = sales.get("units_sold_30d") if sales else None
        margin_pct = margin.get("margin_pct") if margin else None

        recommendation_type = None
        reason = None
        confidence = 0.0

        if competitor_price and local_price and competitor_price < local_price * 0.9 and margin_pct not in (None, 0):
            recommendation_type = "PRICE_CHECK"
            reason = "Competitor price is materially below YomYom shelf price while local margin data exists."
            confidence = _confidence(0.55 + 0.1 * min(len(evidence), 4))
        elif stock is not None and sold_30d not in (None, 0) and stock <= 10 and sold_30d >= 20:
            recommendation_type = "REORDER"
            reason = "Local stock is low relative to recent sales and the product also appears in competitor signals."
            confidence = _confidence(0.6 + 0.08 * min(len(evidence), 4))
        elif competitor.get("appears_in_delivery_catalog") and sold_30d in (None, 0) and stock not in (None, 0):
            recommendation_type = "WATCH_PRODUCT"
            reason = "Competitor catalog presence is strong, but internal demand evidence is still weak."
            confidence = _confidence(0.45 + 0.08 * min(len(evidence), 4))

        if recommendation_type is None:
            continue

        recommendations.append(
            {
                "recommendation_id": _recommendation_id(internal_barcode, signal_id, recommendation_type),
                "generated_at": observed_at.isoformat(),
                "recommendation_type": recommendation_type,
                "barcode": internal_barcode,
                "competitor_barcode": competitor_barcode or None,
                "product_name": product.get("product_name"),
                "category": product.get("category"),
                "confidence": confidence,
                "evidence": evidence,
                "reason": reason,
                "local_price": local_price or None,
                "competitor_price": competitor_price or None,
                "current_stock": stock,
                "units_sold_30d": sold_30d,
                "margin_pct": margin_pct,
                "competitor_signal_id": signal_id,
            }
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    if not recommendations:
        report_path.write_text(
            "\n".join(
                [
                    "# Product Recommendation Readiness",
                    "",
                    f"- Generated at: {observed_at.isoformat()}",
                    "- Status: ready_but_no_recommendations",
                    "- Inputs were present, but no product met the multi-signal rule set yet.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "status": "ready_but_no_recommendations",
            "report_path": str(report_path),
            "recommendation_count": 0,
        }

    PRODUCT_RECOMMENDATION_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = PRODUCT_RECOMMENDATION_DIR / f"product_recommendations_{ts}.parquet"
    pq.write_table(pa.Table.from_pylist(recommendations), parquet_path, compression="snappy")

    lines = [
        "# Product Recommendations",
        "",
        f"- Generated at: {observed_at.isoformat()}",
        f"- Recommendation count: {len(recommendations)}",
        "",
        "## Summary by type",
        "",
    ]
    by_type: dict[str, int] = {}
    for row in recommendations:
        by_type[row["recommendation_type"]] = by_type.get(row["recommendation_type"], 0) + 1
    for key in sorted(by_type):
        lines.append(f"- {key}: {by_type[key]}")
    lines.extend(["", "## Sample rows", ""])
    for row in recommendations[:10]:
        lines.append(
            f"- {row['recommendation_type']} | {row['product_name']} | confidence={row['confidence']:.2f} | evidence={', '.join(row['evidence'])}"
        )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "status": "ok",
        "report_path": str(report_path),
        "parquet_path": str(parquet_path),
        "recommendation_count": len(recommendations),
    }
