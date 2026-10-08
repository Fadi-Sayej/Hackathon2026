"""Declared constants for the engine. One file, published with every figure."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "configs" / "policy.yaml"

# The bases the engine actually implements. A policy naming anything else is a
# misconfiguration, not a fallback: the questions would be ordered by a rule nobody wrote.
QUESTION_MONEY_BASES = ("window_revenue_at_shelf_price",)

# D-21: the boost the model picks is accepted from 0% to 25% and no further. The policy may
# lower the limit; it may not raise it.
D21_MAX_BOOST_PCT = 25


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
    # F9-S1 FR-171: at most this many unvalued places for a capability, {id: n}. Unlisted: no cap.
    surface_unvalued_caps: dict
    # F6-S1 FR-106a, as F9-S1 FR-172 uses it: the capabilities whose published order the
    # surface keeps. The others are still ordered by entry id, until that is changed on its own.
    surface_engine_ordered: tuple
    # D-26: the kinds of work that take turns for the unvalued places, one shift a day.
    surface_rotate: tuple
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
    published_population: str
    owner_declared_ceiling_pct: Optional[float]
    # F8-S1 (Phase 5). No defaults: see _required.
    order_window_days: int
    order_min_report_days: int
    order_freshness_days: int
    order_max_count_age_days: int
    order_publish_disagreement_questions: bool
    running_out_prior_days: int
    running_out_min_listed: int
    running_out_min_absent: int
    running_out_max_absent: int
    running_out_catalogue_change_pct: float
    running_out_thin_collection_ratio: float
    running_out_signal_min_usable: int
    running_out_signal_max_age_days: int
    boost_model: str
    boost_max_pct: float
    boost_request_ceiling: int
    boost_prompt: str
    assortment_gap_window_days: int     # F9-S1 §5 "recent"
    # F12-S1 FR-185 (OQ-1204, answered 2026-10-04 with the Phase 8 plan). Provisional.
    shelf_elasticity: float
    shelf_facings_cap: int
    shelf_height_clearance_mm: int   # D-38, ADR-044: OQ-1213, provisional
    # F12-S1 FR-205, FR-209 (OQ-1207, answered 2026-10-04 with the Phase 8 plan). Provisional.
    shelf_interval_level: float
    shelf_min_arrangements: int
    shelf_min_products: int
    shelf_bootstrap_draws: int
    shelf_bootstrap_seed: int
    # F12-S1 FR-210 … FR-215 (D-32, OQ-1209 approved 2026-10-04). Provisional; the model is the
    # boost's pinned one (ADR-039 Decision 2).
    shelf_explanation_prompt: str
    shelf_explanation_request_ceiling: int
    shelf_explanation_time_budget_s: int
    shelf_explanation_max_chars: int
    shelf_explanation_max_tokens: int
    # F12-S1 FR-218 … FR-223 (D-34, OQ-1211 approved 2026-10-05; ADR-041). The reader runs on its
    # own, not in the nightly, so these are not published with the artefact's thresholds.
    shelf_reader_prompt: str
    shelf_reader_candidate_window_days: int
    shelf_reader_tolerance_mm: int
    shelf_reader_acceptance_min: int
    shelf_reader_request_ceiling: int
    shelf_reader_time_budget_s: int
    shelf_reader_timeout_s: int
    shelf_reader_max_tokens: int

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
                "unvalued_caps": dict(self.surface_unvalued_caps),
                "engine_ordered": list(self.surface_engine_ordered),
                "rotate": list(self.surface_rotate),
            },
            "artefact": {
                "min_price": self.artefact_min_price,
                "cost_ratio": self.artefact_cost_ratio,
            },
            "order_quantity": {
                "window_days": self.order_window_days,
                "min_report_days": self.order_min_report_days,
                "freshness_days": self.order_freshness_days,
                "max_count_age_days": self.order_max_count_age_days,
                "publish_disagreement_questions": self.order_publish_disagreement_questions,
            },
            "market_running_out": {
                "prior_days": self.running_out_prior_days,
                "min_listed": self.running_out_min_listed,
                "min_absent": self.running_out_min_absent,
                "max_absent": self.running_out_max_absent,
                "catalogue_change_pct": self.running_out_catalogue_change_pct,
                "thin_collection_ratio": self.running_out_thin_collection_ratio,
                "signal_min_usable": self.running_out_signal_min_usable,
                "signal_max_age_days": self.running_out_signal_max_age_days,
            },
            "market_boost": {
                "model": self.boost_model,
                "max_pct": self.boost_max_pct,
                "request_ceiling": self.boost_request_ceiling,
                "prompt": self.boost_prompt,
            },
            "assortment_gap": {
                "window_days": self.assortment_gap_window_days,
            },
            "shelf_plan": {
                "elasticity": self.shelf_elasticity,
                "facings_cap": self.shelf_facings_cap,
                "height_clearance_mm": self.shelf_height_clearance_mm,
            },
            "shelf_measurement": {
                "window_days": self.order_window_days,
                "min_report_days": self.order_min_report_days,
                "interval_level": self.shelf_interval_level,
                "min_arrangements": self.shelf_min_arrangements,
                "min_products": self.shelf_min_products,
                "bootstrap_draws": self.shelf_bootstrap_draws,
                "bootstrap_seed": self.shelf_bootstrap_seed,
            },
            "shelf_explanation": {
                "model": self.boost_model,
                "prompt": self.shelf_explanation_prompt,
                "request_ceiling": self.shelf_explanation_request_ceiling,
                "time_budget_s": self.shelf_explanation_time_budget_s,
                "max_chars": self.shelf_explanation_max_chars,
                "max_tokens": self.shelf_explanation_max_tokens,
            },
            "question_limit": self.question_limit,
            "published_population": self.published_population,
            "owner_declared_ceiling_pct": self.owner_declared_ceiling_pct,
        }


def _required(raw: dict, group: str, key: str, kind):
    """A value the policy file must state. F8's values have no default in code.

    The older keys above fall back to a default when absent; these do not, because every one
    of them is either the owner's provisional figure (OQ-906) or an ADR's, and a default here
    would publish a number nobody declared as though someone had.
    """
    section = raw.get(group)
    if not isinstance(section, dict):
        raise ValueError(f"policy group {group!r} is missing; it holds F8-S1's declared values")
    if key not in section or section[key] is None:
        raise ValueError(f"policy value {group}.{key} is missing; it has no default (F8-S1)")
    value = section[key]
    if kind is bool:
        # bool("false") is True. A quoted flag must not switch the questions on.
        if not isinstance(value, bool):
            raise ValueError(f"policy value {group}.{key} must be true or false, not {value!r}")
        return value
    if isinstance(value, bool):
        raise ValueError(f"policy value {group}.{key} must be a {kind.__name__}, not {value!r}")
    return kind(value)


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
        surface_unvalued_caps={str(k): v for k, v in (surface.get("unvalued_caps") or {}).items()},
        surface_engine_ordered=tuple(surface.get("engine_ordered") or ()),
        surface_rotate=tuple(surface.get("rotate") or ()),
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
        published_population=str(raw.get("published_population", "living")),
        owner_declared_ceiling_pct=(None if raw.get("owner_declared_ceiling_pct") is None
                                   else float(raw["owner_declared_ceiling_pct"])),
        order_window_days=_required(raw, "order", "window_days", int),
        order_min_report_days=_required(raw, "order", "min_report_days", int),
        order_freshness_days=_required(raw, "order", "freshness_days", int),
        order_max_count_age_days=_required(raw, "order", "max_count_age_days", int),
        order_publish_disagreement_questions=_required(
            raw, "order", "publish_disagreement_questions", bool),
        running_out_prior_days=_required(raw, "running_out", "prior_days", int),
        running_out_min_listed=_required(raw, "running_out", "min_listed", int),
        running_out_min_absent=_required(raw, "running_out", "min_absent", int),
        running_out_max_absent=_required(raw, "running_out", "max_absent", int),
        running_out_catalogue_change_pct=_required(raw, "running_out", "catalogue_change_pct", float),
        running_out_thin_collection_ratio=_required(raw, "running_out", "thin_collection_ratio", float),
        running_out_signal_min_usable=_required(raw, "running_out", "signal_min_usable", int),
        running_out_signal_max_age_days=_required(raw, "running_out", "signal_max_age_days", int),
        boost_model=_required(raw, "boost", "model", str),
        boost_max_pct=_required(raw, "boost", "max_pct", float),
        boost_request_ceiling=_required(raw, "boost", "request_ceiling", int),
        boost_prompt=_required(raw, "boost", "prompt", str),
        assortment_gap_window_days=_required(raw, "assortment_gap", "window_days", int),
        shelf_elasticity=_required(raw, "shelf", "elasticity", float),
        shelf_facings_cap=_required(raw, "shelf", "facings_cap", int),
        shelf_height_clearance_mm=_required(raw, "shelf", "height_clearance_mm", int),
        shelf_interval_level=_required(raw, "shelf", "interval_level", float),
        shelf_min_arrangements=_required(raw, "shelf", "min_arrangements", int),
        shelf_min_products=_required(raw, "shelf", "min_products", int),
        shelf_bootstrap_draws=_required(raw, "shelf", "bootstrap_draws", int),
        shelf_bootstrap_seed=_required(raw, "shelf", "bootstrap_seed", int),
        shelf_explanation_prompt=_required(raw, "shelf", "explanation_prompt", str),
        shelf_explanation_request_ceiling=_required(raw, "shelf", "explanation_request_ceiling", int),
        shelf_explanation_time_budget_s=_required(raw, "shelf", "explanation_time_budget_s", int),
        shelf_explanation_max_chars=_required(raw, "shelf", "explanation_max_chars", int),
        shelf_explanation_max_tokens=_required(raw, "shelf", "explanation_max_tokens", int),
        shelf_reader_prompt=_required(raw, "shelf", "reader_prompt", str),
        shelf_reader_candidate_window_days=_required(raw, "shelf", "reader_candidate_window_days", int),
        shelf_reader_tolerance_mm=_required(raw, "shelf", "reader_tolerance_mm", int),
        shelf_reader_acceptance_min=_required(raw, "shelf", "reader_acceptance_min", int),
        shelf_reader_request_ceiling=_required(raw, "shelf", "reader_request_ceiling", int),
        shelf_reader_time_budget_s=_required(raw, "shelf", "reader_time_budget_s", int),
        shelf_reader_timeout_s=_required(raw, "shelf", "reader_timeout_s", int),
        shelf_reader_max_tokens=_required(raw, "shelf", "reader_max_tokens", int),
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
    if policy.boost_max_pct > D21_MAX_BOOST_PCT:
        raise ValueError(f"boost.max_pct may not exceed {D21_MAX_BOOST_PCT} (D-21)")
    if policy.running_out_min_listed > policy.running_out_prior_days:
        raise ValueError(
            "running_out.min_listed may not exceed running_out.prior_days: a product cannot be "
            "listed on more of the prior days than there are (ADR-031)")
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
    for cap_id, n in policy.surface_unvalued_caps.items():
        if cap_id not in policy.surface_unvalued_order:
            raise ValueError(f"surface.unvalued_caps names {cap_id!r}, which is not in surface.unvalued_order")
        if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= policy.surface_unvalued_places:
            raise ValueError(f"surface.unvalued_caps.{cap_id} must be a whole number from 1 to "
                             f"surface.unvalued_places ({policy.surface_unvalued_places}), not {n!r}")
    for cap_id in policy.surface_engine_ordered:
        if cap_id not in policy.surface_unvalued_order:
            raise ValueError(f"surface.engine_ordered names {cap_id!r}, which is not in surface.unvalued_order")
    if len(set(policy.surface_rotate)) != len(policy.surface_rotate):
        raise ValueError("surface.rotate repeats a capability")
    for cap_id in policy.surface_rotate:
        if cap_id not in policy.surface_unvalued_order:
            raise ValueError(f"surface.rotate names {cap_id!r}, which is not in surface.unvalued_order")
    if not 0 < policy.shelf_elasticity < 1:
        # FR-185: each further facing counts for less only between 0 and 1 (FR-206's range).
        raise ValueError("shelf.elasticity must be above 0 and below 1 (F12-S1 FR-185, FR-206)")
    if policy.shelf_facings_cap < 1:
        raise ValueError("shelf.facings_cap must be at least 1 (F12-S1 FR-185)")
    if policy.shelf_height_clearance_mm < 0:
        raise ValueError("shelf.height_clearance_mm must be 0 or more (F12-S1 FR-233)")
    if not 0 < policy.shelf_interval_level < 1:
        raise ValueError("shelf.interval_level must be above 0 and below 1 (F12-S1 FR-205)")
    if policy.shelf_min_arrangements < 2 or policy.shelf_min_products < 2 or policy.shelf_bootstrap_draws < 100:
        raise ValueError("shelf minimums must be at least 2 and bootstrap_draws at least 100 (F12-S1 FR-205)")
    if policy.assortment_gap_window_days < 1:
        raise ValueError("assortment_gap.window_days must be at least 1")
    return policy
