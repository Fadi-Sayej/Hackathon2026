#!/usr/bin/env node
/**
 * check_bundle_size.mjs — a ratchet, not an aspiration.
 *
 * ADR-018 declines to ship a JSON-schema validator to the browser because design §16
 * budgets the main chunk under 400 KB and Checkpoint 4 caps the bundle at 500 KB. A budget
 * nothing enforces is a sentence in a document, so this fails the build when the bundle
 * grows past the ceiling below.
 *
 * WHAT IT MEASURES, AND WHY THAT CHANGED (2026-09-13)
 *   It summed every chunk in dist/assets and compared the total to a 500 KB target. That
 *   is not a number anyone downloads. The build has TWO independent entries — index.html,
 *   which the store owner opens, and telemetry.html, which only the team opens — and no
 *   browser ever loads both. Summing them reported 928 KB against a 500 KB target while
 *   the owner's actual download was 496 KB.
 *
 *   So it now resolves each HTML entry to the scripts that entry references and reports
 *   per entry. The gate is unchanged: total against CEILING_KB, a ratchet on everything
 *   the build produces. Whether Checkpoint 4's 500 KB means the owner's entry or the whole
 *   output is not this script's call — it prints both and says which is which.
 *
 * The ceiling is deliberately set just above TODAY's size, not at the target. Lowering it
 * is the point; raising it needs a reason in the commit message.
 *
 *   Note on the old comment here: it said the 4.36 MB demo spine was "the whole budget"
 *   and that the target was unreachable until Phase 4 deleted it. That stopped being true
 *   at the cut-over — the demo spine and planogram are unreachable from any entry, so Vite
 *   already tree-shakes them out. Verified by grepping dist/assets for demoProducts,
 *   loadDemoStoreData, packageGeometry, FIXTURE_PRESETS and allocationEngine: zero hits.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const CEILING_KB = 1000        // measured 930 KB after the cut-over, 2026-09-12 (was 5,016)
const TARGET_KB = 500          // Checkpoint 4 (design §22)
const DIST = 'dist'
const DIR = join(DIST, 'assets')

const kbOf = (name) => Math.round(statSync(join(DIR, name)).size / 1024)

const allJs = readdirSync(DIR).filter((n) => n.endsWith('.js'))
const total = allJs.reduce((sum, n) => sum + kbOf(n), 0)

/** Scripts an HTML entry actually references, so the figure is one a browser downloads. */
function entryChunks(html) {
  const src = readFileSync(join(DIST, html), 'utf8')
  return allJs.filter((n) => src.includes(n))
}

const entries = readdirSync(DIST).filter((n) => n.endsWith('.html'))
const perEntry = entries
  .map((html) => {
    const chunks = entryChunks(html).map((n) => [kbOf(n), n]).sort((a, b) => b[0] - a[0])
    return { html, chunks, kb: chunks.reduce((s, [kb]) => s + kb, 0) }
  })
  .sort((a, b) => b.kb - a.kb)

console.log(`build output: ${total} KB across ${allJs.length} chunks (ceiling ${CEILING_KB} KB)`)
console.log(`Checkpoint 4 target is ${TARGET_KB} KB. No browser loads more than one entry:\n`)
for (const { html, chunks, kb } of perEntry) {
  const verdict = kb <= TARGET_KB ? 'under' : 'OVER'
  const who = html === 'index.html' ? "  ← the owner's app" : ''
  console.log(`  ${String(kb).padStart(4)} KB  ${html.padEnd(16)} ${verdict} the ${TARGET_KB} KB target${who}`)
  for (const [ckb, name] of chunks) console.log(`         ${String(ckb).padStart(4)} KB  ${name}`)
}

const orphans = allJs.filter((n) => !perEntry.some(({ chunks }) => chunks.some(([, c]) => c === n)))
if (orphans.length) {
  console.log(`\n  ${orphans.length} chunk(s) referenced by no entry: ${orphans.join(', ')}`)
}

if (total > CEILING_KB) {
  console.error(`\nFAIL  build output grew to ${total} KB, over the ${CEILING_KB} KB ceiling.`)
  console.error('      Either the growth is justified and CEILING_KB moves with a reason,')
  console.error('      or something was added that does not belong in the browser.')
  process.exit(1)
}
if (total <= TARGET_KB) {
  console.log(`\nNOTE  the whole build output is under ${TARGET_KB} KB — lower CEILING_KB to match.`)
}
console.log('\nOK')
