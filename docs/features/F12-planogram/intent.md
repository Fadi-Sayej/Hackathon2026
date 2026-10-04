---
ID: F12-INTENT
Title: F12 — Planogram
Status: Approved — for specification, by the repository owner on 2026-10-03 (D-30)
Release: V4
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-006
Specs: [F12-S1](specs/F12-S1-planogram.md) (Approved 2026-10-04)
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
be unlocked for specification now, with the plan waiting for sales the way F8 does?" with
"unlock":
- **The plan waits for the store's daily sales reports**, and says why, the way F8's order
  pages wait. It is never shown empty or invented (D-23).
- **The owner's own inputs** (shelf photographs, shelf measurements, his arrangement rules)
  would not wait for sales, as the option was put to him.
- **D-13 stands:** no fixed cameras or sensors.

Not decided by D-30:
- building it, which follows his approval of the spec and its mockups;
- a marked example while the plan waits, which needs a decision of its own because D-29
  confines examples to the order pages;
- whether a first version reads shelves from photographs or takes them by hand, for the spec
  to propose and the owner to approve. The PRD's one-day shelf-photograph trial was never run.

The status above records his approval for specification, as F8's did (ca47a35). The banner at
the top describes the state before D-30, and is kept as the record.

## Added 2026-10-04 (not part of the migrated content)

The repository owner approved [F12-S1](specs/F12-S1-planogram.md), answering "Do you approve
the spec as written?" with "approved". It includes the "I've arranged this shelf" record and the
before-and-after measurement he had asked for on 2026-10-04 ("the planogram is real science",
F12-S1 OQ-1206). Building it follows his approval of its plan and its mockups (F12-S1 C-75).

He then approved its build plan, answering "Do you approve the plan and these numbers?" with "yes but i need you to add ai explanation to this also so the ai tells why to organize the shelf this way". That second part is **D-32**: Shelf plan
explains, in an AI's words, why each shelf is arranged as it is. F12-S1 specifies how, for his
approval.
