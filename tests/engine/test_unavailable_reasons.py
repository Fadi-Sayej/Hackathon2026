# tests/engine/test_unavailable_reasons.py
"""The engine must not emit an unavailable reason the owner has no words for.

`unavailable_reason` is domain vocabulary: the engine decides it, the artefact
carries it unchanged, and only the i18n layer knows what it says to a person. That
split is already how `characterisation`, `capability`, `count` and `evidence` work.

The weakness is that the two halves share no enum — `schemas/dashboard.schema.json`
types the field as a bare string — so a new reason can be added on the Python side
and reach the owner's screen as a raw key. That is not hypothetical: eight of the
nine reasons had no translation at all until #103, and nothing failed.

So this asserts the engine emits nothing outside the vocabulary the dictionaries
carry, and its JS counterpart
(`src/lib/i18n/__tests__/unavailableReason.test.js`) asserts the dictionaries carry
the whole vocabulary. Neither half can move without the other going red.

Found by AST rather than by grep: a literal in a comment or a docstring is not an
emission, and a reason built by string concatenation would be missed by both — the
latter is asserted against directly.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "src" / "engine"
EN_DICT = ROOT / "src" / "lib" / "i18n" / "dictionaries" / "en.js"

# Mirrors ENGINE_REASONS in the JS test. Two lists is one more than ideal; the
# alternative is an enum in the artefact schema, which is an architecture change
# (#103). Until then these two tests are what keep them equal.
#
# `unknown_stock_date` arrived with #102 and is here now. It was left out on this
# branch deliberately, and the merge went exactly as that note predicted: the two
# dictionary edits conflicted, and this test failed on the resolution until the
# reason was added here too. The guard doing its job.
KNOWN = {
    "no_pos_data",
    "no_inventory_data",
    "no_sales_evidence",
    "no_competitor_data",
    "ceiling_degenerate",
    "no_delivery_prices",
    "no_comparable_source",
    "answer_storage_unavailable",
    "capability_error",
    "unknown_stock_date",
}


def _emitted_reasons() -> set[str]:
    """Every string literal passed as the `reason` of CapabilityOutput.unavailable."""
    found: set[str] = set()
    for path in ENGINE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # CapabilityOutput.unavailable only. OwnerState.unavailable carries its
            # own, separate vocabulary (`pull_step_failed`, `mirror_missing`,
            # `no_credentials`…) which DataPage renders selectively rather than as a
            # reason string — a different contract, and not this one.
            if not (isinstance(func, ast.Attribute) and func.attr == "unavailable"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "CapabilityOutput"):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.add(arg.value)
    return found


def _input_reasons() -> set[str]:
    from src.engine.registry import INPUT_REASONS

    return set(INPUT_REASONS.values())


def test_every_reason_the_engine_emits_is_one_the_owner_has_words_for():
    emitted = _emitted_reasons() | _input_reasons()
    # CapabilityOutput.unavailable's positional args include id and spec; only the
    # ones that are actually reasons matter, so compare against KNOWN rather than
    # asserting equality with every literal seen.
    unknown = {r for r in emitted - KNOWN if re.fullmatch(r"[a-z][a-z_]*", r)}
    # Capability ids and spec names also match that shape, so subtract them.
    from src.engine.registry import CAPABILITIES

    unknown -= set(CAPABILITIES)
    unknown -= {"none", "per_sale"}
    assert not unknown, (
        f"the engine can publish {sorted(unknown)}, which no dictionary translates. "
        "Add the copy in all three languages, and to KNOWN here and in "
        "src/lib/i18n/__tests__/unavailableReason.test.js"
    )


def test_every_known_reason_is_translated_in_english():
    """The JS test owns all three languages; this one keeps the Python side honest
    on its own, so a Python-only run still catches the omission."""
    text = EN_DICT.read_text(encoding="utf-8")
    missing = [r for r in sorted(KNOWN) if f"'unavailable.{r}'" not in text]
    assert not missing, f"untranslated: {missing}"


def test_a_reason_is_never_built_by_concatenation():
    """A computed reason would defeat both halves of this pair — neither the AST scan
    nor the dictionary list can see a string that does not exist until runtime."""
    offenders = []
    for path in ENGINE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "unavailable"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "CapabilityOutput"):
                continue
            for arg in node.args:
                if isinstance(arg, (ast.JoinedStr, ast.BinOp)):
                    offenders.append(f"{path.relative_to(ROOT)}:{arg.lineno}")
    assert not offenders, f"reason built at runtime, so it cannot be translated: {offenders}"
