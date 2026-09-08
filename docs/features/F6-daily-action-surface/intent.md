---
ID: F6-INTENT
Title: F6 — Daily Action Surface
Status: Approved
Release: V1
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-NS
Specs: [F6-S1](specs/F6-S1-daily-action-surface.md)
---

# F6 — الشاشة اليومية · Daily Action Surface

> **Migration note.** Content moved verbatim from the pre-migration monolithic
> `intent.md` (preamble — «النجم الثابت»). Nothing was added, removed or reworded. Section numbering from
> the original is kept in the headings so existing citations still resolve.

## Problem

النوايا المنتجة للإشارات تنتج مئات النتائج. بلا حدّ، تعود الشاشة خرطوم إطفاء ولا يُنجز شيء.

## User

مالك المتجر، مرّة كل صباح.

## Solution

> **النجم الثابت:** المدير يفتح شاشة واحدة كل صباح فيرى ماذا يفعل اليوم، مرتّباً بالمال — لا أكثر من 10 إجراءات.

هذه النية مسجَّلة باسم **INT-NS**. سبب تسجيلها نيّةً قائمة بذاتها بدل تكرارها داخل كل مواصفة
مذكور في [سجلّ النوايا (SPEC-000 §1)](../../product/intent-register.md): هي تحكم السلوك عبر كل
نية أخرى.

## Not In Scope

- التقارير عن النتائج عبر الزمن (قدرة أخرى قائمة).
- تنبيه المالك خارج التطبيق.
- إسناد العمل للموظّفين.
- استبدال صفحات التصفّح لكل قدرة.
- قياس التزام المالك.

## Related

- Spec: [F6-S1 — Daily Action Surface](specs/F6-S1-daily-action-surface.md)
- Consumes entries from: F1, F2, F3, F4, F5
- Settled decisions: D-1, D-2, D-3, D-9, D-10 — [intent register §3](../../product/intent-register.md)

## Migration finding

`intent.md` carried this intent as a one-line preamble rather than a numbered section, so
this document is thinner than F1–F5. Nothing was invented to fill it; the requirement
detail lives in [F6-S1](specs/F6-S1-daily-action-surface.md). Recorded in the
[migration report](../../reviews/documentation-structure-migration.md) §6.
