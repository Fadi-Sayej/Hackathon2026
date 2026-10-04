"""The one model client (ADR-032, ADR-039 Decision 3): shared by the boost and the explanation."""
from __future__ import annotations

import json

import pytest

from src.engine import market_boost, model_client


class Fake:
    def __init__(self, status=200, text='{"ok": true}'):
        self.status, self.text, self.bodies = status, text, []

    def __call__(self, url, headers, body, timeout):
        self.bodies.append(json.loads(body))
        return self.status, json.dumps({"content": [{"type": "text", "text": self.text}]}).encode()


def test_the_caller_sets_the_token_limit_and_the_boost_keeps_its_300():
    fake = Fake()
    model_client.ask({"system": "s", "user": "u"}, model="m", key="k", transport=fake, max_tokens=1200)
    market_boost.ask({"system": "s", "user": "u"}, model="m", key="k", transport=fake)
    assert [b["max_tokens"] for b in fake.bodies] == [1200, 300]
    assert all("temperature" not in b for b in fake.bodies)         # ADR-032 Decision 2


def test_a_server_error_is_retried_once_and_then_refused(monkeypatch):
    monkeypatch.setattr(model_client, "RETRY_PAUSE_S", 0.0)
    fake = Fake(status=503)
    with pytest.raises(model_client.ModelUnavailable):
        model_client.ask({"system": "s", "user": "u"}, model="m", key="k", transport=fake, max_tokens=10)
    assert len(fake.bodies) == 2
    assert market_boost.BoostUnavailable is model_client.ModelUnavailable


def test_a_refused_request_is_not_retried():
    fake = Fake(status=400)
    with pytest.raises(model_client.ModelUnavailable):
        model_client.ask({"system": "s", "user": "u"}, model="m", key="k", transport=fake, max_tokens=10)
    assert len(fake.bodies) == 1


def test_the_digest_is_of_the_facts_not_their_order():
    assert model_client.facts_digest({"a": 1, "b": "ש"}) == model_client.facts_digest({"b": "ש", "a": 1})
    assert market_boost.facts_digest is model_client.facts_digest and market_boost.KEY_ENV == model_client.KEY_ENV


def test_the_tests_themselves_can_never_reach_the_real_api():
    # tests/conftest.py: the key is unset and the real transport refuses, for every test.
    import os
    assert model_client.KEY_ENV not in os.environ
    with pytest.raises(RuntimeError, match="real model API"):
        model_client.urllib_transport("u", {}, b"", 1.0)
