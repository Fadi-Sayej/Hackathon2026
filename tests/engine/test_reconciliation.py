# tests/engine/test_reconciliation.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product, summary, window_of
from src.engine.model import entry_id
from src.engine.reconciliation import run, run_hygiene

W = window_of(["2026-01", "2026-02"])


def test_ac_020_detection_flags_negative_implied_opening_and_orders_by_gap_ratio():
    inputs = make_inputs(
        products=[product("1", stock=200.0), product("2", stock=-716.0), product("3", stock=5.0), product("4", stock=-3.0)],
        sales_summary=[summary("1", units=5, receipts=100),            # 200-100+5  = implied 105 → consistent
                       summary("2", units=663, receipts=62),           # -716-62+663 = implied -115 → flagged, ratio 1.85
                       summary("3", units=50, receipts=10),            # 5-10+50    = implied 45 → consistent
                       summary("4", units=0, receipts=0)],             # no receipts → never flagged
        window=W)
    out = run(inputs)
    assert [e.barcode for e in out.entries] == ["2"]
    assert out.entries[0].ordering_key == {"name": "gap_ratio", "value": round(115 / 62, 4)}
    assert out.counts["flagged"] == 1


def test_ac_020_ordering_is_by_gap_ratio_descending():
    inputs = make_inputs(
        products=[product("a", stock=0.0), product("b", stock=0.0)],
        # a: 0-20+10 = -10, missing 10, ratio 0.50 · b: 0-200+10 = -190, missing 190, ratio 0.95
        sales_summary=[summary("a", units=10, receipts=20), summary("b", units=10, receipts=200)], window=W)
    assert [e.barcode for e in run(inputs).entries] == ["b", "a"]


def test_ac_021_ac_022_no_money_anywhere():
    # must actually be flagged for there to be an entry to check: -716-62+663 = -115
    inputs = make_inputs(products=[product("2", stock=-716.0, cost=3.15)],
                         sales_summary=[summary("2", units=663, receipts=62)], window=W)
    out = run(inputs)
    assert all(e.value is None for e in out.entries)
    assert all(isinstance(v, (int, type(None))) for v in out.counts.values())
    assert "cost_price" not in out.entries[0].evidence
    assert all(e.value is None for e in run_hygiene(inputs).entries)


def test_ac_024_evidence_carries_the_three_quantities():
    inputs = make_inputs(products=[product("2", stock=-716.0)],
                         sales_summary=[summary("2", units=663, receipts=62, months=2)], window=W)
    e = run(inputs).entries[0]
    assert e.evidence["recorded_stock"] == -716.0 and e.evidence["receipts"] == 62 and e.evidence["units_sold"] == 663
    assert e.evidence["unaccounted"] == 115 and e.evidence["window_id"] == "2026-01..2026-02"
    assert e.action == "count_product"


def test_ac_025_hygiene_records_without_money_and_with_reasons():
    inputs = make_inputs(products=[product("9", stock=-1.0, shelf=2.0), product(None, name="אייס", shelf=1.0),
                                   product("8", stock=0.0, shelf=None)], sales_summary=[], window=W)
    out = run_hygiene(inputs)
    hyg = {(e.barcode, e.evidence["reason"]) for e in out.entries}
    assert hyg == {("9", "negative_stock"), (None, "no_identifier"), ("8", "absent_price")}
    assert out.counts == {"negative_stock": 1, "no_identifier": 1, "absent_price": 1}
    assert all(e.action == "fix_record" for e in out.entries)


def test_spec_002_s11_detection_unavailable_leaves_hygiene_untouched():
    """The rule the split exists for (AC-107). The inventory CSV always arrives; the seven
    monthly reports may not. Detection cannot close its arithmetic without receipts, and
    says so; a negative stock figure is still wrong on its own evidence."""
    inputs = make_inputs(products=[product("9", stock=-1.0, shelf=2.0)], sales_summary=None, window=None)
    detection, hygiene = run(inputs), run_hygiene(inputs)
    assert detection.status == "unavailable" and detection.unavailable_reason == "no_sales_evidence"
    assert detection.entries == []
    assert hygiene.status == "available" and hygiene.counts["negative_stock"] == 1
    assert len(hygiene.entries) == 1


def test_withdrawn_products_are_excluded_from_hygiene_counts():
    inputs = make_inputs(products=[product("8", stock=0.0, shelf=None)], sales_summary=[], window=W, withdrawn={"8"})
    assert run_hygiene(inputs).counts["absent_price"] == 0


def test_entry_ids_are_keyed_on_the_signal_family_not_the_capability():
    """ADR-009. These ids key the owner's outcomes in Firestore; hygiene moving out of
    reconciliation must not have changed a single one of them."""
    inputs = make_inputs(products=[product("9", stock=-1.0, shelf=2.0)], sales_summary=[], window=W)
    e = run_hygiene(inputs).entries[0]
    assert e.signal_family == "hygiene.negative_stock"
    assert e.id == entry_id("hygiene.negative_stock", "9")


def test_no_pos_data_makes_both_unavailable():
    assert run(make_inputs(products=None)).status == "unavailable"
    assert run_hygiene(make_inputs(products=None)).unavailable_reason == "no_pos_data"


def test_a_missing_stock_table_makes_hygiene_unavailable_not_zero():
    """Without the inventory table every product shapes with recorded_stock None, and a
    count of negative-stock records would come out 0. Zero is a finding; this is an absence
    (ARCH-DRIVER-002, INV-057). `inventory` is in hygiene's requires so the run says so."""
    out = run_hygiene(make_inputs(products=[product("9", shelf=2.0)], inventory=None))
    assert out.status == "unavailable" and out.unavailable_reason == "no_inventory_data"
    assert out.counts == {}
