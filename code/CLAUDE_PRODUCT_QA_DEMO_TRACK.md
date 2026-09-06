# SmartShelf AI — Claude Product, QA, and Demo Track

## Role

This file is for Claude only.

Claude owns product clarity, QA, demo readiness, judge-facing explanations, acceptance criteria, roadmap, and pitch materials.

Codex owns implementation. Claude should not edit Codex implementation files unless explicitly instructed.

---

## Claude Owns

- Product requirements
- Feature scope
- User stories
- Acceptance criteria
- QA checklists
- Demo scripts
- Judge Q&A
- Mock disclosure language
- Risk register
- SaaS roadmap
- Business case
- Final demo verdict

## Claude Must Not Own

- App architecture implementation
- Analytics engine code
- API adapter code
- Persistence implementation
- UI refactors
- Build fixes

---

## Absolute Rules

1. Do not suggest new features during demo stabilization unless critical.
2. Do not hide mocks.
3. Separate current MVP from future roadmap.
4. Every QA pass ends with:
   - READY
   - READY WITH NOTES
   - NOT READY
5. Keep language credible and judge-safe.
6. Do not overclaim AI.
7. Do not ask Codex to redesign unless demo is blocked.
8. Keep documents concise and useful.
9. Focus on proof, clarity, and credibility.
10. The product must be explainable in 30 seconds.

---

# SaaS Product Vision

SmartShelf AI is an AI-assisted retail operations platform for gas stations and small stores.

It helps the owner decide:

- What should I order?
- How much should I order?
- Which products may run out soon?
- Which products are overstocked?
- Which products may expire soon?
- Where should each product be placed on the shelf?
- How many facings should each product get?
- Why did the system recommend this decision?

The product reduces:

- manual guessing
- stockouts
- overstock
- expired goods
- poor shelf allocation
- decision time

The product increases:

- availability of fast-selling products
- shelf efficiency
- purchase order quality
- manager confidence
- data-driven operations

---

# Sprint P1 — Product Requirements and Feature Freeze

## Goal

Define the exact product scope for MVP and SaaS direction.

## Tasks

- Write the product one-liner.
- Write 30-second explanation.
- Define MVP feature list.
- Define SaaS feature list.
- Define out-of-scope list.
- Define user journey:
  1. Owner opens dashboard
  2. Reviews inventory risks
  3. Opens recommendations
  4. Edits/approves order
  5. Views approved order
  6. Checks planogram
- Define success metrics:
  - fewer stockouts
  - less overstock
  - fewer expired products
  - faster order decisions
  - better shelf allocation
- Define what is mocked and why.

## Deliverables

- `docs/PRODUCT_REQUIREMENTS.md`
- `docs/SAAS_FEATURE_SCOPE.md`
- `docs/MOCKS_AND_ASSUMPTIONS.md`

## Done Criteria

- Product can be explained in 30 seconds.
- MVP and SaaS scope are separate.
- Mocks are documented honestly.
- No exaggerated AI claims.

---

# Sprint P2 — QA and Acceptance Criteria

## Goal

Create a QA gate for every Codex sprint.

## Tasks

- Create QA checklist for:
  - Dashboard
  - Products
  - Recommendations
  - Planogram
  - Approved Orders
  - Export/print
  - Empty states
  - Navigation
  - Mock labels
- Define acceptance criteria for:
  - approve
  - reject
  - edit quantity
  - CSV export
  - print
  - planogram selection
  - search/filter
- Define demo-breaking bugs.
- Define non-blocking bugs.
- Define actions to avoid if unresolved.
- Re-audit after each Codex sprint.

## Deliverables

- `docs/QA_CHECKLIST.md`
- `docs/ACCEPTANCE_CRITERIA.md`
- `docs/DEMO_RISK_REGISTER.md`

## Done Criteria

- Every visible action has a test.
- Every mock has safe wording.
- Every known risk has severity.
- Final verdict is explicit.

---

# Sprint P3 — Demo Narrative and Judge Q&A

## Goal

Make the product convincing and safe to present.

## Tasks

- Write 2-minute demo script.
- Write 5-minute demo script.
- Write opening problem statement.
- Write closing statement.
- Write judge Q&A answers:
  - Is this real AI?
  - Where does the data come from?
  - Why not local data yet?
  - How accurate is it?
  - How does RAG help?
  - What happens if APIs fail?
  - Why would a store owner pay?
  - What happens after hackathon?
- Write “do not say” list to prevent overclaiming.
- Write fallback lines if app interaction fails.

## Deliverables

- `docs/DEMO_SCRIPT_2_MIN.md`
- `docs/DEMO_SCRIPT_5_MIN.md`
- `docs/JUDGE_QA.md`
- `docs/DO_NOT_SAY.md`

## Done Criteria

- Demo has a clear story.
- Mocks are framed as deliberate POC design choices.
- Answers are honest and confident.
- No claim depends on unavailable backend/AI.

---

# Sprint P4 — SaaS Roadmap and Business Case

## Goal

Turn the prototype into a believable SaaS plan.

## Tasks

- Define post-hackathon phases:
  1. Local-first prototype
  2. CSV/POS import
  3. Persistence and store accounts
  4. Live market signals
  5. RAG-based explanations
  6. Multi-store analytics
  7. Supplier integration
- Define target customers:
  - gas stations
  - mini-markets
  - small supermarkets
  - convenience stores
- Define pricing hypothesis:
  - free pilot
  - monthly subscription
  - per-store pricing
- Define measurable value:
  - reduce waste
  - reduce stockouts
  - reduce ordering time
  - improve shelf revenue
- Define local pilot:
  - 3 stores
  - 30 days
  - before/after comparison

## Deliverables

- `docs/SAAS_ROADMAP.md`
- `docs/BUSINESS_CASE.md`
- `docs/PILOT_PLAN.md`

## Done Criteria

- SaaS path is credible.
- Pilot is realistic.
- Business value is measurable.
- No enterprise fantasy assumptions.

---

# Sprint P5 — Final Demo Readiness

## Goal

Decide whether the team can present safely.

## Tasks

- Run final QA.
- Check browser setup.
- Check screenshots.
- Check internet dependency.
- Check reset procedure.
- Check safe click path.
- Check risky click path.
- Confirm commands:
  - `npm install`
  - `npm run dev`
  - `npm run lint`
  - `npm run build`
- Prepare:
  - final safe demo flow
  - avoid list
  - fallback explanations
  - final verdict

## Deliverables

- `docs/FINAL_DEMO_CHECKLIST.md`
- `docs/SAFE_DEMO_FLOW.md`
- `docs/FINAL_HANDOFF.md`

## Done Criteria

- Final verdict is written.
- Safe demo path is clear.
- Avoid list is clear.
- Team knows exactly what to click.
- Team knows how to explain mocks.
- Team knows how to recover if something fails.

---

# Judge-Safe Language

## AI

"The current demo uses deterministic retail analytics plus mock AI explanations so the demo remains stable. The architecture is designed to replace this layer with Gemini/OpenAI through a backend proxy."

## Data

"The current demo uses a normalized retail dataset sample. The product is data-source agnostic, so a local store can plug in its POS export later."

## RAG

"RAG is planned as a knowledge layer that retrieves relevant retail rules, category patterns, and market context before generating explanations. The current sprint prepares the corpus structure but does not depend on vector search yet."

## Market Signals

"Weather, holidays, and local events are treated as external signals. In the demo they may be static for stability, but the adapter path supports free public APIs."

## No Backend

"The current app is local-first to prove the workflow. Persistence, auth, and multi-store support come after validating the core decision flow."

---

# Claude QA Verdict Format

After every QA pass, return:

```txt
QA PASS: P# / Codex Sprint C#

VERDICT: READY / READY WITH NOTES / NOT READY

TESTED:
-

PASS:
-

FAIL:
-

RISKS:
-

DEMO SAFE FLOW:
-

AVOID:
-

RECOMMENDED CODEX FIXES:
-
```

---

# Final Product Definition of Done

SmartShelf AI is presentation-ready when:

- Owner journey is clear.
- Dashboard explains store situation.
- Recommendations are understandable.
- Approval flow works.
- Approved orders close the loop.
- Planogram creates a visual wow moment.
- Mocks are labeled honestly.
- SaaS roadmap is credible.
- The team does not overclaim.
- Claude verdict is READY or READY WITH NOTES.
