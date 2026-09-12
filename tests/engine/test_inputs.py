# tests/engine/test_inputs.py
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyarrow as pa
import pyarrow.parquet as pq

from src.engine.inputs import load_inputs
from src.engine.policy import load_policy
from src.owner_state.model import OwnerState


def _silver(tmp_path):
    silver = tmp_path / "silver"; silver.mkdir()
    prod = [{"barcode": "0012", "product_name": "מים", "category": "משקאות", "selling_price": 4.0, "wolt_price": 0.0,
             "cost_price": 0.0, "_source_file": "inv.csv", "_as_of": "2026-08-02"},
            {"barcode": None, "product_name": "אייס", "category": "c", "selling_price": 1.0, "wolt_price": 2.0,
             "cost_price": 0.5, "_source_file": "inv.csv", "_as_of": "2026-08-02"}]
    # product_name is part of the join key (a null barcode has no other), and the real
    # yomyom_inventory.parquet carries it — configs/pos_schema_mapping.yaml, inventory.columns.
    inv = [{"barcode": "0012", "product_name": "מים", "current_stock": -5.0, "_source_file": "inv.csv", "_as_of": "2026-08-02"},
           {"barcode": None, "product_name": "אייס", "current_stock": 3.0, "_source_file": "inv.csv", "_as_of": "2026-08-02"}]
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "yomyom_inventory.parquet")
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_margins.parquet")
    return silver


def test_every_requires_key_names_a_real_engine_inputs_field():
    """A misspelt key reads as "input missing" through getattr(), so the capability would
    publish as unavailable for ever — or KeyError in INPUT_REASONS. Nothing else binds the
    two files together, and this is the test that settles what `inventory` is."""
    from dataclasses import fields
    from src.engine.inputs import EngineInputs
    from src.engine.registry import CAPABILITIES, INPUT_REASONS
    names = {f.name for f in fields(EngineInputs)}
    for cap in CAPABILITIES.values():
        for key in cap.requires:
            assert key in names, f"{cap.id} requires {key!r}, absent from EngineInputs"
            assert key in INPUT_REASONS, f"{key!r} has no reason in INPUT_REASONS"


def test_products_are_shaped_and_owner_cost_wins(tmp_path):
    silver = _silver(tmp_path)
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t",
                                  "answers": {"12": {"cost_price": {"value": 2.5, "at": 1, "status": "answered"}}}})
    inputs = load_inputs(policy=load_policy(), owner=owner, run_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
                         silver_dir=silver, signals_dir=tmp_path / "nosignals", matches_path=tmp_path / "nomatches.parquet")
    p = {r["barcode"]: r for r in inputs.products}
    assert p["12"]["delivery_price"] is None          # zero Wolt price is absent, not zero
    assert p["12"]["cost_price"] == 2.5 and p["12"]["cost_source"] == "owner"
    assert p["12"]["recorded_stock"] == -5.0           # raw, never clamped
    assert p[None]["has_identifier"] is False
    assert inputs.sales_summary is None and inputs.window is None
    assert inputs.observations is None and inputs.matches is None
    assert inputs.vintages["pos"] == {"file": "inv.csv", "as_of": "2026-08-02"}
    assert inputs.vintages["owner_state"]["status"] == "available"


def test_missing_silver_yields_none_products(tmp_path):
    inputs = load_inputs(policy=load_policy(), owner=OwnerState.unavailable("x"),
                         run_at=datetime(2026, 9, 8, tzinfo=timezone.utc), silver_dir=tmp_path / "none",
                         signals_dir=tmp_path / "nosignals", matches_path=tmp_path / "nomatches.parquet")
    assert inputs.products is None


def _dup_silver(tmp_path, rows):
    silver = tmp_path / "silver"; silver.mkdir()
    base = {"_source_file": "inv.csv", "_as_of": "2026-08-02"}
    prod = [{**base, **r} for r in rows]
    inv = [{"barcode": r.get("barcode"), "product_name": r.get("product_name"),
            "current_stock": 1.0, **base} for r in rows]
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "yomyom_inventory.parquet")
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_margins.parquet")
    return silver


def _load(silver, tmp_path):
    return load_inputs(policy=load_policy(), owner=OwnerState.unavailable("x"),
                       run_at=datetime(2026, 9, 8, tzinfo=timezone.utc), silver_dir=silver,
                       signals_dir=tmp_path / "nosig", matches_path=tmp_path / "nomatch.parquet")


def test_identical_duplicate_rows_collapse_into_one_product(tmp_path):
    """Seven of the pilot's 48 duplicates are byte-identical. Nothing is lost by
    collapsing them and there is nothing to tell the owner (ADR-019)."""
    row = {"barcode": "7290105362377", "product_name": "כיף כף", "category": "c",
           "selling_price": 5.9, "wolt_price": 7.9, "cost_price": 3.0}
    inputs = _load(_dup_silver(tmp_path, [row, dict(row)]), tmp_path)
    assert [p["barcode"] for p in inputs.products] == ["7290105362377"]
    assert inputs.conflicting == []


def test_disagreeing_duplicate_rows_are_excluded_and_reported(tmp_path):
    """4062139003150 carries both 15.90 and 16.90. Neither is the shelf price, so the
    product leaves every population and the disagreement is published (ADR-019, D-3)."""
    a = {"barcode": "4062139003150", "product_name": "לייס", "category": "c",
         "selling_price": 15.9, "wolt_price": 15.9, "cost_price": 10.95}
    b = {**a, "selling_price": 16.9, "wolt_price": 16.9}
    inputs = _load(_dup_silver(tmp_path, [a, b]), tmp_path)
    assert inputs.products == []
    assert len(inputs.conflicting) == 1
    c = inputs.conflicting[0]
    assert c["barcode"] == "4062139003150"
    # the shaped domain names, not the POS column names — these are what reach the owner
    assert sorted(c["fields"]) == ["delivery_price", "shelf_price"]
    assert sorted(c["fields"]["shelf_price"]) == [15.9, 16.9]


def test_a_conflict_on_category_alone_still_excludes(tmp_path):
    """Partial presence is not a state the artefact can express (ADR-019, ADR-014)."""
    a = {"barcode": "838948000444", "product_name": "מסטיק", "category": "חטיפים מתוקים",
         "selling_price": 6.9, "wolt_price": 6.9, "cost_price": 4.66}
    b = {**a, "category": "מוצרי אלקטרונים"}
    inputs = _load(_dup_silver(tmp_path, [a, b]), tmp_path)
    assert inputs.products == []
    assert list(inputs.conflicting[0]["fields"]) == ["department"]
