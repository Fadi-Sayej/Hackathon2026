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


# ── Phase 5 Task 5.9: the disagreement question (FR-158, FR-159, D-20, ADR-034) ──────────

import hashlib
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

from src.engine.policy import load_policy

ON = replace(load_policy(), order_publish_disagreement_questions=True)
RUN_AT = datetime(2026, 10, 28, 3, tzinfo=timezone.utc)
LAST = date(2026, 10, 28)
DAYS = [(LAST - timedelta(days=i)).isoformat() for i in range(28)]
DEPT, SILENT = "משקאות", "סיגריות"


def _daily(barcode, days, units=1.0, receipts=0.0):
    return [{"barcode": barcode, "day": d, "units": units, "receipts": receipts} for d in days]


def _signal(*barcodes, on_day=LAST.isoformat()):
    return {"on_day": on_day, "stores": ["s1", "s2"], "excluded": [],
            "products": {b: {"stores_out": ["s1", "s2"], "days_absent": {"s1": 3, "s2": 5}} for b in barcodes}}


def _f8(policy=ON, owner=None, rows=None, running="default", products=None, withdrawn=None, idle=None, monthly=None):
    rows = rows if rows is not None else (
        _daily("steady", DAYS)                         # moving: gets a quantity, not a question
        + _daily("slow", DAYS[21:])                    # sold only in the oldest week: not moving
        + _daily("stocked", DAYS[:1], units=0.0, receipts=6.0))   # delivered, never sold
    prods = products if products is not None else [
        product("steady", department=DEPT, shelf=4.0, cost=1.0, stock=5.0),
        product("slow", department=DEPT, shelf=4.0, cost=1.0, stock=5.0),
        product("stocked", department=DEPT, shelf=4.0, cost=1.0, stock=5.0),
        product("absent", department=DEPT, shelf=4.0, cost=1.0, stock=5.0)]     # no sale, no delivery
    return make_inputs(products=prods, sales_daily=rows, sales_monthly=monthly or [], policy=policy,
                       running_out=_signal("steady", "slow", "stocked", "absent", "silent") if running == "default" else running,
                       owner=owner, withdrawn=withdrawn or set(), idle=idle or set(), run_at=RUN_AT)


def _disagreements(inputs):
    return [i for i in run(inputs).extras["items"] if i["fact"] == "market_disagreement"]


def test_the_market_running_out_of_what_he_stocks_but_does_not_sell_raises_one_question():
    """SCN-141: sold in one of four weeks, or stocked and never sold: asked. Moving: not
    asked, it gets a quantity. Never stocked: not asked, that is F9's question (FR-082)."""
    got = _disagreements(_f8())
    assert [q["barcode"] for q in got] == ["slow", "stocked"]
    slow = got[0]
    assert slow["question_id"] == hashlib.sha256(b"market_disagreement|slow").hexdigest()[:16]
    assert slow["why"] == {"stores_out": 2, "days_absent": [3, 5], "units_in_window": 7.0,
                           "weekly_units": [7.0, 0.0, 0.0, 0.0], "report_days": 28, "no_sales_row": False}
    assert slow["answers"] == ["shelf_place", "price", "weak_market", "sells_elsewhere"]
    assert slow["expected_value"] is None and "money_at_stake" not in slow["why"]


def test_answered_it_is_retired_for_good_even_when_the_facts_change():
    """D-20 over FR-089: once he has said why, it is never asked again."""
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t", "answers": {
        "slow": {"market_disagreement": {"status": "answered", "value": "weak_market"}}}})
    assert [q["barcode"] for q in _disagreements(_f8(owner=owner))] == ["stocked"]
    changed = _daily("steady", DAYS) + _daily("slow", DAYS[14:]) + _daily("stocked", DAYS[:1], units=0.0, receipts=6.0)
    assert "slow" not in {q["barcode"] for q in _disagreements(_f8(owner=owner, rows=changed))}


def test_a_deferred_one_is_open_but_not_presented():
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t", "answers": {
        "slow": {"market_disagreement": {"status": "deferred"}}}})
    assert "slow" not in {q["barcode"] for q in _disagreements(_f8(owner=owner))}


def test_no_window_raises_none_except_where_no_evidence_itemises_the_department():
    """SCN-148 / INV-075: "not moving" is measured over a window. FR-156's department has no
    row in any evidence, so there it is asked, saying the sales evidence has no row for it."""
    thin = _daily("slow", DAYS[:20])                                  # 20 report days: no window
    prods = [product("slow", department=DEPT, shelf=4.0, cost=1.0, stock=5.0),
             product("silent", department=SILENT, shelf=4.0, cost=1.0, stock=3.0),
             product("silent_empty", department=SILENT, shelf=4.0, cost=1.0, stock=0.0)]
    got = _disagreements(_f8(rows=thin, products=prods,
                             running=_signal("slow", "silent", "silent_empty")))
    assert [q["barcode"] for q in got] == ["silent"]
    assert got[0]["why"] == {"stores_out": 2, "days_absent": [3, 5], "units_in_window": None,
                             "weekly_units": None, "report_days": None, "no_sales_row": True}


def test_with_the_market_signal_withheld_none_is_raised():
    """AC-142, and a stale signal describes no night at all."""
    assert _disagreements(_f8(running=None)) == []
    assert _disagreements(_f8(running=_signal("slow", "stocked", on_day="2026-10-20"))) == []


def test_idle_and_withdrawn_products_he_stocks_are_asked():
    """C-67: an idle product is stocked and does not sell, which is exactly D-19's case, and
    F4's withdrawn class is never the test: his stocking, read from the window, is."""
    got = _disagreements(_f8(withdrawn={"slow"}, idle={"stocked"}))
    assert [q["barcode"] for q in got] == ["slow", "stocked"]


def test_they_follow_every_question_with_money():
    """C-68, ADR-027: no ₪ figure, so after every question that has one."""
    prods = [product("costless", department=DEPT, shelf=10.0, cost=None, stock=5.0),
             product("slow", department=DEPT, shelf=4.0, cost=1.0, stock=5.0)]
    inputs = _f8(products=prods, running=_signal("slow"))
    inputs.sales_summary = {"costless": summary("costless", units=50)}
    facts = [i["fact"] for i in run(inputs).extras["items"]]
    assert facts == ["cost_price", "market_disagreement"]


def test_no_why_claims_the_market_sells_a_lot_or_that_he_sold_nothing():
    """§21: competitor volumes are not observed; a missing day is not a zero-sales day."""
    for q in _disagreements(_f8()):
        text = json.dumps(q, ensure_ascii=False).lower()
        assert "sells_a_lot" not in text and "a lot" not in text and "zero_sales" not in text


def test_with_the_flag_off_the_items_are_unchanged_byte_for_byte():
    """The flag is on since Task 5.14; off, it must still take the question out completely, so
    turning it off again is a real way back."""
    v1 = _inputs()
    v1.policy = replace(v1.policy, order_publish_disagreement_questions=False)
    plain = run(v1)
    off = _inputs()
    off.policy = replace(off.policy, order_publish_disagreement_questions=False)
    off.sales_daily = _daily("live1", DAYS)
    off.running_out = _signal("live1", "live2")
    off.run_at = RUN_AT
    with_f8 = run(off)
    assert json.dumps(with_f8.extras, sort_keys=True) == json.dumps(plain.extras, sort_keys=True)
    assert with_f8.counts == plain.counts


def test_the_cost_question_id_is_unchanged():
    q = run(_inputs()).extras["items"][0]
    assert q["question_id"] == hashlib.sha256(f"cost_price|{q['barcode']}".encode()).hexdigest()[:16]


def test_every_question_matches_the_published_question_shape():
    import jsonschema
    schema = json.loads((Path(__file__).resolve().parents[2] / "schemas" / "dashboard.schema.json").read_text(encoding="utf-8"))
    question = {**schema["$defs"]["question"], "$defs": schema["$defs"]}
    inputs = _f8()
    inputs.sales_summary = {"slow": summary("slow", units=5)}
    items = run(inputs).extras["items"]
    assert {i["fact"] for i in items} == {"market_disagreement"}
    for item in items + run(_inputs()).extras["items"]:
        jsonschema.validate(item, question)
    bad = {**items[0], "why": {**items[0]["why"], "money_at_stake": 3.0}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, question)


import pytest  # noqa: E402
