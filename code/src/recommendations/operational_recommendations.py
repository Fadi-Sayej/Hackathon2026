"""
operational_recommendations.py — unified operational recommendations (Step 5).

Merges three internal signal families into ONE clear recommendation set that
needs no competitor matching and works directly on the real YomYom POS export:

  1. Expiry alerts        → PROMOTE_EXPIRING_PRODUCT   (data/signals/expiry/*.parquet)
  2. POS quality issues   → CHECK_NEGATIVE_STOCK,
                            CHECK_MARGIN,
                            VERIFY_UNKNOWN_BARCODE
  3. Internal WOLT gap    → CHECK_WOLT_PRICE_GAP        (selling_price vs wolt_price)

Outputs:
  data/recommendations/operational_recommendations/operational_recommendations_<ts>.parquet
  reports/recommendations/operational_recommendations_<ts>.md

Each row shares a schema with the competitor recommendation engine (recommendation_id,
recommendation_type, barcode, product_name, confidence, evidence, reason, ...) plus a
`recommendation_family` discriminator so a single dashboard can read both families.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from src.common.paths import RECOMMENDATIONS_ROOT, SIGNALS_ROOT, SILVER_POS_ROOT


REPORTS_ROOT = Path(__file__).resolve().parents[2] / "reports" / "recommendations"
OUTPUT_DIR = RECOMMENDATIONS_ROOT / "operational_recommendations"
EXPIRY_SIGNALS_DIR = SIGNALS_ROOT / "expiry"

# ── Thresholds ──────────────────────────────────────────────────────────────
WOLT_GAP_MIN_PCT = 5.0       # flag when |selling - wolt| / selling exceeds this
LOW_MARGIN_PCT = 10.0        # flag margins at or below this (incl. negative)
EXPIRY_ACTIONABLE = {"expired", "critical_7d", "warning_14d", "upcoming_30d"}

_SAMPLE_TOKENS = ("sample", "fake", "demo", "test")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read_parquet_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return pq.read_table(path).to_pylist()


def _latest_expiry_parquet() -> Path | None:
    if not EXPIRY_SIGNALS_DIR.exists():
        return None
    files = sorted(EXPIRY_SIGNALS_DIR.rglob("expiry_alerts_*.parquet"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def _confidence(score: float) -> float:
    return max(0.0, min(1.0, round(score, 2)))


def _recommendation_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _record(observed_at: datetime, **fields: Any) -> dict[str, Any]:
    """Build a recommendation row with all schema keys present (parquet-friendly)."""
    base: dict[str, Any] = {
        "recommendation_id": None,
        "generated_at": observed_at.isoformat(),
        "recommendation_family": "operational",
        "recommendation_type": None,
        "barcode": None,
        "product_name": None,
        "category": None,
        "confidence": 0.0,
        "evidence": [],
        "reason": None,
        "selling_price": None,
        "wolt_price": None,
        "cost_price": None,
        "current_stock": None,
        "margin_pct": None,
        "days_to_expiry": None,
        "expiry_date": None,
        "severity": None,
        "metric_value": None,
    }
    base.update(fields)
    return base


# ── Rule builders ─────────────────────────────────────────────────────────────

def _expiry_recommendations(observed_at: datetime) -> list[dict[str, Any]]:
    path = _latest_expiry_parquet()
    if path is None:
        return []
    severity_conf = {"expired": 0.95, "critical_7d": 0.9, "warning_14d": 0.7, "upcoming_30d": 0.5}
    out: list[dict[str, Any]] = []
    for row in _read_parquet_rows(path):
        severity = row.get("severity")
        barcode = str(row.get("barcode") or "")
        if not barcode:
            continue
        if not row.get("known_in_pos"):
            # Unknown barcode from an expiry scan → verification recommendation instead.
            out.append(
                _record(
                    observed_at,
                    recommendation_id=_recommendation_id(barcode, "VERIFY_UNKNOWN_BARCODE", "expiry"),
                    recommendation_type="VERIFY_UNKNOWN_BARCODE",
                    barcode=barcode,
                    confidence=0.6,
                    evidence=["expiry scan", "not found in POS"],
                    reason="Expiry scan recorded a barcode that does not exist in the POS catalog.",
                    expiry_date=row.get("expiry_date"),
                    days_to_expiry=row.get("days_to_expiry"),
                    severity=severity,
                )
            )
            continue
        if severity not in EXPIRY_ACTIONABLE:
            continue
        out.append(
            _record(
                observed_at,
                recommendation_id=_recommendation_id(barcode, "PROMOTE_EXPIRING_PRODUCT", str(row.get("expiry_date"))),
                recommendation_type="PROMOTE_EXPIRING_PRODUCT",
                barcode=barcode,
                product_name=row.get("product_name"),
                category=row.get("category"),
                confidence=_confidence(severity_conf.get(severity, 0.5)),
                evidence=["expiry scan", severity] + (["stock on hand"] if _num(row.get("current_stock")) else []),
                reason=row.get("recommended_action") or "Promote or discount before expiry.",
                selling_price=_num(row.get("selling_price")),
                wolt_price=_num(row.get("wolt_price")),
                cost_price=_num(row.get("cost_price")),
                current_stock=row.get("current_stock"),
                expiry_date=row.get("expiry_date"),
                days_to_expiry=row.get("days_to_expiry"),
                severity=severity,
            )
        )
    return out


def _negative_stock_recommendations(observed_at: datetime, inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in inventory:
        stock = _num(row.get("current_stock"))
        if stock is None or stock >= 0:
            continue
        barcode = str(row.get("barcode") or "")
        out.append(
            _record(
                observed_at,
                recommendation_id=_recommendation_id(barcode or row.get("product_name") or "", "CHECK_NEGATIVE_STOCK"),
                recommendation_type="CHECK_NEGATIVE_STOCK",
                barcode=barcode or None,
                product_name=row.get("product_name"),
                category=row.get("category"),
                confidence=0.9,
                evidence=["POS inventory", "negative stock"],
                reason="POS reports negative on-hand stock — count or fix data before reordering.",
                current_stock=row.get("current_stock"),
                metric_value=stock,
            )
        )
    return out


def _wolt_gap_recommendations(observed_at: datetime, products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in products:
        sell = _num(row.get("selling_price"))
        wolt = _num(row.get("wolt_price"))
        if not sell or not wolt or sell <= 0:
            continue
        gap_pct = (wolt - sell) / sell * 100.0
        if abs(gap_pct) < WOLT_GAP_MIN_PCT:
            continue
        barcode = str(row.get("barcode") or "")
        direction = "above" if gap_pct > 0 else "below"
        out.append(
            _record(
                observed_at,
                recommendation_id=_recommendation_id(barcode or row.get("product_name") or "", "CHECK_WOLT_PRICE_GAP"),
                recommendation_type="CHECK_WOLT_PRICE_GAP",
                barcode=barcode or None,
                product_name=row.get("product_name"),
                category=row.get("category"),
                confidence=_confidence(0.5 + min(abs(gap_pct) / 100.0, 0.45)),
                evidence=["POS selling price", "WOLT price"],
                reason=f"WOLT price is {abs(gap_pct):.0f}% {direction} the shelf price — align or confirm intentional.",
                selling_price=sell,
                wolt_price=wolt,
                metric_value=round(gap_pct, 2),
            )
        )
    return out


def _margin_recommendations(observed_at: datetime, margins: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in margins:
        sell = _num(row.get("selling_price"))
        cost = _num(row.get("cost_price"))
        if not sell or sell <= 0 or cost is None:
            continue
        margin_pct = (sell - cost) / sell * 100.0
        if margin_pct > LOW_MARGIN_PCT:
            continue
        barcode = str(row.get("barcode") or "")
        negative = margin_pct < 0
        out.append(
            _record(
                observed_at,
                recommendation_id=_recommendation_id(barcode or row.get("product_name") or "", "CHECK_MARGIN"),
                recommendation_type="CHECK_MARGIN",
                barcode=barcode or None,
                product_name=row.get("product_name"),
                category=row.get("category"),
                confidence=_confidence(0.85 if negative else 0.6),
                evidence=["cost price", "selling price"],
                reason=(
                    "Selling below cost — losing money on every sale."
                    if negative
                    else f"Thin margin ({margin_pct:.0f}%) — review pricing or cost."
                ),
                selling_price=sell,
                cost_price=cost,
                margin_pct=round(margin_pct, 2),
                metric_value=round(margin_pct, 2),
            )
        )
    return out


def _unknown_barcode_recommendations(observed_at: datetime, products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in products:
        if row.get("barcode"):
            continue
        name = row.get("product_name") or ""
        out.append(
            _record(
                observed_at,
                recommendation_id=_recommendation_id(name, "VERIFY_UNKNOWN_BARCODE", "pos"),
                recommendation_type="VERIFY_UNKNOWN_BARCODE",
                product_name=row.get("product_name"),
                category=row.get("category"),
                confidence=0.55,
                evidence=["POS catalog", "missing barcode"],
                reason="Catalog item has no barcode — cannot be matched, scanned, or tracked for expiry.",
                selling_price=_num(row.get("selling_price")),
            )
        )
    return out


# ── Reporting ─────────────────────────────────────────────────────────────────

def _build_markdown(observed_at: datetime, recs: list[dict[str, Any]], inputs: dict[str, int]) -> str:
    by_type: dict[str, int] = {}
    for row in recs:
        by_type[row["recommendation_type"]] = by_type.get(row["recommendation_type"], 0) + 1

    lines = [
        "# Operational Recommendations",
        "",
        f"- Generated at: {observed_at.isoformat()}",
        f"- Total recommendations: {len(recs)}",
        f"- Source rows scanned: products={inputs.get('products', 0)}, "
        f"inventory={inputs.get('inventory', 0)}, margins={inputs.get('margins', 0)}, "
        f"expiry_alerts={inputs.get('expiry', 0)}",
        "",
        "## Summary by type",
        "",
    ]
    for key in sorted(by_type):
        lines.append(f"- {key}: {by_type[key]}")

    # Top items per type, sorted by confidence then name.
    for rtype in sorted(by_type):
        rows = sorted(
            (r for r in recs if r["recommendation_type"] == rtype),
            key=lambda r: (-r["confidence"], str(r.get("product_name") or "")),
        )[:10]
        lines.extend(["", f"## {rtype} (top {len(rows)} of {by_type[rtype]})", ""])
        for r in rows:
            name = r.get("product_name") or r.get("barcode") or "UNKNOWN"
            detail = ""
            if rtype == "CHECK_WOLT_PRICE_GAP":
                detail = f" | shelf={r['selling_price']} wolt={r['wolt_price']} gap={r['metric_value']}%"
            elif rtype == "CHECK_MARGIN":
                detail = f" | sell={r['selling_price']} cost={r['cost_price']} margin={r['metric_value']}%"
            elif rtype == "CHECK_NEGATIVE_STOCK":
                detail = f" | stock={r['current_stock']}"
            elif rtype == "PROMOTE_EXPIRING_PRODUCT":
                detail = f" | expiry={r['expiry_date']} days={r['days_to_expiry']} stock={r['current_stock']}"
            lines.append(f"- {name} | confidence={r['confidence']:.2f}{detail} | {r['reason']}")

    return "\n".join(lines) + "\n"


def generate_operational_recommendations() -> dict[str, Any]:
    observed_at = _now()
    ts = observed_at.strftime("%Y%m%dT%H%M%SZ")
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_ROOT / f"operational_recommendations_{ts}.md"

    products = _read_parquet_rows(SILVER_POS_ROOT / "yomyom_products.parquet")
    inventory = _read_parquet_rows(SILVER_POS_ROOT / "yomyom_inventory.parquet")
    margins = _read_parquet_rows(SILVER_POS_ROOT / "yomyom_margins.parquet")
    expiry_path = _latest_expiry_parquet()
    expiry_count = len(_read_parquet_rows(expiry_path)) if expiry_path else 0

    if not products:
        report_path.write_text(
            "# Operational Recommendations\n\n"
            f"- Generated at: {observed_at.isoformat()}\n"
            "- Status: readiness_only\n"
            "- No POS products silver table found. Run the POS import first.\n",
            encoding="utf-8",
        )
        return {"status": "readiness_only", "report_path": str(report_path), "recommendation_count": 0}

    recs: list[dict[str, Any]] = []
    recs += _expiry_recommendations(observed_at)
    recs += _negative_stock_recommendations(observed_at, inventory)
    recs += _wolt_gap_recommendations(observed_at, products)
    recs += _margin_recommendations(observed_at, margins)
    recs += _unknown_barcode_recommendations(observed_at, products)

    recs.sort(key=lambda r: (-r["confidence"], r["recommendation_type"]))

    inputs = {
        "products": len(products),
        "inventory": len(inventory),
        "margins": len(margins),
        "expiry": expiry_count,
    }
    report_path.write_text(_build_markdown(observed_at, recs, inputs), encoding="utf-8")

    parquet_path = None
    if recs:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        parquet_path = OUTPUT_DIR / f"operational_recommendations_{ts}.parquet"
        pq.write_table(pa.Table.from_pylist(recs), parquet_path, compression="snappy")

    by_type: dict[str, int] = {}
    for row in recs:
        by_type[row["recommendation_type"]] = by_type.get(row["recommendation_type"], 0) + 1

    return {
        "status": "ok",
        "report_path": str(report_path),
        "parquet_path": str(parquet_path) if parquet_path else None,
        "recommendation_count": len(recs),
        "by_type": by_type,
    }
