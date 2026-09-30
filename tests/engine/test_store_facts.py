# tests/engine/test_store_facts.py
"""Phase 5 Task 5.3: the store owner's statements per department (ADR-033, F8-S1 FR-157)."""
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from src.engine.store_facts import DEFAULT_PATH, load_store_facts

DEPARTMENTS = {"משקאות", "מאפים", "מוצרי  אלקטרונים"}      # the last, as the catalogue prints it
PROVENANCE = "    stated_by: owner\n    stated_on: 2026-10-01\n    recorded_by: team\n"


def _file(tmp_path, body: str) -> Path:
    path = tmp_path / "store_facts.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _one(tmp_path, entry: str, department: str = "משקאות", provenance: str = PROVENANCE):
    return load_store_facts(_file(tmp_path, f"departments:\n  {department}:\n{entry}{provenance}"), DEPARTMENTS)


# ── The committed file ───────────────────────────────────────────────────────

def test_the_committed_file_states_nothing():
    """OQ-903 and OQ-908 are open: no schedule and no shelf life has been stated yet."""
    assert load_store_facts(DEFAULT_PATH, DEPARTMENTS) == {"facts": {}, "rejected": []}


def test_an_empty_file_gives_no_facts_and_no_error(tmp_path):
    assert load_store_facts(_file(tmp_path, ""), DEPARTMENTS) == {"facts": {}, "rejected": []}
    assert load_store_facts(_file(tmp_path, "departments: {}\n"), DEPARTMENTS) == {"facts": {}, "rejected": []}


# ── Every form parses ────────────────────────────────────────────────────────

@pytest.mark.parametrize("schedule,expected", [
    ("weekdays: [sun, wed]", {"form": "weekdays", "weekdays": ["sun", "wed"]}),
    ("weekdays: [wed, sun]", {"form": "weekdays", "weekdays": ["sun", "wed"]}),
    ("weekdays: [sun]", {"form": "weekdays", "weekdays": ["sun"]}),
    ("weekdays: [sun, mon, tue, wed, thu, fri, sat]",
     {"form": "weekdays", "weekdays": ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]}),
    ("{every_days: 14, from: 2026-10-04}", {"form": "every_days", "every_days": 14, "from": "2026-10-04"}),
    ("no_fixed_days: true", {"form": "no_fixed_days"}),
])
def test_every_schedule_form_parses(tmp_path, schedule, expected):
    entry = f"    order_schedule: {schedule if schedule.startswith('{') else '{' + schedule + '}'}\n"
    out = _one(tmp_path, entry)
    assert out["rejected"] == []
    assert out["facts"]["משקאות"]["order_schedule"] == expected


@pytest.mark.parametrize("shelf,expected", [
    ("shelf_life_days: 7", {"days": 7}),
    # 0 records "keeps less than a day": it gives no quantity, but it is a statement (FR-151).
    ("shelf_life_days: 0", {"days": 0}),
    ("does_not_spoil: true", {"does_not_spoil": True}),
])
def test_every_shelf_life_form_parses(tmp_path, shelf, expected):
    out = _one(tmp_path, f"    {shelf}\n")
    assert out["rejected"] == []
    assert out["facts"]["משקאות"]["shelf_life"] == expected


def test_a_fact_left_unstated_is_absent_not_defaulted(tmp_path):
    """"I don't know" leaves a fact unstated (FR-157): a schedule alone has no shelf life."""
    out = _one(tmp_path, "    order_schedule: {weekdays: [sun]}\n")
    assert out["facts"]["משקאות"]["shelf_life"] is None
    assert "מאפים" not in out["facts"]


def test_every_fact_keeps_when_he_stated_it(tmp_path):
    """ADR-033 Decision 3: published with its date, so he can see what he said and when."""
    out = _one(tmp_path, "    order_schedule: {weekdays: [sun]}\n    shelf_life_days: 3\n")
    fact = out["facts"]["משקאות"]
    assert (fact["stated_by"], fact["stated_on"], fact["recorded_by"]) == ("owner", "2026-10-01", "team")


# ── Rejected, reported, never repaired ───────────────────────────────────────

@pytest.mark.parametrize("entry,reason", [
    ("    shelf_life_days: -1\n", "shelf_life_days"),
    ("    shelf_life_days: 2.5\n", "shelf_life_days"),
    ("    shelf_life_days: true\n", "shelf_life_days"),
    ("    shelf_life_days: 3\n    does_not_spoil: true\n", "both"),
    ("    does_not_spoil: false\n", "does_not_spoil"),
    ("    order_schedule: {weekdays: [sun], no_fixed_days: true}\n", "order_schedule"),
    ("    order_schedule: {weekdays: [sun, funday]}\n", "order_schedule"),
    ("    order_schedule: {weekdays: []}\n", "order_schedule"),
    ("    order_schedule: {weekdays: [sun, sun]}\n", "order_schedule"),
    ("    order_schedule: {every_days: 14}\n", "order_schedule"),
    ("    order_schedule: {every_days: 0, from: 2026-10-04}\n", "order_schedule"),
    ("    order_schedule: {every_days: 14, from: someday}\n", "order_schedule"),
    ("    order_schedule: {no_fixed_days: false}\n", "order_schedule"),
    ("    order_schedule: sundays\n", "order_schedule"),
    ("    shelf_life: 3\n", "shelf_life"),                       # a misspelt key is not ignored
    ("", "states nothing"),
])
def test_a_malformed_entry_is_rejected_and_reported(tmp_path, entry, reason):
    out = _one(tmp_path, entry)
    assert out["facts"] == {}
    assert len(out["rejected"]) == 1 and out["rejected"][0]["department"] == "משקאות"
    assert reason in out["rejected"][0]["reason"]


@pytest.mark.parametrize("provenance", [
    "",
    "    stated_by: owner\n    recorded_by: team\n",                          # no date
    "    stated_by: manager\n    stated_on: 2026-10-01\n    recorded_by: team\n",
    "    stated_by: owner\n    stated_on: 2026-10-01\n",                      # no recorder
    "    stated_by: owner\n    stated_on: 2026-10-01T09:00:00\n    recorded_by: team\n",
])
def test_an_entry_without_its_provenance_is_rejected(tmp_path, provenance):
    out = _one(tmp_path, "    shelf_life_days: 3\n", provenance=provenance)
    assert out["facts"] == {} and len(out["rejected"]) == 1


def test_an_unknown_department_is_rejected(tmp_path):
    out = _one(tmp_path, "    shelf_life_days: 3\n", department="ירקות")
    assert out["facts"] == {}
    assert out["rejected"] == [{"department": "ירקות", "reason": "no catalogue department has this name"}]


def test_a_department_spaced_differently_is_rejected_and_the_catalogue_spelling_named(tmp_path):
    """Matched exactly, never repaired. The catalogue prints two spaces here; the reason
    says so, because the difference is invisible when reading the file."""
    out = _one(tmp_path, "    shelf_life_days: 3\n", department="מוצרי אלקטרונים")
    assert out["facts"] == {}
    assert "'מוצרי  אלקטרונים'" in out["rejected"][0]["reason"]


def test_one_bad_entry_does_not_cost_the_others(tmp_path):
    body = ("departments:\n  משקאות:\n    shelf_life_days: -1\n" + PROVENANCE
            + "  מאפים:\n    shelf_life_days: 2\n" + PROVENANCE)
    out = load_store_facts(_file(tmp_path, body), DEPARTMENTS)
    assert list(out["facts"]) == ["מאפים"]
    assert [r["department"] for r in out["rejected"]] == ["משקאות"]


@pytest.mark.parametrize("body", ["departments: [a, b]\n", "just text\n", "departments:\n  x: [\n", "- 1\n"])
def test_an_unreadable_file_is_one_rejection_not_an_exception(tmp_path, body):
    """A typo in this file must not take the whole run down with it: load_inputs would
    raise, and every capability would lose its artefact (SPEC-002 §11)."""
    out = load_store_facts(_file(tmp_path, body), DEPARTMENTS)
    assert out["facts"] == {}
    assert len(out["rejected"]) == 1 and out["rejected"][0]["department"] is None


# ── In the run (the boundary) ────────────────────────────────────────────────

def _silver_with(tmp_path, departments):
    import pyarrow as pa
    import pyarrow.parquet as pq
    silver = tmp_path / "silver"; silver.mkdir(parents=True, exist_ok=True)
    prod = [{"barcode": f"{i:04d}", "product_name": f"p{i}", "category": d, "selling_price": 4.0,
             "wolt_price": 0.0, "cost_price": 1.0, "_source_file": "inv.csv", "_as_of": "2026-08-02"}
            for i, d in enumerate(sorted(departments))]
    inv = [{"barcode": r["barcode"], "product_name": r["product_name"], "current_stock": 1.0,
            "_source_file": "inv.csv", "_as_of": "2026-08-02"} for r in prod]
    pq.write_table(pa.Table.from_pylist(prod), silver / "products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "inventory.parquet")
    return silver


def _inputs(tmp_path, facts_path, silver=None):
    from helpers import load_inputs_without_market as load_inputs
    from src.engine.policy import load_policy
    from src.owner_state.model import OwnerState
    return load_inputs(policy=load_policy(), owner=OwnerState.unavailable("x"),
                       run_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
                       silver_dir=silver or _silver_with(tmp_path, DEPARTMENTS),
                       signals_dir=tmp_path / "nosig", matches_path=tmp_path / "nomatch.parquet",
                       store_facts_path=facts_path)


def test_the_inputs_carry_the_facts_checked_against_the_catalogue(tmp_path):
    path = _file(tmp_path, "departments:\n  מאפים:\n    shelf_life_days: 2\n" + PROVENANCE
                 + "  ירקות:\n    shelf_life_days: 5\n" + PROVENANCE)
    facts = _inputs(tmp_path, path).store_facts
    assert list(facts["facts"]) == ["מאפים"]
    assert [r["department"] for r in facts["rejected"]] == ["ירקות"]


def test_a_missing_file_is_a_missing_input(tmp_path):
    assert _inputs(tmp_path, tmp_path / "absent.yaml").store_facts is None


def test_a_changed_fact_changes_the_digest(tmp_path):
    silver = _silver_with(tmp_path, DEPARTMENTS)
    entry = "departments:\n  מאפים:\n    shelf_life_days: {n}\n" + PROVENANCE

    def digest(name, n):
        folder = tmp_path / name; folder.mkdir()
        return _inputs(tmp_path, _file(folder, entry.format(n=n)), silver).inputs_digest

    assert digest("a", 2) == digest("b", 2)
    assert digest("c", 2) != digest("d", 3)


def test_the_run_names_every_rejected_entry_in_its_steps(tmp_path, monkeypatch):
    """ADR-033 Decision 2. A rejected entry is a department with no facts, and F8 says so per
    department; the run does not degrade for it."""
    import src.engine.run as run_mod
    from src.owner_state.model import OwnerState
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: OwnerState.from_dict({"status": "available", "pulled_at": "t"}))
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None, "monthly_rows": 42})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    path = _file(tmp_path, "departments:\n  מאפים:\n    shelf_life_days: 2\n" + PROVENANCE
                 + "  ירקות:\n    shelf_life_days: 5\n" + PROVENANCE)
    result = run_mod.run_engine(mode="print", capability_runners={}, now=datetime(2026, 10, 2, tzinfo=timezone.utc),
                                silver_dir=_silver_with(tmp_path, DEPARTMENTS), signals_dir=tmp_path / "nosig",
                                matches_path=tmp_path / "nomatch.parquet", daily_sales_dir=tmp_path / "nodaily",
                                store_facts_path=path, snapshots_root=tmp_path / "nosnap")
    step = next(s for s in result["steps"] if s["step"] == "store_facts")
    assert step["status"] == "degraded" and "ירקות" in step["error"] and "מאפים" not in step["error"]
    assert result["status"] == "ok"


def test_the_run_reads_the_committed_file_by_default_and_rejects_nothing(tmp_path, monkeypatch):
    import src.engine.run as run_mod
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    result = run_mod.run_engine(mode="print", capability_runners={}, now=datetime(2026, 10, 2, tzinfo=timezone.utc),
                                silver_dir=_silver_with(tmp_path, DEPARTMENTS), signals_dir=tmp_path / "nosig",
                                matches_path=tmp_path / "nomatch.parquet", daily_sales_dir=tmp_path / "nodaily",
                                sales_dir=tmp_path / "nosales", snapshots_root=tmp_path / "nosnap")
    step = next(s for s in result["steps"] if s["step"] == "store_facts")
    assert step == {**step, "status": "ok", "error": None}
