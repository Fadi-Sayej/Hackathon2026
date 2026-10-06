"""Phase 8 Task 8.12: the shelf reader (F12-S1 FR-218 … FR-223; AC-207 … AC-210; ADR-041).

Proven on drawn test shelves (tests/fixtures/shelf_photos/draw.py), with a fake model that answers
from the drawing, roughly, as a model would. They are test fixtures, not a store's data (D-23).
The reader's real proof is its acceptance run on the next store's first photos (FR-223). No test
touches the network (conftest.py refuses it).
"""
from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest
import yaml
from PIL import Image

from src.engine.policy import load_policy
from src.engine.shelf_reader import answer as answer_mod
from src.engine.shelf_reader import identity, measure, reading
from src.engine.store_layout import load_store_layout, merge_readings

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("shelf_draw", ROOT / "tests" / "fixtures" / "shelf_photos" / "draw.py")
draw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(draw)

DAY = "2026-10-10"
POLICY = load_policy()
MEASURED = "measured_by: team, measured_on: 2026-10-01"
STATED = "stated_by: owner\n    stated_on: 2026-10-01\n    recorded_by: team"

# Two shelves of 120 cm: groups of identical packages, gaps of 5 to 15 mm, one and several facings.
UNIT = {"length_cm": 120, "shelves": [
    [{"barcode": "7290001", "width_mm": 75, "facings": 3, "gap_mm": 6}, {"barcode": "7290002", "width_mm": 90, "facings": 2, "gap_mm": 6},
     {"barcode": "7290003", "width_mm": 120, "facings": 2}, {"barcode": "7290004", "width_mm": 200, "facings": 1}],
    [{"barcode": "7290005", "width_mm": 66, "facings": 4, "gap_mm": 5}, {"barcode": "7290006", "width_mm": 180, "facings": 2, "gap_mm": 5},
     {"barcode": "7290007", "width_mm": 85, "facings": 1}]]}


def product(barcode, name, price=9.9, dept="משקאות"):
    return {"barcode": barcode, "product_name": name, "department": dept, "shelf_price": price,
            "cost_price": 5.0, "has_identifier": True}


CATALOGUE = [product(r["barcode"], f"מוצר {r['barcode'][-1]}", 10.0 + int(r["barcode"][-1]))
             for shelf in UNIT["shelves"] for r in shelf] + [product("7290099", "לא נמכר")]
SOLD = [{"barcode": p["barcode"], "day": "2026-10-01", "units": 3.0} for p in CATALOGUE if p["barcode"] != "7290099"]


def tagged(unit, by="code"):
    """The unit with each run's tag: its code, or its name and price."""
    out = json.loads(json.dumps(unit))
    for shelf in out["shelves"]:
        for run in shelf:
            p = next(c for c in CATALOGUE if c["barcode"] == run["barcode"])
            run["tag"] = ({"name": None, "code": p["barcode"], "price": None} if by == "code"
                          else {"name": p["product_name"], "code": None, "price": f"{p['shelf_price']:.2f}"})
    return out


def layout_file(tmp_path, *, length=120, shelves=2):
    shelf = f"      - {{length_cm: {length}, {MEASURED}}}\n"
    path = tmp_path / "store_layout.yaml"
    path.write_text(f"fixtures:\n  מדף שתייה:\n    departments: [משקאות]\n    chilled: false\n    eye_level_shelf: 1\n"
                    f"    {STATED}\n    shelves:\n" + shelf * shelves, encoding="utf-8")
    return path


def photograph(tmp_path, unit, fixture="מדף שתייה"):
    folder = tmp_path / "photos" / DAY / fixture
    folder.mkdir(parents=True, exist_ok=True)
    return draw.draw(folder / "unit.jpg", unit)


def asker(tmp_path, answers, *, key="test-key", ask_missing=True):
    fake = draw.FakeReader(answers)
    return answer_mod.Asker(folder=tmp_path / "sealed", prompt="p", prompt_version="v1", model="m", key=key,
                            transport=fake, policy=POLICY, ask_missing=ask_missing), fake


def run_reading(tmp_path, unit, *, jitter=0.03, seed=1, facings=None, by="code"):
    unit = tagged(unit, by)
    truth = photograph(tmp_path, unit)
    layout = load_store_layout(layout_file(tmp_path), CATALOGUE)
    ask, fake = asker(tmp_path, {"מדף שתייה": draw.answer(truth, jitter=jitter, seed=seed, facings=facings)})
    result = reading.read(day=DAY, photo_root=tmp_path / "photos", layout=layout, products=CATALOGUE,
                          sales_daily=SOLD, sales_monthly=[], policy=POLICY, asker=ask)
    return result, fake


# ── Widths (FR-221, AC-208) ───────────────────────────────────────────────────

@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_the_drawn_shelves_widths_come_back_within_five_millimetres(tmp_path, seed):
    result, _ = run_reading(tmp_path, UNIT, jitter=0.04, seed=seed)
    truth = {r["barcode"]: r["width_mm"] for shelf in UNIT["shelves"] for r in shelf}
    assert result["widths"], result["report"]
    for barcode, width in result["widths"].items():
        assert abs(width - truth[barcode]) <= 5, (barcode, width, truth[barcode])
    # A width the reader could not stand behind is absent, never guessed.
    assert set(result["widths"]) <= set(truth)


def test_a_miscounted_run_has_no_width_and_no_current_facings(tmp_path):
    # The model says four facings where three stand: the photo does not bear the count out.
    result, _ = run_reading(tmp_path, UNIT, facings={(0, 0): 4})
    assert "7290001" not in result["widths"] and "7290001" not in result["current"]
    reasons = {r["why"] for r in result["report"] if r.get("barcode") == "7290001"}
    assert "facing_count_differs" in reasons and "facings_not_confirmed" in reasons


def test_one_facing_called_two_is_caught_too(tmp_path):
    result, _ = run_reading(tmp_path, UNIT, facings={(0, 3): 2})
    assert "7290004" not in result["widths"]


def test_the_runs_must_fit_within_the_shelf_in_order():
    # Pixels on a 1,000 mm shelf 100 px wide: 10 mm a pixel, so the slack is half a pixel.
    assert measure.runs_fit([[0, 10], [12, 30]], (0, 100), 1000, 5)
    assert not measure.runs_fit([[5, 40], [35, 60]], (0, 100), 1000, 5)      # overlapping
    assert not measure.runs_fit([[5, 40], [45, 120]], (0, 100), 1000, 5)     # past the side


def test_a_product_read_twice_differently_has_no_width(tmp_path):
    # The same product on both shelves, at two different widths: which is right is not known.
    unit = json.loads(json.dumps(UNIT))
    unit["shelves"][1][2] = {"barcode": "7290004", "width_mm": 120, "facings": 1}
    result, _ = run_reading(tmp_path, unit)
    assert "7290004" not in result["widths"] and "7290004" not in result["current"]
    assert {"barcode": "7290004", "why": "in_two_places"} in result["report"]


# ── Identity (FR-220, AC-207) ─────────────────────────────────────────────────

def test_identity_is_an_exact_code_or_a_unique_name_at_the_shelf_price():
    pool = identity.candidates(CATALOGUE, SOLD, [], date(2026, 10, 10), 90)
    assert "7290099" not in {p["barcode"] for p in pool}                     # not sold in the window
    assert identity.identify({"code": "7290001"}, pool) == ("7290001", None)
    assert identity.identify({"code": "7290099"}, pool) == (None, "code_unknown")
    named = {"name": "מוצר 2", "price": "12.00"}
    assert identity.identify(named, pool) == ("7290002", None)
    assert identity.identify({**named, "price": "12.50"}, pool) == (None, "price_differs")
    assert identity.identify({**named, "price": None}, pool) == (None, "price_unreadable")
    twins = pool + [product("7290100", "מוצר 2", 12.0)]
    assert identity.identify(named, twins) == (None, "name_names_two")
    assert identity.identify(None, pool) == (None, "no_tag")
    assert identity.identify({"name": " מוצר-2 ", "price": "₪12"}, pool) == ("7290002", None)   # spacing and signs


def test_a_name_on_the_tag_reads_like_a_code(tmp_path):
    result, _ = run_reading(tmp_path, UNIT, by="name")
    assert len(result["widths"]) >= 5


def test_with_no_recent_sale_no_product_can_be_named():
    assert identity.candidates(CATALOGUE, [], [], date(2026, 10, 10), 90) == []


# ── The model: asked once, sealed, reused, never in print mode (FR-219, AC-210) ──

def test_an_answer_is_sealed_and_reused_and_print_mode_never_asks(tmp_path):
    unit = tagged(UNIT)
    truth = photograph(tmp_path, unit)
    photo = tmp_path / "photos" / DAY / "מדף שתייה" / "unit.jpg"
    ask, fake = asker(tmp_path, {"מדף שתייה": draw.answer(truth)})
    assert ask.read(photo, "מדף שתייה", 2)[0] is not None and fake.calls == 1
    again, fake2 = asker(tmp_path, {"מדף שתייה": "never asked"})
    assert again.read(photo, "מדף שתייה", 2)[0] is not None and fake2.calls == 0
    printing, fake3 = asker(tmp_path, {}, ask_missing=False)
    other = tmp_path / "other.jpg"
    Image.new("RGB", (40, 40)).save(other)
    assert printing.read(other, "מדף שתייה", 2) == (None, "not_read") and fake3.calls == 0


def test_without_a_key_nothing_is_asked(tmp_path):
    photograph(tmp_path, tagged(UNIT))
    ask, fake = asker(tmp_path, {}, key=None)
    assert ask.read(tmp_path / "photos" / DAY / "מדף שתייה" / "unit.jpg", "מדף שתייה", 2) == (None, "no_model_key")
    assert fake.calls == 0


def test_a_malformed_answer_is_refused_and_asked_again(tmp_path):
    truth = photograph(tmp_path, tagged(UNIT))
    photo = tmp_path / "photos" / DAY / "מדף שתייה" / "unit.jpg"
    bad, fake = asker(tmp_path, {"מדף שתייה": json.dumps({"problem": None, "shelves": []})})
    assert bad.read(photo, "מדף שתייה", 2) == (None, "shelves_not_matched")
    good, fake2 = asker(tmp_path, {"מדף שתייה": draw.answer(truth)})
    assert good.read(photo, "מדף שתייה", 2)[0] is not None and fake2.calls == 1


@pytest.mark.parametrize("raw, why", [
    ("not json", "not_json"),
    (json.dumps({"problem": "glare across the middle", "shelves": []}), "photo_problem"),
    (json.dumps({"problem": None, "shelves": [{"y_top": 0.5, "y_bottom": 0.2, "left_x": 0, "right_x": 1, "runs": []}]}), "bad_shape"),
    (json.dumps({"problem": None, "shelves": [{"y_top": 0.1, "y_bottom": 0.2, "left_x": 0, "right_x": 1,
                                               "runs": [{"box": [0.1, 0.1, 0.2, 0.2], "facings": 0, "tag": None}]}]}), "bad_shape"),
])
def test_the_answers_shape_is_checked(raw, why):
    assert answer_mod.check(raw, 1) == (None, why)


def test_the_request_carries_the_whole_photo_and_full_resolution_tiles(tmp_path):
    path = tmp_path / "wide.jpg"
    Image.new("RGB", (4000, 1200), (200, 200, 200)).save(path)
    images = answer_mod.images(path, 3)
    assert max(images[0].size) <= answer_mod.API_LONG_EDGE
    assert len(images) == 1 + 3 * 3                       # three shelves, three columns of tiles each
    assert all(max(i.size) <= 1.25 * answer_mod.API_LONG_EDGE for i in images[1:])


# ── Pictures, current facings and the readings file (FR-222, FR-223, AC-209) ──

def test_the_reading_writes_pictures_and_a_file_the_loader_reads(tmp_path):
    result, _ = run_reading(tmp_path, UNIT)
    readings, pictures = tmp_path / "shelf_readings.yaml", tmp_path / "pictures"
    reading.write(result, day=DAY, model="m", prompt="v1", readings_path=readings, pictures_dir=pictures)
    for face in pictures.glob("*.jpg"):
        data = face.read_bytes()
        assert data.startswith(b"\xff\xd8\xff") and len(data) <= 150 * 1024
    layout = load_store_layout(layout_file(tmp_path), CATALOGUE, pictures)
    merged = merge_readings(layout, CATALOGUE, readings_path=readings, acceptance_path=tmp_path / "none.yaml",
                            pictures_dir=pictures, tolerance_mm=5, minimum=20)
    assert merged["reader"]["status"] == "waiting_for_acceptance"
    assert merged["widths"] == {}                                    # no width before the acceptance run
    assert set(merged["pictures"]) == set(result["pictures"]) and merged["current"]
    assert all(c["measured_by"] == "reader" for c in merged["current"].values())
    assert not [r for r in merged["rejected"] if r["kind"] in ("width", "current", "picture")]


def _readings(tmp_path, widths: dict) -> Path:
    path = tmp_path / "shelf_readings.yaml"
    path.write_text(yaml.safe_dump({"reading": {"day": DAY}, "widths": {
        b: {"width_mm": w, "measured_by": "reader", "measured_on": DAY} for b, w in widths.items()}},
        allow_unicode=True), encoding="utf-8")
    return path


def _acceptance(tmp_path, widths: dict) -> Path:
    path = tmp_path / "shelf_reader_acceptance.yaml"
    path.write_text(yaml.safe_dump({"products": {
        b: {"width_mm": w, "measured_by": "team", "measured_on": DAY} for b, w in widths.items()}}), encoding="utf-8")
    return path


def test_widths_are_used_only_after_twenty_hand_readings_all_within_five_millimetres(tmp_path):
    catalogue = [product(f"72{n:011d}", f"p{n}") for n in range(25)]
    layout = load_store_layout(layout_file(tmp_path), catalogue)
    read = {p["barcode"]: 80 for p in catalogue}
    hand = {p["barcode"]: 82 for p in catalogue[:20]}

    def merged(hand_widths):
        return merge_readings(layout, catalogue, readings_path=_readings(tmp_path, read),
                              acceptance_path=_acceptance(tmp_path, hand_widths), tolerance_mm=5, minimum=20)

    accepted = merged(hand)
    assert accepted["reader"]["status"] == "accepted" and len(accepted["widths"]) == 25
    assert accepted["reader"]["acceptance"] == {"listed": 20, "within": 20, "minimum": 20, "tolerance_mm": 5}
    assert merged(dict(list(hand.items())[:19]))["widths"] == {}                    # too few listed
    one_out = {**hand, catalogue[0]["barcode"]: 86}
    assert merged(one_out)["reader"]["status"] == "waiting_for_acceptance"          # one outside ±5 mm
    assert merged(one_out)["widths"] == {}


def test_a_reading_written_by_hand_is_rejected(tmp_path):
    # D-34: no one measures by hand, so the readings file holds the reader's readings only.
    layout = load_store_layout(layout_file(tmp_path), CATALOGUE)
    path = tmp_path / "shelf_readings.yaml"
    path.write_text(yaml.safe_dump({"widths": {"7290001": {"width_mm": 75, "measured_by": "team", "measured_on": DAY}}}),
                    encoding="utf-8")
    merged = merge_readings(layout, CATALOGUE, readings_path=path, acceptance_path=tmp_path / "none.yaml",
                            tolerance_mm=5, minimum=20)
    assert merged["reader"]["widths"] == 0
    assert any(r["kind"] == "width" and "measured_by must be one of ['reader']" in r["reason"] for r in merged["rejected"])


def test_no_readings_file_changes_nothing(tmp_path):
    layout = load_store_layout(layout_file(tmp_path), CATALOGUE)
    merged = merge_readings(layout, CATALOGUE, readings_path=tmp_path / "absent.yaml",
                            acceptance_path=tmp_path / "absent2.yaml", tolerance_mm=5, minimum=20)
    assert merged["reader"]["status"] == "no_readings"
    assert {k: v for k, v in merged.items() if k != "reader"} == layout
