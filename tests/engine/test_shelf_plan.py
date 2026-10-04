"""Phase 8 Task 8.3: shelf_plan (F12-S1 FR-181 … FR-189, FR-192, FR-193; AC-174 … AC-181, AC-185 …
AC-187; SCN-161 … SCN-166)."""
from __future__ import annotations

import textwrap
from datetime import date, datetime, timedelta, timezone

import pytest
from helpers import make_inputs, product

from src.engine import shelf_plan
from src.engine.model import entry_id
from src.engine.publish import PublishRefused, check_f12_capability
from src.engine.store_layout import load_store_layout

RUN_AT = datetime(2026, 10, 12, 3, 0, tzinfo=timezone.utc)
LAST = date(2026, 10, 11)
STATED = "stated_by: owner\n    stated_on: 2026-10-01\n    recorded_by: team"


def P(barcode, *, shelf=10.0, cost=4.0, dept="drinks", stock=5.0, name=None):
    return product(barcode, name=name or f"p{barcode}", department=dept, shelf=shelf, cost=cost, stock=stock)


def _daily(per_day: dict, last=LAST, days=28) -> list:
    return [{"barcode": b, "day": (last - timedelta(days=back)).isoformat(), "units": float(u), "receipts": None}
            for back in range(days) for b, u in per_day.items()]


def _layout(tmp_path, catalogue, *, shelves=(100, 90), eye=1, widths=None, rules="", depts="[drinks]", extra=""):
    measured = "measured_by: team, measured_on: 2026-10-01"
    shelf_lines = "".join(f"      - {{length_cm: {n}, {measured}}}\n" for n in shelves)
    eye_line = f"    eye_level_shelf: {eye}\n" if eye else ""
    body = (f"fixtures:\n  F1:\n    departments: {depts}\n    chilled: false\n{eye_line}    {STATED}\n"
            f"    shelves:\n{shelf_lines}{extra}")
    if widths:
        body += "widths:\n" + "".join(f'  "{b}": {{width_mm: {w}, {measured}}}\n' for b, w in widths.items())
    if rules:
        body += "rules:\n" + textwrap.dedent(rules)
    path = tmp_path / "store_layout.yaml"
    path.write_text(body, encoding="utf-8")
    return load_store_layout(path, catalogue)


def _run(tmp_path, catalogue, daily, **layout):
    inputs = make_inputs(products=catalogue, sales_daily=daily, run_at=RUN_AT,
                         store_layout=_layout(tmp_path, catalogue, **layout))
    return shelf_plan.run(inputs)


def _plan(out):
    assert out.status == "available", (out.status, out.unavailable_reason)
    return out.entries[0].evidence


def _facings(plan) -> dict:
    return {p["barcode"]: (s["shelf"], p["facings"]) for s in plan["shelves"] for p in s["products"]}


# ── Waiting (FR-193, AC-172/173/185, SCN-166) ────────────────────────────────

def test_it_waits_for_the_layout_and_the_daily_reports(tmp_path):
    cat = [P("1")]
    assert shelf_plan.run(make_inputs(products=cat, sales_daily=_daily({"1": 1}), run_at=RUN_AT)).unavailable_reason \
        == "no_store_layout"
    out = shelf_plan.run(make_inputs(products=cat, run_at=RUN_AT, store_layout=_layout(tmp_path, cat)))
    assert (out.status, out.unavailable_reason) == ("unavailable", "no_daily_sales")


def test_too_few_report_days_is_no_evidence_window(tmp_path):
    out = _run(tmp_path, [P("1")], _daily({"1": 1}, days=10), widths={"1": 80})
    assert out.unavailable_reason == "no_evidence_window"


def test_reports_that_stopped_are_stale_daily_sales(tmp_path):
    out = _run(tmp_path, [P("1")], _daily({"1": 1}, last=LAST - timedelta(days=20)), widths={"1": 80})
    assert out.unavailable_reason == "stale_daily_sales"


# ── The packing (FR-182 … FR-185, AC-174, SCN-161) ───────────────────────────

def test_scn_161_eye_level_first_by_earnings_then_the_rest_by_fr_185(tmp_path):
    # Two shelves, 130 cm (eye level) and 90 cm; products 40, 40 and 60 cm wide. Margins 6, 4 and 2
    # a sale at the same demand rank them 1, 2, 3, so 1 and 2 take eye level, and 3 no longer fits.
    cat = [P("1", shelf=10, cost=4), P("2", shelf=10, cost=6), P("3", shelf=10, cost=8)]
    out = _run(tmp_path, cat, _daily({"1": 2, "2": 2, "3": 2}), shelves=(130, 90),
               widths={"1": 400, "2": 400, "3": 600})
    plan = _plan(out)
    facings = _facings(plan)
    assert facings["1"][0] == 1 and facings["2"][0] == 1 and facings["3"][0] == 2
    assert plan["shelves"][0]["eye_level"] is True
    # FR-185: shelf 1 has 50 cm left, room for one more facing, and it goes to the top earner.
    assert facings["1"] == (1, 2) and facings["2"] == (1, 1)
    # Shelf 2 has 30 cm left after product 3's first facing: no room for another.
    assert facings["3"] == (2, 1)
    assert plan["plan_window"]["last_day"] == LAST.isoformat() and plan["plan_date"] == "2026-10-12"
    assert [p["earnings_rank"] for p in plan["shelves"][0]["products"]] == [1, 2]


def test_each_further_facing_counts_for_less(tmp_path):
    # A lone top earner and a modest one share a long shelf: the top earner does not take every
    # facing, because its fourth earns less than the modest one's second.
    cat = [P("1", shelf=10, cost=4), P("2", shelf=10, cost=7)]
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=(1000,), widths={"1": 100, "2": 100}))
    f = _facings(plan)
    assert f["1"][1] == 4 and f["2"][1] == 4          # both reach the cap of 4 on a long shelf
    # 50 cm, five 10 cm facings. Product 1 earns twice what 2 does a cm, so it takes the 2nd and
    # 3rd facings. Its 4th would add 0.073 a cm, less than product 2's 2nd at 0.075, so 2 gets it.
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=(50,), widths={"1": 100, "2": 100}))
    assert _facings(plan) == {"1": (1, 3), "2": (1, 2)}


def test_the_facings_cap_and_his_rules_bound_extra_facings(tmp_path):
    cat = [P("1"), P("2")]
    rules = """\
      - {at_most: {barcode: "1", facings: 2}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}
      - {at_least: {barcode: "2", facings: 6}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}
    """
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 1}), shelves=(1000,), widths={"1": 100, "2": 100}, rules=rules))
    f = _facings(plan)
    assert f["1"][1] == 2 and f["2"][1] == 6          # at most 2; at least 6, above the cap of 4


# ── Unknown sizes and earnings (FR-180, FR-186, FR-187, AC-175, AC-177, SCN-162, SCN-165) ─────

def test_a_product_without_a_width_is_not_placed_and_stops_extra_facings(tmp_path):
    cat = [P("1"), P("2")]
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 2}), widths={"1": 100}))
    assert plan["unplaced"]["no_width"] == ["2"]
    assert _facings(plan) == {"1": (1, 1)} and plan["extra_facings"] == "no_width"


def test_a_product_wider_than_every_shelf_is_too_wide_not_over_full(tmp_path):
    cat = [P("1"), P("2")]
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=(50,), widths={"1": 600, "2": 600}))
    assert plan["state"] == "planned"
    assert [t["barcode"] for t in plan["unplaced"]["too_wide"]] == ["1", "2"]


def test_unknown_earnings_keep_one_facing_and_come_after_every_known_one(tmp_path):
    # INV-090, SCN-165: product 2 has no unit cost, so its margin is unknown. It sells most, yet it
    # is packed after both known products, off the eye-level shelf, with one facing.
    cat = [P("1", shelf=10, cost=6), P("2", shelf=10, cost=None), P("3", shelf=10, cost=8)]
    plan = _plan(_run(tmp_path, cat, _daily({"1": 1, "2": 9, "3": 1}), shelves=(40, 40),
                      widths={"1": 200, "2": 200, "3": 200}))
    f = _facings(plan)
    assert f["1"] == (1, 1) and f["3"] == (1, 1) and f["2"] == (2, 1)
    unknown = plan["shelves"][1]["products"][0]
    assert unknown["earnings_unknown"] == ["margin"] and unknown["earnings_unknown_because"] == ["no_unit_cost"]
    assert unknown["earnings_rank"] is None


def test_a_department_no_report_itemises_has_unknown_demand_never_zero(tmp_path):
    # AC-186's facing half: stocked by its count, one facing, demand published as unknown.
    cat = [P("1", dept="drinks"), P("2", dept="cleaning", stock=3.0)]
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2}), depts="[drinks, cleaning]", shelves=(1000,),
                      widths={"1": 100, "2": 100}))
    p2 = next(p for p in plan["shelves"][0]["products"] if p["barcode"] == "2")
    assert p2["facings"] == 1 and p2["daily_mean"] is None and p2["earnings_unknown"] == ["demand"]


def test_zero_demand_is_a_known_zero_one_facing_and_no_more(tmp_path):
    # FR-189: itemised, kept on by his rule, and no sale: earnings known to be zero.
    cat = [P("1"), P("2")]
    rules = '  - {keep_on: {barcode: "2", fixture: F1}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 0}), shelves=(1000,), widths={"1": 100, "2": 100}, rules=rules))
    p2 = next(p for p in plan["shelves"][0]["products"] if p["barcode"] == "2")
    assert p2["facings"] == 1 and p2["daily_mean"] == 0.0 and p2["earnings_unknown"] == []


# ── Over-full and rules (FR-184, FR-188, AC-176, AC-178, SCN-163, SCN-164) ────

def test_an_over_full_fixture_gets_no_plan_and_drops_no_one(tmp_path):
    cat = [P("1"), P("2"), P("3")]
    plan = _plan(_run(tmp_path, cat, _daily({"1": 3, "2": 2, "3": 1}), shelves=(50,),
                      widths={"1": 300, "2": 300, "3": 300}))
    assert plan["state"] == "over_full" and plan["shelves"] is None
    assert plan["did_not_fit_cm"] == 60.0 and plan["planned"] == ["1", "2", "3"]


def test_a_rule_that_cannot_be_met_stops_the_plan_and_is_named(tmp_path):
    cat = [P("1"), P("2")]
    rules = '  - {at_least: {barcode: "1", facings: 4}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=(50,), widths={"1": 200, "2": 200}, rules=rules))
    assert plan["state"] == "stopped_by_rule"
    assert plan["stopped_by"]["kind"] == "at_least" and plan["stopped_by"]["why"] == "does_not_fit"


def test_a_together_set_longer_than_any_shelf_stops_the_plan(tmp_path):
    cat = [P("1"), P("2")]
    rules = '  - {together: {barcodes: ["1", "2"]}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=(30, 30), widths={"1": 200, "2": 200}, rules=rules))
    assert plan["stopped_by"]["why"] == "longer_than_any_shelf"


def test_a_together_set_shares_one_shelf(tmp_path):
    cat = [P("1", cost=1), P("2", cost=8), P("3", cost=2)]
    rules = '  - {together: {barcodes: ["1", "2"]}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 2, "3": 2}), shelves=(40, 40),
                      widths={"1": 200, "2": 200, "3": 200}, rules=rules))
    f = _facings(plan)
    assert f["1"][0] == f["2"][0] == 1 and f["3"][0] == 2


def test_every_catalogue_product_is_placed_or_named(tmp_path):
    # INV-088 / AC-176.
    cat = [P("1"), P("2"), P("3", stock=0.0), P("4")]
    rules = '  - {keep_off: {barcode: "4", fixture: F1}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2}), widths={"1": 50}, rules=rules))
    placed = set(_facings(plan))
    named = {b for k, v in plan["unplaced"].items() for b in v if isinstance(b, str)}
    assert placed == {"1"} and named == {"2", "3", "4"}
    assert plan["unplaced"]["no_sale_in_window"] == ["2", "3"] and plan["unplaced"]["kept_off"] == ["4"]


# ── What is published (FR-189, FR-192, INV-087, AC-180, AC-181, AC-187) ───────

def test_one_shelf_plan_entry_per_fixture_with_no_value_and_no_product(tmp_path):
    out = _run(tmp_path, [P("1")], _daily({"1": 2}), widths={"1": 80})
    e = out.entries[0]
    assert (e.signal_family, e.action, e.barcode, e.product_name, e.department, e.value) == \
        ("shelf.plan", "arrange_shelf", None, None, None, None)
    assert e.id == entry_id("shelf.plan", None, "F1|2026-10-12")
    assert out.extras["elasticity"] == {"value": 0.17, "source": "research", "why": "his_own_not_yet_measured"}
    assert out.thresholds == {"elasticity": 0.17, "facings_cap": 4}


def test_the_conditions_carry_every_date(tmp_path):
    plan = _plan(_run(tmp_path, [P("1")], _daily({"1": 2}), widths={"1": 80}))
    assert plan["stated_on"] == "2026-10-01" and plan["shelves"][0]["measured_on"] == "2026-10-01"
    assert plan["shelves"][0]["products"][0]["width_measured_on"] == "2026-10-01"
    assert plan["plan_window"] == {"first_day": (LAST - timedelta(days=27)).isoformat(), "last_day": LAST.isoformat()}


def test_the_publisher_refuses_any_money_figure_but_margin_per_sale(tmp_path):
    out = _run(tmp_path, [P("1")], _daily({"1": 2}), widths={"1": 80})
    cap = out.to_dict()
    check_f12_capability("shelf_plan", cap)                  # margin_per_sale is the one allowed
    assert "per_cm" not in str(cap)                          # the plan never publishes its ₪ rate
    for field in ("earnings_per_cm", "total_margin"):
        bad = out.to_dict()
        bad["entries"][0]["evidence"]["shelves"][0]["products"][0][field] = 1.0
        with pytest.raises(PublishRefused, match=field):
            check_f12_capability("shelf_plan", bad)
