# src/engine/inputs.py
"""Everything a capability may read, loaded once per run (design.md §11.1)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pyarrow.parquet as pq

from src.common.paths import MATCHING_ROOT, SIGNALS_ROOT, SILVER_POS_ROOT
from src.common.store_types import StoreTypeConfig, load_store_types
from src.engine.model import EvidenceWindow, norm_barcode
from src.engine.policy import Policy
from src.internal_pos.pos_importer import read_pos_vintage
from src.owner_state.model import OwnerState, answered_cost

OUR_FORMAT = "gas_convenience"


@dataclass
class EngineInputs:
    products: Optional[list]
    inventory: Optional[list]        # design §11.1: its own field, so its absence is statable
    sales_monthly: Optional[list]
    sales_summary: Optional[dict]
    window: Optional[EvidenceWindow]
    observations: Optional[list]
    matches: Optional[list]
    stores: StoreTypeConfig
    withdrawn: Optional[set]
    vintages: dict
    owner: OwnerState
    policy: Policy
    run_at: datetime


def _rows(path: Path) -> Optional[list]:
    return pq.read_table(path).to_pylist() if path.exists() else None


def _pos(v) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None


def _num(v) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _shape_products(products, inventory, owner: OwnerState) -> list:
    stock = {}
    for r in inventory or []:
        stock[(norm_barcode(r.get("barcode")), r.get("product_name"))] = _num(r.get("current_stock"))
    out = []
    for r in products:
        barcode = norm_barcode(r.get("barcode"))
        owner_cost = answered_cost(owner, barcode) if barcode else None
        pos_cost = _pos(r.get("cost_price"))
        out.append({
            "barcode": barcode, "has_identifier": barcode is not None,
            "product_name": r.get("product_name"), "department": r.get("category"),
            "shelf_price": _pos(r.get("selling_price")), "delivery_price": _pos(r.get("wolt_price")),
            "cost_price": owner_cost if owner_cost is not None else pos_cost,
            "cost_source": "owner" if owner_cost is not None else ("pos" if pos_cost is not None else None),
            "recorded_stock": stock.get((barcode, r.get("product_name"))),
        })
    return sorted(out, key=lambda p: (p["barcode"] or "", p["product_name"] or ""))


def _window_from_summary(monthly, policy: Policy) -> Optional[EvidenceWindow]:
    from src.internal_pos.sales_importer import evidence_window
    months = sorted({r["month"] for r in monthly})
    return evidence_window(months, policy.full_annual_cycle_months) if months else None


def _shape_observations(signals, stores: StoreTypeConfig) -> Optional[list]:
    if signals is None:
        return None
    excluded = set(stores.excluded_stores(OUR_FORMAT)) | set(stores.client_store_ids())
    out = []
    for s in signals:
        store_id = str(s.get("competitor_store_id") or "")
        if store_id in excluded:
            continue                       # INV-020 / D-5: dropped before any capability sees it
        price = _pos(s.get("delivery_catalog_price")) or _pos(s.get("price_file_price"))
        if price is None or not s.get("barcode"):
            continue
        fmt = stores.store_type(store_id)
        out.append({"barcode": norm_barcode(s.get("barcode")), "price": price, "store_id": store_id,
                    "store_name": s.get("competitor_store_name"), "store_format": fmt,
                    "affinity": stores.affinity(OUR_FORMAT, fmt), "observed_at": s.get("observed_at"),
                    "source_type": "delivery" if _pos(s.get("delivery_catalog_price")) else "price_file"})
    return sorted(out, key=lambda o: (o["barcode"], o["store_id"], o["price"]))


def load_inputs(*, policy: Policy, owner: OwnerState, run_at: datetime, silver_dir: Path = SILVER_POS_ROOT,
                signals_dir: Path = SIGNALS_ROOT / "competitor_product_signals",
                matches_path: Path = MATCHING_ROOT / "product_matches.parquet",
                stores: Optional[StoreTypeConfig] = None) -> EngineInputs:
    stores = stores or load_store_types()
    products_raw = _rows(silver_dir / "yomyom_products.parquet")
    inventory = _rows(silver_dir / "yomyom_inventory.parquet")
    products = _shape_products(products_raw, inventory, owner) if products_raw else None
    monthly = _rows(silver_dir / "sales_monthly.parquet")
    summary_rows = _rows(silver_dir / "sales_summary.parquet")
    summary = {r["barcode"]: r for r in summary_rows} if summary_rows else None
    window = _window_from_summary(monthly, policy) if monthly else None
    latest_signal = sorted(signals_dir.glob("*.parquet")) if signals_dir.exists() else []
    signals = _rows(latest_signal[-1]) if latest_signal else None
    observations = _shape_observations(signals, stores)
    matches = _rows(matches_path)
    if matches:
        for m in matches:
            m["internal_barcode"] = norm_barcode(m.get("internal_barcode"))
    snapshot_date = None
    if observations:
        snapshot_date = max((o["observed_at"] or "")[:10] for o in observations) or None
    vintages = {
        "pos": read_pos_vintage(silver_dir) or {"file": None, "as_of": None},
        "sales": (window.to_dict() if window else {"months": [], "first": None, "last": None, "full_annual_cycle": False}),
        "competitor": {"snapshot_date": snapshot_date, "sources": sorted({o["store_id"] for o in observations or []})},
        "owner_state": {"pulled_at": owner.pulled_at, "status": owner.status},
    }
    vintages["sales"] = {k: vintages["sales"][k] for k in ("months", "first", "last", "full_annual_cycle")}
    return EngineInputs(products=products, inventory=inventory or None,
                        sales_monthly=monthly, sales_summary=summary, window=window,
                        observations=observations, matches=matches, stores=stores, withdrawn=None,
                        vintages=vintages, owner=owner, policy=policy, run_at=run_at)
