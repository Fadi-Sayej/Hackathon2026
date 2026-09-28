"""recent.py — ADR-031's rule replayed over a recent window (F9-S1 §5, FR-167).

F9 asks which products the nearby market ran out of *recently*, not only tonight. It must
not answer with a rule of its own (FR-167): two definitions of "ran out" would decide one
fact twice, and F8 and F9 could disagree about the same night. So this module only replays
`running_out` for each usable night of the window, exactly as that night would have been
judged, and adds nothing to the rule.

It also reads the two listings the capability needs to tell a product the market still sells
from one it has dropped (F9-S1 §5 "still sold"):
- `listed_recent`: orderable at a market store on one of the last `max_absent` usable days;
- `listed_tonight`: orderable on the last night.
"Orderable" is ADR-031's reading: a listed item marked not orderable counts as absent.

Only products flagged in the window are carried, and everything is plain data (ISO dates,
sorted lists), because the result is an engine input: it is hashed into the digest and
replayed by print mode.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, Iterable, List, Set

from src.market.presence import PresenceSeries
from src.market.running_out import running_out


def _orderable(series: PresenceSeries, day: date, market: Set[str]) -> Dict[str, Set[str]]:
    marked = series.unavailable.get(day, set())
    out: Dict[str, Set[str]] = {}
    for barcode, store in series.listings.get(day, ()):
        if store in market and (barcode, store) not in marked:
            out.setdefault(barcode, set()).add(store)
    return out


def recent_market(series: PresenceSeries, market_store_ids: Iterable[str], policy, on_day: date,
                  window_days: int) -> dict:
    """The market's recent running-out, as of the night `on_day` (F9-S1 §5)."""
    market = set(market_store_ids)
    days = sorted(d for d in series.days if d <= on_day)
    first = on_day - timedelta(days=window_days - 1)
    nights = [d for d in days if d >= first]

    flagged: Dict[str, dict] = {}
    for night in nights:
        for barcode, fact in running_out(series, sorted(market), policy, night).items():
            f = flagged.setdefault(barcode, {"nights": [], "stores": set()})
            f["nights"].append(night.isoformat())
            f["stores"].update(fact["stores_out"])

    recent_days = days[-policy.running_out_max_absent:]
    listed_recent: Dict[str, Set[str]] = {}
    for day in recent_days:
        for barcode, stores in _orderable(series, day, market).items():
            if barcode in flagged:
                listed_recent.setdefault(barcode, set()).update(stores)
    tonight = _orderable(series, days[-1], market) if days else {}

    def lists(d: Dict[str, Set[str]]) -> Dict[str, List[str]]:
        return {b: sorted(v) for b, v in sorted(d.items())}

    return {
        "on_day": on_day.isoformat(),
        "window": {"first": first.isoformat(), "last": on_day.isoformat(), "days": window_days,
                   "usable_nights": len(nights)},
        "flagged": {b: {"nights": f["nights"], "stores": sorted(f["stores"])} for b, f in sorted(flagged.items())},
        "listed_recent": lists(listed_recent),
        "listed_tonight": lists({b: s for b, s in tonight.items() if b in flagged}),
        "names": {b: series.product_names[b] for b in sorted(flagged) if b in series.product_names},
    }
