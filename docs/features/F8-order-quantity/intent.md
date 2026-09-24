---
ID: F8-INTENT
Title: F8 — Order Quantity
Status: Approved — for specification, by the repository owner on 2026-09-25
Owner: smartshelf-pm
Release: V2
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-004
Specs: none
Inputs: [docs/product/intent-register.md (D-18 … D-20), docs/product/open-decisions/F8-ordering.md, docs/features/gaps-and-open-questions.md (GAP-008)]
Updated: 2026-09-25
---

# F8 — ماذا أطلب اليوم وبأي كمية؟ · Order Quantity

> **Status: approved for specification.** The three product decisions named below were
> taken on 2026-09-24, by the repository owner, as
> [D-18 … D-20](../../product/intent-register.md#3-decisions-already-made-by-the-intent-layer),
> and on 2026-09-25 he asked for this feature's spec — the act this status was waiting for.
> What the decisions leave open for design is recorded under GAP-008, and the dependencies
> under *Related* stand. Content moved verbatim from the pre-migration `intent.md` (§6),
> except the dated note under *Blocking product decisions*.

## Problem

«ماذا أطلب اليوم وبأي كمية؟» — أكبر قيمة في المنتج كله.

## User

مالك المتجر.

## Solution (direction only — an ordering of inputs, not yet a rule)

**تصحيح جوهري لما كان مكتوباً.** النية 4 كانت تقول إن الطلب يأتي من ملفات مبيعاته. **الترتيب الصحيح معكوس:**

```
١. حركة السوق ومنافسيه في نطاق جغرافي محدَّد   ←  ما الذي يتحرك أصلاً؟
٢. تُقارَن بحركة متجره هو                        ←  وأين موقعه منه؟
٣. تُقيَّد بالصلاحية (النية 7)                    ←  وكم يحتمل قبل التلف؟
```

مبيعاته وحدها تقول ما باعه **مما كان على الرف**؛ لا تقول ما كان يمكن أن يبيعه. حركة السوق هي التي تكشف الفرصة، ومبيعاته هي التي تكشف موقعه منها.

**والنية 5 هي الوجه الآخر لنفس المؤشر.** الـ527 صنفاً الموسومة `WATCH_PRODUCT` اليوم بلا قرار — نصّها *"حضور قوي عند المنافس، ودليل الطلب الداخلي ضعيف"*، وهذه ملاحظة لا إجراء. تصير جملة صريحة:

> **"هذا الصنف يبيع كثيراً في السوق حولك، وعندك ضعيف. نفكّر معاً: مكانه على الرف؟ سعره؟ أم أن سوقه هنا فعلاً ضعيف ونتركه؟"**

الصدق هنا هو الميزة: لا ندّعي أننا نعرف السبب، ندّعي أننا نراه ونريد أن نفهمه معه.

## Blocking product decisions

- كيف تتركّب حركة السوق وحركة متجره في كمية واحدة.
- ما النطاق الجغرافي الذي يعرّف «السوق».
- ماذا يحدث حين تتعارض حركة السوق مع حركته.

Tracked as **GAP-008** in [gaps and open questions](../gaps-and-open-questions.md).

> **Added 2026-09-24 (not part of the migrated content).** All three are decided, by the
> repository owner:
> - the market is the nearby stores of a format comparable to his, three today (D-18);
> - his own sales set the quantity, and the market only adjusts it (D-19);
> - a disagreement is asked on screen, saved, and not asked again (D-20).
>
> The 527 above no longer describes anything. The last artefact carrying `WATCH_PRODUCT`
> was generated on 2026-09-12. Its recommender stopped running on 2026-09-13 and was
> deleted on 2026-09-24 (GAP-008a).

## Related

- Depends on F10 (expiry bound) and on the sales-evidence work in F4.
- Sibling of F9 — both are read off the same market-movement signal.
