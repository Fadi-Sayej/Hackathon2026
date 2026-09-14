"""Is the published stock-count date usable as a reconciliation boundary?

One question, asked in two places that must agree: `_sales_import` decides whether
to window the summary, and `reconciliation.run` decides whether to reconcile at all.
If they disagree, the summary carries figures the capability then publishes over a
window it would have refused — which is the failure this module exists to close.

`resolve_as_of` validates nothing (`src/internal_pos/pos_importer.py`): `--as-of`
is taken verbatim, and `schemas/dashboard.schema.json` types the field as a bare
string. Measured against the real data, three values walked past a presence-only
check and published **439 findings over a window nobody chose**:

    string 'None'    sales_import=error  reconciliation=available  entries=439
    malformed        sales_import=error  reconciliation=available  entries=439
    garbage          sales_import=error  reconciliation=available  entries=439

The mechanism was indirect and worth stating: `date.fromisoformat` raised inside
`_sales_import`, `_step` recorded that as a step error, `import_sales` never ran, and
the PREVIOUS run's `sales_summary.parquet` survived with its non-NULL reconcile
columns. Nothing downstream could tell that the window it was using belonged to a
different date.

So "we do not know the stock date" has to include "what we were given is not a date",
and a date that has not happened yet is not a date a stock count can carry.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional


def usable_stock_date(raw: object, *, today: Optional[date] = None) -> Optional[date]:
    """The stock-count date, or None when there is no usable one.

    None means exactly one thing to every caller: there is no boundary, so no
    reconciliation figure may be derived. It never means "use everything".
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        when = date.fromisoformat(text[:10])
    except ValueError:
        return None
    # A stock count cannot have happened tomorrow. Left as a date comparison rather
    # than a tolerance: the values this guards against are years out (an mtime on a
    # freshly fetched file, a typo'd year), not minutes of clock skew.
    if when > (today or datetime.now(timezone.utc).date()):
        return None
    return when
