"""
labelled_store.py — validate inference against a store whose truth we own (#49 Step 5).

The issue calls this "the most important step in the track and the strongest
evidence the project can show anyone", and says to build it BEFORE the HMM,
because it is also where the HMM's emission probabilities come from:

    "Any company can *claim* competitor-state inference. Almost nobody has a
     labelled store to measure it against."

WHAT IS ACTUALLY MEASURABLE FOR YOMYOM TODAY
--------------------------------------------
Step 5 says to run inference using only signals visible from outside. YomYom has
exactly one such signal:

    price-file presence   NOT AVAILABLE — YomYom is an independent forecourt
                          shop and appears at no branch of the Alonit feed.
                          Checked, not assumed.
    Wolt orderability     AVAILABLE — its own venue, ~190 products.

So the inference under test reduces to one rule: **orderable on Wolt ⇒ in stock**.
That is not a shortcut, it is the whole externally-visible surface of this store,
and measuring it yields the two numbers Step 3 needs:

    P(orderable | in stock)      = recall
    P(orderable | out of stock)  = false-positive rate

⚠️ THE GROUND TRUTH IS STALE, AND THAT IS NOT HIDEABLE
------------------------------------------------------
The inventory table was imported on 2026-06-06. Every stock figure is that
day's. Comparing it against today's orderability measures a 68-day-old shelf, so
the per-product result is only as good as "did this product's situation change".
`staleness_days` travels with every result for that reason, and the caller is
expected to state it. A fresh POS export turns this from an indicative number
into a real one without a line of code changing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import polars as pl

from src.common.paths import EXTERNAL_SNAPSHOTS_ROOT, SILVER_POS_ROOT
from src.common.store import INVENTORY_TABLE
from src.market.baseline import Score, score_membership_rule, wilson_interval
from src.market.presence import DELIVERY_CATALOG, USABLE_STATUSES

# Our own venue is the store's own entry in configs/store_types.yaml (`role: client`), matched
# by the delivery platform's venue id (ADR-036). It used to be matched by the display name
# "Yom Yom", which ties every copy to one store and breaks on a rename upstream.


def normalise_barcode(value) -> str:
    """Shared barcode form for joining POS to delivery data.

    Leading zeros differ between the two sources for the same physical item, so
    they are stripped on both sides. Any change here must be made in
    src/market/presence.py too.
    """
    return str(value or "").strip().lstrip("0")


def _is_our_venue(store_id, ours: Set[str]) -> bool:
    return bool(store_id) and str(store_id).strip() in ours


def _our_venue_ids() -> Set[str]:
    from src.common.store_types import get_store_types
    return set(get_store_types().client_store_ids())


@dataclass
class LabelledStoreResult:
    days: List[str] = field(default_factory=list)
    universe: int = 0
    matched_to_pos: int = 0
    unmatched_barcodes: List[str] = field(default_factory=list)
    staleness_days: Optional[int] = None
    pos_imported_at: Optional[str] = None
    score: Optional[Score] = None
    per_day: List[dict] = field(default_factory=list)

    @property
    def emission_orderable_given_in_stock(self) -> Optional[float]:
        """P(observed orderable | truly in stock). The HMM needs this."""
        return self.score.recall if self.score else None

    @property
    def emission_orderable_given_out_of_stock(self) -> Optional[float]:
        """P(observed orderable | truly out of stock).

        The issue's whole premise is that this is LOW for an online catalogue and
        HIGH for a price file. Measuring it is what distinguishes the two.
        """
        return self.score.false_positive_rate if self.score else None

    @property
    def predicts_everything(self) -> bool:
        """True when the rule called every product orderable, so it discriminated
        nothing.

        On a single day of our own venue this is unavoidable: the universe IS
        that day's orderable set, so the rule cannot be wrong in the negative
        direction and both emission probabilities collapse to 1.0. The number is
        then a statement about assortment overlap, not about inference. It stops
        being degenerate as soon as a second day lets a product drop off.
        """
        return bool(self.score) and self.score.true_negative == 0 and self.score.false_negative == 0

    def to_dict(self) -> dict:
        return {
            "days": self.days,
            "universe": self.universe,
            "matched_to_pos": self.matched_to_pos,
            "unmatched_barcodes": self.unmatched_barcodes[:20],
            "staleness_days": self.staleness_days,
            "pos_imported_at": self.pos_imported_at,
            "score": self.score.to_dict() if self.score else None,
            "predicts_everything": self.predicts_everything,
            "emissions": {
                "P(orderable | in stock)": self.emission_orderable_given_in_stock,
                "P(orderable | out of stock)": self.emission_orderable_given_out_of_stock,
            },
            "per_day": self.per_day,
        }


def load_our_orderability(root: Optional[Path] = None) -> Dict[str, Set[str]]:
    """{day -> barcodes orderable at our own venue}, usable days only."""
    root = root or EXTERNAL_SNAPSHOTS_ROOT
    out: Dict[str, Set[str]] = {}
    if not root.exists():
        return out
    ours = _our_venue_ids()

    for day_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        manifest = day_dir / "_manifest.json"
        if not manifest.exists():
            continue
        try:
            entry = json.loads(manifest.read_text(encoding="utf-8"))
        except ValueError:
            continue
        status = entry.get("sources", {}).get(DELIVERY_CATALOG, {}).get("status")
        if status not in USABLE_STATUSES:
            continue

        found: Set[str] = set()
        for path in sorted((day_dir / DELIVERY_CATALOG).rglob("*.parquet")):
            if "silver" not in path.name:
                continue
            try:
                frame = pl.read_parquet(path)
            except Exception:
                continue
            if "barcode" not in frame.columns or "store_id" not in frame.columns:
                continue
            for row in frame.select(["barcode", "store_id"]).iter_rows(named=True):
                if not _is_our_venue(row.get("store_id"), ours):
                    continue
                barcode = normalise_barcode(row.get("barcode"))
                if barcode:
                    found.add(barcode)
        if found:
            out[day_dir.name] = found
    return out


def load_pos_stock(silver_root: Optional[Path] = None):
    """({barcode -> in stock?}, imported_at) from the POS inventory snapshot."""
    silver_root = silver_root or SILVER_POS_ROOT
    frame = pl.read_parquet(silver_root / INVENTORY_TABLE)

    imported_at = None
    if "_imported_at" in frame.columns and frame.height:
        values = frame["_imported_at"].drop_nulls()
        if len(values):
            imported_at = str(values[0])

    stock: Dict[str, bool] = {}
    for row in frame.select(["barcode", "current_stock"]).iter_rows(named=True):
        barcode = normalise_barcode(row.get("barcode"))
        if not barcode:
            continue
        try:
            quantity = float(row.get("current_stock") or 0)
        except (TypeError, ValueError):
            continue
        # Any positive reading at any duplicate row counts as in stock: the same
        # item sold from two tills appears twice, and one of them holding zero
        # does not mean the shelf is empty.
        stock[barcode] = stock.get(barcode, False) or quantity > 0
    return stock, imported_at


def validate(
    orderability: Dict[str, Set[str]],
    stock: Dict[str, bool],
    pos_imported_at: Optional[str] = None,
    today: Optional[date] = None,
) -> LabelledStoreResult:
    """Score "orderable ⇒ in stock" against the POS, over our own venue.

    The universe is every barcode the venue has been seen to offer, intersected
    with what the POS knows. A product the store never offers online has no
    orderability signal, so including it would measure the delivery assortment
    rather than the inference.
    """
    result = LabelledStoreResult(days=sorted(orderability))
    if not orderability:
        return result

    ever_offered: Set[str] = set()
    for barcodes in orderability.values():
        ever_offered |= barcodes

    result.universe = len(ever_offered)
    matched = {b for b in ever_offered if b in stock}
    result.matched_to_pos = len(matched)
    result.unmatched_barcodes = sorted(ever_offered - matched)
    result.pos_imported_at = pos_imported_at

    if pos_imported_at:
        try:
            imported = datetime.fromisoformat(str(pos_imported_at).replace("Z", "+00:00")).date()
            result.staleness_days = ((today or date.today()) - imported).days
        except ValueError:
            pass

    if not matched:
        return result

    in_stock = {b for b in matched if stock[b]}
    total = Score(
        rule="orderable on our delivery venue ⇒ in stock",
        label_source="YomYom POS current_stock > 0",
        true_positive=0, false_positive=0, true_negative=0, false_negative=0,
    )
    for day in sorted(orderability):
        day_score = score_membership_rule(
            universe=matched,
            predicted_present=orderability[day],
            actually_available=in_stock,
            rule=total.rule,
            label_source=total.label_source,
        )
        result.per_day.append({"day": day, **day_score.to_dict()})
        total.true_positive += day_score.true_positive
        total.false_positive += day_score.false_positive
        total.true_negative += day_score.true_negative
        total.false_negative += day_score.false_negative

    result.score = total
    return result


def precision_interval(result: LabelledStoreResult):
    if not result.score or result.score.predicted_positive == 0:
        return None
    return wilson_interval(result.score.true_positive, result.score.predicted_positive)
