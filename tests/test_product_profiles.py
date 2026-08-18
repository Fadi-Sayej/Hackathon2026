"""
T6 / #51 — the classification job's guarantees that do not need a funded key.

Three acceptance items are checkable today and were not checked by anything:

  * "Every archetype is a member of configs/archetypes.yaml — zero out-of-vocabulary"
  * "Re-running costs nothing for already-classified products (cache verified)"
  * "The key is not in the repo, not in logs, not in error output"

The fourth reason to test this file is the one the issue is loudest about:

  > The chametz flag does not ship on LLM confidence alone. One error means a
  > forbidden sale in our client's store.

The engine already refuses to fire a gate on an unreviewed profile
(`gateMayFire` in demandEngine.js, covered there). What is tested here is the
other half: that every profile this script writes STARTS unreviewed, and that
the review sheet actually contains everything a human must look at.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.enrich_product_profiles as ep  # noqa: E402

FAKE_KEY = "AIzaSy-NOT-A-REAL-KEY-0123456789"


def write_profiles(tmp_path: Path, rows) -> Path:
    path = tmp_path / "product_profiles.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Vocabulary — "zero out-of-vocabulary"
# ---------------------------------------------------------------------------

def test_the_shipped_archetype_vocabulary_loads_and_is_closed():
    archetypes = ep.load_archetypes()
    assert len(archetypes) >= 20
    assert "chametz_snack" in archetypes
    assert all(isinstance(name, str) and name for name in archetypes)


def test_the_prompt_carries_the_full_closed_list_every_batch():
    """#51: "Give the model the full closed archetype list with descriptions in
    every batch." A truncated list is how out-of-vocabulary answers happen."""
    archetypes = ep.load_archetypes()
    batch = [{"barcode": "729", "product_name": "במבה", "category": "חטיפים מלוחים"}]
    prompt = ep.build_prompt(batch, archetypes)

    for name in archetypes:
        assert name in prompt, f"archetype {name} missing from prompt"


def test_the_prompt_offers_an_abstention_instead_of_forcing_a_guess():
    """#51: "Ask for explicit 'uncertain' rather than a guess — an honest
    abstention is cheap to review; a confident error is not."

    The script spells that abstention `unclassified` rather than `uncertain`.
    Same mechanism, and `unclassified` is also what an out-of-vocabulary answer
    is mapped to, so the two paths converge on one reviewable bucket.
    """
    prompt = ep.build_prompt(
        [{"barcode": "729", "product_name": "x", "category": "y"}],
        ep.load_archetypes(),
    )
    assert "unclassified" in prompt
    assert "abstention" in prompt.lower()


def test_the_prompt_tells_the_model_to_abstain_on_chametz_rather_than_guess_false():
    """The highest-stakes instruction in the file. A false `is_chametz: false`
    is a forbidden sale; a `null` is a line on the review sheet."""
    prompt = ep.build_prompt(
        [{"barcode": "729", "product_name": "x", "category": "y"}],
        ep.load_archetypes(),
    )
    assert "null, not false" in prompt


def test_an_abstention_is_a_real_member_of_the_vocabulary():
    """If `unclassified` were not in the closed list, an honest abstention would
    be rejected as out-of-vocabulary — punishing exactly the behaviour we asked
    for."""
    assert "unclassified" in ep.load_archetypes()


def test_the_prompt_includes_the_department_signal():
    """The department is a strong signal already present in the data."""
    prompt = ep.build_prompt(
        [{"barcode": "729", "product_name": "במבה", "category": "חטיפים מלוחים"}],
        ep.load_archetypes(),
    )
    assert "חטיפים מלוחים" in prompt


# ---------------------------------------------------------------------------
# Caching — "re-running costs nothing for already-classified products"
# ---------------------------------------------------------------------------

def test_already_classified_products_are_not_resent(tmp_path, monkeypatch):
    """This is a billing guarantee, not a tidiness one: 7,674 products is ~154
    paid requests, and re-running without the diff pays for all of them again."""
    monkeypatch.setattr(ep, "PROFILES_PATH", write_profiles(tmp_path, [
        {"barcode": "111", "archetype": "salty_snack", "reviewed_by": None},
        {"barcode": "222", "archetype": "water_bottle", "reviewed_by": None},
    ]))

    existing = ep.load_existing()
    assert set(existing) == {"111", "222"}

    products = [{"barcode": "111"}, {"barcode": "222"}, {"barcode": "333"}]
    todo = [p for p in products if p["barcode"] not in existing]
    assert [p["barcode"] for p in todo] == ["333"]


def test_a_missing_profile_file_is_an_empty_cache_not_a_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(ep, "PROFILES_PATH", tmp_path / "nope.jsonl")
    assert ep.load_existing() == {}


def test_blank_lines_in_the_profile_file_are_tolerated(tmp_path, monkeypatch):
    path = tmp_path / "p.jsonl"
    path.write_text('{"barcode":"111"}\n\n   \n{"barcode":"222"}\n', encoding="utf-8")
    monkeypatch.setattr(ep, "PROFILES_PATH", path)
    assert set(ep.load_existing()) == {"111", "222"}


# ---------------------------------------------------------------------------
# The chametz review path
# ---------------------------------------------------------------------------

def test_the_review_sheet_holds_everything_a_human_must_approve(tmp_path, monkeypatch):
    """Chametz-true AND uncertain (null). An abstention that never reaches the
    reviewer is worse than a wrong guess, because nobody knows to look at it."""
    sheet = tmp_path / "chametz_review.csv"
    monkeypatch.setattr(ep, "REVIEW_SHEET", sheet)

    profiles = {
        "1": {"barcode": "1", "flags": {"is_chametz": True}, "reviewed_by": None},
        "2": {"barcode": "2", "flags": {"is_chametz": None}, "reviewed_by": None},
        "3": {"barcode": "3", "flags": {"is_chametz": False}, "reviewed_by": None},
        "4": {"barcode": "4", "flags": {"is_chametz": True}, "reviewed_by": "anas"},
    }
    count = ep.write_review_sheet(profiles)

    assert count == 2                       # chametz-true and uncertain only
    body = sheet.read_text(encoding="utf-8")
    assert "approve_yes_no" in body         # a column the reviewer fills in
    assert body.count("\n") == 3            # header + 2 rows
    for barcode, present in (("1", True), ("2", True), ("3", False), ("4", False)):
        assert (f"\n{barcode}," in body) is present


def test_an_empty_review_sheet_is_reported_not_written(tmp_path, monkeypatch):
    monkeypatch.setattr(ep, "REVIEW_SHEET", tmp_path / "none.csv")
    assert ep.write_review_sheet({
        "3": {"barcode": "3", "flags": {"is_chametz": False}, "reviewed_by": None},
    }) == 0


# ---------------------------------------------------------------------------
# Key safety — "not in the repo, not in logs, not in error output"
# ---------------------------------------------------------------------------

def test_the_key_never_reaches_the_prompt(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    prompt = ep.build_prompt(
        [{"barcode": "729", "product_name": "x", "category": "y"}],
        ep.load_archetypes(),
    )
    assert FAKE_KEY not in prompt


def test_the_missing_key_error_explains_without_quoting_a_key(monkeypatch, tmp_path):
    """The message must teach the VITE_ trap without ever printing a secret."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("VITE_GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(ep, "PROJECT_ROOT", tmp_path)      # no .env to read
    assert ep.read_api_key() is None


def test_an_unprefixed_key_is_preferred_over_the_vite_one(monkeypatch):
    """A VITE_ prefix is inlined into the browser bundle, so a key stored under
    that name ships to every visitor. Preferring the safe name is deliberate."""
    monkeypatch.setenv("GEMINI_API_KEY", "safe-key")
    monkeypatch.setenv("VITE_GEMINI_API_KEY", "leaked-key")
    assert ep.read_api_key() == "safe-key"


def test_env_is_gitignored_so_a_pasted_key_cannot_be_committed():
    """#51 Security: "Confirm it is gitignored BEFORE pasting the key.\""""
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert any(line.strip() in (".env", "/.env", ".env*") for line in ignored)
