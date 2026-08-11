"""
T4 / #49 Step 1 — stockout vs delisting.

The issue is explicit about the danger: *"Reading this backwards inverts the
recommendation — telling a manager to stock up on something the market is
dropping."* So the direction is asserted in both directions, by name, and the
binomial maths is checked against values worked out by hand rather than against
whatever the implementation happens to return.

There is only one day of real snapshots so far, so everything here is synthetic.
That is not a workaround: these are the cases where the right answer is known,
which is the only way to be sure the sign is right before 30 days of real data
arrive.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.market.concentration import (  # noqa: E402
    STATE_DELISTING,
    STATE_STOCKOUT,
    STATE_UNCERTAIN,
    binomial_tail_ge,
    classify,
    detect_drops,
    estimate_base_rate,
)
from src.market.presence import PresenceSeries  # noqa: E402

DAY0 = date(2026, 8, 1)


def series_from(daily):
    """daily: list of iterables of (barcode, store) -> a PresenceSeries."""
    s = PresenceSeries()
    for offset, pairs in enumerate(daily):
        day = DAY0 + timedelta(days=offset)
        s.days.append(day)
        s.listings[day] = set(pairs)
    return s


# ---------------------------------------------------------------------------
# The binomial, checked against hand-worked values
# ---------------------------------------------------------------------------

def test_binomial_tail_matches_hand_calculation():
    # P(X >= 2 | n=3, p=0.5) = (3*0.125) + 0.125 = 0.5
    assert binomial_tail_ge(2, 3, 0.5) == pytest.approx(0.5)
    # P(X >= 3 | n=3, p=0.5) = 0.125
    assert binomial_tail_ge(3, 3, 0.5) == pytest.approx(0.125)
    # P(X >= 3 | n=3, p=0.1) = 0.001
    assert binomial_tail_ge(3, 3, 0.1) == pytest.approx(0.001)


def test_binomial_edge_cases_do_not_explode():
    assert binomial_tail_ge(0, 5, 0.2) == 1.0     # X >= 0 always
    assert binomial_tail_ge(6, 5, 0.2) == 0.0     # more drops than branches
    assert binomial_tail_ge(1, 0, 0.2) == 1.0     # nothing carried
    assert binomial_tail_ge(1, 5, 0.0) == 0.0     # drops impossible
    assert binomial_tail_ge(1, 5, 1.0) == 1.0     # drops certain


# ---------------------------------------------------------------------------
# Direction — the part that inverts the advice if wrong
# ---------------------------------------------------------------------------

def test_scattered_drop_is_a_stockout_opportunity():
    # 1 of 12 branches, against a 5% base rate: ordinary.
    concentration, p_value, state = classify(stores_carrying=12, stores_dropped=1, base_rate=0.05)
    assert state == STATE_STOCKOUT
    assert concentration == pytest.approx(1 / 12)
    assert p_value > 0.01


def test_synchronised_drop_is_a_delisting_warning():
    # All 12 branches on the same day, against a 5% base rate: impossible by chance.
    concentration, p_value, state = classify(stores_carrying=12, stores_dropped=12, base_rate=0.05)
    assert state == STATE_DELISTING
    assert concentration == pytest.approx(1.0)
    assert p_value < 0.01


def test_stockout_and_delisting_are_not_swapped():
    """Guards the exact failure the issue names."""
    _, _, scattered = classify(stores_carrying=20, stores_dropped=1, base_rate=0.05)
    _, _, everywhere = classify(stores_carrying=20, stores_dropped=20, base_rate=0.05)
    assert scattered == STATE_STOCKOUT      # opportunity
    assert everywhere == STATE_DELISTING    # warning
    assert scattered != everywhere


def test_high_concentration_alone_is_not_a_delisting():
    # 3 of 3 branches, but the base stockout rate is 50%: p = 0.125, ordinary.
    # Concentration is 1.0 here — without the significance test this would be a
    # false delisting, which suppresses a perfectly good product.
    concentration, p_value, state = classify(stores_carrying=3, stores_dropped=3, base_rate=0.5)
    assert concentration == pytest.approx(1.0)
    assert p_value == pytest.approx(0.125)
    assert state == STATE_STOCKOUT


def test_significance_alone_is_not_a_delisting():
    # 3 of 20 branches at a 1% base rate is statistically surprising, but 15%
    # of branches is not the market walking away.
    concentration, p_value, state = classify(stores_carrying=20, stores_dropped=3, base_rate=0.01)
    assert p_value < 0.01
    assert concentration < 0.6
    assert state == STATE_STOCKOUT


def test_too_few_branches_reports_uncertain_rather_than_guessing():
    # With one branch there is no coordination to detect. Claiming either state
    # would be a coin flip dressed up as an inference.
    _, _, state = classify(stores_carrying=1, stores_dropped=1, base_rate=0.05)
    assert state == STATE_UNCERTAIN


def test_no_carrying_branches_is_uncertain_not_a_crash():
    concentration, p_value, state = classify(stores_carrying=0, stores_dropped=0, base_rate=0.05)
    assert state == STATE_UNCERTAIN
    assert concentration == 0.0


# ---------------------------------------------------------------------------
# Base rate
# ---------------------------------------------------------------------------

def test_base_rate_is_measured_from_the_data():
    # Day 1: 4 listings. Day 2: one gone. 1/4 = 0.25.
    s = series_from([
        [("a", "1"), ("a", "2"), ("b", "1"), ("b", "2")],
        [("a", "1"), ("b", "1"), ("b", "2")],
    ])
    assert estimate_base_rate(s) == pytest.approx(0.25)


def test_base_rate_of_a_single_day_is_zero_not_a_crash():
    assert estimate_base_rate(series_from([[("a", "1")]])) == 0.0


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

def test_detects_a_network_wide_delisting():
    stores = [str(i) for i in range(1, 13)]
    day1 = [("doomed", s) for s in stores] + [("fine", s) for s in stores]
    day2 = [("fine", s) for s in stores]          # doomed vanishes everywhere
    events = detect_drops(series_from([day1, day2]), base_rate=0.05)

    doomed = [e for e in events if e.barcode == "doomed"]
    assert len(doomed) == 1
    assert doomed[0].state == STATE_DELISTING
    assert doomed[0].is_warning is True
    assert doomed[0].is_opportunity is False


def test_detects_a_single_branch_stockout():
    stores = [str(i) for i in range(1, 13)]
    day1 = [("popular", s) for s in stores]
    day2 = [("popular", s) for s in stores if s != "7"]   # one branch runs out
    events = detect_drops(series_from([day1, day2]), base_rate=0.05)

    assert len(events) == 1
    assert events[0].state == STATE_STOCKOUT
    assert events[0].is_opportunity is True
    assert events[0].stores_dropped == 1
    assert events[0].stores_carrying == 12


def test_products_that_never_disappear_produce_no_events():
    stores = ["1", "2", "3"]
    day = [("steady", s) for s in stores]
    assert detect_drops(series_from([day, day, day]), base_rate=0.05) == []


def test_a_gap_in_collection_is_not_read_as_a_mass_delisting():
    """Only usable days enter the series, so 1 Aug pairs with 3 Aug, not with a void.

    If a failed collection day were treated as an empty market, every product on
    earth would look delisted that morning. presence.load_presence() drops such
    days; this asserts the consequence.
    """
    s = PresenceSeries()
    stores = ["1", "2", "3"]
    for day in (date(2026, 8, 1), date(2026, 8, 3)):     # 2 Aug missing
        s.days.append(day)
        s.listings[day] = {("steady", x) for x in stores}
    s.skipped[date(2026, 8, 2)] = "manifest status 'failed'"

    assert detect_drops(s, base_rate=0.05) == []


def test_events_are_ordered_warnings_first():
    stores = [str(i) for i in range(1, 13)]
    day1 = [("gone", s) for s in stores] + [("blip", s) for s in stores]
    day2 = [("blip", s) for s in stores if s != "4"]
    events = detect_drops(series_from([day1, day2]), base_rate=0.05)

    # The delisting must not be buried under scattered stockouts: a missed
    # warning means someone bulk-buys a product the market is dropping.
    assert events[0].barcode == "gone"
    assert events[0].state == STATE_DELISTING
