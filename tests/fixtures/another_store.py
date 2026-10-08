# tests/fixtures/another_store.py
"""Run as another store's copy would (ADR-036): its own format, and none of this store's venues.

The fixture worlds run in every copy's nightly (the probes) and build the marked examples
every copy ships. A copy's configs/store.yaml names its own format, and its
configs/store_types.yaml starts with no stores. A world that read either would behave
differently in each copy, so the tests that pin a world also run it under this.
"""
from __future__ import annotations

from dataclasses import replace


def serve_another_store(monkeypatch, fmt: str = "hypermarket") -> None:
    import src.engine.inputs as inputs
    from src.common.store_types import load_store_types

    def copys_store_types(path=None):
        return load_store_types(path) if path else replace(load_store_types(), stores={})

    monkeypatch.setattr(inputs, "our_format", lambda: fmt)
    monkeypatch.setattr(inputs, "load_store_types", copys_store_types)
