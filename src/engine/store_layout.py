"""The store's shelves, as the team records them from the owner (ADR-037, F12-S1 FR-178 … FR-180).

One committed file per store copy, `configs/store_layout.yaml`, beside the store facts. It
holds four kinds of fact, and each carries who stated or measured it, and when:

    fixtures:                       # one shelving unit, fridge or freezer, by the owner's name
      <fixture>:
        departments: [<department>, ...]
        chilled: true | false
        eye_level_shelf: <n>        # optional; shelves count from 1, the top
        stated_by: owner
        stated_on: 2026-10-10
        recorded_by: team
        shelves:                    # top to bottom
          - {length_cm: 100, measured_by: team, measured_on: 2026-10-10}
    widths:                         # one product's width at the front of a shelf
      "<barcode>": {width_mm: 75, measured_by: team, measured_on: 2026-10-10}
    current:                        # what stands on the shelf today: the measurement's "before"
      "<barcode>": {fixture: <fixture>, shelf: <n>, facings: <n>, measured_by: team, measured_on: …}
    rules:                          # the owner's arrangement rules, a closed set (FR-188)
      - {together: {barcodes: [...]} | {department: <department>}, stated_by: owner, stated_on: …, recorded_by: team}
      - {keep_on:  {barcode: …, fixture: …}, …}
      - {keep_off: {barcode: …, fixture: …}, …}
      - {at_least: {barcode: …, facings: <n>}, …}
      - {at_most:  {barcode: …, facings: <n>}, …}

Validated at load, never repaired (FR-178). A fixture, width, count or rule that fails is
rejected by name with its reason, and the rest are used. Nothing here estimates a width or a
length, or fills a missing one (D-3, INV-086). The file is store data a copy never inherits
(ADR-036 STARTS_WITHOUT): absent, it is the missing input `no_store_layout`.

A department named on two fixtures is used only as far as "keep on" rules assign its products
between them (FR-179, FR-199). With no such rule it is rejected on both, and a product of a
split department that no rule names is rejected by name.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

import yaml

from src.engine.model import norm_barcode

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "configs" / "store_layout.yaml"

STATED = {"stated_by": "owner", "recorded_by": "team"}
MEASURERS = ("team", "owner")
RULE_KINDS = ("together", "keep_on", "keep_off", "at_least", "at_most")
FIXTURE_KEYS = {"departments", "chilled", "eye_level_shelf", "shelves", "stated_by", "stated_on", "recorded_by"}
SHELF_KEYS = {"length_cm", "measured_by", "measured_on"}
WIDTH_KEYS = {"width_mm", "measured_by", "measured_on"}
CURRENT_KEYS = {"fixture", "shelf", "facings", "measured_by", "measured_on"}
TOP_KEYS = {"fixtures", "widths", "current", "rules"}


class _Rejected(Exception):
    pass


class _Loader(yaml.SafeLoader):
    """Safe YAML that remembers a key named twice. PyYAML keeps the last silently, and fixture keys
    `01` and `1` both read as the name "1": one fixture would vanish unrejected."""


class _Mapping(dict):
    """A mapping read from the file, with the keys it named more than once."""
    twice: frozenset = frozenset()


def _mapping_without_duplicates(loader, node, deep=False):
    seen, twice = set(), set()
    for key_node, _ in node.value:
        key = str(loader.construct_object(key_node, deep=deep))
        (twice if key in seen else seen).add(key)
    out = _Mapping(loader.construct_mapping(node, deep=deep))
    out.twice = frozenset(twice)
    return out


def _twice(entry) -> None:
    """FR-178: the one entry is rejected, and the rest of the file is used."""
    named = sorted(getattr(entry, "twice", ()))
    if named:
        raise _Rejected(f"names {', '.join(named)} twice, so neither is used")


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping_without_duplicates)


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


def _positive(value, what: str) -> int:
    if not _whole(value) or value < 1:
        raise _Rejected(f"{what} must be a whole number, at least 1: {value!r}")
    return value


def _keys(entry, allowed: set, what: str) -> None:
    if not isinstance(entry, dict):
        raise _Rejected(f"{what} must be a mapping: {entry!r}")
    unknown = sorted(set(entry) - allowed, key=str)
    if unknown:
        raise _Rejected(f"unknown key {', '.join(map(str, unknown))}; the keys are {sorted(allowed)}")


def _stated(entry: dict) -> dict:
    for key, expected in STATED.items():
        if entry.get(key) != expected:
            raise _Rejected(f"{key} must be {expected!r}, not {entry.get(key)!r}")
    if "stated_on" not in entry:
        raise _Rejected("stated_on is missing: every statement carries the day he made it")
    return {"stated_by": "owner", "stated_on": _day(entry["stated_on"], "stated_on"), "recorded_by": "team"}


def _measured(entry: dict) -> dict:
    if entry.get("measured_by") not in MEASURERS:
        raise _Rejected(f"measured_by must be one of {list(MEASURERS)}, not {entry.get('measured_by')!r}")
    if "measured_on" not in entry:
        raise _Rejected("measured_on is missing: every measurement carries the day it was taken")
    return {"measured_by": entry["measured_by"], "measured_on": _day(entry["measured_on"], "measured_on")}


def _department(name, departments: set) -> str:
    name = str(name)
    if name in departments:
        return name
    near = sorted(d for d in departments if " ".join(d.split()) == " ".join(name.split()))
    if near:
        raise _Rejected(f"no catalogue department is named {name!r}; the catalogue spells it {near[0]!r}")
    raise _Rejected(f"no catalogue department is named {name!r}")


def _barcode(value, catalogue: dict) -> str:
    barcode = norm_barcode(value)
    if barcode is None or barcode not in catalogue:
        raise _Rejected(f"no catalogue product has the barcode {value!r}")
    return barcode


def _fixture(entry, departments: set) -> dict:
    _keys(entry, FIXTURE_KEYS, "a fixture")
    provenance = _stated(entry)
    listed = entry.get("departments")
    if not isinstance(listed, list) or not listed:
        raise _Rejected("departments must list at least one department")
    named = [_department(d, departments) for d in listed]
    if len(set(named)) != len(named):
        raise _Rejected("departments names one department twice")
    if not isinstance(entry.get("chilled"), bool):
        raise _Rejected(f"chilled must be true or false: {entry.get('chilled')!r}")
    shelves = entry.get("shelves")
    if not isinstance(shelves, list) or not shelves:
        raise _Rejected("shelves must list at least one shelf, top to bottom")
    out_shelves = []
    for number, shelf in enumerate(shelves, start=1):
        try:
            _keys(shelf, SHELF_KEYS, "a shelf")
            _twice(shelf)
            out_shelves.append({"shelf": number, "length_cm": _positive(shelf.get("length_cm"), "length_cm"),
                                **_measured(shelf)})
        except _Rejected as err:
            raise _Rejected(f"shelf {number}: {err}")
    eye = entry.get("eye_level_shelf")
    if eye is not None and (not _whole(eye) or not 1 <= eye <= len(out_shelves)):
        # One shelf, by its number: a list or a second shelf is the edge case F12-S1 §12 rejects.
        raise _Rejected(f"eye_level_shelf must name one shelf, 1 to {len(out_shelves)}: {eye!r}")
    _twice(entry)
    return {"departments": named, "chilled": entry["chilled"], "eye_level_shelf": eye,
            "shelves": out_shelves, **provenance}


def _rule(entry, catalogue: dict, departments: set, fixtures: dict) -> dict:
    if not isinstance(entry, dict):
        raise _Rejected(f"a rule must be a mapping: {entry!r}")
    kinds = [k for k in RULE_KINDS if k in entry]
    if len(kinds) != 1:
        raise _Rejected(f"a rule states exactly one of {list(RULE_KINDS)}")
    kind = kinds[0]
    _keys(entry, {kind, "stated_by", "stated_on", "recorded_by"}, "a rule")
    provenance = _stated(entry)
    body = entry[kind]
    if not isinstance(body, dict):
        raise _Rejected(f"{kind} must be a mapping: {body!r}")

    def fixture_named(value) -> str:
        if str(value) not in fixtures:
            raise _Rejected(f"no recorded fixture is named {value!r}")
        return str(value)

    if kind == "together":
        if set(body) == {"department"}:
            return {"kind": kind, "department": _department(body["department"], departments), **provenance}
        if set(body) == {"barcodes"} and isinstance(body["barcodes"], list) and len(body["barcodes"]) >= 2:
            barcodes = [_barcode(b, catalogue) for b in body["barcodes"]]
            if len(set(barcodes)) != len(barcodes):
                raise _Rejected("together names one product twice")
            return {"kind": kind, "barcodes": barcodes, **provenance}
        raise _Rejected("together names either a department or two or more barcodes")
    if kind in ("keep_on", "keep_off"):
        if set(body) != {"barcode", "fixture"}:
            raise _Rejected(f"{kind} names a barcode and a fixture")
        return {"kind": kind, "barcode": _barcode(body["barcode"], catalogue),
                "fixture": fixture_named(body["fixture"]), **provenance}
    if set(body) != {"barcode", "facings"}:
        raise _Rejected(f"{kind} names a barcode and a number of facings")
    return {"kind": kind, "barcode": _barcode(body["barcode"], catalogue),
            "facings": _positive(body["facings"], "facings"), **provenance}


def _mapping(raw: dict, key: str, rejected: list) -> dict:
    value = raw.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        rejected.append({"kind": "file", "key": key, "reason": f"{key} must be a mapping"})
        return {}
    return value


def load_store_layout(path: Path | str, catalogue: Iterable[dict]) -> dict:
    """`{fixtures, widths, current, rules, assigned, rejected}`, never raising.

    `catalogue` is the shaped products list: barcodes and departments are checked against what
    the catalogue actually prints, so a fact can only attach to a product or department that
    exists. `assigned` maps each product of a split department to the fixture its "keep on"
    rule names.

    A file that cannot be read, or records no fixture, is a rejection of kind `file`. It never
    raises: this runs inside load_inputs, where a raise would cost every capability its artefact
    for one typo here.
    """
    products = {p["barcode"]: p for p in catalogue or () if p.get("barcode")}
    departments = {p["department"] for p in products.values() if p.get("department")}
    empty = {"fixtures": {}, "widths": {}, "current": {}, "rules": [], "assigned": {}}
    try:
        raw = yaml.load(Path(path).read_text(encoding="utf-8"), Loader=_Loader)   # noqa: S506 — a SafeLoader
    except (yaml.YAMLError, UnicodeDecodeError) as err:
        return {**empty, "rejected": [{"kind": "file", "key": None, "reason": f"unreadable: {err}"}]}
    if not isinstance(raw, dict) or not raw.get("fixtures"):
        return {**empty, "rejected": [{"kind": "file", "key": None, "reason": "the file records no fixture"}]}
    rejected: list = []
    unknown = sorted(set(raw) - TOP_KEYS, key=str)
    if unknown:
        rejected.append({"kind": "file", "key": None,
                         "reason": f"unknown key {', '.join(map(str, unknown))}; the keys are {sorted(TOP_KEYS)}"})

    fixtures = {}
    # In the file's order, which is the order Shelf plan lists them in (ADR-038). YAML reads a
    # mapping in that order, so it is as deterministic as sorting, and it is his order.
    listed = _mapping(raw, "fixtures", rejected)
    for name, entry in listed.items():
        if str(name) in getattr(listed, "twice", ()):
            rejected.append({"kind": "fixture", "key": str(name),
                             "reason": "the file names this fixture twice, so neither entry is used"})
            continue
        try:
            fixtures[str(name)] = _fixture(entry, departments)
        except _Rejected as err:
            rejected.append({"kind": "fixture", "key": str(name), "reason": str(err)})

    widths = {}
    listed = _mapping(raw, "widths", rejected)
    for code, entry in sorted(listed.items(), key=lambda kv: str(kv[0])):
        if str(code) in getattr(listed, "twice", ()):
            rejected.append({"kind": "width", "key": str(code),
                             "reason": "the file names this barcode twice, so neither entry is used"})
            continue
        try:
            barcode = _barcode(code, products)
            if barcode in widths:
                raise _Rejected("the barcode has two widths")
            _keys(entry, WIDTH_KEYS, "a width")
            _twice(entry)
            widths[barcode] = {"width_mm": _positive(entry.get("width_mm"), "width_mm"), **_measured(entry)}
        except _Rejected as err:
            rejected.append({"kind": "width", "key": str(code), "reason": str(err)})

    rules = []
    listed_rules = raw.get("rules") or []
    if not isinstance(listed_rules, list):
        rejected.append({"kind": "file", "key": "rules", "reason": "rules must be a list"})
        listed_rules = []
    for number, entry in enumerate(listed_rules, start=1):
        try:
            rules.append(_rule(entry, products, departments, fixtures))
        except _Rejected as err:
            rejected.append({"kind": "rule", "key": str(number), "reason": str(err)})

    # FR-179, FR-199: a department on two fixtures stands only as far as "keep on" rules divide it.
    holders: dict = {}
    for name, fixture in fixtures.items():
        for dept in fixture["departments"]:
            holders.setdefault(dept, []).append(name)
    assigned = {}
    for dept, names in sorted(holders.items()):
        if len(names) < 2:
            continue
        keep_on = {r["barcode"]: r["fixture"] for r in rules
                   if r["kind"] == "keep_on" and products[r["barcode"]].get("department") == dept
                   and r["fixture"] in names}
        if not keep_on:
            rejected.append({"kind": "department", "key": dept,
                             "reason": f"named on {', '.join(names)} with no keep_on rule dividing it"})
            for name in names:
                fixtures[name]["departments"] = [d for d in fixtures[name]["departments"] if d != dept]
            continue
        assigned.update(keep_on)
        for barcode in sorted(b for b, p in products.items() if p.get("department") == dept and b not in keep_on):
            rejected.append({"kind": "product", "key": barcode,
                             "reason": f"its department {dept!r} is split across {', '.join(names)}, "
                                       "and no keep_on rule names it"})

    current = {}
    listed = _mapping(raw, "current", rejected)
    for code, entry in sorted(listed.items(), key=lambda kv: str(kv[0])):
        if str(code) in getattr(listed, "twice", ()):
            rejected.append({"kind": "current", "key": str(code),
                             "reason": "the file names this barcode twice, so neither entry is used"})
            continue
        try:
            barcode = _barcode(code, products)
            _keys(entry, CURRENT_KEYS, "a current placement")
            _twice(entry)
            fixture = str(entry.get("fixture"))
            if fixture not in fixtures:
                raise _Rejected(f"no recorded fixture is named {entry.get('fixture')!r}")
            shelf = entry.get("shelf")
            if not _whole(shelf) or not 1 <= shelf <= len(fixtures[fixture]["shelves"]):
                raise _Rejected(f"shelf must be 1 to {len(fixtures[fixture]['shelves'])} on {fixture}: {shelf!r}")
            facings = entry.get("facings")
            # 0 is a statement: on no shelf today. FR-205 leaves such a product out of the estimate.
            if not _whole(facings) or facings < 0:
                raise _Rejected(f"facings must be a whole number, 0 or more: {facings!r}")
            current[barcode] = {"fixture": fixture, "shelf": shelf, "facings": facings, **_measured(entry)}
        except _Rejected as err:
            rejected.append({"kind": "current", "key": str(code), "reason": str(err)})

    return {"fixtures": fixtures, "widths": widths, "current": current, "rules": rules,
            "assigned": assigned, "rejected": rejected}
