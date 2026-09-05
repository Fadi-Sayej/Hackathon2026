"""Demand multipliers must key on the categories that actually exist.

The bug this guards: the browser's signal table shipped English keys against a
Hebrew catalog, so the intersection was empty and weather and holidays never moved
a single order while appearing to.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.context.demand_signals import build_demand_signals  # noqa: E402

GROCERY = "מוצרי מכולת"
DRINKS = "משקאות"
SWEETS = "חטיפים מתוקים"
ICE_CREAM = "גלידות"


def ctx(*, weather="mild", phase=None, chametz=None, shabbat_eve=False):
    return {
        "weather": {"label": weather},
        "islamic": {"phase": phase},
        "hebrew": {"chametz": {"phase": chametz} if chametz else None,
                   "isShabbatEve": shabbat_eve},
    }


def test_keys_are_real_catalog_categories():
    out = build_demand_signals(ctx(weather="hot"))
    assert DRINKS in out["signals"]
    assert all(any("֐" <= ch <= "׿" for ch in k) for k in out["signals"])


def test_hot_weather_lifts_drinks_and_ice_cream():
    s = build_demand_signals(ctx(weather="hot"))["signals"]
    assert s[DRINKS] > 1 and s[ICE_CREAM] > 1


def test_quiet_day_moves_nothing():
    """An empty table is a real answer, not a missing one."""
    out = build_demand_signals(ctx())
    assert out["signals"] == {}
    assert out["activeReasons"] == []


def test_ramadan_lifts_groceries_and_damps_daytime_snacking():
    s = build_demand_signals(ctx(phase="ramadan"))["signals"]
    assert s[GROCERY] > 1
    assert s["חטיפים מלוחים"] < 1


def test_eid_build_up_lifts_sweets_before_the_day_itself():
    s = build_demand_signals(ctx(phase="eid_build_up"))["signals"]
    assert s[SWEETS] > 1.2


def test_chametz_window_damps_the_proxy_aisles():
    s = build_demand_signals(ctx(chametz="stop_reorder"))["signals"]
    assert s[GROCERY] < 1


def test_two_live_reasons_compound_rather_than_overwrite():
    s = build_demand_signals(ctx(weather="hot", phase="eid_build_up"))["signals"]
    hot_only = build_demand_signals(ctx(weather="hot"))["signals"]
    assert s[DRINKS] > hot_only[DRINKS]


def test_every_multiplier_records_why_it_fired():
    out = build_demand_signals(ctx(weather="hot", phase="ramadan"))
    for category in out["signals"]:
        assert out["basis"][category], category
