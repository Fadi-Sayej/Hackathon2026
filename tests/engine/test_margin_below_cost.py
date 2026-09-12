# tests/engine/test_margin_below_cost.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product
from src.engine.margin_below_cost import run


def test_below_cost_carries_a_per_sale_loss_but_is_never_admitted():
    out = run(make_inputs(products=[product("a", shelf=10.0, cost=12.0), product("b", shelf=10.0, cost=9.5),
                                    product("art", shelf=0.01, cost=2.28)]))
    by = {e.barcode: e for e in out.entries}
    assert by["a"].value.amount == 2.0 and by["a"].value.kind == "per_sale"
    assert all(e.actionable is False for e in out.entries)
    assert all(e.not_actionable_reason == "no_producing_specification" for e in out.entries)
    assert "art" not in by and out.counts["excluded_artefact"] == 1


def test_thin_positive_margins_are_counted_not_valued():
    out = run(make_inputs(products=[product("b", shelf=10.0, cost=9.5)]))
    assert out.counts["thin_margin"] == 1
    assert next(e for e in out.entries if e.barcode == "b").value is None
