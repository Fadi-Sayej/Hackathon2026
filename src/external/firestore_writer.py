"""
firestore_writer.py — push delivery-catalog observations to Firestore.

Collections
-----------
- `stores`            : one doc per (chain, store_id)
- `products`          : current snapshot, doc id = {chain}_{store_id}_{barcode}
- `price_snapshots`   : append-only timestamped copy, doc id includes ISO date

Doc-id rules (idempotency)
--------------------------
- chain     : slug from the target config (e.g. "yomyom", "victory")
- store_id  : provider-side store id (Wolt venue UUID, 10bis restaurantId)
- barcode   : prefer GTIN; fall back to sku; finally slug(product_name)

Idempotency is enforced via `.set(merge=True)` so re-running a scrape simply
overwrites stale prices on the same doc.

Authentication
--------------
A service-account JSON is loaded from one of:
  1. FIREBASE_SERVICE_ACCOUNT_PATH   — absolute path to the JSON file
  2. FIREBASE_SERVICE_ACCOUNT_JSON   — inline JSON string

`.env` (project root) is auto-loaded via python-dotenv.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from loguru import logger

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── .env loading (optional dep) ──────────────────────────────────────────────

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    # python-dotenv missing → assume env vars are set in the environment.
    pass


# ── Firestore SDK is imported lazily so this module is importable in tests
#    even without firebase-admin installed.

_firestore_client = None  # cached after first init


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "unknown"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Initialisation ───────────────────────────────────────────────────────────

def _load_service_account() -> dict[str, Any]:
    """Return the parsed service-account JSON, raising if missing."""
    path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    inline = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

    if path:
        full = Path(path)
        if not full.is_absolute():
            full = _ROOT / full
        if not full.exists():
            raise FileNotFoundError(
                f"FIREBASE_SERVICE_ACCOUNT_PATH points to a missing file: {full}"
            )
        return json.loads(full.read_text(encoding="utf-8"))

    if inline:
        return json.loads(inline)

    raise RuntimeError(
        "No Firebase credentials provided. Set FIREBASE_SERVICE_ACCOUNT_PATH "
        "or FIREBASE_SERVICE_ACCOUNT_JSON in your .env."
    )


def init_firestore():
    """Lazily initialise firebase-admin and return a Firestore client."""
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        cred = credentials.Certificate(_load_service_account())
        project_id = os.environ.get("FIREBASE_PROJECT_ID")
        if project_id:
            firebase_admin.initialize_app(cred, {"projectId": project_id})
        else:
            firebase_admin.initialize_app(cred)

    _firestore_client = firestore.client()
    logger.info("Firestore client initialised (project={}).",
                _firestore_client.project)
    return _firestore_client


# ── Doc-id helpers ───────────────────────────────────────────────────────────

def make_store_doc_id(chain: str, store_id: str) -> str:
    return f"{_slugify(chain)}__{_slugify(store_id)}"


def make_product_doc_id(chain: str, store_id: str, observation: dict[str, Any]) -> str:
    barcode = observation.get("barcode") or observation.get("sku")
    if not barcode:
        barcode = _slugify(observation.get("product_name") or "unknown")
    return f"{_slugify(chain)}__{_slugify(store_id)}__{_slugify(str(barcode))}"


# ── Public API ───────────────────────────────────────────────────────────────

@dataclass
class WriteSummary:
    stores_written: int
    products_written: int
    price_snapshots_written: int
    errors: list[str]


def upsert_store(
    db,
    *,
    chain: str,
    role: str,
    target_key: str,
    store_info: dict[str, Any],
) -> str:
    """
    Upsert a single store document.  `store_info` may come from either the
    Wolt StoreInfo dataclass.__dict__ or the TenBis adapted form (they share
    keys: provider, source_url, store_name, store_id, store_chain, city,
    address, phone, latitude, longitude, currency, raw).
    """
    store_id = store_info.get("store_id") or _slugify(target_key)
    doc_id = make_store_doc_id(chain, str(store_id))

    # `raw` may contain arrays-of-arrays (e.g. Wolt's delivery_geo_range
    # polygon) which Firestore rejects with "invalid nested entity". We
    # store it as a JSON string — the data stays auditable but doesn't try
    # to nest inside Firestore's typed map structure.
    raw_blob = store_info.get("raw") or {}
    raw_json = json.dumps(raw_blob, ensure_ascii=False, default=str)

    payload = {
        "target_key": target_key,
        "chain": chain,
        "role": role,                          # client | competitor
        "provider": store_info.get("provider"),
        "source_url": store_info.get("source_url"),
        "store_id": store_id,
        "store_name": store_info.get("store_name"),
        "store_chain": store_info.get("store_chain"),
        "city": store_info.get("city"),
        "address": store_info.get("address"),
        "phone": store_info.get("phone"),
        "latitude": store_info.get("latitude"),
        "longitude": store_info.get("longitude"),
        "currency": store_info.get("currency"),
        "raw_json": raw_json,
        "updated_at": _now_iso(),
    }
    db.collection("stores").document(doc_id).set(payload, merge=True)
    logger.debug("Firestore stores/{} upserted", doc_id)
    return doc_id


def upsert_products(
    db,
    *,
    chain: str,
    role: str,
    store_id: str,
    observations: Iterable[dict[str, Any]],
) -> int:
    """
    Upsert each observation as a doc under collection `products`.  Returns
    the number of docs written.  Uses batched writes (max 500/batch).
    """
    BATCH_SIZE = 400
    count = 0
    batch = db.batch()
    batch_ops = 0

    for obs in observations:
        doc_id = make_product_doc_id(chain, str(store_id), obs)
        payload = {
            **{k: _serialise(v) for k, v in obs.items()},
            "chain": chain,
            "role": role,
            "store_id": str(store_id),
            "doc_id": doc_id,
            "updated_at": _now_iso(),
        }
        ref = db.collection("products").document(doc_id)
        batch.set(ref, payload, merge=True)
        batch_ops += 1
        count += 1

        if batch_ops >= BATCH_SIZE:
            batch.commit()
            batch = db.batch()
            batch_ops = 0

    if batch_ops:
        batch.commit()

    logger.info("Firestore products: {} docs upserted for chain={}, store_id={}",
                count, chain, store_id)
    return count


def append_price_snapshots(
    db,
    *,
    chain: str,
    role: str,
    store_id: str,
    observed_at: datetime,
    observations: Iterable[dict[str, Any]],
) -> int:
    """
    Append-only price history.  Doc id is product_doc_id + observed date
    (YYYYMMDD) so reruns on the same day stay idempotent but daily history
    is preserved.
    """
    BATCH_SIZE = 400
    date_suffix = observed_at.strftime("%Y%m%d")
    count = 0
    batch = db.batch()
    batch_ops = 0

    for obs in observations:
        product_doc_id = make_product_doc_id(chain, str(store_id), obs)
        doc_id = f"{product_doc_id}__{date_suffix}"
        payload = {
            "chain": chain,
            "role": role,
            "store_id": str(store_id),
            "product_doc_id": product_doc_id,
            "barcode": obs.get("barcode"),
            "sku": obs.get("sku"),
            "product_name": obs.get("product_name"),
            "category": obs.get("category"),
            "price": _serialise(obs.get("price")),
            "sale_price": _serialise(obs.get("sale_price")),
            "currency": obs.get("currency") or "ILS",
            "is_online_available": obs.get("is_online_available"),
            "observed_at": observed_at.isoformat(),
            "observed_date": observed_at.strftime("%Y-%m-%d"),
        }
        ref = db.collection("price_snapshots").document(doc_id)
        batch.set(ref, payload, merge=True)
        batch_ops += 1
        count += 1
        if batch_ops >= BATCH_SIZE:
            batch.commit()
            batch = db.batch()
            batch_ops = 0

    if batch_ops:
        batch.commit()

    logger.info("Firestore price_snapshots: {} docs appended for chain={}",
                count, chain)
    return count


# ── Helpers ──────────────────────────────────────────────────────────────────

def _serialise(value: Any) -> Any:
    """Make a value Firestore-friendly (Decimal → float, datetime → ISO)."""
    from decimal import Decimal

    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialise(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialise(v) for v in value]
    return value


def write_target_to_firestore(
    *,
    chain: str,
    role: str,
    target_key: str,
    store_info: dict[str, Any],
    observations: Iterable[dict[str, Any]],
    observed_at: datetime,
) -> WriteSummary:
    """
    Convenience wrapper: init the client, write store + products + snapshots
    for one target.  Returns a WriteSummary.
    """
    db = init_firestore()
    observations_list = list(observations)
    errors: list[str] = []

    try:
        store_doc_id = upsert_store(
            db,
            chain=chain,
            role=role,
            target_key=target_key,
            store_info=store_info,
        )
        store_id = store_info.get("store_id") or store_doc_id.split("__", 1)[-1]
    except Exception as exc:
        errors.append(f"upsert_store failed: {exc}")
        logger.exception("upsert_store failed for {}", target_key)
        return WriteSummary(0, 0, 0, errors)

    products_written = 0
    snapshots_written = 0
    if observations_list:
        try:
            products_written = upsert_products(
                db,
                chain=chain,
                role=role,
                store_id=str(store_id),
                observations=observations_list,
            )
        except Exception as exc:
            errors.append(f"upsert_products failed: {exc}")
            logger.exception("upsert_products failed for {}", target_key)

        try:
            snapshots_written = append_price_snapshots(
                db,
                chain=chain,
                role=role,
                store_id=str(store_id),
                observed_at=observed_at,
                observations=observations_list,
            )
        except Exception as exc:
            errors.append(f"append_price_snapshots failed: {exc}")
            logger.exception("append_price_snapshots failed for {}", target_key)

    return WriteSummary(
        stores_written=1,
        products_written=products_written,
        price_snapshots_written=snapshots_written,
        errors=errors,
    )
