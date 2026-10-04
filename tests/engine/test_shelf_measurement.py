"""Phase 8 Task 8.5: shelf_measurement, and the plan using it (F12-S1 FR-202 … FR-209; AC-191 … AC-198;
SCN-170 … SCN-174). Proven on the planogram world, tests/fixtures/shelf_signals/build.py."""
from __future__ import annotations

import copy
import importlib.util
import math
from datetime import date, timedelta
from pathlib import Path

import pytest
from helpers import make_inputs

# Loaded under its own name: tests/fixtures/order_signals/build.py is imported as `build` too,
# and Python would hand whichever came first to both.
_spec = importlib.util.spec_from_file_location(
    "shelf_world", Path(__file__).resolve().parents[1] / "fixtures" / "shelf_signals" / "build.py")
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

from src.engine import shelf_measurement as sm  # noqa: E402
from src.engine import shelf_plan  # noqa: E402
from src.engine.model import entry_id  # noqa: E402
from src.engine.order_evidence import evidence_window  # noqa: E402
from src.engine.policy import load_policy  # noqa: E402
from src.engine.publish import check_f12_capability  # noqa: E402
from src.owner_state.model import OwnerState  # noqa: E402

_WORLDS: dict = {}


def _world(variant):
    if variant not in _WORLDS:
        _WORLDS[variant] = W.world(variant)
    return _WORLDS[variant]


def _inputs(w, *, outcomes=None, owner=None, sales=None):
    if owner is None:
        owner = w["owner"] if outcomes is None else OwnerState.from_dict(
            {"status": "available", "pulled_at": "t", "outcomes": outcomes})
    return make_inputs(products=w["products"], sales_daily=sales if sales is not None else w["sales_daily"],
                       store_layout=w["store_layout"], owner=owner, run_at=w["run_at"])


def _arrangement(fixture: str, arranged_on: date, placements: dict) -> tuple:
    plan_date = arranged_on - timedelta(days=2)
    eid = entry_id("shelf.plan", None, f"{fixture}|{plan_date.isoformat()}")
    return eid, {"status": "acted", "reason": None, "at": 0, "snapshot": {
        "signal_family": "shelf.plan", "capability": "shelf_plan", "barcode": None, "characterisation": "shelf_plan",
        "fixture": fixture, "plan_date": plan_date.isoformat(),
        "plan_window": {"first_day": (plan_date - timedelta(days=28)).isoformat(),
                        "last_day": (plan_date - timedelta(days=1)).isoformat()},
        "arranged_on": arranged_on.isoformat(), "placements": placements}}


def _placements(fixture: str) -> dict:
    return {W.barcode(fixture, n): {"shelf": 1, "facings": 2, "eye_level": True} for n in range(1, 7)}


@pytest.fixture(scope="module")
def known():
    w = _world("known")
    return w, sm.measure(_inputs(w))


# ── The windows (FR-202, INV-095, AC-191, AC-198, SCN-170, SCN-174) ───────────

def test_the_before_window_ends_where_the_plans_window_begins(known):
    _, m = known
    for a in m["arrangements"]:
        assert a["before_window"]["last_day"] < a["plan_window"]["first_day"]      # INV-095
        assert date.fromisoformat(a["plan_window"]["first_day"]) - date.fromisoformat(a["before_window"]["last_day"]) \
            == timedelta(days=1)
        assert a["after_window"]["first_day"] > a["arranged_on"]


def test_an_arrangement_still_in_its_after_window_waits_and_publishes_no_change(known):
    # SCN-170: arranged 10 report days ago.
    w, _ = known
    outcomes = copy.deepcopy(w["owner"].outcomes)
    eid, rec = _arrangement("F14", W.LAST - timedelta(days=9), _placements("F14"))
    outcomes[eid] = rec
    m = sm.measure(_inputs(w, outcomes=outcomes))
    late = next(a for a in m["arrangements"] if a["entry_id"] == eid)
    assert late["status"] == "waiting" and late["products"] == []
    assert late["waiting"]["report_days_so_far"] == 9 and late["waiting"]["days_left"] == 19


def test_too_little_history_and_a_second_arrangement_are_not_measurable(known):
    # AC-198, SCN-174.
    w, _ = known
    outcomes = copy.deepcopy(w["owner"].outcomes)
    early_id, early = _arrangement("F13", w["first_day"] + timedelta(days=30), _placements("F13"))
    outcomes[early_id] = early
    first_f01 = next(a for a in W.SHAPES["known"][1][:1])
    again_id, again = _arrangement("F01", w["first_day"] + timedelta(days=first_f01 + 10), _placements("F01"))
    outcomes[again_id] = again
    m = sm.measure(_inputs(w, outcomes=outcomes))
    by_id = {a["entry_id"]: a for a in m["arrangements"]}
    assert (by_id[early_id]["status"], by_id[early_id]["reason"]) == ("not_measurable", "history_too_short")
    assert by_id[again_id]["reason"] == "rearranged_again"
    f01 = [a for a in m["arrangements"] if a["fixture"] == "F01"]
    assert all(a["reason"] == "rearranged_again" for a in f01)


def test_every_fixture_arranged_at_once_leaves_no_yardstick(known):
    # SCN-171.
    w, _ = known
    day = w["first_day"] + timedelta(days=150)
    outcomes = dict(_arrangement(f, day, _placements(f)) for f in W.FIXTURES)
    m = sm.measure(_inputs(w, outcomes=outcomes))
    assert {a["reason"] for a in m["arrangements"]} == {"no_unchanged_fixture"}
    assert m["elasticity"]["verdict"] == "not_measurable"


# ── Who is measured, and the net change (FR-203, FR-204, AC-192, AC-193) ──────

def test_each_net_change_is_after_over_before_over_the_window_term(known):
    _, m = known
    a = m["arrangements"][0]
    change = a["comparison"]["change"]
    for p in a["products"]:
        assert p["net_change"] == pytest.approx(p["after_daily_mean"] / p["before_daily_mean"] / change)


def test_the_interval_holds_the_elasticity_the_world_was_built_with(known):
    # AC-192.
    _, m = known
    lo, hi = m["elasticity"]["interval"]
    assert lo <= W.TRUE_ELASTICITY <= hi
    assert m["elasticity"]["level"] == 0.95 and m["elasticity"]["fixtures"] == 8


def test_eligibility_is_decided_from_the_plans_window_alone(known):
    # AC-193: one product sold nothing in its plan's window and is left out. Another sold there
    # and nothing after, and stays in as a fall.
    w, _ = known
    first_on = w["first_day"] + timedelta(days=W.SHAPES["known"][1][0])
    plan_first, plan_last = first_on - timedelta(days=30), first_on - timedelta(days=3)
    gone, fell = W.barcode("F01", 1), W.barcode("F01", 2)
    sales = []
    for r in w["sales_daily"]:
        d = date.fromisoformat(r["day"])
        if r["barcode"] == gone and plan_first <= d <= plan_last:
            r = {**r, "units": 0.0}
        if r["barcode"] == fell and d > first_on:
            r = {**r, "units": 0.0}
        sales.append(r)
    m = sm.measure(_inputs(w, sales=sales))
    f01 = next(a for a in m["arrangements"] if a["fixture"] == "F01")
    assert f01["left_out"] == [{"barcode": gone, "reason": "no_sale_in_plan_window"}]
    p = next(p for p in f01["products"] if p["barcode"] == fell)
    assert p["after_daily_mean"] == 0.0 and p["net_change"] == 0.0


# ── The verdict, the placebo and the plan (FR-205, FR-206, FR-209, AC-194, AC-197) ──

def test_a_measured_value_in_range_with_a_passed_placebo_replaces_the_research_value(known):
    w, m = known
    assert m["elasticity"]["verdict"] == "measured" and 0 < m["elasticity"]["estimate"] < 1
    assert m["placebo"]["status"] == "passed"
    out = shelf_plan.run(_inputs(w))
    assert out.extras["elasticity"] == {"value": m["elasticity"]["estimate"], "source": "his_store",
                                        "why": "his_own_measured"}


@pytest.mark.parametrize("variant, failed_on", [("drifting", "arranged"), ("rising", "log_facings")])
def test_a_drift_that_was_there_already_fails_the_placebo_and_keeps_017(variant, failed_on):
    w = _world(variant)
    m = sm.measure(_inputs(w))
    assert m["placebo"]["status"] == "failed" and failed_on in m["placebo"]["failed_on"]
    assert (m["elasticity"]["verdict"], m["elasticity"]["why_not_measurable"]) == ("not_measurable", "placebo_failed")
    assert m["plan_uses"] == {"value": 0.17, "source": "research", "why": "placebo_failed"}


def test_without_the_history_for_a_placebo_it_is_not_run_and_017_stays():
    w = _world("short")
    m = sm.measure(_inputs(w))
    assert m["placebo"]["status"] == "not_run"
    assert m["plan_uses"] == {"value": 0.17, "source": "research", "why": "placebo_not_run"}


def test_the_placebo_windows_are_as_far_apart_as_the_measured_ones(known):
    _, m = known
    a = m["arrangements"][0]
    distance = date.fromisoformat(a["after_window"]["first_day"]) - date.fromisoformat(a["before_window"]["first_day"])
    assert distance.days > 28        # the measured windows are a plan's window apart, not adjacent


# ── Unavailable, and never silent (FR-208, AC-196, SCN-173) ──────────────────

def test_owner_state_not_pulled_is_said_and_the_plan_says_why_it_uses_017(known):
    w, _ = known
    inputs = _inputs(w, owner=OwnerState.unavailable("no_credentials"))
    out = sm.run(inputs)
    assert (out.status, out.unavailable_reason) == ("unavailable", "owner_state_unavailable")
    assert shelf_plan.run(inputs).extras["elasticity"] == {
        "value": 0.17, "source": "research", "why": "measurement_unavailable",
        "measurement_reason": "owner_state_unavailable"}


def test_no_arrangement_recorded_is_its_own_reason(known):
    w, _ = known
    out = sm.run(_inputs(w, outcomes={}))
    assert (out.status, out.unavailable_reason) == ("unavailable", "no_arrangement_recorded")


# ── Units only, never extended (FR-207, INV-087, INV-093, AC-195) ────────────

def test_it_publishes_units_only_and_no_fixture_total(known):
    w, _ = known
    cap = sm.run(_inputs(w)).to_dict()
    check_f12_capability("shelf_measurement", cap)
    text = str(cap).lower()
    assert "total" not in text and "₪" not in text
    assert cap["thresholds"]["window_days"] == load_policy().order_window_days


def test_print_mode_reproduces_the_interval(known):
    # NFR-073: the bootstrap's seed is policy, so the same inputs give the same interval.
    w, m = known
    again = sm.measure(_inputs(w))
    assert again["elasticity"]["interval"] == m["elasticity"]["interval"]


def test_the_plan_s_window_is_f8_s_own(known):
    w, _ = known
    out = shelf_plan.run(_inputs(w))
    window = evidence_window({r["day"] for r in w["sales_daily"]}, load_policy(), w["run_at"])
    assert out.extras["evidence_window"]["last_day"] == window.last_day
    assert not math.isnan(out.counts["placed"])
