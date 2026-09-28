---
ID: F9-DECISIONS
Title: F9 Assortment Gap — the two decisions that must be taken before a spec exists
Status: Superseded
Owner: smartshelf-pm
Parent: [SPEC-GAPS · GAP-013](../../features/gaps-and-open-questions.md)
Supersedes: —
Superseded-by: [intent register §3, D-25](../intent-register.md) — decided by the repository owner 2026-09-28
Related Intents: INT-005, INT-004
Inputs: [docs/features/F9-assortment-gap/intent.md, docs/features/F8-order-quantity/specs/F8-S1-order-quantity.md, docs/product/intent-register.md (D-1, D-3, D-8, D-9, D-18, D-19, D-20, D-23), configs/store_types.yaml, public/data/catalogue.json, public/data/dashboard.json, data/internal/silver_pos/sales_summary.parquet, data/external/snapshots/ (delivery_catalog, 2026-08-13 … 2026-09-28)]
Updated: 2026-09-28
---

# F9 — the two decisions

> **Decided 2026-09-28, by the repository owner** ("1b 2a"). Recorded as **D-25** in the
> [intent register §3](../intent-register.md), which is the authority. This brief is kept as
> the record of how it was reached.
>
> | Decision | Answer |
> |---|---|
> | 1 — which of the products he does not stock is a finding | **B, what the market ran out of**: at a market store on at least one recent night, by ADR-031's rule. 132 over the 45 nights held on 2026-09-28 |
> | 2 — what he does with one | **A, an entry on the daily surface**: a place among his ten (D-9), where he records "I'll try it" or "Not for my store". No ₪ figure |
>
> Left to the spec, as this brief said: how many nights count as recent; which of his
> catalogued but idle products count as not stocked; where the entry ranks among the ten.
> Under D-23 no one can record an answer until a new store's owner signs in.

F9's intent asks «ماذا يبيع السوق ولا أبيعه أنا؟» and stops at one blocking decision: what the
owner is expected to *do* with a finding. This document turns that into questions the
repository owner can answer in one sitting, with the options the data supports.

**It answers nothing.** Every figure is cited to where it was read (CLAUDE.md rule 11). F9
stays `Registered — not specified` until a human takes these. When they are taken they are
recorded as the next free D-n in the [intent register §3](../intent-register.md), which is the
authority, and this file is set `Superseded` and kept as the record.

**Everything here runs on data already held (D-23).** The competitor snapshots the nightly
keeps adding, his catalogue and his seven monthly reports. Nothing needs a store to send
anything, and nothing is simulated.

---

## What is already settled: F9 is about products he does not stock

The intent's example sentence is about a product *he sells* weakly while the market sells it
strongly. That case is no longer F9's. F8-S1 (approved 2026-09-25) owns it:

- When the market runs out of a product he stocks, D-19 raises its order.
- When he stocks it but it is not moving, F8-S1 FR-158 asks him about it, once (D-20).
- F8-S1 §3 hands the rest over by name: *"Products he does not stock: whether to carry them is
  F9's question (INT-005)."*

So F9 looks only at what the market lists and he does not stock. Asking about the other
products from a second screen would decide one fact twice.

## What the data can honestly say

Measured on 2026-09-28 with the engine's own code: `load_presence(source_id="delivery_catalog")`,
`market_store_ids` (D-18's market) and ADR-031's `running_out`, replayed for every night. The
replay gives 79 products for 2026-09-28, which is what `dashboard.json` published that night.

The window is 45 usable days, 2026-08-13 … 2026-09-28; four days were skipped as unusable.

| | Products |
|---|---|
| Listed by the market (D-18) on 2026-09-28: Wolt Market 667, Rami Levy In The Neighborhood 488, Super Alonit Einat 378 | **1,427** |
| … in his catalogue (`catalogue.json`: 7,523 products, 7,275 with a barcode) | 432 |
| … **not in his catalogue** | **995** |
| … of those, listed at one market store / two / all three | 960 / 35 / 0 |
| … of those, **the market ran out of on at least one of the 45 nights** | **132** |
| … of those, at two stores and ran out | 6 |

Three things follow, and each limits what F9 may put on a screen.

1. **We never see what a competitor sells.** Only what it lists, and when it drops an item.
   F9 therefore cannot say "sells a lot" (D-1, rule 11).
2. **How many stores list it says little.** The three stores barely overlap: none of the 995
   is listed at all three.
3. **The one sign of demand is the market running out.** It is ADR-031's rule, the one F8
   already uses. "Wolt Market ran out of it on 4 of the last 45 nights" is a sentence the
   data carries.

Two limits on the counts:
- **Matched by barcode, as the engine matches.** Another size of a product he sells shows as
  "not in his catalogue". The market's "5 × Bissli BBQ 55 g" is one: his catalogue has Bissli
  BBQ in other sizes, under other barcodes. The 995 is therefore an upper bound. Pack-size
  matching is OQ-303, still open.
- **"Not in his catalogue" is not quite "does not stock".** F8's rule for "stocks" reads the
  daily reports, which have not arrived (D-23). Which of his catalogued but idle products
  also count is a design point for the spec, after these decisions.

Six of the 132, listed at two stores (read from the snapshots): בירה נשר מאלט 1.5 ל׳ ·
ביסלי ברביקיו 5×55 ג׳ (the multipack above) · עגבניות חתוכות בלה איטליה 3×400 ג׳ · פלפל שיפקה חריף סימפוניה ·
רביולי בטטה שטראוס · לחם לבן שמן זית סמנצאטו.

---

## Decision 1 — Which of the products he does not stock is a finding?

**The question:** «أيّ صنف لا تبيعه يستحق أن نلفت نظرك إليه؟»

| Option | What counts | How many today | What it costs |
|---|---|---|---|
| **A — Everything the market lists** | Listed by any market store | 995 | A list nobody reads to the end, and most of it has no sign of demand at all |
| **B — What the market ran out of** | Ran out at a market store on at least one recent night (ADR-031) | 132 over the 45 nights held | Every finding carries evidence of demand. It is F8's rule, so the two features cannot disagree about what "running out" means. How many nights count as recent is the spec's to set |
| **C — What two stores list** | Listed at two or more market stores | 35 | Breadth is weak evidence here (above): 960 of the 995 are at one store only |

## Decision 2 — What does the owner do with a finding?

This is the intent's blocking decision. The intent itself phrases a finding as the start of a
conversation: *"نفكّر معاً: مكانه على الرف؟ سعره؟ أم أن سوقه هنا فعلاً ضعيف ونتركه؟"*

**The question:** «حين نجد صنفاً يبيعه السوق حولك ولا تبيعه — ماذا تفعل به؟»

| Option | What he sees | What it costs |
|---|---|---|
| **A — An entry on the daily surface** | A card among his ten (D-9), where he records "I'll try it" or "Not for my store" | It competes for the ten places with no ₪ figure: he has no sales of the product to size it with (D-1, D-3). A new outcome type in owner state |
| **B — A question** | Put like F8's disagreements, at most three at a time (D-8): "Wolt Market ran out of it on 4 of the last 45 nights. Would it sell here?" His answer is saved and never asked again (as D-20) | It shares the three question places with F8's questions and the cost questions. A new answer type in owner state |
| **C — A list to read** | A page with the findings and their evidence, for him and the team to talk over. Nothing is recorded | F13 cannot count what came of it. Needs a page only |

**What D-23 changes for all three.** There is no store owner today, and the team's accounts are
read-only (D-22). A and B would show their buttons, but nobody could press them until a new
store's owner signs in. C works as fully today as it ever will.

---

## When these are taken

Recorded as the next free D-n (D-25 today) in the intent register §3, and this file becomes
`Superseded`. GAP-013 is struck through. F9's intent gets a dated note; its status stays
`Registered — not specified` until the repository owner asks for the spec (HANDOVER rule 2).
