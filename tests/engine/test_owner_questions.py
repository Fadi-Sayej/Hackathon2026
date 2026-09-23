# tests/engine/test_owner_questions.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product, summary, window_of
from src.engine.owner_questions import run
from src.owner_state.model import OwnerState

W = window_of(["2026-01", "2026-07"])


def _inputs(owner=None, withdrawn=None, idle=None):
    return make_inputs(
        products=[product("live1", shelf=10.0, cost=None, stock=5.0),      # asked (186 units)
                  product("live2", shelf=4.0, cost=None, stock=5.0),       # asked (84 units)
                  product("live3", shelf=1.0, cost=2.0, stock=5.0),        # has a cost → no question
                  product("dead", shelf=3.0, cost=None, stock=0.0),        # withdrawn → suppressed
                  product("idle1", shelf=3.0, cost=None, stock=9.0)],      # idle → suppressed
        sales_summary=[summary("live1", units=186), summary("live2", units=84), summary("live3", units=5)],
        window=W, owner=owner, withdrawn=withdrawn if withdrawn is not None else {"dead"},
        idle=idle if idle is not None else {"idle1"})


def test_ac_088_only_questions_that_change_an_output():
    q = run(_inputs()).extras
    assert [i["barcode"] for i in q["items"]] == ["live1", "live2"]
    assert q["suppressed"]["no_effect"] >= 1          # live3 already has a cost


def test_ac_081_withdrawn_and_idle_are_suppressed():
    q = run(_inputs()).extras
    assert "dead" not in {i["barcode"] for i in q["items"]}
    assert "idle1" not in {i["barcode"] for i in q["items"]}
    assert q["suppressed"]["withdrawn"] == 1 and q["suppressed"]["idle"] == 1


def test_ac_080_the_limit_is_published_and_never_above_three():
    q = run(_inputs()).extras
    assert q["limit"] == 3


def test_ac_083_ordering_is_by_expected_value():
    items = run(_inputs()).extras["items"]
    assert items[0]["barcode"] == "live1"
    assert items[0]["expected_value"] > items[1]["expected_value"]


def test_ac_082_suppressed_counts_are_reportable():
    out = run(_inputs())
    assert out.counts["open"] == 2 and out.counts["suppressed_withdrawn"] == 1 and out.counts["suppressed_idle"] == 1


def test_ac_087_an_answered_question_is_not_re_presented():
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t",
                                  "answers": {"live1": {"cost_price": {"value": 3.0, "at": 1, "status": "answered"}}}})
    # inputs.products already carries the owner's cost (load_inputs applies it), so simulate that:
    inputs = _inputs(owner=owner)
    for p in inputs.products:
        if p["barcode"] == "live1":
            p["cost_price"], p["cost_source"] = 3.0, "owner"
    q = run(inputs).extras
    assert "live1" not in {i["barcode"] for i in q["items"]}
    assert q["suppressed"]["answered"] == 1


def test_ac_086_a_deferral_leaves_the_question_open_but_unpresented():
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t",
                                  "answers": {"live1": {"cost_price": {"value": None, "at": 1, "status": "deferred"}}}})
    q = run(_inputs(owner=owner)).extras
    assert "live1" not in {i["barcode"] for i in q["items"]}    # deferred: not shown
    assert q["suppressed"]["answered"] == 0                      # and not recorded as content


def test_storage_unavailable_means_no_questions_are_presented():
    out = run(_inputs(owner=OwnerState.unavailable("pull_failed")))
    assert out.status == "unavailable" and out.unavailable_reason == "answer_storage_unavailable"
    assert out.extras["items"] == []


# ── ADR-027: a question whose money is unknown carries no figure ───────────────────────
#
# #130. A missing shelf price was read as 0.0: the question published "₪0 at stake" for a
# stake that is unknown, and sorted last, which under D-8's cap of three means unseen.

def _priced_and_unpriced():
    return make_inputs(
        products=[product("cheap_one", shelf=10.0, cost=None, stock=5.0),     # 1 unit    -> ₪10
                  product("noprice_50", shelf=None, cost=None, stock=5.0),    # 50 units, no price
                  product("dear_one", shelf=2.0, cost=None, stock=5.0),       # 100 units -> ₪200
                  product("noprice_80", shelf=None, cost=None, stock=5.0)],   # 80 units, no price
        sales_summary=[summary("cheap_one", units=1), summary("noprice_50", units=50),
                       summary("dear_one", units=100), summary("noprice_80", units=80)],
        window=W)


def test_adr_027_an_unknown_shelf_price_publishes_no_figure_and_names_what_is_missing():
    q = {i["barcode"]: i for i in run(_priced_and_unpriced()).extras["items"]}["noprice_50"]
    assert q["why"]["money_at_stake"] is None and q["expected_value"] is None
    assert q["why"]["money_missing"] == "shelf_price"
    assert q["why"]["units_sold"] == 50.0


def test_adr_027_a_known_price_keeps_its_figure_and_says_nothing_is_missing():
    q = {i["barcode"]: i for i in run(_priced_and_unpriced()).extras["items"]}["dear_one"]
    assert (q["why"]["money_at_stake"], q["expected_value"], q["why"]["money_missing"]) == (200.0, 200.0, None)


def test_adr_027_questions_with_a_figure_come_first_then_the_rest_by_units_sold():
    order = [i["barcode"] for i in run(_priced_and_unpriced()).extras["items"]]
    assert order == ["dear_one", "cheap_one", "noprice_80", "noprice_50"]


def test_adr_027_the_missing_figure_reaches_the_published_file_as_null(tmp_path, monkeypatch):
    """Rule 12: the tests above read `run`'s return value. This one runs the engine and the
    publisher and reads the file the browser fetches, where a None could still have become
    a 0 or dropped out."""
    import json
    import src.engine.run as run_mod
    from helpers import RUN_AT
    inputs = _priced_and_unpriced()
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: inputs.owner)
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: None)
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "load_inputs", lambda **kw: inputs)
    run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json", now=RUN_AT)
    items = json.loads((tmp_path / "d.json").read_text())["capabilities"]["owner_questions"]["items"]
    q = {i["barcode"]: i for i in items}["noprice_80"]
    assert (q["why"]["money_at_stake"], q["expected_value"], q["why"]["money_missing"]) == (None, None, "shelf_price")
    assert [i["barcode"] for i in items] == ["dear_one", "cheap_one", "noprice_80", "noprice_50"]
