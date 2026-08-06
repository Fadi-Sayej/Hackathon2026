"""Real FastAPI boundary tests for the LLM explanation proxy."""

from __future__ import annotations

import asyncio
import importlib
import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient
from google.api_core.exceptions import TooManyRequests


def _load_proxy(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-a-real-key")
    sys.modules.pop("src.api.llm_proxy", None)
    return importlib.import_module("src.api.llm_proxy")


class _SuccessfulModel:
    async def generate_content_async(self, _prompt, request_options):
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

    async def generate_content_async(self, _prompt, request_options):
        assert request_options["timeout"] > 0
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class _RateLimitedModel:
    async def generate_content_async(self, _prompt, request_options):
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
