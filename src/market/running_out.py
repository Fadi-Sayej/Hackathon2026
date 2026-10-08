"""running_out.py — is the nearby market running out of a product? (ADR-031)

The market is D-18's: the delivery-catalogue stores at or above the format floor, less the
client himself. Today that is Wolt Market, Rami Levy In The Neighborhood and Super Alonit
Einat, three stores of three chains.

The stores do not mark sold-out items, they drop them, so running out is read from absence.
And a catalogue change looks exactly like a wave of stockouts from inside one product's
series: on 2026-09-15 Wolt Market replaced a third of its range in a day. What tells them
apart is that **a stockout is scattered, and a catalogue change is synchronised within one
store**. So every rule here is judged store by store:

1. A product is running out at a store on the night asked about when it was listed there on
   `min_listed` of the `prior_days` usable days before its absence began, and has been absent
   for `min_absent` to `max_absent` consecutive usable days ending that night.
2. An absence that began on one of that store's excluded days never counts. A day is excluded
   when more than `catalogue_change_pct` of the store's steady listings vanished at once, or
   when its listed count fell below `thin_collection_ratio` of its own median (its scrape
   failed while the other venues' did not, so the day was still judged usable).
3. A listed item marked not orderable counts as absent that day.

Only days up to the night asked about are read, so a replay of an earlier night sees what that
night saw. Nothing is stored between runs.

A false signal costs twice: it raises an order, and it spends the product's one disagreement
question (D-20). The rule therefore misses the first two days of a real stockout, and stops
counting after seven, on purpose (ADR-031 Consequences).
"""
from __future__ import annotations

import statistics
from collections import Counter
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Set

from src.market.presence import PresenceSeries

# ADR-031 Decision 5: the signal exists only when enough of the last two weeks was observed.
# The count it needs is policy (running_out.signal_min_usable); the span is the calendar
# fortnight the decision names.
SIGNAL_LOOKBACK_DAYS = 14


def market_store_ids(series: PresenceSeries, stores, our_format: str) -> List[str]:
    """D-18: the stores in the series at or above the format floor, less the client."""
    client = set(stores.client_store_ids())
    return sorted(s for s in series.all_stores()
                  if s not in client and stores.affinity(our_format, stores.store_type(s)) >= stores.min_affinity)


def _days_until(series: PresenceSeries, on_day: date) -> List[date]:
    return [d for d in sorted(series.days) if d <= on_day]


def _store_view(series: PresenceSeries, days: List[date], store: str):
    """One store's listed and orderable barcodes per day, read in one pass over each day."""
    listed, orderable = [], []
    for day in days:
        here = {b for (b, s) in series.listings.get(day, ()) if s == store}
        marked = {b for (b, s) in series.unavailable.get(day, ()) if s == store}
        listed.append(here)
        orderable.append(here - marked)
    return listed, orderable


def _excluded(days: List[date], listed: List[Set[str]], policy) -> Dict[date, str]:
    if not listed:
        return {}
    median = statistics.median(len(x) for x in listed)
    out: Dict[date, str] = {}
    for i, day in enumerate(days):
        if len(listed[i]) < policy.running_out_thin_collection_ratio * median:
            out[day] = "thin_collection"
            continue
        if i == 0:
            continue
        tally = Counter(b for prior in listed[max(0, i - policy.running_out_prior_days):i] for b in prior)
        yesterday = {b for b, n in tally.items() if n >= policy.running_out_min_listed} & listed[i - 1]
        if yesterday and len(yesterday - listed[i]) * 100 > policy.running_out_catalogue_change_pct * len(yesterday):
            out[day] = "catalogue_change"
    return out


def excluded_days(series: PresenceSeries, store: str, policy, on_day: date) -> Dict[date, str]:
    """ADR-031 Decision 2, for one store: {day: 'thin_collection' | 'catalogue_change'}.

    Steady listings are those listed on `min_listed` of the `prior_days` usable days before
    the day; with fewer days behind it there are none, and no day can be a catalogue change.

    "Vanish at once" is measured against the day before: of the steady listings the store
    had on the previous usable day, the share gone today. That is the measure ADR-031's
    figures were taken with (Wolt Market, 09-15: 209 of 564, 37.1%; 09-16: 7.8%). Counting
    every steady listing absent today instead would read the day after a reshuffle as a
    second reshuffle, and the one after that as a third, while nothing new vanished.

    A thin day is named as thin even if it also lost its steady listings: that is what a
    failed scrape looks like, and saying so is the more useful of the two.
    """
    days = _days_until(series, on_day)
    return _excluded(days, _store_view(series, days, store)[0], policy)


def _running_out_at(days, present, excluded, policy) -> Dict[str, int]:
    """{barcode: days absent} at one store, for the last of `days`."""
    last = len(days) - 1
    out: Dict[str, int] = {}
    if last < 0:
        return out
    for barcode in set().union(*present):
        absent = 0
        while absent <= policy.running_out_max_absent and absent <= last and barcode not in present[last - absent]:
            absent += 1
        if not policy.running_out_min_absent <= absent <= policy.running_out_max_absent:
            continue
        start = last + 1 - absent
        if start < policy.running_out_prior_days:
            continue                        # not enough history to call it steady
        before = present[start - policy.running_out_prior_days:start]
        if sum(barcode in day for day in before) < policy.running_out_min_listed:
            continue
        if days[start] in excluded:
            continue
        out[barcode] = absent
    return out


def _assess(series: PresenceSeries, market_store_ids: Iterable[str], policy, on_day: date):
    """({barcode: {stores_out, days_absent}}, {store: {day: reason}}) for the night `on_day`."""
    days = _days_until(series, on_day)
    products: dict = {}
    excluded_by_store: Dict[str, Dict[date, str]] = {}
    for store in sorted(market_store_ids):
        listed, orderable = _store_view(series, days, store)
        excluded = excluded_by_store[store] = _excluded(days, listed, policy)
        for barcode, absent in _running_out_at(days, orderable, excluded, policy).items():
            fact = products.setdefault(barcode, {"stores_out": [], "days_absent": {}})
            fact["stores_out"].append(store)
            fact["days_absent"][store] = absent
    # By barcode: they were found by iterating a set, whose order follows the process's string
    # hashing, and the nightly commits this map, so its bytes must repeat when the data does.
    return dict(sorted(products.items())), excluded_by_store


def running_out(series: PresenceSeries, market_store_ids: Iterable[str], policy, on_day: date) -> dict:
    """`{barcode: {stores_out, days_absent}}` for the night `on_day` (ADR-031 Decisions 1–3).

    `stores_out` lists the market stores it is running out at, and `days_absent` how many
    consecutive usable days it has been gone from each. The market is running out of a
    product when at least one of its stores is (Decision 4).
    """
    return _assess(series, market_store_ids, policy, on_day)[0]


def market_signal(series: PresenceSeries, market_store_ids: List[str], policy, run_day: date) -> Optional[dict]:
    """The input F8 reads, or None when the market was not observed well enough to say.

    None when fewer than `signal_min_usable` of the last fourteen calendar days (ending on
    the run's day) were usable, or when no market store is in the series at all: there is
    then no signal, which is different from a signal that nothing is running out.

    Whether the latest usable day is recent enough is the capability's call, not this one's
    (`market_signal_stale`), because it depends on the run's date in a way the rows do not.

    `excluded` lists only the store-days that can change tonight's answer: those among the
    last `max_absent` usable days, where an absence counted tonight could have begun.
    """
    days = _days_until(series, run_day)
    if not days or not market_store_ids:
        return None
    fortnight = {run_day - timedelta(days=i) for i in range(SIGNAL_LOOKBACK_DAYS)}
    if sum(d in fortnight for d in days) < policy.running_out_signal_min_usable:
        return None
    on_day = days[-1]
    products, excluded_by_store = _assess(series, market_store_ids, policy, on_day)
    recent = set(days[-policy.running_out_max_absent:])
    excluded = [{"store_id": store, "day": day.isoformat(), "reason": reason}
                for store in market_store_ids
                for day, reason in sorted(excluded_by_store[store].items())
                if day in recent]
    return {"on_day": on_day.isoformat(), "stores": list(market_store_ids), "excluded": excluded,
            "products": products}
