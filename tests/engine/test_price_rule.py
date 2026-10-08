# tests/engine/test_price_rule.py
"""D-39, ADR-043: the price rule is the store owner's statement, an input like the others.

A new store's copy starts without one. The engine reads it from configs/store_facts.yaml, never
from the policy, digests it, and reports a malformed one. `check:store` lists it while it is
missing.
"""
from datetime import date, datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

RULE = ("price_rule:\n  max_premium_pct: {pct}\n  stated_by: owner\n  stated_on: not_recorded\n"
        "  recorded_by: team\n  recorded_on: 2026-09-08\n")
RUN_AT = datetime(2026, 10, 8, 8, tzinfo=timezone.utc)


def _facts(tmp_path, body: str) -> Path:
    path = tmp_path / "store_facts.yaml"
    path.write_text("departments: {}\n" + body, encoding="utf-8")
    return path


def _load(tmp_path, facts: Path):
    from src.engine.inputs import load_inputs
    from src.engine.policy import load_policy
    from src.owner_state.model import OwnerState
    return load_inputs(policy=load_policy(), owner=OwnerState.unavailable("x"), run_at=RUN_AT,
                       silver_dir=tmp_path / "silver", signals_dir=tmp_path / "nosig",
                       matches_path=tmp_path / "nomatch.parquet", snapshots_root=tmp_path / "nosnap",
                       store_facts_path=facts)


def test_the_engine_reads_the_owners_rule_from_the_store_facts(tmp_path):
    inputs = _load(tmp_path, _facts(tmp_path, RULE.format(pct=45)))
    assert inputs.price_rule["max_premium_pct"] == 45.0
    assert inputs.price_rule_rejected is None


def test_without_a_stated_rule_there_is_no_rule(tmp_path):
    inputs = _load(tmp_path, _facts(tmp_path, ""))
    assert inputs.price_rule is None and inputs.price_rule_rejected is None


def test_a_malformed_rule_is_no_rule_and_says_why(tmp_path):
    inputs = _load(tmp_path, _facts(tmp_path, RULE.format(pct=0)))
    assert inputs.price_rule is None and "above 0" in inputs.price_rule_rejected


def test_a_different_rule_is_a_different_input(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "c").mkdir()
    a = _load(tmp_path, _facts(tmp_path / "a", RULE.format(pct=60))).inputs_digest
    b = _load(tmp_path, _facts(tmp_path / "b", RULE.format(pct=45))).inputs_digest
    c = _load(tmp_path, _facts(tmp_path / "c", "")).inputs_digest
    assert len({a, b, c}) == 3


def test_the_policy_no_longer_holds_the_rule():
    from src.engine.policy import load_policy
    assert not hasattr(load_policy(), "price_policy_pct")


def test_a_policy_that_still_states_the_rule_is_refused(tmp_path):
    """A copy updated from an older one must not carry another owner's rule back in (D-39)."""
    import yaml
    from src.engine.policy import DEFAULT_PATH, load_policy
    raw = yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8"))
    raw["price_policy_pct"] = 60
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValueError, match="store_facts.yaml"):
        load_policy(path)


def test_a_rejected_rule_is_reported_in_the_runs_steps():
    from src.engine.run import _price_rule_verdict
    assert _price_rule_verdict("max_premium_pct must be above 0, not 0") == (
        "degraded", "rejected: max_premium_pct must be above 0, not 0")
    assert _price_rule_verdict(None) == ("ok", None)


# ── check:store ──────────────────────────────────────────────────────────────

def _readiness(tmp_path, body: str):
    from dataclasses import replace
    import yaml
    from src.common.store import get_store
    from src.common.store_readiness import readiness
    root = Path(__file__).resolve().parents[2]
    store = replace(get_store(), pos_export=tmp_path / "export.csv",
                    sales_monthly_dir=tmp_path / "sales", sales_daily_dir=tmp_path / "sales_daily")
    _facts(tmp_path, body)
    (tmp_path / "delivery_targets.yaml").write_text("targets: []\n", encoding="utf-8")
    types = yaml.safe_load((root / "configs" / "store_types.yaml").read_text(encoding="utf-8"))
    types["stores"] = {}
    (tmp_path / "store_types.yaml").write_text(yaml.safe_dump(types), encoding="utf-8")
    items = readiness(store=store, today=date(2026, 10, 8), facts_path=tmp_path / "store_facts.yaml",
                      targets_path=tmp_path / "delivery_targets.yaml", store_types_path=tmp_path / "store_types.yaml",
                      snapshots_root=tmp_path / "snapshots", secret_names=set(),
                      layout_path=tmp_path / "store_layout.yaml")
    return {item["key"]: item for item in items}


def test_check_store_lists_the_rule_while_it_is_missing(tmp_path):
    item = _readiness(tmp_path, "")["price_rule"]
    assert item["status"] == "missing" and "price_rule" in item["detail"]


def test_check_store_says_why_a_rejected_rule_is_missing(tmp_path):
    item = _readiness(tmp_path, RULE.format(pct=-5))["price_rule"]
    assert item["status"] == "missing" and "above 0" in item["detail"]


def test_check_store_shows_a_stated_rule(tmp_path):
    item = _readiness(tmp_path, RULE.format(pct=45))["price_rule"]
    assert item["status"] == "present" and "45" in item["detail"] and item["blocks"] == []
