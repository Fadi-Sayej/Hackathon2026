---
ID: PLAN
Title: SmartShelf V1 Implementation Plan
Status: Partial — Phases 0, 1, 2 and 3 built (Task 2.7's cut-over done 2026-09-12, once ADR-020 removed D-14 as a blocker); Phase 4 written, not started, gated on Checkpoint 3
Version: 1.1 (written 2026-09-08 against System Design v1.0; refreshed the same day against v1.1)
Parent: [System Design](../architecture/system-design.md)
Related Specs: F1-S1 … F7-S1 (see the System Design's §21 traceability matrix)
---

> **Refreshed against System Design v1.1 on 2026-09-08.** The 2026-09-08 documentation
> migration left this plan at v1.0 and recorded the gap as a finding in the
> [migration report](../reviews/documentation-structure-migration.md) §6. That refresh has
> now been made, so the plan and the design say the same thing:
>
> - `entry_id` hashes a permanent `signal_family`, never the capability id
>   ([ADR-009](../architecture/decisions/ADR-009-stable-entry-identity-via-signal-family.md));
>   the eleven family strings are frozen in Task 0.2 before anything downstream starts.
> - `hygiene` is its own registered capability with its own `requires`; the registry holds
>   **seven** ids and `status` is derived from `requires`, never hand-declared
>   ([ADR-014](../architecture/decisions/ADR-014-a-capability-is-the-smallest-independently-unavailable-unit.md)).
> - `capabilities{}` in the artefact is exactly the registry id set; `catalogue_lifecycle`
>   and `owner_questions` publish inside it, not as top-level blocks.
> - The rule-12 independence probe (design §14, §18) is Task 1.9 — the boundary test a unit
>   test structurally cannot replace. It drives `run_engine` over a copy of the data with the
>   monthly reports withheld at source and reads the published artefact, so it crosses
>   `inputs.py`, `run.py` and the publisher. Its CI home is `collect-daily.yml` beside
>   `check:signals` (Phase 3), not `ci.yml`, which runs without `data/**`.
> - Commands are `python3`, not `.venv/bin/python`: there is no virtualenv in this
>   repository (CLAUDE.md rule 2), and every existing `npm` script already uses `python3`.
>
> Two §18 actions from the [readiness gate](../reviews/system-design-readiness.md) are also
> applied here: the Basic Auth credentials join the prerequisites (ARCH-GATE-011), and
> `inputs.py` is named as the single producer of the effective cost price (ARCH-GATE-007).

# SmartShelf V1 Implementation Plan — Index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build SmartShelf V1 exactly as [`docs/architecture/system-design.md`](../architecture/system-design.md) specifies: one deterministic Python rule engine publishing a single schema-validated artefact, a browser that composes a ≤10-entry daily surface and records owner state, and a reproduction path that is the engine itself.

**Architecture:** Python `src/engine/` owns every figure (seven registered capabilities across six modules — `reconciliation.py` publishes both `reconciliation` and `hygiene` (ADR-014) — plus surface producer, provenance and publisher). Owner state (answers, outcomes, revivals) is the only mutable store: browser-written to Firestore with a localStorage cache, engine-read at run start and mirrored to a committed JSON. The browser reads `public/data/dashboard.json` (schema v2), applies outcomes, allocation and the bound in a pure `compose()` and computes no business rule.

**Tech Stack:** Python 3.9+ (pyarrow, pyyaml, jsonschema, firebase-admin, rapidfuzz, pytest) · Node 20 / React 19 / Vite 8 / Vitest 4 / Playwright (Chrome) · Firestore · GitHub Actions · Vercel.

**Spec:** [`docs/architecture/system-design.md`](../architecture/system-design.md) (authoritative; §7 components, §9 flows, §10 model, §11 contracts, §14 invariants, §21 traceability, §23 phase order) — derived from [the feature specs](../features/) v1.1 and [the PRD and feature intents](../product/PRD.md).

## Global Constraints

Copied verbatim from `docs/architecture/system-design.md`; every task's requirements implicitly include these.

- Run Python from the repo root with `python3`; there is no virtualenv (CLAUDE.md rule 2), and `src` is a namespace package with no install step. Never `cd` elsewhere. Note that `setup.sh`'s `pip install --break-system-packages` does **not** work on this machine's pip (21.2.4; the flag arrived in 23.0.1) — every dependency the plan needs is already installed, so no task should call it.
- No business rule in JavaScript. The browser holds one pure selection function (`compose`) and no arithmetic over money or quantities. (ADR-001)
- A value is `{amount, kind, certainty}`; `kind ∈ {'per_sale'}` in V1; capabilities with `value_policy: none` may never carry a value. (ADR-012)
- "unavailable", "no comparison", "no figure" and "zero" are four different values; a missing input is `None`, never an empty frame; a missing count is `None`, never `0`. (ARCH-DRIVER-002)
- The engine never writes owner state. The browser is the sole writer. (ADR-003, INV-042)
- Withdrawal is recomputed every run from evidence + owner revivals; the engine owns no persistent state. `withdraw_with_stock = false` is asserted. (ADR-004)
- Negative stock is never clamped anywhere in the engine. (C-32)
- `entry_id = sha256(signal_family ‖ '|' ‖ barcode ‖ '|' ‖ variant)[:16]`, stable across runs, thresholds **and any future re-carving of capabilities**. `signal_family` is one of eleven permanent strings, never renamed or reused; the routing `capability` id travels beside it as a mutable field. (ADR-009)
- A capability is the smallest unit that can independently become unavailable; the registry holds seven ids including `hygiene`, and each declares `requires`. `status` is **derived** from `requires` against the inputs that landed — a capability may never declare itself available over a missing input. (ADR-014)
- The artefact is written atomically (`.tmp` + rename); the publisher refuses when any capability lacks a status or breaches its money policy. (ADR-005)
- Every count on every page is rendered with its window / vintage / thresholds. (ARCH-DRIVER-007)
- Three languages (ar/he/en) with key parity; no untranslated key; no number split across lines; no horizontal overflow on a phone. (C-53)
- Determinism: same inputs + policy → same artefact except `generated_at`/`run_id`. Sorted iteration everywhere; no clock reads inside capabilities (run time is an input).
- The three rule definitions the readiness gate left open are declared as provisional policy, not invented in code: `question_money_basis` (ARCH-GATE-002 — §18 action 3), `uncomparable_min_barcode_digits` (ARCH-GATE-004 — action 4), and the ceiling's population, derived **after** the FR-074 withdrawn exclusion and published with the figure (ARCH-GATE-006 — action 5).
- Policy constants live only in `configs/policy.yaml`: `price_policy_pct: 60`, `attention_pct: 100`, `cost_floor_pct: 10`, `freshness_days: 14`, `artefact_min_price: 0.5`, `artefact_cost_ratio: 2`, `max_credible_gap_pct: 300`, `surface: {bound: 10, unvalued_places: 3, unvalued_order: [reconciliation, competitor_position, catalogue_lifecycle, hygiene]}`, `question_limit: 3`, `question_money_basis: window_revenue_at_shelf_price`, `question_yield_factor: 1.0`, `uncomparable_min_barcode_digits: 8`, `ceiling_derivation: {band_pct: 2, drop_ratio: 0.75, min_band_count: 20}`, `implausible_revenue_share: 0.10`, `full_annual_cycle_months: 12`, `withdraw_with_stock: false`.
- Commit style: small, imperative subject, body explains *why*. Never commit `data/**` except `data/owner/owner_state.json` (CI only) and the existing snapshot rule.

## Plans, in dependency order

| Plan | File | Depends on | Deliverable |
|---|---|---|---|
| Phase 0 — Foundations | [`2026-09-08-v1-01-foundations.md`](phase-0-foundations.md) | — | Contract, policy, owner-state model + pull, ingestion fixes, orchestrator + publisher, CI. **Checkpoint 0-B:** a run publishes a valid artefact with no capabilities; CI green |
| Phase 1 — Capabilities | [`2026-09-08-v1-02-capabilities.md`](phase-1-capabilities.md) | Phase 0 | Seven capabilities in six modules, surface producer, provenance, the rule-12 independence probe. Tasks 1a/1b/1c/1d are independent of each other. **Checkpoint 1:** AC tests for SPEC-001…005 pass; publisher assertions hold on real data; the probe passes with `sales_monthly` withheld |
| Phase 2 — Browser ✅ *(cut-over deferred)* | [`phase-2-browser.md`](phase-2-browser.md) | Phase 1 artefact | `loadDashboard`, owner state, `compose`, DailyPage, capability pages, questions, data page, migrations. **Checkpoint 2:** AC-100…AC-112 and e2e invariants pass |
| Phase 3 — Reproduction & gates | [`phase-3-reproduction.md`](phase-3-reproduction.md) | Phases 1–2 | `figures.py` as engine print mode, content addressing, V1 signal probes, nightly workflow. **Checkpoint 3:** fresh clone `npm run figures` ≤ 2 min and equals the artefact's `figures{}` |
| Phase 4 — Removal | [`phase-4-removal.md`](phase-4-removal.md) | Checkpoint 3 | Tag `v1-attic`; delete §5.4's list; stop `operational.json`; drop migrations. **Checkpoint 4:** bundle < 500 KB; CI green |

## Prerequisites that are not code (do before Phase 0, Task 0.13 checks them)

1. Firebase: six `VITE_FIREBASE_*` values in `.env` and in Vercel; Anonymous sign-in enabled; `firestore.rules` deployed; `npm run check:firebase-live` exits 0.
2. GitHub secret `FIREBASE_SERVICE_ACCOUNT_JSON` for a **read-only** service account (`roles/datastore.viewer`).
3. ~~Vercel: the PR preview check currently fails with "Deployment was blocked" on account
   `fadi19`.~~ **Resolved — verified 2026-09-13.** `Vercel` and `Vercel Preview Comments`
   both report SUCCESS on PRs #61, #81 and #85.
4. Basic Auth: `BASIC_AUTH_USER` and `BASIC_AUTH_PASSWORD` set in Vercel for every environment. `middleware.ts` fails closed with 503 when they are unset (design §11.7), so an unset pair takes the pilot app down rather than exposing it — ARCH-GATE-011, readiness gate §18 action 10.

## Release conditions (outside implementation; see design.md §22)

- **SPEC-GAP-A** — margin-below-cost has no producing specification; it is built as a browse-only capability and is *not admitted* to the daily surface until SPEC-008 exists.
- **GAP-009** — before withdrawal ships, the owner confirms that absence from a monthly report means no sale (name twenty absent products).
- **GAP-005** — no coverage figure is stated to the owner until `npm run figures` on a fresh clone reproduces it.
- **GAP-011** — the 18% ceiling is derived from the owner's behaviour, not confirmed as his
  policy. Still worth asking, no longer a gate: `policy.owner_declared_ceiling_pct` accepts
  his answer when it comes, publishes both numbers, and notes when they differ.
- ~~**Owner outcomes are keyed on `signal_family`, but the outcome *snapshot* is not.**~~
  **Settled by [ADR-016](../architecture/decisions/ADR-016-outcome-snapshot-carries-the-signal-family.md)**
  on 2026-09-12: the snapshot carries `signal_family`, the System Design §9.3 and §10.3 are
  edited, and Phase 2 Task 2.1 refuses an outcome without it.
- **ARCH-GATE-003 (INT-MEAS)** — the pilot's own 30-day go/no-go number (PRD §8) has no V1
  delivery: the design removes the telemetry surface that SPEC-000 §4 relied on and builds
  nothing in its place. Either F13 is specified before V1 ships, or the team states on 12/9
  that the number will not compute itself. Carried here from the readiness gate §18 action
  11, which the System Design has not yet recorded in its own §23 release conditions.
