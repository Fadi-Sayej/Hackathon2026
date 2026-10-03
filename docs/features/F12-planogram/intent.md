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

## Added 2026-10-03 (not part of the migrated content)

The repository owner unlocked this feature for specification as **D-30**, answering "should F12
be unlocked for specification now, with the plan waiting for sales the way F8 does?":
- **The owner's inputs** (shelf photographs, shelf measurements, his arrangement rules) can be
  entered as soon as a store exists.
- **The plan waits for the store's daily sales reports**, and says so. It is never shown empty
  or invented, the way F8's order pages wait (D-23).
- **D-13 stands:** no fixed cameras or sensors.

Not decided by D-30, and left to the spec or to the owner: a marked example while the plan
waits (as D-29 allows the order pages), and whether a first version reads shelves from
photographs or takes them by hand. The PRD's one-day shelf-photograph trial was never run.
The status stays `Registered — not specified` until a spec is approved.
