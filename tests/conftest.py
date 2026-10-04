# tests/conftest.py
"""No test may ever reach a real language model (ADR-032, ADR-039).

Publish mode asks the model whenever the key is set and there is something to ask. Today most tests
get away with it because no layout file is committed and no key is set, but a developer with
SMARTSHELF_ANTHROPIC_API_KEY in their shell, or a store copy with its layout committed, would spend
a real key from the test suite and write into data/external/snapshots/. So for every test: the key
is unset, and the real transport refuses. A test that means to ask passes its own fake transport.
"""
import pytest


@pytest.fixture(autouse=True)
def _no_real_model(monkeypatch):
    from src.engine import market_boost, model_client

    def refuse(*args, **kwargs):
        raise RuntimeError("a test tried to call the real model API; pass a fake transport")

    monkeypatch.delenv(model_client.KEY_ENV, raising=False)
    monkeypatch.setattr(model_client, "urllib_transport", refuse)
    monkeypatch.setattr(market_boost, "urllib_transport", refuse)
