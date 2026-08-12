# The receiving ledger (T7)

## Why it exists

The inventory identity is:

```
stock_now = opening + received − sold
```

The YomYom POS export gives `sold` (via the [snapshot-delta velocity
proxy](./SNAPSHOT_DURABILITY.md), not real sales history) and `stock_now` directly. It
has never given `received` — nothing in the export records what actually arrived at
the shop. That missing term had a real cost: `leadTimeDays` was a hardcoded `3` for
every one of the 7,674 products, because no delivery interval had ever been observed
to measure it from.

`src/internal/receiving.py` is the first place a real delivery is ever recorded. It is
an **append-only** ledger — a delivery that happened is a fact, and facts are not
edited in place, only added to.

## The daily loop — for the manager

No developer needed for this part.

1. Open the **Expiry** page in the app.
2. In the **Receiving → Record a delivery** panel, scan (or type) the barcode. The
   product's name appears immediately if it's in the catalog — check it matches
   before continuing.
3. The cursor jumps straight to **Quantity**. Type the number of units, then press
   **Enter** (a barcode-gun Enter after the barcode field also jumps here — it does
   not submit).
4. **Supplier** pre-fills with whoever you used last; a delivery is usually twenty
   items from one supplier, not twenty separate suppliers.
5. **Unit cost** and **Expiry date** are optional — fill them in when the delivery
   note has them, skip them when it doesn't.
6. Press **Save**. The line is queued on this device (it survives closing the app,
   and needs no network) and the form resets for the next item, with supplier and
   date carried over.
7. Made a mistake on the last line? **Undo last** removes only that line.
8. When the delivery is fully entered, press **Download N recorded lines**. This
   saves a `receiving_<date>.csv` file.
9. Send that CSV file to the SmartShelf team (WhatsApp, email — whatever channel is
   already in use). Once it's imported, **Clear list** to empty the queue on this
   device.

Every field on the form uses a number pad (`inputMode="numeric"` / `"decimal"`) — it
is built for a phone in a shop, not a desktop.

## The loop for the team — importing what the manager sends

`scripts/import_receiving_csv.py` **does not exist**. There is no dedicated import
script yet — import the CSV directly with the module function, run with **the
project's venv python** (bare `python3` lacks `pyarrow`, which `src/internal/receiving.py`
pulls in transitively):

```bash
/path/to/.venv/bin/python -c "
from pathlib import Path
from src.internal.receiving import import_receiving_csv
print(import_receiving_csv(Path('inbox.csv')))
"
```

Run from the repo root. `import_receiving_csv` appends every valid row from
`inbox.csv` into `data/internal/receiving/receipts.csv` and returns a summary —
`imported_rows`, `rejected_rows`, and a `rejected_preview` of up to 20 bad rows with
the reason each one failed (invalid rows are reported, never silently dropped).

Once the ledger has new rows, republish the derived data (like every other `npm run
data:*` script in this repo, `npm run data:lead-times` shells out to bare `python3` —
have the project venv active on `PATH` first, or it fails the same way the one-liner
above does without it):

```bash
npm run data:lead-times     # receipts.csv -> data/internal/receiving/supplier_lead_times.json
npm run normalize:data      # picks up the new lead-time ledger (see the warning below)
```

`npm run data:lead-times` runs `scripts/export_supplier_lead_times.py`, which reads
every receipt and writes the measured per-supplier lead times and the
barcode → supplier map that `normalize-datasets.mjs` consumes.

### ⚠️ `npm run normalize:data` can destroy the committed dataset

If `data/internal/silver_pos/` is **absent** — which is its state on a fresh clone,
because it is git-ignored — `npm run normalize:data` does not fail. It silently falls
back to the 30-product demo connector and **overwrites the committed
`src/data/demoProducts.js`** (7,451 real products, 141,572 lines) and five other
committed generated files with demo data. This is a pre-existing hazard in the
pipeline, not something this ledger introduces, but it applies directly here: never
run `npm run normalize:data` on a machine where `data/internal/silver_pos/` hasn't
been populated by a real POS import first. Check `ls data/internal/silver_pos/`
before running it, and if it's empty, import the POS data first (see the root
`CLAUDE.md` Python pipeline commands) instead of proceeding.

## The schema — `RECEIVING_COLUMNS`

Defined in `src/internal/receiving.py`, in this exact order (also the CSV export
order from the capture form, minus `receipt_id` which is computed server-side, not
carried in the export):

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `receipt_id` | string (16 hex chars) | no | Derived, not user input. See below — not a uniqueness constraint. |
| `barcode` | string | no | Required. |
| `product_name` | string | yes | Free text; the only column the CSV writer always quotes. |
| `quantity` | int | no | Must be a whole number > 0. |
| `supplier` | string | no | Required; free text from the delivery note. |
| `unit_cost` | float | yes | Must be ≥ 0 if present. |
| `received_at` | ISO date | no | Defaults to today if blank on manual entry. |
| `expiry_date` | ISO date | yes | Feeds `receipts_as_expiry_scans()` into the existing expiry report when present. |
| `recorded_at` | ISO datetime | no | When the row was written, not when the delivery happened. |
| `source` | string | no | `'manual_ui'` from the form, `'csv_import'` (default) from `import_receiving_csv`. |

## `receipt_id` is not unique by design

`receipt_id = sha256(barcode | received_at | supplier)[:16]`. Two separate deliveries
of the same barcode from the same supplier on the same day therefore hash to the same
id — and the ledger keeps **both rows**, because it is append-only. `receipt_id` is a
stable key for re-import (so importing the same CSV twice is recognizable), not a
uniqueness constraint on the ledger. Do not deduplicate on it, and do not add a
uniqueness check without re-reading the docstring in `src/internal/receiving.py` first.

## When a lead time becomes real

`supplier_lead_times()` counts **distinct delivery dates** per supplier, not receipt
lines — twenty items on one delivery note is one delivery, not twenty. Confidence is
gated on that count (`MIN_DELIVERIES_FOR_LEAD_TIME = 3` in the same module):

| Distinct delivery dates | `median_days` | `confidence` |
|---|---|---|
| < 3 | `null` | `low` |
| 3–5 | measured median | `medium` |
| ≥ 6 | measured median | `high` |

Below 3 dates, the default (`DEFAULT_LEAD_TIME_DAYS = 3`) is kept rather than
presenting a median of one or two gaps as a fact.

**Nothing is measured yet.** As of this writing no supplier in the ledger has reached
three distinct delivery dates, so every product still resolves to `leadTimeDays: 3`
— but now honestly: `leadTimeSource: 'default'` says so explicitly, instead of the
old plain constant that gave no indication it was ever a guess. Once a supplier
crosses the 3-date threshold, `resolveSupplierAndLeadTime()`
(`src/lib/receiving/leadTimeResolver.js`) starts returning `leadTimeSource: 'measured'`
and a real `leadTimeDays`/`leadTimeConfidence` for that supplier's products
automatically — no code change needed, just more deliveries recorded.

## Backing up the ledger

`data/internal/receiving/` is **entirely git-ignored** — see the comment block at the
end of `.gitignore`. This was a deliberate decision, made for two different files for
two different reasons:

- `supplier_lead_times.json` is a regenerable build artifact. Lose it and
  `npm run data:lead-times` reproduces it byte-for-byte from `receipts.csv`. No
  backup needed.
- `receipts.csv` is **irreplaceable** — there is no upstream system to regenerate it
  from — but it was still kept out of git, unlike the B-6 snapshot exception
  (`docs/SNAPSHOT_DURABILITY.md`). The reason is what it contains: the client's real
  supplier names and purchase costs. That is private commercial data, materially
  different from the public competitor prices the snapshot exception covers, and it
  does not belong in a repo by the same reasoning that justified committing
  snapshots.

Durability for `receipts.csv` is therefore **out-of-band**, not automatic, and it
rests on two things that already exist in the daily loop and must not be treated as
optional:

1. **The manager's exported CSV is itself a copy.** Every `receiving_<date>.csv`
   downloaded from the capture form is a complete, independent record of that day's
   deliveries. Don't let the manager delete these from their phone/download folder
   immediately after sending — keep them until the corresponding import is confirmed.
2. **The imported `receipts.csv` needs a copy outside the repo.** After each import,
   whoever runs it should copy `data/internal/receiving/receipts.csv` to storage that
   isn't a single laptop's disk — the same class of place the team already keeps
   other client data it can't risk losing. This document is not prescribing a
   specific product or a new script; it is naming the requirement: **the running
   `receipts.csv` must exist in at least one place besides the machine that most
   recently imported into it.** If that machine is lost between backups, the days of
   deliveries recorded since the last copy are lost with it — and every downstream
   number (lead times, the reconciliation this ledger enables) is that much shakier
   until the shop is caught up again.

## What is still missing

The identity `stock_now = opening + received − sold` still cannot be closed. This
ledger supplies `received`. `sold` is a proxy reconstructed from snapshot deltas
(`src/snapshots/velocity.py`), not measured sales. `opening` — a dated, trusted
starting count — does not exist at all. Without it, any attempt to compute an
"expected vs. actual" stock discrepancy is arithmetic built on an unverified
foundation, not a finding.

**The ₪63,572 discrepancy figure must not be shown to the client** until roughly 20
SKUs have been physically counted and the count matches (or the gap is understood).
Until then it stays out of the UI, out of reports, and out of conversation with the
client — it is an internal sanity-check number, not a validated result.
