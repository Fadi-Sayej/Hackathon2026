"""Which product a run is, from its shelf tag, or its package where it has no tag (F12-S1 FR-220
v0.10; D-34, D-36; ADR-041 Decision 4).

Only the products the store has sold in the policy's recent window are candidates. A run is a
product when its tag shows a code that is exactly one candidate's, or its tag's name matches
exactly one candidate and the tag's price equals that product's shelf price. With no tag, the
brand, name and size printed on its package must match exactly one candidate in the unit's
departments: every word of the POS name but its size printed there, and no printed size
contradicting the POS name's. Anything else is unknown. The model's confidence is never read:
there is none in its answer to read.
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


# A quantity with its unit, in the three languages and as POS names abbreviate them: 1.5 ליטר,
# 500 גר', 80 ג, 330 מ"ל, 1 ק"ג, 250 غ, 1 لتر, 330 ml. Converted to grams or millilitres.
_UNITS = [
    (r'ק["״׳\']?ג|קילו(?:גרם)?|كغ|kg', "g", 1000.0),
    (r'גר(?:ם)?[׳\']?|ג[׳\']?|غرام|غ|gr?', "g", 1.0),
    (r'מ["״׳\']?ל|مل|ml', "ml", 1.0),
    (r'ס["״׳\']?ל|cl', "ml", 10.0),
    (r'ליטר|ל[׳\']?|لتر|l', "ml", 1000.0),
]
_SIZE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(" + "|".join(u for u, _, _ in _UNITS) + r")(?![\w\u0590-\u05ff\u0600-\u06ff])",
                   re.IGNORECASE)


def size(text: Optional[str]) -> tuple:
    """((amount, unit), text without it): the first quantity printed, in grams or millilitres."""
    if not text:
        return None, text or ""
    text = unicodedata.normalize("NFKC", text)
    match = _SIZE.search(text)
    if not match:
        return None, text
    number = float(match.group(1).replace(",", "."))
    for pattern, unit, factor in _UNITS:
        if re.fullmatch(pattern, match.group(2), re.IGNORECASE):
            return (round(number * factor, 3), unit), text[:match.start()] + " " + text[match.end():]
    return None, text


def _words(text: Optional[str]) -> set:
    return set((normal_name(text) or "").split())


def from_package(package: Optional[dict], pool: list, departments: Iterable[str]) -> tuple:
    """(barcode, None) or (None, why): the single candidate in the unit's departments whose POS words,
    but its size, are all printed on the package, with no printed size contradicting its own."""
    if not package or not any(package.get(k) for k in ("brand", "name")):
        return None, "unreadable_package"
    printed_size, _ = size(package.get("size"))
    if printed_size is None:
        printed_size, _ = size(package.get("name"))
    printed = _words(" ".join(filter(None, (package.get("brand"), size(package.get("name"))[1]))))
    held = set(departments)
    named = []
    for p in pool:
        if p.get("department") not in held:
            continue
        own_size, rest = size(p.get("product_name"))
        words = _words(rest)
        if not words or not words <= printed:
            continue
        if own_size is not None and printed_size is not None and own_size != printed_size:
            continue
        named.append(p)
    if len(named) != 1:
        return None, "package_names_none" if not named else "package_names_two"
    return named[0]["barcode"], None


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


def identify(tag: Optional[dict], pool: list, package: Optional[dict] = None, departments: Iterable[str] = ()) -> tuple:
    """(barcode, None) or (None, why). The tag, where there is one, is the only thing read (D-36)."""
    if not tag:
        return from_package(package, pool, departments) if package else (None, "no_tag")
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
