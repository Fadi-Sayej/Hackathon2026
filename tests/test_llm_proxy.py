"""Real FastAPI boundary tests for the LLM explanation proxy."""

from __future__ import annotations

import asyncio
import importlib
import sys
from types import SimpleNamespace

import dotenv
import pytest
from fastapi.testclient import TestClient
from google.api_core.exceptions import TooManyRequests


@pytest.fixture(autouse=True)
def _isolate_dotenv(monkeypatch):
    """Stop the developer's real .env leaking into these tests.

    `llm_proxy` calls `load_dotenv()` at import time, which reads `.env` off disk
    and repopulates VITE_GEMINI_API_KEY *after* monkeypatch has cleared it. That
    made the "no key" tests import a fully configured proxy, so the one asserting
    a 503 instead issued a live Gemini request and got a 429 — a unit test making
    a real, billable API call, and green only on machines with no `.env`.

    It also silently defeated `_load_proxy`: the proxy prefers VITE_GEMINI_API_KEY
    over GEMINI_API_KEY, so the real key outranked the test placeholder.

    Autouse, so every test in this module gets a clean environment regardless of
    which loader it picks.
    """
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.delenv("VITE_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VITE_GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)


def _load_proxy(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-a-real-key")
    sys.modules.pop("src.api.llm_proxy", None)
    return importlib.import_module("src.api.llm_proxy")


def _load_proxy_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VITE_GEMINI_API_KEY", raising=False)
    sys.modules.pop("src.api.llm_proxy", None)
    return importlib.import_module("src.api.llm_proxy")


class _CountingModel:
    """Records how many times the upstream model was actually called."""

    def __init__(self):
        self.calls = 0

    async def generate_content_async(self, _prompt, request_options, generation_config=None):
        assert request_options["timeout"] > 0
        self.calls += 1
        return SimpleNamespace(text='''{
            "shortExplanation": "cached",
            "riskReason": "r",
            "businessImpact": "b",
            "confidenceNote": "c"
        }''')


class _SuccessfulModel:
    async def generate_content_async(self, _prompt, request_options, generation_config=None):
        assert request_options["timeout"] > 0
        return SimpleNamespace(text='''{
            "shortExplanation": "Live proxy explanation",
            "riskReason": "Risk",
            "businessImpact": "Impact",
            "confidenceNote": "Confidence"
        }''')


class _DelayedModel:
    def __init__(self):
        self.cancelled = False

    async def generate_content_async(self, _prompt, request_options, generation_config=None):
        assert request_options["timeout"] > 0
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class _RateLimitedModel:
    async def generate_content_async(self, _prompt, request_options, generation_config=None):
        assert request_options["timeout"] > 0
        raise TooManyRequests(
            "quota exhausted",
            response=SimpleNamespace(headers={"Retry-After": "23"}),
        )


def test_explain_success_through_fastapi_route(monkeypatch):
    proxy = _load_proxy(monkeypatch)
    proxy.model = _SuccessfulModel()

    response = TestClient(proxy.app).post("/explain", json={"product": "test"})

    assert response.status_code == 200
    assert response.json() == {
        "shortExplanation": "Live proxy explanation",
        "riskReason": "Risk",
        "businessImpact": "Impact",
        "confidenceNote": "Confidence",
    }


def test_explain_timeout_returns_504_and_cancels_upstream(monkeypatch):
    proxy = _load_proxy(monkeypatch)
    delayed_model = _DelayedModel()
    proxy.model = delayed_model
    proxy.UPSTREAM_TIMEOUT_SECONDS = 0.01

    response = TestClient(proxy.app).post("/explain", json={"product": "test"})

    assert response.status_code == 504
    assert response.json() == {"detail": "Gemini request timed out"}
    assert delayed_model.cancelled is True


def test_explain_429_preserves_retry_after(monkeypatch):
    proxy = _load_proxy(monkeypatch)
    proxy.model = _RateLimitedModel()

    response = TestClient(proxy.app).post("/explain", json={"product": "test"})

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "23"
    assert response.json() == {"detail": "Gemini rate limit exceeded"}


def test_module_imports_and_health_ok_without_key(monkeypatch):
    # B-4: the proxy must not raise at import when the key is absent, so /health
    # still answers for deploy checks.
    proxy = _load_proxy_without_key(monkeypatch)
    response = TestClient(proxy.app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "llm_configured": False}


def test_explain_without_key_returns_503(monkeypatch):
    proxy = _load_proxy_without_key(monkeypatch)
    response = TestClient(proxy.app).post("/explain", json={"product": "test"})
    assert response.status_code == 503
    assert response.json() == {"detail": "LLM not configured (no API key)"}


class _ConfigRecordingModel:
    """Captures the generation config the proxy asks Gemini for."""

    def __init__(self):
        self.generation_config = None

    async def generate_content_async(self, _prompt, request_options, generation_config=None):
        assert request_options["timeout"] > 0
        self.generation_config = generation_config
        return SimpleNamespace(text='''{
            "shortExplanation": "s",
            "riskReason": "r",
            "businessImpact": "b",
            "confidenceNote": "c"
        }''')


def test_default_model_is_the_cheapest_tier_that_fits_the_task(monkeypatch):
    # The full flash tier bills output at $2.50/1M and thinks by default (thinking
    # tokens bill as output, and the pinned SDK cannot switch that off). flash-lite
    # is $0.40/1M with thinking off — ample for a 4-field JSON answer.
    #
    # Asserts the TIER, not a version string. Pinning 'gemini-2.5-flash-lite' meant
    # this test failed for a routine model bump on 2026-09-08 while the property it
    # exists to protect — never silently defaulting to the expensive tier — was
    # never in danger. Model names move; the cost argument does not.
    proxy = _load_proxy(monkeypatch)
    assert proxy.GEMINI_MODEL.endswith("-flash-lite"), proxy.GEMINI_MODEL


def test_default_model_is_not_a_vite_prefixed_variable(monkeypatch):
    """VITE_GEMINI_MODEL must not steer the server.

    It exists only to be compiled into the browser bundle; letting it win here had
    the proxy following a client-side variable.
    """
    monkeypatch.setenv("VITE_GEMINI_MODEL", "gemini-should-not-win")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    proxy = _load_proxy(monkeypatch)
    assert proxy.GEMINI_MODEL == "gemini-3.5-flash-lite"


def test_explain_asks_for_bounded_json_instead_of_free_text(monkeypatch):
    # Output tokens are the expensive half of the bill: a JSON mime type drops the
    # markdown fence the prompt otherwise invites, and the cap bounds a runaway answer.
    proxy = _load_proxy(monkeypatch)
    recording = _ConfigRecordingModel()
    proxy.model = recording

    response = TestClient(proxy.app).post("/explain", json={"product": "test"})

    assert response.status_code == 200
    assert recording.generation_config["response_mime_type"] == "application/json"
    assert recording.generation_config["max_output_tokens"] == 400


def test_cache_holds_a_working_set_larger_than_the_old_500_ceiling(monkeypatch):
    # The LRU used to be smaller than one pass over the recommendation list, so
    # entry 1 was evicted before the next pass reached it — a 0% hit rate that
    # re-billed every row.
    proxy = _load_proxy(monkeypatch)
    counting = _CountingModel()
    proxy.model = counting
    client = TestClient(proxy.app)

    for index in range(600):
        client.post("/explain", json={"product": f"item-{index}"})
    client.post("/explain", json={"product": "item-0"})

    assert counting.calls == 600  # the first entry survived the pass


def test_identical_payload_is_served_from_cache(monkeypatch):
    # B-4: an identical payload must not re-bill Gemini on every render.
    proxy = _load_proxy(monkeypatch)
    counting = _CountingModel()
    proxy.model = counting
    client = TestClient(proxy.app)

    first = client.post("/explain", json={"product": "milk"})
    second = client.post("/explain", json={"product": "milk"})

    assert first.status_code == 200
    assert second.json() == first.json()
    assert counting.calls == 1  # second answer came from the cache
