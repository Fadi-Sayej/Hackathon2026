#!/usr/bin/env node
/**
 * check_bundle_size.mjs — a ratchet, not an aspiration.
 *
 * ADR-018 declines to ship a JSON-schema validator to the browser because design §16
 * budgets the main chunk under 400 KB and Checkpoint 4 caps the bundle at 500 KB. A budget
 * nothing enforces is a sentence in a document, so this fails the build when the bundle
 * grows past the ceiling below.
 *
 * The ceiling is deliberately set just above TODAY's size, not at the target. The 4.36 MB
 * demo spine (design §20.1 REMOVE) leaves in Phase 4, and CEILING_KB comes down with it.
 * Lowering this number is the point; raising it needs a reason in the commit message.
 */
import { readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const CEILING_KB = 5200        // measured 5,016 KB on 2026-09-12
const TARGET_KB = 500          // Checkpoint 4 (design §22)
const DIR = 'dist/assets'

let total = 0
const chunks = []
for (const name of readdirSync(DIR)) {
  if (!name.endsWith('.js')) continue
  const kb = Math.round(statSync(join(DIR, name)).size / 1024)
  chunks.push([kb, name])
  total += kb
}
chunks.sort((a, b) => b[0] - a[0])

console.log(`bundle: ${total} KB across ${chunks.length} chunks (ceiling ${CEILING_KB} KB, Checkpoint 4 target ${TARGET_KB} KB)`)
for (const [kb, name] of chunks.slice(0, 3)) console.log(`  ${String(kb).padStart(6)} KB  ${name}`)

if (total > CEILING_KB) {
  console.error(`\nFAIL  bundle grew to ${total} KB, over the ${CEILING_KB} KB ceiling.`)
  console.error('      Either the growth is justified and CEILING_KB moves with a reason,')
  console.error('      or something was added that does not belong in the browser.')
  process.exit(1)
}
if (total <= TARGET_KB) {
  console.log(`\nNOTE  the bundle is now under the ${TARGET_KB} KB target — lower CEILING_KB to match.`)
}
console.log('\nOK')
