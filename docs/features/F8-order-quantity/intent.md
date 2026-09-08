---
ID: F8-INTENT
Title: F8 — Order Quantity
Status: Registered — not specified
Release: V2
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-004
Specs: none
---

# F8 — ماذا أطلب اليوم وبأي كمية؟ · Order Quantity

> **Status: registered, deliberately NOT specified.** No `F#-S#` document exists for
> this feature and none may be written until the product decisions named below are
> taken. The reason is recorded in
> [SPEC-000 §4](../../product/intent-register.md#4-intents-deliberately-not-specified-in-this-phase),
> and it is not scheduling: writing requirements now would mean inventing those answers.
> Content moved verbatim from the pre-migration `intent.md` (§6); nothing added.

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

## Related

- Depends on F10 (expiry bound) and on the sales-evidence work in F4.
- Sibling of F9 — both are read off the same market-movement signal.
