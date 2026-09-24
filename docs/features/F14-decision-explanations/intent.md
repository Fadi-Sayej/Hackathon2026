---
ID: F14-INTENT
Title: F14 — Decision explanations: the reason beside every recommendation
Status: Ready for review — becomes `Registered — not specified` once the owner approves the registration
Owner: smartshelf-pm
Release: V2 (proposed — GAP-012 asks when the promise is due)
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-EXPL
Specs: none
Inputs: [docs/product/PRD.md, docs/product/intent-register.md, issue #54, PR #178, tag v1-attic-2026-09-24, docs/features/F8-order-quantity/intent.md, public/data/dashboard.json (generated 2026-09-24T02:46:37Z), ADR-007]
Updated: 2026-09-24
---

# F14 — لماذا هذا القرار؟ · Decision Explanations

> **Status: registered, deliberately NOT specified.** The promise stands. The repository
> owner confirmed it on 2026-09-24, asked directly during the #80 triage. *How* it is kept
> is a product decision nobody has taken yet: [GAP-012](../gaps-and-open-questions.md),
> with the choices laid out in the
> [F14 brief](../../product/open-decisions/F14-decision-explanations.md). A spec is
> forbidden until it is taken.

## Problem

وعدنا YomYom بنظام توصيات **مع مساعد ذكاء اصطناعي يشرح القرار** (#54). والفرق كما كُتب
يومها: «اطلب 24 وحدة» مقابل «اطلب 24 وحدة — غداً 36 درجة، والخميس ذروة، وبقي 12 فقط».
رقم بلا سبب أمرٌ من آلة؛ ورقم بسببه نصيحةٌ من شيء يفهم متجره.

اليوم لا يشرح المنتج شيئاً بجملة. كل بطاقة تعرض أرقامها كما هي — في المخزون الذي لا
يُغلق مثلاً: المخزون المسجّل، والوارد، والمباع، وغير المفسَّر، والفترة — ويبقى على المالك
أن يستنتج السبب وحده. والطبقة التي كُتبت لهذا الوعد، شرحٌ بنموذج لغوي عبر خادم وسيط،
حُذفت من المنتج في 2026-09-24 (#178) مع محرّك الطلبيات الذي كانت تشرحه، لأن أيّ شاشة
لم تعرضها؛ والشيفرة محفوظة في الوسم `v1-attic-2026-09-24`.

## User

مالك المتجر، أمام الشاشة اليومية أو صفحة قدرة، في لحظة القرار: أعدّ هذا الصنف؟ أصحّح
السعر؟ أطلب؟

## Solution (direction only)

جملة سبب واحدة بجانب كل توصية، بلغة المالك، تقول **لماذا** هذا البند أمامه — مبنيّة فقط
من أرقام نشرها المحرّك لذلك البند نفسه.

**ما يُشرح منه موجود اليوم.** كل قدرة تنشر أدلّتها مع كل بند. من `public/data/dashboard.json`
(المولَّد 2026-09-24T02:46:37Z):

| القدرة | بنود | الأدلّة المنشورة مع كل بند |
|---|---:|---|
| `price_consistency` | 199 | `shelf_price`, `delivery_price`, `difference`, `markup_pct`, `ceiling_pct`, `commission_compounds` |
| `reconciliation` | 355 | `recorded_stock`, `receipts`, `units_sold`, `unaccounted`, `window_id`, `reconcile_months` |
| `competitor_position` | 6 | `shelf_price`, `reference`, `premium_pct`, `sources`, `policy_pct`, `attention_pct`, `cost_floor_pct`, `cost_price`, `format_note` |
| `margin_below_cost` | 71 | `shelf_price`, `cost_price`, `margin_pct`, `cost_source` |
| `catalogue_lifecycle` | 1,632 | `evidence_state`, `recorded_stock`, `unit_cost`, `window_id`, `question` |
| `hygiene` | 1,117 | `reason`, `recorded_stock` |

**القيد الحاكم: الشرح لا يضيف رقماً ولا سبباً.**
- كل رقم في جملة السبب رقمٌ منشور في أدلّة بنده.
- وحيث لا يُذكر رقم بصدق، لا يُذكر (D-3). ولا مبلغ على إشارة مشتقّة من كمية مخزون (D-1).
- ولا يَنسب الشرح سبباً لم يثبته الدليل: في المخزون الذي لا يُغلق لا يُقال سرقة ولا كسر ولا
  خطأ إدخال (F2-S1 INV-015).

**Success — countable within a week of the owner using it** (read from the artefact the
owner's screen serves):

1. Every item on the daily surface carries a reason sentence: **10 of 10**.
2. **Zero** reason sentences state a figure that is not in their own item's published
   evidence. This is checked mechanically against the evidence.

## Not In Scope

- **حديث حرّ عن أي موضوع.** الشرح يخصّ البند المعروض فقط، لا المتجر كلّه ولا السوق.
- **الالتفاف على قرار «لا رقم».** لا يقدّر الشرح مبلغاً حيث قرّرت D-1 وD-3 ألّا مبلغ، ولا
  يعطي حدّاً أعلى ولا «مثالاً».
- **التنفيذ.** يشرح ولا يقرّر ولا يفعل شيئاً نيابةً عن المالك.

## Related

- **Depends on F8 for "the decision" in the promise as first written**, which was an order
  quantity. F8 is itself `Registered — not specified` (GAP-008).
- **Explains the V1 findings of F1–F5, where they appear on F6's surface.**
- **Bound by F7.** A figure an explanation states must be one the engine published, and
  so recomputable.

## Settled decisions this depends on

| D-id | What it settles | Why this feature depends on it |
|---|---|---|
| D-1 | No money on a signal derived from a stock quantity | A reason sentence for a reconciliation or idle-stock item may not introduce an amount |
| D-3 | No figure rather than zero where none can be stated | A sentence may not fill a withheld figure with a guess or a zero |
| D-10 | An uncertain figure is labelled uncertain before it is questioned | A sentence that cites an estimated value must say it is an estimate |

## Blocking product decisions

[GAP-012](../gaps-and-open-questions.md): what is explained first, who writes the sentence,
and when the promise is due. The options the data supports are in the
[F14 brief](../../product/open-decisions/F14-decision-explanations.md).

## Open questions

| GAP-id | Question | Who can answer it |
|---|---|---|
| GAP-012 | What is explained first (V1 findings, or F8's orders); who writes the sentence; when the promise is due | the repository owner, and the client for the due date |
