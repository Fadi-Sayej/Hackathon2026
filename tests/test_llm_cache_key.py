"""The explanation cache must be keyed on the decision, not on the request.

Hashing the whole payload looked like caching but was not: marketContext carries
currentDate, so every recommendation missed once a day and was re-billed although
nothing about the decision had moved. And the opposite error is worse — a changed
order quantity that HIT the cache would show the owner yesterday's sentence beside
today's number.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.llm_proxy import _cache_key  # noqa: E402

FACTS = {
    "orderQty": 20,
    "currentStock": 0,
    "dailyRate": 8.38,
    "leadTimeDays": 3,
}


def payload(facts=None, **extra):
    base = {
        "facts": facts if facts is not None else dict(FACTS),
        "language": "he",
        "marketContext": {"currentDate": "2026-09-08", "weather": "hot"},
        "productMetrics": {"id": "ym-1", "name": "קרואסון"},
    }
    base.update(extra)
    return base


def test_same_facts_hit_the_cache_even_on_a_different_day():
    a = _cache_key("explain", payload())
    b = _cache_key("explain", payload(marketContext={"currentDate": "2026-09-09"}))
    assert a == b


def test_a_changed_order_quantity_misses_the_cache():
    """The failure that would put a stale sentence beside a fresh number."""
    changed = dict(FACTS, orderQty=16)
    assert _cache_key("explain", payload()) != _cache_key("explain", payload(changed))


def test_any_changed_figure_misses():
    for field, value in (("currentStock", 5), ("dailyRate", 9.1), ("leadTimeDays", 7)):
        changed = dict(FACTS, **{field: value})
        assert _cache_key("explain", payload()) != _cache_key("explain", payload(changed)), field


def test_language_is_part_of_the_identity():
    """The same decision explained in Hebrew and Arabic is two different answers."""
    assert _cache_key("explain", payload(language="he")) != _cache_key(
        "explain", payload(language="ar")
    )


def test_unrelated_payload_noise_does_not_cause_a_re_bill():
    a = _cache_key("explain", payload())
    b = _cache_key("explain", payload(productMetrics={"id": "ym-1", "name": "renamed"}))
    assert a == b


def test_payloads_without_facts_are_not_all_collapsed_into_one_key():
    """No facts means no shared identity — never one key for every such request."""
    a = _cache_key("explain", {"language": "he", "productMetrics": {"id": "a"}})
    b = _cache_key("explain", {"language": "he", "productMetrics": {"id": "b"}})
    assert a != b
