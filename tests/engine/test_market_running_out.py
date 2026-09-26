# tests/engine/test_market_running_out.py
"""Phase 5 Task 5.4: the `market_running_out` capability (ADR-031 Decision 5, ADR-014)."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import polars as pl

from helpers import make_inputs
from src.engine import market_running_out
from src.engine.registry import CAPABILITIES, INPUT_REASONS

SIGNAL = {"on_day": "2026-09-24", "stores": ["a", "b"],
          "excluded": [{"store_id": "a", "day": "2026-09-21", "reason": "catalogue_change"}],
          "products": {"729001": {"stores_out": ["a"], "days_absent": {"a": 3}},
                       "729002": {"stores_out": ["a", "b"], "days_absent": {"a": 2, "b": 5}}}}


def _run(signal, run_day="2026-09-25"):
    run_at = datetime.fromisoformat(run_day).replace(hour=3, tzinfo=timezone.utc)
    return market_running_out.run(make_inputs(running_out=signal, run_at=run_at)).to_dict()


def test_it_is_registered_as_a_capability_that_carries_no_value():
    spec = CAPABILITIES["market_running_out"]
    assert spec.requires == ("running_out",)
    assert spec.value_policy == "none" and spec.admitted is False
    assert INPUT_REASONS["running_out"] == "market_signal_thin"


def test_no_signal_is_unavailable_with_the_input_reason():
    out = _run(None)
    assert (out["status"], out["unavailable_reason"]) == ("unavailable", "market_signal_thin")


def test_a_signal_older_than_two_days_is_stale():
    """ADR-031 Decision 5: the latest usable day more than two days before the run."""
    assert _run(SIGNAL, "2026-09-26")["status"] == "available"                     # two days
    out = _run(SIGNAL, "2026-09-27")                                              # three
    assert (out["status"], out["unavailable_reason"]) == ("unavailable", "market_signal_stale")


def test_an_available_signal_publishes_its_night_its_exclusions_and_each_product():
    out = _run(SIGNAL)
    assert out["status"] == "available"
    assert out["on_day"] == "2026-09-24"
    assert out["stores"] == ["a", "b"]
    assert out["excluded"] == SIGNAL["excluded"]
    assert out["products"] == SIGNAL["products"]
    assert out["counts"] == {"running_out": 2, "stores": 2, "excluded_store_days": 1}
    # ADR-031 Decision 6: the values travel with the signal.
    assert out["thresholds"]["min_absent"] == 2 and out["thresholds"]["max_absent"] == 7
    # It carries no money and no entry (INV-069): it is a fact the quantity reads.
    assert out["entries"] == []


def test_nothing_running_out_is_available_and_empty_not_unavailable():
    out = _run({**SIGNAL, "products": {}, "excluded": []})
    assert out["status"] == "available" and out["counts"]["running_out"] == 0


# ── Across the boundary: snapshots on disk → inputs → the published artefact ─

MARKET = "65daeb8779ca7f0a9bf964f3"          # Wolt Market: urban_minimarket, above the floor
BELOW = "631480ca6741954d25cf2611"           # Victory: supermarket, below it


def _snapshots(root: Path, days: int = 30, absent_last: int = 3, first=date(2026, 8, 27)):
    """A delivery-catalogue series: 20 steady products at each store, and `p` gone from
    both stores for the last `absent_last` days."""
    for i in range(days):
        day = first + timedelta(days=i)
        rows = [{"barcode": f"72900{j:03d}", "store_id": s, "is_online_available": True}
                for s in (MARKET, BELOW) for j in range(20)]
        if i < days - absent_last:
            rows += [{"barcode": "7290999", "store_id": s, "is_online_available": True} for s in (MARKET, BELOW)]
        folder = root / day.isoformat() / "delivery_catalog" / "01"
        folder.mkdir(parents=True, exist_ok=True)
        pl.DataFrame(rows).write_parquet(folder / "products_silver.parquet")
        (root / day.isoformat() / "_manifest.json").write_text(json.dumps(
            {"date": day.isoformat(), "status": "ok", "sources": {"delivery_catalog": {"status": "ok"}}}))
    return first + timedelta(days=days - 1)


def _load(tmp_path, snapshots, run_at):
    from src.engine.inputs import load_inputs
    from src.engine.policy import load_policy
    from src.owner_state.model import OwnerState
    return load_inputs(policy=load_policy(), owner=OwnerState.unavailable("x"), run_at=run_at,
                       silver_dir=tmp_path / "silver", signals_dir=tmp_path / "nosig",
                       matches_path=tmp_path / "nomatch.parquet", snapshots_root=snapshots)


def test_the_inputs_read_the_market_from_the_snapshots(tmp_path):
    last = _snapshots(tmp_path / "snap")
    inputs = _load(tmp_path, tmp_path / "snap", datetime.combine(last, datetime.min.time(), tzinfo=timezone.utc))
    assert inputs.running_out["on_day"] == last.isoformat()
    assert inputs.running_out["stores"] == [MARKET]                   # the store below the floor is not the market
    assert inputs.running_out["products"] == {"7290999": {"stores_out": [MARKET], "days_absent": {MARKET: 3}}}


def test_no_snapshots_is_no_signal(tmp_path):
    inputs = _load(tmp_path, tmp_path / "none", datetime(2026, 9, 25, tzinfo=timezone.utc))
    assert inputs.running_out is None


def test_a_changed_snapshot_changes_the_digest(tmp_path):
    last = _snapshots(tmp_path / "a")
    _snapshots(tmp_path / "b")
    _snapshots(tmp_path / "c", absent_last=4)
    run_at = datetime.combine(last, datetime.min.time(), tzinfo=timezone.utc)
    a, b, c = (_load(tmp_path, tmp_path / n, run_at).inputs_digest for n in "abc")
    assert a == b and a != c


def test_the_run_publishes_it(tmp_path, monkeypatch):
    import src.engine.run as run_mod
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    last = _snapshots(tmp_path / "snap")
    result = run_mod.run_engine(mode="print", now=datetime.combine(last, datetime.min.time(), tzinfo=timezone.utc),
                                silver_dir=tmp_path / "silver", signals_dir=tmp_path / "nosig",
                                matches_path=tmp_path / "nomatch.parquet", sales_dir=tmp_path / "nosales",
                                daily_sales_dir=tmp_path / "nodaily", snapshots_root=tmp_path / "snap")
    cap = result["artefact"]["capabilities"]["market_running_out"]
    assert cap["status"] == "available"
    assert cap["products"] == {"7290999": {"stores_out": [MARKET], "days_absent": {MARKET: 3}}}
