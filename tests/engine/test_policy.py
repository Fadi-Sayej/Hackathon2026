from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.engine.policy import load_policy


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
    bad = tmp_path / "policy.yaml"
    bad.write_text("version: 1\nwithdraw_with_stock: true\n", encoding="utf-8")
    try:
        load_policy(bad)
    except ValueError as err:
        assert "OQ-409" in str(err)
    else:
        raise AssertionError("withdraw_with_stock: true must be refused until OQ-409 is answered")


def test_policy_as_dict_is_json_serialisable():
    import json
    json.dumps(load_policy().as_dict())


def test_policy_refuses_an_unimplemented_money_basis():
    """ARCH-GATE-002: the questions would be ordered by a rule nobody wrote."""
    import pytest
    from pathlib import Path as _P
    bad = _P("/tmp/policy_bad_basis.yaml")
    bad.write_text("version: 1\nquestion_money_basis: margin_at_risk\n"
                   "surface:\n  unvalued_order: [reconciliation, competitor_position, "
                   "catalogue_lifecycle, hygiene]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="question_money_basis"):
        load_policy(bad)


def test_policy_refuses_an_empty_unvalued_order():
    """Without an order, the three reserved places are filled by dict chance (OQ-601)."""
    import pytest
    from pathlib import Path as _P
    bad = _P("/tmp/policy_no_order.yaml")
    bad.write_text("version: 1\nsurface:\n  bound: 10\n  unvalued_places: 3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unvalued_order"):
        load_policy(bad)
