"""The store owner's own statements about each department (ADR-033, F8-S1 FR-157).

Two facts per department, only he holds them, and the team records them from him:
- when he orders it (`order_schedule`);
- how long its products keep (`shelf_life_days`, or `does_not_spoil: true`).

They live in `configs/store_facts.yaml`, committed, and nowhere else: the team is read-only in
his app (ADR-029), and one fact held in two places diverges (ADR-026's lesson).

Validated at load, never repaired. A malformed entry, or one naming no catalogue department,
is rejected and reported, and that department simply has no facts: F8 then says what is
missing (FR-155). Nothing here defaults, infers or copies a value (INV-071). In particular
`configs/shelf_life.yaml`, the category guesses, is not read (FR-152).
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "configs" / "store_facts.yaml"

WEEKDAYS = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")   # the store's week starts on Sunday
PROVENANCE = {"stated_by": "owner", "recorded_by": "team"}
ENTRY_KEYS = {"order_schedule", "shelf_life_days", "does_not_spoil", "stated_by", "stated_on", "recorded_by"}


class _Rejected(Exception):
    pass


def _day(value, what: str) -> str:
    """A calendar day, as YAML reads `2026-10-04` or as an ISO string. Never a timestamp."""
    if isinstance(value, datetime):
        raise _Rejected(f"{what} must be a day, not a time: {value!r}")
    if isinstance(value, date):
        return value.isoformat()
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        raise _Rejected(f"{what} must be a day such as 2026-10-04, not {value!r}")


def _whole(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _schedule(raw) -> dict:
    """One of the three forms ADR-033 names, and exactly one."""
    if not isinstance(raw, dict):
        raise _Rejected(f"order_schedule must be one of weekdays, every_days with from, or no_fixed_days: {raw!r}")
    forms = [k for k in ("weekdays", "every_days", "no_fixed_days") if k in raw]
    extra = set(raw) - {"weekdays", "every_days", "from", "no_fixed_days"}
    if len(forms) != 1 or extra:
        raise _Rejected(f"order_schedule must state exactly one form: {raw!r}")
    form = forms[0]
    if form == "weekdays":
        days = raw["weekdays"]
        if ("from" in raw or not isinstance(days, list) or not days or len(set(days)) != len(days)
                or any(d not in WEEKDAYS for d in days)):
            raise _Rejected(f"order_schedule weekdays must be distinct days from {list(WEEKDAYS)}: {days!r}")
        return {"form": "weekdays", "weekdays": [d for d in WEEKDAYS if d in days]}
    if form == "every_days":
        n = raw["every_days"]
        if not _whole(n) or n < 1 or "from" not in raw:
            raise _Rejected(f"order_schedule every_days must be a whole number of days, at least 1, "
                            f"with the first order day in from: {raw!r}")
        return {"form": "every_days", "every_days": n, "from": _day(raw["from"], "order_schedule from")}
    if raw["no_fixed_days"] is not True or "from" in raw:
        raise _Rejected(f"order_schedule no_fixed_days must be written as true: {raw!r}")
    return {"form": "no_fixed_days"}


def _shelf_life(entry: dict) -> Optional[dict]:
    has_days, has_flag = "shelf_life_days" in entry, "does_not_spoil" in entry
    if has_days and has_flag:
        raise _Rejected("states both shelf_life_days and does_not_spoil")
    if has_flag:
        if entry["does_not_spoil"] is not True:
            raise _Rejected(f"does_not_spoil must be written as true: {entry['does_not_spoil']!r}")
        return {"does_not_spoil": True}
    if has_days:
        days = entry["shelf_life_days"]
        # 0 is a statement: "keeps less than a day", which gives no quantity (FR-151).
        if not _whole(days) or days < 0:
            raise _Rejected(f"shelf_life_days must be a whole number of days, 0 or more: {days!r}")
        return {"days": days}
    return None


def _entry(department: str, entry, departments: set) -> dict:
    if department not in departments:
        near = sorted(d for d in departments if " ".join(d.split()) == " ".join(department.split()))
        if near:
            raise _Rejected(f"no catalogue department has this name; the catalogue spells it {near[0]!r}")
        raise _Rejected("no catalogue department has this name")
    if not isinstance(entry, dict):
        raise _Rejected(f"an entry must be a mapping of facts: {entry!r}")
    unknown = sorted(set(entry) - ENTRY_KEYS)
    if unknown:
        raise _Rejected(f"unknown key {', '.join(unknown)}; the keys are {sorted(ENTRY_KEYS)}")
    for key, expected in PROVENANCE.items():
        if entry.get(key) != expected:
            raise _Rejected(f"{key} must be {expected!r}, not {entry.get(key)!r}")
    if "stated_on" not in entry:
        raise _Rejected("stated_on is missing: every fact carries the day he stated it")
    stated_on = _day(entry["stated_on"], "stated_on")
    schedule = _schedule(entry["order_schedule"]) if "order_schedule" in entry else None
    shelf_life = _shelf_life(entry)
    if schedule is None and shelf_life is None:
        raise _Rejected("states nothing: leave a department out until he has stated a fact")
    return {"order_schedule": schedule, "shelf_life": shelf_life,
            "stated_by": "owner", "stated_on": stated_on, "recorded_by": "team"}


def load_store_facts(path: Path | str, catalogue_departments: Iterable[str]) -> dict:
    """`{facts: {department: fact}, rejected: [{department, reason}]}`, never raising.

    A department is matched against the catalogue exactly as the catalogue prints it. Three
    of its names carry doubled spaces; a name differing only in spacing is rejected, and the
    reason gives the catalogue's spelling rather than guessing that it was meant.

    A file that cannot be read as `departments:` → mapping is one rejection with no
    department. It never raises: this is read inside load_inputs, and a raise there would
    cost every capability its artefact for one typo here.
    """
    departments = set(catalogue_departments or ())
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as err:
        return {"facts": {}, "rejected": [{"department": None, "reason": f"unreadable: {err}"}]}
    if raw is None:
        return {"facts": {}, "rejected": []}
    listed = raw.get("departments") if isinstance(raw, dict) else None
    if listed is None and isinstance(raw, dict) and "departments" in raw:
        listed = {}
    if not isinstance(listed, dict):
        return {"facts": {}, "rejected": [{"department": None,
                                          "reason": "the file must hold `departments:`, a mapping by department"}]}
    facts, rejected = {}, []
    for department in sorted(listed, key=str):
        try:
            facts[str(department)] = _entry(str(department), listed[department], departments)
        except _Rejected as err:
            rejected.append({"department": str(department), "reason": str(err)})
    return {"facts": facts, "rejected": rejected}
