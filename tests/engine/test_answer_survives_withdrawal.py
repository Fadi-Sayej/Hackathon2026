# tests/engine/test_answer_survives_withdrawal.py
"""AC-090 (SCN-088, NFR-042): a recorded answer survives the product being withdrawn.

The F5 validation record (2026-09-28) found this "met by construction" only: answers live in
owner state keyed by barcode, which classification never touches, and no test withdrew an
answered product. This one does, across the real boundary (rule 12): real silver tables, the
real load_inputs, catalogue_lifecycle withdrawing under `living`, and the hand-off to
owner_questions inside run_engine. Only the owner-state pull and the sales import are stubbed,
because they reach Firestore and the report files.
"""
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyarrow as pa
import pyarrow.parquet as pq

import src.engine.run as run_mod
from src.owner_state.model import OwnerState, answered_cost

LIVE, ANSWERED, UNANSWERED = "7290001", "7290002", "7290003"
AS_OF = "2026-03-01"


def _silver(tmp_path: Path) -> Path:
    silver = tmp_path / "silver"
    silver.mkdir()
    rows = [(LIVE, "חי", 10.0, 4.0, 5.0),
            (ANSWERED, "נענה", 6.0, 0.0, 0.0),     # no POS cost, no stock, no sales: withdrawable
            (UNANSWERED, "שקט", 6.0, 0.0, 0.0)]    # the same, never answered: the control
    prod = [{"barcode": b, "product_name": n, "category": "משקאות", "selling_price": s, "wolt_price": 0.0,
             "cost_price": c, "_source_file": "inv.csv", "_as_of": AS_OF} for b, n, s, c, _ in rows]
    inv = [{"barcode": b, "product_name": n, "current_stock": k, "_source_file": "inv.csv", "_as_of": AS_OF}
           for b, n, _, _, k in rows]
    pq.write_table(pa.Table.from_pylist(prod), silver / "products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "inventory.parquet")
    monthly = [{"barcode": LIVE, "month": m, "product_name": "חי", "units": 5.0, "receipts": 5.0, "revenue": 50.0,
                "cost_price": 4.0, "selling_price": 10.0, "_imported_at": "t", "_source_file": "s.csv"}
               for m in ("2026-01", "2026-02")]
    summary = [{"barcode": LIVE, "product_name": "חי", "months_present": 2, "units_total": 10.0,
                "receipts_total": 10.0, "last_month_with_units": "2026-02", "observed_zero": False,
                "_imported_at": "t"}]
    pq.write_table(pa.Table.from_pylist(monthly), silver / "sales_monthly.parquet")
    pq.write_table(pa.Table.from_pylist(summary), silver / "sales_summary.parquet")
    return silver


def _owner() -> OwnerState:
    return OwnerState.from_dict({"status": "available", "pulled_at": "t", "answers": {
        ANSWERED: {"cost_price": {"value": 2.5, "at": 1, "status": "answered"}}}})


def test_ac_090_an_answer_survives_its_product_being_withdrawn(tmp_path, monkeypatch):
    owner = _owner()
    seen = []
    real_load_inputs = run_mod.load_inputs

    def spy(**kw):
        inputs = real_load_inputs(**kw)
        seen.append(inputs)
        return inputs

    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: owner)
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"monthly_rows": 2})
    monkeypatch.setattr(run_mod, "load_inputs", spy)
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()

    result = run_mod.run_engine(
        mode="print", skip_market=True, population="living",
        now=datetime(2026, 9, 28, tzinfo=timezone.utc), silver_dir=_silver(tmp_path),
        sales_dir=tmp_path / "no-sales", daily_sales_dir=tmp_path / "no-daily",
        signals_dir=tmp_path / "no-signals", matches_path=tmp_path / "no-matches.parquet",
        snapshots_root=snapshots)
    caps = result["artefact"]["capabilities"]
    inputs = seen[-1]

    # Withdrawn, both of them: the answer does not keep a dead product alive.
    assert caps["catalogue_lifecycle"]["status"] == "available"
    assert inputs.withdrawn == {ANSWERED, UNANSWERED}

    # The answer is still recorded, and still read: load_inputs took the owner's cost over the
    # POS's missing one for the withdrawn product, exactly as for a living one.
    assert answered_cost(owner, ANSWERED) == 2.5
    shaped = {p["barcode"]: p for p in inputs.products}[ANSWERED]
    assert (shaped["cost_price"], shaped["cost_source"]) == (2.5, "owner")

    # Not asked again, and counted as answered, not as withdrawn. The control shows the
    # withdrawn set did reach owner_questions, so the answered count is not an accident of a
    # hand-off that never happened.
    questions = caps["owner_questions"]
    asked = {i["barcode"] for i in questions["items"]}
    assert ANSWERED not in asked and UNANSWERED not in asked
    assert questions["suppressed"]["answered"] == 1
    assert questions["suppressed"]["withdrawn"] == 1
