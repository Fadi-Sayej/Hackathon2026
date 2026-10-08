# src/engine/inputs.py
"""Everything a capability may read, loaded once per run (design.md §11.1)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pyarrow.parquet as pq

from src.common.paths import EXTERNAL_SNAPSHOTS_ROOT, MATCHING_ROOT, SIGNALS_ROOT, SILVER_POS_ROOT
from src.common.store import INVENTORY_TABLE, PRODUCTS_TABLE
from src.common.store import get_store
from src.common.store_types import StoreTypeConfig, load_store_types
from src.engine.model import EvidenceWindow, norm_barcode
from src.engine.policy import Policy
from src.internal_pos.pos_importer import read_pos_vintage
from src.engine.stock_date import usable_stock_date
from src.engine.store_facts import DEFAULT_PATH as STORE_FACTS_PATH, load_store_facts
from src.engine.store_layout import (ACCEPTANCE_PATH as SHELF_ACCEPTANCE_PATH, DEFAULT_PATH as STORE_LAYOUT_PATH,
                                     PICTURES_DIR as SHELF_PICTURES_DIR, READINGS_PATH as SHELF_READINGS_PATH,
                                     load_store_layout, merge_readings)
from src.engine.shelf_reader.photos import PHOTOS_ROOT as SHELF_PHOTOS_ROOT, listed as listed_photos
from src.market.presence import DELIVERY_CATALOG, load_presence
from src.market.listed_prices import snapshot_price_reader
from src.market.recent import recent_market
from src.market.running_out import market_signal, market_store_ids
from src.owner_state.model import OwnerState, answered_cost, device_register

def our_format() -> str:
    """The store's own format, from configs/store.yaml (ADR-036). It decides D-18's market and
    how comparable each competitor's price is (ADR-008)."""
    return get_store().format


@dataclass
class EngineInputs:
    products: Optional[list]
    inventory: Optional[list]        # design §11.1: its own field, so its absence is statable
    sales_monthly: Optional[list]
    sales_daily: Optional[list]      # ADR-030: one row per product per report day; None before the first
    sales_summary: Optional[dict]
    window: Optional[EvidenceWindow]
    observations: Optional[list]
    matches: Optional[list]
    stores: StoreTypeConfig
    withdrawn: Optional[set]
    idle: Optional[set]
    conflicting: Optional[list]   # ADR-019: barcodes whose rows disagree
    store_facts: Optional[dict]   # ADR-033: {facts, rejected}; None when the file is absent
    running_out: Optional[dict]   # ADR-031: the market's signal; None when too thin to say
    boost_picks: Optional[dict]   # ADR-035: the day's sealed picks; None when none were sealed
    inputs_digest: str            # Task 3.1: content addressing over what was read
    vintages: dict
    owner: OwnerState
    policy: Policy
    run_at: datetime
    # F9-S1 §5: ADR-031's rule replayed over the recent window (src/market/recent.py). None
    # whenever `running_out` is None: the replay exists exactly when tonight's signal does.
    market_recent: Optional[dict] = None
    # ADR-037: {fixtures, widths, current, rules, assigned, rejected}; None when the file is absent.
    store_layout: Optional[dict] = None
    # ADR-039: the night's sealed explanations, {on_day, explanations, manifest}; None when none.
    shelf_explanations: Optional[dict] = None
    # ADR-042: the store's shelf photos, [{id, unit, collected, read}]; names and dates only.
    shelf_photos: Optional[list] = None


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


def _cut_reconcile_window(summary_rows: list, monthly: Optional[list],
                          reconcile_before: Optional[str]) -> list:
    """ADR-026. The reconcile figures, cut once per run where the stock date meets the reports.

    The importer used to cut them when it wrote the summary, and this module derived the
    boundary again when it published it (#144): one fact, decided at two moments. They
    agreed every normal night and disagreed on the day no report parsed after a new stock
    count, when a summary cut for the old count survived beside the new one. Measured over a
    copy of the real silver tables, that day published 139 findings cut at February beside an
    August count; a clean import on the August date publishes 439.

    Only months STRICTLY BEFORE the boundary count, because sales after a stock count cannot
    explain a shortfall observed at it. `reconcile_before is None` means the stock date is
    unusable, and then the three figures are None, never a full-history sum: a window nobody
    chose is not a window (#102). Measured against the real reports, treating unknown as
    "every month" flagged 443 products where the true vintage flags 360.

    `reconcile_months` counts distinct months, as its name says. A report can print one
    barcode's line twice (#156), and that is still one month.

    Rows are summed in (barcode, month) order, the order the importer summed them in, so a
    normal night publishes the same figures it did when the importer made the cut.

    Absent is not empty: with no monthly table there is nothing to cut, so the figures are
    None, not 0. And a product whose flows are not numbers gets None rather than a
    TypeError: these sums used to run inside the isolated import step, and here a raise would
    cost every capability its artefact, which SPEC-002 §11 forbids. Detection already skips a
    row whose figures are None.
    """
    known = reconcile_before is not None and monthly is not None
    before = defaultdict(list)
    if known:
        for r in sorted(monthly, key=lambda r: (r["barcode"], r["month"])):
            if r["month"] < reconcile_before:
                before[r["barcode"]].append(r)

    def number(v) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    out = []
    for row in summary_rows:
        rows = before.get(row["barcode"], [])
        ok = known and all(number(r["units"]) and number(r["receipts"]) for r in rows)
        out.append({**row,
                    "reconcile_units": sum((r["units"] for r in rows), 0.0) if ok else None,
                    "reconcile_receipts": sum((r["receipts"] for r in rows), 0.0) if ok else None,
                    "reconcile_months": len({r["month"] for r in rows}) if ok else None})
    return out


def _sales_daily_vintage(rows: Optional[list], policy: Policy, run_at: datetime) -> dict:
    """What the daily reports say arrived, read from the rows present (ADR-030 §4, ADR-004).

    `missing_days` and `deliveries_missing_days` look back over the evidence window plus the
    freshness limit, ending the day before the run: the longest span that could ever feed a
    window (F8-S1 FR-144). Older days are missing from nothing F8 could use, and listing them
    would grow the artefact by a day every night. Days before the first report are not
    missing: the series had not started.

    A report day's deliveries are missing when no row that day carries a receipts figure,
    which is what a report without `כניסות מלאי` imports as (FR-149).
    """
    if not rows:
        return {"first_day": None, "last_day": None, "report_days": 0,
                "missing_days": [], "deliveries_missing_days": []}
    days = sorted({r["day"] for r in rows})
    with_deliveries = {r["day"] for r in rows if r.get("receipts") is not None}
    run_day = run_at.date()
    start = max(date.fromisoformat(days[0]),
                run_day - timedelta(days=policy.order_window_days + policy.order_freshness_days))
    span = [(start + timedelta(days=i)).isoformat() for i in range((run_day - start).days)]
    present = set(days)
    return {"first_day": days[0], "last_day": days[-1], "report_days": len(days),
            "missing_days": [d for d in span if d not in present],
            "deliveries_missing_days": [d for d in span if d in present and d not in with_deliveries]}


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


def _shape_observations(signals, stores: StoreTypeConfig, our_fmt: str) -> Optional[list]:
    if signals is None:
        return None
    excluded = set(stores.excluded_stores(our_fmt)) | set(stores.client_store_ids())
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
                    "affinity": stores.affinity(our_fmt, fmt), "observed_at": s.get("observed_at"),
                    "source_type": "delivery" if _pos(s.get("delivery_catalog_price")) else "price_file"})
    return sorted(out, key=lambda o: (o["barcode"], o["store_id"], o["price"]))


def load_inputs(*, policy: Policy, owner: OwnerState, run_at: datetime, silver_dir: Path = SILVER_POS_ROOT,
                signals_dir: Path = SIGNALS_ROOT / "competitor_product_signals",
                matches_path: Path = MATCHING_ROOT / "product_matches.parquet",
                stores: Optional[StoreTypeConfig] = None,
                store_facts_path: Path = STORE_FACTS_PATH,
                store_layout_path: Path = STORE_LAYOUT_PATH,
                shelf_pictures_dir: Path = SHELF_PICTURES_DIR,
                shelf_readings_path: Optional[Path] = None,
                shelf_acceptance_path: Optional[Path] = None,
                shelf_photos_root: Optional[Path] = None,
                snapshots_root: Path = EXTERNAL_SNAPSHOTS_ROOT) -> EngineInputs:
    stores = stores or load_store_types()
    products_raw = _rows(silver_dir / PRODUCTS_TABLE)
    inventory = _rows(silver_dir / INVENTORY_TABLE)
    products, conflicting = (_shape_products(products_raw, inventory, owner)
                            if products_raw else (None, None))
    # ADR-033. Checked against the departments the catalogue actually prints, so a stated
    # fact can only ever attach to a department that exists. Absent file, absent input.
    store_facts = (load_store_facts(store_facts_path, {p["department"] for p in products or [] if p["department"]})
                   if Path(store_facts_path).exists() else None)
    # ADR-037. Checked against the catalogue as printed, like the facts above. A new copy starts
    # without the file (STARTS_WITHOUT), and an absent file is the missing input no_store_layout.
    store_layout = (load_store_layout(store_layout_path, products or [], shelf_pictures_dir)
                    if Path(store_layout_path).exists() else None)
    # ADR-041: the shelf reader's widths, current facings and pictures, its widths only once its
    # acceptance run has passed (F12-S1 FR-222, FR-223).
    # Beside the layout file they belong to, unless named: a test world's layout never reads a
    # store's readings, and a store's readings never meet another layout.
    folder = Path(store_layout_path).parent
    readings_path = shelf_readings_path or folder / SHELF_READINGS_PATH.name
    store_layout = merge_readings(store_layout, products or [],
                                  readings_path=readings_path,
                                  acceptance_path=shelf_acceptance_path or folder / SHELF_ACCEPTANCE_PATH.name,
                                  pictures_dir=shelf_pictures_dir,
                                  tolerance_mm=policy.shelf_reader_tolerance_mm,
                                  minimum=policy.shelf_reader_acceptance_min)
    # ADR-042: the photos sent from the app, and which the reader has read. The store's own folder
    # beside the store's own layout; a test world's beside its layout, as the readings are.
    if shelf_photos_root is None:
        shelf_photos_root = (SHELF_PHOTOS_ROOT if Path(store_layout_path) == Path(STORE_LAYOUT_PATH)
                             else folder / SHELF_PHOTOS_ROOT.name)
    shelf_photos = listed_photos(shelf_photos_root, readings_path)
    # ADR-039 Decision 5: read like the boost's picks, from the night the plan is dated (the run's).
    from src.engine.shelf_explanation import read as read_explanations   # local: it imports this module
    shelf_explanations = read_explanations(snapshots_root, run_at.date().isoformat())
    monthly = _rows(silver_dir / "sales_monthly.parquet")
    # ADR-030. The importer writes this table only when a daily report parsed, and removes an
    # older one when none did, so its absence is the honest "nothing has arrived yet".
    sales_daily = _rows(silver_dir / "sales_daily.parquet")
    summary_rows = _rows(silver_dir / "sales_summary.parquet")
    window = _window_from_summary(monthly, policy) if monthly else None
    latest_signal = sorted(signals_dir.glob("*.parquet")) if signals_dir.exists() else []
    signals = _rows(latest_signal[-1]) if latest_signal else None
    observations = _shape_observations(signals, stores, our_format())
    # ADR-031. Read from the committed delivery-catalogue snapshots, not from silver: the
    # rule needs every day's listings, and silver holds only the latest. The market is
    # D-18's, the stores at or above the floor less the client, and only days up to the run
    # are read, so a run over an earlier date sees what that night saw.
    presence = load_presence(root=snapshots_root, source_id=DELIVERY_CATALOG)
    market_ids = market_store_ids(presence, stores, our_format())
    running_out = market_signal(presence, market_ids, policy, run_at.date())
    # F9-S1: the same rule, market and night, replayed over the recent window.
    market_recent = (recent_market(presence, market_ids, policy, date.fromisoformat(running_out["on_day"]),
                                   policy.assortment_gap_window_days,
                                   price_of=snapshot_price_reader(snapshots_root))   # D-27
                     if running_out else None)
    # ADR-035: the picks sealed for the night the market evidence describes. Read, never asked
    # for here: asking is the live step's, and print mode must read exactly what it sealed.
    from src.engine.market_boost import read_picks      # local: market_boost imports this module
    boost_picks = read_picks(snapshots_root, running_out["on_day"]) if running_out else None
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
        "sales_daily": _sales_daily_vintage(sales_daily, policy, run_at),
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
    # The boundary the reconcile figures are cut at, published because OQ-201 was closed on
    # the words "window vintages published so misalignment is visible" (§21) — and this was
    # the one window that was not (#144). `vintages.sales` spans every monthly row;
    # reconciliation counts only the months BEFORE the stock count.
    #
    # ADR-026: this is also where the cut is MADE, once per run, so the figures, this
    # published boundary and the capability's window are one fact and cannot disagree.
    # `usable_stock_date` rather than a second derivation, so the cut and the capability's
    # own refusal (reconciliation.run) cannot disagree about what the date is.
    #
    # Null means the same thing it means there: we do not know when the stock was counted,
    # so there is no boundary. It is never the full span by default.
    _as_of = usable_stock_date((vintages["pos"] or {}).get("as_of"),
                               source=(vintages["pos"] or {}).get("as_of_source"))
    reconcile_before = _as_of.strftime("%Y-%m") if _as_of else None
    vintages["sales"]["reconcile_before"] = reconcile_before
    summary = ({r["barcode"]: r for r in _cut_reconcile_window(summary_rows, monthly, reconcile_before)}
               if summary_rows else None)
    vintages["sales"] = {k: vintages["sales"][k]
                         for k in ("months", "first", "last", "full_annual_cycle", "reconcile_before")}
    digest = _digest(products, summary_rows, monthly, observations, matches, policy, owner,
                     reconcile_before, sales_daily, store_facts, running_out, boost_picks, market_recent,
                     store_layout, shelf_explanations, shelf_photos)
    return EngineInputs(products=products, inventory=inventory or None,
                        sales_monthly=monthly, sales_daily=sales_daily, sales_summary=summary, window=window,
                        observations=observations, matches=matches, stores=stores, withdrawn=None, idle=None, conflicting=conflicting,
                        store_facts=store_facts, running_out=running_out, boost_picks=boost_picks,
                        inputs_digest=digest,
                        vintages=vintages, owner=owner, policy=policy, run_at=run_at,
                        market_recent=market_recent, store_layout=store_layout,
                        shelf_explanations=shelf_explanations, shelf_photos=shelf_photos)


# When a row was imported is not what the row says. `sales_import` rewrites its tables on
# every run, so hashing `_imported_at` made two runs over identical data disagree — the
# digest would have reported a change on every run and therefore reported nothing.
#
# Note that products reach this function already shaped, so their provenance columns are
# gone before the exclusion list is consulted: two exports carrying identical rows are the
# same input whichever day of a month they were taken. Across months they are not, because
# ADR-026 cuts the reconcile figures at the count's month and _digest hashes that month.
# The export day is not lost, it is published in vintages.pos.as_of.
_NOT_CONTENT = frozenset({"_imported_at", "_source_kind", "created_at"})


def _content_only(row):
    if not isinstance(row, dict):
        return row
    return {k: v for k, v in row.items() if k not in _NOT_CONTENT}


def _digest(products, summary_rows, monthly, observations, matches, policy, owner,
            reconcile_before: Optional[str], sales_daily: Optional[list] = None,
            store_facts: Optional[dict] = None, running_out: Optional[dict] = None,
            boost_picks: Optional[dict] = None, market_recent: Optional[dict] = None,
            store_layout: Optional[dict] = None, shelf_explanations: Optional[dict] = None,
            shelf_photos: Optional[list] = None) -> str:
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
    # ADR-026: the reconcile figures are cut here at load, so the boundary they are cut at is
    # an input like the rows it cuts. It used to reach the digest only through sums the
    # importer baked into the summary; without this line two runs over identical files, with
    # counts in different months, would share a digest while publishing different findings.
    # The month, not the date: two counts within one month cut identically.
    feed("reconcile_before", [{"month": reconcile_before}])
    # ADR-030. F8's quantities are computed from these rows, so they are an input like the
    # monthly ones. Absent before the first daily report, and hashed as absent.
    feed("sales_daily", sales_daily)
    # ADR-033. The facts a quantity is computed from, with the day each was stated: a
    # corrected schedule is a different input even when nothing else moved. Rejected entries
    # are not facts, and computing nothing from them is the same whatever they said.
    feed("store_facts", None if store_facts is None else store_facts["facts"])
    # ADR-031. What the market was doing is an input to the quantity, like our own sales.
    feed("running_out", running_out)
    # ADR-035: a recorded pick is an input like a delivery catalogue, so the live run (which
    # reloads after sealing) and a reproduction digest the same picks.
    feed("boost_picks", boost_picks)
    # F9-S1: the recent replay is read from the same snapshots, but it is what the finding is
    # computed from, so a reproduction must digest the same one.
    feed("market_recent", market_recent)
    # ADR-037. The shelves a plan is packed into, with the day each was measured or stated. As
    # with the store facts, rejected entries are not facts, so only what is used is digested.
    feed("store_layout", None if store_layout is None else
         [{k: store_layout[k]} for k in ("fixtures", "widths", "current", "rules", "assigned")])
    # ADR-039: a sealed explanation is an input like a sealed pick, so the live run (which reloads
    # after sealing) and a reproduction digest the same text.
    feed("shelf_explanations", None if shelf_explanations is None else shelf_explanations["explanations"])
    # ADR-042: Store layout lists them, so a photo collected or read is a different input. Fed only
    # once there is one, so a store with none digests exactly as before the upload existed.
    if shelf_photos:
        feed("shelf_photos", shelf_photos)
    feed("observations", observations)
    feed("matches", matches)
    feed("policy", policy.as_dict())
    # NOT pulled_at, and NOT the device register (ADR-021). The owner's ANSWERS are an
    # input; the moment we fetched them is not, and hashing it made two runs over identical
    # data disagree — which is precisely the failure this digest exists to detect, so it
    # would have detected nothing. `last_seen_at` moves every time anyone opens the app, so
    # hashing it would re-introduce that defect at a higher frequency.
    # His decisions and revivals are inputs too (ADR-023, revised 2026-09-27): order_quantity
    # reads his approvals, catalogue_lifecycle his revivals, and the measurement every decision.
    feed("owner", {"status": owner.status,
                   "answers": _json.dumps(owner.answers, sort_keys=True, default=str),
                   "outcomes": _json.dumps(owner.outcomes, sort_keys=True, default=str),
                   "revivals": _json.dumps(owner.revivals, sort_keys=True, default=str)})
    return h.hexdigest()
