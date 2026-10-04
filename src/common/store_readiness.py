"""store_readiness.py — is this copy ready to serve its store? (ADR-036 §5)

docs/pilot/next-store.md lists what a store must supply. This checks each item against the
copy as it stands: present, missing, stale or not checked. For a missing input it names the
capabilities that stay unavailable, read from the registry's `requires`, so the list is never
written down twice. Secrets are checked by name only; no value is ever read or printed.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

import yaml

from src.common.paths import EXTERNAL_SNAPSHOTS_ROOT, PROJECT_ROOT
from src.common.store import StoreSettings
from src.common.store_types import load_store_types

# Which engine inputs each item feeds (EngineInputs fields, as the registry's `requires` names them).
FEEDS = {
    "pos_export": ("products", "inventory"),
    "sales_monthly": ("sales_summary", "window"),
    "sales_daily": ("sales_daily",),
    "store_facts": ("store_facts",),
    "store_layout": ("store_layout",),
    "nearby_venues": ("running_out", "market_recent", "observations", "matches"),
    "boost_key": ("boost_picks",),
}
DAY_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")
NIGHTLY_SECRET = "FIREBASE_SERVICE_ACCOUNT_JSON"
BOOST_SECRET = "ANTHROPIC_API_KEY"


def blocked_by(inputs: Iterable[str]) -> list[str]:
    from src.engine.registry import CAPABILITIES
    wanted = set(inputs)
    return sorted(cid for cid, spec in CAPABILITIES.items() if wanted & set(spec.requires))


def _item(key: str, label: str, status: str, detail: str, blocks: Optional[list] = None) -> dict:
    return {"key": key, "label": label, "status": status, "detail": detail,
            "blocks": blocks if blocks is not None else (blocked_by(FEEDS.get(key, ())) if status != "present" else [])}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and not p.name.startswith(".")) if folder.is_dir() else []


def _pos_export(store: StoreSettings, today: date) -> dict:
    label = "POS inventory export"
    if not store.pos_export.exists():
        return _item("pos_export", label, "missing", f"{_rel(store.pos_export)} is not committed")
    from src.internal_pos.pos_importer import resolve_as_of
    as_of, source = resolve_as_of(store.pos_export)
    age = (today - date.fromisoformat(as_of)).days
    return _item("pos_export", label, "present",
                 f"{_rel(store.pos_export)}, taken {as_of} ({age} days before {today}; {source})")


def _sales_monthly(store: StoreSettings) -> dict:
    files = _files(store.sales_monthly_dir)
    if not files:
        return _item("sales_monthly", "Monthly sales reports", "missing", f"none in {_rel(store.sales_monthly_dir)}")
    return _item("sales_monthly", "Monthly sales reports", "present",
                 f"{len(files)} in {_rel(store.sales_monthly_dir)}")


def _sales_daily(store: StoreSettings, today: date, freshness_days: int) -> dict:
    label = "Daily sales reports, with deliveries"
    days = sorted(m.group(1) for p in _files(store.sales_daily_dir) if (m := DAY_IN_NAME.search(p.name)))
    if not days:
        return _item("sales_daily", label, "missing", f"none in {_rel(store.sales_daily_dir)} (ADR-030)")
    age = (today - date.fromisoformat(days[-1])).days
    if age > freshness_days:
        return _item("sales_daily", label, "stale",
                     f"{len(days)} report days, the latest {days[-1]}: {age} days old, over {freshness_days}")
    return _item("sales_daily", label, "present", f"{len(days)} report days, the latest {days[-1]}")


def _store_facts(path: Path) -> dict:
    label = "Department order days and shelf lives"
    raw = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
    departments = raw.get("departments") or {}
    if not departments:
        return _item("store_facts", label, "missing", f"no department in {_rel(path)} (ADR-033)")
    return _item("store_facts", label, "present", f"{len(departments)} departments in {_rel(path)}")


def _store_layout(path: Path) -> dict:
    label = "Shelf layout: fixtures, shelf lengths, product widths and today's facings"
    if not path.exists():
        return _item("store_layout", label, "missing",
                     f"{_rel(path)} is not committed: the team records it from the owner's shelves (ADR-037)")
    raw = (yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    fixtures = raw.get("fixtures") if isinstance(raw, dict) else None
    if not fixtures:
        return _item("store_layout", label, "missing", f"no fixture in {_rel(path)} (ADR-037)")
    return _item("store_layout", label, "present", f"{len(fixtures)} fixtures in {_rel(path)}")


def _targets(path: Path) -> list[dict]:
    raw = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
    return [t for t in raw.get("targets") or [] if t.get("enabled", True)]


def _client_venue(stores, targets: list[dict]) -> dict:
    label = "The store's own entries"
    has_type, has_target = bool(stores.client_store_ids()), any(t.get("role") == "client" for t in targets)
    if has_type and has_target:
        return _item("client_venue", label, "present",
                     "role: client in store_types.yaml and delivery_targets.yaml", blocks=[])
    missing = [name for name, ok in (("store_types.yaml", has_type), ("delivery_targets.yaml", has_target)) if not ok]
    return _item("client_venue", label, "missing",
                 f"no role: client entry in {' or '.join(missing)}: the store's own venue would count as a competitor",
                 blocks=[])


def _nearby_venues(targets: list[dict]) -> dict:
    others = [t for t in targets if t.get("role") != "client"]
    if not others:
        return _item("nearby_venues", "Nearby venues collected", "missing",
                     "none in delivery_targets.yaml: run scripts/find_nearby_venues.py and confirm them")
    return _item("nearby_venues", "Nearby venues collected", "present", f"{len(others)} in delivery_targets.yaml")


def _venue_formats(stores, snapshots_root: Path) -> dict:
    label = "A format for each collected venue"
    days = sorted(p for p in snapshots_root.iterdir() if p.is_dir()) if snapshots_root.is_dir() else []
    seen: dict[str, str] = {}
    for day in reversed(days):
        silver = [p for p in (day / "delivery_catalog").rglob("*.parquet") if "silver" in p.name]
        if not silver:
            continue
        import polars as pl
        for path in silver:
            try:
                frame = pl.read_parquet(path, columns=["store_id", "store_name"])
            except Exception:
                continue
            for row in frame.unique().iter_rows(named=True):
                seen.setdefault(str(row["store_id"]), row["store_name"] or "")
        break
    if not seen:
        return _item("venue_formats", label, "missing", "no venue collected yet: the first nightly collects them",
                     blocks=[])
    clients = set(stores.client_store_ids())
    unclassified = [f"{name} ({sid})" for sid, name in sorted(seen.items())
                    if sid not in clients and (sid not in stores.stores or stores.stores[sid].verified != "manual")]
    if unclassified:
        return _item("venue_formats", label, "missing",
                     f"no stated format for {', '.join(unclassified)}: each counts as context only until asked",
                     blocks=[])
    return _item("venue_formats", label, "present",
                 f"all {len(seen) - len(clients & set(seen))} collected venues have a stated format", blocks=[])


def _secret(key: str, label: str, name: str, secret_names: Optional[set], missing_detail: str) -> dict:
    if secret_names is None:
        return _item(key, label, "not checked", f"GitHub secret {name}: not readable from here", blocks=[])
    if name in secret_names:
        return _item(key, label, "present", f"GitHub secret {name} is set")
    return _item(key, label, "missing", f"GitHub secret {name} is not set: {missing_detail}")


def readiness(store: StoreSettings, *, today: date, facts_path: Optional[Path] = None,
              targets_path: Optional[Path] = None, store_types_path: Optional[Path] = None,
              snapshots_root: Optional[Path] = None, secret_names: Optional[set] = None,
              layout_path: Optional[Path] = None) -> list[dict]:
    from src.engine.policy import load_policy
    from src.engine.store_facts import DEFAULT_PATH as FACTS_PATH
    from src.engine.store_layout import DEFAULT_PATH as LAYOUT_PATH
    stores = load_store_types(store_types_path) if store_types_path else load_store_types()
    targets = _targets(targets_path or PROJECT_ROOT / "configs" / "delivery_targets.yaml")
    return [
        _pos_export(store, today),
        _sales_monthly(store),
        _sales_daily(store, today, load_policy().order_freshness_days),
        _store_facts(facts_path or FACTS_PATH),
        _store_layout(layout_path or LAYOUT_PATH),
        _client_venue(stores, targets),
        _nearby_venues(targets),
        _venue_formats(stores, snapshots_root or EXTERNAL_SNAPSHOTS_ROOT),
        {**_secret("nightly_secrets", "The nightly's Firebase credential", NIGHTLY_SECRET, secret_names,
                   "the owner's decisions never reach the published artefact"), "blocks": []},
        _secret("boost_key", "The market boost's model key", BOOST_SECRET, secret_names,
                "the boost stays unavailable (no_boost_key)"),
    ]
