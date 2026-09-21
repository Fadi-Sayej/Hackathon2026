---
ID: F2-VALIDATION
Title: F2 — Stock Reconciliation and Data Hygiene · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F2-S1](../features/F2-stock-truth/specs/F2-S1-stock-reconciliation-and-hygiene.md)
Inputs: [docs/features/F2-stock-truth/specs/F2-S1-stock-reconciliation-and-hygiene.md, docs/features/F2-stock-truth/intent.md, docs/operations/deployment.md, public/data/dashboard.json, src/engine/reconciliation.py, src/surface/compose.js]
Updated: 2026-09-16
---

# Validation F2 — Stock Reconciliation and Data Hygiene

Deployed URL: `https://hackathon2026-fadi19.vercel.app` (gate returns 401, verified 2026-09-16)
Commit: `8f2646a`
Artefact read: `public/data/dashboard.json` at `origin/main`, `generated_at 2026-09-15T03:02:35Z`

## Verdict

**Conformance passes on all ten acceptance criteria.** Fidelity passes — this is the one
feature whose intent was rewritten *because* the first answer was wrong, and the code
honours the correction. **Usefulness is where it is weakest, and there are two findings,
one of which puts a wrong number in front of the owner today.**

---

## Pass one — conformance

| id | Criterion | Verdict | Evidence |
|---|---|---|---|
| AC-020 | negative implied opening flagged, others not, no-receipts never flagged, ordered by gap ratio desc | **met** | Artefact: 439 entries, `ordering_key.name` is `gap_ratio` for all, values descending 9.5 → 0.0033; **0** flagged with `receipts` absent or zero; **439 of 439** carry `unaccounted > 0` |
| AC-021 | no flagged product carries money | **met** | **0 of 439** entries have a `value` |
| AC-022 | no aggregate in currency | **met** | `counts` = `{flagged: 439}`; figure units across F2 are only `products` and `records` — no currency unit anywhere |
| AC-023 | size of the loss stated as not determinable, no figure offered | **met** | `src/engine/reconciliation.py` — every `Entry` is constructed `value=None` (lines 48, 70, 98); no bound, no illustration |
| AC-024 | every flagged product shows the three quantities and the unaccounted | **met** | Entry `evidence` keys: `recorded_stock`, `receipts`, `units_sold`, `unaccounted`, plus `window_id`, `reconcile_months` |
| AC-025 | no hygiene record carries money | **met** | **0 of 1,117** hygiene entries have a `value` |
| AC-026 | no surface sums a recurring and a standing figure | **met** | `src/surface/compose.js:70` — kinds ordered as contiguous runs, never interleaved (D-2 / AC-103) |
| AC-027 | no output states or implies a cause | **met** | One signal family, `recon.impossible_opening`; one characterisation, `inconsistent`; the owner reads *"Numbers that do not add up"* and *"Received and sold do not balance"*. No wording names theft, breakage or entry error |
| AC-028 | recomputation reproduces the flagged set and its ordering | **met** | Two consecutive `run_engine(mode="print")` runs: same 355 ids, same gap-ratio ordering, entries **byte-identical** under `json.dumps(sort_keys=True)` |
| AC-029 | a decision survives the product ceasing to be flagged | **met** | `src/owner/ownerState.js` keys `outcomes` by `entry.id` in a map independent of the artefact; ADR-009 makes that id stable across runs |

### §19 traceability

Both intents are traced. `INT-002` → AC-020, AC-021, AC-023, AC-024, AC-027, AC-028.
`INT-002B` → AC-025. No `INT-` row is left without an `AC-`.

### Scope drift

None found. `src/engine/reconciliation.py`, `src/engine/hygiene` families and
`compose.js`'s allocation are all named in the plan's Phase 1 tasks and in spec §3.

### Shipped but never requested

Nothing. The 12th hygiene family (`conflicting_duplicate`) traces to ADR-019 and, since
2026-09-15, ADR-022.

---

## Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F2-stock-truth/intent.md`.*

**PROBLEM — is the owner measurably less stuck?** Partly, and honestly so. He can see 439
products whose arithmetic cannot close, ordered worst-first, each showing the three
quantities he would check. He cannot see *how much* it cost him, and the intent says that
is correct.

**Is the SUCCESS line countable?** The intent sets no numeric success line — deliberately.
Its claim is negative: *no money on a quantity-derived signal*. That is countable, and it
counts **zero**: no entry, aggregate or figure in either capability carries currency.

**Would the owner recognise this as built for them?** Yes. Hebrew product names, his
departments, his own recorded stock, and page names in his language — *"Stock that does not
add up"*, *"Received and sold do not balance"*. Not `reconciliation`.

**Did anything in NOT NOW get built anyway?** No. The three exclusions hold: no correct
quantity is proposed, no cause is apportioned, and nothing writes to the POS.

**Would you write the same intent again?** Yes, and it is the strongest intent in the
project. It was rewritten *because* the first answer was wrong — ₪63,572 split into
"coherent" and "estimated" — and the rewrite names the exact rows that exposed it
(`בקבוק נביעות 1.5 ליטר`: 1,533 recorded, 4,274 "missing"). The governing sentence is the
one the rest of the repository keeps rediscovering: **a positive number is not a
trustworthy number; it is only a non-negative one.**

---

## Pass three — usefulness

**Contribution to the daily surface: 3 of 10 places.** Computed by running
`compose(artefact, {outcomes:{},answers:{}})` over the committed artefact: the surface is
`{price_consistency: 7, reconciliation: 3}`.

**Turn the signal off.** `npm run check:signals`, 2026-09-16: withholding the sales
reports takes `reconciliation` to `unavailable (no_sales_evidence)` while `hygiene` still
emits 1,117 records — the ADR-014 independence probe, passing. **The feature moves
something**, which is more than four signals in this project's history managed.

**Rule 8.** Honoured in full. Zero money on either half, and no zero substituted for an
absent number.

**Rule 13.** Honoured. The window is month-grained (`window_id: 2026-01..2026-07`,
`reconcile_months`), and nothing claims a resolution the seven monthly reports cannot carry.

---

## Findings

### F2-V1 — the published flagged count is inflated by 24%, and the cause is a vintage bug. **smartshelf-engineer.**

The artefact says **439**. The honest count is **355**.

`reconciliation`'s window depends on the POS vintage, and the vintage on `main` is wrong:
the 09-14 and 09-15 nightlies both published `pos.as_of: 2026-09-14` while
`yomyom-inventory.csv` has not changed since 2026-06-06. `git log -1 -- <file>` in
`actions/checkout`'s default one-commit clone attributes the file to the checkout commit.

Proved rather than inferred, on 2026-09-16:

```
import with the sidecar (2026-06-06)   → reconciliation flagged 355
import forced to 2026-09-14            → reconciliation flagged 439   ← matches the artefact
```

So 84 of the 439 products on that page are flagged because the system believes the stock
count is three months newer than it is. Fix is open as **PR #109**; this validation is the
first evidence that the bug changes a number the owner reads, not only a provenance field.

*It does not change the daily surface.* `reconciliation` is first in `unvalued_order` and
takes all three reserved places either way.

### F2-V2 — INT-002B reaches the daily surface never, by construction. **smartshelf-architect.**

`hygiene` publishes **1,117** records and contributes **0** places to the screen the owner
opens each morning.

Not a defect — it is the configured policy — but the policy's consequence is not recorded
anywhere. `thresholds.surface` reserves `unvalued_places: 3` and orders them
`["reconciliation", "competitor_position", "catalogue_lifecycle", "hygiene"]`. Hygiene is
**last of four competing for three places**, behind a capability that currently has 439
entries. It can only surface on a day `reconciliation` yields fewer than three.

The intent treats INT-002 and INT-002B as two halves of one problem. In delivery one half
is a daily prompt and the other is browse-only. That may well be right — *"Records to fix"*
is a task for a quiet afternoon, not a morning decision — but the intent does not say so,
and nobody has decided it out loud.

### F2-V3 — what I did not check

- **The deployed URL's rendered output.** The gate returns 401 and the Basic Auth
  credentials are not available to this session, so every artefact figure here was read
  from `public/data/dashboard.json` at `origin/main` — the file the deployment serves —
  and not from the rendered page.
- **AC-029 end to end.** The mechanism is verified by reading `ownerState.js` and ADR-009.
  It has never been exercised against a product that actually stopped being flagged,
  because no owner outcome exists yet — write-through only landed today (#95).
- **Whether the owner agrees the 439 are worth his time.** That is the usefulness question
  no artefact answers, and it needs him.

### What surprised me

That the count on the owner's screen turned out to be wrong for a reason that lives three
layers away — in how a CI runner clones a repository. Nothing about `reconciliation` is
broken. It read the vintage it was given, and the vintage was a checkout timestamp wearing
a `git_commit` label. The nightly was green, every probe passed, all ten acceptance
criteria hold, and the number is still 24% too high.
