# src/engine/policy_breach.py
"""SPEC-003 FR-045a — the policy breaches: a price above the store owner's own rule.

Their own capability since ADR-043, so they can wait for the owner's rule (D-39) while the
comparison and the purchase-cost check go on in `competitor_position`. They are computed in
that module's one pass, which is why this module only names the runner: a product the cost
floor stops is never a breach (FR-043a/b), and the two cannot disagree about a price.
"""
from src.engine.competitor_position import run_breaches as run

__all__ = ["run"]
