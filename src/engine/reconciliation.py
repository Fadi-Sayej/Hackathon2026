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
from src.engine.stock_date import usable_stock_date
from src.internal_pos.sales_importer import evidence_window

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


def _detection_entries(inputs: EngineInputs, window) -> list:
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
                      "unaccounted": round(missing, 2), "window_id": window.window_id,
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
    # sales_summary.parquet, so a summary written by an older run survived with its
    # sums intact and no NULL to find. Reproduced: 439 findings published `available`,
    # over a window nobody chose. The stock date is a fact the engine already holds, so
    # the guard reads the fact. (Since ADR-026 the summary carries no cut at all — the
    # figures are cut at load from this run's date — so a surviving summary can no longer
    # carry an old one either.)
    # `.strip()` is not decoration: a whitespace-only value is truthy, so `if not
    # as_of` alone let "   " through to date.fromisoformat() in _sales_import, which
    # raises — a capability_error, which is a worse answer than an honest refusal.
    # Found by mutation, then by the test written against it.
    # usable_stock_date is the single definition both halves ask, so the summary
    # cannot be windowed on a date the capability would have refused, or refused on
    # one the summary used. It rejects a blank, an unparseable string and a future
    # date alike — all three are "we do not know when the stock was counted".
    # `as_of_source` travels with `as_of` for the reason inputs.py already gives: a date is
    # not provenance until you know how it was arrived at. A `file_mtime` date is the
    # checkout time, not a stock count — see stock_date.UNUSABLE_SOURCES.
    pos_vintage = ((inputs.vintages or {}).get("pos") or {})
    if usable_stock_date(pos_vintage.get("as_of"),
                         source=pos_vintage.get("as_of_source")) is None:
        return CapabilityOutput.unavailable(RECON, SPEC, "unknown_stock_date")

    # ADR-026: the window is carved from the one boundary load_inputs cut the figures at,
    # so the period published beside the arithmetic is the period of the arithmetic. That
    # boundary is null exactly when load_inputs found the stock date unusable. The check
    # above can still pass beside it: usable_stock_date reads the wall clock, so a count
    # dated tomorrow at load is dated today here if the run crosses UTC midnight. That is
    # the same unknown, and it gets the same honest refusal, never a window carved from
    # nothing and never a crash.
    reconcile_before = ((inputs.vintages or {}).get("sales") or {}).get("reconcile_before")
    if reconcile_before is None:
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

    # The same strict `<` the cut applies, over the same monthly rows, so the window is the
    # months the figures were summed over. Through load_inputs the guard above leaves at
    # least one; handed inputs that leave none, a window of no months is refused rather than
    # published as "None..None" beside findings.
    window = evidence_window([m for m in inputs.window.months if m < reconcile_before],
                             inputs.policy.full_annual_cycle_months)
    if not window.months:
        return CapabilityOutput.unavailable(RECON, SPEC, "no_sales_evidence")
    flagged = _detection_entries(inputs, window)
    return CapabilityOutput(
        id=RECON, spec=SPEC, status="available", window=window,
        thresholds={}, counts={"flagged": len(flagged)}, entries=flagged,
        figures=[Figure("flagged", len(flagged), "products", ["pos", "sales"],
                        {"window": window.window_id})])


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
