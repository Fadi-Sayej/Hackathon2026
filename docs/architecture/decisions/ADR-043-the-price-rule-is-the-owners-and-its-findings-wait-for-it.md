---
ID: ADR-043
Title: The price rule is the store owner's statement, and the findings it drives wait for it
Status: Accepted
Owner: smartshelf-architect
Date: 2026-10-08
Parent: [System Design](../system-design.md) §19
Related Specs: F3-S1 (FR-045, FR-045a, FR-045b, FR-043a/b)
Updated: 2026-10-08
Inputs: [D-39, D-28, D-23, ADR-009, ADR-014, ADR-033, ADR-036, configs/policy.yaml, configs/store_facts.yaml, src/engine/competitor_position.py, src/engine/registry.py, src/common/store_readiness.py, public/data/dashboard.json (2026-10-08)]
---

# ADR-043 — The price rule is the owner's, and its findings wait for it

**Status:** Accepted (2026-10-08, by the repository owner: "approve", to "Approve the design and
these words? Or tell me what to change.", asked of this decision and the three sentences in §4).

## Context

D-39 (2026-10-08): a new store's copy starts with no price rule. Until its owner states the
most they will charge over nearby stores, the app flags no price as over it. F3 says it is
waiting for the owner's limit, and `npm run check:store` lists the rule as missing. YomYom
keeps its +60%. D-39 leaves the rest of F3 as it is, including the purchase-cost check.

Today the rule cannot do that:
- **Where the rule is kept.** It is `price_policy_pct: 60` in `configs/policy.yaml`. That
  file is code, so every copy carries it. The loader also falls back to 60 when the key is
  absent (`src/engine/policy.py`).
- **One capability does three jobs.** `competitor_position` publishes three things, and only
  one of them uses the rule:
  - the comparison (one row per product, its premium over the reference);
  - the purchase-cost check (FR-043a/b, evaluated before the rule);
  - the policy breaches (FR-045a), in the `competitor.policy_breach` family.

  On 2026-10-08 YomYom's artefact holds 10 breaches (8 to review, 2 urgent) and 6
  purchase-cost findings.
- **What ADR-014 requires.** A capability is the smallest unit that can independently
  become unavailable. Its status is derived from its `requires` and never hand-declared.
  The breaches must now be able to wait while the comparison and the purchase-cost check
  go on, so they must be a capability of their own.

## Decision

1. **The rule is a store fact, kept with the others.** It moves to `configs/store_facts.yaml`,
   which ADR-033 made the place for the owner's statements, as a store-level entry beside
   `departments`:

   ```yaml
   price_rule:
     max_premium_pct: 60
     stated_by: owner
     recorded_by: team
     recorded_on: 2026-09-08
     stated_on: not_recorded
   ```

   - **Validation** works as for a department's facts: rejected and reported, never
     repaired, never defaulted. `max_premium_pct` is a number above 0.
   - **Provenance.** `recorded_on` is required. `stated_on` is the day the owner said it, or
     `not_recorded`.
   - **YomYom's entry** is the owner's own words ("if a product's price is 5, I don't sell it
     for more than 8", F3 intent §3ب). They were first written down on 2026-09-08 (commit
     `9e4160e`). The day they were said is not recorded, and the entry says so rather than
     guess.
   - **policy.yaml** loses `price_policy_pct`, and nothing defaults it.
   - **New copies.** `store_facts.yaml` already starts empty in a new copy (ADR-036 §3), so a
     new copy starts without the rule.

2. **The breaches become their own capability, `policy_breach`** (SPEC-003, F3-S1):
   - **What it is.** Admitted, unvalued, ordered by `premium_pct`, as the breaches are now.
     It requires `products`, `observations`, `matches` and a new input, `price_rule`.
   - **What it publishes:**
     - the `competitor.policy_breach` entries, under the same signal family, so every entry
       id and every recorded outcome stays the same (ADR-009);
     - their thresholds (`policy_pct`, `attention_pct`);
     - their counts (`breaches`, `review`, `attention`).
   - **What stays in `competitor_position`:** the comparison, the purchase-cost findings,
     the cost floor and the rest of its counts.
   - **How they agree.** Both are computed from one pass over the products, so a product the
     cost floor stops is never a breach (FR-043a/b).
   - **Without a stated rule** `policy_breach` is unavailable with the reason `no_price_rule`.
     `competitor_position` is not affected.

3. **Today keeps its order.** `surface.unvalued_order` and `engine_ordered` gain `policy_breach`
   directly after `competitor_position`. The findings page for F3 renders both capabilities'
   entries, as it renders `competitor_position`'s now. For YomYom, every screen must stay as
   it is. That is proved by the screenshot comparison (126 screens, before and after,
   byte-identical) before the screen change merges.

4. **What a store without a rule sees, on F3's findings page in place of the breaches:**

   | | |
   |---|---|
   | English | Your price limit has not been recorded yet: the most you will charge above nearby stores for the same product. |
   | עברית | מגבלת המחיר שלך עדיין לא נרשמה: כמה יותר מהחנויות הסמוכות מותר לגבות על אותו מוצר. |
   | العربية | لم يُسجَّل حدّ السعر الخاص بك بعد: أقصى زيادة على أسعار المتاجر القريبة للمنتج نفسه. |

   It is the `unavailable.no_price_rule` reason, shown wherever an unavailable reason is shown.

5. **Checks:**
   - **`check:store`** gains a row, "The owner's price rule". It feeds `price_rule`, so the row
     names `policy_breach` as what stays unavailable, read from the registry as every row is.
   - **The rule-12 probe** withholds the rule. `policy_breach` must go unavailable
     (`no_price_rule`) while `competitor_position` stays available with its purchase-cost
     findings.

## Rejected options

- **Keep the rule in `policy.yaml`, empty in a new copy, and let all of F3 wait.** This is
  smaller, but the comparison and the purchase-cost check would wait for a rule they do not
  use. D-39 left them as they are.
- **Keep the breaches inside `competitor_position`, with a "rule not stated" marker.** That is
  a hand-declared partial status, which ADR-014 forbids, and an empty breach list would read
  as "no breaches" (CLAUDE.md rules 8 and 10).
- **Put the rule in `configs/store.yaml`.** That file says which store a copy serves, and the
  team fills it. The rule is the owner's statement and needs its provenance, as ADR-033's
  facts have.
- **Put it in `configs/owner_answers.yaml`.** No engine step reads that file.

## Consequences

- **The artefact's shape.** It gains a capability (`published_from` set to its first
  nightly), and `competitor_position` loses its breach entries, counts and two thresholds.
  For YomYom, no figure changes: the same 10 breaches, the same ids, the same order.
- **Screens.** The findings page and the composer read two capabilities where they read one.
  That is a front-end change, so it waits for the repository owner's approval of the words
  above, and then needs the screenshot proof.
- **Still in `policy.yaml`.** GAP-011's `owner_declared_ceiling_pct` is the same kind of owner
  statement, but it is empty at YomYom, so no copy inherits a value. Moving it is not part of
  D-39.

## Reversibility

Moving the rule back to `policy.yaml` and the entries back into `competitor_position` is one
change, and the entry ids never move, because they hash the signal family, not the capability.

## Binds

`src/engine/policy.py`, `src/engine/store_facts.py`, `src/engine/inputs.py`,
`src/engine/competitor_position.py`, `src/engine/registry.py`, `configs/policy.yaml`,
`configs/store_facts.yaml`, `src/common/store_readiness.py`, the rule-12 probe, and the F3
findings page and composer once their change is approved.
