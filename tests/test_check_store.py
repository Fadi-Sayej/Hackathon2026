# tests/test_check_store.py
"""ADR-036 §5: `npm run check:store` says whether a copy is ready, and what each gap blocks.

It is docs/pilot/next-store.md made executable. Each input a store supplies is present,
missing or stale, and a missing one names the capabilities that stay unavailable, read from
the registry's `requires` rather than written down twice. Secrets are checked by name only.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.store import get_store  # noqa: E402
from src.common.store_readiness import readiness  # noqa: E402

HAS_STORE_DATA = get_store().pos_export.exists()


def _empty_copy(tmp_path: Path):
    """A copy with its settings filled and nothing else: what Task 7.5's copy starts as."""
    store = replace(get_store(), pos_export=tmp_path / "export.csv",
                    sales_monthly_dir=tmp_path / "sales", sales_daily_dir=tmp_path / "sales_daily")
    (tmp_path / "store_facts.yaml").write_text("departments: {}\n", encoding="utf-8")
    (tmp_path / "delivery_targets.yaml").write_text("targets: []\n", encoding="utf-8")
    types = yaml.safe_load((ROOT / "configs" / "store_types.yaml").read_text(encoding="utf-8"))
    types["stores"] = {}
    (tmp_path / "store_types.yaml").write_text(yaml.safe_dump(types), encoding="utf-8")
    return dict(store=store, today=date(2026, 10, 1), facts_path=tmp_path / "store_facts.yaml",
                targets_path=tmp_path / "delivery_targets.yaml", store_types_path=tmp_path / "store_types.yaml",
                snapshots_root=tmp_path / "snapshots", secret_names=set(),
                layout_path=tmp_path / "store_layout.yaml")


def _by_key(items):
    return {item["key"]: item for item in items}


def test_an_empty_copy_is_missing_every_input(tmp_path):
    items = _by_key(readiness(**_empty_copy(tmp_path)))
    for key in ("pos_export", "sales_monthly", "sales_daily", "store_facts", "store_layout", "client_venue",
                "nearby_venues"):
        assert items[key]["status"] == "missing", key


def test_a_missing_input_names_what_it_blocks_from_the_registry(tmp_path):
    items = _by_key(readiness(**_empty_copy(tmp_path)))
    assert items["sales_daily"]["blocks"] == ["order_quantity", "shelf_plan"]
    assert items["store_facts"]["blocks"] == ["order_quantity"]
    assert "price_consistency" in items["pos_export"]["blocks"]
    assert "reconciliation" in items["sales_monthly"]["blocks"]
    assert {"market_running_out", "assortment_gap"} <= set(items["nearby_venues"]["blocks"])


def test_secrets_are_checked_by_name(tmp_path):
    kwargs = _empty_copy(tmp_path)
    missing = _by_key(readiness(**kwargs))
    present = _by_key(readiness(**{**kwargs, "secret_names": {"FIREBASE_SERVICE_ACCOUNT_JSON", "ANTHROPIC_API_KEY"}}))
    assert missing["nightly_secrets"]["status"] == "missing"
    assert present["nightly_secrets"]["status"] == "present"
    assert missing["boost_key"]["blocks"] == ["market_boost"]


def test_unknown_secrets_are_said_to_be_unchecked(tmp_path):
    items = _by_key(readiness(**{**_empty_copy(tmp_path), "secret_names": None}))
    assert items["nightly_secrets"]["status"] == "not checked"


@pytest.mark.skipif(not HAS_STORE_DATA, reason="this copy holds no store data yet")
def test_this_copy_reports_what_it_holds():
    items = _by_key(readiness(store=get_store(), today=date(2026, 10, 1), secret_names=None))
    assert items["pos_export"]["status"] == "present"
    assert "2026-06-06" in items["pos_export"]["detail"]
    assert items["sales_monthly"]["status"] == "present"
    assert items["sales_daily"]["status"] == "missing" and items["sales_daily"]["blocks"] == ["order_quantity", "shelf_plan"]
    assert items["store_facts"]["status"] == "missing"
    assert items["store_layout"]["status"] == "missing"     # ADR-037: no store has recorded one yet
    assert items["client_venue"]["status"] == "present"
    assert items["venue_formats"]["status"] == "present"


def test_invalid_settings_exit_1(tmp_path):
    bad = tmp_path / "store.yaml"
    bad.write_text("id: store-a\n", encoding="utf-8")
    result = subprocess.run([sys.executable, "scripts/check_store.py", "--settings", str(bad)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 1
    assert "name" in result.stderr


def test_it_never_prints_a_secret_value():
    env = {"PATH": "/usr/bin:/bin", "FIREBASE_SERVICE_ACCOUNT_JSON": "sekret-value-123",
           "ANTHROPIC_API_KEY": "sk-ant-sekret-456", "VITE_FIREBASE_API_KEY": "AIza-sekret-789"}
    result = subprocess.run([sys.executable, "scripts/check_store.py", "--no-github"],
                            cwd=ROOT, capture_output=True, text=True, env=env)
    output = result.stdout + result.stderr
    for value in env.values():
        if "sekret" in value:
            assert value not in output


def test_a_store_layout_is_present_once_it_records_a_fixture(tmp_path):
    kwargs = _empty_copy(tmp_path)
    assert "is not committed" in _by_key(readiness(**kwargs))["store_layout"]["detail"]
    (tmp_path / "store_layout.yaml").write_text("fixtures: {}\n", encoding="utf-8")
    assert _by_key(readiness(**kwargs))["store_layout"]["status"] == "missing"
    (tmp_path / "store_layout.yaml").write_text("fixtures:\n  F1: {}\n", encoding="utf-8")
    item = _by_key(readiness(**kwargs))["store_layout"]
    assert item["status"] == "present" and item["detail"].startswith("1 fixtures in")
