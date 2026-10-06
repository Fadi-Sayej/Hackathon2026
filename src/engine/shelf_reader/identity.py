"""Which product a run is, from its shelf tag (F12-S1 FR-220, D-34; ADR-041 Decision 4).

Only the products the store has sold in the policy's recent window are candidates. A run is a
product when its tag shows a code that is exactly one candidate's, or its tag's name matches
exactly one candidate and the tag's price equals that product's shelf price. Anything else is
unknown. The model's confidence is never read: there is none in its answer to read.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from typing import Iterable, Optional

from src.engine.model import norm_barcode


def normal_name(name: Optional[str]) -> Optional[str]:
    """Spaces and punctuation are not part of a name: the tag and the POS print them differently."""
    if not name:
        return None
    text = unicodedata.normalize("NFKC", name)
    text = "".join(" " if unicodedata.category(c)[0] in "PZS" else c for c in text)
    text = " ".join(text.split()).casefold()
    return text or None


def _digits(code: Optional[str]) -> Optional[str]:
    digits = re.sub(r"\D", "", code or "")
    return digits or None


def _price(text: Optional[str]) -> Optional[float]:
    match = re.search(r"\d+(?:[.,]\d{1,2})?", (text or "").replace("٫", "."))
    return round(float(match.group(0).replace(",", ".")), 2) if match else None


def candidates(products: Iterable[dict], sales_daily: Iterable[dict], sales_monthly: Iterable[dict],
               today: date, window_days: int) -> list:
    """The catalogue products with a sale in the window, by the daily reports or a monthly one
    whose month overlaps it. With no sale in the window, no product can be named."""
    since = today - timedelta(days=window_days)
    sold = {r["barcode"] for r in sales_daily or () if (r.get("units") or 0) > 0
            and since.isoformat() <= str(r.get("day")) <= today.isoformat()}
    for r in sales_monthly or ():
        month = str(r.get("month") or "")[:7]
        if (r.get("units") or 0) > 0 and month and month >= since.isoformat()[:7] and month <= today.isoformat()[:7]:
            sold.add(r["barcode"])
    return [p for p in products or () if p.get("barcode") in sold]


def identify(tag: Optional[dict], pool: list) -> tuple:
    """(barcode, None) or (None, why)."""
    if not tag:
        return None, "no_tag"
    code = _digits(tag.get("code"))
    if code:
        named = [p for p in pool if code in {norm_barcode(p["barcode"]), re.sub(r"\D", "", str(p["barcode"]))}]
        if len(named) == 1:
            return named[0]["barcode"], None
        if len(named) > 1:
            return None, "code_names_two"
    name = normal_name(tag.get("name"))
    if not name:
        return None, "code_unknown" if code else "unreadable_tag"
    named = [p for p in pool if normal_name(p.get("product_name")) == name]
    if len(named) != 1:
        return None, "name_names_none" if not named else "name_names_two"
    price = _price(tag.get("price"))
    shelf = named[0].get("shelf_price")
    if price is None or shelf is None:
        return None, "price_unreadable"
    if round(float(shelf), 2) != price:
        return None, "price_differs"
    return named[0]["barcode"], None
