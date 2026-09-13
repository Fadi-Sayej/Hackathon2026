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
    idle: Optional[set]
    conflicting: Optional[list]   # ADR-019: barcodes whose rows disagree
    inputs_digest: str            # Task 3.1: content addressing over what was read
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
    return _resolve_identity(sorted(out, key=lambda p: (p["barcode"] or "", p["product_name"] or "")))


# Fields whose disagreement makes a barcode unusable. Everything a capability reads.
_IDENTITY_FIELDS = ("product_name", "department", "shelf_price", "delivery_price",
                    "cost_price", "recorded_stock")


def _resolve_identity(shaped: list) -> tuple:
    """ADR-019. Rows sharing a barcode that agree on every field are the same row twice and
    collapse. Rows that disagree leave the population entirely and are reported: a product
    listed at two shelf prices has no shelf price the system can state (D-3), and picking
    one by arrival order would compute a markup from a number nobody chose.

    Returns (products, conflicting). A barcode-less row cannot be grouped and is kept as
    itself — `hygiene.no_identifier` already reports it.
    """
    groups: dict = {}
    out, conflicting = [], []
    for p in shaped:
        if p["barcode"] is None:
            out.append(p)
            continue
        groups.setdefault(p["barcode"], []).append(p)
    for barcode in sorted(groups):
        rows = groups[barcode]
        if len(rows) == 1:
            out.append(rows[0])
            continue
        fields = {}
        for f in _IDENTITY_FIELDS:
            values = {r[f] for r in rows}
            if len(values) > 1:
                fields[f] = sorted(values, key=lambda v: (v is None, str(v)))
        if not fields:
            out.append(rows[0])                      # the same row twice
            continue
        conflicting.append({"barcode": barcode,
                            "product_name": rows[0]["product_name"],
                            "fields": fields})
    return sorted(out, key=lambda p: (p["barcode"] or "", p["product_name"] or "")), conflicting


def _window_from_summary(monthly, policy: Policy) -> Optional[EvidenceWindow]:
    from src.internal_pos.sales_importer import evidence_window
    months = sorted({r["month"] for r in monthly})
    return evidence_window(months, policy.full_annual_cycle_months) if months else None


def _competitor_vintage(observations: Optional[list]) -> dict:
    """Where the competitor half of a run came from, in terms a reader can check.

    `sources` used to be `sorted({o["store_id"] …})`, so the published provenance listed
    164 "sources" named "401", "402", "403" and a handful of Wolt ObjectIds. Those are
    store identifiers, not sources, and the schema could not catch it — it requires an
    array of strings and says nothing about which strings. The DataPage fixture has
    always expected a feed name (`sources: ['wolt']`).

    So `sources` now names the feeds actually observed — `delivery` (the Wolt catalogue)
    and `price_file` (the Alonit files) — and the store count keeps its information under
    a name that describes it. Neither value is inferred; both are read straight off the
    observations. Mapping a feed kind to a brand would be an assumption, so it is not made
    here.
    """
    obs = observations or []
    return {
        "snapshot_date": (max((o["observed_at"] or "")[:10] for o in obs) or None) if obs else None,
        "sources": sorted({o["source_type"] for o in obs if o.get("source_type")}),
        "store_count": len({o["store_id"] for o in obs if o.get("store_id")}),
    }


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
    products, conflicting = (_shape_products(products_raw, inventory, owner)
                            if products_raw else (None, None))
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
    vintages = {
        # `as_of_source` travels with `as_of` for the same reason `reason` travels with
        # owner_state below: a date is not provenance until you know how it was arrived
        # at. Until 2026-09-13 this said "today" on every CI run, because the default was
        # the file's mtime and `git clone` stamps that with the checkout time.
        "pos": read_pos_vintage(silver_dir) or {"file": None, "as_of": None, "as_of_source": None},
        "sales": (window.to_dict() if window else {"months": [], "first": None, "last": None, "full_annual_cycle": False}),
        "competitor": _competitor_vintage(observations),
        # `reason` travels, because without it a replayed mirror reads as a live pull.
        # _pull_owner_state() falls back to the committed replica when there is no
        # credential — deliberately, so reproduction works on a laptop — and both
        # read_mirror() and the caller flag it. Publishing only status and pulled_at
        # dropped every flag: the Checkpoint 3 clone, with no credential at all, still
        # said `status: available` under a pulled_at from another machine. Design §13
        # requires that the system be unavailable honestly rather than silently local.
        "owner_state": {"pulled_at": owner.pulled_at, "status": owner.status,
                        "reason": owner.reason},
    }
    vintages["sales"] = {k: vintages["sales"][k] for k in ("months", "first", "last", "full_annual_cycle")}
    digest = _digest(products, summary_rows, monthly, observations, matches, policy, owner)
    return EngineInputs(products=products, inventory=inventory or None,
                        sales_monthly=monthly, sales_summary=summary, window=window,
                        observations=observations, matches=matches, stores=stores, withdrawn=None, idle=None, conflicting=conflicting,
                        inputs_digest=digest,
                        vintages=vintages, owner=owner, policy=policy, run_at=run_at)


# When a row was imported is not what the row says. `sales_import` rewrites its tables on
# every run, so hashing `_imported_at` made two runs over identical data disagree — the
# digest would have reported a change on every run and therefore reported nothing.
#
# Note that products reach this function already shaped, so their provenance columns are
# gone before the exclusion list is consulted: two exports carrying identical rows are the
# same input whichever day they were taken. The export day is not lost, it is published in
# vintages.pos.as_of.
_NOT_CONTENT = frozenset({"_imported_at", "_source_kind", "created_at"})


def _content_only(row):
    if not isinstance(row, dict):
        return row
    return {k: v for k, v in row.items() if k not in _NOT_CONTENT}


def _digest(products, summary_rows, monthly, observations, matches, policy, owner) -> str:
    """A hex digest over the CONTENT the run read, not over the files it read them from.

    Content, because a parquet rewritten with identical rows is the same input and must
    produce the same digest; and because the policy is an input — a figure computed under a
    different threshold is a different figure, even from identical data.

    Fed in sorted order so two runs over the same inputs agree regardless of how the rows
    arrived (§ determinism).
    """
    import hashlib
    import json as _json

    h = hashlib.sha256()

    def feed(label: str, rows) -> None:
        h.update(label.encode("utf-8"))
        if rows is None:
            h.update(b"\x00absent")      # absent is not empty, and must not hash alike
            return
        if isinstance(rows, dict):
            rows = [{"k": k, "v": v} for k, v in sorted(rows.items(), key=lambda kv: str(kv[0]))]
        cleaned = [_content_only(row) for row in rows]
        for row in sorted(cleaned, key=lambda r: _json.dumps(r, sort_keys=True, default=str)):
            h.update(_json.dumps(row, sort_keys=True, default=str).encode("utf-8"))

    feed("products", products)
    feed("sales_summary", summary_rows)
    feed("sales_monthly", monthly)
    feed("observations", observations)
    feed("matches", matches)
    feed("policy", policy.as_dict())
    # NOT pulled_at. The owner's ANSWERS are an input; the moment we fetched them is not,
    # and hashing it made two runs over identical data disagree — which is precisely the
    # failure this digest exists to detect, so it would have detected nothing.
    feed("owner", {"status": owner.status,
                   "answers": _json.dumps(owner.answers, sort_keys=True, default=str)})
    return h.hexdigest()
