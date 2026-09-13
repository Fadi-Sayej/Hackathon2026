#!/usr/bin/env node
/**
 * `npm run doctor` — integrity checks on the artefact the owner actually reads.
 *
 * WHY THIS EXISTS SEPARATELY FROM THE TEST SUITE
 *   Unit tests assert on fixtures the author chose. This runs its invariants
 *   against the *real* published artefact, where the interesting failures live.
 *
 *   Four things were found the hard way by the version of this script that read
 *   the catalogue. Only two of them have a successor here, and it is worth being
 *   exact about which, because a header that overstates a tool is how people stop
 *   checking the thing it stopped checking:
 *
 *     - 83 rows dropped by a Map keyed on a non-unique id  → `entry-identity`
 *     - 625 rows with negative stock from a till artefact  → `negative-stock-coherence`
 *     - services (car washes) priced as shelf products     → NO successor
 *     - margins twenty times their department median       → NO successor
 *
 *   The last two needed a whole catalogue to compute — a department median, and
 *   a census of which rows are merchandise at all. The artefact carries neither,
 *   and the catalogue that does is gitignored. They are gone, not relocated, and
 *   `doctor.checks.mjs` says so in its own header alongside velocity.
 *
 *   Each check states what it found, why it matters, and what to do. Exits
 *   non-zero on an ERROR so it can gate a release; WARN and NOTE never fail the
 *   run, because a warning that blocks a build gets silenced within a week.
 *
 * WHAT IT READS, SINCE 2026-09-13
 *   `public/data/dashboard.json`, not the demo spine. It used to load the demo
 *   spine's catalogue loader and two V4 shelf-geometry modules, all of which
 *   leave in Phase 4 Task 4.1 — and the catalogue that replaced them is
 *   gitignored, so a fresh clone cannot see it. The artefact is the only real
 *   data a clone has, and it is the only data the owner receives. See
 *   doctor.checks.mjs for what that does and does not let it check, and for the
 *   two checks that retired with their subject.
 *
 *   Plain `node`, not `vite-node`: it reads JSON and imports nothing from src/.
 */
import { readFileSync } from 'node:fs'

import { ARTEFACT_PATH, ERROR, WARN, errorsIn, runChecks } from './doctor.checks.mjs'

function readArtefact() {
  try {
    return JSON.parse(readFileSync(ARTEFACT_PATH, 'utf8'))
  } catch {
    // Returning null rather than throwing: runChecks() turns an absent or
    // unparseable artefact into an ERROR finding, so the output shape is the
    // same however the run failed.
    return null
  }
}

const findings = runChecks(readArtefact())

const ICON = { [ERROR]: '✗', [WARN]: '!', NOTE: '·' }
const order = { [ERROR]: 0, [WARN]: 1, NOTE: 2 }

console.log('\nSmartShelf doctor — artefact integrity\n')
for (const finding of findings.sort((a, b) => order[a.level] - order[b.level])) {
  console.log(`${ICON[finding.level]} [${finding.check}] ${finding.message}`)
  if (finding.hint) console.log(`    → ${finding.hint}`)
}

const errors = errorsIn(findings)
const warnings = findings.filter((finding) => finding.level === WARN).length
console.log(`\n${errors} error(s), ${warnings} warning(s), ${findings.length} checks reported.\n`)

process.exit(errors ? 1 : 0)
