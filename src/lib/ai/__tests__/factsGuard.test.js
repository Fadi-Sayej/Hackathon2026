/**
 * The model may rephrase around figures it is given. It may not produce one.
 *
 * The case that motivated this is real: asked to rephrase "order 20 units",
 * gemini-3.5-flash-lite wrote "25 units" on the first attempt (2026-09-08). The
 * owner checks these against his shelf, so a single invented figure discredits
 * every other number on the screen.
 */
import { describe, expect, it } from 'vitest'
import {
  allowedNumbers,
  numbersIn,
  validateAgainstFacts,
  validateExplanationResult,
} from '../factsGuard.js'

const facts = {
  currentStock: 0,
  dailyRate: 8.38,
  leadTimeDays: 3,
  expectedDemandDuringLeadTime: 25.14,
  safetyStock: 25.14,
  orderQty: 20,
  uncappedOrderQty: 51,
  shelfLifeDays: 2,
  coverDays: 0,
  censoredDays: 30,
  costToIgnore: 138.27,
  unitCost: 5.5,
  caseSize: null,
  demandMultiplier: 1.2,
  competitorLift: 1,
}

describe('what the model is allowed to say', () => {
  it('accepts text using only figures the decision held', () => {
    const text = 'מלאי 0, קצב 8.38 ליום, זמן אספקה 3 ימים, להזמין 20 יחידות.'
    expect(validateAgainstFacts(text, facts).ok).toBe(true)
  })

  it('rejects a figure that appears nowhere in the decision', () => {
    const text = 'מומלץ להזמין 47 יחידות.'
    const result = validateAgainstFacts(text, facts)
    expect(result.ok).toBe(false)
    expect(result.invented).toContain(47)
  })

  it('does NOT catch a real figure attached to the wrong thing — a stated limit', () => {
    // The live model, given orderQty 20, wrote "order 25 units". 25 is a true
    // rounding of expectedDemandDuringLeadTime (25.14), so the numeric check
    // passes while the sentence tells the owner the wrong quantity. Asserted so
    // nobody mistakes this guard for protection against misapplication.
    const text = 'מומלץ להזמין 25 יחידות.'
    expect(validateAgainstFacts(text, facts).ok).toBe(true)
  })

  it('allows prose to round a rate', () => {
    // 8.38/day written as 8.4 or 8 is rounding, not invention.
    expect(validateAgainstFacts('כ-8.4 ליום', facts).ok).toBe(true)
    expect(validateAgainstFacts('כ-8 ליום', facts).ok).toBe(true)
  })

  it('accepts a derived percentage the renderer itself prints', () => {
    // demandMultiplier 1.2 -> "20%" is a figure the rule-based text also prints.
    expect(validateAgainstFacts('גבוה בכ-20% מהרגיל', facts).ok).toBe(true)
  })

  it('reads Arabic-Indic digits, so an Arabic response cannot smuggle a number', () => {
    expect(numbersIn('اطلب ٤٧ وحدة')).toContain(47)
    expect(validateAgainstFacts('اطلب ٤٧ وحدة', facts).ok).toBe(false)
  })

  it('treats a null field as carrying no permission', () => {
    // caseSize is null, so no case size may be stated at all.
    expect(validateAgainstFacts('באריזות של 24 יחידות', facts).ok).toBe(false)
  })

  it('permits text with no numbers at all', () => {
    expect(validateAgainstFacts('המלאי אזל, כדאי להזמין בהקדם.', facts).ok).toBe(true)
  })
})

describe('validating a whole provider result', () => {
  const clean = {
    explanation: 'מלאי 0, להזמין 20 יחידות.',
    riskReason: 'המלאי אזל.',
    businessImpact: 'עלות של כ-138.27 ₪.',
    confidenceNote: 'זמן האספקה 3 ימים הוא הנחה.',
  }

  it('passes a result whose every field checks out', () => {
    expect(validateExplanationResult(clean, facts).ok).toBe(true)
  })

  it('rejects the entire result when any single field invents a figure', () => {
    const dirty = { ...clean, confidenceNote: 'מבוסס על 14,406 התאמות.' }
    const result = validateExplanationResult(dirty, facts)
    expect(result.ok).toBe(false)
    expect(result.field).toBe('confidenceNote')
    // Half-trustworthy is not trustworthy: the clean fields go too.
    expect(result.invented.length).toBeGreaterThan(0)
  })

  it('rejects rather than accepts when there are no facts to check against', () => {
    expect(validateExplanationResult(clean, null).ok).toBe(false)
  })

  it('ignores non-string fields instead of throwing on them', () => {
    expect(validateExplanationResult({ ...clean, businessImpact: null }, facts).ok).toBe(true)
  })
})

describe('allowedNumbers', () => {
  it('never permits a figure absent from the record', () => {
    const allowed = allowedNumbers(facts)
    expect(allowed.has(20)).toBe(true)
    expect(allowed.has(47)).toBe(false)
    // floor/ceil are not permitted: 51 is uncappedOrderQty, but 52 is nothing.
    expect(allowed.has(52)).toBe(false)
  })

  it('is empty without facts, so nothing can pass unchecked', () => {
    expect(allowedNumbers(null).size).toBe(0)
  })
})

describe('numbers inside the product name are the name, not a claim', () => {
  const named = { ...facts, productName: 'קוקה קולה זירו 1.5 ליטר', orderQty: 19 }

  it('lets the model repeat a size that is part of the name', () => {
    // Before this, 2 of 10 real products were flagged as fabricating "1.5" when
    // the model had simply written the product's own name correctly.
    const text = 'מומלץ להזמין 19 יחידות של קוקה קולה זירו 1.5 ליטר.'
    expect(validateAgainstFacts(text, named).ok).toBe(true)
  })

  it('still rejects a genuine invention alongside the name', () => {
    const text = 'מומלץ להזמין 47 יחידות של קוקה קולה זירו 1.5 ליטר.'
    const result = validateAgainstFacts(text, named)
    expect(result.ok).toBe(false)
    expect(result.invented).toContain(47)
  })
})
