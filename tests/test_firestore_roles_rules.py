"""The staged role rules say what ADR-029 §4 says, before anyone deploys them.

firestore.roles.rules replaces firestore.rules at the switch-over. There is no emulator in
this repository, so the ruleset is checked as text, statement by statement, the way
scripts/check_firestore_rules.py checks the deployed one. A rules file that let the team
write, or let a role-less account read, would otherwise be found by the owner.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGED = (ROOT / "firestore.roles.rules").read_text(encoding="utf-8")
LIVE = (ROOT / "firestore.rules").read_text(encoding="utf-8")


def _code(text: str) -> str:
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def _statements(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", s.strip()) for s in _code(text).split(";") if "allow" in s]


def _block(text: str, path: str) -> str:
    code = _code(text)
    head = f"match {path}"
    start = code.index(head)
    # The block's brace comes after the path, which has braces of its own ({document=**}).
    depth, i = 0, code.index("{", start + len(head))
    for j in range(i, len(code)):
        depth += {"{": 1, "}": -1}.get(code[j], 0)
        if depth == 0:
            return code[i + 1:j]
    raise AssertionError(f"unterminated block for {path}")


STORE = "/stores/yomyom-kafr-qasim/{document=**}"


def test_it_guards_the_same_pinned_store_as_the_live_rules():
    assert f"match {STORE}" in _code(LIVE)
    assert f"match {STORE}" in _code(STAGED)


def test_both_roles_read_and_nothing_else_does():
    block = _statements(_block(STAGED, STORE))
    reads = [s for s in block if s.startswith("allow read")]
    assert reads == ["allow read: if request.auth != null && request.auth.token.role in ['owner', 'team']"]


def test_only_the_owner_writes():
    block = _statements(_block(STAGED, STORE))
    writes = [s for s in block if s.startswith("allow write")]
    assert writes == ["allow write: if request.auth != null && request.auth.token.role == 'owner'"]


def test_no_statement_grants_access_by_sign_in_alone():
    """The live posture, `if request.auth != null` on its own, is exactly what ADR-029 closes."""
    for statement in _statements(STAGED):
        assert not statement.endswith("if request.auth != null"), statement


def test_everything_else_stays_closed():
    assert "allow read, write: if false" in _statements(_block(STAGED, "/{document=**}"))[0]
