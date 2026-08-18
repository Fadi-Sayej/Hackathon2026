"""
T1 / #46 Step 2 — the delivery collector reads its targets from config.

It used to default to one hardcoded Wolt URL while `configs/delivery_targets.yaml`
listed nine enabled venues that nothing in the daily path ever opened. The daily
snapshot therefore carried a single competitor venue for three days, and never
carried `yomyom_kafr_qasim` — our own store, and the labelled ground truth that
#49 Step 5 is built on.

The config is also where the price-file branch mapping lives now, because
declaring "this Wolt venue is branch 657" is a claim someone should be able to
find and challenge, not a dict buried in an analysis script.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.measure_baselines import venue_to_price_store  # noqa: E402
from scripts.run_delivery_venue_connector import (  # noqa: E402
    DEFAULT_TARGETS_PATH,
    load_targets,
)


def write_config(tmp_path: Path, targets) -> Path:
    path = tmp_path / "delivery_targets.yaml"
    path.write_text(yaml.safe_dump({"targets": targets}), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# The real config
# ---------------------------------------------------------------------------

def test_the_real_config_still_contains_our_own_store():
    """If this ever disappears, #49 Step 5 loses its ground truth silently."""
    keys = {t["key"] for t in load_targets(DEFAULT_TARGETS_PATH)}
    assert "yomyom_kafr_qasim" in keys


def test_the_real_config_still_contains_the_one_scorable_venue():
    """super_alonit_einat is the only venue in both the delivery catalogue and
    the price file. Without it the #49 Step 2 baseline cannot be measured at
    all — it was collected for three days by a hardcoded default that this
    config did not know about."""
    mapping = venue_to_price_store()
    assert mapping.get("super-alonit-kibbutz-einat") == "657"


def test_every_declared_price_file_branch_belongs_to_an_enabled_target():
    config = yaml.safe_load(DEFAULT_TARGETS_PATH.read_text(encoding="utf-8"))
    declared = {
        t["key"] for t in config["targets"]
        if t.get("price_file_store_id")
    }
    enabled = {t["key"] for t in load_targets(DEFAULT_TARGETS_PATH)}
    assert declared <= enabled


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def test_disabled_targets_are_not_collected(tmp_path):
    path = write_config(tmp_path, [
        {"key": "a", "url": "https://x/a", "enabled": True},
        {"key": "b", "url": "https://x/b", "enabled": False},
    ])
    assert [t["key"] for t in load_targets(path)] == ["a"]


def test_a_target_missing_its_url_is_skipped_not_fatal(tmp_path):
    """One malformed config entry must not cost a day of everyone else's
    history — and a lost day cannot be re-collected tomorrow."""
    path = write_config(tmp_path, [
        {"key": "broken"},
        {"key": "fine", "url": "https://x/fine"},
    ])
    assert [t["key"] for t in load_targets(path)] == ["fine"]


def test_targets_default_to_enabled(tmp_path):
    path = write_config(tmp_path, [{"key": "a", "url": "https://x/a"}])
    assert len(load_targets(path)) == 1


def test_a_quarantined_target_is_excluded_from_the_daily_run(tmp_path):
    """A venue disabled for a known cause must not fail the manifest nightly.
    An alert that fires every night for something nobody intends to act on
    tonight is how alerts stop being read — #46 Step 5's own warning."""
    path = write_config(tmp_path, [
        {"key": "live", "url": "https://x/live"},
        {"key": "dead", "url": "https://x/dead", "enabled": False,
         "disabled_reason": "wolt serves no assortment"},
    ])
    assert [t["key"] for t in load_targets(path)] == ["live"]


def test_a_quarantined_target_can_be_re_tested_on_demand(tmp_path):
    """Quarantined, not forgotten. Re-checking must not require editing config."""
    path = write_config(tmp_path, [
        {"key": "live", "url": "https://x/live"},
        {"key": "dead", "url": "https://x/dead", "enabled": False},
    ])
    keys = [t["key"] for t in load_targets(path, include_disabled=True)]
    assert keys == ["live", "dead"]


def test_the_real_config_quarantines_shuk_bair_with_a_reason(tmp_path):
    """Whoever re-enables it should find out why it was switched off."""
    config = yaml.safe_load(DEFAULT_TARGETS_PATH.read_text(encoding="utf-8"))
    dead = [t for t in config["targets"] if t.get("enabled") is False]
    assert dead, "expected at least one quarantined target"
    for target in dead:
        assert target.get("disabled_reason"), f"{target['key']} disabled with no reason"


def test_our_own_store_is_never_quarantined():
    """#49 Step 5 loses its ground truth the moment this one goes dark."""
    keys = {t["key"] for t in load_targets(DEFAULT_TARGETS_PATH)}
    assert "yomyom_kafr_qasim" in keys


def test_keys_filter_the_selection(tmp_path):
    path = write_config(tmp_path, [
        {"key": "a", "url": "https://x/a"},
        {"key": "b", "url": "https://x/b"},
    ])
    assert [t["key"] for t in load_targets(path, ["b"])] == ["b"]


def test_an_empty_config_yields_nothing_rather_than_crashing(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    assert load_targets(path) == []


def test_a_missing_config_is_an_error_not_a_silent_empty_run(tmp_path):
    """Silently collecting nothing is how a day goes missing unnoticed."""
    with pytest.raises(FileNotFoundError):
        load_targets(tmp_path / "nope.yaml")


def test_the_venue_mapping_ignores_targets_without_a_branch(tmp_path, monkeypatch):
    import scripts.measure_baselines as mb

    path = write_config(tmp_path, [
        {"key": "mapped", "url": "https://x/venue/mapped-one", "price_file_store_id": 657},
        {"key": "unmapped", "url": "https://x/venue/unmapped-one"},
    ])
    monkeypatch.setattr(mb, "DELIVERY_TARGETS_PATH", path)
    assert mb.venue_to_price_store() == {"mapped-one": "657"}
