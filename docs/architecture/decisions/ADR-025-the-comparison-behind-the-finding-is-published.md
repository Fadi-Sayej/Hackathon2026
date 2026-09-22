---
ID: ADR-025
Title: The comparison behind a competitor finding is published, not only the finding
Status: Ready for review
Owner: smartshelf-architect
Date: 2026-09-22
Parent: [System Design](../system-design.md) §7.3
Related Specs: F1-S1, F3-S1
Inputs: [ADR-001, ADR-005, ADR-020, ADR-024, public/data/dashboard.json (2026-09-22), src/engine/competitor_position.py, docs/features/F3-competitor-price-position/specs/, CLAUDE.md rules 8, 11]
Updated: 2026-09-22
---

# ADR-025 — The comparison behind a competitor finding is published

**Status:** Ready for review · a role may not approve its own output (HANDOVER rule 2)

## Context

`competitor_position` matched **2,619** products against 164 shops in the 2026-09-22 run and
published **6** entries. The funnel, read from the artefact:

```
catalogue               7523
comparable_population   6801
matched                 2619     at least one fresh observation
  no_reference          1684     no comparable price after the affinity floor
  no_cost                 40     FR-043d: no judgement without a cost
  no_shelf_price          39     our own row has no price to compare
evaluated                856
entries                    6
```

So **850 products were compared against a live reference and found acceptably priced**, and
that comparison was computed and dropped at the publish boundary.

The artefact publishes findings, and that is correct — ADR-001. But `PriceGapPage` asks a
different question: *what is this product's position?* It needs the comparison, not the
finding, which is why it sits on an awaiting state while the engine computes the answer
nightly and discards it.

An earlier framing of this said "2,612 comparisons never leave the process". That was wrong
and the correction matters: 1,758 of the 2,619 never produced a comparison at all, and the
**store-level** rollup (`position`, 164 stores) already ships. The real gap is the per-product
comparison, and it is smaller and better-shaped than the first number suggested.

## Decision

**`capabilities.competitor_position.comparison` — one row per MATCHED product, carrying
either the comparison or the reason there is none.**

```json
{"barcode": "16000194304", "shelf_price": 18.9, "stores": 1, "observed_at": "2026-09-22",
 "reference": {"value": 21.9, "kind": "same_format_only", …},
 "premium_pct": -13.7, "uncompared_reason": null}
```

### Every matched product, not only the evaluated ones

Publishing only the 856 evaluated would make the page say **nothing** for a product skipped
as stale or lacking a reference — and to the owner, a blank is indistinguishable from *"no
competitor sells this"*. That is rule 8 and D-3 one layer out: when a figure cannot be
stated, say why, do not fall silent.

Measured, the two options differ by **about 1 KB gzipped**. The cost argument for the
narrower set does not exist.

### Inside the artefact, not beside it

ADR-024 put the catalogue in its own file because it is **182 KB gzipped** and the daily
surface — which needs no catalogue — would have paid it on every load. That argument is
size-shaped, and at this size it points the other way:

| | gzipped | growth on the artefact |
|---|---|---|
| catalogue (ADR-024, beside) | 182 KB | +74 % |
| this comparison (inside) | **31 KB** | **+13 %** |

Inside means one file, one `inputs_digest`, and no way for the findings and the comparison
behind them to drift apart. A second file would have to carry the digest and be checked
against it, which is machinery this does not need.

### No `product_name`, no `department`

`catalogue.json` carries both against the same barcode (ADR-024), and any page rendering this
needs that file anyway. Carrying them here measured **+39 KB gzipped** — more than the whole
block costs without them — for a second copy of the truth, which is what §20.1 deleted
`src/data/*.js` for. The join is by barcode.

### Sorted by barcode

The nightly commits the artefact, so the bytes must repeat when the data does. Same reasoning
as ADR-024's catalogue and ADR-021's `last_seen_at`.

### `no_cost` publishes the position anyway

FR-043d withholds the **judgement** without a cost price, not the comparison. The reference is
known; only the policy verdict would be unsafe. So the row carries `reference` and
`premium_pct` with `uncompared_reason: "no_cost"` — the owner sees where he stands, and the
system does not claim he is in breach.

## What this does not do

**It does not change any finding.** `entries`, `counts` and `position` are untouched, and a
test asserts the published `premium_pct` equals the one in the entry's own evidence — so the
page and the daily surface cannot disagree about a product.

**It does not light `PriceGapPage`.** That page also imports `DATA_FRESHNESS` from
`src/data/marketData.js` — 553 KB frozen at 2026-08-09 — and renders `priceCount: 2767` and
`medianPriceAgeDays: 124` as headline figures, and it computes below-cost itself, getting 63
where the engine says 34. Those are conditions on routing it, not on this ADR.

## A gap this exposed and does not close

**`capabilities` has no schema.** `schemas/dashboard.schema.json` declares no properties for a
capability and sets no `additionalProperties`, so `entries`, `counts`, `position` and now
`comparison` are all unvalidated. ADR-005's promise that *"the publisher refuses an artefact
that breaches the schema"* is therefore much weaker than it reads, over the largest part of
the file. Declaring one new property in isolation would imply a validation that its siblings
do not have, so the guarantee here is in tests instead. **Reported for `smartshelf-architect`.**

## Rejected options

### A second file, like the catalogue
Rejected on the measurement above: 31 KB against the catalogue's 182 KB, and a second file
needs its own digest-matching machinery to prove it belongs to the same run.

### Evaluated products only
Cheaper by 1 KB gzipped and it makes the page silently incomplete. Rejected.

### Leave it and let the page compute from `position`
`position` is a per-store rollup; it cannot answer a per-product question. Any page doing that
arithmetic would be recomputing a figure the engine already has, which FR-138 forbids.

## Consequences

**We accept:** +13 % on the artefact the owner's phone fetches, and one more block the engine
must keep honest.

**We gain:** the 850 comparisons already being computed become visible, and a page that asks
"where do I stand on this product" has an answer that is not a finding.

**We will know it was wrong if:** the block grows past the point where the daily surface — which
does not read it — should be paying for it. The catalogue's threshold was 182 KB; if this
approaches that, it moves beside the artefact and ADR-024's reasoning applies unchanged.
