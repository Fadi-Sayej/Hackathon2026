# tests/engine/test_inputs_store.py
"""ADR-036 §2: the engine takes the store's format and folders from configs/store.yaml.

`OUR_FORMAT` was a constant, "gas_convenience": YomYom's format, written into the code. It
decides D-18's market and how comparable every competitor's price is, so a second store of
another format would have been judged as a forecourt shop.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import src.engine.inputs as inputs  # noqa: E402
import src.engine.run as run_mod  # noqa: E402
from src.common.store import get_store  # noqa: E402
from src.common.store_types import load_store_types  # noqa: E402


def _stores(tmp_path: Path):
    """The committed scale and affinity, with one supermarket of our own making."""
    raw = yaml.safe_load((ROOT / "configs" / "store_types.yaml").read_text(encoding="utf-8"))
    raw["stores"] = {"super-1": {"store_type": "supermarket", "verified": "manual", "basis": "branch_known"}}
    path = tmp_path / "store_types.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return load_store_types(path)


def test_a_competitor_is_judged_from_the_stores_own_format(tmp_path):
    stores = _stores(tmp_path)
    signals = [{"competitor_store_id": "super-1", "barcode": "7290000000017", "delivery_catalog_price": 5.0}]
    as_forecourt = inputs._shape_observations(signals, stores, "gas_convenience")
    as_minimarket = inputs._shape_observations(signals, stores, "urban_minimarket")
    assert as_forecourt[0]["affinity"] == stores.affinity("gas_convenience", "supermarket")
    assert as_minimarket[0]["affinity"] == stores.affinity("urban_minimarket", "supermarket")
    assert as_forecourt[0]["affinity"] != as_minimarket[0]["affinity"]


def test_the_format_is_the_settings_not_a_constant(monkeypatch):
    other = replace(get_store(), format="urban_minimarket")
    monkeypatch.setattr(inputs, "get_store", lambda: other)
    assert inputs.our_format() == "urban_minimarket"
    assert not hasattr(inputs, "OUR_FORMAT")


def test_the_sales_folders_are_the_settings(monkeypatch, tmp_path):
    import importlib

    import src.common.store as store_mod
    other = replace(get_store(), sales_monthly_dir=tmp_path / "monthly", sales_daily_dir=tmp_path / "daily")
    monkeypatch.setattr(store_mod, "get_store", lambda: other)
    try:
        reloaded = importlib.reload(run_mod)
        assert reloaded.SALES_DIR == tmp_path / "monthly"
        assert reloaded.DAILY_SALES_DIR == tmp_path / "daily"
    finally:
        monkeypatch.undo()
        importlib.reload(run_mod)
