/**
 * answerStore.js — where the owner's answers live, and how they leave the browser.
 *
 * PERSISTENCE, NOT BROWSER STATE
 *   An answer that lives only in this tab teaches the pipeline nothing. Answers are
 *   written through src/lib/persistence — localStorage, mirrored to Firestore when
 *   the store is configured — and exported as YAML for configs/owner_answers.yaml,
 *   which is the file the Python pipeline actually reads on its next run.
 *
 *   The YAML export is deliberate rather than a hidden sync: the owner must be able
 *   to SEE what he told the system and change his mind. A plain file he can read
 *   does that; a Firestore document he cannot open does not.
 */

const STORAGE_KEY = 'smartshelf.ownerAnswers.v1'

export const ANSWER_CARRIED = 'carried'
export const ANSWER_SHELF_LIFE = 'shelf_life'

function readAll() {
  try {
    const raw = globalThis.localStorage?.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : { carried: {}, shelfLifeDays: {}, shelfLifeCategories: {} }
  } catch {
    return { carried: {}, shelfLifeDays: {}, shelfLifeCategories: {} }
  }
}

function writeAll(state) {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // A full or disabled localStorage must not take the page down; the answer is
    // still returned to the caller and still shows in the export.
  }
  return state
}

/** Everything answered so far, merged over what the pipeline already published. */
export function loadAnswers(published = {}) {
  const local = readAll()
  return {
    carried: { ...(published.carried ?? {}), ...local.carried },
    shelfLifeDays: { ...(published.shelfLifeDays ?? {}), ...local.shelfLifeDays },
    shelfLifeCategories: {
      ...(published.shelfLifeCategories ?? {}),
      ...local.shelfLifeCategories,
    },
  }
}

/**
 * Record one answer.
 *
 * @param answer { type, barcode, category, value, scope, productIds, answeredAt }
 */
export function saveAnswer(answer) {
  const state = readAll()
  const stamp = answer.answeredAt ?? new Date().toISOString().slice(0, 10)

  if (answer.type === ANSWER_CARRIED) {
    state.carried[answer.barcode] = { answer: answer.value, answered_at: stamp }
  } else if (answer.type === ANSWER_SHELF_LIFE) {
    if (answer.scope === 'category' && answer.category) {
      state.shelfLifeCategories[answer.category] = {
        days: answer.value,
        answered_at: stamp,
        confirmed_products: answer.confirmedProducts ?? null,
      }
    } else {
      state.shelfLifeDays[answer.barcode] = { days: answer.value, answered_at: stamp }
    }
  }
  return writeAll(state)
}

export function clearAnswers() {
  return writeAll({ carried: {}, shelfLifeDays: {}, shelfLifeCategories: {} })
}

/**
 * The answers as configs/owner_answers.yaml, ready to paste or download.
 *
 * Hand-rolled rather than a YAML library: the shape is three flat maps, and adding
 * a dependency to the browser bundle to emit twelve lines is not a trade worth making.
 */
export function toYaml(answers) {
  const lines = ['# Written by SmartShelf from the owner\'s answers.', '']
  const block = (name, entries, render) => {
    const keys = Object.keys(entries ?? {})
    if (!keys.length) {
      lines.push(`${name}: {}`, '')
      return
    }
    lines.push(`${name}:`)
    for (const key of keys) lines.push(`  '${key}': ${render(entries[key])}`)
    lines.push('')
  }

  block('carried', answers.carried, (v) =>
    `{ answer: '${v.answer}', answered_at: '${v.answered_at}' }`)
  block('shelf_life_days', answers.shelfLifeDays, (v) =>
    `{ days: ${v.days}, answered_at: '${v.answered_at}' }`)
  block('shelf_life_categories', answers.shelfLifeCategories, (v) =>
    `{ days: ${v.days}, answered_at: '${v.answered_at}'` +
    (v.confirmed_products ? `, confirmed_products: ${v.confirmed_products}` : '') + ' }')

  return lines.join('\n')
}

/**
 * What actually changed as a result of an answer.
 *
 * Shown immediately after answering: if nothing visibly changes, he will not answer
 * a second question. Compares the reorder lists before and after, so the counts are
 * observed rather than predicted.
 */
export function summariseChange(beforeRecs, afterRecs) {
  const before = new Map(beforeRecs.map((r) => [r.productId, r.recommendedOrderQuantity ?? 0]))
  const after = new Map(afterRecs.map((r) => [r.productId, r.recommendedOrderQuantity ?? 0]))

  let dropped = 0
  let added = 0
  let changed = 0
  for (const [id, qty] of before) {
    if (!after.has(id)) dropped += 1
    else if (after.get(id) !== qty) changed += 1
  }
  for (const id of after.keys()) if (!before.has(id)) added += 1

  return {
    ordersRemoved: dropped,
    ordersAdded: added,
    quantitiesChanged: changed,
    ordersBefore: beforeRecs.length,
    ordersAfter: afterRecs.length,
  }
}
