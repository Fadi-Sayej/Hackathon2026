# src/owner_state/pull.py
"""Pull owner state from Firestore at run start; mirror it for reproduction.

The engine only READS. firebase-admin is imported lazily so tests and local runs
without a service account never touch it (ADR-003)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.owner_state.model import SCHEMA, OwnerState

ROOT = Path(__file__).resolve().parents[2]
MIRROR_PATH = ROOT / "data" / "owner" / "owner_state.json"
DOCS = ("answers", "outcomes", "revivals", "devices", "meta")


def _admin_client(project_id: str, credentials_json: Optional[str], credentials_path: Optional[str]):
    import firebase_admin
    from firebase_admin import credentials, firestore

    if credentials_json:
        cred = credentials.Certificate(json.loads(credentials_json))
    elif credentials_path:
        cred = credentials.Certificate(credentials_path)
    else:
        raise RuntimeError("no service account: set FIREBASE_SERVICE_ACCOUNT_JSON or _PATH")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"projectId": project_id})
    return firestore.client()


def pull(*, project_id: str, store_id: str, credentials_json: Optional[str],
         credentials_path: Optional[str], client=None, now: Optional[datetime] = None) -> OwnerState:
    try:
        client = client or _admin_client(project_id, credentials_json, credentials_path)
        docs = {d.id: d.to_dict() or {} for d in client.collection(f"stores/{store_id}/ownerState").stream()}
    except Exception as exc:  # noqa: BLE001 — any failure is 'unavailable', never 'empty'
        return OwnerState.unavailable(f"pull_failed: {type(exc).__name__}")
    meta = docs.get("meta") or {}
    if int(meta.get("schema", SCHEMA)) != SCHEMA:
        return OwnerState.unavailable("owner_state_schema")
    pulled_at = (now or datetime.now(timezone.utc)).isoformat()
    return OwnerState.from_dict({
        "schema": SCHEMA, "status": "available", "pulled_at": pulled_at,
        "answers": docs.get("answers") or {}, "outcomes": docs.get("outcomes") or {},
        "revivals": docs.get("revivals") or {},
        # ADR-021. One more document in the same collection, so this needs no new step and
        # no second credential — which is why the ADR put it here.
        "devices": docs.get("devices") or {},
    })


def write_mirror(state: OwnerState, path: Path = MIRROR_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return path


def read_mirror(path: Path = MIRROR_PATH) -> OwnerState:
    if not path.exists():
        return OwnerState.unavailable("mirror_missing")
    state = OwnerState.from_dict(json.loads(path.read_text(encoding="utf-8")))
    state.reason = state.reason or "from_mirror"
    return state
