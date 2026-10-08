---
ID: F3-INTENT
Title: F3 — Competitor Price Position
Status: Approved
Owner: smartshelf-pm
Release: V1
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-003
Specs: [F3-S1](specs/F3-S1-competitor-price-position.md)
Inputs: [docs/product/PRD.md, docs/product/intent-register.md, ADR-008, ADR-028]
Updated: 2026-10-08 (dated note: D-39, a new store starts with no price rule); 2026-09-29 (dated note: the 1,970 / 144 / 97 table rests on the deleted Kaggle-era files)
---

# F3 — هل أسعاري معقولة مقابل الجيران؟ · Competitor Price Position

> **Migration note.** Content moved verbatim from the pre-migration monolithic
> `intent.md` (§3 + §3ب + §3ج). Nothing was added, removed or reworded. Section numbering from
> the original is kept in the headings so existing citations still resolve.

## Problem

«هل أسعاري معقولة مقابل الجيران؟» — مع فارق تصنيف المتجر بين الكازية والسوبرماركت.

## User

مالك المتجر.

## Solution

**القاعدة الحاكمة: سعر YomYom لا يكون مرجعاً لنفسه أبداً.** والمرجع مرتَّب:

| المنافس | المسافة | أصناف مقارنة | الوسيط | كيف يُستخدم |
|---|---|---|---|---|
| **Alonit (Dor Alon)** | 1,400م | 755 | **‎−11%** | **المرجع الأول** — كازية مثله |
| Shufersal Deal | 1,800م | 663 | +6% | سياق، **بعلامة صريحة** |
| Rami Levy | 2,100م | 1,314 | +20% | سياق، **بعلامة صريحة** |

**ورقة يحملها إلى الاجتماع:** مقابل الكازية المنافسة، **YomYom أرخص بـ11%** (526 صنفاً أرخص مقابل 144 أغلى). فارقه مع رامي ليفي (+20%) **هو فارق تصنيف المتجر، لا جشع** — والكازية في إسرائيل تبيع أعلى من السوبرماركت لأسباب معروفة.

**لكن التصنيف ليس رخصة مفتوحة.** لذلك عتبتان:

- **90% — الـelbow الإحصائي.** الكثافة تنهار من 34 صنفاً إلى 6. **18 صنفاً** فوقها = خارج كل نمط.
- **60% — الحدّ التجاري.** ثلاثة أضعاف الفارق الطبيعي (+20% مقابل رامي ليفي). **165 صنفاً** فوقه.

**وفوق 200%: صفر أصناف.** المخاوف من فروق مبالغ فيها مشروعة، والواقع أنظف منها — وهذه أيضاً ورقة تُقال.

**تحذير على كل مقارنة مع سوبرماركت:** *"هذا سوبرماركت لا كازية — جزء من الفارق طبيعي."* الكود يملك بوّابة `storeFormat.js` تفعل هذا جزئياً؛ المطلوب أن تُستخدم **كسياق موسوم، لا أن تُلغى** — فارق 90% مع رامي ليفي إشارة حقيقية مهما اختلف التصنيف.

> **Added 2026-09-25 (not part of the migrated content).** `storeFormat.js` no longer exists:
> it was deleted on 2026-09-24 (a740b96, ADR-028). The requirement in the line above is met
> by the engine instead. `src/engine/competitor_position.py` marks every store `comparable`
> or `context` against the comparability floor (ADR-008), so a supermarket comparison is shown
> as labelled context and is not dropped (F3-S1 C-21). Only the file reference was stale.



## 3ب. النية 3 — سياسة تسعير معلنة، تحكمها بوّابة التكلفة

**ما كان مكتوباً:** عتبتان مشتقّتان من توزيع الفروق (90% إحصائية، 60% تجارية) مقابل
أرخص سعر متاح.

**ما تغيّر، وثلاثة أسباب:**

**١. السياسة تسبق الإحصاء.** العتبة المشتقّة من التوزيع تصف ما هو قائم؛ نحن نريد أن نصف
ما نقبله. فالقاعدة صارت سياسة معلنة بلسان المالك: **«إن كان سعر المنتج 5، لا أبيعه بأكثر
من 8»** — أي **+60%**. رقمٌ اختاره، لا رقمٌ استخرجناه.

**٢. المرجع لا يكون سعراً واحداً.** مقارنة الكازية بالسوبرماركت وحده ظلم؛ ومقارنتها
بالكازية وحدها تغطّي 329 صنفاً فقط. فالمرجع **متوسط أرخص سوبرماركت وأرخص كازية**. وحين
لا يتوفّر سعر كازية — 1,215 صنفاً، لأن الكازيات لا تنشر أسعارها كالسلاسل — يُضاف إلى سعر
السوبرماركت **بدل تصنيف مقيس من الـ426 صنفاً التي نملك فيها السعرين معاً**، لا رقم مخترع.

**٣. وقبل كل ذلك: بوّابة التكلفة.** وهذه القاعدة التي لا تُكسر.

**§3ج — البوّابة التي تسبق كل مقارنة**

> **لا تُعرض توصية بتخفيض سعر إن كان السعر المرجعي لا يترك هامشاً لا يقلّ عن 10% فوق
> تكلفة شرائنا.**

سعر المنافس ليس دليلاً على أنّ سعرنا خطأ. قد تكون تكلفة شرائه أقلّ من تكلفتنا، وقد يبيع
هو بخسارة عمداً. وفي الحالتين، التوصية بمجاراته توصية بالخسارة.

وبياناته تُثبت أنّ هذا ليس احتمالاً نظرياً — **43 من 144 صنفاً تتجاوز السياسة كانت
ستنتج توصية خاسرة**:

| الصنف | سعرنا | تكلفتنا | المرجع |
|---|---:|---:|---:|
| `צפתית טרה 4 ק"ג` | ₪158.21 | **₪147.11** | **₪54.00** |
| `גבינה צהובה 28% 3 ק"ג` | ₪112.55 | **₪112.55** | **₪52.85** |
| `ביסלי פיצה 200ג` | ₪13.90 | **₪6.78** | **₪6.50** |

الجبنة الصفدية: رامي ليفي يبيعها بثلث ما نشتريها به. المقارنة هنا ليست بين سعرين بل بين
قوّتَي شراء — سلسلة تشتري بعشرات الأطنان مقابل متجر يشتري كرتونة. توصية «خفّض سعرك» كانت
ستعني خسارة ₪93 على كل قطعة.

**والأصناف الساقطة لا تختفي؛ تتحوّل إلى إشارة أخرى:** *«المنافس يبيعه بأقلّ من تكلفتك —
تكلفة شرائك مرتفعة، فاوض مورّدك.»* مشكلة حقيقية، لكنها في المشتريات لا في التسعير.

**والأصناف بلا سعر تكلفة (4) لا يُحكم عليها إطلاقاً** — القاعدة نفسها: لا رقم بديلاً عن
رقم مجهول.

**النتيجة على بياناته:**

| الطبقة | يبقى |
|---|---|
| 1,970 صنفاً لها سعر منافس | — |
| تتجاوز سياسة +60% من المرجع المتوازن | 144 |
| **بعد بوّابة التكلفة (هامش ≥ 10%)** | **97** |
| منها فوق 100% من المرجع — تحذير فوري | ~15 |

والـ97 الباقية معروضة على مستويين: ما يتجاوز 100% يدخل شاشة الصباح، والباقي في صفحة
الأسعار للمراجعة على مهل. **السياسة +60% محفوظة كاملة؛ المستويان يقرّران متى يزاحم
التنبيه مهامَ اليوم، لا ما إذا كان مخالفاً.**

> **Added 2026-09-29 (not part of the migrated content).** Nothing can reproduce the table
> above now, and that is not an engine fault. Its 1,970 / 144 / 97 were measured against the
> Kaggle-era price files for Alonit Kafr Qasim, Rami Levy Petah Tikva and Shufersal Deal Petah
> Tikva (`scripts/classify_store_types.py` maps `kaggle_dor_alon`, `kaggle_rami_levy` and
> `kaggle_shufersal` to those three stores). Their importer was deleted on 2026-09-24
> (`0a88154`), and none of the three is among the stores the engine compares against today.
> The method survives: `balanced_reference` builds the reference as point 2 above says (the
> cheapest supermarket and the cheapest shop of the store's own format, averaged; the
> supermarket plus the measured allowance when no such shop sells it; that shop's price alone
> when no supermarket does). On the 2026-09-29 data, with the AM-PM shops classified
> (`9ff20bb`), the engine finds 13 products over the policy after the cost gate (the table's
> 97), 2 of them over 100% (its ~15). `npm run figures` gives the current count; this table
> is history.

> **Added 2026-10-08 (not part of the migrated content).** **D-39:** the +60% above is YomYom's
> owner's own rule, and a new store's copy does not inherit it. Until a store's owner states
> their limit, the app flags no price as over it, and F3 says it is waiting for that limit.
> YomYom keeps its +60%.

## Not In Scope

- اقتراح السعر المصحَّح.
- تتبّع تاريخ أسعار المنافسين.
- الحكم على استراتيجية تسعير المنافس.
- توسيع مجموعة المتاجر المرصودة.

## Related

- Spec: [F3-S1 — Competitor Price Position](specs/F3-S1-competitor-price-position.md)
- Settled decisions: D-3, D-5, D-39 — [intent register §3](../../product/intent-register.md)
