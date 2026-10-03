# tests/test_market_context_stockouts.py
"""The nightly's market context does not replay the whole price history for a field nothing reads.

`competitorStockouts` classified every barcode over every committed day of the national price
files: 74 s locally and 217 s on the runner on 2026-10-03, growing each night, and the largest
reason the nightly reached 37 of its 45 minutes. Nothing reads it. The reorder engine that
applied it went with ADR-028, F8 and F9 read ADR-031's nearby-market signal instead, and T4
(#49), the feature that would use it, is on hold. The committed snapshots keep everything it
was computed from, so it can be computed whenever T4 is specified.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.context.build as build  # noqa: E402
import src.context.competitor_stockouts as stockouts  # noqa: E402


def _offline(monkeypatch):
    monkeypatch.setattr(build, "get_weather", lambda lat, lon: {"source": None})
    monkeypatch.setattr(build, "get_hebrew_context", lambda day: {"source": None})
    monkeypatch.setattr(build, "get_islamic_context", lambda day, use_api=False: {"source": None})


def test_the_market_context_does_not_replay_the_price_history(monkeypatch):
    _offline(monkeypatch)

    def replay(*_a, **_k):
        raise AssertionError("market context replayed the whole price history")

    monkeypatch.setattr(stockouts, "stockout_barcodes", replay)
    monkeypatch.setattr(stockouts, "load_presence", replay)
    payload = build.build_market_context()
    field = payload["competitorStockouts"]
    assert field["status"] == "not_computed"
    assert field["barcodes"] == [] and field["days"] is None
    assert "T4" in field["reason"]


def test_the_classification_itself_is_kept_for_t4():
    """Not computed nightly is not deleted: T4 computes it from the same snapshots."""
    assert callable(stockouts.stockout_barcodes)
