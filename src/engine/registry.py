# src/engine/registry.py
"""The complete capability list: what each needs, and what each may publish.

A capability is the smallest unit that can independently become unavailable (ADR-014).
That is why `hygiene` is here and not a characterisation inside `reconciliation`: the
inventory CSV always arrives, the seven monthly sales reports may not, so the two fail
on different days. Everything else the word "capability" does — a badge, a page, a
precedence slot, a value policy — follows this unit; none of them defines it.

`status` is derived from `requires` (§11.2), so SPEC-002 §11 — detection unavailable,
hygiene unaffected — is computed from two lists rather than written by hand."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass(frozen=True)
class CapabilitySpec:
    id: str
    spec: str                  # many-to-one: SPEC-002 yields reconciliation AND hygiene
    value_policy: str          # 'per_sale' | 'none'
    admitted: bool             # may its entries reach the daily surface?
    ordering_key: str          # name of the per-capability ordering key
    requires: Tuple[str, ...]  # EngineInputs fields it cannot compute without, most fundamental first
    # The first nightly that can publish it (YYYY-MM-DD), for a capability registered after the
    # nightly began committing the artefact. The committed dashboard.json is regenerated only
    # by the nightly, so it lacks a new id until then; scripts/check_deploy_data.py reads an
    # artefact generated before this date as expected to lack it, and one from this date on
    # as broken. None: published since the registry began. The publisher ignores it: a real
    # run publishes every registered id, whatever this says.
    published_from: Optional[str] = None


CAPABILITIES = {
    "price_consistency":   CapabilitySpec("price_consistency",   "SPEC-001", "per_sale", True,  "loss_per_sale",
                                          ("products",)),
    "reconciliation":      CapabilitySpec("reconciliation",      "SPEC-002", "none",     True,  "gap_ratio",
                                          ("products", "inventory", "sales_summary", "window")),
    "hygiene":             CapabilitySpec("hygiene",             "SPEC-002", "none",     True,  "hygiene_order",
                                          ("products", "inventory")),
    "competitor_position": CapabilitySpec("competitor_position", "SPEC-003", "none",     True,  "premium_pct",
                                          ("products", "observations", "matches")),
    "catalogue_lifecycle": CapabilitySpec("catalogue_lifecycle", "SPEC-004", "none",     True,  "unit_cost",
                                          ("products", "inventory", "sales_summary", "window")),
    "owner_questions":     CapabilitySpec("owner_questions",     "SPEC-005", "none",     False, "expected_value",
                                          ("products",)),
    "margin_below_cost":   CapabilitySpec("margin_below_cost",   "UNSPECIFIED", "per_sale", False, "loss_per_sale",
                                          ("products",)),
    # F8 (V2). A fact the quantity reads, never an entry: no value, never admitted (ADR-031).
    "market_running_out":  CapabilitySpec("market_running_out",  "F8-S1",    "none",     False, "days_absent",
                                          ("running_out",), published_from="2026-09-27"),
    # F8 (V2). The model's picks, checked and sealed; the quantity reads them (ADR-032, ADR-035).
    "market_boost":        CapabilitySpec("market_boost",        "F8-S1",    "none",     False, "boost_pct",
                                          ("running_out", "boost_picks"), published_from="2026-09-27"),
}

# The reason belongs to the missing input, not to the capability: catalogue_lifecycle with
# no POS file is 'no_pos_data'; the same capability with no monthly reports is
# 'no_sales_evidence'. Rule-level reasons ('ceiling_degenerate', 'answer_storage_unavailable',
# 'no_delivery_prices', 'no_comparable_source') are published by the modules themselves.
INPUT_REASONS = {
    "products": "no_pos_data",
    "inventory": "no_inventory_data",
    "sales_summary": "no_sales_evidence",
    "window": "no_sales_evidence",
    "observations": "no_competitor_data",
    "matches": "no_competitor_data",
    # ADR-031 Decision 5: the market was not observed on enough of the last fortnight.
    "running_out": "market_signal_thin",
    # ADR-035: no sealed picks for the day. A live run with a key always seals a manifest,
    # so the only live night without one is a night with no key.
    "boost_picks": "no_boost_key",
}

# Admitted capabilities that may never carry money (D-1). Their precedence for the three
# reserved places lives in configs/policy.yaml (surface.unvalued_order, OQ-601), not here:
# it is a product decision and must move without a code change.
UNVALUED_CAPABILITIES = tuple(c.id for c in CAPABILITIES.values() if c.admitted and c.value_policy == "none")


def value_policy_for(capability_id: str) -> str:
    return CAPABILITIES[capability_id].value_policy


def derive_status(capability_id: str, inputs: Any) -> Tuple[str, Optional[str]]:
    """The only producer of a capability's status (design §11.2, ADR-014).

    This is the only producer of an *input-level* status. A capability may still publish a
    **rule-level** unavailability of its own — `no_delivery_prices` (no product is price-paired),
    `no_comparable_source` (every source was format-gated away), `answer_storage_unavailable`
    (Firestore is unreachable, SPEC-005 §11), `ceiling_degenerate` — because those are facts about
    the data's content, not about which files landed, and no `requires` list can express them.
    The rule is: a capability may make itself *more* unavailable, never more available.

    A missing input is None — never an empty frame."""
    for key in CAPABILITIES[capability_id].requires:
        if getattr(inputs, key, None) is None:
            return "unavailable", INPUT_REASONS[key]
    return "available", None


def check_unvalued_order(order) -> None:
    """Refuse an order that does not cover every unvalued capability exactly once."""
    missing = set(UNVALUED_CAPABILITIES) - set(order)
    unknown = set(order) - set(UNVALUED_CAPABILITIES)
    if missing or unknown:
        raise ValueError(
            f"surface.unvalued_order must list exactly {sorted(UNVALUED_CAPABILITIES)}; "
            f"missing {sorted(missing)}, unknown {sorted(unknown)}. An unlisted capability "
            "would never reach one of the three reserved places (FR-106)."
        )
