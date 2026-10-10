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
 *   per entry.
 *
 * TWO INSTRUMENTS, AND THEY ARE NOT THE SAME ONE (2026-09-13)
 *   Phase 4's Task 4.1 note settled what Checkpoint 4's 500 KB governs: the OWNER'S ENTRY,
 *   index.html — what his phone downloads before he can read today's work. telemetry.html
 *   is an internal instrument on a desk, it is a separate entry, and no browser loads both.
 *
 *   So this script now gates twice:
 *     TARGET_KB   index.html only. Checkpoint 4's criterion, and the reason the budget
 *                 exists at all. Enforced here, because until today it was printed and
 *                 not enforced — index.html could have crossed 500 KB and this exited 0
 *                 while the ratchet had room. That is the "built, tested, changes nothing"
 *                 failure this repository keeps finding, in a guard rather than a signal.
 *     CEILING_KB  total build output. A ratchet on everything that ships from here,
 *                 including telemetry.html, which no target governs but which still grows.
 *                 A ceiling watching only index.html would let the other entry run away.
 *
 * The ceiling is deliberately set just above TODAY's size, not at the target. Lowering it
 * is the point; raising it needs a reason in the commit message.
 *
 *   Note on the old comment here: it said the 4.36 MB demo spine was "the whole budget"
 *   and that the target was unreachable until Phase 4 deleted it. That stopped being true
 *   at the cut-over — the demo spine and planogram were unreachable from any entry, so Vite
 *   already tree-shook them out. Verified by grepping dist/assets for demoProducts,
 *   loadDemoStoreData, packageGeometry, FIXTURE_PRESETS and allocationEngine: zero hits.
 *   Phase 4 deleted both on 2026-09-24 (ADR-028).
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const CEILING_KB = 1029        // measured 1026 KB on a fresh local build, 2026-10-10, against 1019 KB for main
                               // the same day (CI reads about 1 KB higher): F14's explanation on the Reorder
                               // card and the note above it (F14-S1 FR-238, FR-242, FR-243), mockups approved
                               // by the owner on 2026-10-10. main grew 4 KB (238 → 242), the slot phrases and
                               // the note in three languages; 3 KB load only on demand, in ReorderPage (6 → 9).
                               // The owner's entry is 429 KB, under its 500 KB target. Before that it was 1021,
                               // measured 1018 KB on a fresh local build, 2026-10-08, against 998 KB for main
                               // the same day (CI reads about 1 KB higher): D-38's units and heights (F12-S1
                               // FR-228 … FR-234, ADR-044), approved by the owner on 2026-10-08. main grew
                               // 9 KB (228 → 237), the form's 43 phrases in three languages; 11 KB load only
                               // on demand: the form in StoreLayoutPage (7 → 14 KB), the plan's drawing to
                               // scale (13 → 14), Firestore's getDoc (407 → 408) and the save (1 KB). The
                               // owner's entry is 424 KB, under its 500 KB target. Before that it was 1000,
                               // measured 997 KB on a fresh local build, 2026-10-08, against 983 KB for main
                               // the same day (CI reads about 1 KB higher): D-37's photo upload (F12-S1
                               // FR-224 … FR-227, ADR-042), approved by the owner on 2026-10-06. 11 of the
                               // 14 KB load only on demand: Firestore's reads and bytes in the firebase chunk
                               // (401 → 407 KB), the screen in StoreLayoutPage (5 → 7 KB), and the sender
                               // (3 KB). main grew 3 KB, the screen's 14 phrases in three languages; the
                               // owner's entry is 414 KB, under its 500 KB target. Before that it was 985,
                               // measured 981 KB on a fresh local build, 2026-10-05 (CI reads about 1 KB
                               // higher): Store layout and Shelf plan (Phase 8 Task 8.9), approved by the
                               // owner on 2026-10-05. main grew 54.5 KB (203,154 → 257,624 bytes), most of
                               // it the 134 phrases of the two pages in three languages, and the CSS 6.2 KB.
                               // The owner's entry, index.html, went from 385 KB to 439 KB, under its 500 KB
                               // target. Before that it was 930, measured 926 KB on a fresh local build, 2026-10-04 (CI reads about 1 KB
                               // higher): F12's reasons in the owner's words (Phase 8 Task 8.0), eight
                               // unavailable sentences and the plan's characterisation in three languages,
                               // and the per-capability lookup that keeps Reorder's wording off Shelf plan:
                               // main grew 4.4 KB. Before that it was 925, measured 922 KB on a fresh local build, 2026-10-03 (CI reads about 1 KB
                               // higher): email-and-password sign-in, Firebase's signInWithEmailAndPassword
                               // and sendPasswordResetEmail in its lazily loaded chunk, and ten strings in
                               // three languages. Before that it was 920, measured 917 KB on a fresh local build, 2026-10-03 (CI reads about 1 KB
                               // higher): the sign-in page's welcome screen and its specific error
                               // messages, 13 strings in three languages. index.html is 376 KB.
                               // Before that it was 916, measured 912 KB on a fresh local build, 2026-10-03 (CI reads about 1 KB
                               // higher): D-29's preview on Reorder and Approved orders, a component
                               // and six strings in three languages; the example itself is fetched,
                               // not bundled. index.html is 371 KB. Before that it was 913,
                               // measured 910 KB on a fresh local build, 2026-09-29 (CI reads about 1 KB
                               // higher): D-27 puts the market's listed prices and a third answer on F9's
                               // card, 5 strings in three languages and the per-store price lines.
                               // index.html is 368 KB, under its 500 KB target. Before that it was 910,
                               // measured 906 KB in CI (905 locally), 2026-09-28: idle products'
                               // three answers and the Prices page's reference note (#243), five
                               // strings in three languages; index.html 363 KB. Before that it was
                               // 905, over a measured 903 KB, 2026-09-28: the card batch (#235) put 60 strings in
                               // three languages on the owner's screens (each card's action, the
                               // evidence and threshold labels) and index.html went 352 → 361 KB,
                               // under its 500 KB target. Before that it was 900, over a
                               // measured 894 KB, 2026-09-28, at Checkpoint 4: Phase 4 Task 4.5
                               // rebuilt the telemetry page on measurement.json and deleted what
                               // only the old one read (actionPriority, credibility, persistence,
                               // completionActions). index.html is 352 KB. Before that it was 915,
                               // over a measured 909 KB, 2026-09-27: F8's Reorder and Approved
                               // orders pages and their approved wording in three languages
                               // (Phase 5 Task 5.13) added 21 KB to main's 888, and index.html
                               // stayed at 346 KB. Before that it was 900, over a measured
                               // 873 KB, 2026-09-24, once the strings and styles the
                               // removed pages left behind were deleted: 549 keys from each of
                               // the three dictionaries took 103 KB off index.html. It stood at
                               // 1000 over a measured 928 KB from 2026-09-13, unmoved by the
                               // motion split and by ADR-028's deletions, neither of which took
                               // a byte out of the build. It moves when bytes actually leave.
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

/**
 * A chunk no HTML entry names is not necessarily dead — a dynamic `import()` is
 * referenced from inside another chunk, not from the HTML. That is how the motion
 * layer (gsap, ScrollTrigger, lenis) leaves the owner's entry while staying
 * reachable, and calling it "referenced by no entry" invites someone to delete
 * live code.
 *
 * Reachability is walked from the entries rather than asked one hop at a time.
 * "Is this file named by any shipped chunk?" launders dead code: two unreachable
 * chunks that import each other each vouch for the other, and both get reported
 * as healthy on-demand chunks. Only what an entry can actually reach is lazy;
 * everything else is unreferenced, however much it is mentioned.
 */
const unnamedByHtml = allJs.filter((n) => !perEntry.some(({ chunks }) => chunks.some(([, c]) => c === n)))
const contents = new Map(allJs.map((n) => [n, readFileSync(join(DIR, n), 'utf8')]))

const reachable = new Set(perEntry.flatMap(({ chunks }) => chunks.map(([, name]) => name)))
for (let added = true; added; ) {
  added = false
  for (const name of allJs) {
    if (reachable.has(name)) continue
    if ([...reachable].some((from) => contents.get(from).includes(name))) {
      reachable.add(name)
      added = true
    }
  }
}

const lazy = unnamedByHtml.filter((n) => reachable.has(n))
const orphans = unnamedByHtml.filter((n) => !reachable.has(n))

if (lazy.length) {
  const kb = lazy.reduce((sum, n) => sum + kbOf(n), 0)
  console.log(`\n  ${lazy.length} chunk(s) loaded on demand, ${kb} KB, off every entry's critical path:`)
  for (const name of lazy) console.log(`         ${String(kbOf(name)).padStart(4)} KB  ${name}`)
}
if (orphans.length) {
  console.log(`\n  ${orphans.length} chunk(s) referenced by nothing at all: ${orphans.join(', ')}`)
}

const OWNER_ENTRY = 'index.html'
const owner = perEntry.find(({ html }) => html === OWNER_ENTRY)

if (!owner) {
  console.error(`\nFAIL  ${OWNER_ENTRY} is not in the build. The owner's app is what this`)
  console.error('      target governs, so its absence is a failure, not a pass.')
  process.exit(1)
}
if (owner.kb > TARGET_KB) {
  console.error(`\nFAIL  ${OWNER_ENTRY} is ${owner.kb} KB, over Checkpoint 4's ${TARGET_KB} KB target.`)
  console.error("      That is what the store owner's phone downloads before he can read")
  console.error("      today's work. Move the weight off this entry, or change the target")
  console.error('      in the plan first — not here.')
  process.exit(1)
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
