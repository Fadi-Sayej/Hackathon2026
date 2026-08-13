"""
concentration.py — stockout or delisting? (T4 / #49, Step 1)

No model, no libraries, pure arithmetic. The highest value-to-effort item in the
track, and it works at 30 days of history rather than 60.

THE IDEA
--------
When a product stops appearing at a branch, there are two very different
explanations, and they demand opposite advice:

    scattered across branches and time  → STOCKOUT   → their customer wants it
                                                       today. OPPORTUNITY.
    every branch drops it at once       → DELISTING  → the chain is walking away
                                                       from it. DO NOT BULK BUY.

    concentration(p, t) = stores_dropped(p, t) / stores_carrying(p, t-1)

A high concentration alone is not enough. With three branches, all three dropping
an item on the same day is unremarkable if the per-branch stockout rate is high —
it happens by chance. So the reading is tested against the null hypothesis that
drops are INDEPENDENT across branches, at the observed base rate:

    p_value = P(X >= dropped | Binomial(carrying, base_rate))

    small p  → too synchronised to be chance   → DELISTING
    large p  → consistent with random stockout → STOCKOUT

⚠️ THE DIRECTION IS THE WHOLE POINT.
Reading this backwards tells a manager to stock up on exactly the products the
market is abandoning. Every function below states which way it points, and the
tests assert both directions explicitly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from src.market.presence import PresenceSeries

STATE_STOCKOUT = "STOCKOUT"
STATE_DELISTING = "DELISTING"
STATE_UNCERTAIN = "UNCERTAIN"
# Synchronised and significant, but not yet observed to stay gone. Reported
# separately so a warning is never issued on one day's evidence.
STATE_DELISTING_PROVISIONAL = "DELISTING_PROVISIONAL"

# Days a product must remain absent before a synchronised drop is called a
# delisting rather than a coordinated restock gap. Measured on the first three
# real days: of 11 same-day delisting calls, 9 persisted and 2 were listed again
# the next morning — 18% misclassification against this issue's <10% bar. Both
# false positives would have been caught by requiring a single day of persistence.
CONFIRM_DAYS = 1

# Below this the drop is not synchronised enough to call a delisting whatever the
# p-value says: one branch of twelve dropping an item is a stockout by any reading.
MIN_CONCENTRATION_FOR_DELISTING = 0.6

# Reject independence below this. Deliberately strict: a false DELISTING
# suppresses a product that was merely out of stock, which is the costlier error
# of the two (the acceptance bar in #49 is <10% delisting misclassification).
DELISTING_ALPHA = 0.01

# Below this many carrying branches the binomial has no power — 1 of 1 branch
# dropping is p = base_rate, which never looks significant no matter how real.
MIN_STORES_FOR_INFERENCE = 3


def binomial_tail_ge(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p). Exact, via math.comb — no scipy needed."""
    if n <= 0:
        return 1.0
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    p = min(max(p, 0.0), 1.0)
    if p <= 0.0:
        return 0.0 if k > 0 else 1.0
    if p >= 1.0:
        return 1.0
    return sum(
        math.comb(n, i) * (p ** i) * ((1.0 - p) ** (n - i))
        for i in range(k, n + 1)
    )


@dataclass
class DropEvent:
    barcode: str
    product_name: Optional[str]
    day: date
    previous_day: date
    stores_carrying: int
    stores_dropped: int
    concentration: float
    p_value: float
    state: str
    base_rate: float
    days_absent_since: Optional[int] = None

    @property
    def is_opportunity(self) -> bool:
        """STOCKOUT means a competitor's customer is looking for it right now."""
        return self.state == STATE_STOCKOUT

    @property
    def is_warning(self) -> bool:
        """A confirmed DELISTING means the market is abandoning it — do not bulk buy.

        Provisional ones are deliberately NOT warnings. Acting on one costs a
        product that was merely restocking, and the whole point of the state is
        that we do not yet know.
        """
        return self.state == STATE_DELISTING


def estimate_base_rate(series: PresenceSeries) -> float:
    """Per-branch, per-day probability that a listed product stops being listed.

    Measured from the data rather than assumed, because it varies enormously by
    chain and by how promptly a chain updates its price file. Using a guessed
    rate would make every p-value meaningless.
    """
    carried = 0
    dropped = 0
    for earlier, later in series.consecutive_pairs():
        before = series.listings[earlier]
        after = series.listings[later]
        carried += len(before)
        dropped += len(before - after)
    if carried == 0:
        return 0.0
    return dropped / carried


def classify(
    stores_carrying: int,
    stores_dropped: int,
    base_rate: float,
    alpha: float = DELISTING_ALPHA,
    min_concentration: float = MIN_CONCENTRATION_FOR_DELISTING,
    min_stores: int = MIN_STORES_FOR_INFERENCE,
) -> tuple[float, float, str]:
    """(concentration, p_value, state) for one product on one day.

    DELISTING requires BOTH a high concentration and a p-value too small to be
    chance. Either alone is not enough:

      * concentration without significance — 2 of 2 branches dropping an item
        that is out of stock half the time is unremarkable.
      * significance without concentration — with enough branches a modest share
        can look significant while still being ordinary scattered stockouts.
    """
    if stores_carrying <= 0:
        return 0.0, 1.0, STATE_UNCERTAIN

    concentration = stores_dropped / stores_carrying
    p_value = binomial_tail_ge(stores_dropped, stores_carrying, base_rate)

    if stores_carrying < min_stores:
        # Too few branches to distinguish coordination from coincidence. Saying
        # UNCERTAIN is more useful than a confident coin flip.
        return concentration, p_value, STATE_UNCERTAIN

    if concentration >= min_concentration and p_value <= alpha:
        return concentration, p_value, STATE_DELISTING
    return concentration, p_value, STATE_STOCKOUT


def detect_drops(
    series: PresenceSeries,
    base_rate: Optional[float] = None,
    alpha: float = DELISTING_ALPHA,
    confirm_days: int = CONFIRM_DAYS,
) -> List[DropEvent]:
    """Every product that stopped being listed at one or more branches.

    A synchronised drop is only called DELISTING once the product has stayed
    absent for `confirm_days` subsequent days. Before that it is
    DELISTING_PROVISIONAL: the arithmetic says coordinated, but a chain-wide
    restock gap looks identical on the first morning.
    """
    if base_rate is None:
        base_rate = estimate_base_rate(series)

    # barcode -> the days on which it was listed anywhere, for the persistence check.
    listed_on = {}
    for day, pairs in series.listings.items():
        for barcode, _store in pairs:
            listed_on.setdefault(barcode, set()).add(day)

    events: List[DropEvent] = []
    for earlier, later in series.consecutive_pairs():
        before = series.listings[earlier]
        after = series.listings[later]

        carrying: Dict[str, int] = {}
        dropping: Dict[str, int] = {}
        for barcode, store in before:
            carrying[barcode] = carrying.get(barcode, 0) + 1
            if (barcode, store) not in after:
                dropping[barcode] = dropping.get(barcode, 0) + 1

        for barcode, dropped in dropping.items():
            total = carrying[barcode]
            concentration, p_value, state = classify(total, dropped, base_rate, alpha)

            # How many observed days after the drop the product stayed away.
            later_days = [d for d in series.days if d > later]
            absent_run = 0
            for d in later_days:
                if d in listed_on.get(barcode, set()):
                    break
                absent_run += 1

            if state == STATE_DELISTING:
                if absent_run < confirm_days:
                    if len(later_days) < confirm_days:
                        # Not enough future data yet — say so rather than claim it.
                        state = STATE_DELISTING_PROVISIONAL
                    else:
                        # It came back. That is the definition of a stockout.
                        state = STATE_STOCKOUT

            events.append(
                DropEvent(
                    barcode=barcode,
                    product_name=series.product_names.get(barcode),
                    day=later,
                    previous_day=earlier,
                    stores_carrying=total,
                    stores_dropped=dropped,
                    concentration=round(concentration, 4),
                    p_value=p_value,
                    state=state,
                    base_rate=round(base_rate, 6),
                    days_absent_since=absent_run,
                )
            )

    # Most synchronised first: those are the delisting warnings, and a false
    # negative there is costlier than a false positive on a stockout.
    events.sort(key=lambda e: (-e.concentration, e.p_value))
    return events


def summarise(events: List[DropEvent]) -> Dict[str, object]:
    counts: Dict[str, int] = {}
    for event in events:
        counts[event.state] = counts.get(event.state, 0) + 1
    return {
        "events": len(events),
        "by_state": counts,
        "opportunities": sum(1 for e in events if e.is_opportunity),
        "warnings": sum(1 for e in events if e.is_warning),
        "provisional": sum(1 for e in events if e.state == STATE_DELISTING_PROVISIONAL),
    }
