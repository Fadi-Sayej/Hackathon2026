> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Implementation plan for the T7 receiving ledger, written before the System Design existed. The receiving capture screen survives into V1 only to start the 30-day counter; its V2 design is not written.
>
> **Canonical replacement:** [`docs/implementation/plan.md`](../../implementation/plan.md)
> Kept for history only. Do not act on anything in this file.

---

# T7 Receiving Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture what physically arrives at the store — quantity, supplier, unit cost, date — so that supplier lead time becomes a measured number instead of a hardcoded `3`, and reorder quantities rest on observed deliveries rather than an assumed constant.

**Architecture:** A four-layer vertical slice. (1) A keyboard-first capture form on the existing Receiving panel queues receipts to `localStorage` and exports CSV. (2) A new append-only Python ledger `src/internal/receiving.py` writes `data/internal/receiving/receipts.csv` and bridges receipts carrying an expiry date into the existing expiry report without forking it. (3) `supplier_lead_times()` derives a median delivery interval per supplier, gated at ≥3 deliveries. (4) A generated JSON feeds `scripts/normalize-datasets.mjs`, replacing `leadTimeDays: 3` with a measured value, and the reconciliation of recorded receipts against snapshot-inferred restocks validates both the ledger and the velocity method.

**Tech Stack:** React 19 + Vite (no router, no component-test infrastructure), Vitest (node environment), Python 3.9.6 + pyarrow + csv stdlib, pytest.

---

## Global Constraints

Every task's requirements implicitly include this section.

### From the spec (issue #52) — copied verbatim

- **"If entry is slower than writing on paper, the tool is abandoned within a week."** Target: **under 20 seconds per batch line.**
- **Scan barcode → focus jumps to quantity → Enter → saved.** Keyboard-only, no mouse.
- **Number pad `inputMode="numeric"`** on quantity and cost — "this is a phone in a shop, not a desktop."
- **Remember the last supplier** — "a delivery is usually 20 items from one supplier. Do not make them re-pick it 20 times."
- **Show the product name in Hebrew immediately** on barcode entry. "The lookup already exists — keep it."
- **Never block on network.** Queue to localStorage, sync later. "The existing queue pattern is correct — extend it, do not replace it."
- **Undo on the last entry.** "Mis-scans happen constantly."
- **`receivedAt` defaults to today and `expiryDate` becomes optional.** Required: `quantity`, `supplier`, `receivedAt`. Optional: `unitCost`, `expiryDate`.
- **Test at 390 px** — the store-floor viewport, RTL, Hebrew product names.
- Use the existing `dirProps` from `src/lib/utils/rtl.js` and `formatBarcode` / `formatDate` from `src/lib/utils/format.js`.
- **Add `RECEIVING_ROOT` to `src/common/paths.py` — never hardcode paths; that module is the single source of truth.**
- **Keep `expiry_tracking.py` working.** "A receipt with an expiry date should feed the existing expiry report; do not fork that logic."
- **At least 3 deliveries per supplier** before a median means anything. "Below that, keep the default and mark confidence `low`. Do not present a median of two observations as fact."
- **§4.2 of `docs/UI_DATA_CONTRACT.md` still binds.** Where `velocityConfidence: 'none'`, show the recommendation but **withhold the quantity** and cap confidence at 0.4 with a "Count first" action.
- **Do not surface the ₪63,572 discrepancy figure anywhere in the UI**, in any task of this plan.

### `RECEIVING_COLUMNS` — the exact ledger schema (spec Step 3)

```python
RECEIVING_COLUMNS = [
    "receipt_id",      # stable hash: barcode + received_at + supplier
    "barcode",
    "product_name",
    "quantity",
    "supplier",
    "unit_cost",
    "received_at",     # ISO date
    "expiry_date",     # nullable
    "recorded_at",     # ISO timestamp — when it was typed, not when it arrived
    "source",          # 'manual_ui' | 'csv_import'
]
```

Written to `data/internal/receiving/receipts.csv`.

### Repository realities — verified 2026-08-13 on `worktree-t7-receiving-ledger` @ `436f84d`

- **Baseline is green:** `npm run lint` exits 0, `npm test` = 172 passed, pytest = 89 passed. Do not land a task that breaks any of the three.
- **Vitest's default environment is `node`** (`vitest.config.js`) and the repository had no component test before this plan. **Task 0 adds jsdom + Testing Library**, and from then on a component test opts in per file with a `// @vitest-environment jsdom` docblock. The 172 existing tests keep running under `node` — do not flip the global environment. `vitest.config.js` includes only `src/**/*.{test,spec}.{js,jsx}` — a test outside `src/` will not run.
- **Business logic still belongs in pure modules under `src/lib/`**, not in components. Component tests cover wiring and interaction (focus movement, undo, the error path); they are not the place to re-assert validation rules that `receivingQueue.js` already owns.
- **`globalThis.localStorage` does not exist in the node test environment.** Follow the existing idiom in `src/lib/persistence/localStorageAdapter.js:109` — guard with `typeof globalThis.localStorage !== 'undefined'`, and accept an injected storage object so tests can pass a fake.
- **Python is 3.9.6.** Every new module starts with `from __future__ import annotations`, exactly as `src/expiry/expiry_tracking.py:1` does. `X | Y` is fine in annotations under that import but **fails at runtime** — never use it in `isinstance()` or any evaluated position.
- **Run pytest with the project venv,** because bare `python3` has no pyarrow:
  `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests -q`
  The `npm run test:py` script uses bare `python3` and will fail; that is pre-existing and out of scope.
- **`data/` is largely git-ignored.** The silver Parquet tables are not present in this worktree. Every Python test must build its own fixtures in `tmp_path` and must never read the real `data/` tree.
- **Sales velocity is now real** for 1,565 of 7,674 products (`velocity_confidence`: 504 `high`, 1,061 `medium`, 6,109 `none`). `CLAUDE.md`'s "there is no sales data anywhere" is stale. `REORDER` therefore already emits; what it lacks is a real lead time.
- **`reorderEngine.js` already implements §4.2 correctly** (lines 131-155: `hasVelocityConfidence` gate, `stockReconciles` quantity withholding, confidence capped at 0.4). **Do not reimplement it.** Only Task 9 touches that file.

### Conventions

- Commit after each task's tests pass. Conventional-commit prefixes (`feat:`, `test:`, `fix:`, `docs:`).
- ESLint is the release gate: `npm run lint` must exit 0 before any commit that touches JS/JSX.
- **Expected test counts are a check, not a target.** `pytest.mark.parametrize` and `it.each` each count as one test per case. If your actual count differs from the number a step predicts, **report the actual number in your task report** — never edit or delete a test to make the count match.

### Explicit decisions taken while planning — do not "fix" these

1. **No migration of the legacy `expiry_scan_queue` localStorage key.** The app is not deployed (B-1 pending), so there is no field data to migrate. The receiving queue uses a new key and leaves the legacy key untouched on disk. Fabricating a `quantity` for legacy expiry-only rows is exactly the kind of invented number this project refuses.
2. **`receipt_id` collides by design** for two deliveries of the same barcode from the same supplier on the same day — the spec mandates that exact hash input. The CSV is append-only and keeps both rows; `receipt_id` is a stable key, not a uniqueness constraint. Document it, do not add dedup logic.
3. **`n_observations` counts distinct delivery *dates* per supplier**, not receipt lines. Twenty items on one delivery note is one delivery.
4. **Confidence tiers:** `n < 3` → `'low'` with `median_days: None` (spec-mandated); `3 ≤ n ≤ 5` → `'medium'`; `n ≥ 6` → `'high'`.

### Out of scope — stated, not silently dropped

- **The three human acceptance criteria cannot be verified by this plan:** "the manager records 3 consecutive deliveries unaided", "under 20 seconds per batch line measured with a stopwatch on a real phone", and the physical count of ~20 SKUs. Task 7 ships the form and a manual verification checklist; the stopwatch test is a human handover step.

- **Spec Step 6 — "wire expiry into the gates" — is blocked, and not by what the spec expected.** The spec gates it on issue #50; #50 is **closed** and `configs/market_params.yaml` defines the `pesach_chametz_window` gate. The real blocker is downstream: that file states as **NON-NEGOTIABLE** that "a gate keyed on a flag whose profile has `reviewed_by: null` must NOT fire", and `data/profiles/product_profiles.jsonl` — the file that carries `is_chametz` and `reviewed_by` — **contains zero rows** (verified 2026-08-13). There is therefore no product on which the chametz gate is permitted to fire, and any Step 6 code would be untestable against real data and dead in production. It unblocks when issue #51 (T6, product classification) populates reviewed profiles. Step 6 has no entry in the spec's own Acceptance list, which is consistent with it being forward-looking.
- **Closing the full inventory identity `expected = last_counted + Σreceived − Σsold` is not possible with today's data.** There is no dated opening count, and `yomyom_sales.parquet` holds 7d/30d aggregates rather than a dated series, so the three terms cannot be aligned to a common window. Task 9 delivers the computable and genuinely useful half — reconciling recorded receipts against the restocks that `src/snapshots/velocity.py` currently *infers* from stock rises — and reports the missing terms explicitly rather than estimating them.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `package.json`, `vitest.config.js` (modify) | jsdom + Testing Library, opt-in per file | 0 |
| `src/components/shared/__tests__/smoke.test.jsx` (create) | Proves the component-test path works | 0 |
| `src/common/paths.py` (modify) | `RECEIVING_ROOT`, `RECEIPTS_CSV`, `SUPPLIER_LEAD_TIMES_JSON` | 1 |
| `src/internal/receiving.py` (create) | The ledger: schema, validation, append, load, CSV import | 1 |
| `tests/test_receiving.py` (create) | Ledger unit tests | 1, 3 |
| `src/expiry/expiry_tracking.py` (modify) | Merge receipt-borne expiry dates into the existing report | 2 |
| `tests/test_receiving_expiry_bridge.py` (create) | Bridge tests | 2 |
| `src/internal/receiving.py` (modify) | `supplier_lead_times()`, `barcode_supplier_map()` | 3 |
| `scripts/export_supplier_lead_times.py` (create) | Ledger → `supplier_lead_times.json` | 4 |
| `tests/test_export_supplier_lead_times.py` (create) | Export shape tests | 4 |
| `src/lib/receiving/leadTimeResolver.js` (create) | Pure barcode → `{supplier, leadTimeDays}` resolver | 5 |
| `src/lib/receiving/__tests__/leadTimeResolver.test.js` (create) | Resolver tests | 5 |
| `scripts/normalize-datasets.mjs` (modify) | Consume the resolver instead of `leadTimeDays: 3` | 5 |
| `src/lib/receiving/receivingQueue.js` (create) | Pure queue: entry building, validation, undo, CSV, supplier memory | 6 |
| `src/lib/receiving/__tests__/receivingQueue.test.js` (create) | Queue tests | 6 |
| `src/components/receiving/ReceivingCaptureForm.jsx` (create) | The capture form | 7 |
| `src/components/receiving/__tests__/ReceivingCaptureForm.test.jsx` (create) | Interaction tests for the form | 7 |
| `src/pages/ExpiryPage.jsx` (modify) | Host the form, drop the inlined two-field version | 7 |
| `src/App.css` (modify) | Receiving form styles at 390 px | 7 |
| `docs/RECEIVING_LEDGER.md` (create) | Operator + developer reference | 8 |
| `src/internal/restock_reconcile.py` (create) | Recorded receipts vs. snapshot-inferred restocks | 9 |
| `tests/test_restock_reconcile.py` (create) | Reconciliation tests | 9 |

---

## Task 0: Component-test infrastructure

The capture form is the deliverable this whole track stands on — if it is slower than paper it gets abandoned, and everything downstream dies with it. It should not be the one part of the plan that ships unverified. This task adds the smallest infrastructure that lets Task 7 assert focus movement, undo and the error path, and proves it works before anything depends on it.

**Files:**
- Modify: `package.json` (devDependencies)
- Modify: `vitest.config.js`
- Create: `src/components/shared/__tests__/smoke.test.jsx`

**Interfaces:**
- Consumes: nothing.
- Produces: the ability for any file to opt into a DOM environment with a `// @vitest-environment jsdom` docblock on its first line, and to import `render`, `screen` from `@testing-library/react` and `userEvent` from `@testing-library/user-event`.

**Versions (verified available 2026-08-13):** `jsdom@30.0.1`, `@testing-library/react@16.3.2`, `@testing-library/dom@10` (peer of the former), `@testing-library/user-event@14.6.4`. React is `^19.2.6`; Testing Library 16.x is the line that supports React 19.

- [ ] **Step 1: Install the dev dependencies**

```bash
npm install --save-dev jsdom@^30.0.1 @testing-library/react@^16.3.2 @testing-library/dom@^10 @testing-library/user-event@^14.6.4
```

- [ ] **Step 2: Leave the global environment alone**

Open `vitest.config.js` and confirm it still reads:

```js
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.{test,spec}.{js,jsx}'],
  },
})
```

**Do not change `environment` to `'jsdom'`.** The 172 existing tests are pure-logic tests that run faster and more honestly under `node`; a component test opts in per file instead. No edit is needed in this step — it exists so nobody "helpfully" flips it.

- [ ] **Step 3: Write the smoke test**

Create `src/components/shared/__tests__/smoke.test.jsx`:

```jsx
// @vitest-environment jsdom

/**
 * Proves the component-test path actually works: jsdom is active, React 19
 * renders, Testing Library queries resolve, and user-event drives an interaction.
 *
 * This project runs vitest under `node` by default. Component tests opt in with
 * the docblock on line 1 of this file — copy it into any new .test.jsx.
 */

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { Button } from '../Button.jsx'

// Auto-cleanup only fires when vitest globals are enabled, and they are not.
afterEach(cleanup)

describe('component test infrastructure', () => {
  it('has a DOM', () => {
    expect(typeof document).toBe('object')
  })

  it('renders a shared component and finds it by role', () => {
    render(<Button tone="primary">Save</Button>)
    expect(screen.getByRole('button', { name: 'Save' })).toBeDefined()
  })

  it('drives a click through user-event', async () => {
    const onClick = vi.fn()
    render(<Button tone="primary" onClick={onClick}>Save</Button>)
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })
})
```

If `Button.jsx` does not accept `onClick` or renders something other than a `<button>`, read `src/components/shared/Button.jsx` and adjust the test to what it actually is — do not change `Button.jsx` to suit the test.

- [ ] **Step 4: Run the smoke test**

Run: `npx vitest run src/components/shared/__tests__/smoke.test.jsx`
Expected: PASS, 3 passed.

- [ ] **Step 5: Confirm the existing suite is untouched**

Run: `npm run lint && npm test`
Expected: lint exits 0; 175 tests pass (172 baseline + 3 new). If any of the original 172 changed status, the environment was flipped globally — revert and use the docblock.

- [ ] **Step 6: Commit**

```bash
git add package.json package-lock.json vitest.config.js src/components/shared/__tests__/smoke.test.jsx
git commit -m "test: add jsdom + Testing Library for opt-in component tests"
```

---

## Task 1: The receiving ledger — schema, paths, append, load, import

**Files:**
- Modify: `src/common/paths.py:31-37`
- Create: `src/internal/receiving.py`
- Test: `tests/test_receiving.py`

**Interfaces:**
- Consumes: `PROJECT_ROOT`, `INTERNAL_ROOT` from `src.common.paths`; `parse_expiry_date` from `src.expiry.expiry_tracking` (a general ISO / `DD/MM/YYYY` date parser despite its name).
- Produces:
  - `RECEIVING_COLUMNS: list[str]` — the ten columns above, in order.
  - `MIN_DELIVERIES_FOR_LEAD_TIME = 3`, `DEFAULT_LEAD_TIME_DAYS = 3`
  - `ensure_receipts_csv(path: Path = RECEIPTS_CSV) -> Path`
  - `make_receipt_id(barcode: str, received_at: date, supplier: str) -> str` — 16-char sha256 prefix
  - `add_receipt(*, barcode, quantity, supplier, received_at=None, unit_cost=None, expiry_date=None, product_name=None, source="manual_ui", recorded_at=None, path=RECEIPTS_CSV) -> dict[str, Any]`
  - `load_receipts(path: Path = RECEIPTS_CSV) -> list[dict[str, Any]]`
  - `import_receiving_csv(input_path: Path, path: Path = RECEIPTS_CSV, source: str = "csv_import") -> dict[str, Any]`
- `src/internal/` already contains `pos_importer.py`; there is no `__init__.py` in it and none is needed (the repo imports `src.internal.pos_importer` as a namespace package).

- [ ] **Step 1: Add the paths**

In `src/common/paths.py`, immediately after the `EXPIRY_ROOT` line in the "Top-level data roots" block (line 31), add:

```python
RECEIVING_ROOT    = INTERNAL_ROOT / "receiving"
```

And in the "Internal sub-folders" block, immediately after `EXPIRY_SCANS_CSV` (line 37), add:

```python
# The receiving ledger (T7 / #52). Append-only: the POS records what was sold and
# never what arrived, so this file is the only record of the `received` term in
# stock_now = opening + received - sold.
RECEIPTS_CSV             = RECEIVING_ROOT / "receipts.csv"
SUPPLIER_LEAD_TIMES_JSON = RECEIVING_ROOT / "supplier_lead_times.json"
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_receiving.py`:

```python
"""
Tests for the receiving ledger (src/internal/receiving.py).

Every test writes to tmp_path. The real data/internal/receiving/ tree is never
touched — it is git-ignored and absent in a fresh clone.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.internal.receiving import (  # noqa: E402
    RECEIVING_COLUMNS,
    add_receipt,
    ensure_receipts_csv,
    import_receiving_csv,
    load_receipts,
    make_receipt_id,
)


@pytest.fixture()
def ledger(tmp_path: Path) -> Path:
    return tmp_path / "receipts.csv"


def test_ensure_creates_file_with_exact_header(ledger: Path) -> None:
    ensure_receipts_csv(ledger)
    with ledger.open(encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert header == RECEIVING_COLUMNS


def test_add_receipt_writes_every_column(ledger: Path) -> None:
    record = add_receipt(
        barcode="7290000066318",
        quantity=24,
        supplier="Tempo",
        received_at="2026-08-10",
        unit_cost=4.5,
        expiry_date="2026-12-31",
        product_name="קוקה קולה 1.5 ליטר",
        path=ledger,
    )
    assert set(record) == set(RECEIVING_COLUMNS)
    assert record["quantity"] == 24
    assert record["supplier"] == "Tempo"
    assert record["received_at"] == "2026-08-10"
    assert record["expiry_date"] == "2026-12-31"
    assert record["unit_cost"] == 4.5
    assert record["source"] == "manual_ui"

    rows = load_receipts(ledger)
    assert len(rows) == 1
    assert rows[0]["product_name"] == "קוקה קולה 1.5 ליטר"


def test_received_at_defaults_to_today(ledger: Path) -> None:
    record = add_receipt(barcode="123", quantity=1, supplier="Osem", path=ledger)
    assert record["received_at"] == datetime.now(timezone.utc).date().isoformat()


def test_expiry_date_is_optional_and_empty_when_absent(ledger: Path) -> None:
    record = add_receipt(barcode="123", quantity=1, supplier="Osem", path=ledger)
    assert record["expiry_date"] == ""
    assert record["unit_cost"] == ""


def test_receipt_id_is_stable_across_calls(ledger: Path) -> None:
    first = make_receipt_id("123", date(2026, 8, 10), "Tempo")
    second = make_receipt_id("123", date(2026, 8, 10), "Tempo")
    assert first == second
    assert len(first) == 16
    assert make_receipt_id("123", date(2026, 8, 11), "Tempo") != first
    assert make_receipt_id("123", date(2026, 8, 10), "Osem") != first


def test_ledger_is_append_only_and_keeps_same_day_repeat_deliveries(ledger: Path) -> None:
    add_receipt(barcode="123", quantity=6, supplier="Tempo", received_at="2026-08-10", path=ledger)
    add_receipt(barcode="123", quantity=4, supplier="Tempo", received_at="2026-08-10", path=ledger)
    rows = load_receipts(ledger)
    assert [row["quantity"] for row in rows] == ["6", "4"]
    assert rows[0]["receipt_id"] == rows[1]["receipt_id"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"barcode": "", "quantity": 1, "supplier": "Tempo"},
        {"barcode": "   ", "quantity": 1, "supplier": "Tempo"},
        {"barcode": "123", "quantity": 0, "supplier": "Tempo"},
        {"barcode": "123", "quantity": -5, "supplier": "Tempo"},
        {"barcode": "123", "quantity": "abc", "supplier": "Tempo"},
        {"barcode": "123", "quantity": 1, "supplier": ""},
        {"barcode": "123", "quantity": 1, "supplier": "  "},
    ],
)
def test_add_receipt_rejects_invalid_required_fields(ledger: Path, kwargs: dict) -> None:
    with pytest.raises(ValueError):
        add_receipt(path=ledger, **kwargs)


def test_add_receipt_rejects_negative_unit_cost(ledger: Path) -> None:
    with pytest.raises(ValueError):
        add_receipt(barcode="123", quantity=1, supplier="Tempo", unit_cost=-1, path=ledger)


def test_add_receipt_accepts_dd_mm_yyyy_dates(ledger: Path) -> None:
    record = add_receipt(
        barcode="123", quantity=1, supplier="Tempo", received_at="10/08/2026", path=ledger
    )
    assert record["received_at"] == "2026-08-10"


def test_load_receipts_on_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_receipts(tmp_path / "nothing.csv") == []


def test_import_receiving_csv_counts_good_and_rejected_rows(tmp_path: Path) -> None:
    source = tmp_path / "upload.csv"
    source.write_text(
        "barcode,product_name,quantity,supplier,unit_cost,received_at,expiry_date\n"
        "111,במבה,12,Osem,2.10,2026-08-10,2026-11-01\n"
        "222,ביסלי,6,Osem,,2026-08-10,\n"
        ",broken,3,Osem,,2026-08-10,\n"
        "333,bad qty,0,Osem,,2026-08-10,\n",
        encoding="utf-8",
    )
    ledger = tmp_path / "receipts.csv"
    result = import_receiving_csv(source, path=ledger)

    assert result["imported_rows"] == 2
    assert result["rejected_rows"] == 2
    assert {row["row_number"] for row in result["rejected_preview"]} == {4, 5}
    assert all(row["source"] == "csv_import" for row in load_receipts(ledger))
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests/test_receiving.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.internal.receiving'`

- [ ] **Step 4: Implement the ledger**

Create `src/internal/receiving.py`:

```python
"""
receiving.py — the receiving ledger.

The POS records what was sold. It never records what arrived, which leaves the
inventory identity missing a whole term:

    stock_now = opening + received - sold
                          ^^^^^^^^

This module is the only place that term is captured. The file is append-only:
a delivery that happened is a fact, and facts are not edited in place.

`receipt_id` is a stable hash of (barcode, received_at, supplier) exactly as
specified in issue #52. Two separate deliveries of the same barcode from the
same supplier on the same day therefore share an id. That is intentional — the
id is a stable key for re-import, not a uniqueness constraint, and both rows
are kept.
"""

from __future__ import annotations

import csv
import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.common.paths import RECEIPTS_CSV
# parse_expiry_date is a general date parser (ISO, DD/MM/YYYY, DD-MM-YYYY,
# DD.MM.YYYY) that happens to live in the expiry module. Reused rather than
# duplicated. The dependency runs one way only: expiry_tracking must never
# import this module at module scope.
from src.expiry.expiry_tracking import parse_expiry_date as _parse_date

RECEIVING_COLUMNS = [
    "receipt_id",
    "barcode",
    "product_name",
    "quantity",
    "supplier",
    "unit_cost",
    "received_at",
    "expiry_date",
    "recorded_at",
    "source",
]

# A median over fewer than three deliveries is not a measurement, it is a guess
# with a decimal point. Below this we keep the default and say so.
MIN_DELIVERIES_FOR_LEAD_TIME = 3
DEFAULT_LEAD_TIME_DAYS = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _require_barcode(value: Any) -> str:
    barcode = _clean(value)
    if not barcode:
        raise ValueError("barcode is required")
    return barcode


def _require_quantity(value: Any) -> int:
    try:
        quantity = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"quantity must be a whole number, got {value!r}") from None
    if quantity <= 0:
        raise ValueError(f"quantity must be greater than zero, got {quantity}")
    return quantity


def _require_supplier(value: Any) -> str:
    supplier = _clean(value)
    if not supplier:
        raise ValueError("supplier is required")
    return supplier


def _optional_cost(value: Any) -> Optional[float]:
    text = _clean(value)
    if not text:
        return None
    try:
        cost = float(text)
    except ValueError:
        raise ValueError(f"unit_cost must be a number, got {value!r}") from None
    if cost < 0:
        raise ValueError(f"unit_cost must not be negative, got {cost}")
    return cost


def _optional_date(value: Any) -> Optional[date]:
    text = _clean(value)
    if not text:
        return None
    return _parse_date(text)


def make_receipt_id(barcode: str, received_at: date, supplier: str) -> str:
    key = f"{barcode}|{received_at.isoformat()}|{supplier}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def ensure_receipts_csv(path: Path = RECEIPTS_CSV) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=RECEIVING_COLUMNS).writeheader()
    return path


def add_receipt(
    *,
    barcode: str,
    quantity: Any,
    supplier: str,
    received_at: Any = None,
    unit_cost: Any = None,
    expiry_date: Any = None,
    product_name: Any = None,
    source: str = "manual_ui",
    recorded_at: Any = None,
    path: Path = RECEIPTS_CSV,
) -> dict[str, Any]:
    """Append one delivery line. Raises ValueError on any invalid required field."""
    clean_barcode = _require_barcode(barcode)
    clean_quantity = _require_quantity(quantity)
    clean_supplier = _require_supplier(supplier)
    cost = _optional_cost(unit_cost)
    expiry = _optional_date(expiry_date)

    received = _optional_date(received_at) or _now().date()
    recorded = _clean(recorded_at) or _now().isoformat()

    record = {
        "receipt_id": make_receipt_id(clean_barcode, received, clean_supplier),
        "barcode": clean_barcode,
        "product_name": _clean(product_name),
        "quantity": clean_quantity,
        "supplier": clean_supplier,
        "unit_cost": cost if cost is not None else "",
        "received_at": received.isoformat(),
        "expiry_date": expiry.isoformat() if expiry else "",
        "recorded_at": recorded,
        "source": source,
    }

    ensure_receipts_csv(path)
    with path.open("a", encoding="utf-8", newline="") as handle:
        csv.DictWriter(handle, fieldnames=RECEIVING_COLUMNS).writerow(record)
    return record


def load_receipts(path: Path = RECEIPTS_CSV) -> list[dict[str, Any]]:
    """Every ledger row as written. Missing file reads as an empty ledger."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def import_receiving_csv(
    input_path: Path,
    path: Path = RECEIPTS_CSV,
    source: str = "csv_import",
) -> dict[str, Any]:
    """Load a CSV exported by the capture form. Bad rows are reported, not silently dropped."""
    ensure_receipts_csv(path)
    imported = 0
    rejected: list[dict[str, Any]] = []

    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            try:
                add_receipt(
                    barcode=row.get("barcode", ""),
                    quantity=row.get("quantity", ""),
                    supplier=row.get("supplier", ""),
                    received_at=row.get("received_at") or None,
                    unit_cost=row.get("unit_cost") or None,
                    expiry_date=row.get("expiry_date") or None,
                    product_name=row.get("product_name") or None,
                    source=row.get("source") or source,
                    recorded_at=row.get("recorded_at") or None,
                    path=path,
                )
                imported += 1
            except Exception as exc:
                rejected.append({"row_number": row_number, "error": str(exc), "row": row})

    return {
        "status": "ok",
        "input_path": str(input_path),
        "receipts_csv": str(path),
        "imported_rows": imported,
        "rejected_rows": len(rejected),
        "rejected_preview": rejected[:20],
    }
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests/test_receiving.py -q`
Expected: PASS, 17 passed (the 7 parametrized invalid-field cases count individually).

- [ ] **Step 6: Run the full pytest suite for regressions**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests -q`
Expected: PASS, 106 passed (89 baseline + 17 new).

- [ ] **Step 7: Commit**

```bash
git add src/common/paths.py src/internal/receiving.py tests/test_receiving.py
git commit -m "feat: receiving ledger — schema, validation, append-only CSV"
```

---

## Task 2: Feed receipt expiry dates into the existing expiry report

**Files:**
- Modify: `src/internal/receiving.py` (add one function)
- Modify: `src/expiry/expiry_tracking.py:196-210` (`build_expiry_report`)
- Test: `tests/test_receiving_expiry_bridge.py`

**Interfaces:**
- Consumes: `load_receipts`, `RECEIPTS_CSV` from Task 1.
- Produces: `receipts_as_expiry_scans(path: Path = RECEIPTS_CSV) -> list[dict[str, Any]]`, emitting the **expiry-scan** shape that `build_expiry_report` already consumes: keys `scan_id`, `barcode`, `expiry_date`, `scanned_at`, `source`, `notes`.
- `build_expiry_report` gains one keyword argument: `receipts_path: Optional[Path] = None`.

**Why a function-local import:** `receiving.py` imports `parse_expiry_date` from `expiry_tracking` at module scope. `expiry_tracking` importing `receiving` at module scope would be a cycle. `build_expiry_report` already uses a function-local import for `src.common.source_status` (line 287) — this follows the file's own idiom.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_receiving_expiry_bridge.py`:

```python
"""
The receiving ledger and the expiry report must not fork.

A receipt that carries an expiry date IS an expiry observation, and has to reach
the existing report through the existing bucketing/severity logic — not through a
second copy of it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.expiry.expiry_tracking import build_expiry_report  # noqa: E402
from src.internal.receiving import add_receipt, receipts_as_expiry_scans  # noqa: E402


@pytest.fixture()
def ledger(tmp_path: Path) -> Path:
    return tmp_path / "receipts.csv"


def test_only_receipts_with_an_expiry_date_become_scans(ledger: Path) -> None:
    add_receipt(barcode="111", quantity=6, supplier="Osem", expiry_date="2026-09-01", path=ledger)
    add_receipt(barcode="222", quantity=6, supplier="Osem", path=ledger)

    scans = receipts_as_expiry_scans(ledger)
    assert [scan["barcode"] for scan in scans] == ["111"]


def test_scan_shape_matches_what_the_report_consumes(ledger: Path) -> None:
    add_receipt(
        barcode="111", quantity=6, supplier="Osem", expiry_date="2026-09-01",
        received_at="2026-08-10", path=ledger,
    )
    scan = receipts_as_expiry_scans(ledger)[0]
    assert set(scan) == {"scan_id", "barcode", "expiry_date", "scanned_at", "source", "notes"}
    assert scan["expiry_date"] == "2026-09-01"
    assert scan["source"] == "receiving:manual_ui"
    assert "6" in scan["notes"] and "Osem" in scan["notes"]


def test_missing_ledger_yields_no_scans(tmp_path: Path) -> None:
    assert receipts_as_expiry_scans(tmp_path / "absent.csv") == []


def test_report_includes_receipt_borne_expiry_dates(tmp_path: Path) -> None:
    ledger = tmp_path / "receipts.csv"
    scans_csv = tmp_path / "expiry_scans.csv"
    add_receipt(
        barcode="7290000066318", quantity=12, supplier="Tempo",
        expiry_date="2026-08-15", received_at="2026-08-10", path=ledger,
    )

    report = build_expiry_report(as_of="2026-08-13", path=scans_csv, receipts_path=ledger)

    barcodes = [row["barcode"] for row in report["alerts_preview"]]
    assert "7290000066318" in barcodes
    assert report["summary"]["total_scans"] == 1
    severity = next(r["severity"] for r in report["alerts_preview"] if r["barcode"] == "7290000066318")
    assert severity == "critical_7d"


def test_report_still_works_with_no_receipts_at_all(tmp_path: Path) -> None:
    report = build_expiry_report(
        as_of="2026-08-13",
        path=tmp_path / "expiry_scans.csv",
        receipts_path=tmp_path / "absent.csv",
    )
    assert report["status"] == "ok"
    assert report["summary"]["total_scans"] == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests/test_receiving_expiry_bridge.py -q`
Expected: FAIL — `ImportError: cannot import name 'receipts_as_expiry_scans'`

- [ ] **Step 3: Add the bridge function to `receiving.py`**

Append to `src/internal/receiving.py`:

```python
def receipts_as_expiry_scans(path: Path = RECEIPTS_CSV) -> list[dict[str, Any]]:
    """Receipts that carry an expiry date, in the expiry-scan shape.

    A delivery with a date on the package is an expiry observation. Rather than
    forking the bucketing and severity logic in expiry_tracking, we translate
    into the shape that module already reads.
    """
    scans: list[dict[str, Any]] = []
    for row in load_receipts(path):
        expiry = _clean(row.get("expiry_date"))
        barcode = _clean(row.get("barcode"))
        if not expiry or not barcode:
            continue
        scans.append(
            {
                "scan_id": _clean(row.get("receipt_id")),
                "barcode": barcode,
                "expiry_date": expiry,
                "scanned_at": _clean(row.get("recorded_at")),
                "source": f"receiving:{_clean(row.get('source')) or 'unknown'}",
                "notes": (
                    f"received {_clean(row.get('quantity'))} units "
                    f"from {_clean(row.get('supplier'))} "
                    f"on {_clean(row.get('received_at'))}"
                ),
            }
        )
    return scans
```

- [ ] **Step 4: Merge receipts into `build_expiry_report`**

In `src/expiry/expiry_tracking.py`, change the signature at line 196:

```python
def build_expiry_report(
    *,
    as_of: str | None = None,
    path: Path = EXPIRY_SCANS_CSV,
    receipts_path: Path | None = None,
) -> dict[str, Any]:
```

Then replace line 206 (`scans = load_expiry_scans(path)`) with:

```python
    # A receipt carrying an expiry date is an expiry observation and belongs in
    # this report. Imported inside the function because receiving.py imports
    # parse_expiry_date from this module — same local-import idiom as
    # update_source() below.
    from src.internal.receiving import RECEIPTS_CSV, receipts_as_expiry_scans

    scans = load_expiry_scans(path) + receipts_as_expiry_scans(
        receipts_path if receipts_path is not None else RECEIPTS_CSV
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests/test_receiving_expiry_bridge.py -q`
Expected: PASS, 5 passed.

- [ ] **Step 6: Run the full pytest suite for regressions**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests -q`
Expected: PASS, 111 passed.

- [ ] **Step 7: Commit**

```bash
git add src/internal/receiving.py src/expiry/expiry_tracking.py tests/test_receiving_expiry_bridge.py
git commit -m "feat: receipts with an expiry date feed the existing expiry report"
```

---

## Task 3: Real lead time per supplier

**Files:**
- Modify: `src/internal/receiving.py` (add two functions)
- Test: `tests/test_receiving.py` (append a new class)

**Interfaces:**
- Consumes: `load_receipts`, `MIN_DELIVERIES_FOR_LEAD_TIME`, `_parse_date` from Tasks 1-2.
- Produces:
  - `supplier_lead_times(receipts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]`
    Each value is `{"median_days": float | None, "n_observations": int, "confidence": str}`.
  - `barcode_supplier_map(receipts: list[dict[str, Any]]) -> dict[str, str]`
    Barcode → the supplier of that barcode's **most recent** delivery.

**Semantics fixed by the Global Constraints:** `n_observations` = distinct delivery **dates** for that supplier. `n < 3` → `median_days: None`, `confidence: 'low'`. `3-5` → `'medium'`. `≥6` → `'high'`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_receiving.py` (and add `supplier_lead_times, barcode_supplier_map` to the import block at the top of the file):

```python
def _delivery(barcode: str, supplier: str, day: str, quantity: int = 1) -> dict:
    return {
        "barcode": barcode,
        "supplier": supplier,
        "received_at": day,
        "quantity": str(quantity),
    }


class TestSupplierLeadTimes:
    def test_empty_ledger_yields_no_suppliers(self) -> None:
        assert supplier_lead_times([]) == {}

    def test_two_deliveries_are_not_enough_to_claim_a_median(self) -> None:
        result = supplier_lead_times([
            _delivery("111", "Tempo", "2026-08-01"),
            _delivery("111", "Tempo", "2026-08-08"),
        ])
        assert result["Tempo"]["median_days"] is None
        assert result["Tempo"]["n_observations"] == 2
        assert result["Tempo"]["confidence"] == "low"

    def test_three_deliveries_give_a_medium_confidence_median(self) -> None:
        result = supplier_lead_times([
            _delivery("111", "Tempo", "2026-08-01"),
            _delivery("111", "Tempo", "2026-08-08"),
            _delivery("111", "Tempo", "2026-08-15"),
        ])
        assert result["Tempo"]["median_days"] == 7
        assert result["Tempo"]["n_observations"] == 3
        assert result["Tempo"]["confidence"] == "medium"

    def test_six_deliveries_give_high_confidence(self) -> None:
        days = ["2026-08-01", "2026-08-04", "2026-08-07", "2026-08-10", "2026-08-13", "2026-08-16"]
        result = supplier_lead_times([_delivery("111", "Osem", day) for day in days])
        assert result["Osem"]["median_days"] == 3
        assert result["Osem"]["n_observations"] == 6
        assert result["Osem"]["confidence"] == "high"

    def test_many_lines_on_one_delivery_note_count_as_one_delivery(self) -> None:
        result = supplier_lead_times([
            _delivery(str(n), "Tempo", "2026-08-01") for n in range(20)
        ])
        assert result["Tempo"]["n_observations"] == 1
        assert result["Tempo"]["median_days"] is None

    def test_median_ignores_a_single_outlying_gap(self) -> None:
        result = supplier_lead_times([
            _delivery("111", "Tempo", "2026-01-01"),
            _delivery("111", "Tempo", "2026-01-08"),
            _delivery("111", "Tempo", "2026-01-15"),
            _delivery("111", "Tempo", "2026-06-15"),
        ])
        assert result["Tempo"]["median_days"] == 7

    def test_suppliers_are_tracked_independently(self) -> None:
        rows = [_delivery("111", "Tempo", d) for d in ("2026-08-01", "2026-08-08", "2026-08-15")]
        rows += [_delivery("222", "Osem", d) for d in ("2026-08-01", "2026-08-03", "2026-08-05")]
        result = supplier_lead_times(rows)
        assert result["Tempo"]["median_days"] == 7
        assert result["Osem"]["median_days"] == 2

    def test_rows_with_no_supplier_or_unparseable_date_are_skipped(self) -> None:
        result = supplier_lead_times([
            _delivery("111", "", "2026-08-01"),
            _delivery("111", "Tempo", "not-a-date"),
            _delivery("111", "Tempo", "2026-08-01"),
        ])
        assert list(result) == ["Tempo"]
        assert result["Tempo"]["n_observations"] == 1


class TestBarcodeSupplierMap:
    def test_barcode_maps_to_its_most_recent_supplier(self) -> None:
        result = barcode_supplier_map([
            _delivery("111", "Tempo", "2026-08-01"),
            _delivery("111", "Osem", "2026-08-20"),
            _delivery("222", "Tempo", "2026-08-05"),
        ])
        assert result == {"111": "Osem", "222": "Tempo"}

    def test_rows_missing_a_barcode_or_supplier_are_skipped(self) -> None:
        result = barcode_supplier_map([
            _delivery("", "Tempo", "2026-08-01"),
            _delivery("111", "", "2026-08-01"),
        ])
        assert result == {}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests/test_receiving.py -q`
Expected: FAIL — `ImportError: cannot import name 'supplier_lead_times'`

- [ ] **Step 3: Implement both functions**

Add `import statistics` to the imports of `src/internal/receiving.py`, then append:

```python
def supplier_lead_times(receipts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Median days between consecutive deliveries, per supplier.

    Returns {supplier: {median_days, n_observations, confidence}}.

    n_observations counts distinct delivery DATES, not receipt lines: twenty
    items off one delivery note is one delivery. Below
    MIN_DELIVERIES_FOR_LEAD_TIME, median_days is None and the caller must keep
    its default — a median of two observations is not a measurement.
    """
    days_by_supplier: dict[str, set] = {}
    for row in receipts:
        supplier = _clean(row.get("supplier"))
        raw_day = _clean(row.get("received_at"))
        if not supplier or not raw_day:
            continue
        try:
            day = _parse_date(raw_day)
        except ValueError:
            continue
        days_by_supplier.setdefault(supplier, set()).add(day)

    result: dict[str, dict[str, Any]] = {}
    for supplier, days in days_by_supplier.items():
        ordered = sorted(days)
        count = len(ordered)
        if count < MIN_DELIVERIES_FOR_LEAD_TIME:
            result[supplier] = {
                "median_days": None,
                "n_observations": count,
                "confidence": "low",
            }
            continue
        gaps = [(later - earlier).days for earlier, later in zip(ordered, ordered[1:])]
        result[supplier] = {
            "median_days": statistics.median(gaps),
            "n_observations": count,
            "confidence": "high" if count >= 6 else "medium",
        }
    return result


def barcode_supplier_map(receipts: list[dict[str, Any]]) -> dict[str, str]:
    """Barcode -> the supplier of that barcode's most recent delivery.

    Products carry supplier 'YomYom' for all 7,674 rows because the POS export
    has no supplier column. The ledger is the first place a real supplier per
    product is ever observed.
    """
    latest: dict[str, tuple] = {}
    for row in receipts:
        barcode = _clean(row.get("barcode"))
        supplier = _clean(row.get("supplier"))
        raw_day = _clean(row.get("received_at"))
        if not barcode or not supplier or not raw_day:
            continue
        try:
            day = _parse_date(raw_day)
        except ValueError:
            continue
        if barcode not in latest or day >= latest[barcode][0]:
            latest[barcode] = (day, supplier)
    return {barcode: supplier for barcode, (_, supplier) in latest.items()}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests/test_receiving.py -q`
Expected: PASS, 27 passed (17 from Task 1 + 8 lead-time + 2 supplier-map).

- [ ] **Step 5: Run the full pytest suite for regressions**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests -q`
Expected: PASS, 121 passed.

- [ ] **Step 6: Commit**

```bash
git add src/internal/receiving.py tests/test_receiving.py
git commit -m "feat: measure supplier lead time from the receiving ledger"
```

---

## Task 4: Export lead times for the frontend pipeline

**Files:**
- Create: `scripts/export_supplier_lead_times.py`
- Modify: `package.json` (one script entry)
- Test: `tests/test_export_supplier_lead_times.py`

**Interfaces:**
- Consumes: `load_receipts`, `supplier_lead_times`, `barcode_supplier_map`, `SUPPLIER_LEAD_TIMES_JSON`, `DEFAULT_LEAD_TIME_DAYS`.
- Produces: `build_lead_time_export(receipts) -> dict` and `main(argv=None) -> int` in the script; the JSON file consumed by Task 5 has this exact shape:

```json
{
  "generatedAt": "2026-08-13T09:00:00+00:00",
  "defaultLeadTimeDays": 3,
  "minDeliveriesForLeadTime": 3,
  "leadTimes": { "Tempo": { "median_days": 7, "n_observations": 4, "confidence": "medium" } },
  "supplierByBarcode": { "7290000066318": "Tempo" },
  "totals": { "receipts": 12, "suppliers": 2, "barcodes": 9 }
}
```

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_supplier_lead_times.py`:

```python
"""The JSON contract between the Python ledger and scripts/normalize-datasets.mjs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_supplier_lead_times import build_lead_time_export, main  # noqa: E402
from src.internal.receiving import add_receipt  # noqa: E402


def _seed(ledger: Path) -> None:
    for day in ("2026-08-01", "2026-08-08", "2026-08-15"):
        add_receipt(barcode="7290000066318", quantity=12, supplier="Tempo",
                    received_at=day, path=ledger)
    add_receipt(barcode="111", quantity=6, supplier="Osem",
                received_at="2026-08-02", path=ledger)


def test_export_shape_is_the_documented_contract(tmp_path: Path) -> None:
    ledger = tmp_path / "receipts.csv"
    _seed(ledger)

    from src.internal.receiving import load_receipts

    payload = build_lead_time_export(load_receipts(ledger))

    assert set(payload) == {
        "generatedAt", "defaultLeadTimeDays", "minDeliveriesForLeadTime",
        "leadTimes", "supplierByBarcode", "totals",
    }
    assert payload["defaultLeadTimeDays"] == 3
    assert payload["leadTimes"]["Tempo"]["median_days"] == 7
    assert payload["leadTimes"]["Osem"]["median_days"] is None
    assert payload["supplierByBarcode"]["7290000066318"] == "Tempo"
    assert payload["totals"] == {"receipts": 4, "suppliers": 2, "barcodes": 2}


def test_empty_ledger_still_writes_a_valid_file(tmp_path: Path) -> None:
    out = tmp_path / "supplier_lead_times.json"
    exit_code = main(["--receipts", str(tmp_path / "absent.csv"), "--output", str(out)])
    assert exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["leadTimes"] == {}
    assert payload["supplierByBarcode"] == {}
    assert payload["totals"]["receipts"] == 0


def test_main_writes_the_export_to_disk(tmp_path: Path) -> None:
    ledger = tmp_path / "receipts.csv"
    _seed(ledger)
    out = tmp_path / "nested" / "supplier_lead_times.json"

    assert main(["--receipts", str(ledger), "--output", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["leadTimes"]["Tempo"]["confidence"] == "medium"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests/test_export_supplier_lead_times.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.export_supplier_lead_times'`

(If the import fails because `scripts/` is not a package, add an empty `scripts/__init__.py`. Check first — several existing scripts are imported this way or not at all.)

- [ ] **Step 3: Implement the export script**

Create `scripts/export_supplier_lead_times.py`:

```python
#!/usr/bin/env python3
"""
export_supplier_lead_times.py — publish measured lead times to the frontend pipeline.

scripts/normalize-datasets.mjs hardcoded `leadTimeDays: 3` for all 7,674 products
because no real delivery interval had ever been observed. This writes what the
receiving ledger now knows so that script can stop guessing.

Usage:
    python3 scripts/export_supplier_lead_times.py
    python3 scripts/export_supplier_lead_times.py --receipts path.csv --output out.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.paths import RECEIPTS_CSV, SUPPLIER_LEAD_TIMES_JSON  # noqa: E402
from src.internal.receiving import (  # noqa: E402
    DEFAULT_LEAD_TIME_DAYS,
    MIN_DELIVERIES_FOR_LEAD_TIME,
    barcode_supplier_map,
    load_receipts,
    supplier_lead_times,
)


def build_lead_time_export(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    lead_times = supplier_lead_times(receipts)
    by_barcode = barcode_supplier_map(receipts)
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "defaultLeadTimeDays": DEFAULT_LEAD_TIME_DAYS,
        "minDeliveriesForLeadTime": MIN_DELIVERIES_FOR_LEAD_TIME,
        "leadTimes": lead_times,
        "supplierByBarcode": by_barcode,
        "totals": {
            "receipts": len(receipts),
            "suppliers": len(lead_times),
            "barcodes": len(by_barcode),
        },
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export measured supplier lead times.")
    parser.add_argument("--receipts", default=str(RECEIPTS_CSV))
    parser.add_argument("--output", default=str(SUPPLIER_LEAD_TIMES_JSON))
    args = parser.parse_args(argv)

    payload = build_lead_time_export(load_receipts(Path(args.receipts)))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    measured = [s for s, v in payload["leadTimes"].items() if v["median_days"] is not None]
    print(
        f"Wrote {out} — {payload['totals']['receipts']} receipts, "
        f"{payload['totals']['suppliers']} suppliers, "
        f"{len(measured)} with a measured lead time."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add the npm script**

In `package.json`, next to `"data:velocity"`, add:

```json
    "data:lead-times": "python3 scripts/export_supplier_lead_times.py",
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests/test_export_supplier_lead_times.py -q`
Expected: PASS, 3 passed.

- [ ] **Step 6: Run the full pytest suite**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests -q`
Expected: PASS, 124 passed.

- [ ] **Step 7: Commit**

```bash
git add scripts/export_supplier_lead_times.py tests/test_export_supplier_lead_times.py package.json
git commit -m "feat: export measured supplier lead times for the frontend pipeline"
```

---

## Task 5: Replace the hardcoded `leadTimeDays: 3`

**Files:**
- Create: `src/lib/receiving/leadTimeResolver.js`
- Test: `src/lib/receiving/__tests__/leadTimeResolver.test.js`
- Modify: `scripts/normalize-datasets.mjs:85-113`

**Interfaces:**
- Consumes: the JSON contract produced by Task 4.
- Produces:
  - `DEFAULT_LEAD_TIME_DAYS = 3`, `DEFAULT_SUPPLIER = 'YomYom'`
  - `emptyLedger() -> LeadTimeLedger` — `{ defaultLeadTimeDays, leadTimes: {}, supplierByBarcode: {} }`
  - `normalizeLedger(raw) -> LeadTimeLedger` — tolerates `null`, a missing file, or a malformed payload
  - `resolveSupplierAndLeadTime(barcode, ledger) -> { supplier, leadTimeDays, leadTimeConfidence, leadTimeSource }`
    where `leadTimeSource` is `'measured' | 'default'` and `leadTimeConfidence` is `'low' | 'medium' | 'high'`.

- [ ] **Step 1: Write the failing test**

Create `src/lib/receiving/__tests__/leadTimeResolver.test.js`:

```js
import { describe, expect, it } from 'vitest'

import {
  DEFAULT_LEAD_TIME_DAYS,
  DEFAULT_SUPPLIER,
  emptyLedger,
  normalizeLedger,
  resolveSupplierAndLeadTime,
} from '../leadTimeResolver.js'

const LEDGER = normalizeLedger({
  defaultLeadTimeDays: 3,
  leadTimes: {
    Tempo: { median_days: 7, n_observations: 4, confidence: 'medium' },
    Osem: { median_days: null, n_observations: 2, confidence: 'low' },
    Strauss: { median_days: 2.5, n_observations: 8, confidence: 'high' },
  },
  supplierByBarcode: { 111: 'Tempo', 222: 'Osem', 333: 'Strauss' },
})

describe('leadTimeResolver', () => {
  it('falls back to the defaults for a barcode the ledger has never seen', () => {
    expect(resolveSupplierAndLeadTime('999', LEDGER)).toEqual({
      supplier: DEFAULT_SUPPLIER,
      leadTimeDays: DEFAULT_LEAD_TIME_DAYS,
      leadTimeConfidence: 'low',
      leadTimeSource: 'default',
    })
  })

  it('uses the measured median when the supplier has enough deliveries', () => {
    expect(resolveSupplierAndLeadTime('111', LEDGER)).toEqual({
      supplier: 'Tempo',
      leadTimeDays: 7,
      leadTimeConfidence: 'medium',
      leadTimeSource: 'measured',
    })
  })

  it('keeps the real supplier but the default lead time below three deliveries', () => {
    expect(resolveSupplierAndLeadTime('222', LEDGER)).toEqual({
      supplier: 'Osem',
      leadTimeDays: DEFAULT_LEAD_TIME_DAYS,
      leadTimeConfidence: 'low',
      leadTimeSource: 'default',
    })
  })

  it('rounds a fractional median and never returns less than one day', () => {
    expect(resolveSupplierAndLeadTime('333', LEDGER).leadTimeDays).toBe(3)

    const sameDay = normalizeLedger({
      leadTimes: { Fast: { median_days: 0.2, n_observations: 5, confidence: 'medium' } },
      supplierByBarcode: { 444: 'Fast' },
    })
    expect(resolveSupplierAndLeadTime('444', sameDay).leadTimeDays).toBe(1)
  })

  it('strips a ym- prefix and leading zeroes so product ids resolve', () => {
    expect(resolveSupplierAndLeadTime('ym-111', LEDGER).supplier).toBe('Tempo')
    expect(resolveSupplierAndLeadTime('000111', LEDGER).supplier).toBe('Tempo')
  })

  it('treats a missing, null or malformed ledger as empty rather than throwing', () => {
    for (const raw of [null, undefined, 'nonsense', 42, { leadTimes: 'bad' }]) {
      const ledger = normalizeLedger(raw)
      expect(ledger.leadTimes).toEqual({})
      expect(resolveSupplierAndLeadTime('111', ledger).leadTimeSource).toBe('default')
    }
  })

  it('emptyLedger resolves everything to the defaults', () => {
    const resolved = resolveSupplierAndLeadTime('111', emptyLedger())
    expect(resolved.supplier).toBe(DEFAULT_SUPPLIER)
    expect(resolved.leadTimeDays).toBe(DEFAULT_LEAD_TIME_DAYS)
  })

  it('handles a barcode whose supplier has no lead-time entry at all', () => {
    const ledger = normalizeLedger({ leadTimes: {}, supplierByBarcode: { 555: 'Ghost' } })
    expect(resolveSupplierAndLeadTime('555', ledger)).toEqual({
      supplier: 'Ghost',
      leadTimeDays: DEFAULT_LEAD_TIME_DAYS,
      leadTimeConfidence: 'low',
      leadTimeSource: 'default',
    })
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/lib/receiving/__tests__/leadTimeResolver.test.js`
Expected: FAIL — cannot resolve `../leadTimeResolver.js`

- [ ] **Step 3: Implement the resolver**

Create `src/lib/receiving/leadTimeResolver.js`:

```js
/**
 * Resolve a product's supplier and lead time from the receiving ledger.
 *
 * Every product reached the UI with `leadTimeDays: 3` and `supplier: 'YomYom'`
 * because the POS export carries neither field. The ledger (T7 / #52) is the
 * first place either is ever observed, so this module is the one place that
 * decides when a measured value replaces the assumed one.
 *
 * The rule is deliberately conservative: below three deliveries from a supplier
 * we keep the default lead time, because a median over two observations is a
 * guess with a decimal point on it.
 */

export const DEFAULT_LEAD_TIME_DAYS = 3
export const DEFAULT_SUPPLIER = 'YomYom'

export function emptyLedger() {
  return {
    defaultLeadTimeDays: DEFAULT_LEAD_TIME_DAYS,
    leadTimes: {},
    supplierByBarcode: {},
  }
}

function isPlainObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Tolerates a missing file, a null payload, or a malformed one. Never throws. */
export function normalizeLedger(raw) {
  if (!isPlainObject(raw)) return emptyLedger()
  const defaultDays = Number(raw.defaultLeadTimeDays)
  return {
    defaultLeadTimeDays: Number.isFinite(defaultDays) && defaultDays > 0
      ? defaultDays
      : DEFAULT_LEAD_TIME_DAYS,
    leadTimes: isPlainObject(raw.leadTimes) ? raw.leadTimes : {},
    supplierByBarcode: isPlainObject(raw.supplierByBarcode) ? raw.supplierByBarcode : {},
  }
}

/** Product ids arrive as `ym-<barcode>`; ledger keys are bare, unpadded barcodes. */
function barcodeKeys(barcode) {
  const raw = String(barcode ?? '').trim().replace(/^ym-/, '')
  if (!raw) return []
  const unpadded = raw.replace(/^0+/, '')
  return unpadded && unpadded !== raw ? [raw, unpadded] : [raw]
}

export function resolveSupplierAndLeadTime(barcode, ledger = emptyLedger()) {
  const safe = normalizeLedger(ledger)
  const fallback = {
    supplier: DEFAULT_SUPPLIER,
    leadTimeDays: safe.defaultLeadTimeDays,
    leadTimeConfidence: 'low',
    leadTimeSource: 'default',
  }

  let supplier = null
  for (const key of barcodeKeys(barcode)) {
    if (Object.prototype.hasOwnProperty.call(safe.supplierByBarcode, key)) {
      supplier = safe.supplierByBarcode[key]
      break
    }
  }
  if (!supplier) return fallback

  const entry = safe.leadTimes[supplier]
  const median = Number(entry?.median_days)
  if (!isPlainObject(entry) || entry.median_days === null || !Number.isFinite(median)) {
    return { ...fallback, supplier }
  }

  return {
    supplier,
    leadTimeDays: Math.max(1, Math.round(median)),
    leadTimeConfidence: entry.confidence ?? 'low',
    leadTimeSource: 'measured',
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run src/lib/receiving/__tests__/leadTimeResolver.test.js`
Expected: PASS, 8 passed.

- [ ] **Step 5: Wire the resolver into `normalize-datasets.mjs`**

`readFileSync` and `path` are already imported at `scripts/normalize-datasets.mjs:2,4` — do not add duplicates. Add only the resolver import, next to the existing ones:

```js
import { normalizeLedger, resolveSupplierAndLeadTime } from '../src/lib/receiving/leadTimeResolver.js'
```

Add the ledger path next to the other `SILVER_*` constants (around line 13):

```js
const LEAD_TIMES_JSON = path.join(rootDir, 'data', 'internal', 'receiving', 'supplier_lead_times.json')
```

Add this helper next to the other module-level helpers, above `loadYomYomSilver` (line 72):

```js
// The receiving ledger is the only source of a real supplier or a real delivery
// interval. It is generated by `npm run data:lead-times` and is absent on a
// fresh clone, which must degrade to the old defaults rather than fail the build.
function loadLeadTimeLedger() {
  if (!existsSync(LEAD_TIMES_JSON)) return normalizeLedger(null)
  try {
    return normalizeLedger(JSON.parse(readFileSync(LEAD_TIMES_JSON, 'utf-8')))
  } catch (err) {
    process.stderr.write(`Warning: ignoring unreadable lead-time ledger: ${err.message}\n`)
    return normalizeLedger(null)
  }
}
```

Inside `loadYomYomSilver`, add one line immediately after the `const raw = JSON.parse(...)` on line 76, so the file is read once rather than per product:

```js
    const leadTimeLedger = loadLeadTimeLedger()
```

Then, in the `.map(row => { ... })` callback, add a `const` beside the existing `hasVelocityData` line (line 83):

```js
        const sourcing = resolveSupplierAndLeadTime(row.barcode, leadTimeLedger)
```

and replace lines 108-109 of the returned object literal:

```js
          supplier: 'YomYom',
          leadTimeDays: 3,
```

with:

```js
          supplier: sourcing.supplier,
          leadTimeDays: sourcing.leadTimeDays,
          // 'default' means no supplier has reached three deliveries yet, so the
          // lead time is still the assumed 3 — say so rather than implying it was measured.
          leadTimeSource: sourcing.leadTimeSource,
          leadTimeConfidence: sourcing.leadTimeConfidence,
```

- [ ] **Step 6: Verify the pipeline still runs and degrades cleanly**

Run: `npm run normalize:data`
Expected: completes with exit 0. The ledger JSON does not exist in this worktree, so every product must come out with `supplier: "YomYom"` and `leadTimeDays: 3` — identical to before.

Then confirm the measured path end to end:

```bash
mkdir -p data/internal/receiving
/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python - <<'PY'
from pathlib import Path
from src.internal.receiving import add_receipt
ledger = Path("data/internal/receiving/receipts.csv")
for day in ("2026-08-01", "2026-08-08", "2026-08-15"):
    add_receipt(barcode="7290000066318", quantity=12, supplier="Tempo",
                received_at=day, path=ledger)
PY
/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python scripts/export_supplier_lead_times.py
npm run normalize:data
```

Expected: the export prints `1 with a measured lead time`, and the normalized output for barcode `7290000066318` now carries `supplier: "Tempo"`, `leadTimeDays: 7`, `leadTimeSource: "measured"`. Confirm by grepping the generated dataset. Then delete the scratch ledger: `rm -rf data/internal/receiving`.

- [ ] **Step 7: Run lint and the full JS suite**

Run: `npm run lint && npm test`
Expected: lint exits 0; 183 tests pass (175 after Task 0 + 8 new).

- [ ] **Step 8: Commit**

```bash
git add src/lib/receiving/leadTimeResolver.js src/lib/receiving/__tests__/leadTimeResolver.test.js scripts/normalize-datasets.mjs
git commit -m "feat: measured supplier lead time replaces the hardcoded 3"
```

---

## Task 6: The receiving queue — pure logic

**Files:**
- Create: `src/lib/receiving/receivingQueue.js`
- Test: `src/lib/receiving/__tests__/receivingQueue.test.js`

**Interfaces:**
- Consumes: nothing from earlier tasks. The CSV header it emits must match the columns `import_receiving_csv` (Task 1) reads.
- Produces:
  - `RECEIVING_QUEUE_KEY = 'receiving_queue'`, `LAST_SUPPLIER_KEY = 'receiving_last_supplier'`
  - `RECEIVING_CSV_HEADER = 'barcode,product_name,quantity,supplier,unit_cost,received_at,expiry_date,recorded_at,source'`
  - `todayIso(now = new Date()) -> string`
  - `makeEntry(input, { now } = {}) -> Entry` — throws `Error` with a display-ready message on invalid input
  - `appendEntry(queue, entry) -> Entry[]` (newest first)
  - `undoLast(queue) -> Entry[]`
  - `knownSuppliers(queue) -> string[]`
  - `toCsv(queue) -> string`
  - `loadQueue(storage) -> Entry[]`, `saveQueue(queue, storage) -> void`
  - `readLastSupplier(storage) -> string`, `rememberLastSupplier(supplier, storage) -> void`
  - `getStorage() -> Storage | null`

An `Entry` is `{ barcode, productName, quantity, supplier, unitCost, receivedAt, expiryDate, recordedAt, source }` — `productName` is `''` when unmatched, `unitCost` and `expiryDate` are `''` when absent, `source` is always `'manual_ui'`.

- [ ] **Step 1: Write the failing test**

Create `src/lib/receiving/__tests__/receivingQueue.test.js`:

```js
import { beforeEach, describe, expect, it } from 'vitest'

import {
  RECEIVING_CSV_HEADER,
  RECEIVING_QUEUE_KEY,
  appendEntry,
  knownSuppliers,
  loadQueue,
  makeEntry,
  readLastSupplier,
  rememberLastSupplier,
  saveQueue,
  toCsv,
  todayIso,
  undoLast,
} from '../receivingQueue.js'

function fakeStorage(seed = {}) {
  const store = new Map(Object.entries(seed))
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  }
}

function validInput(overrides = {}) {
  return {
    barcode: '7290000066318',
    productName: 'קוקה קולה 1.5 ליטר',
    quantity: '24',
    supplier: 'Tempo',
    unitCost: '4.5',
    receivedAt: '2026-08-10',
    expiryDate: '2026-12-31',
    ...overrides,
  }
}

describe('makeEntry', () => {
  it('normalizes a complete line', () => {
    const entry = makeEntry(validInput(), { now: new Date('2026-08-13T09:00:00Z') })
    expect(entry).toEqual({
      barcode: '7290000066318',
      productName: 'קוקה קולה 1.5 ליטר',
      quantity: 24,
      supplier: 'Tempo',
      unitCost: 4.5,
      receivedAt: '2026-08-10',
      expiryDate: '2026-12-31',
      recordedAt: '2026-08-13T09:00:00.000Z',
      source: 'manual_ui',
    })
  })

  it('defaults receivedAt to today', () => {
    const entry = makeEntry(validInput({ receivedAt: '' }), { now: new Date('2026-08-13T09:00:00Z') })
    expect(entry.receivedAt).toBe('2026-08-13')
  })

  it('accepts a line with no expiry date and no unit cost', () => {
    const entry = makeEntry(validInput({ expiryDate: '', unitCost: '' }))
    expect(entry.expiryDate).toBe('')
    expect(entry.unitCost).toBe('')
  })

  it('trims the barcode and the supplier', () => {
    const entry = makeEntry(validInput({ barcode: '  111  ', supplier: '  Osem  ' }))
    expect(entry.barcode).toBe('111')
    expect(entry.supplier).toBe('Osem')
  })

  it.each([
    ['', 'barcode'],
    ['   ', 'barcode'],
  ])('rejects a missing barcode (%s)', (barcode) => {
    expect(() => makeEntry(validInput({ barcode }))).toThrow(/barcode/i)
  })

  it.each(['', '0', '-3', 'abc', '2.5'])('rejects quantity %s', (quantity) => {
    expect(() => makeEntry(validInput({ quantity }))).toThrow(/quantity/i)
  })

  it.each(['', '   '])('rejects a missing supplier (%s)', (supplier) => {
    expect(() => makeEntry(validInput({ supplier }))).toThrow(/supplier/i)
  })

  it('rejects a negative or non-numeric unit cost', () => {
    expect(() => makeEntry(validInput({ unitCost: '-1' }))).toThrow(/cost/i)
    expect(() => makeEntry(validInput({ unitCost: 'free' }))).toThrow(/cost/i)
  })
})

describe('queue operations', () => {
  it('puts the newest entry first', () => {
    const first = makeEntry(validInput({ barcode: '111' }))
    const second = makeEntry(validInput({ barcode: '222' }))
    const queue = appendEntry(appendEntry([], first), second)
    expect(queue.map((row) => row.barcode)).toEqual(['222', '111'])
  })

  it('does not mutate the array it is given', () => {
    const queue = []
    appendEntry(queue, makeEntry(validInput()))
    expect(queue).toEqual([])
  })

  it('undo removes only the most recent entry', () => {
    const queue = appendEntry(
      appendEntry([], makeEntry(validInput({ barcode: '111' }))),
      makeEntry(validInput({ barcode: '222' })),
    )
    expect(undoLast(queue).map((row) => row.barcode)).toEqual(['111'])
  })

  it('undo on an empty queue is a no-op', () => {
    expect(undoLast([])).toEqual([])
  })

  it('lists known suppliers uniquely and sorted', () => {
    const queue = [
      makeEntry(validInput({ supplier: 'Tempo' })),
      makeEntry(validInput({ supplier: 'Osem' })),
      makeEntry(validInput({ supplier: 'Tempo' })),
    ]
    expect(knownSuppliers(queue)).toEqual(['Osem', 'Tempo'])
  })
})

describe('toCsv', () => {
  it('emits the header the Python importer reads', () => {
    expect(toCsv([]).trim()).toBe(RECEIVING_CSV_HEADER)
  })

  it('emits one row per entry in the header order', () => {
    const csv = toCsv([makeEntry(validInput(), { now: new Date('2026-08-13T09:00:00Z') })])
    const [header, row] = csv.trim().split('\n')
    expect(header).toBe(RECEIVING_CSV_HEADER)
    expect(row).toBe(
      '7290000066318,"קוקה קולה 1.5 ליטר",24,Tempo,4.5,2026-08-10,2026-12-31,2026-08-13T09:00:00.000Z,manual_ui',
    )
  })

  it('quotes a product name containing a comma or a quote', () => {
    const csv = toCsv([makeEntry(validInput({ productName: 'במבה, גדול "ענק"' }))])
    expect(csv).toContain('"במבה, גדול ""ענק"""')
  })
})

describe('storage', () => {
  let storage
  beforeEach(() => {
    storage = fakeStorage()
  })

  it('round-trips the queue', () => {
    const queue = [makeEntry(validInput())]
    saveQueue(queue, storage)
    expect(loadQueue(storage)).toEqual(queue)
  })

  it('reads an absent, empty or corrupt value as an empty queue', () => {
    expect(loadQueue(fakeStorage())).toEqual([])
    expect(loadQueue(fakeStorage({ [RECEIVING_QUEUE_KEY]: 'not json' }))).toEqual([])
    expect(loadQueue(fakeStorage({ [RECEIVING_QUEUE_KEY]: '{"not":"an array"}' }))).toEqual([])
    expect(loadQueue(null)).toEqual([])
  })

  it('remembers the last supplier across loads', () => {
    rememberLastSupplier('Tempo', storage)
    expect(readLastSupplier(storage)).toBe('Tempo')
  })

  it('reads an unset last supplier as an empty string', () => {
    expect(readLastSupplier(fakeStorage())).toBe('')
    expect(readLastSupplier(null)).toBe('')
  })

  it('never throws when storage rejects a write', () => {
    const failing = {
      getItem: () => null,
      setItem: () => { throw new Error('QuotaExceededError') },
      removeItem: () => {},
    }
    expect(() => saveQueue([], failing)).not.toThrow()
    expect(() => rememberLastSupplier('Tempo', failing)).not.toThrow()
  })
})

describe('todayIso', () => {
  it('returns the UTC calendar date', () => {
    expect(todayIso(new Date('2026-08-13T22:30:00Z'))).toBe('2026-08-13')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npx vitest run src/lib/receiving/__tests__/receivingQueue.test.js`
Expected: FAIL — cannot resolve `../receivingQueue.js`

- [ ] **Step 3: Implement the queue module**

Create `src/lib/receiving/receivingQueue.js`:

```js
/**
 * The receiving queue — every decision about a delivery line except how it looks.
 *
 * Kept separate from the form component for two reasons. The obvious one is that
 * vitest runs in a node environment with no DOM, so this is the only layer that
 * can be tested at all. The load-bearing one is that a mis-typed quantity or a
 * dropped queue is a data-integrity failure, and those rules should not live
 * inside a render function.
 *
 * Nothing here touches the network. The shop's connection drops, and a delivery
 * that cannot be recorded is a delivery that gets written on paper instead.
 */

export const RECEIVING_QUEUE_KEY = 'receiving_queue'
export const LAST_SUPPLIER_KEY = 'receiving_last_supplier'

// Must stay in lockstep with RECEIVING_COLUMNS in src/internal/receiving.py.
// receipt_id is derived server-side and is deliberately absent here.
export const RECEIVING_CSV_HEADER =
  'barcode,product_name,quantity,supplier,unit_cost,received_at,expiry_date,recorded_at,source'

const CSV_FIELDS = [
  'barcode', 'productName', 'quantity', 'supplier',
  'unitCost', 'receivedAt', 'expiryDate', 'recordedAt', 'source',
]

export function todayIso(now = new Date()) {
  return now.toISOString().slice(0, 10)
}

/** The real localStorage when there is one — absent in the node test environment. */
export function getStorage() {
  return typeof globalThis.localStorage !== 'undefined' ? globalThis.localStorage : null
}

function text(value) {
  return String(value ?? '').trim()
}

export function makeEntry(input, { now = new Date() } = {}) {
  const barcode = text(input?.barcode)
  if (!barcode) throw new Error('Scan or type a barcode first.')

  const rawQuantity = text(input?.quantity)
  if (!/^\d+$/.test(rawQuantity)) {
    throw new Error('Quantity must be a whole number of units.')
  }
  const quantity = Number(rawQuantity)
  if (quantity <= 0) throw new Error('Quantity must be at least 1 unit.')

  const supplier = text(input?.supplier)
  if (!supplier) throw new Error('Enter the supplier on the delivery note.')

  const rawCost = text(input?.unitCost)
  let unitCost = ''
  if (rawCost) {
    const parsed = Number(rawCost)
    if (!Number.isFinite(parsed) || parsed < 0) {
      throw new Error('Unit cost must be a number of shekels, or left blank.')
    }
    unitCost = parsed
  }

  return {
    barcode,
    productName: text(input?.productName),
    quantity,
    supplier,
    unitCost,
    receivedAt: text(input?.receivedAt) || todayIso(now),
    expiryDate: text(input?.expiryDate),
    recordedAt: now.toISOString(),
    source: 'manual_ui',
  }
}

export function appendEntry(queue, entry) {
  return [entry, ...(Array.isArray(queue) ? queue : [])]
}

export function undoLast(queue) {
  return Array.isArray(queue) ? queue.slice(1) : []
}

export function knownSuppliers(queue) {
  const seen = new Set()
  for (const entry of Array.isArray(queue) ? queue : []) {
    const supplier = text(entry?.supplier)
    if (supplier) seen.add(supplier)
  }
  return [...seen].sort((a, b) => a.localeCompare(b))
}

function csvCell(value) {
  const raw = value === '' || value === null || value === undefined ? '' : String(value)
  return /[",\n]/.test(raw) ? `"${raw.replace(/"/g, '""')}"` : raw
}

export function toCsv(queue) {
  const rows = (Array.isArray(queue) ? queue : []).map((entry) =>
    CSV_FIELDS.map((field) => csvCell(entry?.[field])).join(','),
  )
  return [RECEIVING_CSV_HEADER, ...rows].join('\n') + '\n'
}

export function loadQueue(storage = getStorage()) {
  if (!storage) return []
  try {
    const parsed = JSON.parse(storage.getItem(RECEIVING_QUEUE_KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveQueue(queue, storage = getStorage()) {
  if (!storage) return
  try {
    storage.setItem(RECEIVING_QUEUE_KEY, JSON.stringify(queue))
  } catch {
    // A full quota must not lose the line the manager just typed — it stays in
    // React state and the CSV export still sees it.
  }
}

export function readLastSupplier(storage = getStorage()) {
  if (!storage) return ''
  try {
    return text(storage.getItem(LAST_SUPPLIER_KEY))
  } catch {
    return ''
  }
}

export function rememberLastSupplier(supplier, storage = getStorage()) {
  if (!storage) return
  try {
    storage.setItem(LAST_SUPPLIER_KEY, text(supplier))
  } catch {
    /* nothing to do — the field simply will not pre-fill next time */
  }
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npx vitest run src/lib/receiving/__tests__/receivingQueue.test.js`
Expected: PASS, 28 passed (the `it.each` blocks contribute 2 + 5 + 2 cases).

- [ ] **Step 5: Run lint and the full JS suite**

Run: `npm run lint && npm test`
Expected: lint exits 0; 211 tests pass (183 after Task 5 + 28 new).

- [ ] **Step 6: Commit**

```bash
git add src/lib/receiving/receivingQueue.js src/lib/receiving/__tests__/receivingQueue.test.js
git commit -m "feat: receiving queue — entry validation, undo, supplier memory, CSV export"
```

---

## Task 7: The capture form

**Files:**
- Create: `src/components/receiving/ReceivingCaptureForm.jsx`
- Test: `src/components/receiving/__tests__/ReceivingCaptureForm.test.jsx`
- Modify: `src/pages/ExpiryPage.jsx:36-40, 48-99, 111-205`
- Modify: `src/App.css:2522-2575` (extend the existing "Expiry capture" block)

**Interfaces:**
- Consumes: every export of `src/lib/receiving/receivingQueue.js` (Task 6); `dirProps` from `src/lib/utils/rtl.js`; `formatBarcode`, `formatDate` from `src/lib/utils/format.js`; `Button` from `src/components/shared/Button.jsx`; the jsdom setup from Task 0.
- Produces: `<ReceivingCaptureForm products={products} />` — self-contained, owns its own queue state, takes no callbacks.

**What the component tests cover:** wiring and interaction — the focus jump, undo, supplier carry-over, the error path, and queue persistence across a remount. They do **not** re-assert the validation rules; those belong to `receivingQueue.js` and are covered by Task 6's 28 tests. Layout at 390 px and the stopwatch test stay manual (Step 7).

- [ ] **Step 1: Write the component**

Create `src/components/receiving/ReceivingCaptureForm.jsx`:

```jsx
import { useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '../shared/Button.jsx'
import { formatBarcode, formatDate } from '../../lib/utils/format.js'
import { dirProps } from '../../lib/utils/rtl.js'
import {
  appendEntry,
  knownSuppliers,
  loadQueue,
  makeEntry,
  readLastSupplier,
  rememberLastSupplier,
  saveQueue,
  toCsv,
  todayIso,
  undoLast,
} from '../../lib/receiving/receivingQueue.js'

/**
 * Recording a delivery has to beat writing it on paper. If it does not, the
 * manager stops after a week and every downstream track that needs this data
 * dies with it. That is why the barcode field jumps straight to quantity, why
 * the supplier is remembered between lines, and why nothing here waits on a
 * network call.
 */
export function ReceivingCaptureForm({ products = [] }) {
  const [queue, setQueue] = useState(() => loadQueue())
  const [barcode, setBarcode] = useState('')
  const [quantity, setQuantity] = useState('')
  const [supplier, setSupplier] = useState(() => readLastSupplier())
  const [unitCost, setUnitCost] = useState('')
  const [receivedAt, setReceivedAt] = useState(() => todayIso())
  const [expiryDate, setExpiryDate] = useState('')
  const [error, setError] = useState('')
  const [justAdded, setJustAdded] = useState(null)

  const barcodeRef = useRef(null)
  const quantityRef = useRef(null)

  useEffect(() => saveQueue(queue), [queue])

  // Confirming the right item before committing is the whole point of the
  // lookup — a mis-scan is otherwise invisible until the data is already wrong.
  const byBarcode = useMemo(() => {
    const map = new Map()
    for (const product of products) {
      const code = String(product.id ?? '').replace(/^ym-/, '')
      if (code) map.set(code, product)
    }
    return map
  }, [products])

  const trimmed = barcode.trim()
  const matchedProduct = trimmed
    ? byBarcode.get(trimmed.replace(/^0+/, '')) ?? byBarcode.get(trimmed)
    : null

  const supplierOptions = useMemo(() => knownSuppliers(queue), [queue])

  function handleBarcodeKeyDown(event) {
    if (event.key !== 'Enter') return
    // A barcode gun sends Enter after the digits. Submitting here would save a
    // line with no quantity, so Enter moves to the next field instead.
    event.preventDefault()
    if (trimmed) quantityRef.current?.focus()
  }

  function handleSubmit(event) {
    event.preventDefault()
    let entry
    try {
      entry = makeEntry({
        barcode,
        productName: matchedProduct?.name ?? '',
        quantity,
        supplier,
        unitCost,
        receivedAt,
        expiryDate,
      })
    } catch (err) {
      setError(err.message)
      return
    }

    setQueue((current) => appendEntry(current, entry))
    rememberLastSupplier(entry.supplier)
    setJustAdded(`${entry.quantity} × ${entry.productName || formatBarcode(entry.barcode)}`)
    setError('')

    // Supplier, date and cost carry over — a delivery is usually twenty items
    // from one supplier on one day.
    setBarcode('')
    setQuantity('')
    setExpiryDate('')
    barcodeRef.current?.focus()
  }

  function handleUndo() {
    setQueue((current) => undoLast(current))
    setJustAdded(null)
    setError('')
    barcodeRef.current?.focus()
  }

  function downloadCsv() {
    const blob = new Blob([toCsv(queue)], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `receiving_${todayIso()}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <form className="receiving-capture" onSubmit={handleSubmit}>
        <label className="expiry-field receiving-field-barcode">
          <span>Barcode</span>
          <input
            ref={barcodeRef}
            className="expiry-input"
            value={barcode}
            onChange={(e) => { setBarcode(e.target.value); setJustAdded(null); setError('') }}
            onKeyDown={handleBarcodeKeyDown}
            placeholder="Scan or type"
            inputMode="numeric"
            autoComplete="off"
            aria-describedby="receiving-match"
          />
        </label>

        <label className="expiry-field receiving-field-quantity">
          <span>Quantity *</span>
          <input
            ref={quantityRef}
            className="expiry-input"
            value={quantity}
            onChange={(e) => { setQuantity(e.target.value); setError('') }}
            placeholder="Units"
            inputMode="numeric"
            autoComplete="off"
          />
        </label>

        <label className="expiry-field">
          <span>Supplier *</span>
          <input
            className="expiry-input"
            value={supplier}
            onChange={(e) => { setSupplier(e.target.value); setError('') }}
            list="receiving-suppliers"
            placeholder="From the delivery note"
            autoComplete="off"
          />
          <datalist id="receiving-suppliers">
            {supplierOptions.map((name) => <option key={name} value={name} />)}
          </datalist>
        </label>

        <label className="expiry-field receiving-field-cost">
          <span>Unit cost ₪</span>
          <input
            className="expiry-input"
            value={unitCost}
            onChange={(e) => { setUnitCost(e.target.value); setError('') }}
            placeholder="Optional"
            inputMode="decimal"
            autoComplete="off"
          />
        </label>

        <label className="expiry-field">
          <span>Received *</span>
          <input
            className="expiry-input"
            type="date"
            value={receivedAt}
            onChange={(e) => setReceivedAt(e.target.value)}
          />
        </label>

        <label className="expiry-field">
          <span>Expiry date</span>
          <input
            className="expiry-input"
            type="date"
            value={expiryDate}
            onChange={(e) => setExpiryDate(e.target.value)}
          />
        </label>

        <Button tone="primary" {...{ type: 'submit' }}>Save</Button>
      </form>

      <p id="receiving-match" className="expiry-match" aria-live="polite">
        {error && <span className="expiry-match-warn">{error}</span>}
        {!error && trimmed && matchedProduct && (
          <span className="expiry-match-ok" dir="auto">✓ {matchedProduct.name}</span>
        )}
        {!error && trimmed && !matchedProduct && (
          <span className="expiry-match-warn">
            Not found in the catalog — check the barcode. You can still save it.
          </span>
        )}
        {!error && !trimmed && justAdded && (
          <span className="expiry-match-ok" dir="auto">Saved: {justAdded}</span>
        )}
      </p>

      {queue.length > 0 && (
        <>
          <div className="recommendation-actions" style={{ marginTop: '1rem', gap: '0.5rem' }}>
            <Button tone="secondary" onClick={downloadCsv}>
              Download {queue.length} recorded {queue.length === 1 ? 'line' : 'lines'}
            </Button>
            <Button tone="ghost" onClick={handleUndo}>Undo last</Button>
            <Button tone="ghost" onClick={() => setQueue([])}>Clear list</Button>
          </div>
          <p className="page-description" style={{ marginTop: '0.5rem' }}>
            Deliveries are saved on this device and survive closing the app. Send the
            downloaded file to the SmartShelf team to load it in.
          </p>
          <div className="compact-list">
            {queue.slice(0, 10).map((row, idx) => (
              <div className="compact-row" key={`${row.barcode}:${row.recordedAt}:${idx}`}>
                <div>
                  <strong {...dirProps(row.productName || row.barcode)}>
                    {row.productName || formatBarcode(row.barcode)}
                  </strong>
                  <span>{row.quantity} units · {row.supplier}</span>
                </div>
                <div className="compact-row-end date-cell">
                  <small>{formatDate(row.receivedAt)}</small>
                  {row.expiryDate && <small>exp {formatDate(row.expiryDate)}</small>}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}
```

- [ ] **Step 2: Host it in `ExpiryPage.jsx`**

Delete from `src/pages/ExpiryPage.jsx`: the `QUEUE_KEY`, `loadQueue`, `saveQueue`, `toCsv`, `isoInDays` helpers (lines 17-46); the `queue`, `barcode`, `expiryDate`, `justAdded` state, the `useEffect`, the `byBarcode` memo, `trimmed`, `matchedProduct`, `addToQueue` and `downloadCsv` (lines 53-99); and the whole `<form>`, `.expiry-quick`, `#expiry-match` and queue-list block (lines 124-205). All of it now lives in the component.

Add the import:

```jsx
import { ReceivingCaptureForm } from '../components/receiving/ReceivingCaptureForm.jsx'
```

Replace the panel body (what was lines 118-205) with:

```jsx
        <p className="page-description">
          When goods arrive, record what came in: how many, from whom, and the date on
          the package if there is one. This is the only record of what the shop actually
          receives — the POS export contains neither deliveries nor expiry dates.
        </p>

        <ReceivingCaptureForm products={products} />
```

And change the panel heading (line 115) from `<h2>Record expiry at intake</h2>` to `<h2>Record a delivery</h2>`.

Remove the now-unused imports from `ExpiryPage.jsx` — `dirProps` and `formatBarcode` if nothing else on the page uses them (the alerts list at lines 226-241 still uses both, so check before deleting). ESLint will fail the build on an unused import.

- [ ] **Step 3: Add the styles**

In `src/App.css`, after the existing `.expiry-match-warn` rule (line 2573), add:

```css
/* ── Receiving capture (T7 / #52) ────────────────────────────────────────── */

/* Six fields on a 390 px phone: a two-column grid keeps every control at a
   thumb-sized target instead of collapsing to a single scrolling column. */
.receiving-capture {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  align-items: end;
}

.receiving-capture .expiry-field {
  flex: initial;
  min-width: 0;
}

/* Barcode is scanned first and is the widest value on the line. */
.receiving-field-barcode {
  grid-column: 1 / -1;
}

.receiving-capture > button {
  grid-column: 1 / -1;
  min-height: 3rem;
}

@media (min-width: 48rem) {
  .receiving-capture {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .receiving-field-barcode {
    grid-column: auto;
  }
  .receiving-capture > button {
    grid-column: auto;
  }
}
```

- [ ] **Step 4: Write the component tests**

Create `src/components/receiving/__tests__/ReceivingCaptureForm.test.jsx`:

```jsx
// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ReceivingCaptureForm } from '../ReceivingCaptureForm.jsx'
import { RECEIVING_QUEUE_KEY, LAST_SUPPLIER_KEY } from '../../../lib/receiving/receivingQueue.js'

const PRODUCTS = [{ id: 'ym-7290000066318', name: 'קוקה קולה 1.5 ליטר' }]

afterEach(cleanup)
beforeEach(() => {
  globalThis.localStorage.clear()
})

function fields() {
  return {
    barcode: screen.getByLabelText(/barcode/i),
    quantity: screen.getByLabelText(/quantity/i),
    supplier: screen.getByLabelText(/supplier/i),
    save: screen.getByRole('button', { name: /^save$/i }),
  }
}

async function recordOneLine(user, { barcode = '7290000066318', quantity = '24', supplier = 'Tempo' } = {}) {
  const el = fields()
  await user.clear(el.barcode)
  await user.type(el.barcode, barcode)
  await user.clear(el.quantity)
  await user.type(el.quantity, quantity)
  await user.clear(el.supplier)
  await user.type(el.supplier, supplier)
  await user.click(el.save)
}

describe('ReceivingCaptureForm', () => {
  it('shows the Hebrew product name as soon as a known barcode is entered', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await user.type(fields().barcode, '7290000066318')
    expect(screen.getByText(/קוקה קולה 1.5 ליטר/)).toBeDefined()
  })

  it('warns but still allows a barcode that is not in the catalog', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await user.type(fields().barcode, '999')
    expect(screen.getByText(/not found in the catalog/i)).toBeDefined()
  })

  it('moves focus to quantity on Enter in the barcode field instead of submitting', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    const el = fields()
    await user.type(el.barcode, '7290000066318{Enter}')
    expect(document.activeElement).toBe(el.quantity)
    // Nothing was saved: no queue list appeared.
    expect(screen.queryByRole('button', { name: /download/i })).toBeNull()
  })

  it('saves a line and returns focus to the barcode field', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await recordOneLine(user)
    expect(screen.getByText(/saved:/i)).toBeDefined()
    expect(document.activeElement).toBe(fields().barcode)
  })

  it('keeps the supplier but clears barcode and quantity between lines', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await recordOneLine(user, { supplier: 'Tempo' })
    const el = fields()
    expect(el.supplier.value).toBe('Tempo')
    expect(el.barcode.value).toBe('')
    expect(el.quantity.value).toBe('')
  })

  it('shows the validation message and saves nothing when quantity is empty', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    const el = fields()
    await user.type(el.barcode, '7290000066318')
    await user.type(el.supplier, 'Tempo')
    await user.click(el.save)
    expect(screen.getByText(/quantity must be a whole number/i)).toBeDefined()
    expect(screen.queryByRole('button', { name: /download/i })).toBeNull()
  })

  it('undo removes only the most recent line', async () => {
    const user = userEvent.setup()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    await recordOneLine(user, { barcode: '111', quantity: '5' })
    await recordOneLine(user, { barcode: '222', quantity: '6' })
    expect(screen.getByRole('button', { name: /download 2 recorded lines/i })).toBeDefined()

    await user.click(screen.getByRole('button', { name: /undo last/i }))
    expect(screen.getByRole('button', { name: /download 1 recorded line/i })).toBeDefined()
  })

  it('the queue survives a remount, and the supplier pre-fills', async () => {
    const user = userEvent.setup()
    const { unmount } = render(<ReceivingCaptureForm products={PRODUCTS} />)
    await recordOneLine(user, { supplier: 'Osem' })
    expect(globalThis.localStorage.getItem(RECEIVING_QUEUE_KEY)).toContain('Osem')
    expect(globalThis.localStorage.getItem(LAST_SUPPLIER_KEY)).toBe('Osem')

    unmount()
    render(<ReceivingCaptureForm products={PRODUCTS} />)
    expect(screen.getByRole('button', { name: /download 1 recorded line/i })).toBeDefined()
    expect(fields().supplier.value).toBe('Osem')
  })
})
```

If a query fails because a `<label>` is not associated with its input, fix the **component** (that is a real accessibility defect on a touch form), not the query.

- [ ] **Step 5: Run the component tests**

Run: `npx vitest run src/components/receiving/__tests__/ReceivingCaptureForm.test.jsx`
Expected: PASS, 8 passed.

- [ ] **Step 6: Run lint, the full JS suite, and the build**

Run: `npm run lint && npm test && npm run build`
Expected: lint exits 0 (no unused imports left in `ExpiryPage.jsx`); 219 tests pass (211 after Task 6 + 8 new); build exits 0.

- [ ] **Step 7: Verify by hand at 390 px**

Step 4's tests already cover the focus jump, undo, supplier carry-over, the error path and persistence. What remains is what a DOM test cannot see. Run `npm run dev`, open the Expiry page, set the browser device width to **390 px**, and record the result of every line in the task report:

1. **Nothing overflows horizontally at 390 px** — the page must not scroll sideways.
2. **Quantity and Unit cost open a numeric keypad.** Confirm `inputMode="numeric"` and `inputMode="decimal"` on the rendered elements in devtools.
3. **Every control is a thumb-sized target** — no input shorter than the existing `.expiry-input` minimum of 2.9rem.
4. **A Hebrew product name renders right-to-left** inside a left-to-right row without dragging the rest of the row with it.
5. **Focus is visible** as it moves from Barcode to Quantity — a manager cannot use a keyboard flow they cannot see.
6. **Saving with no expiry date and no unit cost works** and reads naturally on screen.
7. **The datalist offers previously used suppliers** after two lines from different suppliers.

- [ ] **Step 8: Commit**

```bash
git add src/components/receiving/ReceivingCaptureForm.jsx src/components/receiving/__tests__/ReceivingCaptureForm.test.jsx src/pages/ExpiryPage.jsx src/App.css
git commit -m "feat: keyboard-first delivery capture form with undo and supplier memory"
```

---

## Task 8: Document the ledger

**Files:**
- Create: `docs/RECEIVING_LEDGER.md`
- Modify: `CLAUDE.md` (two edits)

**Interfaces:** Consumes the finished behaviour of Tasks 1-7. Produces no code.

- [ ] **Step 1: Write the reference doc**

Create `docs/RECEIVING_LEDGER.md` covering, with no placeholders:

- **Why it exists** — the `received` term is missing from `stock_now = opening + received − sold`, and `leadTimeDays` was hardcoded to `3` for all 7,674 products as a result.
- **The daily loop for the manager** — open the Expiry page, scan, quantity, Enter, repeat; download the CSV at the end of the delivery; send it to the SmartShelf team.
- **The loop for the team** — `python3 scripts/import_receiving_csv.py` does not exist; the import is called as
  `/path/to/.venv/bin/python -c "from pathlib import Path; from src.internal.receiving import import_receiving_csv; print(import_receiving_csv(Path('inbox.csv')))"`.
  Then `npm run data:lead-times`, then `npm run normalize:data`.
- **The schema** — the `RECEIVING_COLUMNS` table with the type and nullability of each column.
- **`receipt_id` is not unique by design** — the collision rule from the Global Constraints, spelled out.
- **When a lead time becomes real** — ≥3 distinct delivery dates per supplier; below that the default `3` is retained and confidence is `low`. State the medium/high thresholds.
- **What is still missing** — the identity cannot be closed without a dated opening count and a dated sales series; the ₪63,572 figure must not be shown to the client until ~20 SKUs have been physically counted.

- [ ] **Step 2: Correct the two stale claims in `CLAUDE.md`**

In the **Key Constraints** section, replace the bullet beginning "**There is no sales data anywhere.**" with a statement of the verified position: sales velocity now covers 1,565 of 7,674 products (504 `high`, 1,061 `medium`, 6,109 `none`), so velocity-derived features work for that subset and are suppressed elsewhere by `velocityConfidence: 'none'`.

In the same section, amend the bullet listing hardcoded constants: `leadTimeDays` and `supplier` are no longer hardcoded — they resolve from `data/internal/receiving/supplier_lead_times.json` when present and fall back to `3` / `'YomYom'` when it is absent. `shelfQuantity`, `shelfCapacity`, `returnedUnits` and `damagedUnits` remain hardcoded.

Add a `npm run data:lead-times` row to the commands section.

- [ ] **Step 3: Verify no stale command is documented**

Run: `grep -n "data:lead-times" package.json docs/RECEIVING_LEDGER.md CLAUDE.md`
Expected: a hit in all three files.

- [ ] **Step 4: Commit**

```bash
git add docs/RECEIVING_LEDGER.md CLAUDE.md
git commit -m "docs: receiving ledger reference; correct stale sales-data claims"
```

---

## Task 9: Reconcile recorded deliveries against inferred restocks

**Files:**
- Create: `src/internal/restock_reconcile.py`
- Test: `tests/test_restock_reconcile.py`

**Interfaces:**
- Consumes: `load_receipts` (Task 1); `build_intervals` from `src.snapshots.velocity`.
- Produces:
  - `received_by_barcode(receipts, start=None, end=None) -> dict[str, float]`
  - `reconcile_restocks(receipts, intervals) -> dict[str, dict[str, Any]]` — per barcode,
    `{"inferred_restocked": float, "recorded_received": float, "delta": float, "verdict": str}`
    with `verdict` in `{"matches", "under_recorded", "over_recorded", "no_receipts", "unobserved"}`.
  - `RECONCILE_TOLERANCE_UNITS = 1.0`

**Why this and not the full identity:** `src/snapshots/velocity.py:237` *infers* a restock from any rise in stock between two snapshots, because until now nothing recorded real deliveries. The ledger makes that inference checkable, which is the honest half of Step 5. The other half — `expected = last_counted + Σreceived − Σsold` — needs a dated opening count and a dated sales series, neither of which exists (see Out of scope).

- [ ] **Step 1: Write the failing test**

Create `tests/test_restock_reconcile.py`:

```python
"""
The velocity engine INFERS a restock from any rise in stock between snapshots.
The receiving ledger records what actually arrived. Where the two disagree by
more than a unit, one of them is wrong, and the manager needs to know which.

Every interval here is synthetic — src/snapshots/velocity.py's own tests take the
same approach, because velocity has no ground truth to check against even with
real snapshots.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.internal.restock_reconcile import (  # noqa: E402
    RECONCILE_TOLERANCE_UNITS,
    received_by_barcode,
    reconcile_restocks,
)


def _receipt(barcode: str, day: str, quantity: int, supplier: str = "Tempo") -> dict:
    return {
        "barcode": barcode,
        "supplier": supplier,
        "received_at": day,
        "quantity": str(quantity),
    }


def _interval(barcode: str, restocked: float) -> dict:
    return {"barcode": barcode, "restocked": restocked, "sold": 0.0}


class TestReceivedByBarcode:
    def test_sums_quantities_per_barcode(self) -> None:
        result = received_by_barcode([
            _receipt("111", "2026-08-01", 12),
            _receipt("111", "2026-08-08", 6),
            _receipt("222", "2026-08-01", 4),
        ])
        assert result == {"111": 18.0, "222": 4.0}

    def test_window_excludes_deliveries_outside_it(self) -> None:
        receipts = [
            _receipt("111", "2026-07-01", 10),
            _receipt("111", "2026-08-05", 5),
            _receipt("111", "2026-09-01", 7),
        ]
        assert received_by_barcode(receipts, start="2026-08-01", end="2026-08-31") == {"111": 5.0}

    def test_unparseable_rows_are_skipped_not_counted_as_zero(self) -> None:
        result = received_by_barcode([
            _receipt("111", "not-a-date", 10),
            _receipt("", "2026-08-01", 10),
            _receipt("111", "2026-08-01", 3),
        ])
        assert result == {"111": 3.0}

    def test_empty_ledger_yields_empty_map(self) -> None:
        assert received_by_barcode([]) == {}


class TestReconcileRestocks:
    def test_agreement_within_tolerance_reads_as_a_match(self) -> None:
        result = reconcile_restocks([_receipt("111", "2026-08-01", 12)], [_interval("111", 12.0)])
        assert result["111"]["verdict"] == "matches"
        assert result["111"]["delta"] == 0.0

    def test_tolerance_boundary_is_inclusive(self) -> None:
        result = reconcile_restocks(
            [_receipt("111", "2026-08-01", 12)],
            [_interval("111", 12.0 + RECONCILE_TOLERANCE_UNITS)],
        )
        assert result["111"]["verdict"] == "matches"

    def test_stock_rose_more_than_was_recorded(self) -> None:
        result = reconcile_restocks([_receipt("111", "2026-08-01", 5)], [_interval("111", 20.0)])
        assert result["111"]["verdict"] == "under_recorded"
        assert result["111"]["delta"] == 15.0

    def test_more_was_recorded_than_the_stock_ever_rose(self) -> None:
        result = reconcile_restocks([_receipt("111", "2026-08-01", 30)], [_interval("111", 4.0)])
        assert result["111"]["verdict"] == "over_recorded"
        assert result["111"]["delta"] == -26.0

    def test_stock_rose_with_no_receipt_recorded_at_all(self) -> None:
        result = reconcile_restocks([], [_interval("111", 9.0)])
        assert result["111"]["verdict"] == "no_receipts"
        assert result["111"]["recorded_received"] == 0.0

    def test_receipt_recorded_but_no_snapshot_ever_saw_the_product(self) -> None:
        result = reconcile_restocks([_receipt("111", "2026-08-01", 9)], [])
        assert result["111"]["verdict"] == "unobserved"
        assert result["111"]["inferred_restocked"] == 0.0

    def test_multiple_intervals_for_one_barcode_are_summed(self) -> None:
        result = reconcile_restocks(
            [_receipt("111", "2026-08-01", 20)],
            [_interval("111", 8.0), _interval("111", 12.0)],
        )
        assert result["111"]["verdict"] == "matches"

    def test_barcodes_are_reconciled_independently(self) -> None:
        result = reconcile_restocks(
            [_receipt("111", "2026-08-01", 10), _receipt("222", "2026-08-01", 10)],
            [_interval("111", 10.0), _interval("222", 40.0)],
        )
        assert result["111"]["verdict"] == "matches"
        assert result["222"]["verdict"] == "under_recorded"

    def test_nothing_anywhere_yields_nothing(self) -> None:
        assert reconcile_restocks([], []) == {}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests/test_restock_reconcile.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.internal.restock_reconcile'`

- [ ] **Step 3: Implement the reconciliation**

Create `src/internal/restock_reconcile.py`:

```python
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
    totals: dict[str, float] = {}
    for interval in intervals:
        barcode = _clean(interval.get("barcode"))
        if not barcode:
            continue
        try:
            restocked = float(interval.get("restocked") or 0.0)
        except (TypeError, ValueError):
            continue
        totals[barcode] = totals.get(barcode, 0.0) + restocked
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests/test_restock_reconcile.py -q`
Expected: PASS, 13 passed (4 in `TestReceivedByBarcode`, 9 in `TestReconcileRestocks`).

- [ ] **Step 5: Confirm the interval shape against the real producer**

Run:

```bash
/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -c "
import inspect
from src.snapshots import velocity
print(inspect.getsource(velocity.build_intervals))"
```

Confirm each emitted move carries a `barcode` key and a `restocked` key. If the key names differ, fix `_inferred_by_barcode` and the test's `_interval` helper to match the real producer — the reconciliation is worthless if it reads a field the pipeline does not emit. Record what you found in the task report.

- [ ] **Step 6: Run the full pytest suite**

Run: `/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests -q`
Expected: PASS, 137 passed.

- [ ] **Step 7: Commit**

```bash
git add src/internal/restock_reconcile.py tests/test_restock_reconcile.py
git commit -m "feat: reconcile recorded deliveries against snapshot-inferred restocks"
```

---

## Final verification

After Task 9, all three gates must be green from a clean tree:

```bash
npm run lint
npm test
/Users/anasakkari/Desktop/1-Projects/SmartShelf/.venv/bin/python -m pytest tests -q
npm run build
```

Expected: lint 0, **219 JS tests**, **137 Python tests**, build 0.

## Handover to the human — what this plan does not prove

Report these to the user at the end, as open items rather than completed ones:

1. **The 20-second stopwatch test has not been run.** It requires a real phone and a real person.
2. **"The manager records 3 consecutive deliveries unaided" has not been observed.**
3. **No supplier has 3 deliveries yet**, so every product still resolves to `leadTimeDays: 3` — with `leadTimeSource: 'default'` now saying so honestly instead of pretending. The measured path is tested and wired; it activates on the third delivery from any supplier.
4. **The ₪63,572 discrepancy remains unvalidated** and is surfaced nowhere.
