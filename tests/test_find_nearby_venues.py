# tests/test_find_nearby_venues.py
"""ADR-036 §4: a new store's nearby venues are found from its location, then confirmed by a
person.

YomYom's list was built by hand once, and nothing could build another store's. The finder
reads the delivery platform's public retail listing around the store and writes candidates
to a review file. It never writes configs/delivery_targets.yaml, and it never guesses a
venue's format: it only says whether configs/store_types.yaml already classifies it.

The fixture is the live listing around YomYom, captured once on 2026-09-30 and trimmed to
the fields the finder reads. Nothing in it is invented.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.external.venue_discovery import haversine_km, nearby, venues_from_listing  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "venue_discovery" / "wolt_retail_2026-09-30.json"
HERE = (32.1091501, 34.9624392)                     # where the fixture was captured from
VICTORY_PARK_AFEK = "65af9c58e895c470fe3eb763"      # 0.21 km away in the fixture
SUPER_ALONIT_EINAT = "689d9d1ea1357c9968d6850f"     # 2.84 km
BINGO = "6846c439813000ebeb979157"                  # 0.86 km, listed as general merchandise


@pytest.fixture(scope="module")
def listing():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_distance_is_measured_on_the_globe():
    # One degree of latitude on a sphere of radius 6,371 km is pi * 6371 / 180 km.
    assert haversine_km(0, 0, 1, 0) == pytest.approx(3.141592653589793 * 6371 / 180, rel=1e-9)
    assert haversine_km(32, 35, 33, 35) == pytest.approx(3.141592653589793 * 6371 / 180, rel=1e-9)
    assert haversine_km(*HERE, *HERE) == 0


def test_every_venue_in_the_listing_is_read(listing):
    venues = venues_from_listing(listing)
    assert len(venues) == 394
    victory = next(v for v in venues if v.id == VICTORY_PARK_AFEK)
    assert victory.slug == "victory-rosh-haayin-park-afek"
    assert victory.product_line == "grocery"
    assert victory.url == "https://wolt.com/en/isr/petah-tikva/venue/victory-rosh-haayin-park-afek"


def test_grocery_venues_within_the_radius_nearest_first(listing):
    found = nearby(listing, lat=HERE[0], lon=HERE[1], radius_km=5)
    assert found[0]["id"] == VICTORY_PARK_AFEK
    assert found[0]["distance_km"] == pytest.approx(0.21, abs=0.01)
    assert all(v["distance_km"] <= 5 for v in found)
    assert [v["distance_km"] for v in found] == sorted(v["distance_km"] for v in found)
    assert {v["product_line"] for v in found} == {"grocery"}
    assert len(found) == 35


def test_the_radius_is_the_stores_own(listing):
    near = {v["id"] for v in nearby(listing, lat=HERE[0], lon=HERE[1], radius_km=1)}
    assert VICTORY_PARK_AFEK in near and SUPER_ALONIT_EINAT not in near


def test_a_configured_venue_is_listed_whatever_its_line(listing):
    """Bingo is configured for YomYom, and the listing files it as general merchandise."""
    found = nearby(listing, lat=HERE[0], lon=HERE[1], radius_km=5, configured_ids={BINGO})
    bingo = next(v for v in found if v["id"] == BINGO)
    assert bingo["configured"] is True and bingo["product_line"] == "general_merchandise"


def test_it_says_what_is_classified_and_never_guesses_a_format(listing):
    found = nearby(listing, lat=HERE[0], lon=HERE[1], radius_km=5,
                   classified={VICTORY_PARK_AFEK: "supermarket"})
    by_id = {v["id"]: v for v in found}
    assert by_id[VICTORY_PARK_AFEK]["format"] == "supermarket"
    assert by_id[SUPER_ALONIT_EINAT]["format"] is None


def test_the_script_writes_only_its_review_file(tmp_path):
    targets = ROOT / "configs" / "delivery_targets.yaml"
    before = hashlib.sha256(targets.read_bytes()).hexdigest()
    out = tmp_path / "review.json"
    result = subprocess.run([sys.executable, "scripts/find_nearby_venues.py", "--listing", str(FIXTURE),
                             "--lat", str(HERE[0]), "--lon", str(HERE[1]), "--out", str(out)],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    review = json.loads(out.read_text(encoding="utf-8"))
    assert review["radius_km"] and review["venues"]
    assert hashlib.sha256(targets.read_bytes()).hexdigest() == before
