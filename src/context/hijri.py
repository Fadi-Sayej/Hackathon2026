"""
hijri.py — tabular Islamic (civil) calendar arithmetic.

Deliberately the same calendar the browser used: src/lib/context/hijri.js (removed
2026-09-24, ADR-028) read the Hijri date from `Intl.DateTimeFormat('en-u-ca-islamic-civil')`,
and this reimplements that same tabular civil calendar. Verified against Intl's own output
across a multi-year span in tests/test_islamic_context.py.

ACCURACY, STATED HONESTLY
    The tabular calendar can differ from local moon-sighting by a day. That is
    acceptable for shaping demand — a one-day error at the edge of Ramadan slightly
    mistimes a boost — and is NOT acceptable for anything religiously binding.
    Nothing here is used as such.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import NamedTuple

# Julian day number of 1 Muharram AH 1 in the civil (tabular) reckoning.
ISLAMIC_EPOCH_JD = 1948439.5

RAMADAN = 9
SHAWWAL = 10
DHU_AL_HIJJAH = 12


class Hijri(NamedTuple):
    year: int
    month: int
    day: int


def _gregorian_to_jd(g: date) -> int:
    a = (14 - g.month) // 12
    y = g.year + 4800 - a
    m = g.month + 12 * a - 3
    return (
        g.day
        + (153 * m + 2) // 5
        + 365 * y
        + y // 4
        - y // 100
        + y // 400
        - 32045
    )


def to_hijri(g: date) -> Hijri:
    """Gregorian date -> tabular Islamic civil date."""
    jd = _gregorian_to_jd(g)
    days = jd - int(ISLAMIC_EPOCH_JD + 0.5)
    # 30-year cycle of 10631 days; the civil calendar is purely arithmetic.
    cycle, rem = divmod(days, 10631)
    year_in_cycle = min(int((rem * 30) / 10631) + 1, 30)
    # Walk back if the estimate overshot the year's start.
    while _hijri_to_jd(Hijri(cycle * 30 + year_in_cycle, 1, 1)) > jd:
        year_in_cycle -= 1
    year = cycle * 30 + year_in_cycle
    # In a common year month 12 has 29 days, so the estimate can land on a
    # non-existent 30th instead of rolling into 1 Muharram. Without this the last
    # day of such a year is misread AND the next new year's day is skipped entirely.
    while _hijri_to_jd(Hijri(year + 1, 1, 1)) <= jd:
        year += 1
    month = min(int((jd - _hijri_to_jd(Hijri(year, 1, 1))) / 29.5) + 1, 12)
    while _hijri_to_jd(Hijri(year, month, 1)) > jd:
        month -= 1
    day = jd - _hijri_to_jd(Hijri(year, month, 1)) + 1
    return Hijri(year, month, day)


def _hijri_to_jd(h: Hijri) -> int:
    # ceil, not floor: month 1 has 30 days, so the days-before-month-2 term must
    # round 29.5 up. Flooring it silently shifts roughly half of all dates by a day,
    # which is invisible in spot checks and wrong at every month boundary.
    return int(
        h.day
        + math.ceil(29.5 * (h.month - 1))
        + (h.year - 1) * 354
        + (3 + 11 * h.year) // 30
        + ISLAMIC_EPOCH_JD
        - 0.5
    )


def to_gregorian(h: Hijri) -> date:
    jd = _hijri_to_jd(h)
    a = jd + 32044
    b = (4 * a + 3) // 146097
    c = a - (146097 * b) // 4
    d = (4 * c + 3) // 1461
    e = c - (1461 * d) // 4
    m = (5 * e + 2) // 153
    return date(
        100 * b + d - 4800 + m // 10,
        m + 3 - 12 * (m // 10),
        e - (153 * m + 2) // 5 + 1,
    )


def month_start(g: date, month: int) -> date | None:
    """First Gregorian day of the given Hijri month containing/next after `g`."""
    h = to_hijri(g)
    if h.month == month:
        return to_gregorian(Hijri(h.year, month, 1))
    return None


def next_month_start(g: date, month: int) -> date:
    """Gregorian date on which the next occurrence of that Hijri month begins."""
    h = to_hijri(g)
    year = h.year if h.month < month else h.year + 1
    start = to_gregorian(Hijri(year, month, 1))
    if start <= g:
        start = to_gregorian(Hijri(year + 1, month, 1))
    return start


def days_between(a: date, b: date) -> int:
    return (b - a) // timedelta(days=1)
