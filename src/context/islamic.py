"""
islamic.py — Ramadan, both Eids, and the run-up windows that change an order.

WHY THE WINDOWS, NOT THE DATES
    Knowing today is Eid is useless for ordering — the goods had to be on the shelf
    a week ago. So, exactly as hebcal.js gates on CHAMETZ_STOP_REORDER_DAYS rather
    than on Pesach itself, this reports which *window* today falls in. The window
    lengths live in configs/demand_windows.yaml because they are business decisions
    for the store owner, not facts to hardcode.

SOURCE, AND A FALLBACK THAT IS REAL
    Aladhan (https://aladhan.com/islamic-calendar-api, free, no key) is tried first
    when a caller asks for it. It was unreachable from the build environment on
    2026-09-05 (connection timeout), which is precisely why the fallback has to be a
    working calendar rather than a stub: src/context/hijri.py computes the tabular
    Islamic civil calendar arithmetically, offline, and is verified date-for-date
    against the browser's own `islamic-civil` calendar over ~4 years. The fallback
    is the path that actually runs here, and it is exact to that reference.

    Note that Aladhan's calendar endpoint is itself tabular by default, so it does
    not buy accuracy over the arithmetic — it is a cross-check, not an oracle.
    Neither source is moon-sighting, and a ±1 day difference at a month edge is
    possible. That is fine for shaping demand and is not fine for anything
    religiously binding; nothing here is used as such.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.common.paths import PROJECT_ROOT
from src.context.hijri import (
    DHU_AL_HIJJAH,
    RAMADAN,
    SHAWWAL,
    Hijri,
    next_month_start,
    to_gregorian,
    to_hijri,
)

CONFIG_PATH = PROJECT_ROOT / "configs" / "demand_windows.yaml"
ALADHAN_URL = "https://api.aladhan.com/v1/gToH"

SOURCE_ALADHAN = "aladhan"
SOURCE_COMPUTED = "computed_hijri"

# Phases, ordered from earliest to most urgent. A caller that does not recognise a
# phase must treat it as "no gate" rather than guessing.
PHASE_RAMADAN_BUILD_UP = "ramadan_build_up"
PHASE_RAMADAN = "ramadan"
PHASE_EID_BUILD_UP = "eid_build_up"
PHASE_EID = "eid"


def load_windows(path: Optional[Path] = None) -> Dict[str, Any]:
    """Owner-editable window lengths. Falls back to the documented defaults."""
    path = path or CONFIG_PATH
    defaults = {
        "ramadan_build_up_days": 21,
        "eid_al_fitr_build_up_days": 10,
        "eid_al_adha_build_up_days": 10,
        "eid_tail_days": 3,
    }
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        defaults.update(loaded.get("islamic") or {})
    except (OSError, yaml.YAMLError):
        pass
    return defaults


def _aladhan_hijri(day: date, timeout: float = 10.0) -> Optional[Hijri]:
    """Ask Aladhan for the Hijri date. None on any failure — never raises."""
    url = f"{ALADHAN_URL}?date={day.strftime('%d-%m-%Y')}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "smartshelf/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read())
        h = payload["data"]["hijri"]
        return Hijri(int(h["year"]), int(h["month"]["number"]), int(h["day"]))
    except (urllib.error.URLError, OSError, KeyError, ValueError, TypeError):
        return None


def get_islamic_context(
    day: Optional[date] = None,
    *,
    use_api: bool = False,
    windows: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Everything the reorder decision needs from the Islamic calendar for one day.

    Never raises and never returns a partial shape: a missing factor must vanish
    without trace rather than take the pipeline down.
    """
    day = day or date.today()
    win = windows or load_windows()

    hijri = _aladhan_hijri(day) if use_api else None
    source = SOURCE_ALADHAN if hijri else SOURCE_COMPUTED
    if hijri is None:
        hijri = to_hijri(day)

    is_ramadan = hijri.month == RAMADAN
    is_eid_fitr = hijri.month == SHAWWAL and hijri.day <= win["eid_tail_days"]
    is_eid_adha = (
        hijri.month == DHU_AL_HIJJAH
        and 10 <= hijri.day <= 10 + win["eid_tail_days"]
    )

    ramadan_start = (
        to_gregorian(Hijri(hijri.year, RAMADAN, 1)) if is_ramadan
        else next_month_start(day, RAMADAN)
    )
    days_to_ramadan = (ramadan_start - day).days
    eid_fitr_start = to_gregorian(
        Hijri(hijri.year if hijri.month <= SHAWWAL else hijri.year + 1, SHAWWAL, 1)
    )
    days_to_eid_fitr = (eid_fitr_start - day).days
    adha_start = to_gregorian(
        Hijri(hijri.year if hijri.month <= DHU_AL_HIJJAH else hijri.year + 1, DHU_AL_HIJJAH, 10)
    )
    days_to_eid_adha = (adha_start - day).days

    # Most urgent wins. Eid sits inside the last third of Ramadan, so its build-up
    # must outrank the Ramadan phase or it would never be reported.
    phase = None
    if is_eid_fitr or is_eid_adha:
        phase = PHASE_EID
    elif 0 < days_to_eid_fitr <= win["eid_al_fitr_build_up_days"]:
        phase = PHASE_EID_BUILD_UP
    elif 0 < days_to_eid_adha <= win["eid_al_adha_build_up_days"]:
        phase = PHASE_EID_BUILD_UP
    elif is_ramadan:
        phase = PHASE_RAMADAN
    elif 0 < days_to_ramadan <= win["ramadan_build_up_days"]:
        phase = PHASE_RAMADAN_BUILD_UP

    return {
        "date": day.isoformat(),
        "hijri": {"year": hijri.year, "month": hijri.month, "day": hijri.day},
        "isRamadan": is_ramadan,
        "ramadanDay": hijri.day if is_ramadan else None,
        "isLastTenNights": is_ramadan and hijri.day >= 21,
        "isEidAlFitr": is_eid_fitr,
        "isEidAlAdha": is_eid_adha,
        "ramadanStart": ramadan_start.isoformat(),
        "daysToRamadan": days_to_ramadan,
        "daysToEidAlFitr": days_to_eid_fitr,
        "phase": phase,
        "windows": win,
        "source": source,
    }
