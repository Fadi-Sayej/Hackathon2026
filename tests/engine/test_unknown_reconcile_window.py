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


def _vintaged(inputs, as_of="2026-08-12"):
    """make_inputs() builds no vintages, and run() now reads the stock date from
    there rather than inferring it from NULLs in the summary."""
    inputs.vintages.setdefault("pos", {})["as_of"] = as_of
    return inputs


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

REPORT = "﻿תאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n"


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

def test_reconciliation_is_unavailable_when_the_stock_date_is_unknown():
    """Not `available` with zero findings.

    An empty detection list under a green status is indistinguishable from
    "reconciled, nothing missing" — the same silent conversion in a new costume.
    """
    inputs = make_inputs(products=[product("2", stock=-716.0)],
                         sales_summary=[_unwindowed("2", units=663, receipts=62)], window=W)
    inputs.vintages.setdefault("pos", {})["as_of"] = None

    out = run(inputs)

    assert out.status == "unavailable"
    assert out.unavailable_reason == "unknown_stock_date"
    assert out.entries == []


def test_an_empty_stock_date_is_as_unknown_as_a_missing_one():
    """`""` is not a date, and the guard must not treat it as one.

    Found by mutation: changing `if not as_of` to `if as_of is None` left every
    other test green. An empty string would then pass the guard and reach
    `date.fromisoformat(as_of[:10])` in _sales_import, which raises ValueError —
    a capability_error, which is a worse answer than an honest refusal. Anything
    falsy is "we do not know".
    """
    for empty in ("", "   ", None):
        inputs = make_inputs(products=[product("2", stock=-716.0)],
                             sales_summary=[summary("2", units=663, receipts=62)], window=W)
        inputs.vintages.setdefault("pos", {})["as_of"] = empty

        out = run(inputs)

        assert out.status == "unavailable", f"{empty!r} must read as no date"
        assert out.unavailable_reason == "unknown_stock_date"


def test_a_stale_summary_with_no_nulls_is_still_refused():
    """The hole in inferring the date from NULLs in the summary.

    When no monthly report parses, `import_sales` returns early and does NOT
    rewrite sales_summary.parquet — a summary from an older run survives with its
    full-history sums and no NULL to find. Reproduced against the real data: 439
    findings published `available`, over a window nobody chose. So the guard asks
    the vintage, which is the fact, rather than the summary, which is a proxy.
    """
    inputs = make_inputs(products=[product("2", stock=-716.0)],
                         sales_summary=[summary("2", units=663, receipts=62)],  # NOT null
                         window=W)
    inputs.vintages.setdefault("pos", {})["as_of"] = None

    out = run(inputs)

    assert out.status == "unavailable", "a stale non-null summary must not slip past"
    assert out.unavailable_reason == "unknown_stock_date"


def test_a_known_date_that_precedes_every_report_is_refused_too():
    """The date is known; the window is still empty.

    A count dated before the first monthly report leaves every row with
    reconcile_receipts 0.0 — no NULL anywhere — and the `receipts <= 0` skip would
    swallow all of them, publishing `available` with zero findings. Measured: a
    2025-12-31 count against Jan–Jul reports zeroes all 1,778 rows.
    """
    inputs = _vintaged(make_inputs(
        products=[product("2", stock=-716.0)],
        sales_summary=[summary("2", units=0, receipts=0, months=0,
                               reconcile_units=0.0, reconcile_receipts=0.0, reconcile_months=0)],
        window=W))

    out = run(inputs)

    assert out.status == "unavailable"
    assert out.unavailable_reason == "no_sales_evidence"


def test_a_first_run_with_no_silver_reports_no_pos_data_not_an_unknown_date(tmp_path):
    """The clean-clone case, across the whole engine rather than at the function.

    A fresh checkout has no silver layer at all (`data/internal/silver_pos/` is
    gitignored). The new guards must not intercept that: `derive_status` already
    answers it, and answering it twice with a different reason would tell an
    operator to look for a stock-count date when what is missing is every table.
    """
    import src.engine.run as run_mod

    result = run_mod.run_engine(mode="print", skip_market=True, silver_dir=tmp_path,
                                sales_dir=tmp_path / "no-reports")
    recon = result["artefact"]["capabilities"]["reconciliation"]

    assert recon["status"] == "unavailable"
    assert recon["unavailable_reason"] == "no_pos_data", \
        "the requires list answers a first run; the stock-date guards must not preempt it"
    assert result["status"] == "degraded"


def test_reconciliation_still_runs_when_the_window_is_known():
    """The guard must not fire on a healthy run."""
    inputs = _vintaged(make_inputs(products=[product("2", stock=-716.0)],
                                   sales_summary=[summary("2", units=663, receipts=62)], window=W))

    out = run(inputs)

    assert out.status == "available"
    assert [e.barcode for e in out.entries] == ["2"]


def test_one_product_missing_its_window_does_not_silence_the_whole_capability():
    """A row without reconciliation figures is skipped; rows that have them are
    still reconciled."""
    inputs = _vintaged(make_inputs(
        products=[product("1", stock=-716.0), product("2", stock=-716.0)],
        sales_summary=[summary("1", units=663, receipts=62),
                       _unwindowed("2", units=663, receipts=62)],
        window=W))

    out = run(inputs)

    assert out.status == "available"
    assert [e.barcode for e in out.entries] == ["1"]


def test_a_row_missing_only_its_unit_count_does_not_crash_the_capability():
    """float()/int() below would raise on any of the three, and a TypeError here
    becomes `capability_error` — a worse answer than an honest skip."""
    row = summary("2", units=663, receipts=62)
    row["reconcile_units"] = None
    inputs = _vintaged(make_inputs(products=[product("2", stock=-716.0)],
                                   sales_summary=[summary("1", units=663, receipts=62), row],
                                   window=W))

    out = run(inputs)

    assert out.status == "available"
    assert [e.barcode for e in out.entries] == []


# ── A date that is not a date, and a date that has not happened ──────────────
# Found by an adversarial review of this branch. `resolve_as_of` validates nothing,
# so `--as-of` is taken verbatim and the schema types the field as a bare string.
# Measured against the real data, each of these published 439 findings `available`:
# date.fromisoformat raised inside _sales_import, _step recorded a step error,
# import_sales never ran, and the PREVIOUS summary survived with its non-NULL
# reconcile columns — so the presence-only guard had nothing to catch.

def test_a_string_that_is_not_a_date_is_not_a_date():
    from src.engine.stock_date import usable_stock_date

    for junk in ("None", "2026-13-45", "unknown", "DROP TABLE", "   ", "", None):
        assert usable_stock_date(junk) is None, f"{junk!r} must not be usable"


def test_a_stock_count_cannot_have_happened_tomorrow():
    """An mtime on a freshly fetched export is always today or later, and every
    historical report precedes it — which is "use the entire history" reached
    through a date that is present and well-formed."""
    from datetime import date, timedelta
    from src.engine.stock_date import usable_stock_date

    today = date(2026, 9, 14)
    assert usable_stock_date("2099-12-31", today=today) is None
    assert usable_stock_date((today + timedelta(days=1)).isoformat(), today=today) is None
    assert usable_stock_date(today.isoformat(), today=today) == today, "today itself is fine"
    assert usable_stock_date("2026-06-06", today=today) == date(2026, 6, 6)


def test_the_capability_refuses_a_date_it_cannot_parse():
    """Both halves ask usable_stock_date, so the summary cannot be windowed on a
    date the capability would have refused."""
    for junk in ("None", "2026-13-45", "2099-12-31"):
        inputs = make_inputs(products=[product("2", stock=-716.0)],
                             sales_summary=[summary("2", units=663, receipts=62)], window=W)
        inputs.vintages.setdefault("pos", {})["as_of"] = junk

        out = run(inputs)

        assert out.status == "unavailable", f"{junk!r} must not reconcile"
        assert out.unavailable_reason == "unknown_stock_date"


# ── The third door: a date that parses, is in the past, and still is not one ──
#
# #102 closed "the date is absent". #109 closed "the date is wrong because git was
# asked on a shallow clone". Both leave `file_mtime` — the ladder's last rung, which
# `git clone` sets to the checkout time. On a runner that is always today: it parses,
# it is not in the future, and it widens the window to every month. The production
# instance came in through the other door and cost 355 → 439 findings; this one is the
# same arithmetic reached by the ladder's own fallback.

def test_a_filesystem_timestamp_is_not_a_stock_count_date():
    from src.engine.stock_date import usable_stock_date

    assert usable_stock_date("2026-06-06", source="file_mtime") is None
    # The other three rungs are statements about the data, not about the disk.
    for source in ("declared", "declared_sidecar", "git_commit"):
        assert usable_stock_date("2026-06-06", source=source) == date(2026, 6, 6), source


def test_an_absent_source_is_not_a_reason_to_refuse():
    """ADR-017: unknown is not false. Tables written before `_as_of_source` existed carry
    no source, and refusing those would take a working capability off the owner's screen
    for a column's age rather than for a defect."""
    from src.engine.stock_date import usable_stock_date

    assert usable_stock_date("2026-06-06") == date(2026, 6, 6)
    assert usable_stock_date("2026-06-06", source=None) == date(2026, 6, 6)


def test_reconciliation_refuses_a_date_that_came_from_the_filesystem():
    """The whole point: the date is valid by every other test in this file — it parses,
    it is in the past — and the capability must still refuse, because what it measures is
    when the file was written, not when the shelf was counted."""
    inputs = make_inputs(products=[product("2", stock=-716.0)],
                         sales_summary=[_unwindowed("2", units=663, receipts=62)], window=W)
    inputs.vintages.setdefault("pos", {}).update(
        {"as_of": "2026-06-06", "as_of_source": "file_mtime"})

    out = run(inputs)

    assert out.status == "unavailable"
    assert out.unavailable_reason == "unknown_stock_date"
    assert out.entries == []


def test_the_same_date_from_git_is_accepted():
    """The guard must key on the SOURCE, not on the date. Same value, different rung."""
    inputs = make_inputs(products=[product("2", stock=-716.0)],
                         sales_summary=[summary("2", units=663, receipts=62, months=3)], window=W)
    inputs.vintages.setdefault("pos", {}).update(
        {"as_of": "2026-06-06", "as_of_source": "git_commit"})

    assert run(inputs).status == "available"
