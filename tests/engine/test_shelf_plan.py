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
    assert [p["rank"] for p in plan["shelves"][0]["products"]] == [1, 2]


def test_no_shelf_is_left_empty_while_products_remain(tmp_path):
    # F12-S1 v0.9 FR-183, found by the mockups (docs/reviews/F12-screens-mockups.md): six 10 cm
    # products fit on one 120 cm shelf, and the old packing left the other 120 cm shelf empty.
    # First facings now spread by shelf length, 30 cm a shelf, so each shelf holds three, the top
    # three earners at eye level, and each shelf's spare length becomes extra facings.
    cat = [P(str(n), shelf=10, cost=10 - n) for n in range(1, 7)]
    plan = _plan(_run(tmp_path, cat, _daily({str(n): 2 for n in range(1, 7)}), shelves=(120, 120),
                      widths={str(n): 100 for n in range(1, 7)}))
    eye, other = plan["shelves"]
    assert eye["eye_level"] and [p["rank"] for p in eye["products"]] == [1, 2, 3]
    assert [p["rank"] for p in other["products"]] == [4, 5, 6]
    assert eye["used_cm"] == 120 and other["used_cm"] == 120      # the cap of 4 fills both


def test_where_a_size_is_unknown_the_top_earners_keep_eye_level(tmp_path):
    # A product of unmeasured width stands on the unit, so no spare length is known to be free and
    # no extra facings are given (FR-186). Spreading would then only move top earners off eye level
    # into space nothing fills, so each product goes on the first shelf with room, as before v0.9.
    cat = [P(str(n), shelf=10, cost=10 - n) for n in range(1, 8)]
    plan = _plan(_run(tmp_path, cat, _daily({str(n): 2 for n in range(1, 8)}), shelves=(120, 120),
                      widths={str(n): 100 for n in range(1, 7)}))
    assert plan["extra_facings"] == "no_width" and plan["unplaced"]["no_width"] == ["7"]
    assert [p["rank"] for p in plan["shelves"][0]["products"]] == [1, 2, 3, 4, 5, 6]


def test_a_shelf_too_short_for_its_share_still_takes_its_top_earner(tmp_path):
    # The eye-level shelf's share (20 cm of 60 cm on 40 + 80) is narrower than the top earner,
    # which goes there all the same: a shelf takes the next product while it is empty.
    # Earnings a cm at the same demand: 6/30, 2/15 and 1/15, so they rank 1, 3, 2.
    cat = [P("1", shelf=10, cost=4), P("2", shelf=10, cost=9), P("3", shelf=10, cost=8)]
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 2, "3": 2}), shelves=(40, 80),
                      widths={"1": 300, "2": 150, "3": 150}))
    assert [p["barcode"] for p in plan["shelves"][0]["products"]] == ["1"]
    assert [p["barcode"] for p in plan["shelves"][1]["products"]] == ["3", "2"]


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
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=(50,), widths={"1": 600, "2": 200}))
    assert plan["state"] == "planned" and _facings(plan) == {"2": (1, 1)}
    assert [t["barcode"] for t in plan["unplaced"]["too_wide"]] == ["1"]
    assert plan["extra_facings"] == "too_wide"


def test_a_fixture_with_nothing_to_place_gets_no_plan(tmp_path):
    # §12: shown by layout_facts, and no plan, never an empty one called a plan.
    cat = [P("1"), P("2")]
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=(50,), widths={"1": 600, "2": 600}))
    assert plan["state"] == "nothing_placeable" and plan["shelves"] is None
    unstocked = [P("1", stock=0.0), P("2", stock=0.0)]          # no report itemises them; counts at zero
    out = _run(tmp_path, unstocked, _daily({"9": 1}), widths={"1": 100})
    assert out.entries[0].evidence["state"] == "no_planned_products" and out.entries[0].actionable is False


def test_unknown_earnings_keep_one_facing_and_come_after_every_known_one(tmp_path):
    # INV-090, SCN-165: product 2 has no unit cost, so its margin is unknown. It sells most, yet it
    # is packed after both known products, off the eye-level shelf, with one facing. The 60 cm of
    # first facings spread 30 cm a shelf (FR-183): the top earner alone at eye level, where its
    # spare 20 cm becomes a second facing, and the other two on shelf 2.
    cat = [P("1", shelf=10, cost=6), P("2", shelf=10, cost=None), P("3", shelf=10, cost=8)]
    plan = _plan(_run(tmp_path, cat, _daily({"1": 1, "2": 9, "3": 1}), shelves=(40, 40),
                      widths={"1": 200, "2": 200, "3": 200}))
    f = _facings(plan)
    assert f["1"] == (1, 2) and f["3"] == (2, 1) and f["2"] == (2, 1)
    unknown = next(p for p in plan["shelves"][1]["products"] if p["barcode"] == "2")
    assert unknown["unknown_parts"] == ["margin"] and unknown["unknown_because"] == ["no_unit_cost"]
    assert unknown["rank"] is None


def test_a_department_no_report_itemises_has_unknown_demand_never_zero(tmp_path):
    # AC-186's facing half: stocked by its count, one facing, demand published as unknown.
    cat = [P("1", dept="drinks"), P("2", dept="cleaning", stock=3.0)]
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2}), depts="[drinks, cleaning]", shelves=(1000,),
                      widths={"1": 100, "2": 100}))
    p2 = next(p for p in plan["shelves"][0]["products"] if p["barcode"] == "2")
    assert p2["facings"] == 1 and p2["daily_mean"] is None and p2["unknown_parts"] == ["demand"]


def test_zero_demand_is_a_known_zero_one_facing_and_no_more(tmp_path):
    # FR-189: itemised, kept on by his rule, and no sale: earnings known to be zero.
    cat = [P("1"), P("2")]
    rules = '  - {keep_on: {barcode: "2", fixture: F1}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
    plan = _plan(_run(tmp_path, cat, _daily({"1": 2, "2": 0}), shelves=(1000,), widths={"1": 100, "2": 100}, rules=rules))
    p2 = next(p for p in plan["shelves"][0]["products"] if p["barcode"] == "2")
    assert p2["facings"] == 1 and p2["daily_mean"] == 0.0 and p2["unknown_parts"] == []


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
    # FR-206: no arrangement recorded, so the research value, saying why.
    assert out.extras["elasticity"] == {"value": 0.17, "source": "research", "why": "measurement_unavailable",
                                        "measurement_reason": "no_arrangement_recorded"}
    assert out.thresholds == {"elasticity": 0.17, "facings_cap": 4, "height_clearance_mm": 20}


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



# ── The review's cases (Phase 8 PR 1) ────────────────────────────────────────

def test_at_least_does_not_turn_a_fitting_fixture_over_full(tmp_path):
    # 100 cm: A (20 cm, ranked first) and B (30 cm). First facings need 50 cm, so the fixture is
    # not over-full, whatever his rule asks. "At least 3" takes 40 cm more and fits; "at least 4"
    # takes 60 cm more, does not fit, and is the rule named, not "over-full, 30 cm did not fit".
    cat = [P("A", cost=1), P("B", cost=8)]
    rule = '  - {{at_least: {{barcode: "A", facings: {n}}}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}}\n'
    plan = _plan(_run(tmp_path, cat, _daily({"A": 2, "B": 2}), shelves=(100,), widths={"A": 200, "B": 300},
                      rules=rule.format(n=3)))
    assert plan["state"] == "planned" and _facings(plan) == {"A": (1, 3), "B": (1, 1)}
    plan = _plan(_run(tmp_path, cat, _daily({"A": 2, "B": 2}), shelves=(100,), widths={"A": 200, "B": 300},
                      rules=rule.format(n=4)))
    assert (plan["state"], plan["stopped_by"]["why"]) == ("stopped_by_rule", "does_not_fit")


def test_a_genuinely_over_full_fixture_is_over_full_whatever_the_rules(tmp_path):
    cat = [P("A", cost=1), P("B", cost=8)]
    rules = '  - {at_least: {barcode: "A", facings: 4}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
    plan = _plan(_run(tmp_path, cat, _daily({"A": 2, "B": 2}), shelves=(40,), widths={"A": 200, "B": 300}, rules=rules))
    assert plan["state"] == "over_full" and plan["did_not_fit_cm"] == 30.0


def test_at_least_where_a_size_is_unknown_cannot_be_met(tmp_path):
    # INV-091 / FR-186: with a product of no width on the shelf, no spare length is known to be free.
    cat = [P("A"), P("B")]
    rules = '  - {at_least: {barcode: "A", facings: 3}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
    plan = _plan(_run(tmp_path, cat, _daily({"A": 2, "B": 2}), shelves=(500,), widths={"A": 100}, rules=rules))
    assert (plan["state"], plan["stopped_by"]["why"]) == ("stopped_by_rule", "sizes_unknown")


@pytest.mark.parametrize("why, layout", [
    ("no_width", {"widths": {"B": 100}}),
    ("product_not_planned", {"widths": {"A": 100, "B": 100}, "daily": {"B": 2}}),
])
def test_at_least_on_a_product_the_plan_does_not_place_stops_the_plan(tmp_path, why, layout):
    # FR-188: never dropped silently.
    cat = [P("A"), P("B")]
    rules = '  - {at_least: {barcode: "A", facings: 2}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
    plan = _plan(_run(tmp_path, cat, _daily(layout.get("daily", {"A": 2, "B": 2})), shelves=(500,),
                      widths=layout["widths"], rules=rules))
    assert (plan["state"], plan["stopped_by"]["why"]) == ("stopped_by_rule", why)


def test_a_stocked_product_a_keep_on_rule_places_earns_facings_like_any_other(tmp_path):
    # FR-198's single facing is for a product he does not stock. FR-199 makes every product of a
    # split department need such a rule, and they must not all be held to one facing.
    cat = [P("A"), P("B")]
    rules = ('  - {keep_on: {barcode: "A", fixture: F1}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
             '  - {keep_on: {barcode: "B", fixture: F1}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n')
    plan = _plan(_run(tmp_path, cat, _daily({"A": 2, "B": 0}), shelves=(1000,), widths={"A": 100, "B": 100}, rules=rules))
    f = _facings(plan)
    assert f["A"][1] == 4 and f["B"][1] == 1                 # B is not stocked: one facing, by FR-198


def test_the_plans_demand_is_order_quantitys_daily_mean(tmp_path):
    # AC-179 (INV-085): wherever order_quantity publishes a daily_mean, the plan's demand equals it.
    from src.engine import order_quantity
    cat = [P("1"), P("2")]
    # Units that change by the day, so a demand taken over any other window would not match.
    daily = [{**r, "units": float((int(r["day"][-2:]) * (3 if r["barcode"] == "1" else 1)) % 7)}
             for r in _daily({"1": 1, "2": 1}, days=60)]
    facts = {"facts": {"drinks": {"order_schedule": {"form": "weekdays", "weekdays": ["sun"]},
                                  "shelf_life": {"days": 30}, "stated_by": "owner", "stated_on": "2026-10-01",
                                  "recorded_by": "team"}}, "rejected": []}
    inputs = make_inputs(products=cat, sales_daily=daily, run_at=RUN_AT, store_facts=facts,
                         store_layout=_layout(tmp_path, cat, widths={"1": 100, "2": 100}))
    suggested = {e.barcode: e.evidence["daily_mean"] for e in order_quantity.run(inputs).entries}
    planned = {p["barcode"]: p["daily_mean"] for s in shelf_plan.run(inputs).entries[0].evidence["shelves"]
               for p in s["products"]}
    assert suggested and all(planned[b] == mean for b, mean in suggested.items())


def test_the_money_guard_refuses_earnings_profit_and_gain_whatever_they_are_called(tmp_path):
    out = _run(tmp_path, [P("1")], _daily({"1": 2}), widths={"1": 80})
    check_f12_capability("shelf_plan", out.to_dict())
    for field in ("earnings", "profit_per_facing", "gain"):
        bad = out.to_dict()
        bad["entries"][0]["evidence"][field] = 1.0
        with pytest.raises(PublishRefused, match=field):
            check_f12_capability("shelf_plan", bad)


def test_no_f12_capability_registers_a_figure(tmp_path):
    # scripts/figures.py lists them as registering none, so their being unavailable is not a lost
    # figure. This keeps that claim true from the code's side.
    import importlib.util
    from pathlib import Path
    from src.engine import layout_facts, shelf_measurement
    spec = importlib.util.spec_from_file_location("figures", Path(__file__).resolve().parents[2] / "scripts" / "figures.py")
    figures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(figures)
    inputs = make_inputs(products=[P("1")], sales_daily=_daily({"1": 2}), run_at=RUN_AT,
                         store_layout=_layout(tmp_path, [P("1")], widths={"1": 80}))
    for module in (layout_facts, shelf_plan, shelf_measurement):
        assert module.run(inputs).figures == [], module.CAP
        assert module.CAP in figures._REGISTERS_NO_FIGURE



def test_at_least_on_a_product_of_unknown_earnings_cannot_be_met(tmp_path):
    # FR-187, INV-086: such a product gets no more than one facing, so his rule cannot be obeyed,
    # and FR-188 stops the plan and names it.
    cat = [P("A", cost=None), P("B")]
    rules = '  - {at_least: {barcode: "A", facings: 3}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}\n'
    plan = _plan(_run(tmp_path, cat, _daily({"A": 2, "B": 2}), shelves=(500,), widths={"A": 100, "B": 100}, rules=rules))
    assert (plan["state"], plan["stopped_by"]["why"]) == ("stopped_by_rule", "earnings_unknown")


# ── Pictures (D-33; F12-S1 FR-216, FR-217, AC-206) ───────────────────────────

def test_a_pictures_address_reaches_the_plan_and_changes_nothing_else(tmp_path):
    import copy
    from src.engine import layout_facts
    cat = [P("1", shelf=10, cost=4), P("2", shelf=10, cost=6)]
    daily = _daily({"1": 2, "2": 2})
    plain = _layout(tmp_path, cat, shelves=(100,), widths={"1": 100, "2": 100})
    pictured = copy.deepcopy(plain)
    pictured["pictures"] = {"1": {"file": "1.png", "src": "/store/shelf-pictures/1.png?v=2026-10-01",
                                  "cropped_by": "reader", "cropped_on": "2026-10-01"}}

    def run(layout):
        inputs = make_inputs(products=cat, sales_daily=daily, run_at=RUN_AT, store_layout=layout)
        return shelf_plan.run(inputs).to_dict(), layout_facts.run(inputs).to_dict()

    (plan_a, facts_a), (plan_b, facts_b) = run(plain), run(pictured)
    placed = {p["barcode"]: p for s in plan_b["entries"][0]["evidence"]["shelves"] for p in s["products"]}
    assert placed["1"]["picture"] == "/store/shelf-pictures/1.png?v=2026-10-01" and placed["2"]["picture"] is None
    assert facts_b["pictures"] == {"1": {"src": "/store/shelf-pictures/1.png?v=2026-10-01", "cropped_on": "2026-10-01"}}
    assert facts_b["without_picture"] == {"F1": ["2"]} and facts_a["without_picture"] == {"F1": ["1", "2"]}

    # AC-206: take the picture fields away, and both capabilities are what they were without them.
    for s in plan_b["entries"][0]["evidence"]["shelves"]:
        for p in s["products"]:
            p["picture"] = None
    assert plan_b == plan_a
    for f in (facts_a, facts_b):
        f.pop("pictures"), f.pop("without_picture"), f["counts"].pop("without_picture")
    assert facts_b == facts_a


# ── Heights (D-38; F12-S1 v0.12 FR-233, AC-219) ──────────────────────────────

def _tall(tmp_path, catalogue, daily, *, shelves, heights, widths, eye=1, rules=""):
    """A unit whose shelves carry heights: (length cm, height cm or None) from the top."""
    measured = "measured_by: owner, measured_on: 2026-10-01"
    shelf_lines = "".join(f"      - {{length_cm: {n}, height_cm: {'null' if h is None else h}, {measured}}}\n"
                          for n, h in shelves)
    body = (f"fixtures:\n  F1:\n    departments: [drinks]\n    chilled: false\n    eye_level_shelf: {eye}\n"
            f"    stated_by: owner\n    stated_on: 2026-10-01\n    recorded_by: app\n    shelves:\n{shelf_lines}")
    body += "widths:\n" + "".join(f'  "{b}": {{width_mm: {w}, measured_by: team, measured_on: 2026-10-01}}\n'
                                  for b, w in widths.items())
    if rules:
        body += "rules:\n" + textwrap.dedent(rules)
    path = tmp_path / "store_layout.yaml"
    path.write_text(body, encoding="utf-8")
    layout = load_store_layout(path, catalogue)
    assert not layout["rejected"], layout["rejected"]
    layout["heights"] = {b: {"height_mm": h, "measured_by": "reader", "measured_on": "2026-10-01"}
                         for b, h in heights.items()}
    return _plan(shelf_plan.run(make_inputs(products=catalogue, sales_daily=daily, run_at=RUN_AT, store_layout=layout)))


def test_a_product_goes_only_under_a_shelf_it_fits_with_the_clearance(tmp_path):
    # Eye level (shelf 1) is 30 cm high; a 29 cm bottle needs 31 cm with the 2 cm clearance, so it
    # passes over eye level to the 40 cm shelf, though it earns the most.
    cat = [P("1", shelf=10, cost=2), P("2", shelf=10, cost=6)]
    plan = _tall(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=[(100, 30), (100, 40)],
                 heights={"1": 290, "2": 150}, widths={"1": 100, "2": 100})
    f = _facings(plan)
    assert f["1"][0] == 2 and f["2"][0] == 1
    assert plan["shelves"][0]["height_cm"] == 30 and plan["shelves"][1]["products"][0]["height_mm"] == 290
    clearance = 20
    for shelf in plan["shelves"]:
        assert all(p["height_mm"] + clearance <= shelf["height_cm"] * 10 for p in shelf["products"])


def test_a_shelf_open_above_takes_any_height(tmp_path):
    cat = [P("1")]
    plan = _tall(tmp_path, cat, _daily({"1": 2}), shelves=[(100, None), (100, 20)],
                 heights={"1": 600}, widths={"1": 100})
    assert _facings(plan)["1"][0] == 1 and plan["shelves"][0]["height_cm"] is None


def test_a_product_taller_than_every_shelf_is_listed_with_its_height(tmp_path):
    cat = [P("1"), P("2")]
    plan = _tall(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=[(100, 30), (100, 35)],
                 heights={"1": 340, "2": 100}, widths={"1": 100, "2": 100})
    assert plan["unplaced"]["too_tall"] == [{"barcode": "1", "height_mm": 340}]
    assert "1" not in _facings(plan) and plan["extra_facings"] == "too_tall"


def test_with_no_height_a_product_is_not_placed_and_no_extra_facing_is_given(tmp_path):
    cat = [P("1"), P("2")]
    plan = _tall(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=[(100, 30)],
                 heights={"2": 100}, widths={"1": 100, "2": 100})
    assert plan["unplaced"]["no_height"] == ["1"] and _facings(plan) == {"2": (1, 1)}
    assert plan["extra_facings"] == "no_height"


def test_a_together_set_stands_on_a_shelf_every_one_of_them_fits_under(tmp_path):
    # Product 1 earns the most and would take eye level (shelf 1, 30 cm high), but its partner is
    # 40 cm tall: together they go on the 45 cm shelf, the one shelf both fit under.
    cat = [P("1", shelf=10, cost=2), P("2", shelf=10, cost=8)]
    rules = """\
      - {together: {barcodes: ["1", "2"]}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}
    """
    plan = _tall(tmp_path, cat, _daily({"1": 2, "2": 2}), shelves=[(100, 30), (100, 45)],
                 heights={"1": 150, "2": 400}, widths={"1": 100, "2": 100}, rules=rules)
    assert _facings(plan)["1"][0] == 2 and _facings(plan)["2"][0] == 2


def test_a_unit_recorded_without_heights_is_planned_as_before(tmp_path):
    cat = [P("1")]
    out = _run(tmp_path, cat, _daily({"1": 2}), widths={"1": 100})
    plan = _plan(out)
    assert "height_cm" not in plan["shelves"][0] and "height_mm" not in plan["shelves"][0]["products"][0]
    assert plan["unplaced"]["no_height"] == [] and plan["unplaced"]["too_tall"] == []
