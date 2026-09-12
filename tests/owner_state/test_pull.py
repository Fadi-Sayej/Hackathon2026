# tests/owner_state/test_pull.py
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.owner_state.model import OwnerState
from src.owner_state.pull import pull, read_mirror, write_mirror


class _Doc:
    def __init__(self, id, data): self.id, self._data = id, data
    def to_dict(self): return self._data


class _Col:
    def __init__(self, docs): self._docs = docs
    def stream(self): return iter(self._docs)


class _Client:
    """Stands in for firestore.Client: collection('stores/x/ownerState')."""
    def __init__(self, docs): self._docs = docs
    def collection(self, path):
        assert path == "stores/yomyom-kafr-qasim/ownerState"
        return _Col(self._docs)


def test_pull_reads_the_four_documents():
    client = _Client([
        _Doc("answers", {"123": {"cost_price": {"value": 2.0, "at": 1, "status": "answered"}}}),
        _Doc("outcomes", {"e1": {"status": "acted", "at": 1}}),
        _Doc("revivals", {}),
        _Doc("meta", {"schema": 1, "updated_at": 5}),
    ])
    s = pull(project_id="p", store_id="yomyom-kafr-qasim", credentials_json=None, credentials_path=None, client=client)
    assert s.status == "available"
    assert s.answers["123"]["cost_price"]["value"] == 2.0
    assert s.outcomes["e1"]["status"] == "acted"


def test_pull_failure_is_unavailable_not_empty():
    class Broken:
        def collection(self, path): raise RuntimeError("network")
    s = pull(project_id="p", store_id="yomyom-kafr-qasim", credentials_json=None, credentials_path=None, client=Broken())
    assert s.status == "unavailable" and s.reason == "pull_failed: RuntimeError"


def test_pull_rejects_unknown_schema():
    client = _Client([_Doc("meta", {"schema": 99})])
    s = pull(project_id="p", store_id="yomyom-kafr-qasim", credentials_json=None, credentials_path=None, client=client)
    assert s.status == "unavailable" and s.reason == "owner_state_schema"


def test_mirror_round_trip(tmp_path):
    s = OwnerState.from_dict({"schema": 1, "status": "available", "pulled_at": "t",
                              "answers": {"1": {}}, "outcomes": {}, "revivals": {}})
    p = write_mirror(s, tmp_path / "owner_state.json")
    back = read_mirror(p)
    assert back.status == "available" and back.answers == {"1": {}}
    assert json.loads(p.read_text())["schema"] == 1


def test_missing_mirror_is_unavailable(tmp_path):
    assert read_mirror(tmp_path / "nope.json").reason == "mirror_missing"
