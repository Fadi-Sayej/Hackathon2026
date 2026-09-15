# tests/owner_state/test_device_register.py
"""ADR-021 — the engine half of the device register.

The register exists so Task 4.3's precondition ("every pilot device has opened the app since
the cut-over") can be checked instead of guessed, and what that precondition protects is the
owner's own recorded decisions. So the tests that matter here are the ones about what the
register must NOT say: that nobody has registered is not the same fact as nobody existing,
and a timestamp that moves on every page view must not reach `inputs_digest`.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.owner_state.model import OwnerState, device_register
from src.owner_state.pull import pull, read_mirror, write_mirror

# 2026-09-13T09:00:00Z and 2026-08-30T11:02:00Z, in the epoch milliseconds the browser writes.
SEP_13 = 1789290000000
AUG_30 = 1788087720000


def _available(devices):
    return OwnerState.from_dict({"schema": 1, "status": "available", "pulled_at": "t",
                                 "devices": devices})


def _device(ms, first=None):
    return {"device_id": "ignored", "first_seen_at": first or ms, "last_seen_at": ms}


def test_no_register_is_unavailable_and_never_zero():
    """ARCH-DRIVER-002, and rule 8's 'no number rather than zero'. `count: 0` would read as
    'nobody has opened the app', which is a claim; 'not_registered' is the fact."""
    reg = device_register(_available({}))
    assert reg == {"status": "unavailable", "reason": "not_registered",
                   "count": None, "last_seen_at": []}


def test_an_unavailable_pull_does_not_report_an_empty_register():
    """A failed pull sees no documents at all. Reporting that as 'not_registered' would blame
    the browser for a network failure."""
    reg = device_register(OwnerState.unavailable("pull_failed: RuntimeError"))
    assert reg["status"] == "unavailable" and reg["reason"] == "owner_state_unavailable"
    assert reg["count"] is None


def test_it_counts_distinct_profiles_and_sorts_their_dates():
    reg = device_register(_available({"aaa": _device(SEP_13), "bbb": _device(AUG_30)}))
    assert reg["status"] == "available" and reg["count"] == 2
    assert reg["last_seen_at"] == ["2026-08-30T11:02:00Z", "2026-09-13T09:00:00Z"]


def test_the_device_id_is_never_published():
    """ADR-021 review finding 2. The id is working state for counting; publishing it puts a
    per-profile identifier into a committed file and buys nothing the purpose needs."""
    reg = device_register(_available({"a-very-identifiable-id": _device(SEP_13)}))
    assert "a-very-identifiable-id" not in repr(reg)
    assert set(reg) == {"status", "reason", "count", "last_seen_at"}


def test_a_record_with_no_usable_date_still_counts_as_a_profile():
    """It is a profile that registered; only its date is missing. Dropping it from the count
    would under-report, and inventing a date for it would be worse."""
    reg = device_register(_available({"a": _device(SEP_13), "b": {"device_id": "b"}, "c": None}))
    assert reg["count"] == 3
    assert reg["last_seen_at"] == ["2026-09-13T09:00:00Z"]


def test_a_nonsense_timestamp_is_dropped_rather_than_rendered():
    reg = device_register(_available({"a": _device(0), "b": _device("yesterday"), "c": _device(True)}))
    assert reg["count"] == 3 and reg["last_seen_at"] == []


def test_pull_carries_the_register_off_the_same_collection():
    """No new step and no second credential: it is one more document in
    stores/{store}/ownerState, which pull() already streams whole."""
    class _Doc:
        def __init__(self, id, data): self.id, self._data = id, data
        def to_dict(self): return self._data

    class _Client:
        def collection(self, path):
            assert path == "stores/yomyom-kafr-qasim/ownerState", path
            docs = [_Doc("meta", {"schema": 1}), _Doc("devices", {"aaa": _device(SEP_13)})]
            return type("Col", (), {"stream": lambda self: iter(docs)})()

    state = pull(project_id="p", store_id="yomyom-kafr-qasim", credentials_json=None,
                 credentials_path=None, client=_Client())
    assert device_register(state)["count"] == 1


def test_the_mirror_round_trips_the_register():
    """Reproduction on a laptop replays the mirror (ADR-002). A register the mirror drops
    would make the reproduced artefact disagree with the one CI published."""
    import tempfile
    state = _available({"aaa": _device(SEP_13)})
    with tempfile.TemporaryDirectory() as d:
        path = write_mirror(state, Path(d) / "owner_state.json")
        assert device_register(read_mirror(path)) == device_register(state)
