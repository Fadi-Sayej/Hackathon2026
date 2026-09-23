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


# ── The cut must not invent a window ─────────────────────────────────────────
#
# ADR-026 moved the cut from the importer to load_inputs, so these ask load_inputs. The
# importer no longer takes a stock date at all; what it still owes is everything that
# does not need one.

def _load_after_import(tmp_path, sales, as_of, *, source="declared_sidecar", stock=50.0):
    """The importer, then load_inputs, over silver carrying a chosen stock count — the
    boundary ADR-026 moved the cut across."""
    from datetime import datetime, timezone
    import src.engine.run as run_mod
    from src.engine.inputs import load_inputs
    from src.engine.policy import load_policy
    from src.owner_state.model import OwnerState

    silver = _pos_silver(tmp_path / "silver", as_of, stock=stock, source=source)
    run_mod._sales_import(sales, silver)
    return load_inputs(policy=load_policy(), owner=OwnerState.unavailable("no_credentials"),
                       run_at=datetime(2026, 9, 23, tzinfo=timezone.utc), silver_dir=silver,
                       signals_dir=tmp_path / "n", matches_path=tmp_path / "n.parquet")


def test_the_importer_writes_everything_lifecycle_reads_without_a_stock_date(tmp_path):
    """`catalogue_lifecycle` reads the same table and asks nothing about the stock date —
    1,632 entries on 2026-09-16. The importer needs no date to write what it reads."""
    sales = tmp_path / "sales"
    _report(sales, "ינואר", units=10, receipts=100)
    _report(sales, "יולי", units=900, receipts=5)

    import_sales(sales, silver_dir=tmp_path / "silver")

    row = pq.read_table(tmp_path / "silver" / "sales_summary.parquet").to_pylist()[0]
    assert row["units_total"] == 910
    assert row["receipts_total"] == 105
    assert row["months_present"] == 2
    assert row["last_month_with_units"] == "2026-07"
    assert (tmp_path / "silver" / "sales_monthly.parquet").exists()


def test_a_known_stock_date_cuts_before_its_month(tmp_path):
    """The nightly's behaviour is pinned, at the place the cut now happens. Counted on
    2026-06-06: January counts, July (after the count) does not."""
    sales = tmp_path / "sales"
    _report(sales, "ינואר", units=10, receipts=100)
    _report(sales, "יולי", units=900, receipts=5)

    inputs = _load_after_import(tmp_path, sales, "2026-06-06")

    row = inputs.sales_summary["12"]
    assert inputs.vintages["sales"]["reconcile_before"] == "2026-06"
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


def _load_with(tmp_path, as_of, as_of_source):
    """Silver carrying a chosen vintage, loaded. test_inputs.py's `_dup_silver` hard-codes
    `_as_of` and writes no `_as_of_source`, and the source is the axis these tests vary, so
    this builds its own rather than widening a helper another file owns."""
    from datetime import datetime, timezone
    from src.engine.inputs import load_inputs
    from src.engine.policy import load_policy
    from src.owner_state.model import OwnerState

    silver = tmp_path / "silver"
    silver.mkdir(parents=True, exist_ok=True)
    base = {"_source_file": "inv.csv", "_as_of": as_of, "_as_of_source": as_of_source}
    row = {"barcode": "0012", "product_name": "מים", "category": "c",
           "selling_price": 4.0, "wolt_price": 5.0, "cost_price": 1.0}
    prod = [{**base, **row}]
    inv = [{"barcode": row["barcode"], "product_name": row["product_name"],
            "current_stock": 1.0, **base}]
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "yomyom_inventory.parquet")
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_margins.parquet")
    return load_inputs(policy=load_policy(), owner=OwnerState.unavailable("no_credentials"),
                       run_at=datetime(2026, 9, 8, tzinfo=timezone.utc), silver_dir=silver,
                       signals_dir=tmp_path / "n", matches_path=tmp_path / "n.parquet")

# ── The boundary is published, not merely obeyed (#105) ──────────────────────
#
# OQ-201 asked whether stock, receipts and sales cover the same period, and the answer
# recorded at system-design §21 is "window vintages published so misalignment is visible".
# Reconciliation's own window was the one that was not: `vintages.sales` spans every monthly
# row, while the capability counts only months BEFORE the stock count. Measured on the
# 2026-09-21 artefact, the published span said seven months and no entry used more than five.

def test_the_reconciliation_boundary_is_published(tmp_path):
    """Visible, not inferable. `evidence.reconcile_months` is a count, not a boundary — two
    products with different histories can share a count and not a window."""
    inputs = _load_with(tmp_path, "2026-06-06", "declared_sidecar")
    assert inputs.vintages["sales"]["reconcile_before"] == "2026-06"


def test_the_boundary_comes_from_the_same_definition_the_capability_refuses_on():
    """One definition, asked twice. If `usable_stock_date` rejects the date the capability
    goes `unknown_stock_date`, and a published month beside a refusing capability would say
    the window was known when it was not."""
    from src.engine.stock_date import usable_stock_date

    assert usable_stock_date("2026-06-06", source="declared_sidecar").strftime("%Y-%m") == "2026-06"
    for unusable in (None, "", "   ", "not-a-date"):
        assert usable_stock_date(unusable) is None
    assert usable_stock_date("2026-06-06", source="file_mtime") is None


def test_a_refused_date_publishes_no_boundary(tmp_path):
    """Null, never the full span. The defect this guards is a window that overstates what
    was reconciled; defaulting to everything would BE that defect."""
    inputs = _load_with(tmp_path, "2026-06-06", "file_mtime")
    assert inputs.vintages["sales"]["reconcile_before"] is None
    # Unavailable, and the specific reason is whichever gate fires first — this fixture has
    # no sales summary, so `derive_status` returns `no_sales_evidence` before the capability
    # reaches its own `unknown_stock_date` refusal. Both are honest; the tests above pin the
    # stock-date one directly. What matters here is that no findings are published over a
    # boundary the engine does not have.
    out = run(inputs)
    assert out.status == "unavailable" and out.entries == []


# ── ADR-026: the reconcile window is cut once per run, at load ───────────────
#
# The boundary used to be decided twice: by the importer when it wrote the summary, and
# again by load_inputs when #144 published it. The two agree every normal night and
# disagree on the day no report parses after a new stock count, because the summary cut
# for the old count survives beside the new one. ADR-026 makes the cut once, in
# load_inputs, so the figures, the published boundary and the capability's window are one
# fact. Most of these drive the whole engine, because the loss happened between modules.
#
# One product, 0012, sells in January (10 units, 100 received) and July (5, 900).

def _pos_silver(silver, as_of, *, stock, source="declared_sidecar"):
    """POS tables for 0012 carrying a chosen stock count. Rewrites only the POS tables, so
    calling it on an existing silver keeps whatever sales tables an earlier run left."""
    silver.mkdir(parents=True, exist_ok=True)
    base = {"_source_file": "inv.csv", "_as_of": as_of, "_as_of_source": source}
    row = {"barcode": "0012", "product_name": "מים", "category": "c",
           "selling_price": 4.0, "wolt_price": 5.0, "cost_price": 1.0}
    pq.write_table(pa.Table.from_pylist([{**base, **row}]), silver / "yomyom_products.parquet")
    pq.write_table(pa.Table.from_pylist([{**base, **row}]), silver / "yomyom_margins.parquet")
    pq.write_table(pa.Table.from_pylist([{"barcode": "0012", "product_name": "מים",
                                          "current_stock": stock, **base}]),
                   silver / "yomyom_inventory.parquet")
    return silver


def _two_reports(tmp_path):
    sales = tmp_path / "sales"
    _report(sales, "ינואר", units=10, receipts=100)
    _report(sales, "יולי", units=5, receipts=900)
    return sales


def _engine(silver, sales_dir):
    """The whole path (importer, load_inputs, capability, publisher) in print mode."""
    from datetime import datetime, timezone
    import src.engine.run as run_mod

    return run_mod.run_engine(mode="print", skip_market=True, silver_dir=silver,
                              sales_dir=sales_dir, signals_dir=silver.parent / "no-signals",
                              matches_path=silver.parent / "no-matches.parquet",
                              now=datetime(2026, 9, 23, tzinfo=timezone.utc))["artefact"]


def test_adr_026_the_window_published_is_the_span_reconciled(tmp_path):
    """AC-024, NFR-010: the period beside the arithmetic is the period of the arithmetic.

    Counted on 2026-06-06, so only January is summed: 50 − 100 + 10 = −40, flagged. The
    window used to say 2026-01..2026-07 beside January's figures."""
    silver = _pos_silver(tmp_path / "silver", "2026-06-06", stock=50.0)

    artefact = _engine(silver, _two_reports(tmp_path))
    recon = artefact["capabilities"]["reconciliation"]

    assert recon["status"] == "available"
    assert recon["window"]["window_id"] == "2026-01..2026-01"
    assert [e["evidence"]["window_id"] for e in recon["entries"]] == ["2026-01..2026-01"]
    assert artefact["figures"]["reconciliation.flagged"]["thresholds"]["window"] == "2026-01..2026-01"
    assert artefact["vintages"]["sales"]["reconcile_before"] == "2026-06"


def test_adr_026_lifecycle_keeps_the_span_of_the_sales_data(tmp_path):
    """What must not move. Catalogue lifecycle reasons over every month (ADR-011), so its
    window stays the sales span however the reconcile window is cut."""
    silver = _pos_silver(tmp_path / "silver", "2026-06-06", stock=50.0)

    artefact = _engine(silver, _two_reports(tmp_path))

    assert artefact["capabilities"]["catalogue_lifecycle"]["window"]["window_id"] == "2026-01..2026-07"
    assert artefact["vintages"]["sales"]["months"] == ["2026-01", "2026-07"]


def test_adr_026_a_new_count_is_reconciled_against_the_reports_on_disk(tmp_path):
    """#105 finding 2, made impossible rather than refused.

    A summary cut at a February count survives a night when no report parses, and an August
    export lands. At February 0012 is not short (500 − 100 + 10 = 410). Counted in August
    against both months, it is (500 − 1000 + 15 = −485). The engine used to publish the
    February cut beside the August stock. It must publish what a clean import on the August
    date publishes."""
    sales = _two_reports(tmp_path)
    silver = _pos_silver(tmp_path / "silver", "2026-02-15", stock=500.0)
    _engine(silver, sales)                                     # the February night
    _pos_silver(silver, "2026-08-12", stock=500.0)             # an August export lands…
    bad_day = _engine(silver, tmp_path / "no-reports")         # …and no report parses
    control = _engine(_pos_silver(tmp_path / "control", "2026-08-12", stock=500.0), sales)

    want = control["capabilities"]["reconciliation"]
    got = bad_day["capabilities"]["reconciliation"]
    assert [(e["barcode"], e["evidence"]["unaccounted"]) for e in want["entries"]] == [("12", 485.0)]
    assert [(e["barcode"], e["evidence"]["unaccounted"]) for e in got["entries"]] == [("12", 485.0)]
    assert got["window"]["window_id"] == "2026-01..2026-07"
    assert bad_day["vintages"]["sales"]["reconcile_before"] == "2026-08"


def test_adr_026_an_unusable_stock_date_cuts_nothing(tmp_path):
    """#102, kept where the cut now lives. A filesystem timestamp is not a stock count, so
    there is no boundary: the figures stay unknown, never the whole history."""
    inputs = _load_after_import(tmp_path, _two_reports(tmp_path), "2026-06-06", source="file_mtime")

    row = inputs.sales_summary["12"]
    assert (row["reconcile_units"], row["reconcile_receipts"], row["reconcile_months"]) == (None, None, None)
    assert inputs.vintages["sales"]["reconcile_before"] is None
    assert run(inputs).unavailable_reason == "unknown_stock_date"


def test_adr_026_reconcile_months_counts_months_not_rows(tmp_path):
    """#156 part 1. A report can print one barcode's line twice, and the month it covers is
    still one month. (Whether the two lines are one sale is #156 part 2, not asserted here.)"""
    sales = tmp_path / "sales"
    sales.mkdir(parents=True)
    line = "מים,0012,10,2.00,4.00,20.00,100,2.00,0.00,22,\n"
    (sales / "דוח מכירות חודש ינואר 2026.csv").write_text(REPORT + line + line, encoding="utf-8")

    inputs = _load_after_import(tmp_path, sales, "2026-06-06")

    assert inputs.sales_summary["12"]["reconcile_months"] == 1


def test_adr_026_the_boundary_is_part_of_the_digest(tmp_path):
    """ADR-026 part 5. Identical files with counts in different months cut different
    figures, so the digest must differ. Two counts within one month cut identically, so it
    must not."""
    sales = _two_reports(tmp_path)

    def digest(as_of):
        return _engine(_pos_silver(tmp_path / as_of, as_of, stock=50.0), sales)["inputs_digest"]

    june = digest("2026-06-06")
    assert june != digest("2026-08-12")
    assert june == digest("2026-06-20")


def test_adr_026_no_published_boundary_means_nothing_is_carved():
    """The window is carved from vintages.sales.reconcile_before, which is null exactly when
    the stock date is unusable. A null boundary beside a usable POS date cannot come out of
    load_inputs. If it ever reaches the capability, the answer is the honest refusal, not a
    window carved from nothing and not a crash."""
    inputs = _vintaged(make_inputs(products=[product("2", stock=-716.0)],
                                   sales_summary=[summary("2", units=663, receipts=62)], window=W))
    inputs.vintages["sales"]["reconcile_before"] = None

    out = run(inputs)

    assert out.status == "unavailable"
    assert out.unavailable_reason == "unknown_stock_date"
    assert out.entries == []
