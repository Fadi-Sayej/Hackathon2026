# src/owner_state/shelf_photos.py
"""Collect the shelf photos sent from the app into the store's copy (ADR-042 Decision 4, F12-S1 FR-226).

The app writes a photo under the store's own Firestore subtree:

    stores/<store>/shelfPhotos/<photo>/parts/<n>   {data: bytes ≤ PART_MAX, n, at}
    stores/<store>/shelfPhotos/<photo>             {unit, sentAt, size, parts, sha256, type, schema}

The parts first and the manifest last, so a manifest means the whole photo is there. Each night:
- every manifest's parts are joined and checked against its size and digest;
- a photo that passes is written to `<root>/<day>/<unit>/<photo>.jpg`. Where a unit has several,
  the newest sent stands there and the earlier ones go to `replaced/`, which the reader does not
  open, so a unit is read from one photo (ADR-041 Decision 1);
- a photo that fails stays in Firestore, and the summary names it;
- parts with no manifest, the newest older than ABANDONED_AFTER, are an abandoned send.

Nothing is deleted here. `delete` removes exactly what the ledger names, and the nightly calls it
only after the photos are pushed, so a failed push loses nothing.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

PART_MAX = 900_000                      # bytes a part: a Firestore document holds at most 1 MiB
SIZE_MAX = 16 * 1024 * 1024             # the app sends at most 12 MB as taken; a redrawn photo is smaller
ABANDONED_AFTER = timedelta(days=2)
SCHEMA = 1
_UNSAFE = re.compile(r"[/\\\x00-\x1f\x7f]")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def folder_name(unit: str) -> str:
    """The unit's name as a folder: only `/`, `\\`, control characters and leading dots removed, so
    it meets the layout file's unit of the same name (ADR-042 Decision 4)."""
    return _UNSAFE.sub("", str(unit)).strip().lstrip(".").strip()


def _manifest_problem(m: dict) -> Optional[str]:
    if m.get("schema") != SCHEMA:
        return "unknown_schema"
    if not isinstance(m.get("unit"), str) or not folder_name(m["unit"]):
        return "no_unit"
    size, parts = m.get("size"), m.get("parts")
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= SIZE_MAX:
        return "bad_size"
    if not isinstance(parts, int) or isinstance(parts, bool) or parts != -(-size // PART_MAX):
        return "bad_part_count"
    if not isinstance(m.get("sha256"), str) or not _HEX64.match(m["sha256"]):
        return "bad_digest"
    if m.get("type") != "image/jpeg":
        return "not_jpeg"
    if not isinstance(m.get("sentAt"), (int, float)) or isinstance(m.get("sentAt"), bool):
        return "no_sent_time"
    return None


def _joined(ref, m: dict) -> tuple:
    """(bytes, None) when the parts make the photo the manifest describes, else (None, why)."""
    parts = {}
    for snap in ref.collection("parts").stream():
        d = snap.to_dict() or {}
        parts[snap.id] = d.get("data")
    if sorted(parts) != sorted(str(n) for n in range(m["parts"])):
        return None, "parts_missing"
    if not all(isinstance(parts[str(n)], (bytes, bytearray)) and 0 < len(parts[str(n)]) <= PART_MAX
               for n in range(m["parts"])):
        return None, "bad_part"
    data = b"".join(bytes(parts[str(n)]) for n in range(m["parts"]))
    if len(data) != m["size"]:
        return None, "size_differs"
    if hashlib.sha256(data).hexdigest() != m["sha256"]:
        return None, "digest_differs"
    if not data.startswith(b"\xff\xd8\xff"):
        return None, "not_jpeg"
    return data, None


def _newest_part(ref) -> Optional[float]:
    times = [(s.to_dict() or {}).get("at") for s in ref.collection("parts").stream()]
    times = [t for t in times if isinstance(t, (int, float)) and not isinstance(t, bool)]
    return max(times) if times else None


def collect(client, store_id: str, *, day: str, root: Path, now: Optional[datetime] = None) -> dict:
    """Write tonight's photos under `root/day` and return the ledger: what was collected, replaced,
    failed and abandoned. Every read happens before any file is written."""
    now = now or datetime.now(timezone.utc)
    ledger = {"day": day, "collected": [], "replaced": [], "failed": [], "abandoned": []}
    good = []
    for ref in client.collection(f"stores/{store_id}/shelfPhotos").list_documents():
        snap = ref.get()
        if not snap.exists:                          # parts with no manifest
            newest = _newest_part(ref)
            if newest is None or now - datetime.fromtimestamp(newest / 1000, timezone.utc) > ABANDONED_AFTER:
                ledger["abandoned"].append(ref.id)
            continue
        m = snap.to_dict() or {}
        why = _manifest_problem(m)
        data = None
        if why is None:
            data, why = _joined(ref, m)
        if why is not None:
            ledger["failed"].append({"id": ref.id, "unit": m.get("unit"), "why": why})
            continue
        good.append((m["sentAt"], ref.id, folder_name(m["unit"]), data))

    by_unit: dict = {}
    for sent_at, photo, unit, data in sorted(good):
        by_unit.setdefault(unit, []).append((photo, data))
    for unit, photos in sorted(by_unit.items()):
        folder = Path(root) / day / unit
        folder.mkdir(parents=True, exist_ok=True)
        *earlier, (newest, data) = photos
        # A photo already standing for the unit tonight (a second run, or one committed by hand)
        # is replaced by the newer one, never read beside it.
        for standing in sorted(p for p in folder.iterdir() if p.is_file()):
            (folder / "replaced").mkdir(exist_ok=True)
            standing.rename(folder / "replaced" / standing.name)
        for photo, old in earlier:
            (folder / "replaced").mkdir(exist_ok=True)
            (folder / "replaced" / f"{photo}.jpg").write_bytes(old)
            ledger["replaced"].append(photo)
        (folder / f"{newest}.jpg").write_bytes(data)
        ledger["collected"].append(newest)
    return ledger


def delete(client, store_id: str, ledger: dict) -> int:
    """Remove from Firestore exactly the photos the ledger names: collected, replaced, abandoned."""
    gone = 0
    collection = client.collection(f"stores/{store_id}/shelfPhotos")
    for photo in ledger.get("collected", []) + ledger.get("replaced", []) + ledger.get("abandoned", []):
        ref = collection.document(photo)
        for part in ref.collection("parts").list_documents():
            part.delete()
        ref.delete()
        gone += 1
    return gone
