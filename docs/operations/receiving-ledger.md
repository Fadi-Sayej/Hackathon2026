# The receiving ledger (T7)

## Why it exists

The inventory identity is:

```
stock_now = opening + received − sold
```

The YomYom POS export gives `sold` (via the [snapshot-delta velocity
proxy](./snapshot-durability.md), not real sales history) and `stock_now` directly. It
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
2. Leave the mode on **Delivery** (the default). For something already on the shelf
   that just needs a date, see *Expiry only* below.
3. In the **Receiving → Record a delivery** panel, scan (or type) the barcode. The
   product's name appears immediately if it's in the catalog — check it matches
   before continuing.
4. The cursor jumps straight to **Quantity**. Type the number of units, then press
   **Enter** (a barcode-gun Enter after the barcode field also jumps here — it does
   not submit). Enter in the quantity field saves the line, so a whole delivery can
   be entered without touching the screen.
5. **Supplier** pre-fills with whoever you used last; a delivery is usually twenty
   items from one supplier, not twenty separate suppliers.
6. **Unit cost** and **Expiry date** are optional — fill them in when the delivery
   note has them, skip them when it doesn't.
7. Press **Save**. The line is queued on this device (it survives closing the app,
   and needs no network) and the form resets for the next item, with supplier and
   date carried over.
8. Made a mistake on the last line? **Undo last** removes only that line.
9. When the delivery is fully entered, press **Download N recorded lines**. This
   saves a `receiving_<date>.csv` file.
10. Send that CSV file to the SmartShelf team (WhatsApp, email — whatever channel is
    already in use). Once it's imported, **Clear list** to empty the queue on this
    device.

The three fields that take digits — barcode, quantity and unit cost — ask the phone
for a number pad (`inputMode="numeric"` / `"decimal"`). Supplier is free text with a
dropdown of suppliers already used, and the two dates use the phone's own date
picker. It is built for a phone in a shop, not a desktop.

### Expiry only — a date on something already on the shelf

Not every expiry date comes off a delivery. A worker walking the fridge and finding a
carton dated next week has a date worth recording and no delivery to attach it to.

Switch the mode at the top of the panel to **Expiry only**. Quantity, supplier, unit
cost and the received date disappear; the barcode and the expiry date are all that is
asked for, and the **Quick date** buttons (3 days / 1 week / 2 weeks / 1 month) fill
the date in one tap. **Download** then saves an `expiry_scans_<date>.csv` — a
different file for a different importer, and the two lists are kept separately so an
expiry line can never end up in the receiving ledger claiming a delivery happened.

There is no supplier field here on purpose. Requiring one would mean typing a name
that never delivered the item, and `supplier_lead_times()` would then count that day
as a real delivery date for that supplier.

The team imports that file with the expiry importer, not the receiving one:

```bash
/path/to/.venv/bin/python -c "
from pathlib import Path
from src.expiry.expiry_tracking import import_expiry_csv
print(import_expiry_csv(Path('expiry_scans_2026-08-13.csv')))
"
```

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

Run from the repo root. `import_receiving_csv` appends each new valid row from
`inbox.csv` into `data/internal/receiving/receipts.csv` and returns a summary —
`imported_rows`, `rejected_rows`, and a `rejected_preview` of up to 20 bad rows with
the reason each one failed (invalid rows are reported, never silently dropped), plus
`skipped_duplicates` and a `skipped_preview` for rows that were already in the ledger.

**Importing the same file twice is safe.** A row is skipped when the whole normalized
row already exists — not when `receipt_id` matches, because `receipt_id` collides for
two genuine same-day deliveries (see below) and skipping on it would discard a real
one. The comparison runs after parsing, so `10/08/2026` does not slip past as a new
delivery day. One case the data cannot settle: a hand-written CSV with no
`recorded_at` has no per-line timestamp to distinguish its rows, so it is compared on
its remaining columns — two genuinely identical same-day deliveries typed that way
will have the second reported in `skipped_preview`. Every CSV the capture form
exports carries `recorded_at`, so this only affects files typed by hand.

Once the ledger has new rows, republish the derived data (like every other `npm run
data:*` script in this repo, `npm run data:lead-times` shells out to bare `python3` —
have the project venv active on `PATH` first, or it fails the same way the one-liner
above does without it):

```bash
npm run data:lead-times     # receipts.csv -> data/internal/receiving/supplier_lead_times.json
npm run normalize:data      # picks up the new lead-time ledger (see below)
```

`npm run data:lead-times` runs `scripts/export_supplier_lead_times.py`, which reads
every receipt and writes the measured per-supplier lead times and the
barcode → supplier map that `normalize-datasets.mjs` consumes.

### `npm run normalize:data` refuses to run against an absent silver Parquet

If `data/internal/silver_pos/` is **absent** — which is its state on a fresh clone,
because it is git-ignored — falling through to the 30-product demo connector would
overwrite the committed `src/data/demoProducts.js` (7,451 real products, 141,572
lines) and five other committed generated files with demo data. This was a
pre-existing hazard in the pipeline, not something this ledger introduced, but the
ledger workflow is what turns `npm run normalize:data` into a routine step, so it now
guards against it directly: the script counts the products already committed in
`src/data/demoProducts.js`, and if that count is above a small threshold (300 — well
past any hand-authored demo set, well under the real dataset) and the silver Parquet
is missing, it **refuses to run and exits non-zero** instead of silently overwriting
anything. The message it prints explains what would have happened and how to proceed:
import the real POS data first (see the root `CLAUDE.md` Python pipeline commands) so
`data/internal/silver_pos/` is populated, then re-run. For the rare case where the
demo dataset is genuinely wanted with no real POS data present, pass
`--allow-demo-fallback` to opt in explicitly: `npm run normalize:data --
--allow-demo-fallback`.

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
stable grouping key, not a uniqueness constraint on the ledger. Do not deduplicate on
it, and do not add a uniqueness check without re-reading the docstring in
`src/internal/receiving.py` first. Re-import protection does not use it: that is a
whole-row comparison (`_row_identity`), precisely so those two real deliveries both
survive an import.

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

`leadTimeSource` is carried through `productAdapter.js` onto every normalized product
and is read where it matters: the reorder reason text (`reorderEngine.js`) and the
on-screen explanation (`mockAI.js`) each phrase it in their own words, but both convey
the same thing while it is `'default'` — that the lead time is an assumed figure, that
not enough deliveries have been recorded to measure the real one, and that the number
is the system default rather than an observed measurement — and both drop the
qualifier once it is `'measured'`. That
matters most in the state just after the first supplier crosses three dates: the
resolver then returns that supplier's **real name** with the fallback lead time for
its *other* barcodes, and a sentence naming a real supplier alongside a number reads
as a measurement of that supplier unless it says otherwise.

### What the number actually measures — read this before trusting it

`supplier_lead_times()` returns the **median gap between consecutive delivery dates**:
how often this supplier turns up. It is *not* order-to-arrival time — nothing in the
ledger records when an order was placed, so responsiveness cannot be measured from it.
A supplier who calls every Monday and delivers next-day yields `median_days: 7`, not 1.

`reorderEngine.js` then consumes `leadTimeDays` as the horizon to cover: it multiplies
it by daily sales to size an order, and treats `daysUntilStockout <= leadTimeDays` as
stockout risk. **That is an assumption, not a measurement**, and it is deliberate:
YomYom does not place orders on demand, it is a periodic-review shop that gets what it
gets when the supplier's van comes. For a shop like that the interval you must survive
on is the gap between vans, so the delivery cadence is the right horizon — but if the
shop starts placing on-demand orders, or a supplier delivers weekly while accepting
next-day calls, this number will overstate what has to be covered.

The field is **not renamed** despite the mismatch: too many consumers read
`leadTimeDays`, and a rename would spread the confusion rather than fix it. The
assumption is documented here and at `scripts/normalize-datasets.mjs` instead.

## Checking the ledger against the shelves

`src/internal/restock_reconcile.py` compares deliveries recorded here against the
restocks `src/snapshots/velocity.py` infers from a stock rise between two POS
snapshots — the only independent check either source has.

```bash
npm run check:restocks             # scripts/reconcile_restocks.py
npm run check:restocks -- --json   # the raw per-barcode report
```

It reads and prints; it writes nothing and nothing downstream consumes it. Output is
grouped worst-first: `no_receipts` (stock rose, nothing recorded) and
`under_recorded` are the ones that cost something; `unobserved` usually means the
goods sold through before the next snapshot rather than that anything is wrong.
Barcodes with no movement on either side are counted, not listed — with one delivery
in the ledger there are ~7,300 of them, and calling those "agreements" would be a wall
of meaningless success. With no receipts or fewer than two comparable snapshots it
says so and exits 0: that is the normal pre-pilot state, not a failure.

Like `npm run data:lead-times`, it shells out to bare `python3` and needs the project
venv on `PATH` (it imports `pyarrow` transitively through the snapshot reader).

## Backing up the ledger

`data/internal/receiving/` is **entirely git-ignored** — see the comment block at the
end of `.gitignore`. This was a deliberate decision, made for two different files for
two different reasons:

- `supplier_lead_times.json` is a regenerable build artifact. Lose it and
  `npm run data:lead-times` reproduces it byte-for-byte from `receipts.csv`. No
  backup needed.
- `receipts.csv` is **irreplaceable** — there is no upstream system to regenerate it
  from — but it was still kept out of git, unlike the B-6 snapshot exception
  (`docs/operations/snapshot-durability.md`). The reason is what it contains: the client's real
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
