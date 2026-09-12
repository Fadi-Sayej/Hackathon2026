# src/owner_state/model.py
"""The only mutable state in the system, read-only in Python (design.md §10.3, ADR-003)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.engine.model import norm_barcode

SCHEMA = 1


@dataclass
class OwnerState:
    status: str
    pulled_at: Optional[str]
    answers: dict = field(default_factory=dict)
    outcomes: dict = field(default_factory=dict)
    revivals: dict = field(default_factory=dict)
    schema: int = SCHEMA
    reason: Optional[str] = None

    @classmethod
    def unavailable(cls, reason: str) -> "OwnerState":
        return cls(status="unavailable", pulled_at=None, reason=reason)

    @classmethod
    def from_dict(cls, d: dict) -> "OwnerState":
        answers = {norm_barcode(k) or k: v for k, v in (d.get("answers") or {}).items()}
        revivals = {norm_barcode(k) or k: v for k, v in (d.get("revivals") or {}).items()}
        return cls(status=d.get("status", "available"), pulled_at=d.get("pulled_at"),
                   answers=answers, outcomes=dict(d.get("outcomes") or {}), revivals=revivals,
                   schema=int(d.get("schema", SCHEMA)), reason=d.get("reason"))

    def to_dict(self) -> dict:
        return {"schema": self.schema, "status": self.status, "pulled_at": self.pulled_at,
                "reason": self.reason, "answers": self.answers, "outcomes": self.outcomes,
                "revivals": self.revivals}


def answered_cost(state: OwnerState, barcode) -> Optional[float]:
    rec = (state.answers.get(norm_barcode(barcode) or "") or {}).get("cost_price") or {}
    if rec.get("status") != "answered":
        return None
    value = rec.get("value")
    return float(value) if isinstance(value, (int, float)) and value > 0 else None


def standing_outcome(state: OwnerState, entry_id: str, now_ms: int) -> Optional[dict]:
    rec = state.outcomes.get(entry_id)
    if not rec:
        return None
    status = rec.get("status")
    if status in ("acted", "declined"):
        return rec
    if status == "deferred" and (rec.get("deferred_until") or 0) > now_ms:
        return rec
    return None


def revival_active(state: OwnerState, barcode, window_id: str) -> bool:
    rec = state.revivals.get(norm_barcode(barcode) or "")
    return bool(rec) and rec.get("window_id") == window_id
