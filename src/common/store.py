"""store.py — what makes this copy one store's (ADR-036, D-28).

Each store runs its own copy of SmartShelf with only its own data. Everything store-specific
the code needs is read from configs/store.yaml through this module, and nothing is defaulted:
a copy that forgot a key would otherwise run quietly on another store's identity. A missing or
invalid key raises StoreSettingsError naming the key.

The derived POS tables carry no store's name, because one copy holds one store.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Optional

import yaml

from src.common.paths import PROJECT_ROOT, SILVER_POS_ROOT

STORE_SETTINGS_PATH = PROJECT_ROOT / "configs" / "store.yaml"

# The two tables the POS importer writes and the engine reads (configs/pos_schema_mapping.yaml
# names them for the importer; this is where every reader takes them from).
PRODUCTS_TABLE = "products.parquet"
INVENTORY_TABLE = "inventory.parquet"
SILVER_PRODUCTS = SILVER_POS_ROOT / PRODUCTS_TABLE
SILVER_INVENTORY = SILVER_POS_ROOT / INVENTORY_TABLE

REQUIRED_KEYS = (
    "id", "name", "site_title", "location.lat", "location.lon", "format",
    "pos.export", "sales.monthly_dir", "sales.daily_dir", "market.radius_km", "firebase.project_id",
    "site.address",
)


class StoreSettingsError(ValueError):
    """configs/store.yaml is missing, incomplete or invalid. The message names the key."""


@dataclass(frozen=True)
class Location:
    lat: float
    lon: float


@dataclass(frozen=True)
class StoreSettings:
    id: str
    name: str
    site_title: str
    location: Location
    format: str
    pos_export: Path
    sales_monthly_dir: Path
    sales_daily_dir: Path
    market_radius_km: float
    firebase_project_id: str
    site_address: str


def _get(raw: Mapping, dotted: str, path: Path):
    node = raw
    for part in dotted.split("."):
        if not isinstance(node, Mapping) or part not in node or node[part] is None or node[part] == "":
            raise StoreSettingsError(f"{path}: `{dotted}` is missing. Every store setting is required "
                                     "(ADR-036); none is defaulted.")
        node = node[part]
    return node


def _text(raw: Mapping, dotted: str, path: Path) -> str:
    value = _get(raw, dotted, path)
    if not isinstance(value, str) or not value.strip():
        raise StoreSettingsError(f"{path}: `{dotted}` must be text, not {value!r}.")
    return value.strip()


def _number(raw: Mapping, dotted: str, path: Path, low: float, high: float) -> float:
    value = _get(raw, dotted, path)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not (low <= float(value) <= high):
        raise StoreSettingsError(f"{path}: `{dotted}` must be a number from {low} to {high}, not {value!r}.")
    return float(value)


def _host(raw: Mapping, dotted: str, path: Path) -> str:
    """A bare host name, as Firebase's authorised domains hold it: no scheme, path or space."""
    import re
    value = _text(raw, dotted, path)
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", value):
        raise StoreSettingsError(f"{path}: `{dotted}` must be a bare host like shop.example.app, not {value!r}.")
    return value


def _formats() -> tuple:
    from src.common.store_types import get_store_types
    return tuple(get_store_types().formats)


def load_store(path: Optional[Path] = None) -> StoreSettings:
    """Read and validate a store settings file. Relative paths in it are from the repository root."""
    path = Path(path) if path is not None else STORE_SETTINGS_PATH
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise StoreSettingsError(f"{path} does not exist. It states which store this copy serves "
                                 "(ADR-036); docs/operations/new-store.md says how to fill it.") from None
    if not isinstance(raw, Mapping):
        raise StoreSettingsError(f"{path}: not a mapping of settings.")
    for dotted in REQUIRED_KEYS:                   # the first missing key, in the file's own order
        _get(raw, dotted, path)
    fmt = _text(raw, "format", path)
    known = _formats()
    if fmt not in known:
        raise StoreSettingsError(f"{path}: `format` is {fmt!r}, which configs/store_types.yaml's scale "
                                 f"does not know. Use one of: {', '.join(known)}.")
    radius = _number(raw, "market.radius_km", path, 0.0, 100.0)
    if radius <= 0:
        raise StoreSettingsError(f"{path}: `market.radius_km` must be above 0, not {radius!r}.")
    return StoreSettings(
        id=_text(raw, "id", path),
        name=_text(raw, "name", path),
        site_title=_text(raw, "site_title", path),
        location=Location(lat=_number(raw, "location.lat", path, -90.0, 90.0),
                          lon=_number(raw, "location.lon", path, -180.0, 180.0)),
        format=fmt,
        pos_export=PROJECT_ROOT / _text(raw, "pos.export", path),
        sales_monthly_dir=PROJECT_ROOT / _text(raw, "sales.monthly_dir", path),
        sales_daily_dir=PROJECT_ROOT / _text(raw, "sales.daily_dir", path),
        market_radius_km=radius,
        firebase_project_id=_text(raw, "firebase.project_id", path),
        site_address=_host(raw, "site.address", path),
    )


@lru_cache(maxsize=1)
def get_store() -> StoreSettings:
    """This copy's store, read once per process."""
    return load_store(STORE_SETTINGS_PATH)


def store_id_for_owner_state(env: Mapping[str, str], path: Optional[Path] = None) -> str:
    """The store whose owner state the engine pulls: the settings' id.

    VITE_STORE_ID may still be set, by the nightly or a laptop's .env. If it names a different
    store, the run stops: pulling one store's decisions into another's artefact is the leak
    D-28 exists to prevent.
    """
    store_id = (load_store(path) if path is not None else get_store()).id
    configured = (env.get("VITE_STORE_ID") or "").strip()
    if configured and configured != store_id:
        raise StoreSettingsError(f"VITE_STORE_ID is {configured!r}, but configs/store.yaml's `id` is "
                                 f"{store_id!r}. One copy serves one store (D-28).")
    return store_id


def firebase_project_for_owner_state(env: Mapping[str, str], path: Optional[Path] = None) -> str:
    """The Firebase project the engine pulls owner state from: the settings' project.

    Each copy has its own Firebase project (ADR-036 §1). An environment naming a different
    one would pull another copy's store into this one, so the run stops instead.
    """
    project = (load_store(path) if path is not None else get_store()).firebase_project_id
    for key in ("FIREBASE_PROJECT_ID", "VITE_FIREBASE_PROJECT_ID"):
        configured = (env.get(key) or "").strip()
        if configured and configured != project:
            raise StoreSettingsError(f"{key} is {configured!r}, but configs/store.yaml's "
                                     f"`firebase.project_id` is {project!r}. One copy, one project (D-28).")
    return project


# ── The store-data manifest (ADR-036 §3) ────────────────────────────────────────────────────
# Every path that holds a store's data or its owner's statements, from the repository root.
# A new store's copy starts without the first group and with an empty template of the second
# (scripts/new_store_copy.py writes them); `--update` never touches either. Everything else is
# code, which every copy shares. The store's own POS export and its sidecar are added from the
# settings (store_data_paths).
STARTS_WITHOUT = (
    "data/internal/**",            # the POS snapshots, the monthly and daily reports, silver
    "data/owner/**",               # the owner-state mirror: the owner's decisions and answers
    "data/external/snapshots/**",  # the market around another store's location
    "public/data/*.json",          # the published artefacts, built from that store's data
    "docs/pilot/**",               # that store's handover, conversations and questions
    "configs/measured_weights.yaml",   # measured from that store's sales (analyse_sales_movement)
    "configs/store_policy.yaml",       # what that store's sales showed it carries; nothing reads it
    # ADR-037, F12-S1: that store's shelves. Absent, not empty, in a new copy: an empty file is a
    # present one (FR-193), and only an absent one says the measurements were never recorded.
    "configs/store_layout.yaml",
    # ADR-040, F12-S1 NFR-078: that store's product pictures, cropped from its own shelf photos.
    "public/store/**",
    # ADR-041: what the shelf reader read from that store's photos, and its acceptance run's hand
    # readings. The photos themselves are under data/internal/**, above.
    "configs/shelf_readings.yaml",
    "configs/shelf_reader_acceptance.yaml",
    "samples/**",
)
KEPT_IN_EVERY_COPY = ("docs/pilot/next-store.md",)
STARTS_EMPTY = (
    "configs/store.yaml",
    "configs/store_facts.yaml",
    "configs/owner_answers.yaml",
    "configs/delivery_targets.yaml",
    "configs/store_types.yaml",    # its scale and affinity kept; its stores emptied
    "firestore.rules",             # the pinned store id
    ".firebaserc",                 # the project the rules deploy to
    ".env.example",                # the Firebase project and store id a developer starts from
)


def store_data_paths(store: StoreSettings) -> tuple:
    """The store's own export and its declared date, as repository paths."""
    export = store.pos_export.relative_to(PROJECT_ROOT).as_posix()
    return export, export.rsplit(".", 1)[0] + ".vintage.json"


def is_store_data(rel: str, store: StoreSettings) -> bool:
    """True for a path a new copy must not inherit, whether it starts without it or empty."""
    from fnmatch import fnmatch
    if rel in KEPT_IN_EVERY_COPY:
        return False
    return (rel in store_data_paths(store) or rel in STARTS_EMPTY
            or any(fnmatch(rel, pattern) for pattern in STARTS_WITHOUT))
