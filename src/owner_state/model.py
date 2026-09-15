# src/owner_state/model.py
"""The only mutable state in the system, read-only in Python (design.md §10.3, ADR-003)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    # ADR-021. Keyed by an opaque device_id the browser mints; the id is working state for
    # counting distinct writers and is never published.
    devices: dict = field(default_factory=dict)
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
                   devices=dict(d.get("devices") or {}),
                   schema=int(d.get("schema", SCHEMA)), reason=d.get("reason"))

    def to_dict(self) -> dict:
        return {"schema": self.schema, "status": self.status, "pulled_at": self.pulled_at,
                "reason": self.reason, "answers": self.answers, "outcomes": self.outcomes,
                "revivals": self.revivals, "devices": self.devices}


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


def _iso(ms) -> Optional[str]:
    """Epoch milliseconds — what the browser writes everywhere — as UTC ISO-8601."""
    if not isinstance(ms, (int, float)) or isinstance(ms, bool) or ms <= 0:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return None


def device_register(state: OwnerState) -> dict:
    """ADR-021: how many browser profiles have written owner state, and when each last did.

    Published under `vintages.owner_state`, never as its own block, and never carrying the
    `device_id` — the id exists so distinct writers can be counted, and once counted it has
    done its work.

    An absent register is `unavailable`, never `count: 0` (ARCH-DRIVER-002, and rule 8's "no
    number rather than zero"): nobody having opened the app and nobody having registered look
    identical from here, and only one of them is a fact.

    `count` counts every registered profile. `last_seen_at` carries only the timestamps that
    parse, so a corrupted record still counts as a profile without inventing a date for it —
    the two can therefore differ in length, and that asymmetry is deliberate.
    """
    if state.status != "available":
        return {"status": "unavailable", "reason": "owner_state_unavailable",
                "count": None, "last_seen_at": []}
    if not state.devices:
        return {"status": "unavailable", "reason": "not_registered",
                "count": None, "last_seen_at": []}
    seen = [_iso((rec or {}).get("last_seen_at")) for rec in state.devices.values()]
    return {"status": "available", "reason": None,
            "count": len(state.devices),
            "last_seen_at": sorted(t for t in seen if t)}
