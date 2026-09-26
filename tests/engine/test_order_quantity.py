# tests/engine/test_order_quantity.py
"""Phase 5 Task 5.8: the `order_quantity` capability (F8-S1 FR-143 … FR-163, ADR-034)."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from helpers import make_inputs, product
from src.engine import market_boost as mb
from src.engine import order_quantity as oq
from src.engine.model import entry_id
from src.engine.registry import CAPABILITIES, INPUT_REASONS

THU = date(2026, 10, 29)                                   # a Thursday
RUN_AT = datetime(2026, 10, 29, 3, tzinfo=timezone.utc)
LAST = THU - timedelta(days=1)                             # the latest report day
DAYS = [(LAST - timedelta(days=i)).isoformat() for i in range(28)]
DEPT, OTHER, SILENT = "משקאות", "מאפים", "סיגריות"
PROVENANCE = {"stated_by": "owner", "stated_on": "2026-10-01", "recorded_by": "team"}


def facts(schedule=None, shelf=None, dept=DEPT, **more):
    entry = {"order_schedule": schedule if schedule is not None else {"form": "weekdays", "weekdays": ["sun"]},
             "shelf_life": shelf if shelf is not None else {"days": 90}, **PROVENANCE}
    return {"facts": {dept: entry, **more}, "rejected": []}


def daily(barcode, units=2.0, receipts=1.0, days=DAYS):
    return [{"barcode": barcode, "day": d, "units": units, "receipts": receipts} for d in days]


def inputs(*, products=None, rows=None, store_facts=None, monthly=None, run_at=RUN_AT, count_date="2026-06-06",
           running=None, picks=None, owner=None):
    made = make_inputs(
        products=products if products is not None else [product("a", name="מים", department=DEPT, stock=20.0, shelf=4.0)],
        sales_daily=rows if rows is not None else daily("a"),
        sales_monthly=monthly if monthly is not None else [],
        store_facts=store_facts if store_facts is not None else facts(),
        running_out=running, boost_picks=picks, run_at=run_at, owner=owner)
    made.vintages["pos"] = {"file": "f", "as_of": count_date, "as_of_source": "declared"}
    return made


def out(**kw):
    return oq.run(inputs(**kw)).to_dict()


# ── Registration and the input-level reasons ─────────────────────────────────

def test_it_is_registered_carrying_no_value():
    spec = CAPABILITIES["order_quantity"]
    # The plan named the two F8 inputs; the catalogue is the third, or withholding it would
    # take the capability down undeclared (rule 12).
    assert spec.requires == ("products", "sales_daily", "store_facts")
    assert spec.value_policy == "none" and spec.admitted is False and spec.published_from
    assert INPUT_REASONS["sales_daily"] == "no_daily_sales"
    assert INPUT_REASONS["store_facts"] == "no_store_facts"


def test_monthly_reports_only_is_unavailable_with_no_daily_sales():
    """SCN-132: the seven monthly reports supply no quantity at all (INV-070)."""
    got = oq.run(make_inputs(products=[product("a", department=DEPT)], sales_monthly=[{"barcode": "a", "month": "2026-07", "units": 60.0, "receipts": 5.0}],
                             sales_daily=None, store_facts=facts(), run_at=RUN_AT)).to_dict()
    assert (got["status"], got["unavailable_reason"]) == ("unavailable", "no_daily_sales")


def test_no_store_facts_file_is_unavailable():
    got = oq.run(make_inputs(products=[product("a", department=DEPT)], sales_daily=daily("a"),
                             store_facts=None, run_at=RUN_AT)).to_dict()
    assert got["unavailable_reason"] == "no_store_facts"


def test_daily_reports_that_stopped_arriving_are_stale():
    got = out(run_at=RUN_AT + timedelta(days=8))
    assert (got["status"], got["unavailable_reason"]) == ("unavailable", "stale_daily_sales")


# ── No quantity, and why, per department (FR-155, FR-156) ────────────────────

def _reasons(got, dept=DEPT):
    return got["departments"][dept]["reasons"]


def test_no_window_is_said_per_department():
    got = out(rows=daily("a", days=DAYS[:20]))
    assert got["status"] == "available" and got["entries"] == []
    assert _reasons(got) == {"no_window": 1}


def test_a_department_with_no_schedule_is_named():
    """SCN-140."""
    got = out(store_facts={"facts": {}, "rejected": []})
    assert got["entries"] == [] and _reasons(got) == {"no_order_schedule": 1}


def test_no_fixed_days_is_named():
    got = out(store_facts=facts(schedule={"form": "no_fixed_days"}))
    assert _reasons(got) == {"no_fixed_days": 1}


def test_a_department_with_no_shelf_life_is_named():
    """SCN-146."""
    only_schedule = {"facts": {DEPT: {"order_schedule": {"form": "weekdays", "weekdays": ["sun"]},
                                      "shelf_life": None, **PROVENANCE}}, "rejected": []}
    assert _reasons(out(store_facts=only_schedule)) == {"no_shelf_life": 1}


def test_a_department_the_evidence_does_not_itemise_is_named():
    """SCN-142 / FR-156: read over ANY evidence, the monthly reports included."""
    prods = [product("a", department=DEPT), product("s", department=SILENT)]
    got = out(products=prods, store_facts=facts(**{SILENT: {**facts()["facts"][DEPT]}}))
    assert _reasons(got, SILENT) == {"not_itemised": 1}
    # A monthly row is enough to itemise a department, though it supplies no quantity.
    got = out(products=prods, monthly=[{"barcode": "s", "month": "2026-07", "units": 3.0, "receipts": 1.0}],
              store_facts=facts(**{SILENT: {**facts()["facts"][DEPT]}}))
    assert _reasons(got, SILENT) == {"not_moving": 1}


def test_not_moving_is_counted_per_department():
    got = out(rows=daily("a", days=DAYS[7:]) + daily("b", days=DAYS[:1]),
              products=[product("a", department=DEPT), product("b", department=DEPT)])
    assert _reasons(got) == {"not_moving": 2}


def test_below_one_per_cycle_is_named():
    """SCN-149: every day, about two a week."""
    every_day = {"form": "weekdays", "weekdays": ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]}
    rows = [r for i, r in enumerate(daily("a", units=1.0)) if i % 3 == 0]
    got = out(rows=rows + daily("x", units=0.0), store_facts=facts(schedule=every_day),
              products=[product("a", department=DEPT)])
    assert _reasons(got) == {"below_one_per_cycle": 1}


def test_a_shelf_life_under_a_day_is_named():
    """SCN-139."""
    assert _reasons(out(store_facts=facts(shelf={"days": 0}))) == {"shelf_life_under_a_day": 1}


# ── A suggestion (FR-146 … FR-154) ───────────────────────────────────────────

def test_a_gross_suggestion_for_sunday_says_why_the_count_was_not_used():
    """SCN-133: Thursday run, Sunday order, a count from 6 June."""
    got = out()
    (entry,) = got["entries"]
    assert entry["signal_family"] == "order.suggestion" and entry["action"] == "place_order"
    assert entry["id"] == entry_id("order.suggestion", "a", "2026-11-01")
    assert entry["value"] is None
    ev = entry["evidence"]
    assert ev["order_day"] == "2026-11-01" and ev["cycle"] == {"first_day": "2026-11-01", "last_day": "2026-11-07", "days": 7}
    assert ev["daily_mean"] == 2.0 and ev["adjusted_daily_mean"] == 2.0 and ev["expected_sales"] == 14.0
    assert ev["weekly_units"] == [14.0, 14.0, 14.0, 14.0]
    assert ev["kind"] == "gross" and ev["quantity"] == 14
    assert ev["count"] == {"recorded_stock": 20.0, "as_of": "2026-06-06", "used": False,
                           "not_used_because": "count_too_old", "flags": []}
    assert ev["shelf_life"] == {"days": 90, "stated_on": "2026-10-01"} and ev["capped"] is False
    assert ev["schedule"] == {"form": "weekdays", "weekdays": ["sun"], "stated_on": "2026-10-01"}
    assert ev["schedule_changed"] is False


def test_a_net_suggestion_deducts_the_stock_at_the_order_day():
    """SCN-134: a count on Monday, three report days since, Thursday run for Sunday."""
    got = out(count_date="2026-10-26")
    ev = got["entries"][0]["evidence"]
    assert ev["count"]["used"] is True
    assert (ev["since_count"]["deliveries"], ev["since_count"]["sales"]) == (3.0, 6.0)
    assert ev["stock_now"] == 17.0 and ev["stock_at_order_day"] == 11.0      # Thu–Sat at 2 a day
    assert ev["kind"] == "net" and ev["quantity"] == 3                       # 14 − 11


def test_a_flagged_count_is_not_used_and_the_flag_is_named():
    """SCN-135: hygiene flags a product with no shelf price."""
    got = out(count_date="2026-10-26",
              products=[product("a", name="מים", department=DEPT, stock=20.0, shelf=None)])
    ev = got["entries"][0]["evidence"]
    assert ev["count"]["used"] is False and ev["count"]["not_used_because"] == "count_flagged"
    assert ev["count"]["flags"] == ["hygiene.absent_price"]
    assert ev["kind"] == "gross"


def test_a_stock_that_covers_the_need_is_counted_not_suggested():
    """FR-150: not a zero quantity; the department says how many are covered."""
    got = out(count_date="2026-10-26",
              products=[product("a", department=DEPT, stock=60.0, shelf=4.0)])
    assert got["entries"] == []
    assert got["departments"][DEPT]["covered_by_stock"] == 1
    assert got["counts"]["covered_by_stock"] == 1


def test_the_same_order_day_is_the_same_entry_on_friday_and_saturday():
    """SCN-145: an approval holds; on Sunday night the next Sunday is a new entry."""
    fri, sat, mon = (RUN_AT + timedelta(days=d) for d in (1, 2, 4))
    ids = [out(run_at=r)["entries"][0]["id"] for r in (RUN_AT, fri, sat)]
    assert len(set(ids)) == 1
    assert out(run_at=mon)["entries"][0]["id"] != ids[0]


def test_a_pending_approval_for_another_day_marks_the_schedule_changed():
    """ADR-034 Decision 4: an approval never carries to a new day, and the engine says so."""
    from src.owner_state.model import OwnerState
    old_day = "2026-10-31"                                           # a Saturday, since changed
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t", "outcomes": {
        entry_id("order.suggestion", "a", old_day): {"status": "acted", "at": 1, "snapshot": {
            "signal_family": "order.suggestion", "barcode": "a", "order_day": old_day}}}})
    assert out(owner=owner)["entries"][0]["evidence"]["schedule_changed"] is True
    past = OwnerState.from_dict({"status": "available", "pulled_at": "t", "outcomes": {
        entry_id("order.suggestion", "a", "2026-10-25"): {"status": "acted", "at": 1, "snapshot": {
            "signal_family": "order.suggestion", "barcode": "a", "order_day": "2026-10-25"}}}})
    assert out(owner=past)["entries"][0]["evidence"]["schedule_changed"] is False


# ── The boost (SCN-136, INV-074) ─────────────────────────────────────────────

def _signal():
    return {"on_day": LAST.isoformat(), "stores": ["s1"], "excluded": [],
            "products": {"a": {"stores_out": ["s1"], "days_absent": {"s1": 3}}}}


def _sealed(tmp_path, pct=10):
    class Fake:
        def __call__(self, url, headers, body, timeout):
            return 200, json.dumps({"content": [{"type": "text", "text": json.dumps(
                {"boost_pct": pct, "reason": "نفدت عند الجيران"})}]}).encode()
    base = inputs(running=_signal(), run_at=datetime(2026, 10, 28, 3, tzinfo=timezone.utc))
    mb.live_step(base, snapshots_root=tmp_path, key="k", transport=Fake(), now=base.run_at)
    return mb.read_picks(tmp_path, LAST.isoformat())


def test_an_accepted_pick_raises_the_daily_mean_once():
    """SCN-136: the adjusted daily mean is 10% higher, once, and every expectation uses it."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        picks = _sealed(Path(d))
    got = out(running=_signal(), picks=picks, run_at=datetime(2026, 10, 28, 3, tzinfo=timezone.utc))
    ev = got["entries"][0]["evidence"]
    assert ev["boost"]["applied"] is True and ev["boost"]["pct"] == 10
    assert ev["boost"]["model"] == "claude-sonnet-5" and ev["boost"]["label"] == "model_estimate"
    assert ev["daily_mean"] == 2.0 and ev["adjusted_daily_mean"] == pytest.approx(2.2)
    assert ev["expected_sales"] == pytest.approx(2.2 * ev["cycle"]["days"])


def test_without_picks_the_suggestion_is_unboosted_and_says_why():
    got = out(running=_signal(), picks=None, run_at=datetime(2026, 10, 28, 3, tzinfo=timezone.utc))
    boost = got["entries"][0]["evidence"]["boost"]
    assert boost["applied"] is False and boost["not_applied_because"] == "no_boost_key"


def test_without_a_market_signal_the_suggestion_says_the_signal_was_unavailable():
    """SCN-137 / FR-148."""
    boost = out(running=None)["entries"][0]["evidence"]["boost"]
    assert boost["applied"] is False and boost["not_applied_because"] == "market_signal_thin"


def test_a_product_the_market_is_not_running_out_of_is_not_boosted_and_says_so():
    other = {**_signal(), "products": {}}
    boost = out(running=other, run_at=datetime(2026, 10, 28, 3, tzinfo=timezone.utc))["entries"][0]["evidence"]["boost"]
    assert boost["not_applied_because"] == "market_not_running_out"


# ── No money, anywhere (INV-069) ─────────────────────────────────────────────

MONEY = re.compile(r"price|cost|revenue|margin|shekel|₪|money|amount", re.I)


def _keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _keys(v)


def test_no_entry_carries_a_value_or_a_money_field():
    got = out(count_date="2026-10-26")
    assert got["entries"]
    for entry in got["entries"]:
        assert entry["value"] is None
        assert not [k for k in _keys(entry["evidence"]) if MONEY.search(k)]


# ── The one derivation of a flag (plan item 3) ───────────────────────────────

def test_flagged_barcodes_are_exactly_what_reconciliation_and_hygiene_publish():
    from src.engine import reconciliation
    made = inputs(products=[product("a", department=DEPT, stock=-3.0, shelf=4.0),
                            product("b", department=DEPT, stock=2.0, shelf=None)])
    flags = reconciliation.flagged_barcodes(made)
    published = {e.barcode for e in reconciliation.run_hygiene(made).entries}
    assert set(flags) == published == {"a", "b"}
    assert flags["a"] == ["hygiene.negative_stock"] and flags["b"] == ["hygiene.absent_price"]


# ── Across the boundary: a print-mode re-run reproduces every figure (AC-140, AC-149, NFR-067) ─

def test_a_print_mode_rerun_reproduces_every_quantity_and_fact(tmp_path, monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq
    import src.engine.run as run_mod
    from src.internal_pos.sales_daily_importer import import_sales_daily

    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    silver = tmp_path / "silver"; silver.mkdir()
    prod = [{"barcode": b, "product_name": n, "category": DEPT, "selling_price": 4.0, "wolt_price": 0.0,
             "cost_price": 1.0, "_source_file": "inv.csv", "_as_of": "2026-10-26", "_as_of_source": "declared"}
            for b, n in (("7290001", "מים"), ("7290002", "קולה"))]
    inv = [{"barcode": r["barcode"], "product_name": r["product_name"], "current_stock": 9.0,
            "_source_file": "inv.csv", "_as_of": "2026-10-26", "_as_of_source": "declared"} for r in prod]
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "yomyom_inventory.parquet")
    reports = tmp_path / "daily"; reports.mkdir()
    header = "תאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n"
    for i, d in enumerate(DAYS):
        (reports / f"דוח מכירות יום {d}.csv").write_text(
            "﻿" + header + f"מים,7290001,{2 + i % 3},1,4,2,1,1,0,1,\nקולה,7290002,1,1,4,2,0,1,0,1,\n", encoding="utf-8")
    import_sales_daily(reports, silver_dir=silver)
    stated = tmp_path / "store_facts.yaml"
    stated.write_text(f"departments:\n  {DEPT}:\n    order_schedule: {{weekdays: [sun, wed]}}\n    shelf_life_days: 5\n"
                      "    stated_by: owner\n    stated_on: 2026-10-01\n    recorded_by: team\n", encoding="utf-8")
    world = dict(silver_dir=silver, daily_sales_dir=reports, store_facts_path=stated, sales_dir=tmp_path / "nomonthly",
                 signals_dir=tmp_path / "nosig", matches_path=tmp_path / "nomatch.parquet",
                 snapshots_root=tmp_path / "nosnap")
    first = run_mod.run_engine(mode="print", now=RUN_AT, **world)["artefact"]
    again = run_mod.run_engine(mode="print", now=RUN_AT, **world)["artefact"]
    cap = first["capabilities"]["order_quantity"]
    assert cap["status"] == "available"
    # 7290001 sells two to four a day: a suggestion. 7290002 sells one a day, and the count
    # of 9 on Monday (9 − 3 sold, nothing delivered, less Thursday to Saturday) leaves 3 at
    # Sunday against a three-day cycle's 3: covered by stock, counted, not suggested (FR-150).
    assert [e["barcode"] for e in cap["entries"]] == ["7290001"]
    assert cap["departments"][DEPT]["covered_by_stock"] == 1
    assert again["capabilities"]["order_quantity"] == cap
    assert again["inputs_digest"] == first["inputs_digest"]
    # And every published quantity recomputes from its published facts alone.
    for entry in cap["entries"]:
        ev = entry["evidence"]
        assert ev["expected_sales"] == pytest.approx(ev["adjusted_daily_mean"] * ev["cycle"]["days"])
        need = ev["expected_sales"] - (ev["stock_at_order_day"] or 0.0) if ev["kind"] == "net" else ev["expected_sales"]
        cap_units = int(ev["adjusted_daily_mean"] * ev["shelf_life"]["days"] - (ev["stock_at_order_day"] or 0.0))
        assert ev["quantity"] == min(int(need + 0.5), cap_units)
