"""
restock_reconcile.py — check inferred restocks against recorded deliveries.

src/snapshots/velocity.py infers a restock from any rise in stock between two
snapshots, because until the receiving ledger existed nothing recorded real
deliveries. That inference is now checkable, and the disagreements are the
interesting part:

  under_recorded  stock rose more than the ledger says arrived — a delivery was
                  not recorded, or a stock count was corrected upward.
  over_recorded   more was recorded than the stock ever rose — the goods sold
                  through inside the interval, or the quantity was mistyped.
  no_receipts     stock rose and nothing was recorded at all.
  unobserved      a delivery was recorded for a product no snapshot has seen.

This is deliberately NOT the full inventory identity. Closing
`expected = last_counted + received - sold` needs a dated opening count and a
dated sales series, and the POS export provides neither.

`intervals` is whatever `build_intervals()` in src/snapshots/velocity.py
returns: a list of one dict per snapshot pair, each carrying a `movement` map
of `barcode -> {"sold": ..., "restocked": ...}` (see velocity.py:237, and how
compute_velocity() itself reads `item["movement"]`). There is no top-level
`barcode` or `restocked` key on an interval — the restock amount for a given
barcode is nested inside its own interval's movement map, and a barcode can
appear in several intervals, which is why the totals below are summed rather
than looked up once.
"""

from __future__ import annotations

from typing import Any, Optional

from src.expiry.expiry_tracking import parse_expiry_date as _parse_date

# One unit of slack. Snapshots are taken at a moment; a delivery booked minutes
# either side of one lands in the neighbouring interval, and chasing a
# single-unit disagreement would bury the real ones.
RECONCILE_TOLERANCE_UNITS = 1.0


def _clean(value: Any) -> str:
    return str(value if value is not None else "").strip()


def received_by_barcode(
    receipts: list[dict[str, Any]],
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> dict[str, float]:
    """Total units received per barcode, optionally within [start, end] inclusive."""
    start_date = _parse_date(start) if start else None
    end_date = _parse_date(end) if end else None

    totals: dict[str, float] = {}
    for row in receipts:
        barcode = _clean(row.get("barcode"))
        raw_day = _clean(row.get("received_at"))
        if not barcode or not raw_day:
            continue
        try:
            day = _parse_date(raw_day)
            quantity = float(_clean(row.get("quantity")))
        except ValueError:
            continue
        if start_date and day < start_date:
            continue
        if end_date and day > end_date:
            continue
        totals[barcode] = totals.get(barcode, 0.0) + quantity
    return totals


def _inferred_by_barcode(intervals: list[dict[str, Any]]) -> dict[str, float]:
    """Total inferred restock per barcode, summed across every interval it appears in.

    Each interval's movement map only covers the barcodes present in BOTH of
    that interval's two snapshots (see build_intervals's `if prev_value is
    None: continue`), so a barcode's total restock is scattered across
    whichever intervals it was observed in, not held in one place.
    """
    totals: dict[str, float] = {}
    for interval in intervals:
        movement = interval.get("movement") or {}
        for barcode, move in movement.items():
            clean_barcode = _clean(barcode)
            if not clean_barcode:
                continue
            try:
                restocked = float((move or {}).get("restocked") or 0.0)
            except (TypeError, ValueError):
                continue
            totals[clean_barcode] = totals.get(clean_barcode, 0.0) + restocked
    return totals


def _verdict(inferred: float, recorded: float) -> str:
    if recorded == 0.0 and inferred > 0.0:
        return "no_receipts"
    if inferred == 0.0 and recorded > 0.0:
        return "unobserved"
    if abs(inferred - recorded) <= RECONCILE_TOLERANCE_UNITS:
        return "matches"
    return "under_recorded" if inferred > recorded else "over_recorded"


def reconcile_restocks(
    receipts: list[dict[str, Any]],
    intervals: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Per barcode: what the snapshots inferred, what the ledger recorded, and the gap."""
    recorded = received_by_barcode(receipts)
    inferred = _inferred_by_barcode(intervals)

    result: dict[str, dict[str, Any]] = {}
    for barcode in sorted(set(recorded) | set(inferred)):
        inferred_units = inferred.get(barcode, 0.0)
        recorded_units = recorded.get(barcode, 0.0)
        result[barcode] = {
            "inferred_restocked": inferred_units,
            "recorded_received": recorded_units,
            "delta": inferred_units - recorded_units,
            "verdict": _verdict(inferred_units, recorded_units),
        }
    return result
