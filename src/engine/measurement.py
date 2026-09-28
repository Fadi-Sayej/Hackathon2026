"""The pilot measurement (F13-S1, ADR-023 as revised 2026-09-27).

What this run shows, what the owner decided, and the money his acted-on decisions froze when
he made them. The browser renders it and computes nothing (ADR-001).

- No target is compared with it (D-24).
- "Shown" is this run's entries; no past artefact is read (ADR-004, D-23). So no figure
  divides decisions by one run's entries: they are different sets.
- Money is each acted-on decision's snapshot value, the value the engine published on the
  entry when he decided (ADR-016, FR-138). It is summed per kind and certainty, never across
  them (FR-139, D-10). A decision without one is a count (FR-140, INV-066).
- Without the owner state it is unavailable with its reason, and states no count (FR-142).

It is its own file, public/data/measurement.json, beside dashboard.json and never inside it
(ADR-029 Decision 6): the edge gate can keep a file from the owner, but not a field inside a
file his app downloads. It names the run it was computed with, so the two files disagreeing
is detectable.

`measure` is pure: no clock, no storage, no I/O (NFR-064, NFR-065).
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
MEASUREMENT_PATH = ROOT / "public" / "data" / "measurement.json"
SCHEMA_PATH = ROOT / "schemas" / "measurement.schema.json"
SCHEMA_VERSION = 1

STATUSES = ("acted", "declined", "deferred")
UNKNOWN_FAMILY = "unknown"


def _iso(ms) -> Optional[str]:
    if not isinstance(ms, (int, float)):
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _counts() -> dict:
    return {"shown": 0, "decided": 0, "acted": 0, "declined": 0, "deferred": 0, "not_in_this_run": 0}


def measure(outputs, owner) -> dict:
    if owner.status != "available":
        return {"status": "unavailable", "unavailable_reason": owner.reason or "owner_state_unavailable",
                "window": {"first": None, "last": None, "pulled_at": owner.pulled_at}}

    by_family: dict = defaultdict(_counts)
    shown_ids = set()
    for out in outputs:
        for entry in out.entries:
            shown_ids.add(entry.id)
            by_family[entry.signal_family]["shown"] += 1

    money: dict = defaultdict(lambda: {"amount": 0.0, "decisions": 0})
    declined_reasons: Counter = Counter()
    times = []
    for entry_id, rec in (owner.outcomes or {}).items():
        rec = rec or {}
        snap = rec.get("snapshot") or {}
        family = by_family[snap.get("signal_family") or UNKNOWN_FAMILY]
        family["decided"] += 1
        status = rec.get("status")
        if status in STATUSES:
            family[status] += 1
        if entry_id not in shown_ids:
            family["not_in_this_run"] += 1
        if isinstance(rec.get("at"), (int, float)):
            times.append(rec["at"])
        if status == "declined":
            declined_reasons[rec.get("reason") or "none"] += 1
        value = snap.get("value")
        if status == "acted" and isinstance(value, (int, float)) and snap.get("kind"):
            row = money[(snap["kind"], snap.get("certainty") or "confirmed")]
            row["amount"] += value
            row["decisions"] += 1

    totals = _counts()
    for counts in by_family.values():
        for key in totals:
            totals[key] += counts[key]

    return {
        "status": "available",
        "unavailable_reason": None,
        "window": {"first": _iso(min(times)) if times else None, "last": _iso(max(times)) if times else None,
                   "pulled_at": owner.pulled_at},
        "totals": totals,
        "by_family": {family: dict(counts) for family, counts in sorted(by_family.items())},
        "money": [{"kind": kind, "certainty": certainty, "amount": round(row["amount"], 2),
                   "decisions": row["decisions"]}
                  for (kind, certainty), row in sorted(money.items())],
        "declined_reasons": dict(sorted(declined_reasons.items())),
    }


def build_measurement(outputs, owner, *, generated_at: str, run_id: str, inputs_digest: str,
                      devices: Optional[dict]) -> dict:
    return {"schema_version": SCHEMA_VERSION, "generated_at": generated_at, "run_id": run_id,
            "inputs_digest": inputs_digest, "devices": devices, **measure(outputs, owner)}


def validate_measurement(payload: dict) -> None:
    jsonschema.validate(payload, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def write_measurement(payload: dict, path: Path = MEASUREMENT_PATH) -> Path:
    """Validated first and written atomically, like the catalogue (ADR-024): a payload that
    breaches the schema never replaces the last good file."""
    validate_measurement(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return path
