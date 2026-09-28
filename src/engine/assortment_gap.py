# src/engine/assortment_gap.py
"""What the nearby market ran out of recently that he does not stock (F9-S1, D-25).

A finding (F9-S1 §5) is a product that:
- is not in his catalogue (FR-166). Every catalogued product is F8's (D-19, FR-158), so the
  two features never speak about the same product;
- ADR-031's rule flagged at a market store on at least one recent night (FR-167). That is
  read from the replay in `inputs.market_recent`, never re-derived here;
- the market still sells: orderable at a market store on one of the last `max_absent`
  usable days, or running out tonight. Past `max_absent` days the store has more likely
  dropped it, and F9 does not point at what the market stopped selling.

It carries no value of any kind (FR-169, INV-081): we never see what a competitor sells,
only what it lists, so the entry states nights and stores and nothing else. Entries are
published in FR-172's order, which the surface keeps (policy `surface.engine_ordered`).
"""
from __future__ import annotations

from src.engine.inputs import EngineInputs
from src.engine.market_running_out import is_stale
from src.engine.model import CapabilityOutput, Entry, entry_id
from src.engine.registry import derive_status

CAP, SPEC = "assortment_gap", "F9-S1"
FAMILY = "assortment.market_ran_out"


def _thresholds(policy) -> dict:
    ro = policy.as_dict()["market_running_out"]
    return {"window_days": policy.assortment_gap_window_days, "max_absent": ro["max_absent"],
            "min_absent": ro["min_absent"], "prior_days": ro["prior_days"], "min_listed": ro["min_listed"]}


def _findings(inputs: EngineInputs) -> list:
    recent = inputs.market_recent
    stocked = {str(p["barcode"]) for p in inputs.products if p.get("barcode")}
    tonight = recent["on_day"]
    out = []
    for barcode, flag in recent["flagged"].items():
        if barcode in stocked:
            continue                                            # INV-080: F8's product
        still_sold = barcode in recent["listed_recent"] or tonight in flag["nights"]
        if not still_sold:
            continue                                            # SCN-153: dropped
        out.append((barcode, flag))
    # FR-172: more nights, then more stores, then the later night, then the barcode.
    out.sort(key=lambda bf: (-len(bf[1]["nights"]), -len(bf[1]["stores"]),
                             _neg_iso(max(bf[1]["nights"])), bf[0]))
    return out


def _neg_iso(day: str) -> tuple:
    """Sort key that puts the later ISO date first, inside an ascending sort."""
    y, m, d = (int(x) for x in day.split("-"))
    return (-y, -m, -d)


def _entry(barcode: str, flag: dict, recent: dict) -> Entry:
    name = recent["names"].get(barcode)
    return Entry(
        # FR-170, ADR-009: the id derives from the barcode alone, so an answer keeps applying.
        id=entry_id(FAMILY, barcode), signal_family=FAMILY, capability=CAP, barcode=barcode,
        product_name=name, department=None, action="try_product", characterisation="market_ran_out",
        evidence={"stores_ran_out": list(flag["stores"]), "nights_ran_out": len(flag["nights"]),
                  "last_ran_out": max(flag["nights"]),
                  "listed_at": list(recent["listed_tonight"].get(barcode, [])),
                  "window": dict(recent["window"]), "market_name": name},
        value=None,
        ordering_key={"name": "nights_ran_out", "value": len(flag["nights"])},
    )


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    # FR-174: the same judgement of staleness as market_running_out, so the two never disagree.
    if is_stale(inputs.running_out, inputs.run_at, inputs.policy):
        out = CapabilityOutput.unavailable(CAP, SPEC, "market_signal_stale")
        out.extras = {"on_day": inputs.running_out["on_day"]}
        return out
    recent = inputs.market_recent
    entries = [_entry(b, f, recent) for b, f in _findings(inputs)]
    return CapabilityOutput(
        id=CAP, spec=SPEC, status="available", thresholds=_thresholds(inputs.policy),
        counts={"findings": len(entries), "stores": len(inputs.running_out["stores"]),
                "usable_nights": recent["window"]["usable_nights"]},
        entries=entries,
        extras={"on_day": recent["on_day"], "recent_window": dict(recent["window"])})
