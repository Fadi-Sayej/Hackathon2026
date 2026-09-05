"""hebrew.py — Hebrew calendar and the chametz windows, from Hebcal (free, no key).

Ported from src/lib/context/hebcal.js. The window lengths live in
configs/demand_windows.yaml alongside the Islamic ones, so both calendars are tuned
in one place rather than one in YAML and one hardcoded in JS.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.common.paths import PROJECT_ROOT

BASE_URL = "https://www.hebcal.com/hebcal"
CONFIG_PATH = PROJECT_ROOT / "configs" / "demand_windows.yaml"

PHASE_PESACH = "pesach"
PHASE_CLEAR_STOCK = "clear_stock"
PHASE_STOP_REORDER = "stop_reorder"

_EREV = re.compile(r"^Erev\b", re.I)
_FAST = re.compile(r"(Tzom|Fast of|Ta'anit|Yom Kippur)", re.I)


def load_windows(path: Optional[Path] = None) -> Dict[str, Any]:
    defaults = {
        "chametz_stop_reorder_days": 30,
        "chametz_clear_stock_days": 14,
        "pesach_length_days": 8,
    }
    try:
        loaded = yaml.safe_load((path or CONFIG_PATH).read_text(encoding="utf-8")) or {}
        defaults.update(loaded.get("jewish") or {})
    except (OSError, yaml.YAMLError):
        pass
    return defaults


def fetch_year(year: int, timeout: float = 15.0) -> List[Dict[str, Any]]:
    url = (
        f"{BASE_URL}?v=1&cfg=json&year={year}&month=x"
        "&maj=on&min=on&mod=on&mf=on&geo=none"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "smartshelf/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read())
        return payload.get("items") or []
    except (urllib.error.URLError, OSError, ValueError):
        return []


def find_pesach_start(items: List[Dict[str, Any]]) -> Optional[str]:
    """Match the untranslated title so a Hebrew-locale response cannot break it."""
    for item in items:
        if re.match(r"^Pesach I$", item.get("title", ""), re.I):
            return (item.get("date") or "")[:10] or None
    for item in items:
        title = item.get("title", "")
        if re.match(r"^Pesach\b", title, re.I) and not re.search(r"Erev", title, re.I):
            return (item.get("date") or "")[:10] or None
    return None


def chametz_window(today: date, pesach_start: Optional[str], win: Dict[str, Any]):
    """Where today sits relative to Pesach. None means no gate applies."""
    if not pesach_start:
        return None
    delta = (date.fromisoformat(pesach_start) - today).days
    if -win["pesach_length_days"] < delta <= 0:
        return {"phase": PHASE_PESACH, "action": "BLOCK", "daysToPesach": delta}
    if 0 < delta <= win["chametz_clear_stock_days"]:
        return {"phase": PHASE_CLEAR_STOCK, "action": "CLEAR_STOCK", "daysToPesach": delta}
    if win["chametz_clear_stock_days"] < delta <= win["chametz_stop_reorder_days"]:
        return {"phase": PHASE_STOP_REORDER, "action": "STOP_REORDER", "daysToPesach": delta}
    return None


def get_hebrew_context(day: Optional[date] = None, *, windows=None) -> Dict[str, Any]:
    """Never raises; degrades to a null-filled shape so a dead API stays invisible."""
    day = day or date.today()
    win = windows or load_windows()
    empty = {
        "date": day.isoformat(), "holidays": [], "isErevChag": False,
        "isFastDay": False, "isShabbatEve": day.weekday() == 4,
        "chametz": None, "pesachStart": None, "windows": win, "source": None,
    }
    items = fetch_year(day.year)
    if not items:
        return empty

    pesach = find_pesach_start(items)
    if pesach and (date.fromisoformat(pesach) - day).days < -win["pesach_length_days"]:
        pesach = find_pesach_start(fetch_year(day.year + 1)) or pesach

    todays = [i for i in items if (i.get("date") or "")[:10] == day.isoformat()]
    return {
        "date": day.isoformat(),
        "holidays": [
            {"title": i.get("title"), "hebrew": i.get("hebrew"), "category": i.get("category")}
            for i in todays
        ],
        "isErevChag": any(_EREV.match(i.get("title", "")) for i in todays),
        "isFastDay": any(_FAST.search(i.get("title", "")) for i in todays),
        "isShabbatEve": day.weekday() == 4,  # Friday
        "chametz": chametz_window(day, pesach, win),
        "pesachStart": pesach,
        "windows": win,
        "source": "hebcal",
    }
