"""
build.py — fetch every demand-shaping signal once per run, and commit the result.

WHY AN ARTIFACT AND NOT A FETCH
    Weather and both calendars used to be fetched in the browser at render time.
    Three consequences, all bad: the Python recommender could not see any of them,
    two page loads could disagree about the same day, and nothing was reproducible
    because the inputs were never written down. A decision you cannot replay is a
    decision you cannot debug.

    So the pipeline fetches once, writes public/data/market-context.json, and both
    the recommender and the frontend read that file. One source of truth, committed
    alongside the recommendations it produced, testable from a fixture.

EVERY SOURCE DEGRADES INDEPENDENTLY
    A dead weather API must not cost us the calendar. Each block carries its own
    `source`, which is null when that source failed, and `status` summarises. The
    artifact is always written: a context with two of three sources is worth more
    than no context at all, provided the caller can see which two.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.common.paths import PROJECT_ROOT
from src.context.demand_signals import build_demand_signals
from src.context.hebrew import get_hebrew_context
from src.context.islamic import get_islamic_context
from src.context.shelf_life import load_shelf_life
from src.context.weather import get_weather

OUTPUT_PATH = PROJECT_ROOT / "public" / "data" / "market-context.json"

SCHEMA_VERSION = 1


def build_market_context(
    day: Optional[date] = None,
    *,
    use_islamic_api: bool = False,
) -> Dict[str, Any]:
    """Assemble the context. Never raises: each source already degrades to nulls."""
    day = day or date.today()

    weather = get_weather()
    hebrew = get_hebrew_context(day)
    islamic = get_islamic_context(day, use_api=use_islamic_api)

    sources = {
        "weather": weather.get("source"),
        "hebrew": hebrew.get("source"),
        "islamic": islamic.get("source"),
    }
    live = [k for k, v in sources.items() if v]
    status = "ok" if len(live) == len(sources) else ("partial" if live else "unavailable")

    demand = build_demand_signals(
        {"weather": weather, "hebrew": hebrew, "islamic": islamic}
    )

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "date": day.isoformat(),
        "status": status,
        "sources": sources,
        "weather": weather,
        "hebrew": hebrew,
        "islamic": islamic,
        # The decision the pipeline made, for the frontend to render rather than
        # recompute. Keyed on real catalog categories.
        "demandSignals": demand["signals"],
        "demandBasis": demand["basis"],
        "activeReasons": demand["activeReasons"],
        # Category shelf-life defaults, published so the browser caps order
        # quantities against the same numbers the pipeline holds.
        "shelfLife": load_shelf_life(),
    }


def write_market_context(
    day: Optional[date] = None,
    *,
    path: Optional[Path] = None,
    use_islamic_api: bool = False,
) -> Dict[str, Any]:
    payload = build_market_context(day, use_islamic_api=use_islamic_api)
    out = path or OUTPUT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": payload["status"],
        "output": str(out),
        "sources": payload["sources"],
        "islamicPhase": payload["islamic"]["phase"],
        "chametzPhase": (payload["hebrew"]["chametz"] or {}).get("phase"),
        "weatherLabel": payload["weather"]["label"],
        "activeReasons": payload["activeReasons"],
    }
