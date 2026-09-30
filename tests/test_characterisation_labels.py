# tests/test_characterisation_labels.py
"""Every characterisation the engine can publish has its label in all three languages.

The card and the capability page render `t(`characterisation.${entry.characterisation}`)`,
and the translator falls back to the key itself. competitor_position has published
`policy_breach_attention` since F3 was built, but no finding reached that tier until #250
reclassified 57 shops (2026-09-29). The next night's artefact carried two, and the owner's
cards showed the raw key in every language. checkpoint2.test.jsx saw it only on the first CI
run after that artefact landed, because a nightly push starts no CI.

This reads the labels from the engine's source, so a missing one fails when the code is
written rather than on the first night the data produces it.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("en", "he", "ar")

# A characterisation no card or capability page asks for, with where it is worded instead.
WORDED_ELSEWHERE = {
    # F8's suggestions render on the Reorder page in its own `reorder.*` wording. The
    # capability is not admitted to Today, so no EntryCard receives one.
    "order_suggestion": "src/pages/ReorderPage.jsx",
}

# `characterisation="x"`, or `characterisation="x" if … else "y"`.
_LITERAL = re.compile(r'characterisation\s*=\s*"([a-z][a-z0-9_]*)"(?:\s+if\s+[^,\n]+?\s+else\s+"([a-z][a-z0-9_]*)")?')


def engine_characterisations() -> set:
    found = set()
    for path in (ROOT / "src" / "engine").glob("*.py"):
        for match in _LITERAL.finditer(path.read_text(encoding="utf-8")):
            found.update(label for label in match.groups() if label)
    return found


def dictionary_labels(language: str) -> set:
    text = (ROOT / "src" / "lib" / "i18n" / "dictionaries" / f"{language}.js").read_text(encoding="utf-8")
    return set(re.findall(r"'characterisation\.([a-zA-Z0-9_]+)'", text))


def test_the_engine_source_is_read():
    """A regex that silently matched nothing would pass everything below."""
    found = engine_characterisations()
    assert {"policy_breach_attention", "policy_breach_review", "confirmed_loss", "market_ran_out"} <= found
    assert len(found) >= 12


def test_every_characterisation_has_a_label_in_every_language():
    needed = engine_characterisations() - set(WORDED_ELSEWHERE)
    for language in LANGUAGES:
        missing = sorted(needed - dictionary_labels(language))
        assert missing == [], f"{language}.js has no label for {missing}: a card would show the raw key"


def test_each_exemption_is_still_published_and_its_page_exists():
    for label, page in WORDED_ELSEWHERE.items():
        assert label in engine_characterisations(), f"{label} is exempted but the engine no longer publishes it"
        assert (ROOT / page).exists()
