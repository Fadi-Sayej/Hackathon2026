---
ID: F12-INTENT
Title: F12 — Planogram
Status: Registered — not specified
Release: V4
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-006
Specs: none
---

# F12 — رتّب رفوفي لأربح أكثر · Planogram

> **Status: registered, deliberately NOT specified.** See
> [SPEC-000 §4](../../product/intent-register.md#4-intents-deliberately-not-specified-in-this-phase).
> Content below is verbatim from the approved intent layer (`intent.md` §1 row and §9.7).

## Problem

«رتّب رفوفي لأربح أكثر».

## What is at stake

+20–68% هامش لكل متر خطّي.

## Data today

❌ — تحتاج صورة الرف + طلب V2 + قواعده.

## Not In Scope — permanently

**مراقبة رف لحظية بحسّاسات أو كاميرات مثبّتة** — مشروع عتاد لا يحمله فريق من اثنين.
**مقتولة، لا مؤجّلة** (`intent.md` §9.1, recorded as **D-13**).

Deferring F12 does **not** reopen D-13: when this feature is finally specified, the sensor
and fixed-camera approach remains permanently excluded, not merely postponed.

## Framing commitment

**والبلانوغرام يُعرض كخطة مؤرّخة بشروطها — لا كميزة جاهزة** رغم أن العرض التجريبي يعمل
(`intent.md` §9.7).

## Blocking dependencies

Three inputs that do not exist yet: shelf photographs with dimensions, real demand from
F8, and the owner's own arrangement rules.

## Related

- The V1 build removes the working planogram demo to a `v1-attic` git tag
  ([System Design §5.4](../../architecture/system-design.md)).
