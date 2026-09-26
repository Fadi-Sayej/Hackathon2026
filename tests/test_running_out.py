"""Phase 5 Task 5.4: the market running out of a product (ADR-031).

A false signal costs twice: it raises an order, and it spends the product's only
disagreement question (D-20). So most of these tests are about what must NOT count.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.store_types import load_store_types  # noqa: E402
from src.engine.policy import load_policy  # noqa: E402
from src.market.presence import PresenceSeries  # noqa: E402
from src.market.running_out import (  # noqa: E402
    excluded_days,
    market_signal,
    market_store_ids,
    running_out,
)

POLICY = load_policy()
DAY0 = date(2026, 8, 1)
W, R = "wolt", "rami"                                   # two market stores, by stand-in id


def build(patterns: dict, *, days: int = 30, filler: int = 20, rotating: dict | None = None,
          not_orderable: dict | None = None) -> PresenceSeries:
    """A series over `days` usable days.

    `patterns` maps (store, barcode) to a string of 1/0 per day. Every store also lists
    `filler` products every day, so one product's absence is a small share of its steady
    listings, as it is in the real catalogues (a few percent a day, ADR-031 Context).
    `rotating[store][i]` adds that many one-day-only listings on day i. `not_orderable`
    maps (store, barcode) to the day indexes it is listed but not orderable.
    """
    s = PresenceSeries()
    stores = {store for (store, _b) in patterns}
    for i in range(days):
        day = DAY0 + timedelta(days=i)
        s.days.append(day)
        pairs = {(f"f{j}", store) for store in stores for j in range(filler)}
        pairs |= {(b, store) for (store, b), pattern in patterns.items() if pattern[i] == "1"}
        for store, per_day in (rotating or {}).items():
            pairs |= {(f"r{i}_{k}", store) for k in range(per_day[i])}
        s.listings[day] = pairs
        s.unavailable[day] = {(b, store) for (store, b), idx in (not_orderable or {}).items() if i in idx}
    return s


def last_day(s: PresenceSeries) -> date:
    return s.days[-1]


def absent_for(k: int, days: int = 30) -> str:
    return "1" * (days - k) + "0" * k


# ── Decision 1 and 3: the length of the absence ──────────────────────────────

@pytest.mark.parametrize("k,counts", [(1, False), (2, True), (7, True), (8, False)])
def test_only_an_absence_of_two_to_seven_usable_days_counts(k, counts):
    s = build({(W, "p"): absent_for(k)})
    out = running_out(s, [W], POLICY, last_day(s))
    assert ("p" in out) is counts
    if counts:
        assert out["p"] == {"stores_out": [W], "days_absent": {W: k}}


def test_it_must_have_been_listed_on_ten_of_the_fourteen_days_before():
    # Absent for 3 days at the end; before that, listed on only 9 of the 14 days.
    pattern_9 = "1" * 13 + "01010101011111" + "000"
    assert pattern_9[13:27].count("1") == 9
    s9 = build({(W, "p"): pattern_9})
    assert "p" not in running_out(s9, [W], POLICY, last_day(s9))
    pattern_10 = "1" * 13 + "01010101111111" + "000"
    assert pattern_10[13:27].count("1") == 10
    s10 = build({(W, "p"): pattern_10})
    assert "p" in running_out(s10, [W], POLICY, last_day(s10))


def test_it_needs_fourteen_usable_days_of_history_before_the_absence():
    s = build({(W, "p"): "1" * 13 + "000"}, days=16)
    assert running_out(s, [W], POLICY, last_day(s)) == {}


def test_a_product_absent_at_one_store_only_names_that_store():
    s = build({(W, "p"): absent_for(3), (R, "p"): "1" * 30})
    assert running_out(s, [W, R], POLICY, last_day(s))["p"] == {"stores_out": [W], "days_absent": {W: 3}}


def test_several_stores_out_are_all_named_with_their_own_lengths():
    s = build({(W, "p"): absent_for(3), (R, "p"): absent_for(5)})
    assert running_out(s, [W, R], POLICY, last_day(s))["p"] == {
        "stores_out": sorted([W, R]), "days_absent": {W: 3, R: 5}}


def test_not_orderable_counts_as_absent():
    """ADR-031 Decision 1: a listed item marked not orderable is absent that day."""
    s = build({(W, "p"): "1" * 30}, not_orderable={(W, "p"): {27, 28, 29}})
    assert running_out(s, [W], POLICY, last_day(s))["p"]["days_absent"] == {W: 3}


def test_only_days_up_to_the_night_asked_about_are_read():
    """A replay of an earlier night must not see what happened after it."""
    s = build({(W, "p"): "1" * 25 + "00111"})
    night = DAY0 + timedelta(days=26)
    assert running_out(s, [W], POLICY, night)["p"]["days_absent"] == {W: 2}


# ── Decision 2: the per-store guard ──────────────────────────────────────────

def test_a_catalogue_change_excludes_the_absences_that_begin_on_it():
    """More than 10% of the store's steady listings vanish at once: a reshuffle, not a
    wave of stockouts. Wolt Market dropped 37.1% of them on 2026-09-15."""
    patterns = {(W, "p"): absent_for(3)}
    patterns.update({(W, f"g{j}"): absent_for(3) for j in range(3)})   # 4 of 24 = 16.7%
    s = build(patterns)
    start = s.days[-3]
    assert excluded_days(s, W, POLICY, last_day(s)) == {start: "catalogue_change"}
    assert running_out(s, [W], POLICY, last_day(s)) == {}


def test_an_ordinary_day_is_not_a_catalogue_change():
    patterns = {(W, "p"): absent_for(3), (W, "g0"): absent_for(3)}       # 2 of 22 = 9.1%
    s = build(patterns)
    assert excluded_days(s, W, POLICY, last_day(s)) == {}
    assert set(running_out(s, [W], POLICY, last_day(s))) == {"p", "g0"}


def test_the_guard_is_per_store():
    """One store's reshuffle excludes nothing at another."""
    patterns = {(W, f"g{j}"): absent_for(3) for j in range(4)}
    patterns[(R, "p")] = absent_for(3)
    s = build(patterns)
    assert excluded_days(s, R, POLICY, last_day(s)) == {}
    assert "p" in running_out(s, [W, R], POLICY, last_day(s))


def test_a_thin_collection_excludes_the_absences_that_begin_on_it():
    """The store's listed count fell below half its own median: its scrape failed, even
    though the day was usable across the other venues."""
    rotating = [40] * 30
    rotating[27] = 5                                    # 20 + 5 listings against a median of 61
    s = build({(W, "p"): absent_for(3)}, rotating={W: rotating})
    start = s.days[-3]
    assert excluded_days(s, W, POLICY, last_day(s)) == {start: "thin_collection"}
    assert running_out(s, [W], POLICY, last_day(s)) == {}


# ── Only the D-18 market ─────────────────────────────────────────────────────

REAL = {
    "wolt_market": "65daeb8779ca7f0a9bf964f3",      # urban_minimarket, 0.7
    "rami_levy": "6315c7a3f00f9e43ec812476",        # urban_minimarket, 0.7
    "super_alonit": "689d9d1ea1357c9968d6850f",     # gas_convenience, 1.0
    "victory": "631480ca6741954d25cf2611",          # supermarket, 0.1: below the floor
    "yom_yom": "68e64a15ddc7ae17b6279458",          # the client himself
}


def test_the_market_is_the_stores_at_or_above_the_floor_less_the_client():
    s = build({(sid, "p"): "1" * 30 for sid in REAL.values()})
    assert market_store_ids(s, load_store_types(), "gas_convenience") == sorted(
        [REAL["wolt_market"], REAL["rami_levy"], REAL["super_alonit"]])


def test_a_store_below_the_floor_never_contributes():
    s = build({(REAL["victory"], "p"): absent_for(3), (REAL["wolt_market"], "q"): absent_for(3)})
    ids = market_store_ids(s, load_store_types(), "gas_convenience")
    assert set(running_out(s, ids, POLICY, last_day(s))) == {"q"}


# ── Decision 5: when the signal exists at all ────────────────────────────────

def test_the_signal_needs_ten_usable_days_in_the_last_fourteen():
    s = build({(W, "p"): absent_for(3)})
    run_day = last_day(s)
    thin = build({(W, "p"): absent_for(3)})
    for day in thin.days[-14:][:5]:                     # 9 of the last 14 remain
        thin.days.remove(day)
        del thin.listings[day]
    assert market_signal(thin, [W], POLICY, run_day) is None
    assert market_signal(s, [W], POLICY, run_day) is not None


def test_the_signal_says_which_night_it_describes_and_what_it_excluded():
    patterns = {(W, f"g{j}"): absent_for(3) for j in range(4)}
    patterns[(R, "p")] = absent_for(3)
    s = build(patterns)
    run_day = last_day(s) + timedelta(days=1)          # the run is the morning after
    signal = market_signal(s, [R, W], POLICY, run_day)
    assert signal["on_day"] == last_day(s).isoformat()
    assert signal["stores"] == [R, W]
    assert signal["excluded"] == [{"store_id": W, "day": s.days[-3].isoformat(), "reason": "catalogue_change"}]
    assert set(signal["products"]) == {"p"}


def test_no_market_store_in_the_series_is_no_signal():
    s = build({(W, "p"): absent_for(3)})
    assert market_signal(s, [], POLICY, last_day(s)) is None


# ── The replay ADR-031 was decided on ────────────────────────────────────────

SNAPSHOTS = ROOT / "data" / "external" / "snapshots"
CATALOGUE = ROOT / "public" / "data" / "catalogue.json"


@pytest.mark.skipif(not (SNAPSHOTS / "2026-09-24").exists() or not CATALOGUE.exists(),
                    reason="the committed market snapshots are not in this checkout")
def test_the_replay_over_the_committed_snapshots():
    """ADR-031's replay, pinned to 2026-08-29 … 2026-09-24 so it stays valid as snapshots
    accumulate: only Wolt Market's 08-31, 09-01 and 09-15 are excluded, and every night
    flags 10 to 40 of his products."""
    from src.market.presence import DELIVERY_CATALOG, load_presence

    series = load_presence(root=SNAPSHOTS, source_id=DELIVERY_CATALOG)
    ids = market_store_ids(series, load_store_types(), "gas_convenience")
    assert ids == sorted([REAL["wolt_market"], REAL["rami_levy"], REAL["super_alonit"]])

    last = date(2026, 9, 24)
    excluded = sorted((sid, d.isoformat()) for sid in ids
                      for d in excluded_days(series, sid, POLICY, last) if d >= date(2026, 8, 29))
    assert excluded == [(REAL["wolt_market"], "2026-08-31"), (REAL["wolt_market"], "2026-09-01"),
                        (REAL["wolt_market"], "2026-09-15")]

    his = {str(p["barcode"]).strip().lstrip("0")
           for p in json.loads(CATALOGUE.read_text(encoding="utf-8"))["products"] if p.get("barcode")}
    nights = [d for d in series.days if date(2026, 8, 29) <= d <= last]
    flagged = {d: len(set(running_out(series, ids, POLICY, d)) & his) for d in nights}
    assert len(nights) >= 20
    assert all(10 <= n <= 40 for n in flagged.values()), flagged
