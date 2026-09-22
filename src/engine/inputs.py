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
from src.engine.stock_date import usable_stock_date
from src.owner_state.model import OwnerState, answered_cost, device_register

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


class MisalignedInventoryError(ValueError):
    """The inventory table is not row-for-row the products table, so a row's stock cannot
    be attached to it by position. Refused rather than guessed (#89)."""


def _stock_by_row(products, inventory) -> list:
    """One stock value per product row, taken from the SAME row of the export.

    #89. This used to be a dict keyed on (barcode, product_name), and that key is not
    unique: the pilot carries 30 keys with more than one row and differing stock, so the
    last row's stock was written onto every earlier one. Counted per raw row, before any
    grouping: 35 rows published another row's stock — 13 real negatives shown as a
    different negative, 12 real negatives hidden as zero or positive, and 9 rows at zero
    or above shown as negative. Those raw counts include barcoded rows that leave the
    population as conflicts either way, so they do not sum to the change in the published
    negative-stock count.

    It also blinds ADR-019 by construction: rows that disagree on stock reach
    `_resolve_identity` already agreeing. On the pilot none disagreed on stock alone, so no
    conflict was hidden outright — but 9 conflict records omitted stock from the fields
    they said were in dispute.

    Position is the identity that works, because the two tables are the same export: the
    importer projects every silver table from one `normalized_rows` list in one loop
    (`pos_importer.import_pos_file`). It is checked rather than assumed, because the day a
    table is regenerated on its own, attaching stock by position would publish one
    product's stock on another — this same defect, quieter.
    """
    if not inventory:
        return [None] * len(products)          # a missing stock table is None, never 0
    if len(inventory) != len(products):
        raise MisalignedInventoryError(
            f"inventory has {len(inventory)} rows and products has {len(products)}; "
            "they must be the same export, row for row")
    for i, (p, r) in enumerate(zip(products, inventory)):
        if (norm_barcode(p.get("barcode")) != norm_barcode(r.get("barcode"))
                or p.get("product_name") != r.get("product_name")):
            raise MisalignedInventoryError(
                f"row {i}: products has {p.get('barcode')!r} {p.get('product_name')!r}, "
                f"inventory has {r.get('barcode')!r} {r.get('product_name')!r}")
    return [_num(r.get("current_stock")) for r in inventory]


def _shape_products(products, inventory, owner: OwnerState) -> list:
    stock = _stock_by_row(products, inventory)
    out = []
    for i, r in enumerate(products):
        barcode = norm_barcode(r.get("barcode"))
        owner_cost = answered_cost(owner, barcode) if barcode else None
        pos_cost = _pos(r.get("cost_price"))
        out.append({
            "barcode": barcode, "has_identifier": barcode is not None,
            "product_name": r.get("product_name"), "department": r.get("category"),
            "shelf_price": _pos(r.get("selling_price")), "delivery_price": _pos(r.get("wolt_price")),
            "cost_price": owner_cost if owner_cost is not None else pos_cost,
            "cost_source": "owner" if owner_cost is not None else ("pos" if pos_cost is not None else None),
            "recorded_stock": stock[i],
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

    Returns (products, conflicting).

    ADR-022 extends this to barcode-less rows, grouped by `product_name`. They used to be
    "kept as itself", which was only safe while names were unique, and on the pilot they are
    not: 27 barcode-less names are listed more than once. Kept as themselves, rows sharing a
    name published their findings under one entry id (`entry_id` falls back to the name), so
    the owner resolving one silently resolved the others (#89). No field the export carries
    tells two such rows apart — name, department and price repeat, and position is not stable
    across exports (ADR-009) — so the honest identity is the name, under the same rule a
    barcode gets: agree on everything and they are one row, disagree and they are a record.
    """
    groups: dict = {}
    out, conflicting = [], []
    for p in shaped:
        key = ("barcode", p["barcode"]) if p["barcode"] is not None else ("name", p["product_name"])
        groups.setdefault(key, []).append(p)
    for key in sorted(groups, key=lambda k: (k[0], str(k[1]))):
        rows = groups[key]
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
        conflicting.append({"barcode": rows[0]["barcode"],
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
        # `devices` is ADR-021: how many browser profiles have written, and when each last
        # did. It sits here rather than in a block of its own because this is where
        # owner-state provenance lives, and it is provenance — see _digest() on why its
        # timestamps are not hashed.
        "owner_state": {"pulled_at": owner.pulled_at, "status": owner.status,
                        "reason": owner.reason, "devices": device_register(owner)},
    }
    # The boundary reconciliation actually used, published because OQ-201 was closed on the
    # words "window vintages published so misalignment is visible" (§21) — and this is the
    # one window that was not. `vintages.sales` spans every monthly row; reconciliation
    # counts only the months BEFORE the stock count, so the two differ whenever the count
    # predates the last report. Measured on the 2026-09-21 artefact: the published window
    # said seven months while no entry used more than five.
    #
    # `usable_stock_date` rather than a second derivation, so this and the capability's own
    # refusal (reconciliation.run) cannot disagree about what the date is — the single
    # definition that module exists to be.
    #
    # Null means the same thing it means there: we do not know when the stock was counted,
    # so there is no boundary. It is never the full span by default.
    _as_of = usable_stock_date((vintages["pos"] or {}).get("as_of"),
                               source=(vintages["pos"] or {}).get("as_of_source"))
    vintages["sales"]["reconcile_before"] = _as_of.strftime("%Y-%m") if _as_of else None
    vintages["sales"] = {k: vintages["sales"][k]
                         for k in ("months", "first", "last", "full_annual_cycle", "reconcile_before")}
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
    # NOT pulled_at, and NOT the device register (ADR-021). The owner's ANSWERS are an
    # input; the moment we fetched them is not, and hashing it made two runs over identical
    # data disagree — which is precisely the failure this digest exists to detect, so it
    # would have detected nothing. `last_seen_at` moves every time anyone opens the app, so
    # hashing it would re-introduce that defect at a higher frequency.
    feed("owner", {"status": owner.status,
                   "answers": _json.dumps(owner.answers, sort_keys=True, default=str)})
    return h.hexdigest()
