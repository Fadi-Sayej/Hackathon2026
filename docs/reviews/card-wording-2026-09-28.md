---
ID: CARD-WORDING-2026-09-28
Title: What the owner's cards and pages say — wording and rendering, for approval
Status: Approved — by the repository owner, 2026-09-28 ("approve", on the wording and screenshots below)
Owner: smartshelf-engineer
Parent: [F6-S1](../features/F6-daily-action-surface/specs/F6-S1-daily-action-surface.md)
Inputs: [docs/reviews/F3-validation.md, F4-validation.md, F6-validation.md, F7-validation.md, public/data/dashboard.json (2026-09-28)]
Updated: 2026-09-29 (the thresholds question decided: keep them)
---

# What the owner's cards and pages say

Fixes the screen findings of the 2026-09-28 validations. Nothing here changes what is chosen for
the owner or any number; it changes how each card and page says it. **The wording below is
mine, in all three languages; the repository owner approved it on 2026-09-28.**

## What changes

1. **Every card says what to do** (F6 AC-110c). The engine already chose an action for every
   finding; the card now says it, in bold, under what is wrong.
2. **Today says what date its figures come from** (F7 AC-120): one line above the cards, from
   the stock file's date (6 June 2026 today).
3. **The evidence reads as words and figures** (F3, F4, F6 AC-112):
   - prices carry ₪ and percentages carry %;
   - a competitor finding's reference is stated as a price and how it was made, and its sources as a number of shops, where the card printed `[object Object]` once per source (118 times on one card);
   - codes (`negative_stock`, `no_row`, `pos`) become sentences, and the engine's English note becomes the language's own;
   - a value the engine does not have is left out, where the card printed `null`;
   - sentences are set in the text face, figures stay in the figure face.
4. **The implausible quantity is asked, not asserted** (F4 AC-069): «هل هذه الكمية صحيحة؟».
5. **The catalogue page states its seasonal limit** beside the dead count (F4 AC-067).
6. **Every threshold label is in the page's language**, with yes/no for `true`/`false` and the
   ceiling method in words. Two labels on the price page had **no translation at all** and
   showed as raw keys (`threshold.ceiling_source`, `threshold.ceiling_pct_derived`). The test
   meant to catch that (`checkpoint2`, AC-112) missed any key printed straight after a number,
   and is fixed too.

## Before and after (Arabic unless named)

| Screen | Image |
|---|---|
| Today, as it is now | [today-ar.png](card-wording-2026-09-28/today-ar.png) · [today-he.png](card-wording-2026-09-28/today-he.png) |
| A competitor card (it reaches Today once reconciliation's entries are settled) | [competitor-cards-ar.png](card-wording-2026-09-28/competitor-cards-ar.png) |
| Catalogue cards, with the implausible quantity | [catalogue-cards-ar.png](card-wording-2026-09-28/catalogue-cards-ar.png) |
| Data-cleanup cards | [hygiene-cards-ar.png](card-wording-2026-09-28/hygiene-cards-ar.png) |
| The catalogue page | [catalogue-page-ar.png](card-wording-2026-09-28/catalogue-page-ar.png) |
| The price page | [price-page-ar.png](card-wording-2026-09-28/price-page-ar.png) |
| The competitor page | [competitor-page-ar.png](card-wording-2026-09-28/competitor-page-ar.png) |

The competitor, catalogue and data-cleanup cards were rendered from today's real entries with
the higher-ranked ones set aside, because today only F1 and F2 reach Today's ten places.

## The wording

### What to do (new)

| Key | English | العربية | עברית |
|---|---|---|---|
| `action.verify_price` | Check this product's prices. | راجع أسعار هذا الصنف. | בדוק את המחירים של המוצר. |
| `action.count_product` | Count it on the shelf and in the storeroom. | عُدّه على الرف وفي المخزن. | ספור אותו על המדף ובמחסן. |
| `action.fix_record` | Fix its record in your till system. | صحّح سجلّه في نظام نقاط البيع. | תקן את הרשומה שלו במערכת הקופה. |
| `action.decide_idle` | Check it: is it on the shelf, is the count right, do you still sell it? | تحقّق منه: هل هو على الرف؟ هل العدد صحيح؟ هل ما زلت تبيعه؟ | בדוק: האם הוא על המדף? האם הספירה נכונה? האם אתה עדיין מוכר אותו? |
| `action.review_policy` | Compare this price with your pricing policy. | قارن هذا السعر بسياسة تسعيرك. | השווה את המחיר למדיניות התמחור שלך. |
| `action.check_purchase_cost` | Check what you pay your supplier for it. | راجع كم تدفع للمورّد ثمنه. | בדוק כמה אתה משלם עליו לספק. |

### The card's question (changed)

| Key | English | العربية | עברית |
|---|---|---|---|
| `characterisation.implausible_quantity` | Is this quantity right? | هل هذه الكمية صحيحة؟ | האם הכמות הזאת נכונה? |

### Evidence labels (changed: they were English in all three languages)

| Key | English | العربية | עברית |
|---|---|---|---|
| `evidence.attention_pct` | Urgent above | عاجل فوق | דחוף מעל |
| `evidence.cost_floor_pct` | Minimum margin over cost | أدنى هامش فوق التكلفة | מרווח מינימלי מעל העלות |
| `evidence.cost_source` | Cost from | مصدر التكلفة | מקור העלות |
| `evidence.evidence_state` | In the sales reports | في تقارير المبيعات | בדוחות המכירות |
| `evidence.format_note` | Note | ملاحظة | הערה |
| `evidence.margin_pct` | Margin | الهامش | המרווח |
| `evidence.policy_pct` | Your pricing policy | سياسة تسعيرك | מדיניות התמחור שלך |
| `evidence.premium_pct` | Above the reference | فوق السعر المرجعي | מעל מחיר הייחוס |
| `evidence.question` | Question | سؤال | שאלה |
| `evidence.reference` | Reference price | السعر المرجعي | מחיר ייחוס |
| `evidence.sources` | Compared with | مقارنةً بـ | בהשוואה ל |
| `evidence.unit_cost` | Cost per unit | تكلفة الوحدة | עלות ליחידה |

### Evidence values and the new lines (new)

| Key | English | العربية | עברית |
|---|---|---|---|
| `evidence.department` | Department | القسم | המחלקה |
| `evidence.sourcesCount` | {n} shops | {n} من المتاجر | {n} חנויות |
| `evidence.format_note.text` | Part of any difference comes from the kind of shop. | جزء من أي فرق سببه نوع المتجر. | חלק מכל הפרש נובע מסוג החנות. |
| `evidence.referenceKind.midpoint` | {value}: halfway between a supermarket ({supermarket}) and a shop like yours ({same}) | {value}: في المنتصف بين سوبرماركت ({supermarket}) ومتجر مثل متجرك ({same}) | {value}: באמצע בין סופרמרקט ({supermarket}) לחנות כמו שלך ({same}) |
| `evidence.referenceKind.same_format_only` | {value}: a shop like yours | {value}: متجر مثل متجرك | {value}: חנות כמו שלך |
| `evidence.referenceKind.supermarket_plus_allowance` | {value}: a supermarket's {supermarket}, plus {pct} for the kind of shop | {value}: سعر سوبرماركت {supermarket}، مع {pct} لفرق نوع المتجر | {value}: מחיר סופרמרקט {supermarket}, ועוד {pct} בגלל סוג החנות |
| `evidence.evidence_state.no_row` | no line in any report | لا سطر له في أي تقرير | אין לו שורה באף דוח |
| `evidence.evidence_state.observed_zero` | listed with zero units | مُدرج بصفر وحدات | מופיע עם אפס יחידות |
| `evidence.evidence_state.observed_units` | sold | بيع | נמכר |
| `evidence.cost_source.pos` | your stock file | ملف مخزونك | קובץ המלאי שלך |
| `evidence.cost_source.owner` | your answer | جوابك | התשובה שלך |
| `evidence.reason.negative_stock` | Stock below zero | مخزون أقل من صفر | מלאי מתחת לאפס |
| `evidence.reason.no_identifier` | No barcode | بلا باركود | בלי ברקוד |
| `evidence.reason.absent_price` | No shelf price | بلا سعر رف | בלי מחיר מדף |
| `evidence.reason.conflicting_duplicate` | The same barcode twice, with different details | الباركود نفسه مرتين، بتفاصيل مختلفة | אותו ברקוד פעמיים, עם פרטים שונים |
| `daily.asOf` | Figures from your stock file of {date}. | الأرقام من ملف مخزونك بتاريخ {date}. | המספרים מקובץ המלאי שלך מתאריך {date}. |
| `capability.note.seasonal` | Classified on {period}. A seasonal product can look dead in these months, so none of this is final until a full year of sales exists. | صُنّفت على {period}. قد يبدو صنف موسمي ميتًا في هذه الأشهر، فلا شيء من هذا نهائي قبل سنة كاملة من المبيعات. | סווג לפי {period}. מוצר עונתי יכול להיראות מת בחודשים האלה, ולכן שום דבר כאן אינו סופי לפני שנה מלאה של מכירות. |
| `threshold.value.derived` | measured from your prices | مقيس من أسعارك | נמדד מהמחירים שלך |
| `threshold.value.owner_declared` | as you stated it | كما ذكرته | כפי שקבעת |
| `threshold.value.densest_density_collapse` | where the number of markups drops most | حيث ينهار عدد نسب الرفع أكثر | איפה שמספר התוספות צונח הכי חד |

### Threshold labels (changed, and two added)

| Key | English | العربية | עברית |
|---|---|---|---|
| `threshold.artefact_cost_ratio` | Cost this many times the price is an entry error | تكلفة بهذه الأضعاف من السعر خطأ إدخال | עלות פי כך מהמחיר היא טעות הקלדה |
| `threshold.artefact_min_price` | A price below this is an entry error (₪) | سعر أقل من هذا خطأ إدخال (₪) | מחיר נמוך מזה הוא טעות הקלדה (₪) |
| `threshold.attention_pct` | Urgent above (%) | عاجل فوق (%) | דחוף מעל (%) |
| `threshold.ceiling_bands` | Markup bands measured | شرائح الرفع المقيسة | רצועות תוספת שנמדדו |
| `threshold.ceiling_method` | How the ceiling was found | كيف حُدّد السقف | איך נקבעה התקרה |
| `threshold.ceiling_population` | Products the ceiling was measured on | الأصناف التي قيس عليها السقف | המוצרים שעליהם נמדדה התקרה |
| `threshold.ceiling_population_excludes_withdrawn` | Withdrawn products left out | الأصناف المسحوبة مستبعدة | מוצרים שהוסרו לא נכללו |
| `threshold.comparability_floor` | Least likeness to your shop that counts | أدنى تشابه مع متجرك يُحتسب | הדמיון המינימלי לחנות שלך שנחשב |
| `threshold.cost_floor_pct` | Minimum margin over cost (%) | أدنى هامش فوق التكلفة (%) | מרווח מינימלי מעל העלות (%) |
| `threshold.format_allowance_basis_count` | Products the shop-type allowance was measured on | الأصناف التي قيس عليها فرق نوع المتجر | המוצרים שעליהם נמדד הפרש סוג החנות |
| `threshold.format_allowance_pct` | Allowance for the kind of shop (%) | فرق نوع المتجر (%) | הפרש סוג החנות (%) |
| `threshold.freshness_days` | Prices older than this are not used (days) | لا تُستخدم أسعار أقدم من هذا (أيام) | מחירים ישנים מזה לא נכללים (ימים) |
| `threshold.full_annual_cycle_months` | Months in a full year of sales | أشهر سنة كاملة من المبيعات | חודשים בשנה מלאה של מכירות |
| `threshold.implausible_revenue_share` | Share of sales that makes a quantity implausible | حصة من المبيعات تجعل الكمية غير معقولة | חלק מהמכירות שהופך כמות לבלתי סבירה |
| `threshold.max_credible_gap_pct` | Largest believable gap (%) | أكبر فرق يُصدَّق (%) | הפער הגדול ביותר שאפשר להאמין לו (%) |
| `threshold.policy_pct` | Your pricing policy (%) | سياسة تسعيرك (%) | מדיניות התמחור שלך (%) |
| `threshold.question_limit` | Questions shown at once | الأسئلة المعروضة معًا | שאלות שמוצגות בבת אחת |
| `threshold.thin_margin_pct` | A margin below this is thin (%) | هامش أقل من هذا رقيق (%) | מרווח נמוך מזה הוא דק (%) |
| `threshold.withdraw_with_stock` | Products with stock are withdrawn | تُسحب الأصناف التي لها مخزون | מוצרים עם מלאי מוסרים |
| `threshold.ceiling_source` | Where the ceiling comes from | مصدر السقف | מקור התקרה |
| `threshold.ceiling_pct_derived` | Ceiling measured from your prices | السقف المقيس من أسعارك | התקרה שנמדדה מהמחירים שלך |

## Not in this batch: decisions first

- **Idle stock's three answers** (F4 AC-071b). FR-070 wants distinguishable outcomes: *still on
  the shelf and unsold*, *the count is wrong*, *no longer carried*. Today an idle card offers
  the generic Done / Not worth it / Later. This needs a decision on what each answer records,
  not only on wording.
- **The Prices page's reference** (F3 AC-042, AC-053): whether the page should say that a
  reference is a supermarket price plus the measured 7.08%, and which kinds of shop it came
  from.
- **Whether the owner should see the technical thresholds at all** (the ceiling's bands, the
  entry-error ratios). This batch translates them; it does not decide to keep them.
  **Decided 2026-09-29 by the repository owner: keep them.** They say why something was
  flagged, and hiding them would be a screen change for no gain; the translations stand.
