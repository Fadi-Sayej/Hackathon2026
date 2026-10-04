"""Phase 8 Task 8.2: layout_facts, the recorded shelves and what is missing (F12-S1 FR-190, FR-191,
FR-196 … FR-199; AC-172, AC-173, AC-176, AC-186)."""
from __future__ import annotations

import textwrap
from datetime import date, datetime, timedelta, timezone

from helpers import make_inputs, product

from src.engine import layout_facts
from src.engine.store_layout import load_store_layout

RUN_AT = datetime(2026, 10, 12, 3, 0, tzinfo=timezone.utc)
LAST = date(2026, 10, 11)
STATED = "stated_by: owner\n    stated_on: 2026-10-01\n    recorded_by: team"
SHELF = "{length_cm: 100, measured_by: team, measured_on: 2026-10-01}"

CATALOGUE = [
    product("1001", department="drinks", stock=5.0),      # sells every day
    product("1002", department="drinks", stock=5.0),      # never sells, never delivered
    product("2001", department="cleaning", stock=3.0),    # a department no report itemises
    product("2002", department="cleaning", stock=0.0),
    product("2003", department="cleaning", stock=None),
    product("3001", department="bakery", stock=2.0),      # on no fixture
]


def _daily(barcodes=("1001",)) -> list:
    return [{"barcode": b, "day": (LAST - timedelta(days=back)).isoformat(), "units": 2.0, "receipts": None}
            for back in range(28) for b in barcodes]


def _layout(tmp_path, body: str) -> dict:
    path = tmp_path / "store_layout.yaml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return load_store_layout(path, CATALOGUE)


def _fixture(name, departments, extra=""):
    return (f"  {name}:\n    departments: {departments}\n    chilled: false\n{extra}    {STATED}\n"
            f"    shelves:\n      - {SHELF}\n      - {SHELF}\n")


TWO_FIXTURES = "fixtures:\n" + _fixture("F1", "[drinks]") + _fixture("F2", "[cleaning]") + """\
widths:
  "1001": {width_mm: 80, measured_by: team, measured_on: 2026-10-01}
"""


MONTHLY = [{"barcode": "1001", "month": "2026-07", "units": 60.0}]   # itemises drinks, as F8 reads it (FR-156)


def _run(tmp_path, body=TWO_FIXTURES, daily=None, monthly=None):
    inputs = make_inputs(products=CATALOGUE, sales_daily=daily, sales_monthly=monthly, run_at=RUN_AT,
                         store_layout=_layout(tmp_path, body) if body is not None else None)
    return layout_facts.run(inputs)


def test_no_layout_file_is_no_store_layout(tmp_path):
    # AC-172, FR-196.
    out = _run(tmp_path, body=None)
    assert (out.status, out.unavailable_reason) == ("unavailable", "no_store_layout")


def test_it_needs_no_sales(tmp_path):
    # AC-173, D-30: available with no daily report at all, and every recorded fixture is shown.
    out = _run(tmp_path, daily=None)
    assert out.status == "available"
    assert set(out.extras["fixtures"]) == {"F1", "F2"}
    assert out.extras["fixtures"]["F1"]["stated_on"] == "2026-10-01"
    assert out.extras["evidence_window"] is None


def test_every_fixture_rejected_is_layout_all_rejected_and_names_them(tmp_path):
    out = _run(tmp_path, body="fixtures:\n" + _fixture("F1", "[nowhere]"))
    assert (out.status, out.unavailable_reason) == ("unavailable", "layout_all_rejected")
    assert [r["key"] for r in out.extras["rejected"]] == ["F1"]


def test_without_a_window_products_without_a_width_count_the_catalogue(tmp_path):
    # FR-190: the reports itemise drinks, but there is no window, so whether he stocks its
    # products is not known yet. Every catalogue product is counted, and none is called unstocked.
    out = _run(tmp_path, daily=None, monthly=MONTHLY)
    assert out.extras["without_width_counts"] == "catalogue"
    assert out.extras["without_width"]["F1"] == ["1002"]
    assert out.extras["unplanned"]["F1"]["waiting_for_window"] == ["1001", "1002"]
    assert out.extras["unplanned"]["F1"]["no_sale_in_window"] == []


def test_with_a_window_they_count_only_the_planned_products(tmp_path):
    # FR-190 and FR-198: 1002 is not stocked, so it is listed as such and not as width-less.
    out = _run(tmp_path, daily=_daily())
    assert out.extras["without_width_counts"] == "planned"
    assert out.extras["without_width"]["F1"] == []
    assert out.extras["unplanned"]["F1"]["no_sale_in_window"] == ["1002"]
    assert out.extras["evidence_window"]["last_day"] == LAST.isoformat()


def test_a_department_no_report_itemises_is_judged_by_its_count(tmp_path):
    # AC-186, FR-197: above zero is stocked, zero or below is listed, unknown is "stock unknown".
    out = _run(tmp_path, daily=_daily())
    unplanned = out.extras["unplanned"]["F2"]
    assert unplanned["count_zero_or_below"] == ["2002"] and unplanned["stock_unknown"] == ["2003"]
    assert out.extras["without_width"]["F2"] == ["2001"]


def test_departments_on_no_fixture_are_listed_not_errors(tmp_path):
    out = _run(tmp_path)
    assert out.extras["departments_on_no_fixture"] == ["bakery"]
    assert out.counts["departments_on_no_fixture"] == 1


def test_a_keep_on_rule_plans_an_unstocked_product_all_the_same(tmp_path):
    # FR-198: planned with one facing, so it is not in any "not planned" list.
    body = TWO_FIXTURES + """\
rules:
  - {keep_on: {barcode: "1002", fixture: F1}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}
  - {keep_off: {barcode: "2001", fixture: F2}, stated_by: owner, stated_on: 2026-10-01, recorded_by: team}
"""
    out = _run(tmp_path, body=body, daily=_daily())
    assert out.extras["unplanned"]["F1"]["no_sale_in_window"] == []
    assert out.extras["without_width"]["F1"] == ["1002"]
    assert out.extras["unplanned"]["F2"]["kept_off"] == ["2001"]
    assert [r["kind"] for r in out.extras["fixtures"]["F2"]["rules"]] == ["keep_off"]


def test_every_catalogue_product_of_a_fixture_is_accounted_for(tmp_path):
    # INV-088's layout half: planned or listed with its reason, never silently dropped.
    out = _run(tmp_path, daily=_daily())
    for name, dept in (("F1", "drinks"), ("F2", "cleaning")):
        listed = {b for bs in out.extras["unplanned"][name].values() for b in bs}
        catalogue = {p["barcode"] for p in CATALOGUE if p["department"] == dept}
        planned = catalogue - listed
        assert planned and listed <= catalogue


def test_it_carries_no_value_and_no_entry(tmp_path):
    out = _run(tmp_path, daily=_daily())
    assert out.entries == [] and "value" not in str(out.extras).lower()
