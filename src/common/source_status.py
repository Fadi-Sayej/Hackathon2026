"""
source_status.py — shared data-source status contract.

Every pipeline step (POS import, Kaggle import, competitor scraper, exporter) records
the state of the source it produced into a single JSON the frontend can read:

  public/data/sources.json

Schema (one entry per source_id):
  {
    "source_id":      str,                 # e.g. "yomyom_pos", "kaggle_dor_alon"
    "label":          str,                 # human-friendly name
    "kind":           str,                 # "internal_pos" | "competitor" | "expiry" | ...
    "status":         "not_started" | "partial" | "running" | "complete" | "error",
    "last_updated":   ISO-8601 str | None,
    "row_count":      int,
    "schema_version": str,
  }

This is the integration glue: it lets the dashboard show what is real, how fresh it is,
and whether scraping is still in progress — instead of guessing from row counts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCES_JSON = PROJECT_ROOT / "public" / "data" / "sources.json"

VALID_STATUSES = {"not_started", "partial", "running", "complete", "error"}

# Sources the system knows about up front, so the dashboard can show "not_started"
# for sources that have never produced data yet (e.g. scraper not run).
KNOWN_SOURCES: dict[str, dict[str, str]] = {
    "yomyom_pos": {"label": "YomYom POS", "kind": "internal_pos"},
    "expiry_scans": {"label": "Expiry scans", "kind": "expiry"},
    "kaggle_dor_alon": {"label": "Dor Alon (Kaggle)", "kind": "competitor"},
    "kaggle_rami_levy": {"label": "Rami Levy (Kaggle)", "kind": "competitor"},
    "kaggle_shufersal": {"label": "Shufersal (Kaggle)", "kind": "competitor"},
    "wolt_delivery": {"label": "Wolt delivery catalog", "kind": "competitor"},
    "alonit_prices": {"label": "Alonit price file", "kind": "competitor"},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scaffold() -> dict[str, dict[str, Any]]:
    return {
        sid: {
            "source_id": sid,
            "label": meta["label"],
            "kind": meta["kind"],
            "status": "not_started",
            "last_updated": None,
            "row_count": 0,
            "schema_version": "1",
        }
        for sid, meta in KNOWN_SOURCES.items()
    }


def load_sources() -> dict[str, dict[str, Any]]:
    """Load the current sources map, scaffolding any known-but-missing entries."""
    base = _scaffold()
    if SOURCES_JSON.exists():
        try:
            existing = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
            for sid, entry in (existing.get("sources") or {}).items():
                base[sid] = {**base.get(sid, {}), **entry}
        except (json.JSONDecodeError, OSError):
            pass
    return base


def update_source(
    source_id: str,
    *,
    status: str,
    row_count: int = 0,
    label: str | None = None,
    kind: str | None = None,
    schema_version: str = "1",
) -> dict[str, Any]:
    """Record/refresh one source's status and persist sources.json. Returns full payload."""
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status {status!r}; expected one of {sorted(VALID_STATUSES)}")

    sources = load_sources()
    known = KNOWN_SOURCES.get(source_id, {})
    sources[source_id] = {
        "source_id": source_id,
        "label": label or known.get("label") or source_id,
        "kind": kind or known.get("kind") or "other",
        "status": status,
        "last_updated": _now_iso(),
        "row_count": int(row_count),
        "schema_version": schema_version,
    }
    return _write(sources)


def competitor_scraping_status(sources: dict[str, dict[str, Any]] | None = None) -> str:
    """Derive an aggregate scraping status across all competitor sources."""
    sources = sources or load_sources()
    competitor = [s for s in sources.values() if s.get("kind") == "competitor"]
    if not competitor:
        return "not_started"
    completed = sum(1 for s in competitor if s.get("status") == "complete")
    running = sum(1 for s in competitor if s.get("status") in ("running", "partial"))
    if completed == len(competitor):
        return "complete"
    if completed > 0 or running > 0:
        return "partial"
    return "not_started"


def _write(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "generated_at": _now_iso(),
        "scraping_status": competitor_scraping_status(sources),
        "sources": sources,
    }
    SOURCES_JSON.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def write_summary() -> dict[str, Any]:
    """Re-persist sources.json from current state (recomputes aggregate status)."""
    return _write(load_sources())
