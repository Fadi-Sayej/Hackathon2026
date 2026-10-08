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

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, entry_id
from src.engine.registry import derive_status

CAP, SPEC = "competitor_position", "SPEC-003"
# ADR-043: the breaches are their own capability, which waits for the owner's rule (D-39) while the
# comparison and the purchase-cost check go on here. One pass computes both (_evaluate), so a
# product the cost floor stops is never a breach (FR-043a/b), and their order is one order.
BREACH_CAP = "policy_breach"
BREACH_COUNTS = ("breaches", "attention", "review")
BREACH_THRESHOLDS = ("policy_pct", "attention_pct")
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


def _observed(observed_at: Optional[str]) -> Optional[datetime]:
    """When the price was seen, or None when the observation does not say."""
    if not observed_at:
        return None
    try:
        seen = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    return seen if seen.tzinfo is not None else seen.replace(tzinfo=timezone.utc)


def _fresh(observed_at: Optional[str], run_at: datetime, days: int) -> bool:
    seen = _observed(observed_at)
    return seen is not None and seen >= run_at - timedelta(days=days)


def _seen_at(obs: list) -> Optional[str]:
    """The date of the newest observation: how recent the best evidence is."""
    return max((o.get("observed_at") or "") for o in obs)[:10] or None


def _is_structurally_uncomparable(p: dict, policy) -> bool:
    """Services and internal codes: a barcode shorter than the declared length is not a retail
    identifier, so no other shop can carry it and no comparison is possible (FR-052).

    The length is declared in configs/policy.yaml, not here: ARCH-GATE-004 left the predicate
    to the spec layer, so it is provisional and must move without a code change."""
    b = p["barcode"]
    return not b or len(b) < policy.uncomparable_min_barcode_digits


def run(inputs: EngineInputs) -> CapabilityOutput:
    """The comparison and the purchase-cost check: everything F3 publishes but the breaches."""
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    ev = _evaluate(inputs)
    counts = {k: v for k, v in ev["counts"].items() if k not in BREACH_COUNTS}
    thresholds = {k: v for k, v in ev["thresholds"].items() if k not in BREACH_THRESHOLDS}
    entries = [e for e in ev["entries"] if e.capability == CAP]
    figures = [Figure(k, v, "products", ["pos", "competitor"], thresholds) for k, v in counts.items()]
    figures.append(Figure("format_allowance_pct", ev["allowance_pct"], "percent", ["competitor"],
                          {"basis_count": ev["allowance_n"]}))
    out = CapabilityOutput(id=CAP, spec=SPEC, status="available", thresholds=thresholds, counts=counts,
                           entries=entries, figures=figures, notes=ev["notes"])
    out.extras = ev["extras"]
    return out


def run_breaches(inputs: EngineInputs) -> CapabilityOutput:
    """The policy breaches (FR-045a), judged against the owner's own rule (D-39, ADR-043)."""
    status, reason = derive_status(BREACH_CAP, inputs)   # no rule stated: no_price_rule
    if status == "unavailable":
        return CapabilityOutput.unavailable(BREACH_CAP, SPEC, reason)
    ev = _evaluate(inputs)
    counts = {k: ev["counts"][k] for k in BREACH_COUNTS}
    thresholds = {k: ev["thresholds"][k] for k in BREACH_THRESHOLDS}
    figures = [Figure(k, v, "products", ["pos", "competitor"], thresholds) for k, v in counts.items()]
    out = CapabilityOutput(id=BREACH_CAP, spec=SPEC, status="available", thresholds=thresholds, counts=counts,
                           entries=[e for e in ev["entries"] if e.capability == BREACH_CAP], figures=figures)
    out.extras = {"rule": inputs.price_rule}      # what it was judged by, and who stated it when
    return out


def _evaluate(inputs: EngineInputs) -> dict:
    # D-39, ADR-043: the owner's own rule, or None until it is stated. Without it no breach is
    # judged; a purchase-cost finding carries it as context only, and never needs it (FR-043a/b).
    rule_pct = inputs.price_rule["max_premium_pct"] if inputs.price_rule else None
    # An empty observations list is DATA — we collected and found nothing for these
    # products — and FR-051 requires each of them to be counted "no comparison" rather
    # than nothing at all. Absence is None, and derive_status above has already refused
    # that case ("a missing input is None — never an empty frame", registry.py).
    policy, run_at, stores = inputs.policy, inputs.run_at, inputs.stores
    withdrawn = inputs.withdrawn or set()
    floor = stores.min_affinity

    approved = {m["internal_barcode"] for m in inputs.matches if m.get("approved", True)}
    by_barcode: dict = {}
    # Dated, and older than the bound. An undated observation is refused by _fresh too, but
    # lands in neither: "too old" is a claim about its age, and its age is unknown.
    stale: dict = {}
    for o in inputs.observations:
        if o["barcode"] not in approved and inputs.matches:
            pass                                                   # observations are already barcode-keyed
        if not _fresh(o["observed_at"], run_at, policy.freshness_days):
            if _observed(o["observed_at"]) is not None:
                stale.setdefault(o["barcode"], []).append(o)
            continue
        by_barcode.setdefault(o["barcode"], []).append(o)

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
              # Counted in the product loop, over the comparable population like every other
              # coverage count. It used to be every stale barcode in the competitor feed: 1,085
              # on 2026-09-23, where this reads 53. 1,028 were barcodes the store does not sell.
              "stale_skipped": 0}
    entries: list[Entry] = []
    position: dict = {}
    # FR-102's problem in this capability's own terms (#137). Six findings reach the owner
    # from 860 evaluated products; the other 854 were compared against a live reference and
    # found acceptably priced, and that comparison was computed and dropped. A page that
    # answers "what is this product's position" needs the comparison, not the finding.
    #
    # Every MATCHED product gets a row, and a row carries either the comparison or the
    # reason there is none. Publishing only the evaluated ones would make the page say
    # nothing for a product skipped as stale — indistinguishable, to the owner, from "no
    # competitor sells this". That is rule 8 and D-3: when a number cannot be stated, say so,
    # do not fall silent. Measured, the two options differ by 1 KB gzipped.
    #
    # So does every product seen ONLY in stale observations. It is not matched — nothing
    # fresh — and until 2026-09-23 that meant no row, which was exactly the silence above.
    comparison: list = []

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
            old = stale.get(b)
            if old:
                # SCN-047: not surfaced, and any display marks the observation's age — which
                # needs the age published. Our own missing price is named first, as below.
                reason = "stale" if p["shelf_price"] else "no_shelf_price"
                if reason == "stale":
                    counts["stale_skipped"] += 1
                comparison.append({"barcode": b, "shelf_price": p["shelf_price"], "stores": len(old),
                                   "observed_at": _seen_at(old), "reference": None, "premium_pct": None,
                                   "uncompared_reason": reason})
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
        seen_at = _seen_at(obs)
        # Barcode and figures only. `product_name` and `department` are in catalogue.json
        # (ADR-024) against the same barcode, and a page showing this needs that file
        # anyway — carrying them here too costs 41 KB gzipped for a second copy of the
        # truth, which is what §20.1 deleted src/data/*.js for. Measured both ways.
        row = {"barcode": b, "shelf_price": p["shelf_price"], "stores": len(obs),
               "observed_at": seen_at, "reference": None, "premium_pct": None,
               "uncompared_reason": None}
        if reference is None or not p["shelf_price"]:
            counts["no_comparison"] += 1
            # Which of the two it was, because they are different facts to a reader: no
            # comparable price at all, versus a product of ours with no shelf price to compare.
            row["uncompared_reason"] = "no_shelf_price" if not p["shelf_price"] else "no_reference"
            comparison.append(row)
            continue
        if p["cost_price"] is None:
            counts["no_cost_skipped"] += 1                          # FR-043d: no judgement without a cost
            # The reference IS known here; only the judgement is withheld. Publishing it
            # lets the page show his position without claiming the policy verdict.
            row["reference"] = reference
            row["premium_pct"] = round((p["shelf_price"] / reference["value"] - 1.0) * 100.0, 2)
            row["uncompared_reason"] = "no_cost"
            comparison.append(row)
            continue
        counts["evaluated"] += 1

        premium_pct = (p["shelf_price"] / reference["value"] - 1.0) * 100.0
        row["reference"] = reference
        row["premium_pct"] = round(premium_pct, 2)
        comparison.append(row)
        sources = [{"store_id": o["store_id"], "store_name": o["store_name"], "format": o["store_format"],
                    "price": o["price"], "observed_at": o["observed_at"],
                    "role": "comparable" if o["affinity"] >= floor else "context"} for o in obs]
        evidence = {"shelf_price": p["shelf_price"], "cost_price": p["cost_price"], "reference": reference,
                    "premium_pct": round(premium_pct, 2), "policy_pct": rule_pct,
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
        if rule_pct is None or premium_pct <= rule_pct:
            continue
        counts["breaches"] += 1
        attention = premium_pct > policy.attention_pct
        counts["attention" if attention else "review"] += 1
        entries.append(Entry(id=entry_id("competitor.policy_breach", b), signal_family="competitor.policy_breach",
                             capability=BREACH_CAP, barcode=b, product_name=p["product_name"],
                             department=p["department"], action="review_policy",
                             characterisation="policy_breach_attention" if attention else "policy_breach_review",
                             evidence=evidence, value=None, attention="today" if attention else "review",
                             ordering_key={"name": "premium_pct", "value": round(premium_pct, 2)}))

    entries.sort(key=lambda e: (0 if e.attention == "today" else 1, -e.ordering_key["value"], e.barcode))
    for row in position.values():
        diffs = row.pop("_diffs")
        row["median_diff_pct"] = round(statistics.median(diffs), 2) if diffs else None
    thresholds = {"policy_pct": rule_pct, "attention_pct": policy.attention_pct,
                  "cost_floor_pct": policy.cost_floor_pct, "format_allowance_pct": allowance_pct,
                  "format_allowance_basis_count": allowance_n, "freshness_days": policy.freshness_days,
                  "comparability_floor": floor}
    notes = [] if allowance_pct is not None else ["format_allowance_unmeasurable"]
    return {"counts": counts, "thresholds": thresholds, "entries": entries, "notes": notes,
            "allowance_pct": allowance_pct, "allowance_n": allowance_n,
            "extras": {"position": sorted(position.values(), key=lambda r: (-r["affinity"], r["store_id"])),
                       # Sorted by barcode for the reason ADR-024 sorts the catalogue: the nightly
                       # commits this file, so the bytes must repeat when the data does.
                       "comparison": sorted(comparison, key=lambda r: str(r["barcode"] or ""))}}
