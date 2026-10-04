"""layout_facts — the store's recorded shelves, and what is missing from them (F12-S1 FR-190, FR-191,
FR-196 … FR-199).

It needs no sales (D-30): the owner's own inputs do not wait for daily reports. Store layout shows
it the same before and after sales arrive (FR-191). It publishes:
- each fixture as recorded, with the day each fact was measured or stated (ADR-037);
- the departments on no fixture;
- per fixture, the products without a width. While F8's window does not exist that counts the
  departments' catalogue products; once it exists, only the planned ones (FR-190);
- per fixture, the catalogue products not planned, by reason (FR-197, FR-198, FR-199), from the
  one definition `shelf_plan` packs from (`shelf_population`);
- every rejected entry, by kind, key and reason (FR-178).

No value and no entries (FR-192): it is a page's facts, never one of Today's places.
"""
from __future__ import annotations

from src.engine.model import CapabilityOutput
from src.engine.order_evidence import evidence_window
from src.engine.order_quantity import itemised_departments
from src.engine.registry import derive_status
from src.engine.shelf_population import PLANNED, REASONS, departments_on_no_fixture, population

CAP, SPEC = "layout_facts", "F12-S1"


def window_of(inputs):
    """F8's window, exactly as `order_quantity` takes it: None without reports, too few, or stale."""
    daily = inputs.sales_daily or []
    return evidence_window({r["day"] for r in daily}, inputs.policy, inputs.run_at) if daily else None


def run(inputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    layout = inputs.store_layout
    rejected = list(layout.get("rejected") or [])
    if not layout.get("fixtures"):
        out = CapabilityOutput.unavailable(CAP, SPEC, "layout_all_rejected")
        out.extras = {"rejected": rejected}
        return out

    window = window_of(inputs)
    pop = population(layout, inputs.products, inputs.sales_daily, window, itemised_departments(inputs))
    widths = layout.get("widths") or {}
    fixtures, without_width, unplanned = {}, {}, {}
    for name, fixture in sorted(layout["fixtures"].items()):
        members = pop[name]
        fixtures[name] = {**fixture, "rules": [r for r in layout.get("rules") or [] if _concerns(r, name, fixture, members)]}
        counted = ([b for b, m in members.items() if m["status"] == PLANNED] if window is not None
                   else [b for b, m in members.items() if m["status"] not in ("kept_off", "rejected")])
        without_width[name] = sorted(b for b in counted if b not in widths)
        unplanned[name] = {r: sorted(b for b, m in members.items() if m["status"] == r) for r in REASONS}

    no_fixture = departments_on_no_fixture(layout, inputs.products)
    counts = {"fixtures": len(fixtures), "departments_on_no_fixture": len(no_fixture),
              "without_width": sum(len(v) for v in without_width.values()), "rejected": len(rejected)}
    return CapabilityOutput(
        id=CAP, spec=SPEC, status="available", counts=counts,
        extras={"fixtures": fixtures, "departments_on_no_fixture": no_fixture,
                "without_width": without_width, "without_width_counts": "planned" if window is not None else "catalogue",
                "unplanned": unplanned,
                "widths": {b: widths[b] for b in sorted(widths) if any(b in pop[n] for n in pop)},
                "current": dict(sorted((layout.get("current") or {}).items())),
                "evidence_window": window.to_dict() if window else None,
                "rejected": rejected})


def _concerns(rule: dict, name: str, fixture: dict, members: dict) -> bool:
    """Whether a rule applies to this fixture, so Store layout lists it there."""
    if rule["kind"] in ("keep_on", "keep_off"):
        return rule["fixture"] == name
    if rule["kind"] == "together":
        if "department" in rule:
            return rule["department"] in fixture["departments"]
        return any(b in members for b in rule["barcodes"])
    return rule["barcode"] in members
