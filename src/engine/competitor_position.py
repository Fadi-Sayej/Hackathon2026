# src/engine/competitor_position.py
"""SPEC-003 — is our price reasonable against the neighbours?

Order is load-bearing (FR-043b): freshness → balanced reference → COST FLOOR →
declared policy → attention split. A competitor's price is never a benchmark on
its own (INV-026) and never produces a recommendation that leaves the owner at or
below his own purchase cost (INV-025)."""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.engine.inputs import OUR_FORMAT, EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, entry_id
from src.engine.registry import derive_status

CAP, SPEC = "competitor_position", "SPEC-003"
SUPERMARKET_FORMATS = ("supermarket", "hypermarket", "midsize_grocery")


def measure_format_allowance(pairs: list) -> tuple:
    """FR-044b — the typical premium of same-format stores over supermarkets,
    measured from products holding both prices. Never an assumed constant."""
    diffs = [(same / sup - 1.0) * 100.0 for sup, same in pairs if sup and sup > 0 and same]
    if not diffs:
        return None, 0
    return round(statistics.median(diffs), 4), len(diffs)


def balanced_reference(same_format_min: Optional[float], supermarket_min: Optional[float],
                       allowance_pct: Optional[float]) -> Optional[dict]:
    if same_format_min is not None and supermarket_min is not None:
        return {"value": round((same_format_min + supermarket_min) / 2.0, 4), "kind": "midpoint",
                "same_format": same_format_min, "supermarket": supermarket_min, "allowance_pct": None}
    if same_format_min is not None and supermarket_min is None:
        return {"value": round(same_format_min, 4), "kind": "same_format_only",
                "same_format": same_format_min, "supermarket": None, "allowance_pct": None}
    if supermarket_min is not None and allowance_pct is not None:
        return {"value": round(supermarket_min * (1.0 + allowance_pct / 100.0), 4),
                "kind": "supermarket_plus_allowance", "same_format": None,
                "supermarket": supermarket_min, "allowance_pct": allowance_pct}
    return None                                                    # FR-044c: no comparison


def _fresh(observed_at: Optional[str], run_at: datetime, days: int) -> bool:
    if not observed_at:
        return False
    try:
        seen = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    return seen >= run_at - timedelta(days=days)


def _is_structurally_uncomparable(p: dict, policy) -> bool:
    """Services and internal codes: a barcode shorter than the declared length is not a retail
    identifier, so no other shop can carry it and no comparison is possible (FR-052).

    The length is declared in configs/policy.yaml, not here: ARCH-GATE-004 left the predicate
    to the spec layer, so it is provisional and must move without a code change."""
    b = p["barcode"]
    return not b or len(b) < policy.uncomparable_min_barcode_digits


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    # An empty observations list is DATA — we collected and found nothing for these
    # products — and FR-051 requires each of them to be counted "no comparison" rather
    # than nothing at all. Absence is None, and derive_status above has already refused
    # that case ("a missing input is None — never an empty frame", registry.py).
    policy, run_at, stores = inputs.policy, inputs.run_at, inputs.stores
    withdrawn = inputs.withdrawn or set()
    floor = stores.min_affinity

    approved = {m["internal_barcode"] for m in inputs.matches if m.get("approved", True)}
    by_barcode: dict = {}
    stale_only: set = set()
    for o in inputs.observations:
        if o["barcode"] not in approved and inputs.matches:
            pass                                                   # observations are already barcode-keyed
        if not _fresh(o["observed_at"], run_at, policy.freshness_days):
            stale_only.add(o["barcode"]); continue
        by_barcode.setdefault(o["barcode"], []).append(o)
    stale_only -= set(by_barcode)

    # Format allowance, measured once over products holding BOTH a supermarket and a
    # same-format price (FR-044b).
    pairs = []
    for b, obs in by_barcode.items():
        sup = [o["price"] for o in obs if o["store_format"] in SUPERMARKET_FORMATS]
        same = [o["price"] for o in obs if o["affinity"] >= floor]
        if sup and same:
            pairs.append((min(sup), min(same)))
    allowance_pct, allowance_n = measure_format_allowance(pairs)

    counts = {"catalogue": len(inputs.products), "comparable_population": 0, "matched": 0,
              "structurally_uncomparable": 0, "no_comparison": 0, "evaluated": 0, "breaches": 0,
              "attention": 0, "review": 0, "purchase_cost_findings": 0, "no_cost_skipped": 0,
              "stale_skipped": len(stale_only)}
    entries: list[Entry] = []
    position: dict = {}

    for p in inputs.products:
        b = p["barcode"]
        if b in withdrawn:
            continue
        if _is_structurally_uncomparable(p, policy):
            counts["structurally_uncomparable"] += 1
            continue
        counts["comparable_population"] += 1
        obs = by_barcode.get(b) or []
        if not obs:
            counts["no_comparison"] += 1
            continue
        counts["matched"] += 1

        for o in obs:                                              # FR-053 position, incl. cheaper
            row = position.setdefault(o["store_id"], {"store_id": o["store_id"], "store_name": o["store_name"],
                                                      "format": o["store_format"], "affinity": o["affinity"],
                                                      "matched": 0, "cheaper_here": 0, "dearer_here": 0, "_diffs": []})
            row["matched"] += 1
            if p["shelf_price"]:
                diff = (p["shelf_price"] / o["price"] - 1.0) * 100.0
                row["_diffs"].append(diff)
                if diff < 0:
                    row["cheaper_here"] += 1
                elif diff > 0:
                    row["dearer_here"] += 1

        same = [o for o in obs if o["affinity"] >= floor]
        sup = [o for o in obs if o["store_format"] in SUPERMARKET_FORMATS]
        reference = balanced_reference(min((o["price"] for o in same), default=None),
                                       min((o["price"] for o in sup), default=None), allowance_pct)
        if reference is None or not p["shelf_price"]:
            counts["no_comparison"] += 1
            continue
        if p["cost_price"] is None:
            counts["no_cost_skipped"] += 1                          # FR-043d: no judgement without a cost
            continue
        counts["evaluated"] += 1

        premium_pct = (p["shelf_price"] / reference["value"] - 1.0) * 100.0
        sources = [{"store_id": o["store_id"], "store_name": o["store_name"], "format": o["store_format"],
                    "price": o["price"], "observed_at": o["observed_at"],
                    "role": "comparable" if o["affinity"] >= floor else "context"} for o in obs]
        evidence = {"shelf_price": p["shelf_price"], "cost_price": p["cost_price"], "reference": reference,
                    "premium_pct": round(premium_pct, 2), "policy_pct": policy.price_policy_pct,
                    "attention_pct": policy.attention_pct, "cost_floor_pct": policy.cost_floor_pct,
                    "sources": sources, "format_note": "part of any difference is attributable to store format"}

        # FR-043a/b: the cost floor is evaluated BEFORE the policy and cannot be overridden.
        if reference["value"] < p["cost_price"] * (1.0 + policy.cost_floor_pct / 100.0):
            counts["purchase_cost_findings"] += 1
            entries.append(Entry(id=entry_id("competitor.purchase_cost", b),
                                 signal_family="competitor.purchase_cost", capability=CAP, barcode=b,
                                 product_name=p["product_name"], department=p["department"],
                                 action="check_purchase_cost", characterisation="purchase_cost",
                                 evidence=evidence, value=None, attention="review",
                                 ordering_key={"name": "premium_pct", "value": round(premium_pct, 2)}))
            continue
        if premium_pct <= policy.price_policy_pct:
            continue
        counts["breaches"] += 1
        attention = premium_pct > policy.attention_pct
        counts["attention" if attention else "review"] += 1
        entries.append(Entry(id=entry_id("competitor.policy_breach", b), signal_family="competitor.policy_breach",
                             capability=CAP, barcode=b, product_name=p["product_name"],
                             department=p["department"], action="review_policy",
                             characterisation="policy_breach_attention" if attention else "policy_breach_review",
                             evidence=evidence, value=None, attention="today" if attention else "review",
                             ordering_key={"name": "premium_pct", "value": round(premium_pct, 2)}))

    entries.sort(key=lambda e: (0 if e.attention == "today" else 1, -e.ordering_key["value"], e.barcode))
    for row in position.values():
        diffs = row.pop("_diffs")
        row["median_diff_pct"] = round(statistics.median(diffs), 2) if diffs else None
    thresholds = {"policy_pct": policy.price_policy_pct, "attention_pct": policy.attention_pct,
                  "cost_floor_pct": policy.cost_floor_pct, "format_allowance_pct": allowance_pct,
                  "format_allowance_basis_count": allowance_n, "freshness_days": policy.freshness_days,
                  "comparability_floor": floor}
    notes = [] if allowance_pct is not None else ["format_allowance_unmeasurable"]
    figures = [Figure(k, v, "products", ["pos", "competitor"], thresholds) for k, v in counts.items()]
    figures.append(Figure("format_allowance_pct", allowance_pct, "percent", ["competitor"],
                          {"basis_count": allowance_n}))
    out = CapabilityOutput(id=CAP, spec=SPEC, status="available", thresholds=thresholds, counts=counts,
                           entries=entries, figures=figures, notes=notes)
    out.extras = {"position": sorted(position.values(), key=lambda r: (-r["affinity"], r["store_id"]))}
    return out
