import copy
from pathlib import Path
import sys

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.engine.policy import DEFAULT_PATH, load_policy

# The F8-S1 keys (Phase 5 Task 5.0), each of which the loader requires.
F8_KEYS = {
    "order": ("window_days", "min_report_days", "freshness_days", "max_count_age_days",
              "publish_disagreement_questions"),
    "running_out": ("prior_days", "min_listed", "min_absent", "max_absent",
                    "catalogue_change_pct", "thin_collection_ratio", "signal_min_usable",
                    "signal_max_age_days"),
    "boost": ("model", "max_pct", "request_ceiling", "prompt"),
}


def _committed():
    return yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8"))


def _write(tmp_path, raw):
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return path


def test_policy_loads_declared_constants():
    p = load_policy()
    assert p.price_policy_pct == 60
    assert p.attention_pct == 100
    assert p.cost_floor_pct == 10
    assert p.surface_bound == 10
    assert p.surface_unvalued_places == 3
    assert p.surface_unvalued_order == ("reconciliation", "competitor_position", "catalogue_lifecycle", "hygiene")
    assert p.question_limit == 3
    assert p.question_money_basis == "window_revenue_at_shelf_price"
    assert p.uncomparable_min_barcode_digits == 8
    assert p.withdraw_with_stock is False


def test_policy_refuses_withdraw_with_stock(tmp_path):
    raw = _committed()
    raw["withdraw_with_stock"] = True
    try:
        load_policy(_write(tmp_path, raw))
    except ValueError as err:
        assert "OQ-409" in str(err)
    else:
        raise AssertionError("withdraw_with_stock: true must be refused until OQ-409 is answered")


def test_policy_as_dict_is_json_serialisable():
    import json
    json.dumps(load_policy().as_dict())


def test_policy_refuses_an_unimplemented_money_basis(tmp_path):
    """ARCH-GATE-002: the questions would be ordered by a rule nobody wrote."""
    import pytest
    raw = _committed()
    raw["question_money_basis"] = "margin_at_risk"
    with pytest.raises(ValueError, match="question_money_basis"):
        load_policy(_write(tmp_path, raw))


def test_policy_refuses_an_empty_unvalued_order(tmp_path):
    """Without an order, the three reserved places are filled by dict chance (OQ-601)."""
    import pytest
    raw = _committed()
    del raw["surface"]["unvalued_order"]
    with pytest.raises(ValueError, match="unvalued_order"):
        load_policy(_write(tmp_path, raw))


# ── F8-S1 (Phase 5 Task 5.0): order quantity, running out, the boost ──────────────────────
#
# None of these keys has a default in code. A value the owner or an ADR has not stated is
# refused, never supplied: a defaulted 28 would look exactly like a declared one in the
# artefact, and "never guessed" is the phase's first constraint.


def test_policy_loads_the_order_quantity_values():
    """OQ-906's provisional window, freshness and count age; the flag is on since Task 5.14."""
    p = load_policy()
    assert p.order_window_days == 28
    assert p.order_min_report_days == 21
    assert p.order_freshness_days == 7
    assert p.order_max_count_age_days == 7
    assert p.order_publish_disagreement_questions is True


def test_policy_loads_the_running_out_values():
    """ADR-031: 10 of the prior 14 usable days, absent 2 to 7, the two per-store guards."""
    p = load_policy()
    assert p.running_out_prior_days == 14
    assert p.running_out_min_listed == 10
    assert p.running_out_min_absent == 2
    assert p.running_out_max_absent == 7
    assert p.running_out_catalogue_change_pct == 10
    assert p.running_out_thin_collection_ratio == 0.5
    assert p.running_out_signal_min_usable == 10
    assert p.running_out_signal_max_age_days == 2


def test_policy_loads_the_boost_values():
    """ADR-032: the pinned model, D-21's 25% limit, the 200-request ceiling."""
    p = load_policy()
    assert p.boost_model == "claude-sonnet-5"
    assert p.boost_max_pct == 25
    assert p.boost_request_ceiling == 200
    assert p.boost_prompt == "configs/prompts/market_boost.v1.md"


@pytest.mark.parametrize("group,key", [(g, k) for g, keys in F8_KEYS.items() for k in keys])
def test_policy_refuses_a_missing_f8_key(tmp_path, group, key):
    raw = copy.deepcopy(_committed())
    del raw[group][key]
    with pytest.raises(ValueError, match=f"{group}.{key}"):
        load_policy(_write(tmp_path, raw))


@pytest.mark.parametrize("group", sorted(F8_KEYS))
def test_policy_refuses_a_missing_f8_group(tmp_path, group):
    raw = copy.deepcopy(_committed())
    del raw[group]
    with pytest.raises(ValueError, match=group):
        load_policy(_write(tmp_path, raw))


def test_policy_refuses_a_boost_above_d21(tmp_path):
    """D-21 caps the boost at 25%. A policy edit must not be able to lift it."""
    raw = copy.deepcopy(_committed())
    raw["boost"]["max_pct"] = 26
    with pytest.raises(ValueError, match="D-21"):
        load_policy(_write(tmp_path, raw))


def test_policy_refuses_min_listed_above_prior_days(tmp_path):
    """ADR-031: "listed on 10 of the prior 14" cannot ask for more days than it looks at."""
    raw = copy.deepcopy(_committed())
    raw["running_out"]["min_listed"] = 15
    with pytest.raises(ValueError, match="min_listed"):
        load_policy(_write(tmp_path, raw))


def test_policy_refuses_a_flag_written_as_a_string(tmp_path):
    """`bool("false")` is True: a quoted flag would publish every disagreement question."""
    raw = copy.deepcopy(_committed())
    raw["order"]["publish_disagreement_questions"] = "false"
    with pytest.raises(ValueError, match="publish_disagreement_questions"):
        load_policy(_write(tmp_path, raw))


def test_policy_publishes_the_f8_values_with_every_figure():
    """The file's promise: every declared constant travels into meta.thresholds."""
    t = load_policy().as_dict()
    assert t["order_quantity"] == {
        "window_days": 28, "min_report_days": 21, "freshness_days": 7,
        "max_count_age_days": 7, "publish_disagreement_questions": True,
    }
    assert t["market_running_out"] == {
        "prior_days": 14, "min_listed": 10, "min_absent": 2, "max_absent": 7,
        "catalogue_change_pct": 10, "thin_collection_ratio": 0.5,
        "signal_min_usable": 10, "signal_max_age_days": 2,
    }
    assert t["market_boost"] == {
        "model": "claude-sonnet-5", "max_pct": 25, "request_ceiling": 200,
        "prompt": "configs/prompts/market_boost.v1.md",
    }
