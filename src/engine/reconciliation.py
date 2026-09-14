# src/engine/reconciliation.py
"""SPEC-002 — two capabilities, one module.

`reconciliation` needs the monthly reports to close the arithmetic:

    implied_opening = recorded_stock − receipts + units_sold

A negative implied opening is arithmetically impossible, so the three numbers cannot all
be true. `hygiene` needs only the inventory: negative stock, no usable barcode or an
absent price is wrong on its own evidence.

They are two capabilities because they fail on different days — the inventory CSV always
arrives, the seven monthly reports may not (ADR-014, SPEC-002 §11). Neither attaches money
(FR-023, INV-010, INV-013); the ordering key is the gap ratio (FR-024)."""
from __future__ import annotations

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, entry_id
from src.engine.registry import derive_status

SPEC = "SPEC-002"
RECON, HYGIENE = "reconciliation", "hygiene"
HYGIENE_ORDER = {"negative_stock": 0, "no_identifier": 1, "absent_price": 2,
                 "conflicting_duplicate": 3}


def _hygiene_entries(inputs: EngineInputs) -> list:
    withdrawn = inputs.withdrawn or set()
    out = []
    for p in inputs.products:
        if p["barcode"] in withdrawn:
            continue
        reasons = []
        if p["recorded_stock"] is not None and p["recorded_stock"] < 0:
            reasons.append("negative_stock")
        if not p["has_identifier"]:
            reasons.append("no_identifier")
        if p["shelf_price"] is None:
            reasons.append("absent_price")
        for reason in reasons:
            family = f"hygiene.{reason}"
            out.append(Entry(
                id=entry_id(family, p["barcode"] or p["product_name"]), signal_family=family,
                capability=HYGIENE, barcode=p["barcode"], product_name=p["product_name"],
                department=p["department"], action="fix_record", characterisation="hygiene",
                evidence={"reason": reason,
                          "recorded_stock": p["recorded_stock"] if reason == "negative_stock" else None},
                value=None, ordering_key={"name": "hygiene_order", "value": HYGIENE_ORDER[reason]}))
    out.extend(_conflicting_entries(inputs))
    return sorted(out, key=lambda e: (e.ordering_key["value"], e.product_name or "", e.barcode or ""))


def _conflicting_entries(inputs: EngineInputs) -> list:
    """ADR-019. A barcode whose rows disagree never reaches inputs.products, so it cannot be
    found by walking them — it arrives on its own field. The record carries the disagreeing
    fields and both values and no money: the prices are precisely what is in doubt (D-1).

    ADR-022: a conflict can now be a barcode-less name. Its id falls back to the name the
    same way `_hygiene_entries` does — `entry_id(family, None)` would give every
    barcode-less conflict one shared id, which is #89 again, in the one record that exists
    to report it."""
    family = "hygiene.conflicting_duplicate"
    out = []
    for c in inputs.conflicting or []:
        out.append(Entry(
            id=entry_id(family, c["barcode"] or c.get("product_name")), signal_family=family,
            capability=HYGIENE, barcode=c["barcode"], product_name=c.get("product_name"),
            department=None, action="fix_record", characterisation="hygiene",
            evidence={"reason": "conflicting_duplicate", "fields": c["fields"]},
            value=None,
            ordering_key={"name": "hygiene_order", "value": HYGIENE_ORDER["conflicting_duplicate"]}))
    return out


def _detection_entries(inputs: EngineInputs) -> list:
    withdrawn = inputs.withdrawn or set()
    out = []
    for p in inputs.products:
        b = p["barcode"]
        if not b or b in withdrawn or p["recorded_stock"] is None:
            continue
        s = inputs.sales_summary.get(b)
        # A row whose windowed figures are absent was summarised without a usable
        # window. Skipping it and defaulting it to 0.0 produce the same output — the
        # row is not flagged either way — so this is defence, not the thing keeping
        # the capability honest. What does that is the pair of guards in run(): the
        # whole capability goes unavailable rather than publishing a thinner list.
        # All three columns are checked, not just receipts: `float()` and `int()`
        # below would raise on any one of them, and a TypeError here becomes
        # `capability_error`, which is a worse answer than an honest skip.
        if s is not None and any(s.get(k) is None for k in
                                 ("reconcile_receipts", "reconcile_units", "reconcile_months")):
            continue
        receipts = float(s["reconcile_receipts"]) if s else 0.0
        if receipts <= 0:
            continue                                     # FR-021: nothing to close without receipts
        units = float(s["reconcile_units"])
        implied = p["recorded_stock"] - receipts + units
        if implied >= 0:
            continue
        missing = -implied
        out.append(Entry(
            id=entry_id("recon.impossible_opening", b), signal_family="recon.impossible_opening",
            capability=RECON, barcode=b, product_name=p["product_name"],
            department=p["department"], action="count_product", characterisation="inconsistent",
            evidence={"recorded_stock": p["recorded_stock"], "receipts": receipts, "units_sold": units,
                      "unaccounted": round(missing, 2), "window_id": inputs.window.window_id,
                      "reconcile_months": int(s["reconcile_months"])},
            value=None, ordering_key={"name": "gap_ratio", "value": round(missing / receipts, 4)}))
    return sorted(out, key=lambda e: (-e.ordering_key["value"], e.barcode))


def run(inputs: EngineInputs) -> CapabilityOutput:
    """The detection half. Unavailable without receipts — never 'available with zero'."""
    status, reason = derive_status(RECON, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(RECON, SPEC, reason)

    # Two rule-level unavailabilities, neither expressible by a `requires` list.
    # derive_status's contract allows a capability to make itself MORE unavailable,
    # never more available.
    #
    # The first asks the vintage directly rather than inferring it from NULLs in the
    # summary. Inferring was the first version of this guard and it had a hole: when
    # no monthly report parses, import_sales returns early and does NOT rewrite
    # sales_summary.parquet, so a summary written by an older run survives with its
    # full-history sums intact and no NULL to find. Reproduced: 439 findings
    # published `available`, over a window nobody chose. The stock date is a fact the
    # engine already holds, so the guard reads the fact.
    as_of = ((inputs.vintages or {}).get("pos") or {}).get("as_of")
    if not as_of:
        return CapabilityOutput.unavailable(RECON, SPEC, "unknown_stock_date")

    # The second: the date is known, but it precedes every month we have, so no
    # month is inside the reconciliation window. Every row then carries
    # reconcile_receipts 0.0, the `receipts <= 0` skip below swallows all of them,
    # and the capability would publish `available` with zero findings — "reconciled,
    # nothing missing" when nothing was reconciled at all. Measured: a 2025-12-31
    # count against Jan–Jul reports zeroes all 1,778 rows. `no_sales_evidence` is
    # literally what this is — there is none before the count.
    if inputs.sales_summary and not any(
            (row.get("reconcile_months") or 0) > 0 for row in inputs.sales_summary.values()):
        return CapabilityOutput.unavailable(RECON, SPEC, "no_sales_evidence")

    flagged = _detection_entries(inputs)
    return CapabilityOutput(
        id=RECON, spec=SPEC, status="available", window=inputs.window,
        thresholds={}, counts={"flagged": len(flagged)}, entries=flagged,
        figures=[Figure("flagged", len(flagged), "products", ["pos", "sales"],
                        {"window": inputs.window.window_id})])


def run_hygiene(inputs: EngineInputs) -> CapabilityOutput:
    """The hygiene half. Depends on the inventory alone, so it survives a missing report."""
    status, reason = derive_status(HYGIENE, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(HYGIENE, SPEC, reason)
    entries = _hygiene_entries(inputs)
    counts = {reason_name: sum(1 for e in entries if e.evidence["reason"] == reason_name)
              for reason_name in HYGIENE_ORDER}
    return CapabilityOutput(
        id=HYGIENE, spec=SPEC, status="available",
        thresholds={}, counts=counts, entries=entries,
        figures=[Figure(name, counts[name], "records", ["pos"]) for name in HYGIENE_ORDER])
