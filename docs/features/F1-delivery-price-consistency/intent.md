---
ID: F1-INTENT
Title: F1 — Delivery-Platform Price Consistency
Status: Approved
Release: V1
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-001
Specs: [F1-S1](specs/F1-S1-delivery-price-consistency.md)
---

# F1 — حارس سعر التوصيل · Delivery-Platform Price Consistency

> **Migration note.** Content moved verbatim from the pre-migration monolithic
> `intent.md` (§2). Nothing was added, removed or reworded. Section numbering from
> the original is kept in the headings so existing citations still resolve.

## Problem

«لا أريد أن أخسر في كل عملية بيع» — سعر الرف مقابل سعر منصّة التوصيل في التصدير نفسه.

## User

مالك المتجر، على الشاشة اليومية.

## Solution

**ما كان مكتوباً:** "₪2,336 خسارة في كل عملية بيع" من 1,147 فجوة Wolt.

**ما كشفته البيانات:** 79% من أصنافه سعر Wolt فيها **مساوٍ لسعر الرف بالضبط** (4,932 من 6,260). ومن الـ1,260 التي يرفعها، **الوسيط 8.4% لا 30%**. ونصّ التوصية في الكود نفسه يقول *"align **or confirm intentional**"* — أي أنه **سؤال**، بينما الوثيقة أعلنته **خسارة**. لو قلناها كخسارة لردّ المالك: *"أنا أرفع سعر Wolt عمداً لتغطية العمولة — أتحسب ربحي خسارة؟"* وسقطت كل أرقامنا معها.

**العتبة من بياناته، لا من افتراض.** الكثافة تنهار عند 18%: من 81 صنفاً في شريحة 16–18% إلى **8 أصناف** في 18–20% — انهيار 90%، ثم ترتفع ثانية. أي أن **سياسته الفعلية تقف عند 18%**.

| # | المؤشر | العدد | الرسالة للمالك |
|---|---|---|---|
| 🔴 ١ | **Wolt أرخص من رفّك** | **68** | خسارة مؤكدة — سعر أقل **وعمولة فوقه**. (زيت زيتون: رف ₪37.90 · Wolt ₪21.90) |
| 🔴 ٢ | **أغلى من السوق +90%** | **18** | شذوذ إحصائي — تأكّد من السعر |
| ⚠️ ٣ | **أغلى من السوق +60%** | **165** | فوق المعقول لكازية — مقصود؟ |
| ⚠️ ٤ | **زيادة Wolt فوق 18%** | **136** | خارج سياستك المعتادة — مقصود؟ |

**387 تنبيهاً حقيقياً بدل 1,147** — والباقي (1,124 صنفاً ضمن 0–18%) **لا يُعرض إطلاقاً، لأنه سياسته السليمة**.

## Not In Scope

- المقارنة بأي متجر آخر (F3).
- الهامش مقابل التكلفة — إشارة أخرى بعتبة أخرى.
- اقتراح السعر المصحَّح.

## Related

- Spec: [F1-S1 — Delivery-Platform Price Consistency](specs/F1-S1-delivery-price-consistency.md)
- Settled decisions that bind this feature: D-2, D-3, D-4 — [intent register §3](../../product/intent-register.md)
