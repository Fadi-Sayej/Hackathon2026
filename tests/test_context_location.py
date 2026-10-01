# tests/test_context_location.py
"""ADR-036 §2: the weather context is asked for the store's own location.

`weather.py` defaulted to coordinates near YomYom, so every copy would have read one town's
weather. The location is now the store's settings, and the weather call has no default.
"""
from __future__ import annotations

import inspect
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.context.build as build  # noqa: E402
from src.common.store import Location, get_store  # noqa: E402
from src.context.weather import get_weather  # noqa: E402


def test_the_weather_is_asked_for_the_stores_location(monkeypatch):
    asked = {}
    monkeypatch.setattr(build, "get_weather", lambda lat, lon: asked.update(lat=lat, lon=lon) or {"source": None})
    monkeypatch.setattr(build, "get_store", lambda: replace(get_store(), location=Location(lat=31.5, lon=35.1)))
    build.build_market_context(date(2026, 9, 30))
    assert asked == {"lat": 31.5, "lon": 35.1}


def test_the_weather_call_has_no_default_location():
    params = inspect.signature(get_weather).parameters
    assert params["lat"].default is inspect.Parameter.empty
    assert params["lon"].default is inspect.Parameter.empty
