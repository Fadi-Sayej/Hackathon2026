"""listed_prices.py — what a market store listed a product at on one day (D-27, F9-S1 FR-168).

The price the card shows beside an assortment-gap finding: the delivery app's listed price,
read from the same silver delivery-catalogue snapshot `presence.py` reads for listings, with
the same barcode normalisation (leading zeros stripped) and the same file choice (silver only,
so no row is read twice). A listed price is evidence of what the market charges, never money
at stake, and a price the snapshot does not carry is None, never zero (D-3).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import polars as pl

from src.market.presence import DELIVERY_CATALOG


def _amount(raw) -> Optional[float]:
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _read(day_dir: Path) -> Dict[Tuple[str, str], dict]:
    out: Dict[Tuple[str, str], dict] = {}
    source = day_dir / DELIVERY_CATALOG
    if not source.exists():
        return out
    for path in sorted(source.rglob("*.parquet")):
        if "silver" not in path.name:
            continue
        try:
            frame = pl.read_parquet(path)
        except Exception:
            continue
        if not {"barcode", "store_id", "price"} <= set(frame.columns):
            continue
        cols = ["barcode", "store_id", "price"] + (["sale_price"] if "sale_price" in frame.columns else [])
        for row in frame.select(cols).iter_rows(named=True):
            barcode = str(row.get("barcode") or "").strip().lstrip("0")
            store = str(row.get("store_id") or "").strip()
            price = _amount(row.get("price"))
            if not barcode or not store or price is None or (barcode, store) in out:
                continue
            out[(barcode, store)] = {"price": price, "sale_price": _amount(row.get("sale_price"))}
    return out


def snapshot_price_reader(root: Path) -> Callable[[date, str, str], Optional[dict]]:
    """price_of(day, barcode, store) over the snapshots under `root`, each day read once."""
    cache: Dict[date, Dict[Tuple[str, str], dict]] = {}

    def price_of(day: date, barcode: str, store: str) -> Optional[dict]:
        if day not in cache:
            cache[day] = _read(Path(root) / day.isoformat())
        return cache[day].get((barcode, store))
    return price_of
