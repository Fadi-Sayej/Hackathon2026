# tests/engine/test_catalogue_lifecycle.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product, summary, window_of
from src.engine.catalogue_lifecycle import classify_evidence, run
from src.owner_state.model import OwnerState

W7 = window_of(["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"])
W12 = window_of([f"2025-{m:02d}" for m in range(8, 13)] + [f"2026-{m:02d}" for m in range(1, 8)], full=True)
MONTHLY = [{"barcode": "L", "month": "2026-01", "units": 10, "receipts": 0, "revenue": 100.0}]


def _inputs(window=W7, owner=None, monthly=MONTHLY):
    return make_inputs(
        products=[product("L", stock=3.0, cost=1.0), product("W", stock=0.0, cost=2.0), product("I", stock=4.0, cost=34.0),
                  product("I2", stock=2.0, cost=None), product("N", stock=-2.0), product(None, name="x", stock=0.0),
                  product("Z", stock=0.0), product("A", stock=None)],
        sales_summary=[summary("L", units=10), summary("Z", units=0, observed_zero=True)],
        sales_monthly=monthly, window=window, owner=owner)


def test_evidence_states():
    assert classify_evidence({"units_total": 3, "observed_zero": False}) == "observed_units"
    assert classify_evidence({"units_total": 0, "observed_zero": True}) == "observed_zero"
    assert classify_evidence(None) == "no_row"


def test_ac_065_partition_and_ac_070_exclusions():
    out = run(_inputs())
    c = out.counts
    assert c["living"] == 1 and c["withdrawable"] == 2 and c["idle"] == 2
    assert c["excluded_negative_stock"] == 1 and c["excluded_no_identifier"] == 1 and c["excluded_stock_absent"] == 1
    assert out.withdrawn_barcodes == {"W", "Z"} and "N" not in out.withdrawn_barcodes


def test_ac_060_idle_is_never_withdrawn_and_ac_071_ranked_by_unit_cost_without_stock():
    out = run(_inputs())
    idle = [e for e in out.entries if e.characterisation == "idle"]
    assert [e.barcode for e in idle] == ["I", "I2"]                 # missing cost last
    assert idle[0].evidence["unit_cost"] == 34.0 and idle[1].evidence["unit_cost"] is None
    assert "recorded_stock" not in idle[0].evidence and all(e.value is None for e in idle)


def test_ac_063a_short_window_makes_every_withdrawal_provisional():
    out = run(_inputs())
    assert out.extras["provisional"] is True
    assert all(w["provisional"] for w in out.extras["withdrawn"])
    assert all("seasonal" in w["statement"] for w in out.extras["withdrawn"])
    assert "seasonal_misclassification_possible" in out.notes


def test_ac_063c_full_cycle_drops_the_statement():
    out = run(_inputs(window=W12))
    assert out.extras["provisional"] is False and "seasonal_misclassification_possible" not in out.notes


def test_ac_062_a_sale_revives_without_owner_action():
    inputs = _inputs()
    inputs.sales_summary["W"] = summary("W", units=1)
    assert "W" not in run(inputs).withdrawn_barcodes


def test_ac_063_manual_revival_holds_for_the_window_only():
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t",
                                  "revivals": {"W": {"at": 1, "window_id": W7.window_id}}})
    out = run(_inputs(owner=owner))
    assert "W" not in out.withdrawn_barcodes and out.counts["revived_manually"] == 1
    later = OwnerState.from_dict({"status": "available", "pulled_at": "t",
                                  "revivals": {"W": {"at": 1, "window_id": "old"}}})
    assert "W" in run(_inputs(owner=later)).withdrawn_barcodes


def test_ac_066_no_sales_evidence_means_no_classification():
    out = run(make_inputs(products=[product("W", stock=0.0)], sales_summary=None, window=None))
    assert out.status == "unavailable" and out.unavailable_reason == "no_sales_evidence"
    assert out.withdrawn_barcodes == set()


def test_ac_069_implausible_quantity_is_a_question_not_a_valuation():
    monthly = [{"barcode": "L", "month": "2026-01", "units": 10, "receipts": 0, "revenue": 1000.0}]
    inputs = make_inputs(products=[product("cups", stock=4005.0, cost=170.0), product("L", stock=1.0, cost=1.0)],
                         sales_summary=[summary("L", units=10)], sales_monthly=monthly, window=W7)
    out = run(inputs)
    q = [e for e in out.entries if e.characterisation == "implausible_quantity"]
    assert [e.barcode for e in q] == ["cups"]
    assert "valuation" not in q[0].evidence and q[0].evidence["recorded_stock"] == 4005.0 and q[0].value is None


def test_withdrawn_evidence_states_no_row_not_zero():
    out = run(_inputs())
    by = {w["barcode"]: w for w in out.extras["withdrawn"]}
    assert by["W"]["evidence_state"] == "no_row" and by["Z"]["evidence_state"] == "observed_zero"
