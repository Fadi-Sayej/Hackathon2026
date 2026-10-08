"""collect_shelf_photos.py — bring what the owner sent from the app into the store's copy (ADR-042, ADR-044).

    python3 scripts/collect_shelf_photos.py collect --ledger /tmp/shelf_photos.json
    python3 scripts/collect_shelf_photos.py delete  --ledger /tmp/shelf_photos.json

The nightly runs `collect` before the reader and the engine, commits and pushes the photos, and
only then runs `delete`, which removes from Firestore exactly what the ledger names. A failed push
skips `delete`, and the photos are collected again the next night.

`collect` also writes the units the owner entered on Store layout into the layout file (D-38,
ADR-044), when that save is newer than the one the file took. The owner's list stays in Firestore:
it is the owner's state, not something in transit.

The store and its Firebase project are configs/store.yaml's (ADR-036), and the credential is the
service account the engine already pulls owner state with. Without one, or when Firestore cannot
be read, nothing is collected and the night goes on: a photo that waits is not lost.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.store import firebase_project_for_owner_state, store_id_for_owner_state  # noqa: E402
from src.engine.shelf_reader.photos import PHOTOS_ROOT  # noqa: E402
from src.owner_state.pull import _admin_client  # noqa: E402
from src.engine.store_layout import DEFAULT_PATH as LAYOUT_PATH  # noqa: E402
from src.owner_state import shelf_units  # noqa: E402
from src.owner_state.shelf_photos import collect, delete  # noqa: E402


def _client():
    cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or None
    cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH") or None
    if not (cred_json or cred_path):
        return None
    return _admin_client(firebase_project_for_owner_state(os.environ), cred_json, cred_path)


def main(argv=None, *, client=None, root: Path = PHOTOS_ROOT, now=None, layout_path: Path = LAYOUT_PATH) -> int:
    parser = argparse.ArgumentParser(description="Collect the shelf photos sent from the app (ADR-042).")
    parser.add_argument("action", choices=("collect", "delete"))
    parser.add_argument("--ledger", required=True, type=Path, help="what was collected, for `delete` to remove")
    parser.add_argument("--day", help="the photos' day folder; tonight's UTC date when left out")
    args = parser.parse_args(argv)
    store = store_id_for_owner_state(os.environ)

    if args.action == "delete":
        if not args.ledger.exists():
            print("No ledger: nothing was collected, so nothing is deleted.")
            return 0
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        client = client or _client()
        if client is None:
            print("::warning::no service account: the collected photos stay in Firestore")
            return 0
        print(f"Deleted {delete(client, store, ledger)} photo(s) from Firestore.")
        return 0

    try:
        client = client or _client()
    except Exception as exc:  # noqa: BLE001 — a night without photos, never a failed night
        print(f"::warning::the shelf photos were not collected: {type(exc).__name__}")
        return 0
    if client is None:
        print("No service account: the shelf photos were not collected.")
        return 0
    now = now or datetime.now(timezone.utc)
    day = args.day or now.date().isoformat()
    try:
        ledger = collect(client, store, day=day, root=root, now=now)
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::the shelf photos were not collected: {type(exc).__name__}")
        return 0
    args.ledger.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        why = shelf_units.apply(shelf_units.pull(client, store), layout_path)
    except Exception as exc:  # noqa: BLE001 — the units wait for the next night
        why = f"not read: {type(exc).__name__}"
    print("The units entered in the app were written into the layout file." if why is None
          else f"The layout file was left as it is: {why}.")
    print(f"Shelf photos for {day}: {len(ledger['collected'])} collected, {len(ledger['replaced'])} replaced "
          f"by a newer photo of the same unit, {len(ledger['abandoned'])} abandoned sends cleared.")
    for f in ledger["failed"]:
        print(f"::warning::shelf photo {f['id']} ({f.get('unit')}) stays in Firestore: {f['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
