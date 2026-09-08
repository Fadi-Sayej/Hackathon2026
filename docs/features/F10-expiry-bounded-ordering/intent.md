---
ID: F10-INTENT
Title: F10 — Expiry-Bounded Ordering
Status: Registered — not specified
Release: V2 (promoted from V3)
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-007
Specs: none
---

# F10 — كم أطلب حتى لا يتلف؟ · Expiry-Bounded Ordering

> **Status: registered, deliberately NOT specified.** No `F#-S#` document exists for
> this feature and none may be written until the product decisions named below are
> taken. The reason is recorded in
> [SPEC-000 §4](../../product/intent-register.md#4-intents-deliberately-not-specified-in-this-phase),
> and it is not scheduling: writing requirements now would mean inventing those answers.
> Content moved verbatim from the pre-migration `intent.md` (§7); nothing added.

## Problem

«كم أطلب حتى لا يتلف؟» — يحدّ كل توصيات V2.

## User

مالك المتجر وطاقمه.

## Solution (direction only)

**كانت في V3 كميزة لاحقة. تصير في V2 لأنها تحدّ توصيات الطلب نفسها.**

توصية "اطلب 80 وحدة" بلا معرفة الصلاحية توصية ناقصة: الرقم الصحيح هو **أقل من (ما يبيعه قبل التلف) و(ما يحتاجه)**. بدونها نوصي بكميات تتحوّل هدراً — وهذا يضرب مصداقية V2 كلها في أول طلبية فاسدة.

**زمنها تقويمي لا هندسي:** ~3 أيام هندسة (الشاشة جاهزة)، ثم **30 يوم تسجيل من طاقمه** حتى تتراكم بيانات كافية. لذلك تبدأ **يوم 12/9 نفسه**، بالتوازي مع V1، لا بعده.

## Blocking dependency

بيانات الصلاحية لا توجد قبل أن يسجّل الطاقم الاستلام لثلاثين يوماً. الزمن **تقويمي لا هندسي**.

## Related

- Bounds F8's quantities.
- The receiving/expiry capture screen stays in the V1 product **only** to start the 30-day
  counter on 12/9; it produces V2 data and V1 reads none of it
  ([System Design §5.1, §8](../../architecture/system-design.md)).
