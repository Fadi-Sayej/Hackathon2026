"""Phase 6 Task 6.1: ADR-031's rule replayed over F9-S1's recent window (FR-167, §5).

F9 must not carry a second definition of "ran out" (FR-167), so every test here checks the
replay against `running_out` itself, or against what that rule already pins in
tests/test_running_out.py. What is new is only the window, and the two listings the
capability reads to tell "still sold" from "dropped".
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engine.policy import load_policy  # noqa: E402
from src.market.presence import PresenceSeries  # noqa: E402
from src.market.recent import recent_market  # noqa: E402
from src.market.running_out import running_out  # noqa: E402

POLICY = load_policy()
DAY0 = date(2026, 8, 1)
W, R, X = "wolt", "rami", "outside"          # two market stores, and one that is not


def build(patterns: dict, *, days: int = 30, filler: int = 20, not_orderable: dict | None = None,
          names: dict | None = None) -> PresenceSeries:
    """`patterns` maps (store, barcode) to a string of 1/0 per usable day. Every store also
    lists `filler` steady products, so one product's absence is a small share (ADR-031)."""
    s = PresenceSeries()
    stores = {store for (store, _b) in patterns}
    for i in range(days):
        day = DAY0 + timedelta(days=i)
        s.days.append(day)
        pairs = {(f"f{j}", store) for store in stores for j in range(filler)}
        pairs |= {(b, store) for (store, b), pattern in patterns.items() if pattern[i] == "1"}
        s.listings[day] = pairs
        s.unavailable[day] = {(b, store) for (store, b), idx in (not_orderable or {}).items() if i in idx}
    s.product_names.update(names or {})
    return s


def present_then_absent(k: int, days: int = 30) -> str:
    return "1" * (days - k) + "0" * k


def recent(s, market=(W, R), window_days=14, on_day=None):
    return recent_market(s, list(market), POLICY, on_day or s.days[-1], window_days)


def test_tonights_flags_are_exactly_the_rules_flags_for_tonight():
    s = build({(W, "a"): present_then_absent(3), (R, "b"): present_then_absent(5),
               (W, "c"): present_then_absent(1), (R, "d"): "1" * 30})
    out = recent(s)
    tonight = s.days[-1].isoformat()
    flagged_tonight = {b for b, f in out["flagged"].items() if tonight in f["nights"]}
    assert flagged_tonight == set(running_out(s, [W, R], POLICY, s.days[-1]))
    assert flagged_tonight == {"a", "b"}


def test_each_night_in_the_window_is_judged_by_the_rule_as_it_stood_that_night():
    # Gone for 4 days: absent 2, 3 and 4 days on the last three nights, so flagged on three.
    s = build({(W, "a"): present_then_absent(4)})
    nights = recent(s)["flagged"]["a"]["nights"]
    assert nights == [d.isoformat() for d in s.days[-3:]]
    for day in s.days[-3:]:
        assert "a" in running_out(s, [W], POLICY, day)


def test_a_night_older_than_the_window_is_not_recent():
    # Ran out for two days just before the window (days 14 and 15 of 30; the window starts
    # on day 16), after the fortnight of history the rule needs, and came back.
    pattern = "1" * 14 + "00" + "1" * 14
    s = build({(W, "a"): pattern})
    assert "a" not in recent(s, market=(W,))["flagged"]
    assert "a" in recent(s, market=(W,), window_days=30)["flagged"]


def test_the_window_states_its_span_and_how_many_nights_were_usable():
    s = build({(W, "a"): "1" * 30})
    del s.days[-5]                          # one day of the last fortnight was unusable
    w = recent(s, market=(W,))["window"]
    assert w == {"first": (s.days[-1] - timedelta(days=13)).isoformat(),
                 "last": s.days[-1].isoformat(), "days": 14, "usable_nights": 13}


def test_the_stores_it_ran_out_at_are_the_union_over_the_window():
    s = build({(W, "a"): present_then_absent(3), (R, "a"): "1" * 20 + "00" + "1" * 8})
    f = recent(s)["flagged"]["a"]
    assert f["stores"] == [R, W]


def test_listed_recently_reads_the_last_max_absent_usable_days_and_only_orderable_listings():
    max_absent = POLICY.running_out_max_absent
    # "a": gone 3 days, so orderable within the last max_absent days.
    # "b": gone 9 days: dropped, not listed recently (SCN-153).
    # "c": still listed, but marked not orderable for the last 9 days (ADR-031 rule 3).
    s = build({(W, "a"): present_then_absent(3), (W, "b"): present_then_absent(9),
               (W, "c"): "1" * 30}, not_orderable={(W, "c"): set(range(21, 30))})
    out = recent(s, market=(W,))
    assert out["listed_recent"].get("a") == [W]
    assert "b" not in out["listed_recent"]
    assert "c" not in out["listed_recent"]
    assert max_absent == 7


def test_gone_exactly_max_absent_days_is_flagged_tonight_but_not_listed_recently():
    """The §5 edge that "or running out tonight" exists for (INV-082)."""
    k = POLICY.running_out_max_absent
    s = build({(W, "a"): present_then_absent(k)})
    out = recent(s, market=(W,))
    assert s.days[-1].isoformat() in out["flagged"]["a"]["nights"]
    assert "a" not in out["listed_recent"]


def test_listed_tonight_is_the_orderable_listing_on_the_last_night():
    s = build({(W, "a"): present_then_absent(3), (R, "a"): "1" * 30})
    out = recent(s)
    assert out["listed_tonight"]["a"] == [R]


def test_a_store_outside_the_market_is_never_read():
    s = build({(X, "a"): present_then_absent(3), (W, "f0"): "1" * 30})
    out = recent(s, market=(W,))
    assert "a" not in out["flagged"]


def test_a_replay_of_an_earlier_night_sees_only_what_that_night_saw():
    s = build({(W, "a"): "1" * 20 + "000" + "1" * 7})
    earlier = s.days[22]
    out = recent(s, market=(W,), on_day=earlier)
    assert out["on_day"] == earlier.isoformat()
    assert out["flagged"]["a"]["nights"][-1] == earlier.isoformat()
    assert "a" not in out["listed_tonight"]


def test_only_flagged_products_are_carried_and_named():
    s = build({(W, "a"): present_then_absent(3), (W, "z"): "1" * 30}, names={"a": "Bamba", "z": "Other"})
    out = recent(s, market=(W,))
    assert set(out["flagged"]) == {"a"}
    assert set(out["listed_recent"]) <= {"a"} and set(out["names"]) == {"a"}
    assert out["names"]["a"] == "Bamba"


def test_the_result_is_plain_data_and_deterministic():
    s = build({(W, "a"): present_then_absent(3), (R, "a"): present_then_absent(4)})
    first, second = recent(s), recent(s)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    json.dumps(first)                         # no dates, no sets


# ── D-27: the price each market store last listed it at (F9-S1 FR-168, amended) ───────────────

def test_each_store_s_price_is_from_the_last_day_it_listed_the_product():
    # Wolt lists "a" until three days ago; Rami still lists it tonight.
    s = build({(W, "a"): present_then_absent(3), (R, "a"): "1" * 30})
    asked = []
    def price_of(day, barcode, store):
        asked.append((day, barcode, store))
        return {"price": 10.0 + (1 if store == R else 0), "sale_price": None}
    out = recent_market(s, [W, R], POLICY, s.days[-1], 14, price_of=price_of)
    assert out["prices"]["a"] == {
        R: {"price": 11.0, "sale_price": None, "on": s.days[-1].isoformat()},
        W: {"price": 10.0, "sale_price": None, "on": s.days[-4].isoformat()},
    }
    assert set(b for (_d, b, _s) in asked) == {"a"}             # only flagged products are priced


def test_a_price_the_snapshot_does_not_carry_is_left_out_never_zero():
    s = build({(W, "a"): present_then_absent(3)})
    out = recent_market(s, [W], POLICY, s.days[-1], 14, price_of=lambda day, b, store: None)
    assert out["prices"] == {}


def test_without_a_price_reader_there_are_no_prices():
    s = build({(W, "a"): present_then_absent(3)})
    assert recent_market(s, [W], POLICY, s.days[-1], 14)["prices"] == {}

