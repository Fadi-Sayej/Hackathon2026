---
ID: F2-INTENT
Title: F2 — Stock Truth (reconciliation + data hygiene)
Status: Approved
Release: V1
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-002, INT-002B
Specs: [F2-S1](specs/F2-S1-stock-reconciliation-and-hygiene.md)
---

# F2 — أين يختفي مخزوني؟ · Stock Truth

> **Migration note.** Content moved verbatim from the pre-migration monolithic
> `intent.md` (§2ب). Nothing was added, removed or reworded. Section numbering from
> the original is kept in the headings so existing citations still resolve.

## Problem

نيّتان مسجّلتان يخدمهما ملفّ مواصفة واحد:

- **INT-002** — «أين يختفي مخزوني؟» — أصناف لا تتّسق أرقامها حسابياً. **بلا مبلغ، بقرار مقصود.**
- **INT-002B** — «أين يختفي مخزوني؟» — نظافة البيانات: مخزون سالب، باركود مجهول، سعر صفر. **بلا رقم، بقرار مقصود.**

## User

مالك المتجر أو موظّف يقوم بالجرد.

## Solution

**ما كان مكتوباً:** ₪63,572 مقسّمة إلى ₪43,281 «متماسك» (مخزونه موجب) و₪20,291 «تقديري»
(مخزونه سالب).

**لماذا كان ذلك التقسيم خاطئاً.** الصيغة `الناقص = المخزون الحالي − الوارد + المباع`
تستخدم كمية المخزون في **كل** حالة، لا في السالبة وحدها. وبياناته هو تكشف الخلل:

| الصنف | المخزون المسجّل | «الناقص» المحسوب |
|---|---:|---:|
| `בקבוק נביעות 1.5 ליטר` | 1,533 | **4,274** |
| `עין גדי 2 ליטר` | 349 | **3,487** |

المخزون هنا موجب، فيصنَّف «متماسكاً» — لكن الرقم يدّعي ضياع أربعة أضعاف ما هو مسجّل
أصلاً، في كازية. **الرقم الموجب ليس رقماً موثوقاً؛ هو فقط رقم غير سالب.** ومن أعلى عشرين
صنفاً بالقيمة، تسعة مخزونها سالب.

والحقيقة الحاكمة أبسط من أي تقسيم: **ملف المخزون لم يراجعه المالك بعد، ولا يصير الرقم
موثوقاً لأنه تجاوز الصفر.**

**القرار:** الكشف يبقى — «أرقام هذا الصنف لا تُغلق حسابياً» مثبت مهما كانت المدخلات.
**والمبلغ يسقط كاملاً**، لا يُقسَّم. والترتيب بحجم الفجوة نسبةً إلى الوارد. والرقم الحقيقي
يُعرف بعد العدّ، لا قبله.

**ومكسب غير متوقّع:** بسقوطه لم يبقَ في V1 إلا نوع واحد يحمل مالاً — الأسعار والهوامش.
فترتيب الشاشة اليومية بالمال صار ممكناً بلا تناقض، بعد أن كان مستحيلاً حين تنافس عليها
نوعان لا يُقارنان. وهذا يُسقط أكبر ثغرتين في المواصفات.

## Not In Scope

- تحديد الكمية الصحيحة.
- نسبة السبب (سرقة، كسر، خطأ إدخال) — لا يُميَّز بينها من هذا الدليل.
- الكتابة في نظام الـPOS (D-7).

## Related

- Spec: [F2-S1 — Stock Reconciliation and Data Hygiene](specs/F2-S1-stock-reconciliation-and-hygiene.md)
- Settled decisions: D-1, D-2, D-3, D-7 — [intent register §3](../../product/intent-register.md)
- **Design note (downstream, not a change to this intent):** the System Design's ADR-014
  answers this one spec with **two** capabilities (`reconciliation`, `hygiene`) because the
  two halves fail independently. The intent and spec boundary is unchanged.
