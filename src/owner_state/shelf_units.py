# src/owner_state/shelf_units.py
"""Write the units the owner entered in the app into the layout file (D-38, ADR-044 Decision 3,
F12-S1 FR-229).

The app keeps the owner's whole list in one document, `stores/<store>/ownerState/layout`:

    {schema: 1, saved_at: "2026-10-08T09:12:00.000Z", units: [{name, departments, chilled,
     eye_level_shelf, shelves: [{length_cm, height_cm}]}]}

Each night, before the engine, a save newer than the one the file last took replaces the file's
`fixtures`; everything else in the file is kept. A unit the owner changed carries the day of the
save, `recorded_by: app`, and `measured_by: owner` on its shelves. An unchanged unit keeps its
entry, dates and recorder included. The file records which save it took, `entered_in_app`, so a
save is applied once and a later correction by the team is not undone the next night.

Nothing here validates a unit beyond its shape: the loader checks it as it checks any other, and
names what it rejects on Store layout (FR-178).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

SCHEMA = 1
HEADER = ("# configs/store_layout.yaml — the store's shelving units (ADR-037). Since D-38 the owner\n"
          "# enters them on Store layout and the nightly writes them here (ADR-044); the rules and the\n"
          "# rest are kept as recorded. Changed only by commit.\n")


def pull(client, store_id: str) -> Optional[dict]:
    snap = client.collection(f"stores/{store_id}/ownerState").document("layout").get()
    return snap.to_dict() if snap.exists else None


def _shape(unit: dict) -> tuple:
    """What the owner states about a unit, for telling a changed one from an unchanged one."""
    return (tuple(unit.get("departments") or ()), bool(unit.get("chilled")), unit.get("eye_level_shelf") or None,
            tuple((s.get("length_cm"), s.get("height_cm", "absent")) for s in unit.get("shelves") or ()))


def _entry(unit: dict, day: str) -> dict:
    entry = {"departments": list(unit.get("departments") or []), "chilled": bool(unit.get("chilled"))}
    if unit.get("eye_level_shelf"):
        entry["eye_level_shelf"] = unit["eye_level_shelf"]
    entry.update({"stated_by": "owner", "stated_on": day, "recorded_by": "app",
                  "shelves": [{"length_cm": s.get("length_cm"), "height_cm": s.get("height_cm"),
                               "measured_by": "owner", "measured_on": day} for s in unit.get("shelves") or []]})
    return entry


def apply(doc: Optional[dict], layout_path: Path) -> Optional[str]:
    """Write the save into the file when it is newer than the one the file took. Returns why it
    was not written, or None when it was."""
    if not doc:
        return "nothing_saved"
    if doc.get("schema") != SCHEMA or not isinstance(doc.get("units"), list) or not isinstance(doc.get("saved_at"), str):
        return "unknown_schema"
    path = Path(layout_path)
    raw = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
    if not isinstance(raw, dict):
        return "file_unreadable"
    taken = (raw.get("entered_in_app") or {}).get("saved_at") if isinstance(raw.get("entered_in_app"), dict) else None
    if taken is not None and str(taken) >= doc["saved_at"]:
        return "already_taken"
    day = doc["saved_at"][:10]
    # By name as text: YAML reads a unit named 1 as a number.
    before = {str(k): v for k, v in raw["fixtures"].items()} if isinstance(raw.get("fixtures"), dict) else {}
    fixtures = {}
    for unit in doc["units"]:
        if not isinstance(unit, dict) or not str(unit.get("name") or "").strip():
            continue
        name = str(unit["name"]).strip()
        old = before.get(name)
        fixtures[name] = old if isinstance(old, dict) and _shape(old) == _shape(unit) else _entry(unit, day)
    out = {"fixtures": fixtures, **{k: v for k, v in raw.items() if k not in ("fixtures", "entered_in_app")},
           "entered_in_app": {"saved_at": doc["saved_at"]}}
    path.write_text(HEADER + yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return None
