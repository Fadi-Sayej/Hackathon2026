"""Phase 8 Task 8.1: the layout file is validated at load and never repaired (ADR-037).

F12-S1 FR-178 … FR-180, FR-199; AC-184. Each test writes the file it means, so a rejection
is pinned to the one fact that caused it.
"""
from __future__ import annotations

import textwrap

from src.engine.store_layout import load_store_layout

CATALOGUE = [
    {"barcode": "7290001", "department": "drinks"},
    {"barcode": "7290002", "department": "drinks"},
    {"barcode": "7290003", "department": "drinks"},
    {"barcode": "7291001", "department": "snacks"},
    {"barcode": "7291002", "department": "snacks"},
    {"barcode": "7292001", "department": "dairy  products"},   # a doubled space, as the catalogue prints three
]

STATED = "stated_by: owner\n    stated_on: 2026-10-10\n    recorded_by: team"
SHELF = "{length_cm: 100, measured_by: team, measured_on: 2026-10-10}"


def _fixture(name: str, departments: str, *, shelves: int = 2, extra: str = "") -> str:
    shelf_lines = "\n".join(f"      - {SHELF}" for _ in range(shelves))
    return (f"  {name}:\n    departments: {departments}\n    chilled: false\n{extra}"
            f"    {STATED}\n    shelves:\n{shelf_lines}\n")


def _load(tmp_path, body: str) -> dict:
    path = tmp_path / "store_layout.yaml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return load_store_layout(path, CATALOGUE)


def _reasons(out: dict, kind: str) -> dict:
    return {r["key"]: r["reason"] for r in out["rejected"] if r["kind"] == kind}


def test_a_well_formed_file_is_read_whole(tmp_path):
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]", extra="    eye_level_shelf: 2\n") + """\
widths:
  "7290001": {width_mm: 75, measured_by: team, measured_on: 2026-10-10}
current:
  "7290001": {fixture: F1, shelf: 1, facings: 2, measured_by: team, measured_on: 2026-10-11}
rules:
  - {at_least: {barcode: "7290001", facings: 2}, stated_by: owner, stated_on: 2026-10-10, recorded_by: team}
""")
    assert out["rejected"] == []
    f1 = out["fixtures"]["F1"]
    assert f1["departments"] == ["drinks"] and f1["eye_level_shelf"] == 2 and f1["chilled"] is False
    assert [s["shelf"] for s in f1["shelves"]] == [1, 2] and f1["shelves"][0]["length_cm"] == 100
    assert f1["stated_on"] == "2026-10-10" and f1["shelves"][0]["measured_on"] == "2026-10-10"
    assert out["widths"]["7290001"]["width_mm"] == 75
    assert out["current"]["7290001"] == {"fixture": "F1", "shelf": 1, "facings": 2,
                                         "measured_by": "team", "measured_on": "2026-10-11"}
    assert out["rules"][0]["kind"] == "at_least" and out["rules"][0]["facings"] == 2


def test_a_malformed_fixture_is_named_and_the_others_are_used(tmp_path):
    # SCN-167, AC-184: one bad fixture costs only itself.
    bad = "  F2:\n    departments: [snacks]\n    chilled: maybe\n    " + STATED + "\n    shelves:\n      - " + SHELF + "\n"
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]") + bad)
    assert set(out["fixtures"]) == {"F1"}
    assert "chilled must be true or false" in _reasons(out, "fixture")["F2"]


def test_two_eye_level_shelves_are_rejected(tmp_path):
    # F12-S1 §12: one fixture, at most one eye-level shelf. It is one number, never a list.
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]", extra="    eye_level_shelf: [1, 2]\n"))
    assert out["fixtures"] == {} and "eye_level_shelf must name one shelf" in _reasons(out, "fixture")["F1"]


def test_an_eye_level_shelf_the_fixture_does_not_have_is_rejected(tmp_path):
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]", extra="    eye_level_shelf: 3\n"))
    assert "1 to 2" in _reasons(out, "fixture")["F1"]


def test_a_length_or_width_is_a_positive_whole_number_and_never_estimated(tmp_path):
    shelves = "      - {length_cm: 0, measured_by: team, measured_on: 2026-10-10}\n"
    fixture = "  F1:\n    departments: [drinks]\n    chilled: false\n    " + STATED + "\n    shelves:\n" + shelves
    out = _load(tmp_path, "fixtures:\n" + fixture + _fixture("F2", "[snacks]") + """\
widths:
  "7290001": {width_mm: 7.5, measured_by: team, measured_on: 2026-10-10}
  "7290002": {measured_by: team, measured_on: 2026-10-10}
""")
    assert "shelf 1: length_cm must be a whole number" in _reasons(out, "fixture")["F1"]
    widths = _reasons(out, "width")
    assert set(widths) == {"7290001", "7290002"} and out["widths"] == {}


def test_every_fact_carries_its_provenance(tmp_path):
    no_day = "  F1:\n    departments: [drinks]\n    chilled: false\n    stated_by: owner\n    recorded_by: team\n" \
             "    shelves:\n      - " + SHELF + "\n"
    out = _load(tmp_path, "fixtures:\n" + no_day + _fixture("F2", "[snacks]") + """\
widths:
  "7290001": {width_mm: 75, measured_by: someone, measured_on: 2026-10-10}
""")
    assert "stated_on is missing" in _reasons(out, "fixture")["F1"]
    assert "measured_by must be one of" in _reasons(out, "width")["7290001"]


def test_a_barcode_or_department_outside_the_catalogue_is_rejected(tmp_path):
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[dairy products]") + _fixture("F2", "[drinks]") + """\
widths:
  "9999999": {width_mm: 75, measured_by: team, measured_on: 2026-10-10}
rules:
  - {keep_off: {barcode: "9999999", fixture: F2}, stated_by: owner, stated_on: 2026-10-10, recorded_by: team}
""")
    # The catalogue's own spelling is named, never silently matched.
    assert "the catalogue spells it 'dairy  products'" in _reasons(out, "fixture")["F1"]
    assert "no catalogue product" in _reasons(out, "width")["9999999"]
    assert "no catalogue product" in _reasons(out, "rule")["1"]


def test_leading_zeros_are_the_catalogue_s_barcode(tmp_path):
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]") + """\
widths:
  "07290001": {width_mm: 75, measured_by: team, measured_on: 2026-10-10}
""")
    assert out["widths"]["7290001"]["width_mm"] == 75


def test_only_the_five_rules_are_rules(tmp_path):
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]") + """\
rules:
  - {always_first: {barcode: "7290001"}, stated_by: owner, stated_on: 2026-10-10, recorded_by: team}
  - {together: {barcodes: ["7290001"]}, stated_by: owner, stated_on: 2026-10-10, recorded_by: team}
  - {keep_on: {barcode: "7290001", fixture: F9}, stated_by: owner, stated_on: 2026-10-10, recorded_by: team}
  - {together: {department: drinks}, stated_by: owner, stated_on: 2026-10-10, recorded_by: team}
""")
    reasons = _reasons(out, "rule")
    assert set(reasons) == {"1", "2", "3"}
    assert "exactly one of" in reasons["1"] and "two or more barcodes" in reasons["2"]
    assert "no recorded fixture is named 'F9'" in reasons["3"]
    assert [r["kind"] for r in out["rules"]] == ["together"]


def test_a_department_on_two_fixtures_with_no_keep_on_rule_is_rejected_on_both(tmp_path):
    # FR-179: neither fixture holds it, rather than one being guessed.
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks, snacks]") + _fixture("F2", "[drinks]"))
    assert "named on F1, F2 with no keep_on rule" in _reasons(out, "department")["drinks"]
    assert out["fixtures"]["F1"]["departments"] == ["snacks"] and out["fixtures"]["F2"]["departments"] == []


def test_a_split_department_s_unnamed_product_is_rejected_by_name(tmp_path):
    # FR-199: the rules divide it; whatever they leave out is named, never placed by a guess.
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]") + _fixture("F2", "[drinks]") + """\
rules:
  - {keep_on: {barcode: "7290001", fixture: F1}, stated_by: owner, stated_on: 2026-10-10, recorded_by: team}
  - {keep_on: {barcode: "7290002", fixture: F2}, stated_by: owner, stated_on: 2026-10-10, recorded_by: team}
""")
    assert out["assigned"] == {"7290001": "F1", "7290002": "F2"}
    assert set(_reasons(out, "product")) == {"7290003"}
    assert "drinks" in out["fixtures"]["F1"]["departments"]


def test_a_current_placement_must_point_at_a_real_shelf(tmp_path):
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]") + """\
current:
  "7290001": {fixture: F1, shelf: 5, facings: 1, measured_by: team, measured_on: 2026-10-10}
  "7290002": {fixture: F7, shelf: 1, facings: 1, measured_by: team, measured_on: 2026-10-10}
  "7290003": {fixture: F1, shelf: 1, facings: 0, measured_by: team, measured_on: 2026-10-10}
""")
    reasons = _reasons(out, "current")
    assert "shelf must be 1 to 2" in reasons["7290001"] and "F7" in reasons["7290002"]
    # Zero is a statement, "on no shelf today", and FR-205 leaves such a product out itself.
    assert out["current"]["7290003"]["facings"] == 0


def test_an_unreadable_or_empty_file_is_one_named_rejection_and_never_raises(tmp_path):
    assert _load(tmp_path, "fixtures: [unclosed\n")["rejected"][0]["kind"] == "file"
    out = _load(tmp_path, "fixtures: {}\n")
    assert out["fixtures"] == {} and out["rejected"] == [{"kind": "file", "key": None,
                                                          "reason": "the file records no fixture"}]
    out = _load(tmp_path, "")
    assert out["rejected"][0]["reason"] == "the file records no fixture"


def test_an_unknown_key_is_named_rather_than_ignored(tmp_path):
    out = _load(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]", extra="    colour: red\n") + "notes: hi\n")
    assert "unknown key colour" in _reasons(out, "fixture")["F1"]
    assert any("unknown key notes" in r["reason"] for r in out["rejected"] if r["kind"] == "file")


# ── In the run (the boundary) ────────────────────────────────────────────────

from datetime import datetime, timezone  # noqa: E402

DEPTS = {"7290001": "drinks", "7290002": "drinks", "7291001": "snacks"}


def _silver(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    silver = tmp_path / "silver"
    silver.mkdir(parents=True, exist_ok=True)
    prod = [{"barcode": b, "product_name": f"p{b}", "category": d, "selling_price": 4.0, "wolt_price": 0.0,
             "cost_price": 1.0, "_source_file": "inv.csv", "_as_of": "2026-08-02"} for b, d in DEPTS.items()]
    inv = [{"barcode": r["barcode"], "product_name": r["product_name"], "current_stock": 1.0,
            "_source_file": "inv.csv", "_as_of": "2026-08-02"} for r in prod]
    pq.write_table(pa.Table.from_pylist(prod), silver / "products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "inventory.parquet")
    return silver


def _inputs(tmp_path, layout_path, silver=None):
    from helpers import load_inputs_without_market as load_inputs
    from src.engine.policy import load_policy
    from src.owner_state.model import OwnerState
    return load_inputs(policy=load_policy(), owner=OwnerState.unavailable("x"),
                       run_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
                       silver_dir=silver or _silver(tmp_path), signals_dir=tmp_path / "nosig",
                       matches_path=tmp_path / "nomatch.parquet", store_facts_path=tmp_path / "nofacts.yaml",
                       store_layout_path=layout_path)


def _write(folder, body: str):
    path = folder / "store_layout.yaml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_the_inputs_carry_the_layout_checked_against_the_catalogue(tmp_path):
    path = _write(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]") + _fixture("F2", "[bakery]"))
    layout = _inputs(tmp_path, path).store_layout
    assert list(layout["fixtures"]) == ["F1"]
    assert [r["key"] for r in layout["rejected"]] == ["F2"]


def test_a_missing_file_is_the_missing_input_no_store_layout(tmp_path):
    from src.engine.registry import INPUT_REASONS
    assert _inputs(tmp_path, tmp_path / "absent.yaml").store_layout is None
    assert INPUT_REASONS["store_layout"] == "no_store_layout"


def test_a_changed_measurement_changes_the_digest_and_a_rejected_entry_does_not(tmp_path):
    silver = _silver(tmp_path)

    def digest(name, body):
        folder = tmp_path / name
        folder.mkdir()
        return _inputs(tmp_path, _write(folder, body), silver).inputs_digest

    base = "fixtures:\n" + _fixture("F1", "[drinks]")
    width = 'widths:\n  "7290001": {{width_mm: {w}, measured_by: team, measured_on: 2026-10-10}}\n'
    junk = 'widths:\n  "9999999": {width_mm: 70, measured_by: team, measured_on: 2026-10-10}\n'
    assert digest("a", base + width.format(w=75)) == digest("b", base + width.format(w=75))
    assert digest("c", base + width.format(w=75)) != digest("d", base + width.format(w=80))
    assert digest("e", base) == digest("f", base + junk)
    absent = _inputs(tmp_path, tmp_path / "absent.yaml", silver).inputs_digest
    assert absent != digest("g", base)


def test_the_run_names_every_rejected_entry_in_its_steps(tmp_path, monkeypatch):
    """FR-178 / SCN-167: by kind and key, and the run does not degrade for it."""
    import src.engine.run as run_mod
    from src.owner_state.model import OwnerState
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: OwnerState.from_dict({"status": "available", "pulled_at": "t"}))
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None, "monthly_rows": 42})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    path = _write(tmp_path, "fixtures:\n" + _fixture("F1", "[drinks]") + _fixture("F2", "[bakery]"))
    result = run_mod.run_engine(mode="print", capability_runners={}, now=datetime(2026, 10, 12, tzinfo=timezone.utc),
                                silver_dir=_silver(tmp_path), signals_dir=tmp_path / "nosig",
                                matches_path=tmp_path / "nomatch.parquet", daily_sales_dir=tmp_path / "nodaily",
                                store_facts_path=tmp_path / "nofacts.yaml", store_layout_path=path,
                                snapshots_root=tmp_path / "nosnap")
    step = next(s for s in result["steps"] if s["step"] == "store_layout")
    assert step["status"] == "degraded" and "fixture F2" in step["error"] and "F1" not in step["error"]
    assert result["status"] == "ok"
