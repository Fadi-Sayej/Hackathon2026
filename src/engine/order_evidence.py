# src/engine/order_evidence.py
"""The evidence an order quantity is computed from (F8-S1 FR-143 … FR-146). Pure functions.

Only report days count: sales and deliveries per product per day (ADR-030). A report longer
than a day is never divided into days (INV-070), so a monthly row that reached this module
would be exactly that mistake, and is refused rather than read.

Three kinds of day, kept apart everywhere below:
- a **report day** the product has a row on: it sold what the row says;
- a **report day** it has no row on: inside a department the evidence itemises, it sold
  nothing that day (ASM-065);
- a **missing day**, with no report at all: left out of every mean, never read as zero
  (INV-072).

And one more, per product: a report day on which its units are unknown, because the cell
was blank or two reprinted lines disagree (#156). That day is not observed for that product,
so it too is left out of its mean, and no sale is assumed on it.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, List, Optional, Tuple

WEEK = 7


@dataclass(frozen=True)
class Window:
    """The evidence window: the `window_days` ending on the latest report day (FR-144)."""
    first_day: str
    last_day: str
    report_days: Tuple[str, ...]                 # the report days inside it, oldest first
    weeks: Tuple[Tuple[str, str], ...]           # 7-day blocks back from last_day, oldest first

    def week_of(self, day: str) -> Optional[int]:
        for i, (start, end) in enumerate(self.weeks):
            if start <= day <= end:
                return i
        return None

    def to_dict(self) -> dict:
        return {"first_day": self.first_day, "last_day": self.last_day,
                "report_days": len(self.report_days), "weeks": [list(w) for w in self.weeks]}


def _day(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def evidence_window(report_days: Iterable, policy, run_at: datetime) -> Optional[Window]:
    """The window, or None when there is none (FR-144).

    It exists only when its latest report day is at most `order.freshness_days` before the
    run, it holds at least `order.min_report_days` report days, and each of its weeks holds
    at least one. A report day after the run is not read: a misnamed file cannot become the
    last day of the evidence.
    """
    run_day = run_at.date()
    days = sorted({_day(d) for d in report_days if _day(d) <= run_day})
    if not days:
        return None
    last = days[-1]
    if (run_day - last).days > policy.order_freshness_days:
        return None
    return window_between(last - timedelta(days=policy.order_window_days - 1), last, days, policy)


def window_between(first, last, report_days: Iterable, policy) -> Optional[Window]:
    """The span `first` … `last` held to FR-144's rules, or None when it fails them.

    It must hold at least `order.min_report_days` report days, and each of its 7-day weeks,
    counted back from `last`, at least one. F8's own window is the span ending on its latest
    report day (`evidence_window`). F12-S1's before and after windows (FR-202) are spans fixed
    by a plan and an arrangement. Both are judged here, so the rule is written once.
    """
    first, last = _day(first), _day(last)
    inside = sorted({_day(d) for d in report_days if first <= _day(d) <= last})
    if len(inside) < policy.order_min_report_days:
        return None
    weeks = []
    end = last
    while end >= first:
        start = max(first, end - timedelta(days=WEEK - 1))
        weeks.append((start, end))
        end = start - timedelta(days=1)
    weeks.reverse()
    if any(not any(start <= d <= end for d in inside) for start, end in weeks):
        return None
    return Window(first_day=first.isoformat(), last_day=last.isoformat(),
                  report_days=tuple(d.isoformat() for d in inside),
                  weeks=tuple((s.isoformat(), e.isoformat()) for s, e in weeks))


def _daily(rows: Iterable[dict]) -> List[dict]:
    rows = list(rows)
    for r in rows:
        if "day" not in r:
            raise ValueError(
                f"not a daily row: {sorted(r)}. Quantities come only from report days, and a longer "
                "report is never divided into days (F8-S1 INV-070)")
    return rows


def _units_by_day(rows: List[dict], window: Window) -> dict:
    """{day: units} over the window's report days where this product's units are known."""
    printed = defaultdict(list)
    for r in rows:
        if r["day"] in window.report_days:
            printed[r["day"]].append(r.get("units"))
    known = {}
    for day in window.report_days:
        lines = printed.get(day)
        if not lines:
            known[day] = 0.0                         # a report day without it: no sale (ASM-065)
            continue
        values = set(lines)
        if None in values or len(values) > 1:
            continue                                 # blank, or reprints that disagree: unknown
        known[day] = float(lines[0])
    return known


def product_evidence(rows: Iterable[dict], window: Window) -> dict:
    """One product's evidence over the window (FR-145, FR-146, AC-140).

    `daily_mean` is the units sold on the report days its units are known, over the number
    of those days: a mean of observed days, not a division of any report. `moving` is a sale
    in every one of the window's weeks.
    """
    known = _units_by_day(_daily(rows), window)
    weekly = [0.0] * len(window.weeks)
    for day, units in known.items():
        weekly[window.week_of(day)] += units
    total = sum(known.values())
    return {"moving": bool(known) and all(w > 0 for w in weekly),
            "weekly_units": weekly,
            "units_in_window": total,
            "report_days": len(known),
            "daily_mean": total / len(known) if known else None}


def stocks(rows: Iterable[dict], window: Optional[Window], latest_count: Optional[float], *,
           itemised: bool) -> bool:
    """Whether he stocks the product (F8-S1 §5, the FR-158 population).

    In a department the evidence itemises: the window records a sale or a delivery of it.
    In one it does not (FR-156): his latest recorded count shows it above zero. An unknown
    count is not "stocks": the question it would raise is asked once, ever (D-20). Never
    F4's withdrawn class (C-67, D-14).
    """
    if not itemised:
        return latest_count is not None and latest_count > 0
    if window is None:
        return False
    for r in _daily(rows):
        if r["day"] not in window.report_days:
            continue
        if (r.get("units") or 0) > 0 or (r.get("receipts") or 0) > 0:
            return True
    return False
