"""
competitor_stockouts.py — a competitor being out of stock is demand coming his way.

WHAT THIS IS AND IS NOT
    It is an ADJUSTMENT to a demand rate. It is not a gate. Whether the shop should
    reorder is decided entirely from his own stock, corrected demand, lead time and
    shelf life; this only nudges the rate when the surrounding branches have stopped
    carrying something he sells. That decision lived in src/lib/analytics/reorderEngine.js
    until ADR-028 removed it on 2026-09-24. The adjustment is still published in
    public/data/market-context.json (src/context/build.py), which ADR-028 keeps for V2.

    Until 2026-09-07 competitor data GATED the reorder decision — a product with no
    competitor match could not be ordered at all — which is exactly backwards.

WHY STOCKOUT AND NOT SIMPLY "ABSENT"
    src/market/concentration.py already separates the two cases statistically:
    scattered drops across branches read as STOCKOUT (their customer still wants it,
    and today has nowhere else to buy it); synchronised drops that stay gone read as
    DELISTING (the chain is walking away, and following them is the wrong move).
    Only STOCKOUT is treated as a lift. Lifting on a delisting would have us
    stocking up on something the market is abandoning.

HONESTY
    The lift is a single configurable number, not a per-product estimate, because
    nothing in the data supports a per-product one. It is published with the reason
    attached so the explanation can say why the rate moved.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from src.market.concentration import STATE_STOCKOUT, detect_drops, estimate_base_rate
from src.market.presence import load_presence

# Minimum usable snapshot days before the classification means anything. Below this
# the statistics have no power and every product looks like a drop.
MIN_DAYS = 2


def stockout_barcodes(limit_to: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Barcodes the surrounding branches are out of (not walking away from).

    `limit_to` narrows the answer to the shop's own catalogue — a competitor
    stockout on something he does not sell is not a signal, it is noise.
    """
    series = load_presence()
    if len(series.days) < MIN_DAYS:
        return {
            "barcodes": [],
            "days": len(series.days),
            "status": "insufficient_history",
        }

    events = detect_drops(series, base_rate=estimate_base_rate(series))
    found: Set[str] = {
        str(event.barcode)
        for event in events
        if getattr(event, "state", None) == STATE_STOCKOUT and event.barcode
    }
    if limit_to is not None:
        found &= {str(b) for b in limit_to}

    return {
        "barcodes": sorted(found),
        "days": len(series.days),
        "status": "ok",
    }
