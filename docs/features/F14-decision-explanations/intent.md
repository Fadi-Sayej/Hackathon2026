---
ID: F14-INTENT
Title: F14 — Decision explanations: the reason beside every order suggestion
Status: Registered — not specified
Owner: smartshelf-pm
Release: V2, with F8 — no due date (D-17)
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-EXPL
Specs: none
Inputs: [docs/product/PRD.md, docs/product/intent-register.md (D-15 … D-20), issue #54, PR #178, tag v1-attic-2026-09-24, docs/features/F8-order-quantity/intent.md, docs/product/open-decisions/F14-decision-explanations.md, ADR-007]
Updated: 2026-09-24
---

# F14 — لماذا هذا القرار؟ · Decision Explanations

> **Status: registered, deliberately NOT specified, and now for F8's reason.** The promise
> stands: the repository owner confirmed it on 2026-09-24. How it is kept was decided the same
> day, as [D-15 … D-17](../../product/intent-register.md):
> - it explains **F8's order suggestions**;
> - a model writes the sentence **once a night**, under three conditions;
> - it has **no due date**.
>
> A spec is forbidden until F8 exists, because the orders it explains do not
> ([GAP-008](../gaps-and-open-questions.md)).

## Problem

وعدنا YomYom بنظام توصيات **مع مساعد ذكاء اصطناعي يشرح القرار** (#54). والفرق كما كُتب
يومها: «اطلب 24 وحدة» مقابل «اطلب 24 وحدة — غداً 36 درجة، والخميس ذروة، وبقي 12 فقط».
رقم بلا سبب أمرٌ من آلة؛ ورقم بسببه نصيحةٌ من شيء يفهم متجره.

اليوم لا يشرح المنتج شيئاً بجملة، ولا يقترح طلبيات أصلاً: اقتراح الكمية هو F8، ولم يُحدَّد
بعد. والطبقة التي كُتبت لهذا الوعد، شرحٌ بنموذج لغوي عبر خادم وسيط، حُذفت من المنتج في
2026-09-24 (#178) مع محرّك الطلبيات الذي كانت تشرحه، لأن أيّ شاشة لم تعرضها؛ والشيفرة محفوظة
في الوسم `v1-attic-2026-09-24`.

## User

مالك المتجر، أمام اقتراح طلبية، في لحظة القرار: أطلب هذه الكمية أم لا؟

## Solution (direction only)

بجانب كل اقتراح طلبية جملة سبب واحدة بلغة المالك، تقول **لماذا** هذه الكمية — مبنيّة فقط من
الحقائق التي ينشرها F8 مع ذلك الاقتراح. يكتبها نموذج مرّةً كل ليلة، وتُنشر مع الاقتراح؛ لا
يعمل شيء لحظة فتح الشاشة (D-16، ويتّسق مع ADR-007).

**القيد الحاكم: الشرح لا يضيف رقماً ولا سبباً.**
- كل رقم في الجملة رقمٌ منشور في حقائق اقتراحها.
- يُفحص ذلك آلياً قبل النشر، لا بطلبٍ في التعليمات. في التجربة الوحيدة الحقيقية حوّل نموذجٌ
  «اطلب 20 وحدة» إلى «25 وحدة» (`factsGuard.js`، الوسم أعلاه).
- وحيث لا يُذكر رقم بصدق لا يُذكر (D-3). ولا مبلغ على إشارة مشتقّة من كمية مخزون (D-1).

**Success — countable within a week of the owner using F8's suggestions** (read from the
published artefact):

1. Every order suggestion on screen carries a reason sentence: **N of N**.
2. **Zero** sentences state a figure their suggestion's facts lack. This is what the
   mechanical check counts.

## Not In Scope

- **شرح نتائج V1** (الأسعار، المخزون الذي لا يُغلق، الكتالوج…). قرار D-15: تبقى تعرض أدلّتها كما هي.
- **حديث حرّ عن أي موضوع.** الشرح يخصّ الاقتراح المعروض فقط.
- **الالتفاف على قرار «لا رقم».** لا يقدّر مبلغاً حيث قرّرت D-1 وD-3 ألّا مبلغ، ولا يعطي
  حدّاً أعلى ولا «مثالاً».
- **مساعد يُسأل على الشاشة لحظياً.** رُفض لصالح الكتابة الليلية (D-16).

## Related

- **Depends on F8** (`Registered — not specified`; its decisions are D-18 … D-20). There
  is nothing to explain until F8 publishes order suggestions and the facts behind them.
- **Bound by F7.** A figure an explanation states must be one the engine published, and so
  recomputable.

## Settled decisions this depends on

| D-id | What it settles | Why this feature depends on it |
|---|---|---|
| D-1 | No money on a signal derived from a stock quantity | A sentence may not introduce an amount on a quantity-derived fact |
| D-3 | No figure rather than zero where none can be stated | A sentence may not fill a withheld figure with a guess or a zero |
| D-10 | An uncertain figure is labelled uncertain before it is questioned | A sentence citing an estimated value must say it is an estimate |
| D-15 | F14 explains order suggestions, not V1's findings | What F14 explains, and why it waits on F8 |
| D-16 | A model writes the sentence once a night, from the suggestion's facts, with a paid account, a monthly ceiling and alert, and a mechanical figure check before publishing | How the sentence is produced, and the conditions it is published under |
| D-17 | No due date | When: with F8 in V2, and no date is committed |

## Blocking product decisions

None of F14's own; GAP-012 is resolved as D-15 … D-17. F8's three decisions were taken too,
on 2026-09-24, as D-18 … D-20 ([GAP-008](../gaps-and-open-questions.md)). F14 now waits only
on F8 being specified.

## Open questions

None. GAP-008, F8's three decisions, was resolved on 2026-09-24 as D-18 … D-20.
