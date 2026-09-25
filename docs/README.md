# SmartShelf — Documentation Map

One canonical source per artifact type. If two documents disagree, the one **higher** in
the chain wins.

```
PRD                     what the product is, for whom, and what is out of scope
 └─ Feature Intents     why each feature exists
     └─ Feature Specs   what each feature must observably do
         └─ System Design   how the whole system satisfies all approved specs
             └─ ADRs         the architecture decisions the design made
                 └─ Implementation Plan   in what order it gets built
                     └─ Implementation    the code
```

## Authority hierarchy

1. [**PRD**](product/PRD.md) — and the settled decisions D-1 … D-22 in the [intent register](product/intent-register.md) §3
2. [**Feature Intents**](features/) — `features/F#-*/intent.md`
3. [**Approved Feature Specs**](features/) — `features/F#-*/specs/F#-S#-*.md`
4. [**System Design**](architecture/system-design.md) — the single authoritative architecture
5. [**ADRs**](architecture/decisions/) — ADR-001 … ADR-028
6. [**Implementation Plan**](implementation/plan.md)
7. **Code** — evidence of what exists, never product authority

Anything under [`archive/`](archive/) is **LEGACY — NON-AUTHORITATIVE**. Every file there
carries a banner saying so.

---

## Product

| Document | What it is |
|---|---|
| [PRD](product/PRD.md) | Problem · user · feature register (F1–F14) · releases · not-in-scope · owner commitments · decision criterion · figures · open decisions |
| [Release phases](product/release-phases.md) | Three customer-facing delivery phases with dates · **proposes a change to PRD §5's dates, does not take it** |
| [Intent register (SPEC-000)](product/intent-register.md) | INT-id ↔ spec map · **settled decisions D-1 … D-22** · why F9–F14 are deliberately unspecified |
| [Open decisions](product/open-decisions/) | One brief per feature blocked on a product decision · poses the choices the data supports · **not authority** — answers land as `D-n` in the intent register §3, then the brief is `Superseded` |

## Features

Specs are organised by feature. Requirement ids (`FR-…`, `INV-…`, `NFR-…`, `AC-…`) are
globally unique across the specification layer and were **not** renumbered by the
2026-09-08 migration.

| Feature | Intent | Spec | Release |
|---|---|---|---|
| F1 — Delivery-Platform Price Consistency | [intent](features/F1-delivery-price-consistency/intent.md) | [F1-S1](features/F1-delivery-price-consistency/specs/F1-S1-delivery-price-consistency.md) | V1 |
| F2 — Stock Truth | [intent](features/F2-stock-truth/intent.md) | [F2-S1](features/F2-stock-truth/specs/F2-S1-stock-reconciliation-and-hygiene.md) | V1 |
| F3 — Competitor Price Position | [intent](features/F3-competitor-price-position/intent.md) | [F3-S1](features/F3-competitor-price-position/specs/F3-S1-competitor-price-position.md) | V1 |
| F4 — Catalogue Lifecycle | [intent](features/F4-catalogue-lifecycle/intent.md) | [F4-S1](features/F4-catalogue-lifecycle/specs/F4-S1-catalogue-lifecycle.md) | V1 |
| F5 — Owner Knowledge Capture | [intent](features/F5-owner-knowledge-capture/intent.md) | [F5-S1](features/F5-owner-knowledge-capture/specs/F5-S1-owner-knowledge-capture.md) | V1 |
| F6 — Daily Action Surface | [intent](features/F6-daily-action-surface/intent.md) | [F6-S1](features/F6-daily-action-surface/specs/F6-S1-daily-action-surface.md) | V1 |
| F7 — Figure Provenance | [intent](features/F7-figure-provenance/intent.md) | [F7-S1](features/F7-figure-provenance/specs/F7-S1-figure-provenance.md) | V1 |
| F8 — Order Quantity | [intent](features/F8-order-quantity/intent.md) | [F8-S1](features/F8-order-quantity/specs/F8-S1-order-quantity.md) — `Ready for review` | V2 |
| F9 — Assortment Gap | [intent](features/F9-assortment-gap/intent.md) | *not specified* | V2 |
| F10 — Expiry-Bounded Ordering | [intent](features/F10-expiry-bounded-ordering/intent.md) | *not specified* | V2 |
| F11 — Supplier Lead Times | [intent](features/F11-supplier-lead-times/intent.md) | *not specified* | V3 |
| F12 — Planogram | [intent](features/F12-planogram/intent.md) | *not specified* | V4 |
| F13 — Pilot Measurement | [intent](features/F13-pilot-measurement/intent.md) | [F13-S1](features/F13-pilot-measurement/specs/F13-S1-pilot-measurement.md) — **`Blocked`** | V1 |

Cross-feature register: [**gaps, open questions and assumptions (SPEC-GAPS)**](features/gaps-and-open-questions.md)
— `GAP-…`, `OQ-…`, `ASM-…`.

## Architecture

- [**System Design**](architecture/system-design.md) — one document, system-level, answering
  all seven approved specs as one coherent system. Not owned by any feature.
- [**ADRs**](architecture/decisions/) — ADR-001 … ADR-028, one file each.

| ADR | Decision |
|---|---|
| [ADR-001](architecture/decisions/ADR-001-one-rule-engine-in-python.md) | One rule engine, in Python; the browser computes no business rule |
| [ADR-002](architecture/decisions/ADR-002-reproduction-is-the-engine-in-print-mode.md) | Reproduction is the engine in print mode |
| [ADR-003](architecture/decisions/ADR-003-owner-state-in-firestore-browser-written.md) | Owner state in Firestore, written only by the browser, pulled by the engine |
| [ADR-004](architecture/decisions/ADR-004-catalogue-lifecycle-recomputed-every-run.md) | Catalogue lifecycle recomputed every run; the engine owns no persistent state |
| [ADR-005](architecture/decisions/ADR-005-typed-capability-contract-and-one-artefact.md) | A typed capability contract and one schema-validated artefact |
| [ADR-006](architecture/decisions/ADR-006-surface-composition-is-a-pure-browser-function.md) | Surface composition is a pure browser function over engine candidates |
| [ADR-007](architecture/decisions/ADR-007-static-site-nightly-ci-no-runtime-server.md) | Static site, nightly CI, no runtime server |
| [ADR-008](architecture/decisions/ADR-008-store-format-affinity-enforced-in-the-engine.md) | Store-format affinity enforced in the engine |
| [ADR-009](architecture/decisions/ADR-009-stable-entry-identity-via-signal-family.md) | Entry identity is a permanent `signal_family`, not the capability id |
| [ADR-010](architecture/decisions/ADR-010-demo-catalogue-and-normalize-data-leave-the-product.md) | The generated demo catalogue and `normalize:data` leave the product |
| [ADR-011](architecture/decisions/ADR-011-evidence-semantics-no-row-is-recorded.md) | Evidence semantics: `no_row` is recorded, and classification states it |
| [ADR-012](architecture/decisions/ADR-012-money-is-a-typed-value-with-a-declared-policy.md) | Money is a typed value with a declared per-capability policy |
| [ADR-013](architecture/decisions/ADR-013-tests-run-before-merge.md) | Tests run before merge |
| [ADR-014](architecture/decisions/ADR-014-a-capability-is-the-smallest-independently-unavailable-unit.md) | A capability is the smallest independently-unavailable unit; hygiene is one |
| [ADR-015](architecture/decisions/ADR-015-ceiling-is-the-densest-qualifying-collapse.md) | The markup ceiling is the densest qualifying collapse, not the last |
| [ADR-016](architecture/decisions/ADR-016-outcome-snapshot-carries-the-signal-family.md) | The owner-outcome snapshot carries the signal family |
| [ADR-017](architecture/decisions/ADR-017-a-run-states-whether-its-sales-evidence-arrived.md) | A run states whether its sales evidence arrived |
| [ADR-018](architecture/decisions/ADR-018-the-browser-does-not-ship-a-schema-validator.md) | The browser does not ship a schema validator |
| [ADR-019](architecture/decisions/ADR-019-a-conflicting-duplicate-barcode-is-a-hygiene-record.md) | A conflicting duplicate barcode is a hygiene record, never a silent pick |
| [ADR-020](architecture/decisions/ADR-020-the-published-population-is-a-policy-not-a-constant.md) | The published population is a policy setting, not a constant |
| [ADR-021](architecture/decisions/ADR-021-the-artefact-states-how-many-devices-wrote-owner-state.md) | The artefact states how many devices have written owner state, and when |
| [ADR-022](architecture/decisions/ADR-022-a-barcode-less-row-is-identified-by-its-name.md) | A barcode-less row is identified by its name, under ADR-019's rule; amends one sentence of ADR-019 |
| [ADR-023](architecture/decisions/ADR-023-the-engine-publishes-the-pilot-measurement.md) | The engine publishes the pilot measurement; the browser renders it — **`Ready for review`** |
| [ADR-024](architecture/decisions/ADR-024-the-catalogue-is-published-beside-the-artefact.md) | The product catalogue is published beside the artefact, not inside it — accepted 2026-09-17 |
| [ADR-025](architecture/decisions/ADR-025-the-comparison-behind-the-finding-is-published.md) | The comparison behind a competitor finding is published, not only the finding — accepted 2026-09-22 |
| [ADR-026](architecture/decisions/ADR-026-reconciliation-publishes-the-span-it-reconciled.md) | The reconcile window is cut once per run, at the run's own stock date, and reconciliation publishes that cut — accepted 2026-09-23 |
| [ADR-027](architecture/decisions/ADR-027-a-question-whose-money-is-unknown-carries-no-figure.md) | A question whose money is unknown carries no figure, and ranks after every question that has one — accepted 2026-09-24 |
| [ADR-028](architecture/decisions/ADR-028-the-nav-is-the-owners-and-only-unshipped-code-leaves.md) | The nav is the owner's, and §20.1 removes only the code no screen runs — accepted 2026-09-24 |

ADR-001 … ADR-022 and ADR-024 … ADR-028 are `Accepted`. ADR-023 is `Ready for review`. ADR-022 amends a sentence of ADR-019 and was accepted on 2026-09-13, after the defect it fixes was verified end to end: `entry_id` falls back to `product_name`, and `compose.js` skips any entry whose id carries a settled outcome, so two barcode-less rows sharing a name settled together on the owner's screen. ADR-020 was accepted on 2026-09-13 **conditional on GAP-009**:
`published_population: whole` is the right value while that question is open, and becomes
`living` when it closes.

## Quality gates

| Gate | Verdict |
|---|---|
| [Intent → Spec conformance](reviews/intent-spec-conformance.md) | CONDITIONAL PASS (run 2) |
| [System Design → Implementation readiness](reviews/system-design-readiness.md) | CONDITIONAL PASS (run 3, 2026-09-13) — 0 blockers, **1 MAJOR open** (ARCH-GATE-003). GATE-002 and GATE-004 closed against the built artefact |
| [Documentation structure migration](reviews/documentation-structure-migration.md) | see report |
| [F2 — stock reconciliation and hygiene](reviews/F2-validation.md) | conformance PASS (10/10) · fidelity PASS · usefulness 3 of 10 daily places; 2 findings |
| [Nav reachability 2026-09-21](reviews/nav-reachability-2026-09-21.md) | **OPEN** — `CapabilityPage` is unrouted, so FR-102/C-51/AC-110 are discharged by nothing and **1,638 of 3,380 published findings are reachable from no screen**. Wants an ADR on §20.1 versus the restore |
| [Nightly incident 2026-09-13](reviews/nightly-2026-09-13-incident.md) | FIXED — the nightly published the owner's artefact and never committed it; all 6 findings closed |

## Implementation

[**Plan**](implementation/plan.md) v1.1 — refreshed against System Design v1.1 on
2026-09-08 and reviewed by a five-advisor council before it was committed. Phases 0, 1, 2
and 3 are **built**; Phase 4 is **written, not started** — see its own status header for
what gates it.

- [Phase 0 — Foundations](implementation/phase-0-foundations.md) — the typed contract,
  policy loader, owner-state model + Firestore pull, ingestion fixes, the engine
  orchestrator and atomic publisher, CI.
- [Phase 1 — Capabilities](implementation/phase-1-capabilities.md) — the seven registered
  capabilities across six modules, the surface producer, provenance, and Task 1.9's
  rule-12 independence probe.
- [Phase 2 — Browser](implementation/phase-2-browser.md) — `loadDashboard`, owner state,
  `compose`, `DailyPage` and the capability pages. Task 2.7's cut-over shipped **2026-09-12**
  once [ADR-020](architecture/decisions/ADR-020-the-published-population-is-a-policy-not-a-constant.md)
  removed D-14 as a blocker: the owner's screen has read `dashboard.json` (schema 2) since,
  not `operational.json`.
- [Phase 3 — Reproduction & gates](implementation/phase-3-reproduction.md) — `figures.py` as
  the engine's print mode, content addressing, the V1 signal probes, the nightly workflow.
- [Phase 4 — Removal](implementation/phase-4-removal.md) — **not started, deliberately.**
  Deletes the old demo/V2/planogram/LLM/MCP chain and `operational.json` once Checkpoint 3
  is green (two consecutive clean scheduled nightlies — one so far) and three open
  questions (P4-OQ-1 … P4-OQ-3) are answered.

## Operations (not product authority)

How the system is run and why its data survives. True today, but outside the authority
chain above.

| Document | What it is |
|---|---|
| [Deployment](operations/deployment.md) | Vercel release runbook: build, env, the Basic-Auth gate, what must be committed |
| [Snapshot durability](operations/snapshot-durability.md) | Why the daily market snapshot is committed and what a lost day costs |
| [Receiving ledger](operations/receiving-ledger.md) | The `received` term the POS never records: operator flow, CSV shape, lead times |

## Pilot (what reaches the store owner)

| Document | What it is |
|---|---|
| [Handover — Arabic](pilot/handover-yomyom-ar.md) | **The version actually handed over.** Arabic is the language of every exchange with the manager |
| [Handover — English](pilot/handover-yomyom-en.md) | Source text for the Arabic handover; keep the two in sync |
| [Owner conversation — 2026-09](pilot/owner-conversation-2026-09.md) | **The current one.** Eight questions: GAP-009 (and the evidence that its assumption is wrong), GAP-011, the three numbers F13-S1 is blocked on, and the two facts F8-S1 needs |
| [Questions for YomYom](pilot/questions-for-yomyom.md) | The August pilot-setup questions, each drawn from his own export. Superseded for the 09-2026 conversation by the row above |
| [Release phases — Arabic](pilot/release-phases-ar.html) | **The version shown to the owner on 12/9.** Three dated phases, each a working product |
| [`app-qr.png`](pilot/app-qr.png) · [`app-share-qr.png`](pilot/app-share-qr.png) | QR codes for the deployed pilot app |

## Sources

| Document | What it is |
|---|---|
| [Alonit signal source](sources/alonit_signal_source.md) | What the Dor Alon price-transparency feed and the Wolt catalogue provide, and what they cannot prove |

## Archive — LEGACY, NON-AUTHORITATIVE

Nothing under [`archive/`](archive/) is authority; every file carries a banner.

| Folder | What it holds |
|---|---|
| [`archive/`](archive/) | The pre-design architecture trace, superseded per-person track notes, sprint plans and audits |
| [`archive/pre-pivot/`](archive/pre-pivot/) | The hackathon and demo era: demo scripts, judge Q&A, QA checklists, the old PRD and acceptance criteria |
| [`archive/plans/`](archive/plans/) | Executed implementation plans |
| [`archive/business-material/`](archive/business-material/) | Pitch deck, incubation-programme material and market research (`.docx`/`.pdf`) |
