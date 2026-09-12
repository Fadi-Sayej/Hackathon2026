# tests/owner_state/test_model.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.owner_state.model import OwnerState, answered_cost, revival_active, standing_outcome


def _state():
    return OwnerState.from_dict({
        "schema": 1, "status": "available", "pulled_at": "2026-09-08T00:00:00+00:00",
        "answers": {"123": {"cost_price": {"value": 4.5, "at": 1, "status": "answered"}},
                    "456": {"cost_price": {"value": None, "at": 1, "status": "deferred", "reason": "unknown"}}},
        "outcomes": {"e1": {"status": "acted", "at": 1}, "e2": {"status": "deferred", "at": 1, "deferred_until": 100}},
        "revivals": {"789": {"at": 1, "window_id": "2026-01..2026-07"}},
    })


def test_answered_cost_ignores_deferrals():
    s = _state()
    assert answered_cost(s, "123") == 4.5
    assert answered_cost(s, "0123") == 4.5      # normalised barcode
    assert answered_cost(s, "456") is None


def test_standing_outcome_respects_deferral_deadline():
    s = _state()
    assert standing_outcome(s, "e1", now_ms=50)["status"] == "acted"
    assert standing_outcome(s, "e2", now_ms=50)["status"] == "deferred"
    assert standing_outcome(s, "e2", now_ms=101) is None


def test_revival_is_window_bound():
    s = _state()
    assert revival_active(s, "789", "2026-01..2026-07") is True
    assert revival_active(s, "789", "2026-01..2026-08") is False


def test_unavailable_state_is_empty_and_says_why():
    s = OwnerState.unavailable("pull_failed")
    assert s.status == "unavailable" and s.reason == "pull_failed"
    assert s.answers == {} and s.outcomes == {} and s.revivals == {}
