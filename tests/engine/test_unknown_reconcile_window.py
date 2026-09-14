# tests/engine/test_unknown_reconcile_window.py
"""An unknown stock-count date must not become "use every month".

`reconciliation` asks one question: given the stock counted on day X, and the
receipts and units sold in the months BEFORE X, is the implied opening stock
negative? The window is not a convenience filter — it is the causal boundary that
makes the arithmetic mean anything. Sales after the count cannot explain a
shortfall observed at the count.

`import_sales` took `inventory_as_of=None` to mean no boundary at all:

    in_window = [r for r in rows if reconcile_before is None or r["month"] < reconcile_before]

Measured against the real seven monthly reports and the real inventory, that is
not a rounding difference. With the true vintage (2026-06-06) 360 products are
flagged; with the window unknown, 443 — **117 invented, 34 genuine ones lost, and
100 of the 326 in common carrying a different `unaccounted`**, in both directions.
Each invented row sends the owner to recount a shelf for no reason.

CI never saw it: the nightly reruns the POS importer, so `_as_of` is always
present. It reaches whoever reproduces locally, which is what
docs/reviews/checkpoint-3-reproduction.md asks a stranger to do.

CLAUDE.md rule 8, in the engine rather than the UI: a figure that cannot be stated
honestly must not be stated.
"""
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyarrow as pa
import pyarrow.parquet as pq

from helpers import make_inputs, product, summary, window_of
from src.engine.reconciliation import run
from src.internal_pos.sales_importer import import_sales

W = window_of(["2026-01", "2026-02", "2026-03"])


def _unwindowed(barcode, *, units, receipts):
    """A summary row built without a stock-count date.

    helpers.summary() substitutes the plain totals when the reconcile_* arguments
    are None, so it cannot express "unknown" — which is the whole subject here.
    """
    row = summary(barcode, units=units, receipts=receipts)
    row["reconcile_units"] = None
    row["reconcile_receipts"] = None
    row["reconcile_months"] = None
    return row

REPORT = "﻿tתאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n"


def _report(directory: Path, hebrew_month: str, *, units: int, receipts: int) -> None:
    """One monthly sales report, in the shape read_report parses."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"דוח מכירות חודש {hebrew_month} 2026.csv").write_text(
        REPORT + f"מים,0012,{units},2.00,4.00,{units * 2}.00,{receipts},2.00,0.00,22,\n",
        encoding="utf-8",
    )


# ── The importer must not invent a window ────────────────────────────────────

def test_an_unknown_as_of_writes_no_reconciliation_figures(tmp_path):
    """The regression. `None` meant "every month"; it must mean "unknown"."""
    sales = tmp_path / "sales"
    _report(sales, "ינואר", units=10, receipts=100)
    _report(sales, "יולי", units=900, receipts=5)      # after any plausible count

    result = import_sales(sales, inventory_as_of=None, silver_dir=tmp_path / "silver")

    row = pq.read_table(tmp_path / "silver" / "sales_summary.parquet").to_pylist()[0]
    assert row["reconcile_units"] is None, "a window nobody chose must not be summed"
    assert row["reconcile_receipts"] is None
    assert row["reconcile_months"] is None
    assert result["reconcile_before"] is None


def test_an_unknown_as_of_still_writes_everything_that_does_not_need_a_window(tmp_path):
    """Only the three windowed figures are withheld.

    `catalogue_lifecycle` reads the same table and asks nothing about the stock
    date — 1,632 entries today. Withholding the whole table to protect three
    columns would take it down with them, which is why this is not
    `sales_summary = None`.
    """
    sales = tmp_path / "sales"
    _report(sales, "ינואר", units=10, receipts=100)
    _report(sales, "יולי", units=900, receipts=5)

    import_sales(sales, inventory_as_of=None, silver_dir=tmp_path / "silver")

    row = pq.read_table(tmp_path / "silver" / "sales_summary.parquet").to_pylist()[0]
    assert row["units_total"] == 910
    assert row["receipts_total"] == 105
    assert row["months_present"] == 2
    assert row["last_month_with_units"] == "2026-07"
    assert (tmp_path / "silver" / "sales_monthly.parquet").exists()


def test_a_known_as_of_is_unchanged(tmp_path):
    """The nightly's behaviour is pinned. Only months before the count count."""
    sales = tmp_path / "sales"
    _report(sales, "ינואר", units=10, receipts=100)
    _report(sales, "יולי", units=900, receipts=5)

    result = import_sales(sales, inventory_as_of=date(2026, 6, 6), silver_dir=tmp_path / "silver")

    row = pq.read_table(tmp_path / "silver" / "sales_summary.parquet").to_pylist()[0]
    assert result["reconcile_before"] == "2026-06"
    assert row["reconcile_units"] == 10, "July is after the count and must be excluded"
    assert row["reconcile_receipts"] == 100
    assert row["reconcile_months"] == 1


# ── The consumer must refuse to compute, not compute a zero ──────────────────

def test_reconciliation_is_unavailable_when_the_window_is_unknown():
    """Not `available` with zero findings.

    An empty detection list under a green status is indistinguishable from
    "reconciled, nothing missing" — the same silent conversion in a new costume.
    """
    inputs = make_inputs(
        products=[product("2", stock=-716.0)],
        sales_summary=[_unwindowed("2", units=663, receipts=62)],
        window=W)

    out = run(inputs)

    assert out.status == "unavailable"
    assert out.unavailable_reason == "unknown_stock_date"
    assert out.entries == []


def test_reconciliation_still_runs_when_the_window_is_known():
    """The guard must not fire on a healthy run."""
    inputs = make_inputs(
        products=[product("2", stock=-716.0)],
        sales_summary=[summary("2", units=663, receipts=62)],
        window=W)

    out = run(inputs)

    assert out.status == "available"
    assert [e.barcode for e in out.entries] == ["2"]


def test_one_product_missing_its_window_does_not_silence_the_whole_capability():
    """A row without reconciliation figures is skipped; rows that have them are
    still reconciled. The capability goes unavailable only when it has nothing
    windowed to work from."""
    inputs = make_inputs(
        products=[product("1", stock=-716.0), product("2", stock=-716.0)],
        sales_summary=[summary("1", units=663, receipts=62),
                       _unwindowed("2", units=663, receipts=62)],
        window=W)

    out = run(inputs)

    assert out.status == "available"
    assert [e.barcode for e in out.entries] == ["1"]
