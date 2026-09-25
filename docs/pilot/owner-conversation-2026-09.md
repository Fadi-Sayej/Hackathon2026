---
ID: PILOT-CONV-2026-09
Title: The owner conversation — what to ask, and why each answer changes the build
Status: Ready for review
Owner: smartshelf-pm
Parent: [PRD](../product/PRD.md)
Inputs: [GAP-009, GAP-011, F13-S1 §14, F8-S1 (OQ-903, OQ-904), docs/reviews/system-design-readiness.md run 3, data/internal/silver_pos/*.parquet]
Updated: 2026-09-25 (#7 and #8 added for F8-S1)
---

# The owner conversation

Eight questions. Six are his to answer and two are ours to check with him. Every figure below
was read from his own export, not from a document (rule 11).

**Bring the product list in §1 on a phone.** It is the whole of GAP-009 and it takes about
four minutes.

---

## 1. GAP-009 — and we now think the answer is "no"

**What we were going to ask:** *"When a product is absent from your monthly reports, does
that mean it sold nothing?"* Automatic withdrawal rests on it, for 3,932 products.

**What we found before asking.** Five departments with 20+ products have **not one row in any
of the seven reports**, across seven months:

| Department | Products | Rows in seven months |
|---|---|---|
| מחלקת drive | 51 | **0** |
| מאפים (גדרון - שמרים) | 46 | **0** |
| אריזות ו מוצרי ניקוי לסופר | 41 | **0** |
| מוצרי מאפים | 25 | **0** |
| בשרים | 25 | **0** |

A drive-through that sold nothing in seven months is not a finding, it is a broken
assumption. Same for a bakery and a meat counter. **So "absent" does not mean "sold
nothing" — at least not for these 188 products. It means these reports do not itemise them.**

Catalogue-wide, **1,778 of 7,674 products (23.2%)** appear in at least one report.

### The question to actually ask

> **هل التقارير الشهرية السبعة تغطي كل الأقسام؟** لاحظنا أن أقسام كاملة — الـ drive،
> المخبوزات، اللحوم، مواد التنظيف والتغليف — لا تظهر فيها ولا مرة واحدة خلال سبعة أشهر.
> هل تُباع هذه عبر صندوق أو نظام مختلف؟

And then, showing the list: **هل بِعتَ أياً من هذه خلال آخر سبعة أشهر؟**

Twenty products absent from every report **while he is holding stock of them**, one per
department, highest stock first:

| Product | Department | In stock |
|---|---|---|
| פקדון משקה בודד | מוצרי שימוש מטבח -חנות | 6268 |
| כוס חד פעמי 8 OZ  (יח 1000) | מוצרי קפה (סאשה ) | 4005 |
| פיקדון | פיקדון  ו משטחים - ארגזים | 3493 |
| תפוז טרי 1K TAPUZ TARI ( אדום ) | תפוז טרי ( שימוש עצמי ) | 1593 |
| קונוס שלשי | אבזרי עישון | 1088 |
| מאפה לחמניית פרצלה יחידה | מאפים (גדרון - שמרים ) | 720 |
| קרואסון שוקולד | מחלקת drive | 645 |
| נביעות 500 מ"ל TO GO | מוצרי מכולת | 360 |
| סוכריה על מקל | חטיפים מתוקים | 298 |
| מקלות ביסקוויט בכוס מפרץ ההרפתקאות | מוצרי יום הולדת ו מתנות | 251 |
| ממתק ליקריץ שטיחים חמוצים קולה 20 גרם | חטיפים מלוחים | 144 |
| משקה TMAX גולד 250 מ"ל | משקאות | 121 |
| חלב בקבוק טבעי | מוצרי מקרר | 83 |
| אבטיח | פירות וירקות | 78 |
| MEN GLASSES | משקפים | 76 |
| מיכל חד פעמי 230 גרם עם שסתום והברגה | מוצרי חצר תחנה | 72 |
| בונזו מולטיפאק 3*400 גרם - חום | בעלי חיים | 66 |
| דבש עם פיצוחים גדול | פיצוחים | 61 |
| נייר אלמניוום לנרגילה | חד פעמי | 55 |
| מלח שולחן מעולה | מוצרי בית | 53 |

**What each answer changes.** If whole departments are sold through another till, withdrawal
by absence is wrong for them and must be scoped to departments the reports actually cover —
and D-14 stays in force. If he says these genuinely did not sell, the assumption holds and
`published_population` can move to `living` (ADR-020, one line).

---

## 2. GAP-011 — is 18% your ceiling, or just where your pricing stops?

The rule derives **18%** from his own distribution: 81 products in the 16–18% band
collapsing to 7 in 18–20%. That is evidence of where his pricing stops, not a statement that
he believes his ceiling is 18%. **1,124 products are kept silent** because they sit inside
"his sound policy", so the difference matters.

> **ما هي نسبة الربح القصوى التي تعتبرها سياستك؟** نحن نستنتج 18% من أسعارك نفسها — هل
> هذا رقمك، أم أنه صدفة؟

**A different answer is not a defect.** It means his behaviour and his stated policy have
parted, which is more useful than either number alone. Whatever he says goes into
`policy.owner_declared_ceiling_pct` (currently `null`); the system publishes both and notes
when they differ.

---

## 3. A figure we have committed to saying, and cannot yet

`intent.md` §9.4 commits to telling him that **1,628** items in his catalogue are services
and internal codes that nobody else sells. **Our own rule finds 722** — well under half.

> **Updated 2026-09-13, from 782.** The figure moved when ADR-022 stopped counting
> barcode-less products that share a name as separate products: 60 such rows now appear as
> 26 conflict records instead, and all 60 were structurally uncomparable, so the count fell
> by exactly 60 and the comparable population did not move (7,523 − 722 = 6,801). The gap
> to 1,628 got wider, not narrower — which makes this question more pressing, not less.

Either the barcode-digit test under-counts services that carry a plausible code, or the
1,628 was looser than the sentence implies. **Do not say either number until this is
settled** (rule 11). Raised by the readiness gate's run 3.

---

## 4, 5, 6 — the three numbers F13-S1 is blocked on

[F13-S1](../features/F13-pilot-measurement/specs/F13-S1-pilot-measurement.md) is written and
`Blocked`. These three unblock it. F13's intent is explicit that they are settled **before**
more code is written.

| # | Question | Arabic | Why it blocks |
|---|---|---|---|
| 4 | **رقم النجاح** — after 30 days, how many ₪ recovered makes this a success? | بعد 30 يوماً، كم ₪ مستردّة تجعل التجربة ناجحة؟ | The measurement surface has no threshold to render against |
| 5 | **سعر الاشتراك** — agreed *today*, starting automatically if the number is met | ما هو سعر الاشتراك إذا تحقّق الرقم؟ | Not a build input. The intent is blunt about why it is asked now: a free trial with no agreed price measures politeness, not value |
| 6 | **إيقاع البيانات** — daily or weekly, and who sends it | يومي أم أسبوعي، ومَن يرسله؟ | Sets the measurement window's granularity, which every figure must state |

**A caveat to raise on #4 before he answers.** Of the three things his success number adds up
— «أسعار مصحّحة + مخزون مفسّر + كتالوج منظّف» — **only corrected prices can honestly be
stated in money.** Explained stock is derived from counts he himself calls unreliable, and we
do not put a shekel figure on those (D-1). So the number he names should be about **corrected
prices**, with the other two reported as counts beside it. That is OQ-801, and his answer
decides it.

---

## 7, 8 — the two facts F8-S1 needs before it can suggest any order

[F8-S1](../features/F8-order-quantity/specs/F8-S1-order-quantity.md) is written and
approved (2026-09-25). It cannot publish a single quantity until he answers these two. They
cannot be guessed: the repository owner asked on 2026-09-25 that they not be.

| # | Question | Arabic | Why it blocks |
|---|---|---|---|
| 7 | **Can the POS export, per product and per day, both sales and deliveries (כניסות מלאי)? And can it be sent at least weekly?** | هل يستطيع نظام الـPOS أن يصدّر لكل صنف ولكل يوم المبيعات وכניסות המלאי؟ وهل يمكن إرسالها مرة في الأسبوع على الأقل؟ | The seven monthly reports cannot be divided into days (rule 13). Without this, no order quantity exists, and without the deliveries no stock count can be carried forward (OQ-904) |
| 8 | **For each department: when does he order it (which weekdays, or every how many days from when, or no fixed days), and how long do its products keep?** | لكل قسم: متى تطلبه؟ في أيّ أيام، أو كل كم يوماً ومنذ متى، أو بلا أيام ثابتة؟ وكم يوماً تبقى منتجاته صالحة؟ | A suggestion is for a department's next order day and is capped by what sells before it spoils. Neither may be guessed: a department with no answer, or with no fixed days, gets no suggestion (OQ-903, OQ-908) |

**#1 matters to F8 too.** If the departments missing from every report sell through another
till, F8 must not treat their absence as "sold nothing" (F8-S1 FR-156).

---

## What to bring back

1. Do the five zero-coverage departments sell through a different till? *(→ GAP-009, ADR-020)*
2. Of the twenty products: which, if any, sold in the last seven months? *(→ GAP-009)*
3. His markup ceiling, in his words, or "no policy". *(→ GAP-011, `owner_declared_ceiling_pct`)*
4. The success ₪ number, and whether it is prices-only. *(→ F13-S1 §14, OQ-801)*
5. The subscription price. *(→ PRD §8)*
6. Data cadence and who sends it. *(→ F13-S1 FR-141)*
7. Whether the POS can export sales and deliveries per product per day, sent at least weekly. *(→ F8-S1 OQ-904)*
8. Per department: when he orders it, and how long its products keep. *(→ F8-S1 OQ-903, OQ-908)*

Answers go into [gaps-and-open-questions.md](../features/gaps-and-open-questions.md) with the
date, and the three F13 numbers into F13-S1 §14. Nothing here is quoted onward until it is
written down — that is rule 11, and §3 above is what happens when it is not.
