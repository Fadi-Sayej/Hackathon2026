"""
demand_signals.py — turn market context into per-category demand multipliers.

WHY THIS MOVED OUT OF THE BROWSER
    reorderEngine.js read `marketContext.demandSignals[product.category]` and
    multiplied its velocity by it. The signal table it read shipped English keys
    ('Cold Drinks', 'Snacks', 'Ice Cream') while every category in the YomYom
    catalog is Hebrew ('משקאות', 'חטיפים מלוחים', 'גלידות'). Verified on
    2026-09-05: the intersection is empty, so the multiplier was 1 for every real
    product and weather and holidays never moved a single order. The context was
    decorative.

    Multipliers are now computed here, keyed on the categories that actually exist,
    written into public/data/market-context.json, and applied by the Python
    recommender, product_recommendations.py, until it stopped running on 2026-09-13; it
    was deleted on 2026-09-24 (Phase 4 Task 4.2). reorderEngine.js consumed the result
    until ADR-028 removed it the same day. So nothing applies these multipliers today;
    ADR-028 keeps them published for V2.

THESE ARE STARTING VALUES, NOT MEASUREMENTS
    Nothing in the data yet proves any of these numbers: a full Ramadan has not been
    observed with this pipeline running, and the sales history is seven monthly
    aggregates. They are deliberately modest, they are all in one table so the store
    owner can argue with them, and `basis` records why each one fired so a
    recommendation can always explain itself.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Real catalog categories (Hebrew), by the demand story they belong to.
COLD_DRINKS = ("משקאות", "מחלקת -barista")
FROZEN = ("גלידות", "קפואים מצוננים")
CHILLED = ("מוצרי מקרר",)
SWEET_SNACKS = ("חטיפים מתוקים",)
SALTY_SNACKS = ("חטיפים מלוחים", "פיצוחים")
GROCERY = ("מוצרי מכולת",)
PRODUCE = ("פירות וירקות",)
GIFTS = ("מוצרי יום הולדת ו מתנות", "תכשיטים לילדות קטנות")
HOUSEHOLD = ("מוצרי בית", "מוצרי ניקיון ו טיפוח אישי")

# Bread, pasta, biscuits and beer are chametz. The catalog has no chametz-level
# breakdown, so the grocery and sweet-snack aisles are the closest honest proxy —
# and the gate is a flag for the owner to confirm, never an automatic block.
CHAMETZ_PROXY = GROCERY + SWEET_SNACKS


def _apply(signals: Dict[str, float], basis: Dict[str, List[str]],
           categories: Tuple[str, ...], factor: float, reason: str) -> None:
    for category in categories:
        # Multiplicative so two live reasons compound rather than overwrite.
        signals[category] = round(signals.get(category, 1.0) * factor, 3)
        basis.setdefault(category, []).append(reason)


def build_demand_signals(context: Dict[str, Any]) -> Dict[str, Any]:
    """Category multipliers implied by today's weather and both calendars."""
    signals: Dict[str, float] = {}
    basis: Dict[str, List[str]] = {}

    weather = context.get("weather") or {}
    islamic = context.get("islamic") or {}
    hebrew = context.get("hebrew") or {}

    label = weather.get("label")
    if label == "hot":
        _apply(signals, basis, COLD_DRINKS, 1.20, "hot_weather")
        _apply(signals, basis, FROZEN, 1.15, "hot_weather")
    elif label == "cold":
        _apply(signals, basis, COLD_DRINKS, 0.90, "cold_weather")
        _apply(signals, basis, FROZEN, 0.85, "cold_weather")
    elif label == "rainy":
        _apply(signals, basis, FROZEN, 0.90, "rainy")

    phase = islamic.get("phase")
    if phase == "ramadan_build_up":
        # Households stock the pantry before the month starts.
        _apply(signals, basis, GROCERY, 1.25, "ramadan_build_up")
        _apply(signals, basis, PRODUCE, 1.15, "ramadan_build_up")
        _apply(signals, basis, CHILLED, 1.15, "ramadan_build_up")
    elif phase == "ramadan":
        # Daytime trade collapses and the evening concentrates it; net effect on a
        # convenience store is up on food, down on impulse daytime snacking.
        _apply(signals, basis, GROCERY, 1.20, "ramadan")
        _apply(signals, basis, CHILLED, 1.20, "ramadan")
        _apply(signals, basis, PRODUCE, 1.15, "ramadan")
        _apply(signals, basis, SALTY_SNACKS, 0.85, "ramadan_daytime_fasting")
    elif phase == "eid_build_up":
        _apply(signals, basis, SWEET_SNACKS, 1.35, "eid_build_up")
        _apply(signals, basis, GIFTS, 1.30, "eid_build_up")
        _apply(signals, basis, COLD_DRINKS, 1.10, "eid_build_up")
    elif phase == "eid":
        _apply(signals, basis, SWEET_SNACKS, 1.20, "eid")
        _apply(signals, basis, GIFTS, 1.15, "eid")

    chametz = (hebrew.get("chametz") or {}).get("phase")
    if chametz == "stop_reorder":
        _apply(signals, basis, CHAMETZ_PROXY, 0.75, "chametz_stop_reorder")
    elif chametz in ("clear_stock", "pesach"):
        _apply(signals, basis, CHAMETZ_PROXY, 0.50, f"chametz_{chametz}")

    if hebrew.get("isShabbatEve"):
        _apply(signals, basis, GROCERY, 1.10, "shabbat_eve")
        _apply(signals, basis, CHILLED, 1.10, "shabbat_eve")

    return {
        "signals": signals,
        "basis": basis,
        # An empty table is a real answer — a mild Tuesday in no window moves nothing.
        "activeReasons": sorted({r for reasons in basis.values() for r in reasons}),
    }
