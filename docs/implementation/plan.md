---
ID: PLAN
Title: SmartShelf V1 Implementation Plan
Status: Partial — Phases 0 and 1 written; Phases 2–4 NOT YET CREATED
Version: 1.0 (written 2026-09-08 against System Design v1.0)
Parent: [System Design](../architecture/system-design.md)
Related Specs: F1-S1 … F7-S1 (see the System Design's §21 traceability matrix)
---

> **⚠ Staleness note added by the 2026-09-08 documentation migration — content unchanged.**
> This plan was written against **System Design v1.0**. The design is now **v1.1**: the
> implementation-readiness gate's blocker (ARCH-GATE-001) was closed by
> [ADR-014](../architecture/decisions/ADR-014-a-capability-is-the-smallest-independently-unavailable-unit.md)
> and [ADR-009](../architecture/decisions/ADR-009-stable-entry-identity-via-signal-family.md).
> At least two statements below are therefore superseded and must be refreshed **before
> Phase 0 is executed**:
>
> - the `entry_id` formula (now hashes a permanent `signal_family`, not `capability`);
> - the capability count and registry list (now **seven**, including `hygiene`; `status` is
>   derived from a declared `requires` list).
>
> The migration deliberately did **not** rewrite the plan's content — that is a planning
> act, not a structural one. Recorded as a finding in the
> [migration report](../reviews/documentation-structure-migration.md) §6.

# SmartShelf V1 Implementation Plan — Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build SmartShelf V1 exactly as [`docs/architecture/system-design.md`](../architecture/system-design.md) specifies: one deterministic Python rule engine publishing a single schema-validated artefact, a browser that composes a ≤10-entry daily surface and records owner state, and a reproduction path that is the engine itself.

**Architecture:** Python `src/engine/` owns every figure (six capability modules + surface producer + provenance + publisher). Owner state (answers, outcomes, revivals) is the only mutable store: browser-written to Firestore with a localStorage cache, engine-read at run start and mirrored to a committed JSON. The browser reads `public/data/dashboard.json` (schema v2), applies outcomes, allocation and the bound in a pure `compose()` and computes no business rule.

**Tech Stack:** Python 3.9+ (pyarrow, pyyaml, jsonschema, firebase-admin, rapidfuzz, pytest) · Node 20 / React 19 / Vite 8 / Vitest 4 / Playwright (Chrome) · Firestore · GitHub Actions · Vercel.

**Spec:** [`docs/architecture/system-design.md`](../architecture/system-design.md) (authoritative; §7 components, §9 flows, §10 model, §11 contracts, §14 invariants, §21 traceability, §23 phase order) — derived from [the feature specs](../features/) v1.1 and [the PRD and feature intents](../product/PRD.md).

## Global Constraints

Copied verbatim from `docs/architecture/system-design.md`; every task's requirements implicitly include these.

- Run Python from the repo root with `.venv/bin/python`; `src` is a namespace package (no install step). Never `cd` elsewhere.
- No business rule in JavaScript. The browser holds one pure selection function (`compose`) and no arithmetic over money or quantities. (ADR-001)
- A value is `{amount, kind, certainty}`; `kind ∈ {'per_sale'}` in V1; capabilities with `value_policy: none` may never carry a value. (ADR-012)
- "unavailable", "no comparison", "no figure" and "zero" are four different values; a missing input is `None`, never an empty frame; a missing count is `None`, never `0`. (ARCH-DRIVER-002)
- The engine never writes owner state. The browser is the sole writer. (ADR-003, INV-042)
- Withdrawal is recomputed every run from evidence + owner revivals; the engine owns no persistent state. `withdraw_with_stock = false` is asserted. (ADR-004)
- Negative stock is never clamped anywhere in the engine. (C-32)
- `entry_id = sha256(capability ‖ '|' ‖ barcode ‖ '|' ‖ variant)[:16]`, stable across runs and thresholds. (ADR-009)
- The artefact is written atomically (`.tmp` + rename); the publisher refuses when any capability lacks a status or breaches its money policy. (ADR-005)
- Every count on every page is rendered with its window / vintage / thresholds. (ARCH-DRIVER-007)
- Three languages (ar/he/en) with key parity; no untranslated key; no number split across lines; no horizontal overflow on a phone. (C-53)
- Determinism: same inputs + policy → same artefact except `generated_at`/`run_id`. Sorted iteration everywhere; no clock reads inside capabilities (run time is an input).
- Policy constants live only in `configs/policy.yaml`: `price_policy_pct: 60`, `attention_pct: 100`, `cost_floor_pct: 10`, `freshness_days: 14`, `artefact_min_price: 0.5`, `artefact_cost_ratio: 2`, `max_credible_gap_pct: 300`, `surface: {bound: 10, unvalued_places: 3}`, `question_limit: 3`, `ceiling_derivation: {band_pct: 2, drop_ratio: 0.75, min_band_count: 20}`, `implausible_revenue_share: 0.10`, `full_annual_cycle_months: 12`, `withdraw_with_stock: false`.
- Commit style: small, imperative subject, body explains *why*. Never commit `data/**` except `data/owner/owner_state.json` (CI only) and the existing snapshot rule.

## Plans, in dependency order

| Plan | File | Depends on | Deliverable |
|---|---|---|---|
| Phase 0 — Foundations | [`2026-09-08-v1-01-foundations.md`](phase-0-foundations.md) | — | Contract, policy, owner-state model + pull, ingestion fixes, orchestrator + publisher, CI. **Checkpoint 0-B:** a run publishes a valid artefact with no capabilities; CI green |
| Phase 1 — Capabilities | [`2026-09-08-v1-02-capabilities.md`](phase-1-capabilities.md) | Phase 0 | Six capability modules, surface producer, provenance. Tasks 1a/1b/1c/1d are independent of each other. **Checkpoint 1:** AC tests for SPEC-001…005 pass; publisher assertions hold on real data |
| Phase 2 — Browser | **NOT YET CREATED** | Phase 1 artefact | `loadDashboard`, owner state, `compose`, DailyPage, capability pages, questions, data page, migrations. **Checkpoint 2:** AC-100…AC-112 and e2e invariants pass |
| Phase 3 — Reproduction & gates | **NOT YET CREATED** | Phases 1–2 | `figures.py` as engine print mode, content addressing, V1 signal probes, nightly workflow. **Checkpoint 3:** fresh clone `npm run figures` ≤ 2 min and equals the artefact's `figures{}` |
| Phase 4 — Removal | **NOT YET CREATED** | Checkpoint 3 | Tag `v1-attic`; delete §5.4's list; stop `operational.json`; drop migrations. **Checkpoint 4:** bundle < 500 KB; CI green |

## Prerequisites that are not code (do before Phase 0, Task 0.13 checks them)

1. Firebase: six `VITE_FIREBASE_*` values in `.env` and in Vercel; Anonymous sign-in enabled; `firestore.rules` deployed; `npm run check:firebase-live` exits 0.
2. GitHub secret `FIREBASE_SERVICE_ACCOUNT_JSON` for a **read-only** service account (`roles/datastore.viewer`).
3. Vercel: the PR preview check currently fails with "Deployment was blocked" on account `fadi19` — fix the project's deployment protection so previews build.

## Release conditions (outside implementation; see design.md §22)

- **SPEC-GAP-A** — margin-below-cost has no producing specification; it is built as a browse-only capability and is *not admitted* to the daily surface until SPEC-008 exists.
- **GAP-009** — before withdrawal ships, the owner confirms that absence from a monthly report means no sale (name twenty absent products).
- **GAP-005** — no coverage figure is stated to the owner until `npm run figures` on a fresh clone reproduces it.
