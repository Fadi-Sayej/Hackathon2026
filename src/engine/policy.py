"""Declared constants for the engine. One file, published with every figure."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "configs" / "policy.yaml"

# The bases the engine actually implements. A policy naming anything else is a
# misconfiguration, not a fallback: the questions would be ordered by a rule nobody wrote.
QUESTION_MONEY_BASES = ("window_revenue_at_shelf_price",)


@dataclass(frozen=True)
class Policy:
    version: int
    price_policy_pct: float
    attention_pct: float
    cost_floor_pct: float
    freshness_days: int
    artefact_min_price: float
    artefact_cost_ratio: float
    max_credible_gap_pct: float
    surface_bound: int
    surface_unvalued_places: int
    surface_unvalued_order: tuple
    question_limit: int
    question_money_basis: str
    question_yield_factor: float
    uncomparable_min_barcode_digits: int
    ceiling_band_pct: float
    ceiling_drop_ratio: float
    ceiling_min_band_count: int
    implausible_revenue_share: float
    full_annual_cycle_months: int
    withdraw_with_stock: bool

    def as_dict(self) -> dict:
        """The artefact's `thresholds` block, grouped as design §11.4 defines it.

        Not `asdict(self)`. A flat dump is convenient here and useless at the other end:
        F7-S1 requires every count to be rendered with the thresholds that governed it, and
        that is only possible if the reader can tell which knobs belong to which capability.
        The dataclass stays flat because a policy file is edited as a list; the contract is
        grouped because an artefact is read per finding.
        """
        return {
            "version": self.version,
            "price_consistency": {
                "band_pct": self.ceiling_band_pct,
                "drop_ratio": self.ceiling_drop_ratio,
                "min_band_count": self.ceiling_min_band_count,
                "max_credible_gap_pct": self.max_credible_gap_pct,
            },
            "competitor_position": {
                "policy_pct": self.price_policy_pct,
                "attention_pct": self.attention_pct,
                "cost_floor_pct": self.cost_floor_pct,
                "freshness_days": self.freshness_days,
                "uncomparable_min_barcode_digits": self.uncomparable_min_barcode_digits,
            },
            "catalogue_lifecycle": {
                "implausible_revenue_share": self.implausible_revenue_share,
                "full_annual_cycle_months": self.full_annual_cycle_months,
                "withdraw_with_stock": self.withdraw_with_stock,
            },
            "owner_questions": {
                "limit": self.question_limit,
                "money_basis": self.question_money_basis,
                "yield_factor": self.question_yield_factor,
            },
            "surface": {
                "bound": self.surface_bound,
                "unvalued_places": self.surface_unvalued_places,
                "unvalued_order": list(self.surface_unvalued_order),
            },
            "artefact": {
                "min_price": self.artefact_min_price,
                "cost_ratio": self.artefact_cost_ratio,
            },
            "question_limit": self.question_limit,
        }


def load_policy(path: Path | str | None = None) -> Policy:
    raw = yaml.safe_load(Path(path or DEFAULT_PATH).read_text(encoding="utf-8")) or {}
    surface = raw.get("surface", {}) or {}
    ceiling = raw.get("ceiling_derivation", {}) or {}
    policy = Policy(
        version=int(raw.get("version", 1)),
        price_policy_pct=float(raw.get("price_policy_pct", 60)),
        attention_pct=float(raw.get("attention_pct", 100)),
        cost_floor_pct=float(raw.get("cost_floor_pct", 10)),
        freshness_days=int(raw.get("freshness_days", 14)),
        artefact_min_price=float(raw.get("artefact_min_price", 0.5)),
        artefact_cost_ratio=float(raw.get("artefact_cost_ratio", 2)),
        max_credible_gap_pct=float(raw.get("max_credible_gap_pct", 300)),
        surface_bound=int(surface.get("bound", 10)),
        surface_unvalued_places=int(surface.get("unvalued_places", 3)),
        surface_unvalued_order=tuple(surface.get("unvalued_order") or ()),
        question_limit=int(raw.get("question_limit", 3)),
        question_money_basis=str(raw.get("question_money_basis", "window_revenue_at_shelf_price")),
        question_yield_factor=float(raw.get("question_yield_factor", 1.0)),
        uncomparable_min_barcode_digits=int(raw.get("uncomparable_min_barcode_digits", 8)),
        ceiling_band_pct=float(ceiling.get("band_pct", 2)),
        ceiling_drop_ratio=float(ceiling.get("drop_ratio", 0.75)),
        ceiling_min_band_count=int(ceiling.get("min_band_count", 20)),
        implausible_revenue_share=float(raw.get("implausible_revenue_share", 0.10)),
        full_annual_cycle_months=int(raw.get("full_annual_cycle_months", 12)),
        withdraw_with_stock=bool(raw.get("withdraw_with_stock", False)),
    )
    if policy.withdraw_with_stock:
        raise ValueError(
            "withdraw_with_stock must be false: extending automatic withdrawal to "
            "stock-carrying entries is OQ-409 and is not authorised (SPEC-004 INV-030)."
        )
    if policy.question_limit > 3:
        raise ValueError("question_limit may not exceed 3 (D-8)")
    if policy.surface_bound > 10:
        raise ValueError("surface.bound may not exceed 10 (D-9)")
    if policy.question_money_basis not in QUESTION_MONEY_BASES:
        raise ValueError(
            f"question_money_basis {policy.question_money_basis!r} is not implemented; "
            f"the engine knows {QUESTION_MONEY_BASES} (ARCH-GATE-002)"
        )
    from src.engine.registry import check_unvalued_order   # local: registry imports nothing
    check_unvalued_order(policy.surface_unvalued_order)     # a validator nobody calls is a comment
    if len(set(policy.surface_unvalued_order)) != len(policy.surface_unvalued_order):
        raise ValueError("surface.unvalued_order repeats a capability")
    if not policy.surface_unvalued_order:
        raise ValueError(
            "surface.unvalued_order must list every unvalued capability in precedence order: "
            "it decides which unvalued work reaches the three reserved places (OQ-601, design §9.2)."
        )
    return policy
