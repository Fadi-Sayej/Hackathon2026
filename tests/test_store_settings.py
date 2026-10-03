# tests/test_store_settings.py
"""ADR-036 §2: configs/store.yaml is what makes this copy one store's.

Nothing is defaulted. A copy that forgot a key would otherwise run quietly on another store's
identity, which is the failure the settings file exists to prevent. So every key is required,
and a missing or invalid one stops the run and names itself.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.store import (  # noqa: E402
    REQUIRED_KEYS, STORE_SETTINGS_PATH, StoreSettingsError, firebase_project_for_owner_state, load_store,
    store_id_for_owner_state,
)

VALID = {
    "id": "store-a",
    "name": "Store A",
    "site_title": "SmartShelf AI — Store A",
    "location": {"lat": 32.1, "lon": 34.9},
    "format": "urban_minimarket",
    "pos": {"export": "store-a-inventory.csv"},
    "sales": {"monthly_dir": "data/internal/raw_pos/store-a/sales",
              "daily_dir": "data/internal/raw_pos/store-a/sales_daily"},
    "market": {"radius_km": 5},
    "firebase": {"project_id": "store-a-project"},
    "site": {"address": "store-a.example.app"},
}


def _write(tmp_path: Path, data) -> Path:
    path = tmp_path / "store.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def _without(data: dict, dotted: str) -> dict:
    copy = yaml.safe_load(yaml.safe_dump(data))
    *parents, leaf = dotted.split(".")
    node = copy
    for part in parents:
        node = node[part]
    del node[leaf]
    return copy


def test_a_complete_file_gives_every_setting(tmp_path):
    store = load_store(_write(tmp_path, VALID))
    assert store.id == "store-a"
    assert store.name == "Store A"
    assert store.site_title == "SmartShelf AI — Store A"
    assert (store.location.lat, store.location.lon) == (32.1, 34.9)
    assert store.format == "urban_minimarket"
    assert store.market_radius_km == 5.0
    assert store.firebase_project_id == "store-a-project"
    assert store.site_address == "store-a.example.app"


def test_paths_are_read_from_the_repository_root(tmp_path):
    store = load_store(_write(tmp_path, VALID))
    assert store.pos_export == ROOT / "store-a-inventory.csv"
    assert store.sales_monthly_dir == ROOT / "data/internal/raw_pos/store-a/sales"
    assert store.sales_daily_dir == ROOT / "data/internal/raw_pos/store-a/sales_daily"


@pytest.mark.parametrize("dotted", REQUIRED_KEYS)
def test_a_missing_key_stops_the_run_and_names_itself(tmp_path, dotted):
    with pytest.raises(StoreSettingsError, match=re.escape(dotted)):
        load_store(_write(tmp_path, _without(VALID, dotted)))


@pytest.mark.parametrize("dotted", ["id", "name", "site_title", "format", "pos.export"])
def test_an_empty_value_is_as_missing_as_an_absent_one(tmp_path, dotted):
    data = yaml.safe_load(yaml.safe_dump(VALID))
    *parents, leaf = dotted.split(".")
    node = data
    for part in parents:
        node = node[part]
    node[leaf] = ""
    with pytest.raises(StoreSettingsError, match=re.escape(dotted)):
        load_store(_write(tmp_path, data))


def test_a_format_the_scale_does_not_know_is_refused(tmp_path):
    with pytest.raises(StoreSettingsError, match="format"):
        load_store(_write(tmp_path, {**VALID, "format": "corner_shop"}))


@pytest.mark.parametrize("location, key", [({"lat": 132, "lon": 34.9}, "location.lat"),
                                           ({"lat": 32.1, "lon": -200}, "location.lon"),
                                           ({"lat": "north", "lon": 34.9}, "location.lat")])
def test_a_location_off_the_globe_is_refused(tmp_path, location, key):
    with pytest.raises(StoreSettingsError, match=re.escape(key)):
        load_store(_write(tmp_path, {**VALID, "location": location}))


def test_a_radius_that_is_not_positive_is_refused(tmp_path):
    with pytest.raises(StoreSettingsError, match="market.radius_km"):
        load_store(_write(tmp_path, {**VALID, "market": {"radius_km": 0}}))


def test_no_file_is_refused_and_names_the_path(tmp_path):
    missing = tmp_path / "store.yaml"
    with pytest.raises(StoreSettingsError, match=re.escape(str(missing))):
        load_store(missing)


def test_the_committed_settings_are_complete():
    """Whatever store this copy serves, its settings file loads."""
    assert load_store(STORE_SETTINGS_PATH).id


def test_the_owner_state_store_is_the_settings_id(tmp_path):
    path = _write(tmp_path, VALID)
    assert store_id_for_owner_state({}, path) == "store-a"
    assert store_id_for_owner_state({"VITE_STORE_ID": "store-a"}, path) == "store-a"


def test_an_environment_naming_another_store_is_refused(tmp_path):
    """The nightly would otherwise pull one store's decisions into another store's artefact."""
    with pytest.raises(StoreSettingsError, match="VITE_STORE_ID"):
        store_id_for_owner_state({"VITE_STORE_ID": "store-b"}, _write(tmp_path, VALID))


def test_the_importer_writes_the_tables_every_reader_names():
    """One fact, one place: the POS importer's config and the readers must agree on the names."""
    from src.common.store import INVENTORY_TABLE, PRODUCTS_TABLE
    mapping = yaml.safe_load((ROOT / "configs" / "pos_schema_mapping.yaml").read_text(encoding="utf-8"))
    assert mapping["silver_tables"]["products"]["filename"] == PRODUCTS_TABLE
    assert mapping["silver_tables"]["inventory"]["filename"] == INVENTORY_TABLE


def test_the_owner_state_project_is_the_settings_project(tmp_path):
    path = _write(tmp_path, VALID)
    assert firebase_project_for_owner_state({}, path) == "store-a-project"
    assert firebase_project_for_owner_state({"FIREBASE_PROJECT_ID": "store-a-project"}, path) == "store-a-project"


@pytest.mark.parametrize("key", ["FIREBASE_PROJECT_ID", "VITE_FIREBASE_PROJECT_ID"])
def test_an_environment_naming_another_project_is_refused(tmp_path, key):
    """Another copy's Firebase project holds another store's owner state (D-28)."""
    with pytest.raises(StoreSettingsError, match=key):
        firebase_project_for_owner_state({key: "store-b-project"}, _write(tmp_path, VALID))


@pytest.mark.parametrize("address", ["https://store-a.example.app", "store-a.example.app/", "store a.app"])
def test_the_site_address_is_a_bare_host(tmp_path, address):
    """It is what Firebase's authorised domains hold, and what the sign-in page links to."""
    with pytest.raises(StoreSettingsError, match="site.address"):
        load_store(_write(tmp_path, {**VALID, "site": {"address": address}}))
