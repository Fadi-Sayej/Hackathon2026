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
                                          ("products", "observations", "matches", "price_rule")),
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
    # F8 (V2). The suggestions themselves (ADR-034). It names products, their departments and
    # their counts, so the POS catalogue is as much an input as the two F8 ones.
    "order_quantity":      CapabilitySpec("order_quantity",      "F8-S1",    "none",     False, "units_in_window",
                                          ("products", "sales_daily", "store_facts"),
                                          published_from="2026-09-27"),
    # F9 (V2). What the nearby market ran out of recently that he does not stock (D-25). It
    # has no value and is admitted: F9-S1 FR-171 gives it one unvalued place, the first. His
    # catalogue is the first input, because without it every market product looks unstocked.
    "assortment_gap":      CapabilitySpec("assortment_gap",      "F9-S1",    "none",     True,  "nights_ran_out",
                                          ("products", "running_out", "market_recent"),
                                          published_from="2026-09-29"),
    # F12 (V4). The store's recorded shelves and what is missing from them. It needs no sales
    # (D-30), and it is a page's facts, never one of Today's places (F12-S1 FR-192).
    "layout_facts":        CapabilitySpec("layout_facts",        "F12-S1",   "none",     False, "fixture_order",
                                          ("products", "store_layout"), published_from="2026-10-05"),
    # F12 (V4). Each fixture's dated plan. It waits for daily sales the way F8 does (D-30), so
    # the reports are an input like the layout; F8's freshness and window stop it as they stop F8.
    "shelf_plan":          CapabilitySpec("shelf_plan",          "F12-S1",   "none",     False, "fixture_order",
                                          ("products", "store_layout", "sales_daily"), published_from="2026-10-05"),
    # F12 (V4). What his recorded arrangements changed, in units (FR-202 … FR-209). Owner state is
    # not a registry input: its absence is the rule-level owner_state_unavailable, as F13's is.
    "shelf_measurement":   CapabilitySpec("shelf_measurement",   "F12-S1",   "none",     False, "arranged_on",
                                          ("products", "store_layout", "sales_daily"), published_from="2026-10-05"),
    # F12 (V4, D-32). The AI's explanation of each fixture's plan, sealed nightly (ADR-039). Its
    # own capability, so a missing key never touches the plan (ADR-014, INV-096).
    "shelf_explanation":   CapabilitySpec("shelf_explanation",   "F12-S1",   "none",     False, "fixture_order",
                                          ("products", "store_layout", "sales_daily", "shelf_explanations"),
                                          published_from="2026-10-05"),
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
    # F9-S1: the recent replay exists exactly when tonight's signal does, for the same reason.
    "market_recent": "market_signal_thin",
    # ADR-035: no sealed picks for the day. A live run with a key always seals a manifest,
    # so the only live night without one is a night with no key.
    "boost_picks": "no_boost_key",
    # ADR-030: no daily report has arrived yet. F8 waits for them, and says so.
    "sales_daily": "no_daily_sales",
    # ADR-033: the store facts file itself is absent (an empty one is a file with no facts).
    "store_facts": "no_store_facts",
    # D-39, ADR-043: the owner has not stated a price rule yet. A new copy starts here.
    "price_rule": "no_price_rule",
    # ADR-037: the layout file itself is absent. A new copy starts without it (ADR-036), so this
    # is what a store says until the team records its first fixture.
    "store_layout": "no_store_layout",
    # ADR-039: no explanations were sealed for the night. A live run with a key always seals a
    # manifest, so the only night without one is a night with no key, as with the boost.
    "shelf_explanations": "no_model_key",
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
