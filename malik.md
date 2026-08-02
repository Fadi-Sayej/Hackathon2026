# Malik — Track D: In-Store Workflows & Customer Handover

> 📋 **Read `PLAN.md` first** — phases, integration gates, go/no-go criteria, and the cut line.
> This file is only your slice of it. **You also own the manual QA pass before every gate:
> every screen at 390px, on a real phone, in Hebrew.**

> **You own (nobody else edits):** `src/pages/`, `src/components/`, `docs/`, `DEMO_SCRIPT.md`,
> customer-facing training material
> **Never touch:** `src/App.jsx` or `src/lib/` (Anas), `scripts/*.py` (Fadi),
> `src/api/` (Nagham)

Read first: `CLAUDE.md`, `README.md` (§Expiry Tracking at Receiving), `src/pages/OperationalPage.jsx`,
`src/pages/ExpiryPage.jsx`, `public/data/operational.json`

---

## What we are handing YomYom

A deployed web app a store manager opens each morning that says **what to act on today**, computed
from their own real data. The pilot measures whether acting on those alerts makes money.

## Your mission

You own the part that decides whether this pilot succeeds or quietly dies: **whether a real person
in a real shop actually uses it.** The other three are making the data true, reachable, and
readable. You make it *worth opening tomorrow morning*.

The most important thing to internalise: **YomYom staff will never run a Python script.** Today,
recording an expiry date requires `python scripts/record_expiry_scan.py --barcode ... --expiry-date ...`
from a terminal. That is not a product. It is your job to turn workflows like that into screens.

---

### D-0 (P0 — DAY 1, DO THIS BEFORE ANY CODE) — Get two answers from YomYom

**You own this.** Fadi's velocity engine is designed to work without these answers, but its
accuracy depends on them, and the sooner they land the less rework everyone does.

Send the manager **one** message containing both asks. Two small requests in one note — don't spend
two separate favours:

1. **"Can your POS export sales or transactions, not just current inventory?"**
   Ask for a sample of *any* sales report the system can produce, even a rough one. Today we only
   have an inventory snapshot, so we cannot see what actually sold — this is the single biggest
   limitation in the product.

2. **"Can you send us the stock export once a day, every morning?"**
   Today it arrives irregularly. Frame it as **30 seconds a morning**, and offer to automate it
   (scheduled export, shared folder, WhatsApp) rather than asking them for discipline. Explain the
   benefit in their terms: *the more often you send it, the more accurate the recommendations get.*

**Done when:** both answers are written into `PLAN.md` §7 (replace the 🔴 Blocking block with the
real answers and the date received), and **Fadi is told directly** — they are the consumer.

If the answer to #2 is "no, only weekly", say so immediately and loudly. It does not stop the pilot,
but Fadi must widen the confidence bands and we must lower what we promise the customer.

### D-0b (P0 — DAY 1) — Co-sign the UI data contract

Anas is drafting `docs/UI_DATA_CONTRACT.md` — the exact prop shape `App.jsx` passes into your
pages. **Review and agree it before you write a single component.** This is the only real coupling
between your work and Anas's, and it is where the two of you will collide if you skip it.

You are the consumer: if a field you need for a screen isn't in the contract, say so **now**, not
after C has built the chain.

### D-1 (P0) — The daily action list

`public/data/operational.json` already holds **2,183 real recommendations** generated from YomYom's
own data: 1,147 Wolt price gaps, 625 negative-stock issues, 307 unknown barcodes, 104 margin risks.
This is the strongest, most defensible thing we have. Right now it renders as an undifferentiated
list.

Turn `OperationalPage` into the app's home screen:

- **Today's actions, ranked by ₪ at stake** — not by category, not alphabetically. A manager has ten
  minutes; the top of the list must be the most valuable thing they can do.
- Each item: what's wrong, what to do, what it's worth, and **Done / Dismiss / Snooze** buttons.
- Dismissal must capture *why* (wrong data / not worth it / already handled). **That feedback is the
  most valuable output of the entire pilot** — it tells us which recommendation types to keep.
- 2,183 items is overwhelming. Show the top ~20 by value, with the rest behind a filter.
- Wire the buttons through Nagham's persistence layer so decisions survive and are measurable.

### D-2 (P0) — In-app expiry capture

Expiry is the one thing the POS genuinely cannot tell us, and it is where a convenience store
actually loses money. The pipeline (`record_expiry_scan.py` → `build_expiry_report.py`) works — it
just has no human interface.

- A phone-friendly screen: enter/scan a barcode, pick an expiry date, save.
- Use the device camera for barcode scanning if you can get it working quickly; a numeric keypad
  fallback is acceptable and must exist regardless.
- After a barcode is entered, show the product name from the POS data immediately so staff can
  confirm they scanned the right thing.
- Expiry alerts then feed the daily action list: "3 units expiring in 2 days — discount or pull."
- Coordinate with Nagham — this writes to the backend, not a CSV on someone's laptop.

### D-3 (P1) — The price-gap screen

14,406 real barcode matches against Dor Alon, Rami Levy, Shufersal and Wolt is our most compelling
evidence. Build the screen that shows a manager, in their own language: *"You sell this at ₪8.00,
Shufersal sells it at ₪6.90, you're ₪1.10 above on a product you hold 40 units of."*

Sort by units held × gap — the products where being mispriced costs the most. Include the **60
products currently selling below cost**; that is money leaving the till on every scan, and it is
the finding most likely to make YomYom trust the tool.

⚠️ Flag the data's age honestly. The Kaggle competitor prices are from 2024 (Fadi is refreshing
them). **Never present a stale price as today's price** — one wrong claim about a competitor and we
lose the customer's confidence permanently.

### D-4 (P1) — Daily summary the manager can keep

A one-page, printable/shareable summary: today's actions, what was done yesterday, ₪ saved so far.
`@media print` rules already exist in `App.css`. Many small-shop owners want paper or a WhatsApp
screenshot, not a login.

### D-5 (P0) — Handover package

We are handing this to a real business. Written in **Hebrew or Arabic**, not English:

1. **One-page quick start** — how to open it, what the daily 10 minutes looks like.
2. **The morning routine** — exporting the POS CSV and where it goes. Get the exact steps from
   Fadi; without a daily export, velocity never accrues and the product degrades over the pilot.
3. **A one-page "what this is / what it isn't"** — state plainly that competitor prices are
   reference data, that early recommendations have limited sales history, and what the tool does
   *not* do. Setting expectations honestly at handover is what buys us a second meeting.
4. **A feedback channel** — one WhatsApp number or form. Make it trivially easy to tell us something
   is wrong.

### D-6 (P0) — Remove the planogram from the pilot

✅ **Decided: hide it.** Measured against real data, the planogram assigns **all 7,451 products to
the BOTTOM shelf with exactly 2 facings each** — zero products at eye level, top score 0.07/1.0.
It also depends on `shelfCapacity`, which is hardcoded to `10` for every product because no data
source we have contains real shelf dimensions.

- Remove `planogram` from the navigation in `AppShell`.
- Leave `PlanogramPage.jsx` in the repo — this is a hide, not a delete. It comes back once velocity
  exists, the categories are remapped to Hebrew, and someone has measured YomYom's actual shelves.
- Say nothing about it in the handover docs. Do not describe it as "coming soon" unless the team
  has genuinely committed to the shelf survey.

**Do not let a store manager make a shelving decision from numbers we invented.** This is the
clearest example of the honesty bar in `PLAN.md` §4.

---

## Contract with the rest of the team

- **Anas owns `App.jsx` and all the engines; you own the pages and components.** C computes and
  passes data down, you render it. **Agree the prop shape with C before either of you starts** —
  this is the most likely place for the two of you to collide.
- Persistence and telemetry come from Nagham. Don't invent your own storage.
- The 2,183 recommendations in `operational.json` come from Fadi's pipeline. If you need a new
  field, ask — don't compute it in the component.

## Done when

- A person who has never seen the app can open it on a phone and know what to do first.
- Recording an expiry date takes under 15 seconds and no terminal.
- Every action a manager takes is captured, so Nagham can report acceptance rates at pilot's end.
- The handover doc is in the customer's language and a non-technical reader can follow it.
