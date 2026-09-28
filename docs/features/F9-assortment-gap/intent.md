---
ID: F9-INTENT
Title: F9 — Assortment Gap
Status: Registered — not specified
Release: V2
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-005
Specs: none
---

# F9 — ماذا يبيع السوق ولا أبيعه أنا؟ · Assortment Gap

> **Status: registered, deliberately NOT specified.** No `F#-S#` document exists for
> this feature and none may be written until the product decisions named below are
> taken. The reason is recorded in
> [SPEC-000 §4](../../product/intent-register.md#4-intents-deliberately-not-specified-in-this-phase),
> and it is not scheduling: writing requirements now would mean inventing those answers.
> Content moved verbatim from the pre-migration `intent.md` (§6); nothing added.

## Problem

«ماذا يبيع السوق ولا أبيعه أنا؟» — فرصة، لا خسارة.

## User

مالك المتجر.

## Solution (direction only)

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

## Blocking product decision

ما الذي يُتوقَّع من المالك أن **يفعله** بنتيجة «قوي في السوق، ضعيف عندك». `intent.md` §6 يصوغها
فاتحةَ حوار، وهذه ليست بعد قراراً يستطيع النظام تسجيله.

## Related

- Sibling of F8 — the other face of the same market-movement signal.
- The 527 products carrying `WATCH_PRODUCT` today are this feature's raw material; the tag
  leaves V1 with the System Design's §5.3.

## Added 2026-09-28 (not part of the migrated content)

The blocking decision above was taken by the repository owner as **D-25**, from the
[F9 brief](../../product/open-decisions/F9-assortment-gap.md):
- **A finding** is a product he does not stock that the market (D-18) has run out of,
  by ADR-031's rule.
- **It is an entry on his daily surface**, where he records "I'll try it" or "Not for my
  store".

The products he does stock are F8's (D-19, F8-S1 FR-158), so the "weak here" half of the
sentence above is no longer F9's. The `WATCH_PRODUCT` tag and its 527 are gone with the
recommender that produced them (GAP-008a). The status stays `Registered — not specified`
until a spec is approved.
