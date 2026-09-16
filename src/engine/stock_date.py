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

It also has to include "what we were given is a filesystem timestamp". `file_mtime` is the
last rung of `resolve_as_of`'s four-rung ladder, reached only when a declared date, a
sidecar and git all failed — and on a CI runner it is the CHECKOUT time, because `git clone`
stamps every file with the moment it was written. That is not a weaker signal about when
stock was counted; it is a measurement of something else entirely.

This is not hypothetical either. Measured on the committed artefacts at `a559357`, the
nightly published `as_of: 2026-09-14` for a CSV last changed on 2026-06-06, widening the
window from `< 2026-06` to `< 2026-09` and turning **355 findings into 439** — 118 invented,
34 genuine ones lost. That instance came in through `git_commit` on a shallow clone (#99,
fixed by #109's sidecar), and the ladder's response was to fall through to `file_mtime`,
which fails the same way and passes every check above. So the source is asked as well as
the value.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional


#: `vintages.pos.as_of_source` values that do not describe when stock was counted.
#: `file_mtime` measures when the file arrived on this filesystem — checkout time under
#: `git clone`, which on CI is always "today" and therefore always passes every other
#: check in this function. The other three rungs (`declared`, `declared_sidecar`,
#: `git_commit`) are all statements about the DATA; only this one is about the disk.
UNUSABLE_SOURCES = frozenset({"file_mtime"})


def usable_stock_date(raw: object, *, source: object = None,
                      today: Optional[date] = None) -> Optional[date]:
    """The stock-count date, or None when there is no usable one.

    None means exactly one thing to every caller: there is no boundary, so no
    reconciliation figure may be derived. It never means "use everything".

    `source` is `vintages.pos.as_of_source`. It is optional because tables written before
    that column existed carry no source, and an absent source is not a reason to refuse —
    unknown is not false (ADR-017). A source that is positively known to measure the
    filesystem is.
    """
    if raw is None:
        return None
    if source is not None and str(source) in UNUSABLE_SOURCES:
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
