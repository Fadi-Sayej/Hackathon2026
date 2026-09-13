/**
 * doctor.checks.mjs — the checks `npm run doctor` runs, as pure functions.
 *
 * WHAT THIS AUDITS, AND WHAT IT DOES NOT
 *   It audits `public/data/dashboard.json` — the artefact the owner's browser
 *   downloads. It does NOT audit the catalogue. Those are different populations
 *   and conflating them is the specific way this script failed before: its
 *   negative-stock check read `currentStock < 0` on rows the adapter had already
 *   clamped to zero, so it reported a clean bill while 631 negative rows sat in
 *   the source. It claimed catalogue scope while holding post-pipeline scope.
 *
 *   The artefact carries only FLAGGED rows — roughly 3.5k entries over a ~7.6k
 *   catalogue — so no check here can speak for the catalogue, and none of them
 *   pretends to. Every message that states a quantity states its denominator with
 *   it. When the denominator is unavailable the check says so rather than
 *   printing a number that reads as a total (CLAUDE.md rule 8, applied to the
 *   tool that enforces rule 8).
 *
 * WHY IT MOVED HERE FROM THE DEMO SPINE
 *   It read the demo spine's catalogue loader — the committed generated
 *   catalogue — plus two V4 shelf-geometry modules. All of those leave in Phase 4
 *   Task 4.1, and the catalogue that replaced them (`data/internal/silver_pos/`)
 *   is gitignored, so a fresh clone cannot see it. The artefact is the only real
 *   data a clone has, and it is also the only data the owner actually receives.
 *
 * WHAT LEFT, SAID OUT LOUD RATHER THAN DROPPED
 *   - shelf-geometry coverage and fixture floor-plan bounds go with the V4
 *     shelf-layout modules. Their subject is being deleted; a check whose
 *     subject is gone is not a loss.
 *   - velocity confidence bands have NO successor here. `Entry` carries no
 *     velocity field, deliberately (INV-005/C-3). That check cannot be made from
 *     a fresh clone at all, and saying so is more honest than approximating it.
 *
 * Separated from doctor.mjs so it can be tested. Every check is driven in both
 * directions in `__tests__/doctor.checks.test.mjs` — CLAUDE.md rule 12: a check
 * that has never failed is not proven wired.
 */
import { fileURLToPath, URL as NodeURL } from 'node:url'

export const ERROR = 'ERROR'
export const WARN = 'WARN'
export const NOTE = 'NOTE'

export const SCHEMA_VERSION = 2

export const ARTEFACT_PATH = fileURLToPath(
  new NodeURL('../public/data/dashboard.json', import.meta.url),
)

/** Capabilities whose `entries` are not surface entries and carry no per-row evidence. */
const NOT_ENTRIES = new Set(['owner_questions'])

const n = (value) => (typeof value === 'number' && Number.isFinite(value) ? value : null)
const count = (value) => (value === null ? 'an unknown number of' : value.toLocaleString('en-US'))

/** Every entry across every capability, tagged with the capability it came from. */
function allEntries(artefact) {
  const out = []
  for (const [id, capability] of Object.entries(artefact.capabilities ?? {})) {
    if (NOT_ENTRIES.has(id)) continue
    for (const entry of capability?.entries ?? []) out.push({ id, entry })
  }
  return out
}

/**
 * Run every check over one artefact.
 *
 * Returns a flat list of `{ level, check, message, hint }`. It never throws on a
 * malformed artefact — a doctor that crashes on bad input is a doctor that tells
 * you nothing on exactly the day you needed it.
 */
export function runChecks(artefact) {
  const findings = []
  const report = (level, check, message, hint) => findings.push({ level, check, message, hint })

  // ── 0. The artefact must be there and be a shape we understand ───────
  if (!artefact || typeof artefact !== 'object' || Array.isArray(artefact)) {
    report(
      ERROR,
      'artefact',
      'no readable artefact at public/data/dashboard.json',
      'It is committed, so a clone should have it. Rebuild with `npm run data:refresh`.',
    )
    return findings
  }
  if (artefact.schema_version !== SCHEMA_VERSION) {
    report(
      ERROR,
      'artefact',
      `artefact declares schema_version ${JSON.stringify(artefact.schema_version)}, not ${SCHEMA_VERSION}`,
      'Every check below reads the schema-2 shape. Refusing rather than misreading it.',
    )
    return findings
  }

  const tagged = allEntries(artefact)
  const entries = tagged.map(({ entry }) => entry)
  const capabilities = artefact.capabilities ?? {}
  const catalogue = n(capabilities.competitor_position?.counts?.catalogue)

  // ── 1. Scope, stated before any number is ────────────────────────────
  // The banner exists so no reader mistakes a flagged-subset figure for a
  // catalogue figure. That mistake is what kept a dead check alive for months.
  {
    const barcodes = new Set(entries.map((e) => e.barcode).filter(Boolean))
    report(
      NOTE,
      'scope',
      catalogue === null
        ? `auditing ${count(entries.length)} published entries covering ${count(barcodes.size)} products; the catalogue total is not stated in this artefact`
        : `auditing ${count(entries.length)} published entries covering ${count(barcodes.size)} of ${count(catalogue)} catalogue rows`,
      'This audits the artefact the owner downloads, not the catalogue. Catalogue-wide checks need data/internal/silver_pos/, which is gitignored.',
    )
  }

  // ── 2. Entry identity (ADR-009) ──────────────────────────────────────
  // The descendant of the old unique-id check, and the reason that check
  // existed: a Map keyed on a non-unique id keeps the last row and drops the
  // rest. Here the stakes are higher than a dropped row. ADR-009 makes `id` the
  // permanent identity, and src/owner/ownerState.js keys the owner's recorded
  // outcomes by it — so two entries sharing an id means marking one done
  // silently marks the other done too, in the owner's hands, unrecoverably.
  {
    const seen = new Map()
    for (const { entry } of tagged) seen.set(entry.id, (seen.get(entry.id) ?? 0) + 1)
    const collided = [...seen.entries()].filter(([, times]) => times > 1)
    const surplus = collided.reduce((sum, [, times]) => sum + times - 1, 0)

    if (collided.length) {
      const where = new Set(
        tagged.filter(({ entry }) => (seen.get(entry.id) ?? 0) > 1).map(({ entry }) => entry.signal_family),
      )
      report(
        ERROR,
        'entry-identity',
        `${count(collided.length)} entry ids of ${count(entries.length)} published entries are used more than once, covering ${count(surplus)} surplus entries (${[...where].join(', ')})`,
        'ADR-009 makes this id permanent identity and ownerState.v2 keys outcomes by it: recording an outcome on one of these resolves the others silently. Fix id generation in the engine.',
      )
    } else {
      report(NOTE, 'entry-identity', `${count(entries.length)} published entries, all ids distinct`)
    }

    // recordOutcome() throws without signal_family (ADR-016), so an entry
    // missing it cannot be acted on at all — the owner clicks and gets an error.
    const unfamilied = entries.filter((e) => !e.signal_family)
    if (unfamilied.length) {
      report(
        ERROR,
        'entry-identity',
        `${count(unfamilied.length)} of ${count(entries.length)} published entries carry no signal_family`,
        'recordOutcome() rejects these (ADR-016). The owner cannot record an outcome against them.',
      )
    }
  }

  // ── 3. Value discipline (CLAUDE.md rule 8) ───────────────────────────
  // Money is the thing this repository has been burned by most. The artefact
  // declares `value_kinds_present` so the browser knows whether a total is even
  // expressible; if that declaration disagrees with the entries, a summary can
  // sum a per-sale figure with a one-off one, which is the "₪106,164 per sale"
  // headline rule 8 exists to prevent.
  {
    const valued = entries.filter((e) => e.value)
    const observed = new Set(valued.map((e) => e.value?.kind).filter(Boolean))
    const declared = new Set(artefact.value_kinds_present ?? [])

    const undeclared = [...observed].filter((kind) => !declared.has(kind))
    const unbacked = [...declared].filter((kind) => !observed.has(kind))

    if (undeclared.length) {
      report(
        ERROR,
        'value-discipline',
        `entries carry value kinds the artefact does not declare: ${undeclared.join(', ')}`,
        'value_kinds_present is what the browser trusts when deciding whether a total may be shown (rule 8).',
      )
    }
    if (unbacked.length) {
      report(
        ERROR,
        'value-discipline',
        `artefact declares value kinds no entry carries: ${unbacked.join(', ')}`,
        'A declared kind invites a total that nothing backs.',
      )
    }

    const malformed = valued.filter((e) => n(e.value?.amount) === null)
    if (malformed.length) {
      report(
        ERROR,
        'value-discipline',
        `${count(malformed.length)} of ${count(valued.length)} valued entries carry an amount that is not a finite number`,
        'When a figure cannot be stated honestly the entry must carry no value at all, never zero or null (rule 8, F7-S1).',
      )
    }
    if (!undeclared.length && !unbacked.length && !malformed.length) {
      report(
        NOTE,
        'value-discipline',
        `${count(valued.length)} of ${count(entries.length)} published entries carry a money value, all of declared kinds (${[...declared].join(', ') || 'none'})`,
      )
    }
  }

  // ── 4. Negative-stock flag coherence ─────────────────────────────────
  // The successor to the check that was dead. It no longer asks the catalogue
  // whether stock is negative — it asks whether the rows the engine FLAGGED as
  // negative actually carry negative evidence, and whether the count it
  // published matches the rows it published. Those can disagree; that is a real
  // engine bug and nothing else looks for it.
  {
    const flagged = entries.filter((e) => e.signal_family === 'hygiene.negative_stock')
    const published = n(capabilities.hygiene?.counts?.negative_stock)
    const incoherent = flagged.filter((e) => !(n(e.evidence?.recorded_stock) < 0))

    if (incoherent.length) {
      report(
        WARN,
        'negative-stock-coherence',
        `${count(incoherent.length)} of ${count(flagged.length)} rows flagged as negative stock do not carry negative evidence`,
        'The flag and the evidence behind it disagree. One of them is wrong.',
      )
    }
    if (published !== null && published !== flagged.length) {
      report(
        WARN,
        'negative-stock-coherence',
        `hygiene.counts.negative_stock says ${count(published)} but ${count(flagged.length)} such entries were published`,
        'The published count and the published rows are computed separately; a gap means one of them drifted.',
      )
    }
    if (!incoherent.length && (published === null || published === flagged.length)) {
      report(
        NOTE,
        'negative-stock-coherence',
        `${count(flagged.length)} of ${count(entries.length)} published entries flag negative stock, each with negative evidence`,
      )
    }
  }

  // ── 5. Flagged-row pricing coherence ─────────────────────────────────
  // The successor to the old pricing check. It cannot census the catalogue's
  // prices — most rows are not in the artefact — so it does the thing it CAN do
  // honestly: re-derive each flagged row's verdict from the evidence published
  // beside it. Note this keys on `characterisation`, not `signal_family`: both
  // below_cost and thin_margin ship as signal_family `margin.below_cost`, and
  // thin_margin rows legitimately have cost BELOW shelf price. Keying on the
  // family would report every thin-margin row as incoherent.
  {
    const margin = capabilities.margin_below_cost?.entries ?? []
    const belowCost = margin.filter((e) => e.characterisation === 'below_cost')
    const thin = margin.filter((e) => e.characterisation === 'thin_margin')

    const notBelow = belowCost.filter(
      (e) => !(n(e.evidence?.cost_price) > n(e.evidence?.shelf_price)),
    )
    const notThin = thin.filter((e) => {
      const cost = n(e.evidence?.cost_price)
      const shelf = n(e.evidence?.shelf_price)
      return cost === null || shelf === null || cost > shelf
    })

    if (notBelow.length) {
      report(
        WARN,
        'pricing-coherence',
        `${count(notBelow.length)} of ${count(belowCost.length)} rows characterised below_cost do not show cost above shelf price`,
        'The owner is being asked to verify a price on evidence that does not support the claim.',
      )
    }
    if (notThin.length) {
      report(
        WARN,
        'pricing-coherence',
        `${count(notThin.length)} of ${count(thin.length)} rows characterised thin_margin are not thin-margin shaped`,
        'A thin margin is a positive one. These belong in below_cost or nowhere.',
      )
    }
    if (margin.length && !notBelow.length && !notThin.length) {
      report(
        NOTE,
        'pricing-coherence',
        `${count(belowCost.length)} below-cost and ${count(thin.length)} thin-margin rows of ${count(margin.length)} published margin entries, each consistent with its own evidence`,
      )
    }
  }

  // ── 6. Can the owner identify what he is being asked to act on? ──────
  // The successor to the uncategorised-products check. An entry the owner cannot
  // locate on a shelf is an entry he cannot action, whatever else is right
  // about it.
  {
    const nameless = entries.filter((e) => !e.barcode && !e.product_name)
    const departmentless = entries.filter((e) => !e.department)

    if (nameless.length) {
      report(
        WARN,
        'identification',
        `${count(nameless.length)} of ${count(entries.length)} published entries carry neither a barcode nor a product name`,
        'EntryCard falls back to "unnamed"; the owner cannot find the product.',
      )
    }
    if (departmentless.length) {
      report(
        WARN,
        'identification',
        `${count(departmentless.length)} of ${count(entries.length)} published entries carry no department`,
        'Findable by name, but not groupable by aisle.',
      )
    }
    if (!nameless.length && !departmentless.length) {
      report(NOTE, 'identification', `all ${count(entries.length)} published entries are identifiable`)
    }
  }

  // ── 7. Run health (CLAUDE.md rule 10) ────────────────────────────────
  // An empty export is a failure, not a result — and so is a partial one that
  // reports success. A step that failed while the run still published means the
  // owner is reading a surface with a silent hole in it.
  {
    const steps = artefact.run?.steps ?? []
    const failed = steps.filter((step) => step.status && step.status !== 'ok')
    if (failed.length) {
      report(
        ERROR,
        'run-health',
        `${count(failed.length)} of ${count(steps.length)} run steps did not succeed, yet the artefact was published: ${failed.map((s) => `${s.step} (${s.status})`).join(', ')}`,
        'Rule 10: an incomplete export is a failure, not a result. The owner cannot see which half is missing.',
      )
    } else if (steps.length) {
      report(NOTE, 'run-health', `all ${count(steps.length)} run steps succeeded`)
    }
  }

  // ── 8. What this run can no longer tell you ──────────────────────────
  // Stated every run, on purpose. A capability that quietly stops being checked
  // is indistinguishable from one that passes.
  report(
    NOTE,
    'retired',
    'velocity confidence is not checked: Entry carries no velocity field (INV-005), and the catalogue that has one is gitignored',
    'Catalogue-wide velocity and pricing censuses belong in the export path, where the parquet exists. Not approximated here.',
  )

  return findings
}

/** ERROR count, which is what the exit code is made of. */
export const errorsIn = (findings) => findings.filter((f) => f.level === ERROR).length
