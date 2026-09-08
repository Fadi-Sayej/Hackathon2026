---
ID: F5-INTENT
Title: F5 — Owner Knowledge Capture
Status: Approved
Release: V1
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-010
Specs: [F5-S1](specs/F5-S1-owner-knowledge-capture.md)
---

# F5 — أكمل بياناتي الناقصة بأقل إزعاج · Owner Knowledge Capture

> **Migration note.** Content moved verbatim from the pre-migration monolithic
> `intent.md` (§5). Nothing was added, removed or reworded. Section numbering from
> the original is kept in the headings so existing citations still resolve.

## Problem

«أكمل بياناتي الناقصة — بأقل إزعاج».

## User

مالك المتجر — الوحيد الذي يملك الجواب.

## Solution

**1,270 صنفاً بلا سعر تكلفة (17% من الكتالوج).** وهذا يعمينا مالياً عنها تماماً: الهامش، قيمة المخزون المفقود، ربحية الرف — كلها تحتاج التكلفة. **صنف منها يبيع بخسارة لن يظهر في أي شاشة.**

**لكن السؤال لا يذهب إلى المالك 1,270 مرة.** بتقاطعها مع النية 9:

| | العدد | ماذا نفعل |
|---|---|---|
| بلا تكلفة **وميتة ومخزونها صفر** | **1,253** | 🗑️ تُحذف مع النية 9 — **لا سؤال** |
| بلا تكلفة وميتة وعليها مخزون | 5 | ⏸️ **لا يُسأل عنها** — راكدة، والسؤال يُعاد تقييمه إن باعت |
| **بلا تكلفة وحيّة (تبيع فعلاً)** | **12** | ✅ **هذه وحدها نسأل عنها** |

**12 سؤالاً، لا 1,270.** يجيب عليها في دقيقتين. وأكبرها `שטיפה פסח` (باع 186 وحدة) و`תפוצ'יפס ברביקיו` (84 وحدة).

**والصيغة تتبع قاعدة الأسئلة المبنية في `src/lib/questions/`: ثلاثة أسئلة على الشاشة كحدّ أقصى**، مرتّبة بـ«المال × كم صنفاً يصلحه الجواب». الرابع يحوّلها استمارة، والاستمارة تُهجر.

## Not In Scope

- بناء واجهة إدخال بيانات عامة للكتالوج.
- تغطية التكلفة الكاملة كهدف بحدّ ذاته.
- أي سؤال لا يغيّر مخرجاً.

## Related

- Spec: [F5-S1 — Owner Knowledge Capture](specs/F5-S1-owner-knowledge-capture.md)
- Settled decisions: D-3, D-8 — [intent register §3](../../product/intent-register.md)
