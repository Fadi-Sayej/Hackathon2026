/**
 * openQuestions.js — what the system should ask the owner, and in what order.
 *
 * The system knows exactly where it is guessing: whether a STOCKOUT_SUSPECTED line
 * was dropped on purpose, and how long a perishable actually keeps. Both guesses
 * drive real orders — we would otherwise recommend 80 units of something he
 * deliberately stopped carrying.
 *
 * RANKING
 *   money at stake x how many products the answer would affect. A shelf-life answer
 *   for a bakery category fixes every bakery line at once, so it outranks a single
 *   high-value product whose answer helps only itself.
 *
 * THE LIMIT IS THE FEATURE
 *   At most three on screen. Four makes it a form, and a form gets abandoned — at
 *   which point the system learns nothing and keeps guessing.
 */

export const MAX_QUESTIONS_ON_SCREEN = 3

export const QUESTION_CARRIED = 'carried'
export const QUESTION_SHELF_LIFE = 'shelf_life'

function keyOf(product) {
  return product.barcode ?? product.id
}

/** Products whose availability the system genuinely cannot resolve on its own. */
function needsCarriedAnswer(product, answered) {
  return (
    product.availabilityState === 'STOCKOUT_SUSPECTED' && !answered.carried?.[keyOf(product)]
  )
}

/**
 * Perishable-looking products with no owner shelf life yet.
 *
 * "Perishable-looking" is deliberately the category table's own opinion: if the
 * category carries a shelf-life default, an answer would improve it. Categories
 * marked non-perishable are never asked about.
 */
function needsShelfLifeAnswer(product, shelfLife, answered) {
  const category = product.category
  if (!category) return false
  if (answered.shelfLifeCategories?.[category]) return false
  if (answered.shelfLifeDays?.[keyOf(product)]) return false
  const days = shelfLife?.categories?.[category]
  return typeof days === 'number' && days > 0
}

/**
 * Build the ranked question list.
 *
 * @param products         normalized products
 * @param recommendations  reorder recommendations, for money at stake
 * @param context          { shelfLife, ownerAnswers }
 */
export function buildOpenQuestions(products = [], recommendations = [], context = {}) {
  const answered = context.ownerAnswers ?? {}
  const shelfLife = context.shelfLife ?? {}

  // Money at stake per product, taken from the decision that already ranked them —
  // not recomputed here.
  const valueByProduct = new Map()
  for (const rec of recommendations) {
    if (rec.type !== 'REORDER') continue
    valueByProduct.set(
      rec.productId,
      Math.max(valueByProduct.get(rec.productId) ?? 0, rec.valueAtStake ?? 0),
    )
  }

  // How many products one answer would settle. A category answer travels.
  const perCategory = new Map()
  for (const product of products) {
    if (!product.category) continue
    perCategory.set(product.category, (perCategory.get(product.category) ?? 0) + 1)
  }

  const questions = []
  for (const product of products) {
    const value = valueByProduct.get(product.id) ?? 0

    if (needsCarriedAnswer(product, answered)) {
      questions.push({
        id: `carried:${keyOf(product)}`,
        type: QUESTION_CARRIED,
        productId: product.id,
        barcode: product.barcode ?? null,
        productName: product.name,
        category: product.category,
        productsAffected: 1,
        moneyAtStake: value,
        score: value,
      })
    }

    if (needsShelfLifeAnswer(product, shelfLife, answered)) {
      const affected = perCategory.get(product.category) ?? 1
      questions.push({
        id: `shelf_life:${product.category}`,
        type: QUESTION_SHELF_LIFE,
        productId: product.id,
        barcode: product.barcode ?? null,
        productName: product.name,
        category: product.category,
        productsAffected: affected,
        moneyAtStake: value,
        currentGuessDays: shelfLife.categories?.[product.category] ?? null,
        // A category answer fixes every line in it, so it is worth more than its
        // own product's value alone suggests.
        score: value * Math.log10(affected + 1) * 10,
      })
    }
  }

  // One question per category for shelf life: asking about six bakery items
  // separately is exactly the form we are trying not to build.
  const seen = new Set()
  const deduped = []
  for (const question of questions.sort((a, b) => b.score - a.score)) {
    if (seen.has(question.id)) continue
    seen.add(question.id)
    deduped.push(question)
  }
  return deduped
}

/** The at-most-three he actually sees. */
export function topQuestions(questions, limit = MAX_QUESTIONS_ON_SCREEN) {
  return questions.slice(0, limit)
}

/**
 * What answering would change, stated before he answers. Counts only — the
 * direction cannot be known until the answer exists.
 */
export function questionImpact(question, products = []) {
  if (question.type === QUESTION_SHELF_LIFE) {
    return {
      productsAffected: products.filter((p) => p.category === question.category).length,
      moneyAtStake: question.moneyAtStake,
    }
  }
  return { productsAffected: 1, moneyAtStake: question.moneyAtStake }
}
