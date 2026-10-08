"""The units the owner entered in the app, written into the layout file (D-38, ADR-043 Decision 3,
F12-S1 FR-229, AC-216). Test units and departments, not a store's (D-23)."""
from __future__ import annotations

import yaml

from src.engine.store_layout import load_store_layout
from src.owner_state.shelf_units import apply

CATALOGUE = [{"barcode": "7290001", "department": "drinks"}, {"barcode": "7291001", "department": "snacks"}]
TEAM_FILE = """\
fixtures:
  Fridge:
    departments: [drinks]
    chilled: true
    stated_by: owner
    stated_on: 2026-09-01
    recorded_by: team
    shelves:
      - {length_cm: 100, measured_by: team, measured_on: 2026-09-01}
widths:
  "7290001": {width_mm: 75, measured_by: team, measured_on: 2026-09-01}
rules:
  - {at_most: {barcode: "7290001", facings: 2}, stated_by: owner, stated_on: 2026-09-01, recorded_by: team}
"""


def doc(units, saved_at="2026-10-08T09:00:00.000Z"):
    return {"schema": 1, "saved_at": saved_at, "units": units}


DRY = {"name": "Dry", "departments": ["snacks"], "chilled": False, "eye_level_shelf": 2,
       "shelves": [{"length_cm": 120, "height_cm": None}, {"length_cm": 120, "height_cm": 40}]}
FRIDGE_SAME = {"name": "Fridge", "departments": ["drinks"], "chilled": True, "eye_level_shelf": None,
               "shelves": [{"length_cm": 100}]}


def _file(tmp_path, body=TEAM_FILE):
    path = tmp_path / "store_layout.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_a_newer_save_replaces_the_units_and_keeps_the_rest(tmp_path):
    path = _file(tmp_path)
    assert apply(doc([DRY]), path) is None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert list(raw["fixtures"]) == ["Dry"]
    dry = raw["fixtures"]["Dry"]
    assert (dry["recorded_by"], str(dry["stated_on"])) == ("app", "2026-10-08")
    assert dry["shelves"][0] == {"length_cm": 120, "height_cm": None, "measured_by": "owner", "measured_on": "2026-10-08"}
    assert raw["rules"] and raw["widths"] and raw["entered_in_app"] == {"saved_at": "2026-10-08T09:00:00.000Z"}
    layout = load_store_layout(path, CATALOGUE)
    assert not layout["rejected"], layout["rejected"]
    assert layout["fixtures"]["Dry"]["shelves"][1]["height_cm"] == 40 and layout["entered_in_app"] == "2026-10-08T09:00:00.000Z"


def test_an_unchanged_unit_keeps_its_entry_and_dates(tmp_path):
    path = _file(tmp_path)
    assert apply(doc([FRIDGE_SAME, DRY]), path) is None
    fridge = yaml.safe_load(path.read_text(encoding="utf-8"))["fixtures"]["Fridge"]
    assert fridge["recorded_by"] == "team" and str(fridge["stated_on"]) == "2026-09-01"


def test_a_changed_unit_carries_the_day_of_the_change(tmp_path):
    path = _file(tmp_path)
    taller = {**FRIDGE_SAME, "shelves": [{"length_cm": 100, "height_cm": 35}]}
    apply(doc([taller]), path)
    fridge = yaml.safe_load(path.read_text(encoding="utf-8"))["fixtures"]["Fridge"]
    assert fridge["recorded_by"] == "app" and fridge["shelves"][0]["height_cm"] == 35


def test_a_save_is_taken_once_so_a_later_team_correction_stands(tmp_path):
    path = _file(tmp_path)
    apply(doc([DRY]), path)
    corrected = path.read_text(encoding="utf-8").replace("length_cm: 120", "length_cm: 118", 1)
    path.write_text(corrected, encoding="utf-8")
    assert apply(doc([DRY]), path) == "already_taken"
    assert path.read_text(encoding="utf-8") == corrected
    assert apply(doc([DRY], saved_at="2026-10-09T08:00:00.000Z"), path) is None


def test_nothing_saved_or_an_unknown_shape_leaves_the_file(tmp_path):
    path = _file(tmp_path)
    assert apply(None, path) == "nothing_saved"
    assert apply({"schema": 2, "saved_at": "x", "units": []}, path) == "unknown_schema"
    assert path.read_text(encoding="utf-8") == TEAM_FILE


def test_a_unit_named_like_a_number_is_matched_by_its_name(tmp_path):
    path = _file(tmp_path, TEAM_FILE.replace("  Fridge:", "  1:"))
    apply(doc([{**FRIDGE_SAME, "name": "1"}]), path)
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["fixtures"]["1"]["recorded_by"] == "team"


def test_the_first_save_writes_a_file_where_there_was_none(tmp_path):
    path = tmp_path / "store_layout.yaml"
    assert apply(doc([DRY]), path) is None
    assert list(load_store_layout(path, CATALOGUE)["fixtures"]) == ["Dry"]
