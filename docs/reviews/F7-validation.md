---
ID: F7-VALIDATION
Title: F7 — Figure Provenance and Reproducibility · validation
Status: Ready for review
Owner: smartshelf-validator
Parent: [F7-S1](../features/F7-figure-provenance/specs/F7-S1-figure-provenance.md)
Inputs: [docs/features/F7-figure-provenance/specs/F7-S1-figure-provenance.md, docs/features/F7-figure-provenance/intent.md, docs/product/PRD.md §9, docs/reviews/checkpoint-3-reproduction.md, public/data/dashboard.json (2026-09-28), scripts/figures.py, src/engine/provenance.py, src/pages/DataPage.jsx, src/surface/EntryCard.jsx, tests/engine/test_figures_cli.py, tests/engine/test_figures_verdict.py, GitHub deployment records (Production)]
Updated: 2026-09-28
---

# Validation F7 — Figure Provenance and Reproducibility

- **Deployed URL:** `https://hackathon2026-fadi19.vercel.app` (serves the sign-in page; ADR-029).
- **Commit in production:** `2a716ec`. GitHub deployment `6708764605`, `success`, 2026-09-28 11:29Z.
- **Artefact read:** `public/data/dashboard.json` at `2a716ec`, `generated_at 2026-09-28T03:10:39Z`, run `ok`, 47 figures.
- **Reproduction run:** `python3 scripts/figures.py --json --skip-market` on 2026-09-28 at `review/validations-f3-f13` (main plus these records), after rebuilding the market half from the committed 2026-09-28 snapshot.
- **Context:** the pilot with the YomYom store ended on 2026-09-27 (D-23).

## Verdict

**The engine keeps F7's promise exactly: on the same data, `npm run figures` reproduces 46 of
the 47 published figures to the digit and threshold, and the 47th differs only in where the
owner state was read from.** Two things fall short of the spec, and both are about paper and
screens rather than the engine. The owner's cards state figures without the date of the data
behind them, and that data is now 114 days old. And the figures printed in the PRD and in
F7's own intent still include six that the engine does not reproduce.

---

## Pass one — conformance

| Source | id | Criterion | Verdict | Evidence |
|---|---|---|---|---|
| spec §15 | AC-120 | every figure on an owner-facing surface or document carries its input vintage | **partial** | In the artefact, every figure names its `inputs` and `vintages` states each one (POS as of 2026-06-06, sales 2026-01…07, competitor 2026-09-28, owner state). The Data page renders them (`DataPage.jsx:81-120`); the Prices page says when prices were seen; reconciliation cards state their months. **Today's price cards do not**: F1's seven valued cards show `shelf_price`, `delivery_price`, `difference`, `markup_pct`, `ceiling_pct`, and no date. They rest on a POS export 114 days old |
| spec §15 | AC-121 | all figures reproduced in one action, no preparation | **met, with one documented step on a fresh clone** | `npm run figures` exits 0 here, with NOTE lines only (since #224). A fresh clone needs `scripts/import_yomyom_pos.py` first, because `data/**` is gitignored (CLAUDE.md rule 6); Checkpoint 3 measured that path (`checkpoint-3-reproduction.md`) |
| spec §15 | AC-122 | an input removed → that figure unavailable, no remembered value | **met** | `figures.py` exits 1 naming the missing input (`test_figures_verdict.py`, "a capability with registered figures that is unavailable still fails"); `check_v1_signals.py` withholds each input |
| spec §15 | AC-123 | an unstatable figure is absent, distinguishable from zero | **met** | `figures.py` treats a figure carrying nothing as missing, never 0 (`_carries_nothing`); `CapabilityPage` renders a null count as `count.undetermined` |
| spec §15 | AC-124 | every estimate labelled wherever stated | **met** | `EntryCard` labels `certainty: estimated` on the card (`DailyPage.test.jsx`); no published figure is an estimate today |
| spec §15 | AC-125 | reproduction states input vintage and reproduction time | **met** | The payload carries `vintages`, `generated_at` (2026-09-28T12:10Z in this run), `inputs_digest`, `population` |
| spec §15 | AC-126 | every composite shows its components and kinds | **met (none exists)** | No composite figure is published: `value_kinds_present` is `["per_sale"]`, and F13's measurement keeps one money row per kind and certainty (OQ-801 closed 2026-09-28) |
| spec §15 | AC-127 | a figure on the surface equals reproduction on the same data | **met** | 46 of 47 figures identical in value and thresholds. The 47th, `provenance.owner_state_available`, has the same value (1) and different thresholds: the laptop reads the committed owner-state mirror (no Firestore credentials), the nightly the live pull. Before the market half was rebuilt from the 2026-09-28 snapshot, 15 differed; so the comparison is only as good as the "same data" |
| spec §15 | AC-128 | every figure in the owner-facing intent document reproduces, or was removed | **partial** | PRD §9 (and F7's intent, which carries the same table) against the artefact: **68** inverted and **18%** ceiling reproduce exactly. Not reproduced and still printed: **6,260** (published population 5,986), **4,932** (4,671), **136** (131), **371** (355), **1,970** (a different definition; 2,614 matched), **−11%** against Alonit (the Alonit station matches 5 products). The table carries a banner dated 2026-09-08 saying not to read it from paper |
| spec §15 | AC-129 | a derived threshold stated with every dependent figure | **met** | Every `price_consistency.*` figure carries `ceiling_pct 18`; every `competitor_position.*` figure carries policy, attention, cost floor and allowance |
| spec §7 | INV-060 … INV-065 | | **met in the engine; INV-060 partial on screen** | INV-060 as AC-120; INV-061 as AC-123; INV-062 as AC-122; INV-063 as AC-124; INV-064 as AC-126; INV-065: one implementation, the engine in print mode (ADR-002), as AC-127 |
| spec §19 | INT-PROV, protected | traced to an AC | **met** | Every §19 row names an AC |

### Scope drift

| Change | In a plan task's `Files:` list? | In spec §3 scope? | Note |
|---|---|---|---|
| #224 (`09ca1a0`): capabilities that register no figure are NOTE, not FAIL | issue, not a plan task | yes (FR-126, §11.6) | Traced to System Design §11.6's "registered figure" |

### Shipped but never requested

Nothing.

---

## Pass two — fidelity

*Spec and PRD closed. Read only `docs/features/F7-figure-provenance/intent.md`.*

**PROBLEM (every figure on paper ages; one not recomputed in front of its owner starts an
argument that cannot be won): is the owner measurably less stuck?** The team is. Any figure the
engine publishes can be recomputed in front of him in one command, and it matches.

**SUCCESS — count it.** The intent's success is the command. 46 of 47 figures reproduce exactly
on the same data (AC-127).

**USER: the team when it quotes a figure; the owner when he doubts one.** The team has the
command. The owner, when he doubts a card on Today, cannot see what date the figure rests on
(AC-120).

**NOT NOW: anything deferred built?** No history of figures, no audit of who quoted what.

**Would you write the same intent again?** Yes, but not its table. The banner is right that
paper ages; the table under it is the proof, and it is still there. The intent's own sentence
names the nightly as regenerating `public/data/operational.json`, a file deleted on 2026-09-28.

---

## Pass three — usefulness

| Question | Answer | Read from |
|---|---|---|
| Figures published | 47 | `public/data/dashboard.json` → `figures` |
| `generated_at` | 2026-09-28T03:10:39Z, run `ok` | `public/data/dashboard.json` |
| Reproduced identically on the same data | 46 of 47 | `scripts/figures.py --json`, 2026-09-28 |
| Turned off | An input withheld: the figures it feeds are named missing and the command exits 1 | `test_figures_verdict.py`, `check_v1_signals.py` |
| Rule 8 | **yes**: no figure sums kinds; per-sale figures are labelled per sale | `figures`, `value_kinds_present` |
| Rule 13 | Honoured: sales figures state their seven months; no figure divides them into days | `figures[*].thresholds`, `vintages.sales` |

---

## What surprised me

The reproduction promise holds to the digit, and it held only after the market half was rebuilt
from the same snapshot. Fifteen figures differed until then. "Same data" is doing all the work
in AC-127, and on a laptop nothing warns you that yours is a day old.

## Not checked, and why

- A fresh clone today: Checkpoint 3 did it on 2026-09-12 and nothing about the path has changed
  but #224, which makes it exit 0.
- Every figure in every other intent: only PRD §9's table was compared; F3's and F4's records
  compare their own.

## Open items

| Item | Owning role | Why it matters |
|---|---|---|
| ~~State the POS date on the cards that rest on it, now that it is 114 days old and will not change (D-23)~~ **Done 2026-09-28, #235** (approved by the owner; see `docs/reviews/card-wording-2026-09-28.md`) | smartshelf-architect, then smartshelf-engineer; screen change, owner approves | AC-120 partial |
| ~~Remove from PRD §9 (and F7's intent table) the figures that no longer reproduce, or replace them with the command~~ **Noted 2026-09-29**: a dated note under each banner names the six that no longer reproduce; the migrated table is kept as written | smartshelf-pm | AC-128 partial |
| ~~PRD §9 and F7's intent say the nightly regenerates `operational.json`, deleted on 2026-09-28~~ **Noted 2026-09-29** in both | smartshelf-pm | A present-tense claim about a deleted file; the Checkpoint 4 sweep missed it |
| ~~Make `figures.py` say when the local market half is older than the artefact it is compared with~~ **Done 2026-09-28, #234 (`8f71e28`)**: a NOTE names the figures that read the market and how to rebuild; the exit code is unchanged | smartshelf-engineer | AC-127 depends on "same data" and nothing checks it |
