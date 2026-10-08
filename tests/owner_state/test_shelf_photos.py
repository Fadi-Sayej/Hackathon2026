"""Collecting the shelf photos sent from the app (ADR-042 Decision 4, F12-S1 FR-226, AC-212, AC-213).

Against an in-memory stand-in for the few Firestore calls the collector makes. The photos are a
few bytes that start like a JPEG: test data, not a store's (D-23).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from src.owner_state.shelf_photos import PART_MAX, collect, delete, folder_name

STORE = "test-store"
NOW = datetime(2026, 10, 10, 0, 5, tzinfo=timezone.utc)
MS = int(NOW.timestamp() * 1000)


class Snap:
    def __init__(self, id, data):
        self.id, self._data = id, data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class Ref:
    def __init__(self, store, path):
        self.store, self.path = store, path
        self.id = path.rsplit("/", 1)[-1]

    def get(self):
        return Snap(self.id, self.store.docs.get(self.path))

    def collection(self, name):
        return Col(self.store, f"{self.path}/{name}")

    def delete(self):
        self.store.docs.pop(self.path, None)


class Col:
    def __init__(self, store, path):
        self.store, self.path = store, path

    def _children(self):
        depth = self.path.count("/") + 1
        ids = {p.split("/")[depth] for p in self.store.docs if p.startswith(self.path + "/")}
        return sorted(ids)

    def list_documents(self):            # as Firestore's: a document with only subcollections too
        return [Ref(self.store, f"{self.path}/{i}") for i in self._children()]

    def stream(self):
        return [Snap(i, self.store.docs[f"{self.path}/{i}"]) for i in self._children()
                if f"{self.path}/{i}" in self.store.docs]

    def document(self, id):
        return Ref(self.store, f"{self.path}/{id}")


class FakeFirestore:
    def __init__(self):
        self.docs = {}

    def collection(self, path):
        return Col(self, path)

    def send(self, photo, unit, data, *, sent_at=MS, manifest=True, **override):
        """What the app writes: the parts, then the manifest."""
        base = f"stores/{STORE}/shelfPhotos/{photo}"
        parts = [data[i:i + PART_MAX] for i in range(0, len(data), PART_MAX)]
        for n, chunk in enumerate(parts):
            self.docs[f"{base}/parts/{n}"] = {"data": chunk, "n": n, "at": sent_at}
        if manifest:
            self.docs[base] = {"schema": 1, "unit": unit, "sentAt": sent_at, "size": len(data),
                               "parts": len(parts), "sha256": hashlib.sha256(data).hexdigest(),
                               "type": "image/jpeg", **override}

    def photos(self):
        return sorted({p.split("/")[3] for p in self.docs})


def jpeg(tag: bytes, size: int = 40) -> bytes:
    return b"\xff\xd8\xff\xe0" + (tag * size)[:size]


def test_a_photo_is_joined_checked_and_written_as_the_same_bytes(tmp_path):
    db = FakeFirestore()
    big = jpeg(b"abc", 2 * PART_MAX + 17)            # three parts
    db.send("p1", "מקרר 1", big)
    ledger = collect(db, STORE, day="2026-10-10", root=tmp_path, now=NOW)
    written = tmp_path / "2026-10-10" / "מקרר 1" / "p1.jpg"
    assert written.read_bytes() == big                 # AC-212: byte for byte
    assert ledger["collected"] == ["p1"] and not ledger["failed"]
    assert db.photos() == ["p1"]                        # nothing deleted by collecting


def test_sending_again_leaves_one_photo(tmp_path):
    db = FakeFirestore()
    db.send("p1", "מדף יבש", jpeg(b"x"))
    db.send("p1", "מדף יבש", jpeg(b"x"))               # Send pressed twice: the same documents
    collect(db, STORE, day="2026-10-10", root=tmp_path, now=NOW)
    assert [p.name for p in (tmp_path / "2026-10-10" / "מדף יבש").iterdir()] == ["p1.jpg"]


@pytest.mark.parametrize("spoil, why", [
    (lambda db: db.docs.pop(f"stores/{STORE}/shelfPhotos/p1/parts/1"), "parts_missing"),
    (lambda db: db.docs[f"stores/{STORE}/shelfPhotos/p1/parts/0"].update(data=b"\xff\xd8\xff" + b"y" * (PART_MAX - 3)),
     "digest_differs"),
    (lambda db: db.docs[f"stores/{STORE}/shelfPhotos/p1"].update(size=5), "bad_part_count"),
    (lambda db: db.docs[f"stores/{STORE}/shelfPhotos/p1"].update(unit="  ..//  "), "no_unit"),
    (lambda db: db.docs[f"stores/{STORE}/shelfPhotos/p1"].update(schema=2), "unknown_schema"),
])
def test_a_photo_that_fails_its_check_is_not_written_and_stays(tmp_path, spoil, why):
    db = FakeFirestore()
    db.send("p1", "מקרר 1", jpeg(b"abc", PART_MAX + 10))
    spoil(db)
    ledger = collect(db, STORE, day="2026-10-10", root=tmp_path, now=NOW)
    assert ledger["failed"] == [{"id": "p1", "unit": ledger["failed"][0]["unit"], "why": why}]
    assert not ledger["collected"] and not (tmp_path / "2026-10-10").exists()
    delete(db, STORE, ledger)
    assert db.photos() == ["p1"]                        # AC-213: never deleted


def test_bytes_that_are_not_a_jpeg_are_refused(tmp_path):
    db = FakeFirestore()
    db.send("p1", "מקרר 1", b"GIF89a" + b"z" * 30)
    assert collect(db, STORE, day="2026-10-10", root=tmp_path, now=NOW)["failed"][0]["why"] == "not_jpeg"


def test_the_newest_photo_of_a_unit_stands_and_the_earlier_are_kept_aside(tmp_path):
    db = FakeFirestore()
    db.send("old", "מקרר 1", jpeg(b"o"), sent_at=MS - 60_000)
    db.send("new", "מקרר 1", jpeg(b"n"), sent_at=MS)
    db.send("dry", "מדף יבש", jpeg(b"d"))
    ledger = collect(db, STORE, day="2026-10-10", root=tmp_path, now=NOW)
    fridge = tmp_path / "2026-10-10" / "מקרר 1"
    assert sorted(p.name for p in fridge.iterdir() if p.is_file()) == ["new.jpg"]
    assert (fridge / "replaced" / "old.jpg").read_bytes() == jpeg(b"o")
    assert sorted(ledger["collected"]) == ["dry", "new"] and ledger["replaced"] == ["old"]


def test_a_photo_already_standing_tonight_is_replaced_not_read_beside_the_new_one(tmp_path):
    fridge = tmp_path / "2026-10-10" / "מקרר 1"
    fridge.mkdir(parents=True)
    (fridge / "by-hand.jpg").write_bytes(jpeg(b"h"))
    db = FakeFirestore()
    db.send("new", "מקרר 1", jpeg(b"n"))
    collect(db, STORE, day="2026-10-10", root=tmp_path, now=NOW)
    assert sorted(p.name for p in fridge.iterdir() if p.is_file()) == ["new.jpg"]
    assert (fridge / "replaced" / "by-hand.jpg").exists()


def test_parts_with_no_manifest_are_an_abandoned_send_only_after_two_days(tmp_path):
    db = FakeFirestore()
    db.send("recent", "מקרר 1", jpeg(b"r"), manifest=False, sent_at=MS - int(timedelta(hours=30).total_seconds() * 1000))
    db.send("stale", "מקרר 1", jpeg(b"s"), manifest=False, sent_at=MS - int(timedelta(days=3).total_seconds() * 1000))
    ledger = collect(db, STORE, day="2026-10-10", root=tmp_path, now=NOW)
    assert ledger["abandoned"] == ["stale"] and not ledger["collected"]
    delete(db, STORE, ledger)
    assert db.photos() == ["recent"]                    # still being sent, perhaps


def test_delete_removes_exactly_what_the_ledger_names_with_its_parts(tmp_path):
    db = FakeFirestore()
    db.send("p1", "מקרר 1", jpeg(b"a", PART_MAX + 5))
    db.send("bad", "מקרר 2", jpeg(b"b"), sha256="0" * 64)
    db.send("late", "מקרר 3", jpeg(b"c"))
    ledger = collect(db, STORE, day="2026-10-10", root=tmp_path, now=NOW)
    db.send("later", "מקרר 3", jpeg(b"d"))              # sent while the night ran: not in the ledger
    ledger["collected"].remove("late")                  # as if its push had not happened
    delete(db, STORE, ledger)
    assert db.photos() == ["bad", "late", "later"]


@pytest.mark.parametrize("unit, folder", [
    ("מקרר 1", "מקרר 1"), ("  Fridge/1 ", "Fridge1"), ("..\\x", "x"), ("a\x00b\nc", "abc"), ("...", ""),
])
def test_a_units_name_becomes_its_folder_with_only_unsafe_characters_removed(unit, folder):
    assert folder_name(unit) == folder


def _cli():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / "scripts" / "collect_shelf_photos.py"
    spec = importlib.util.spec_from_file_location("collect_shelf_photos", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_nightly_command_writes_a_ledger_and_delete_reads_it(tmp_path, monkeypatch):
    cli = _cli()
    monkeypatch.setattr(cli, "store_id_for_owner_state", lambda env, path=None: STORE)
    db = FakeFirestore()
    db.send("p1", "מקרר 1", jpeg(b"a"))
    ledger = tmp_path / "ledger.json"
    assert cli.main(["collect", "--ledger", str(ledger)], client=db, root=tmp_path / "photos", now=NOW) == 0
    assert json.loads(ledger.read_text(encoding="utf-8"))["collected"] == ["p1"]
    assert (tmp_path / "photos" / "2026-10-10" / "מקרר 1" / "p1.jpg").exists()
    assert cli.main(["delete", "--ledger", str(ledger)], client=db) == 0
    assert db.photos() == []


def test_without_a_service_account_or_a_ledger_the_night_goes_on(tmp_path, monkeypatch):
    cli = _cli()
    monkeypatch.setattr(cli, "store_id_for_owner_state", lambda env, path=None: STORE)
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_PATH", raising=False)
    ledger = tmp_path / "ledger.json"
    assert cli.main(["collect", "--ledger", str(ledger)], root=tmp_path) == 0 and not ledger.exists()
    assert cli.main(["delete", "--ledger", str(ledger)]) == 0
