# tests/engine/helpers.py
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.store_types import load_store_types
from src.engine.inputs import EngineInputs
from src.engine.model import EvidenceWindow
from src.engine.policy import load_policy
from src.owner_state.model import OwnerState

RUN_AT = datetime(2026, 9, 8, 6, 0, tzinfo=timezone.utc)


def product(barcode, *, name="p", department="d", shelf=None, delivery=None, cost=None, cost_source=None, stock=None):
    return {"barcode": barcode, "has_identifier": barcode is not None, "product_name": name, "department": department,
            "shelf_price": shelf, "delivery_price": delivery, "cost_price": cost,
            "cost_source": cost_source or ("pos" if cost is not None else None), "recorded_stock": stock}


def summary(barcode, *, units=0.0, receipts=0.0, months=1, last=None, observed_zero=False,
            reconcile_units=None, reconcile_receipts=None, reconcile_months=None, name="p"):
    return {"barcode": barcode, "product_name": name, "months_present": months, "units_total": units,
            "receipts_total": receipts, "last_month_with_units": last, "observed_zero": observed_zero,
            "reconcile_units": units if reconcile_units is None else reconcile_units,
            "reconcile_receipts": receipts if reconcile_receipts is None else reconcile_receipts,
            "reconcile_months": months if reconcile_months is None else reconcile_months}


def observation(barcode, price, store_id, store_format, affinity, observed_at="2026-09-08T00:00:00Z",
                source_type="price_file", store_name=None):
    return {"barcode": barcode, "price": price, "store_id": store_id, "store_name": store_name or store_id,
            "store_format": store_format, "affinity": affinity, "observed_at": observed_at, "source_type": source_type}


def match(internal_barcode, external_barcode, store_id, method="barcode_exact", confidence=1.0):
    return {"internal_barcode": internal_barcode, "external_barcode": external_barcode,
            "competitor_store_id": store_id, "match_method": method, "match_confidence": confidence, "approved": True}


def window_of(months, full=False):
    return EvidenceWindow(months=list(months), first=months[0], last=months[-1], count=len(months), full_annual_cycle=full)


def make_inputs(**kw):
    owner = kw.get("owner") or OwnerState.from_dict({"status": "available", "pulled_at": "t"})
    sales_summary = kw.get("sales_summary")
    return EngineInputs(
        products=kw.get("products"),
        # inventory defaults to present whenever products are: a test that says nothing about
        # the stock table is not a test about the stock table being absent.
        inventory=kw.get("inventory", [] if kw.get("products") is not None else None),
        sales_monthly=kw.get("sales_monthly"),
        sales_summary={s["barcode"]: s for s in sales_summary} if sales_summary is not None else None,
        window=kw.get("window"), observations=kw.get("observations"), matches=kw.get("matches"),
        stores=load_store_types(), withdrawn=kw.get("withdrawn"), conflicting=kw.get("conflicting", []), idle=kw.get("idle"),
        vintages={"pos": {"file": "f", "as_of": "2026-08-02"},
                  "sales": {"months": [], "first": None, "last": None, "full_annual_cycle": False},
                  "competitor": {"snapshot_date": "2026-09-08", "sources": []},
                  "owner_state": {"pulled_at": owner.pulled_at, "status": owner.status}},
        owner=owner, policy=kw.get("policy") or load_policy(), run_at=kw.get("run_at") or RUN_AT)
