const COMPLIANCE_STATES = {
  CORRECT: 'CORRECT',
  MISPLACED: 'MISPLACED',
  WRONG_FACINGS: 'WRONG_FACINGS',
  MISSING: 'MISSING',
  UNEXPECTED: 'UNEXPECTED',
}

const SHELF_LEVEL_LABELS = {
  EYE_LEVEL: 'Eye level',
  MIDDLE: 'Middle shelf',
  TOP: 'Top shelf',
  BOTTOM: 'Bottom shelf',
}

export function analyzeCompliance(idealPlanogram, detectedShelf) {
  const idealMap = new Map(idealPlanogram.map((item) => [item.productId, item]))
  const detectedMap = new Map(detectedShelf.map((item) => [item.productId, item]))

  const results = []

  for (const [productId, ideal] of idealMap) {
    const detected = detectedMap.get(productId)
    if (!detected) {
      results.push({
        productId,
        productName: ideal.productName,
        state: COMPLIANCE_STATES.MISSING,
        idealShelf: ideal.shelfLevel,
        idealShelfLabel: SHELF_LEVEL_LABELS[ideal.shelfLevel],
        detectedShelf: null,
        idealFacings: ideal.facings,
        detectedFacings: 0,
        message: `${ideal.productName} is missing from the shelf`,
      })
    } else if (detected.shelfLevel !== ideal.shelfLevel) {
      results.push({
        productId,
        productName: ideal.productName,
        state: COMPLIANCE_STATES.MISPLACED,
        idealShelf: ideal.shelfLevel,
        idealShelfLabel: SHELF_LEVEL_LABELS[ideal.shelfLevel],
        detectedShelf: detected.shelfLevel,
        detectedShelfLabel: SHELF_LEVEL_LABELS[detected.shelfLevel],
        idealFacings: ideal.facings,
        detectedFacings: detected.facings,
        message: `${ideal.productName} should be on ${SHELF_LEVEL_LABELS[ideal.shelfLevel]} but found on ${SHELF_LEVEL_LABELS[detected.shelfLevel]}`,
      })
    } else if (Math.abs(detected.facings - ideal.facings) > 0) {
      results.push({
        productId,
        productName: ideal.productName,
        state: COMPLIANCE_STATES.WRONG_FACINGS,
        idealShelf: ideal.shelfLevel,
        idealShelfLabel: SHELF_LEVEL_LABELS[ideal.shelfLevel],
        detectedShelf: detected.shelfLevel,
        idealFacings: ideal.facings,
        detectedFacings: detected.facings,
        message: `${ideal.productName} has ${detected.facings} facings instead of ${ideal.facings}`,
      })
    } else {
      results.push({
        productId,
        productName: ideal.productName,
        state: COMPLIANCE_STATES.CORRECT,
        idealShelf: ideal.shelfLevel,
        idealShelfLabel: SHELF_LEVEL_LABELS[ideal.shelfLevel],
        detectedShelf: detected.shelfLevel,
        idealFacings: ideal.facings,
        detectedFacings: detected.facings,
        message: `${ideal.productName} is correctly placed`,
      })
    }
  }

  for (const [productId, detected] of detectedMap) {
    if (!idealMap.has(productId)) {
      results.push({
        productId,
        productName: detected.productName,
        state: COMPLIANCE_STATES.UNEXPECTED,
        idealShelf: null,
        detectedShelf: detected.shelfLevel,
        detectedShelfLabel: SHELF_LEVEL_LABELS[detected.shelfLevel],
        idealFacings: 0,
        detectedFacings: detected.facings,
        message: `${detected.productName} is on the shelf but not in the planogram`,
      })
    }
  }

  const correct = results.filter((r) => r.state === COMPLIANCE_STATES.CORRECT).length
  const total = idealMap.size
  const score = total > 0 ? correct / total : 0

  return {
    score,
    totalIdeal: total,
    correctCount: correct,
    misplacedCount: results.filter((r) => r.state === COMPLIANCE_STATES.MISPLACED).length,
    wrongFacingsCount: results.filter((r) => r.state === COMPLIANCE_STATES.WRONG_FACINGS).length,
    missingCount: results.filter((r) => r.state === COMPLIANCE_STATES.MISSING).length,
    unexpectedCount: results.filter((r) => r.state === COMPLIANCE_STATES.UNEXPECTED).length,
    items: results,
  }
}

export function generateMockDetectedShelf(idealPlanogram) {
  const shelfLevels = ['EYE_LEVEL', 'MIDDLE', 'TOP', 'BOTTOM']
  const detected = []

  for (const item of idealPlanogram) {
    const rand = Math.random()

    if (rand < 0.12) {
      continue
    }

    if (rand < 0.28) {
      const otherLevels = shelfLevels.filter((l) => l !== item.shelfLevel)
      detected.push({
        ...item,
        shelfLevel: otherLevels[Math.floor(Math.random() * otherLevels.length)],
      })
    } else if (rand < 0.40) {
      const facingDelta = Math.random() > 0.5 ? 1 : -1
      detected.push({
        ...item,
        facings: Math.max(1, item.facings + facingDelta),
      })
    } else {
      detected.push({ ...item })
    }
  }

  return detected
}

export { COMPLIANCE_STATES }
