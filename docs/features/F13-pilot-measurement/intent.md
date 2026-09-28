---
ID: F13-INTENT
Title: F13 — Pilot Measurement (30-day recovered ₪)
Status: Approved — specified as F13-S1, which the repository owner approved on 2026-09-28
Release: V1 (the pilot's own decision criterion)
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-MEAS
Specs: [F13-S1](specs/F13-S1-pilot-measurement.md) (Approved 2026-09-28)
Updated: 2026-09-28
---

# F13 — رقم النجاح · Pilot Measurement

> **Added 2026-09-27 (not part of the migrated content).** The pilot with the YomYom store
> ended (D-23) without its three numbers: the success figure, the price and the data
> cadence. F13 waits for another store's owner to state them.

> **Added 2026-09-27 (not part of the migrated content).** Later the same day, **D-24**: there
> is no success number, so F13 measures how much success there is and sets no figure to reach;
> and the subscription price will be discussed later. Only the data cadence still waits for
> another store's owner.

> **Status: registered, deliberately NOT specified — for a different reason from F9–F12.**
> [SPEC-000 §4](../../product/intent-register.md#4-intents-deliberately-not-specified-in-this-phase)
> declines to specify it because `intent.md` §11.1 states it is *already measured by an
> existing surface*, so no new capability was being designed. Content below is verbatim
> from `intent.md` §11.

## Problem

بعد 30 يوماً من V1، كم ₪ مستردّة تجعل التجربة ناجحة — ومَن يقيسها.

## User

المالك والفريق معاً، في قرار الاستمرار.

## Solution

**ثلاثة أرقام تُحسم قبل كتابة سطر كود إضافي:**

1. **رقم النجاح:** بعد 30 يوماً من V1، كم ₪ مستردّة (أسعار مصحّحة + مخزون مفسّر + كتالوج منظّف) تجعلها ناجحة؟ القياس آلي عبر شاشة القياس المبنية.
2. **سعر الاشتراك إن نجحت:** يُتّفق عليه **اليوم** ويبدأ تلقائياً عند تحقّق الرقم. الالتزام المسبق هو التحقّق الحقيقي — تجربة مجانية بلا سعر متفق عليه تقيس المجاملة لا القيمة.
3. **إيقاع البيانات:** يومي أم أسبوعي، ومن يرسله.

**وبعد 30 يوماً، الجواب واحد من ثلاثة:** الرقم تحقّق → اشتراك ونكمل · لم يتحقّق لكن الاستخدام يومي → نراجع النوايا معه · لا استخدام → نتوقّف بشرف، وقد خسرنا شهراً لا سنة.

## Open obligations already recorded

- Whatever that surface states is a figure, so **F7-S1 governs it in full** — provenance,
  reproduction, and no figure rather than zero.
- Its money component «مخزون مفسّر» **cannot be expressed in money** under D-1 and
  F2-S1 FR-023. What it may contain instead is **OQ-801 (P1)** in
  [gaps and open questions](../gaps-and-open-questions.md).

## Migration finding — unresolved, carried forward

The System Design removes the telemetry surface that SPEC-000 §4 relies on, and builds no
replacement ([System Design §5.4](../../architecture/system-design.md)). This is recorded
as **ARCH-GATE-003 (MAJOR, open)** in the
[implementation readiness gate](../../reviews/system-design-readiness.md). It is a product
decision for the specification layer and was **not** resolved by the documentation
migration.
