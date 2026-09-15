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
    # `_silver()` writes the parquet by hand without `_as_of_source`, as tables written
    # before that column existed do. `None` there reads as "we do not know how this
    # vintage was arrived at", which is the honest answer rather than a guess.
    assert inputs.vintages["pos"] == {"file": "inv.csv", "as_of": "2026-08-02",
                                      "as_of_source": None}
    assert inputs.vintages["owner_state"]["status"] == "available"


def test_owner_state_vintage_says_when_it_came_from_the_committed_mirror(tmp_path):
    """A replayed mirror must not read as a live pull.

    `_pull_owner_state()` falls back to the committed replica when no credential is
    present — that is deliberate, so reproduction works on a laptop. It is flagged twice
    on the way: `read_mirror()` sets reason='from_mirror', and `_pull_owner_state()` would
    set 'no_credentials'. Then the vintage published only `pulled_at` and `status`, so
    both flags were dropped and nothing reached the artefact.

    Measured on the Checkpoint 3 run-2 clone: no service account, every FIREBASE_*
    variable stripped, and the published provenance still said
    `owner_state: {status: available}` with a `pulled_at` from a different machine 22
    hours earlier, and `provenance.owner_state_available: 1`. Design §13 says the system
    behaves as unavailable *honestly* and is "not silently local"; this was silently
    local.

    Rule 12 in miniature — a flag set carefully and carried nowhere.
    """
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "2026-09-12T13:50:57+00:00",
                                  "reason": "from_mirror"})
    inputs = load_inputs(policy=load_policy(), owner=owner,
                         run_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
                         silver_dir=tmp_path / "nosilver", signals_dir=tmp_path / "nosignals",
                         matches_path=tmp_path / "nomatches.parquet")
    v = inputs.vintages["owner_state"]
    assert v["status"] == "available"
    assert v["pulled_at"] == "2026-09-12T13:50:57+00:00"
    assert v["reason"] == "from_mirror", "a replayed mirror must be distinguishable from a live pull"

    live = OwnerState.from_dict({"status": "available", "pulled_at": "2026-09-13T10:55:30+00:00"})
    lv = load_inputs(policy=load_policy(), owner=live,
                     run_at=datetime(2026, 9, 13, tzinfo=timezone.utc),
                     silver_dir=tmp_path / "nosilver", signals_dir=tmp_path / "nosignals",
                     matches_path=tmp_path / "nomatches.parquet").vintages["owner_state"]
    assert lv["reason"] is None, "a live pull carries no reason, so the field stays falsy"


def test_competitor_vintage_names_its_sources_and_counts_its_stores():
    """`vintages.competitor.sources` has to hold sources.

    It held `store_id`. On the live artefact that meant the owner's provenance block
    listed 164 "sources" reading "401", "402", "403" and seven Wolt ObjectIds like
    "631480ca6741954d25cf2611". The DataPage fixture has always expected a feed name
    (`sources: ['wolt']`), so this is a drift between name and content, not a
    preference — and the schema cannot catch it: it requires an array of strings and
    says nothing about which strings.

    Same defect family as the `row_count` that retired sources.json: a field written
    without a definition. The store count is kept, under a name that says what it is.
    """
    from src.engine.inputs import _competitor_vintage

    observations = [
        {"store_id": "401", "source_type": "price_file", "observed_at": "2026-09-13T02:00:00Z"},
        {"store_id": "402", "source_type": "price_file", "observed_at": "2026-09-13T02:00:00Z"},
        {"store_id": "631480ca6741954d25cf2611", "source_type": "delivery",
         "observed_at": "2026-09-12T02:00:00Z"},
    ]
    v = _competitor_vintage(observations)
    assert v["sources"] == ["delivery", "price_file"]   # what the data came from
    assert v["store_count"] == 3                        # not thrown away, just named
    assert v["snapshot_date"] == "2026-09-13"           # newest observation wins
    assert "401" not in v["sources"]

    empty = _competitor_vintage(None)
    assert empty == {"snapshot_date": None, "sources": [], "store_count": 0}


def test_missing_silver_yields_none_products(tmp_path):
    inputs = load_inputs(policy=load_policy(), owner=OwnerState.unavailable("x"),
                         run_at=datetime(2026, 9, 8, tzinfo=timezone.utc), silver_dir=tmp_path / "none",
                         signals_dir=tmp_path / "nosignals", matches_path=tmp_path / "nomatches.parquet")
    assert inputs.products is None


def _dup_silver(tmp_path, rows):
    silver = tmp_path / "silver"; silver.mkdir(parents=True, exist_ok=True)
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


def test_the_digest_is_over_content_not_over_files(tmp_path):
    """Task 3.1. Identical content must digest identically however it arrived, and a changed
    policy constant must change it — a figure computed under a different threshold is a
    different figure."""
    row = {"barcode": "0012", "product_name": "מים", "category": "c", "selling_price": 4.0,
           "wolt_price": 5.0, "cost_price": 1.0}
    a = _load(_dup_silver(tmp_path / "a", [row]), tmp_path)
    b = _load(_dup_silver(tmp_path / "b", [dict(row)]), tmp_path)
    assert a.inputs_digest == b.inputs_digest
    assert len(a.inputs_digest) == 64


def test_a_changed_policy_changes_the_digest(tmp_path):
    from dataclasses import replace
    row = {"barcode": "0012", "product_name": "מים", "category": "c", "selling_price": 4.0,
           "wolt_price": 5.0, "cost_price": 1.0}
    silver = _dup_silver(tmp_path, [row])
    base = load_policy()
    one = load_inputs(policy=base, owner=OwnerState.unavailable("x"),
                      run_at=datetime(2026, 9, 8, tzinfo=timezone.utc), silver_dir=silver,
                      signals_dir=tmp_path / "n", matches_path=tmp_path / "n.parquet")
    two = load_inputs(policy=replace(base, surface_bound=99), owner=OwnerState.unavailable("x"),
                      run_at=datetime(2026, 9, 8, tzinfo=timezone.utc), silver_dir=silver,
                      signals_dir=tmp_path / "n", matches_path=tmp_path / "n.parquet")
    assert one.inputs_digest != two.inputs_digest


def test_the_digest_ignores_when_the_owner_state_was_fetched(tmp_path):
    """The owner's answers are an input; the moment we fetched them is not. Hashing
    pulled_at made two runs over identical data disagree, which would have made the digest
    detect nothing at all."""
    row = {"barcode": "0012", "product_name": "מים", "category": "c", "selling_price": 4.0,
           "wolt_price": 5.0, "cost_price": 1.0}
    silver = _dup_silver(tmp_path, [row])
    answers = {"0012": {"cost_price": {"value": 2.5, "at": 1, "status": "answered"}}}
    early = OwnerState.from_dict({"status": "available", "pulled_at": "2026-09-12T08:00:00Z", "answers": answers})
    later = OwnerState.from_dict({"status": "available", "pulled_at": "2026-09-12T23:59:59Z", "answers": answers})
    common = dict(run_at=datetime(2026, 9, 8, tzinfo=timezone.utc), silver_dir=silver,
                  signals_dir=tmp_path / "n", matches_path=tmp_path / "n.parquet",
                  policy=load_policy())
    assert load_inputs(owner=early, **common).inputs_digest == load_inputs(owner=later, **common).inputs_digest


def test_the_digest_ignores_the_device_register(tmp_path):
    """ADR-021 review finding 3, and the one that would have cost real time. `last_seen_at`
    moves every time anyone opens the app — far more often than `pulled_at`, which is already
    excluded for exactly this reason. Hashing it would make two runs over identical data
    disagree, and the cause would have looked like the engine rather than the ADR."""
    row = {"barcode": "0012", "product_name": "מים", "category": "c", "selling_price": 4.0,
           "wolt_price": 5.0, "cost_price": 1.0}
    silver = _dup_silver(tmp_path, [row])
    answers = {"0012": {"cost_price": {"value": 2.5, "at": 1, "status": "answered"}}}
    common = dict(run_at=datetime(2026, 9, 8, tzinfo=timezone.utc), silver_dir=silver,
                  signals_dir=tmp_path / "n", matches_path=tmp_path / "n.parquet",
                  policy=load_policy())
    base = {"status": "available", "pulled_at": "t", "answers": answers}
    quiet = OwnerState.from_dict({**base, "devices": {"aaa": {"first_seen_at": 1, "last_seen_at": 1}}})
    busy = OwnerState.from_dict({**base, "devices": {"aaa": {"first_seen_at": 1, "last_seen_at": 1789290000000},
                                                     "bbb": {"first_seen_at": 2, "last_seen_at": 1789290000001}}})
    assert load_inputs(owner=quiet, **common).inputs_digest == load_inputs(owner=busy, **common).inputs_digest
    # …and it is published, so excluding it from the digest is not the same as dropping it.
    assert load_inputs(owner=busy, **common).vintages["owner_state"]["devices"]["count"] == 2


def test_a_changed_owner_answer_does_change_the_digest(tmp_path):
    row = {"barcode": "0012", "product_name": "מים", "category": "c", "selling_price": 4.0,
           "wolt_price": 5.0, "cost_price": 1.0}
    silver = _dup_silver(tmp_path, [row])
    common = dict(run_at=datetime(2026, 9, 8, tzinfo=timezone.utc), silver_dir=silver,
                  signals_dir=tmp_path / "n", matches_path=tmp_path / "n.parquet",
                  policy=load_policy())
    a = OwnerState.from_dict({"status": "available", "pulled_at": "t", "answers": {"0012": {"cost_price": {"value": 2.5, "at": 1, "status": "answered"}}}})
    b = OwnerState.from_dict({"status": "available", "pulled_at": "t", "answers": {"0012": {"cost_price": {"value": 9.9, "at": 1, "status": "answered"}}}})
    assert load_inputs(owner=a, **common).inputs_digest != load_inputs(owner=b, **common).inputs_digest


def test_reimporting_the_same_data_does_not_change_the_digest(tmp_path):
    """The failure the first digest shipped with, and which the unit tests above all
    missed: sales_import rewrites its tables on every run with a fresh `_imported_at`, so
    two runs over identical data disagreed. A digest that changes every run reports a change
    every run and therefore reports nothing.

    `_as_of` is deliberately NOT excluded — the POS vintage is content, and a different
    export day is a different input.
    """
    row = {"barcode": "0012", "product_name": "מים", "category": "c", "selling_price": 4.0,
           "wolt_price": 5.0, "cost_price": 1.0}
    first = _dup_silver(tmp_path / "first", [{**row, "_imported_at": "2026-09-12T08:00:00Z"}])
    again = _dup_silver(tmp_path / "again", [{**row, "_imported_at": "2026-09-12T23:59:59Z"}])
    assert _load(first, tmp_path).inputs_digest == _load(again, tmp_path).inputs_digest

def test_identical_rows_from_different_export_days_are_the_same_input(tmp_path):
    """Deliberate. The digest is over CONTENT: if two POS exports carry identical rows they
    are the same input, whichever day they were taken. The export day is not lost — it is
    published in vintages.pos.as_of, where a reader can see it."""
    row = {"barcode": "0012", "product_name": "מים", "category": "c", "selling_price": 4.0,
           "wolt_price": 5.0, "cost_price": 1.0}
    import pyarrow as pa_, pyarrow.parquet as pq_
    a = _dup_silver(tmp_path / "a", [row])
    b = _dup_silver(tmp_path / "b", [row])
    pq_.write_table(pa_.Table.from_pylist([{**row, "_source_file": "inv.csv", "_as_of": "2026-09-01"}]),
                    b / "yomyom_products.parquet")
    assert _load(a, tmp_path).inputs_digest == _load(b, tmp_path).inputs_digest


# ── #89: the stock join overwrote rows that share a key ──────────────────────────────
#
# _shape_products joined inventory through a dict keyed on (barcode, product_name). That key
# is not unique — the pilot has 30 keys carrying more than one row with differing stock — so
# the last row's stock was written onto every earlier one. 35 raw rows published another
# row's stock: 13 real negatives shown as a different negative, 12 hidden as zero or
# positive, and 9 rows at zero or above shown as negative.
#
# Every ADR-019 test above passed throughout, because _dup_silver gives every duplicate row
# current_stock=1.0: no test ever let two rows disagree on stock, so none crossed the point
# where the disagreement was being erased. These do.

def _rows_silver(tmp_path, rows):
    """Like _dup_silver, but each row carries its OWN stock, in export order."""
    silver = tmp_path / "silver"; silver.mkdir(parents=True, exist_ok=True)
    base = {"_source_file": "inv.csv", "_as_of": "2026-08-02"}
    prod = [{**base, **{k: v for k, v in r.items() if k != "current_stock"}} for r in rows]
    inv = [{"barcode": r.get("barcode"), "product_name": r.get("product_name"),
            "current_stock": r["current_stock"], **base} for r in rows]
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "yomyom_inventory.parquet")
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_margins.parquet")
    return silver


def test_89_a_barcoded_duplicate_disagreeing_only_on_stock_is_reported(tmp_path):
    """The join handed both rows the same stock, so ADR-019 saw them agree and collapsed
    them — publishing one stock and silently losing the other. A disagreement that the join
    erases is a disagreement ADR-019 can never see."""
    a = {"barcode": "7290000000017", "product_name": "במבה", "category": "c",
         "selling_price": 5.0, "wolt_price": 6.0, "cost_price": 3.0, "current_stock": -5.0}
    b = {**a, "current_stock": 10.0}
    inputs = _load(_rows_silver(tmp_path, [a, b]), tmp_path)
    assert inputs.products == [], "a product listed with two stocks has no stock the system can state"
    assert len(inputs.conflicting) == 1
    assert sorted(inputs.conflicting[0]["fields"]["recorded_stock"]) == [-5.0, 10.0]


def test_89_barcode_less_rows_sharing_a_name_and_disagreeing_are_a_conflict(tmp_path):
    """The pilot's 'בייגל סלמון נורוויגי': two barcode-less rows, stock -400 and -7. Both
    were published as -7 and the -400 disappeared.

    ADR-022. A barcode-less row used to be "kept as itself", which made both rows publish
    findings under ONE entry id — so the owner resolving one resolved the other. Grouped by
    name like a barcode is, they disagree, so neither is a product the system can state and
    both numbers survive in the conflict record instead of being erased."""
    from src.engine.inputs import _shape_products
    a = {"barcode": None, "product_name": "בייגל סלמון", "category": "barista",
         "selling_price": 34.9, "wolt_price": 0.0, "cost_price": 0.0}
    b = dict(a)
    inv = [{"barcode": None, "product_name": "בייגל סלמון", "current_stock": -400.0},
           {"barcode": None, "product_name": "בייגל סלמון", "current_stock": -7.0}]
    products, conflicting = _shape_products([a, b], inv, OwnerState.unavailable("x"))
    assert products == []
    assert len(conflicting) == 1
    assert conflicting[0]["barcode"] is None and conflicting[0]["product_name"] == "בייגל סלמון"
    assert sorted(conflicting[0]["fields"]["recorded_stock"]) == [-400.0, -7.0]


def test_89_barcode_less_rows_identical_in_every_field_collapse():
    """The one pilot name listed twice with nothing different. Same row twice, nothing to
    tell the owner — exactly ADR-019's rule for a barcode, now applied to a name."""
    from src.engine.inputs import _shape_products
    row = {"barcode": None, "product_name": "קפה", "category": "barista",
           "selling_price": 9.0, "wolt_price": 0.0, "cost_price": 0.0}
    inv = [{"barcode": None, "product_name": "קפה", "current_stock": 3.0}] * 2
    products, conflicting = _shape_products([row, dict(row)], inv, OwnerState.unavailable("x"))
    assert [p["product_name"] for p in products] == ["קפה"]
    assert conflicting == []


def test_89_a_barcode_less_row_with_a_unique_name_is_untouched():
    from src.engine.inputs import _shape_products
    row = {"barcode": None, "product_name": "אייס", "category": "c",
           "selling_price": 1.0, "wolt_price": 0.0, "cost_price": 0.0}
    products, conflicting = _shape_products([row], [{"barcode": None, "product_name": "אייס",
                                                     "current_stock": -2.0}], OwnerState.unavailable("x"))
    assert len(products) == 1 and products[0]["recorded_stock"] == -2.0 and conflicting == []


def test_89_no_two_hygiene_entries_share_an_id(tmp_path):
    """#89's acceptance criterion, end to end through the capability: ownerState.js keys the
    owner's outcomes by entry id, so two entries sharing one means one decision silently
    settles both. Covers the trap in grouping barcode-less rows: a conflict record built from
    `entry_id(family, None)` would give EVERY barcode-less conflict the same id."""
    from collections import Counter
    from src.engine import reconciliation
    rows = [
        # two barcode-less names, each listed twice and disagreeing
        {"barcode": None, "product_name": "כריך טונה", "category": "drive",   "current_stock": 0.0},
        {"barcode": None, "product_name": "כריך טונה", "category": "barista", "current_stock": -96.0},
        {"barcode": None, "product_name": "כריך אבוקדו", "category": "barista", "current_stock": -185.0},
        {"barcode": None, "product_name": "כריך אבוקדו", "category": "barista", "current_stock": -1.0},
        # a barcode-less singleton with negative stock and no identifier
        {"barcode": None, "product_name": "בייגל", "category": "barista", "current_stock": -3.0},
        # a barcoded duplicate that disagrees
        {"barcode": "7290000000024", "product_name": "במבה", "category": "c", "current_stock": -5.0},
        {"barcode": "7290000000024", "product_name": "במבה", "category": "c", "current_stock": 10.0},
    ]
    for r in rows:
        r.setdefault("selling_price", 5.0); r.setdefault("wolt_price", 0.0); r.setdefault("cost_price", 1.0)
    inputs = _load(_rows_silver(tmp_path, rows), tmp_path)
    ids = Counter(e.id for e in reconciliation._hygiene_entries(inputs))
    assert [i for i, n in ids.items() if n > 1] == [], "an id shared by two entries settles both"
    conflicts = [e for e in reconciliation._hygiene_entries(inputs)
                 if e.signal_family == "hygiene.conflicting_duplicate"]
    assert len(conflicts) == 3, "tuna, avocado and bamba each conflict once"


def test_89_a_misaligned_inventory_is_refused_not_silently_joined():
    """The fix joins inventory to products by position, which is correct only because the two
    tables are the same export in the same order (7,674 of 7,674 aligned on the pilot). If a
    future export breaks that, attaching stock by position would publish one product's stock
    on another — the same defect, quieter. So misalignment is an error, not a guess."""
    import pytest
    from src.engine.inputs import _shape_products, MisalignedInventoryError
    prod = [{"barcode": "1", "product_name": "a"}, {"barcode": "2", "product_name": "b"}]
    inv = [{"barcode": "2", "product_name": "b", "current_stock": 1.0},
           {"barcode": "1", "product_name": "a", "current_stock": 2.0}]
    with pytest.raises(MisalignedInventoryError):
        _shape_products(prod, inv, OwnerState.unavailable("x"))
    with pytest.raises(MisalignedInventoryError):
        _shape_products(prod, inv[:1], OwnerState.unavailable("x"))


def test_89_a_missing_inventory_still_reads_as_none_not_zero():
    """A withheld stock table is `None` for every row (ARCH-DRIVER-002). The positional join
    must not turn "no table" into an alignment error or into zero."""
    from src.engine.inputs import _shape_products
    products, _ = _shape_products([{"barcode": "1", "product_name": "a"}], None, OwnerState.unavailable("x"))
    assert products[0]["recorded_stock"] is None
