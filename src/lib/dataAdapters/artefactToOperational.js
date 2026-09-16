/**
 * artefactToOperational — let the restored twelve-page UI read the live engine.
 *
 * WHY THIS EXISTS
 *   The old pages were written against `public/data/operational.json`, produced by a
 *   pipeline that stopped on 2026-09-13 and cannot honestly be restarted: its recommender
 *   required a silver table Task 0.6 deleted for synthesising a 30-day sales figure from
 *   monthly reports (rule 13). That file is now frozen — a rollback target, not a feed.
 *
 *   The engine publishes `public/data/dashboard.json` instead, nightly, and it is the only
 *   live source. This maps one onto the other so the pages the owner asked for read today's
 *   data rather than a still photograph of 2026-09-13.
 *
 * WHAT IT DOES NOT DO
 *   It does not invent the fields the artefact has no answer for. Everything below is read
 *   from the artefact or left absent; nothing is defaulted to zero to make a card render.
 *   Specifically absent, and absent on purpose:
 *
 *     expiry            the engine publishes no expiry capability. `ExpiryPage` gets the
 *                       empty shape and says so, rather than a confident set of zero alerts.
 *     salesLast7Days    no silver POS table carries any sales or velocity column. This is
 *     salesLast30Days   what Reorder and the planogram screens need, and why they come back
 *                       empty. See navGroups.js.
 *     supplier          in yomyom_products.parquet, not in the artefact. `ApprovedOrdersPage`
 *                       groups by it, so it groups under one heading until the engine
 *                       publishes a catalogue.
 *
 * D-1 IS ENFORCED HERE, NOT LEFT TO THE PAGE
 *   `recon.impossible_opening` maps to `CHECK_STOCK_DISCREPANCY`, and the old ranker prices
 *   that type as `metricValue * costPrice` — the shortfall in units, valued at cost. Over
 *   the frozen artefact that is 458 findings summing to ₪103,828.75, led by ₪8,718.96.
 *
 *   D-1 says a signal derived from stock quantities carries no shekel figure at all, because
 *   the manager said the counts are unreliable in both directions. The engine honours it:
 *   all 439 reconciliation entries publish `value: null`. So this adapter does not emit
 *   `costPrice` on a reconciliation row — without a cost the old ranker already returns null
 *   rather than guessing, which is exactly the behaviour D-1 wants, reached through the code
 *   path the old page already has.
 *
 *   The finding still surfaces. It is the *price* on it that does not.
 */

/** Old recommendation type per new signal family. Families absent here are not surfaced. */
const TYPE_BY_FAMILY = {
  'price.inverted': 'CHECK_WOLT_PRICE_GAP',
  'price.above_ceiling': 'CHECK_WOLT_PRICE_GAP',
  'margin.below_cost': 'CHECK_MARGIN',
  'recon.impossible_opening': 'CHECK_STOCK_DISCREPANCY',
  'hygiene.negative_stock': 'CHECK_NEGATIVE_STOCK',
  'hygiene.no_identifier': 'VERIFY_UNKNOWN_BARCODE',
  'hygiene.absent_price': 'VERIFY_UNKNOWN_BARCODE',
  'hygiene.conflicting_duplicate': 'VERIFY_UNKNOWN_BARCODE',
}

/** Families whose money must never reach the old ranker. See the D-1 note above. */
const QUANTITY_DERIVED = new Set(['recon.impossible_opening', 'hygiene.negative_stock'])

const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : null)

/**
 * The figure the old card shows beside the type. Read from the evidence the engine
 * published for that family — never recomputed, so the two UIs cannot disagree.
 */
function metricFor(family, evidence) {
  switch (family) {
    case 'price.inverted':
    case 'price.above_ceiling':
      return num(evidence.markup_pct) ?? num(evidence.difference)
    case 'margin.below_cost':
      return num(evidence.margin_pct)
    case 'recon.impossible_opening':
      return num(evidence.unaccounted)
    case 'hygiene.negative_stock':
      return num(evidence.recorded_stock)
    default:
      return null
  }
}

function toRecommendation(entry, capabilityId) {
  const family = entry.signal_family
  const type = TYPE_BY_FAMILY[family]
  if (!type) return null
  const ev = entry.evidence || {}
  const quantityDerived = QUANTITY_DERIVED.has(family)

  return {
    id: entry.id,
    type,
    family,
    capability: capabilityId,
    productName: entry.product_name ?? null,
    barcode: entry.barcode ?? null,
    category: entry.department ?? null,
    sellingPrice: num(ev.shelf_price),
    woltPrice: num(ev.delivery_price),
    // Withheld on a quantity-derived family so the old ranker states no figure (D-1).
    costPrice: quantityDerived ? null : num(ev.cost_price),
    metricValue: metricFor(family, ev),
    reason: entry.characterisation ?? null,
    confidence: entry.value?.certainty ?? null,
    severity: entry.attention ? 'high' : 'normal',
  }
}

/**
 * `posHealth` from the engine's own counts. Every number here is read from
 * `capabilities.*.counts` or `figures`, so the old header cannot drift from the new pages.
 */
function posHealthFrom(artefact) {
  const counts = artefact?.capabilities?.hygiene?.counts || {}
  const figures = artefact?.figures || {}
  const figure = (name) => num(figures[name]?.value)
  const entryCount = (id) => (artefact?.capabilities?.[id]?.entries || []).length

  return {
    totalProducts: figure('competitor_position.catalogue') ?? 0,
    missingBarcode: counts.no_identifier ?? 0,
    zeroPrice: counts.absent_price ?? 0,
    // The engine asks the owner for a cost rather than counting absences, so there is no
    // equivalent. Reported as the open question count, which is the honest nearest thing.
    zeroCost: entryCount('owner_questions'),
    negativeStock: counts.negative_stock ?? 0,
    woltPriceGaps: entryCount('price_consistency'),
    marginRisks: entryCount('margin_below_cost'),
    sourceFile: artefact?.vintages?.pos?.file ?? null,
  }
}

/**
 * The source strip along the bottom of the old Today page, rebuilt from `vintages`.
 * `sources.json` was retired by ADR-005 at the cut-over, so this is where provenance now
 * lives — and it carries the vintage's own honesty with it: `as_of_source` says whether the
 * POS date was declared by a human or inferred, which the old strip never showed.
 */
function sourcesFrom(artefact) {
  const v = artefact?.vintages || {};
  const rows = []
  if (v.pos) {
    rows.push({
      source_id: 'yomyom_pos',
      label: v.pos.file ?? 'POS export',
      status: v.pos.as_of ? 'complete' : 'not_started',
      last_updated: v.pos.as_of ?? null,
      as_of_source: v.pos.as_of_source ?? null,
      row_count: null,
    })
  }
  if (v.competitor) {
    rows.push({
      source_id: 'competitor',
      label: (v.competitor.sources || []).join(' · ') || 'competitor',
      status: v.competitor.snapshot_date ? 'complete' : 'not_started',
      last_updated: v.competitor.snapshot_date ?? null,
      row_count: v.competitor.store_count ?? null,
    })
  }
  if (v.sales) {
    rows.push({
      source_id: 'sales_reports',
      label: `${v.sales.first ?? '?'} … ${v.sales.last ?? '?'}`,
      status: (v.sales.months || []).length ? 'complete' : 'not_started',
      last_updated: v.sales.last ?? null,
      row_count: (v.sales.months || []).length,
    })
  }
  return rows
}

/**
 * Capabilities the engine could not run today, carried through so the old page can say so.
 *
 * The old UI has no place for this and treats an empty list as "all clear" — the single
 * biggest thing it loses. Passing it through lets `OperationalPage` distinguish "nothing to
 * do" from "we could not look", without which a capability that never ran reads as success.
 */
function unavailableFrom(artefact) {
  return Object.entries(artefact?.capabilities || {})
    .filter(([, c]) => c.status === 'unavailable')
    .map(([id, c]) => ({ id, reason: c.unavailable_reason ?? null }))
}

/** `dashboard.json` → the shape the pre-cut-over pages read. */
export function artefactToOperational(artefact) {
  if (!artefact) return null

  const capabilities = artefact.capabilities || {}
  const recommendations = Object.entries(capabilities)
    .flatMap(([id, c]) => (c.entries || []).map((e) => toRecommendation(e, id)))
    .filter(Boolean)

  const byType = {}
  const byFamily = {}
  for (const r of recommendations) {
    byType[r.type] = (byType[r.type] || 0) + 1
    byFamily[r.family] = (byFamily[r.family] || 0) + 1
  }

  return {
    meta: {
      generatedAt: artefact.generated_at ?? null,
      status: artefact.run?.status ?? 'unavailable',
      competitorSignals: artefact.vintages?.competitor?.store_count ?? 0,
      competitorRecommendations: (capabilities.competitor_position?.entries || []).length,
      scrapingStatus: artefact.vintages?.competitor?.snapshot_date ? 'complete' : 'not_started',
      // New, and the reason this adapter is not a pure translation: the old shape has no
      // way to say a capability did not run.
      unavailable: unavailableFrom(artefact),
      population: artefact.population ?? null,
    },
    posHealth: posHealthFrom(artefact),
    // The engine publishes no expiry capability. Absent, not zeroed — see the header.
    expiry: null,
    byType,
    byFamily,
    sources: sourcesFrom(artefact),
    recommendations,
  }
}
