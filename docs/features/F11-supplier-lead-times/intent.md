---
ID: F11-INTENT
Title: F11 — Supplier Lead Times
Status: Registered — not specified
Release: V3
Parent: [PRD](../../product/PRD.md)
Intent IDs: INT-008
Specs: none
---

# F11 — متى يصل كل مورّد فعلاً؟ · Supplier Lead Times

> **Status: registered, deliberately NOT specified.** See
> [SPEC-000 §4](../../product/intent-register.md#4-intents-deliberately-not-specified-in-this-phase).
> The only content the approved intent layer carries for this feature is its row in the
> intent table; it is reproduced below verbatim and nothing was added.

## Problem

«متى يصل كل مورّد فعلاً؟» — مهلة حقيقية بدل الافتراض.

## Data today

❌ — تُقاس بعد **3 تسليمات لكل مورّد**.

## Decision produced

مهلة حقيقية بدل الافتراض.

## What is at stake

دقّة توصيات V2.

## Blocking dependency

`intent.md` §1 notes the timeline is calendar-bound, not engineering-bound: three observed
deliveries per supplier must accumulate first.

## Migration finding

This feature's intent content in the approved layer is a single table row. Nothing was
invented to expand it. Recorded in the
[migration report](../../reviews/documentation-structure-migration.md) §6.
