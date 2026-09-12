# src/engine/price_consistency.py
"""SPEC-001 — the store's shelf price against its own delivery-platform price.

Four states; the ceiling is DERIVED from the store's own markup distribution
(FR-004) as the last band boundary where density collapses. Inverted = a
confirmed per-sale loss; above the ceiling = a question, never a loss (FR-008)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, Value, entry_id
from src.engine.registry import derive_status

CAP, SPEC = "price_consistency", "SPEC-001"
IDENTICAL_EPS = 0.005


@dataclass(frozen=True)
class CeilingResult:
    pct: Optional[float]
    method: str
    bands: list


def derive_ceiling(markups: list, *, band_pct: float, drop_ratio: float, min_band_count: int) -> CeilingResult:
    """Bands of `band_pct` over the positive markups. A candidate ceiling is the upper
    edge of a band whose successor holds at most (1 − drop_ratio) of its count, provided
    the band itself holds at least `min_band_count`. The ceiling is the candidate whose
    own band holds the MOST products; ties take the HIGHER edge (ADR-015).

    The store's policy is a mass, not a boundary — the band where that mass ends is the
    policy's edge (INV-002). Selecting the last candidate instead reads a 24-item tail
    band on the pilot export as a second policy and returns 26% where the approved intent
    derives 18%; selecting the first returns 2% on this module's own fixture."""
    positive = [m for m in markups if m > 0]
    if not positive:
        return CeilingResult(None, "densest_density_collapse", [])
    top = max(positive)
    n_bands = int(top // band_pct) + 1
    counts = [0] * n_bands
    for m in positive:
        counts[int(m // band_pct)] += 1
    bands = [{"from": i * band_pct, "to": (i + 1) * band_pct, "count": c} for i, c in enumerate(counts)]
    ceiling, best_count = None, 0
    for i in range(1, n_bands):
        prev, cur = counts[i - 1], counts[i]
        if prev >= min_band_count and cur <= (1 - drop_ratio) * prev:
            if prev >= best_count:                   # a tie extends policy upward
                ceiling, best_count = float(i * band_pct), prev
    return CeilingResult(ceiling, "densest_density_collapse", bands)


def markup_pct(shelf: float, delivery: float) -> float:
    return (delivery / shelf - 1.0) * 100.0


def classify(shelf: float, delivery: float, ceiling_pct: Optional[float]) -> str:
    if abs(delivery - shelf) < IDENTICAL_EPS:
        return "identical"
    if delivery < shelf:
        return "inverted"
    if ceiling_pct is None:
        return "undetermined"
    return "above" if markup_pct(shelf, delivery) > ceiling_pct else "within"


def _is_artefact(p: dict, policy) -> bool:
    if p["shelf_price"] < policy.artefact_min_price:
        return True
    return p["cost_price"] is not None and p["cost_price"] > policy.artefact_cost_ratio * p["shelf_price"]


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    policy = inputs.policy
    withdrawn = inputs.withdrawn or set()
    paired = [p for p in inputs.products
              if p["has_identifier"] and p["barcode"] not in withdrawn
              and p["shelf_price"] is not None and p["delivery_price"] is not None]
    if not paired:
        return CapabilityOutput.unavailable(CAP, SPEC, "no_delivery_prices")

    excluded_artefact = [p for p in paired if _is_artefact(p, policy)]
    kept = [p for p in paired if not _is_artefact(p, policy)]
    excluded_gap = [p for p in kept if abs(markup_pct(p["shelf_price"], p["delivery_price"])) > policy.max_credible_gap_pct]
    kept = [p for p in kept if abs(markup_pct(p["shelf_price"], p["delivery_price"])) <= policy.max_credible_gap_pct]

    markups = [markup_pct(p["shelf_price"], p["delivery_price"]) for p in kept if p["delivery_price"] > p["shelf_price"] + IDENTICAL_EPS]
    ceiling = derive_ceiling(markups, band_pct=policy.ceiling_band_pct, drop_ratio=policy.ceiling_drop_ratio,
                             min_band_count=policy.ceiling_min_band_count)
    notes: list[str] = []
    ceiling_pct = ceiling.pct
    if ceiling_pct is None:
        notes.append("ceiling_undetermined")
        # INV-003 again, on the other path. "No ceiling could be derived" and "the
        # population cannot carry a ceiling" are different findings, and only the
        # second is a broken threshold. A single band holding more than the density
        # bound of the whole pair set is the second: there is no collapse to find
        # because almost every product shares one markup.
        if ceiling.bands:
            dominant = max(b["count"] for b in ceiling.bands)
            if kept and dominant > 0.10 * len(kept):
                notes.append("ceiling_degenerate")

    states = {p["barcode"]: classify(p["shelf_price"], p["delivery_price"], ceiling_pct) for p in kept}
    # INV-003 / NFR-003: a ceiling that surfaces ≥10 % of the pair set describes normal pricing.
    if ceiling_pct is not None:
        surfaced = sum(1 for s in states.values() if s in ("above", "inverted"))
        if surfaced >= len(kept) or surfaced > 0.10 * len(kept):
            notes.append("ceiling_degenerate")
            ceiling_pct = None
            states = {p["barcode"]: classify(p["shelf_price"], p["delivery_price"], None) for p in kept}

    entries: list[Entry] = []
    for p in kept:
        s, b = states[p["barcode"]], p["barcode"]
        shelf, delivery = p["shelf_price"], p["delivery_price"]
        evidence = {"shelf_price": shelf, "delivery_price": delivery, "difference": round(delivery - shelf, 2),
                    "markup_pct": round(markup_pct(shelf, delivery), 2), "ceiling_pct": ceiling_pct}
        if s == "inverted":
            loss = round(shelf - delivery, 2)
            entries.append(Entry(id=entry_id("price.inverted", b), signal_family="price.inverted",
                                 capability=CAP, barcode=b, product_name=p["product_name"],
                                 department=p["department"], action="verify_price", characterisation="confirmed_loss",
                                 evidence={**evidence, "commission_compounds": True},
                                 value=Value(loss, "per_sale", "confirmed"),
                                 ordering_key={"name": "loss_per_sale", "value": loss}))
        elif s == "above":
            entries.append(Entry(id=entry_id("price.above_ceiling", b), signal_family="price.above_ceiling",
                                 capability=CAP, barcode=b, product_name=p["product_name"],
                                 department=p["department"], action="verify_price", characterisation="question",
                                 evidence=evidence, value=None,
                                 ordering_key={"name": "markup_pct", "value": evidence["markup_pct"]}))
    entries.sort(key=lambda e: (0 if e.characterisation == "confirmed_loss" else 1, -e.ordering_key["value"], e.barcode))

    counts = {"population": len(paired),
              "identical": sum(1 for s in states.values() if s == "identical"),
              "within": None if ceiling_pct is None else sum(1 for s in states.values() if s == "within"),
              "above": None if ceiling_pct is None else sum(1 for s in states.values() if s == "above"),
              "inverted": sum(1 for s in states.values() if s == "inverted"),
              "excluded_artefact": len(excluded_artefact), "excluded_gap": len(excluded_gap)}
    # ARCH-GATE-006: the ceiling is derived AFTER the FR-074 withdrawn exclusion, so a
    # withdrawal moves the ceiling and the population must travel with the figure.
    #
    # Reported, not asserted. ADR-020 makes the published population a policy setting, so
    # this run may have been given no withdrawn set at all — claiming the exclusion happened
    # when it did not is the kind of unearned label the whole provenance layer exists to stop.
    excludes_withdrawn = bool(inputs.withdrawn)
    thresholds = {"ceiling_pct": ceiling_pct, "ceiling_method": ceiling.method, "ceiling_bands": ceiling.bands,
                  "ceiling_population": len(kept), "ceiling_population_excludes_withdrawn": excludes_withdrawn,
                  "artefact_min_price": policy.artefact_min_price, "artefact_cost_ratio": policy.artefact_cost_ratio,
                  "max_credible_gap_pct": policy.max_credible_gap_pct}
    figures = [Figure(k, v, "products", ["pos"], {"ceiling_pct": ceiling_pct}) for k, v in counts.items()]
    figures.append(Figure("ceiling_pct", ceiling_pct, "percent", ["pos"],
                          {"method": ceiling.method, "population": len(kept),
                           "excludes_withdrawn": excludes_withdrawn}))
    return CapabilityOutput(id=CAP, spec=SPEC, status="available", thresholds=thresholds, counts=counts,
                            entries=entries, figures=figures, notes=notes)
