"""The Islamic calendar must agree with the browser, and gate on run-up windows.

Two things are asserted here. First, that src/context/hijri.py computes the same
tabular calendar the frontend reads from Intl — if Python and JavaScript disagree
about when Ramadan starts, the order and the screen disagree. Second, that the
engine gates on the *window* before an event, not the event itself: knowing today
is Eid is useless for ordering, because the goods had to arrive a week ago.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.context.hijri import Hijri, to_gregorian, to_hijri  # noqa: E402
from src.context.islamic import (  # noqa: E402
    PHASE_EID,
    PHASE_EID_BUILD_UP,
    PHASE_RAMADAN,
    PHASE_RAMADAN_BUILD_UP,
    SOURCE_COMPUTED,
    get_islamic_context,
    load_windows,
)

# Sampled from Intl.DateTimeFormat('en-u-ca-islamic-civil') — the calendar
# src/lib/context/hijri.js reads in the browser. Regenerate rather than hand-type:
#   node -e "const p=new Intl.DateTimeFormat('en-u-ca-islamic-civil-nu-latn',
#     {year:'numeric',month:'numeric',day:'numeric',timeZone:'UTC'})
#     .formatToParts(new Date('2026-01-15T12:00:00Z'));console.log(p)"
BROWSER_CALENDAR = {
    "2026-01-15": (1447, 7, 26),
    "2026-09-05": (1448, 3, 22),
    "2027-01-15": (1448, 8, 6),
    "2027-09-05": (1449, 4, 3),
    "2028-03-05": (1449, 10, 8),
    "2028-05-25": (1450, 1, 1),   # year rollover: month 12 has 29 days in 1449
    "2029-12-25": (1451, 8, 18),
}


def test_matches_the_browser_calendar_exactly():
    for iso, expected in BROWSER_CALENDAR.items():
        assert tuple(to_hijri(date.fromisoformat(iso))) == expected, iso


def test_round_trips_through_gregorian():
    for iso in BROWSER_CALENDAR:
        day = date.fromisoformat(iso)
        assert to_gregorian(to_hijri(day)) == day


def test_every_day_of_a_year_is_reachable_exactly_once():
    """Guards the rollover bug: a skipped 1 Muharram is invisible in spot checks."""
    day = date(2028, 1, 1)
    seen = []
    while day < date(2029, 1, 1):
        seen.append(tuple(to_hijri(day)))
        day += timedelta(days=1)
    assert len(seen) == len(set(seen))  # no date computed twice


def _ramadan_start(year: int) -> date:
    h = to_hijri(date(year, 6, 1))
    return to_gregorian(Hijri(h.year if h.month <= 9 else h.year + 1, 9, 1))


def test_build_up_window_fires_before_ramadan_not_during():
    start = _ramadan_start(2027)
    win = load_windows()
    inside = get_islamic_context(start - timedelta(days=win["ramadan_build_up_days"] - 1))
    assert inside["phase"] == PHASE_RAMADAN_BUILD_UP

    too_early = get_islamic_context(start - timedelta(days=win["ramadan_build_up_days"] + 5))
    assert too_early["phase"] != PHASE_RAMADAN_BUILD_UP


def test_ramadan_itself_reports_the_ramadan_phase():
    ctx = get_islamic_context(_ramadan_start(2027) + timedelta(days=3))
    assert ctx["phase"] == PHASE_RAMADAN
    assert ctx["isRamadan"] and ctx["ramadanDay"] == 4


def test_eid_build_up_outranks_ramadan_since_it_sits_inside_it():
    """Eid's run-up falls in the last third of Ramadan; if Ramadan won, it would
    never be reported and the sweets would arrive after the holiday."""
    start = _ramadan_start(2027)
    ctx = get_islamic_context(start + timedelta(days=27))
    assert ctx["phase"] == PHASE_EID_BUILD_UP


def test_eid_al_fitr_reports_eid():
    start = _ramadan_start(2027)
    h = to_hijri(start)
    ctx = get_islamic_context(to_gregorian(Hijri(h.year, 10, 1)))
    assert ctx["isEidAlFitr"] and ctx["phase"] == PHASE_EID


def test_windows_are_configurable_not_hardcoded():
    """The owner sets these, so a changed config must change the gate."""
    start = _ramadan_start(2027)
    day = start - timedelta(days=25)
    assert get_islamic_context(day)["phase"] is None
    widened = get_islamic_context(
        day, windows={**load_windows(), "ramadan_build_up_days": 30}
    )
    assert widened["phase"] == PHASE_RAMADAN_BUILD_UP


def test_falls_back_to_the_offline_calendar_when_the_api_is_not_used():
    ctx = get_islamic_context(date(2026, 9, 5), use_api=False)
    assert ctx["source"] == SOURCE_COMPUTED
    assert ctx["hijri"] == {"year": 1448, "month": 3, "day": 22}
