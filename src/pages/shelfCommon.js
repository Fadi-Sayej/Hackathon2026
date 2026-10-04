import { useI18n } from '../lib/i18n/index.js'

/**
 * What Store layout and Shelf plan share (F12-S1): dates in the page's language, a count of
 * facings in each language's own form, product names from the catalogue, and his rules in words.
 *
 * Nothing here computes a figure (ADR-001). Every number the pages show is a field the engine
 * published; these only choose the words around it.
 */

const LOCALE = { ar: 'ar-u-nu-latn', he: 'he-IL', en: 'en-GB' }

export function useDates() {
  const { language } = useI18n()
  const locale = LOCALE[language] || LOCALE.en
  const at = (iso) => new Date(`${iso}T00:00:00Z`)
  return {
    date: (iso) => (iso ? new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(at(iso)) : ''),
    long: (iso) => (iso ? new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(at(iso)) : ''),
    number: (x, digits = 2) => new Intl.NumberFormat(locale, { maximumFractionDigits: digits }).format(x),
    // Two decimals always, so 0.17 and 0.20, or ×1.56 and ×0.90, line up when read side by side.
    fixed: (x) => new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(x),
    percent: (x) => new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 0 }).format(x),
  }
}

export function facingsText(n, language) {
  if (language === 'he') return n === 1 ? 'חזית אחת' : n === 2 ? 'שתי חזיתות' : `${n} חזיתות`
  if (language === 'ar') return n === 1 ? 'واجهة واحدة' : n === 2 ? 'واجهتان' : n <= 10 ? `${n} واجهات` : `${n} واجهة`
  return n === 1 ? '1 facing' : `${n} facings`
}

export function daysText(n, language) {
  if (language === 'he') return n === 1 ? 'יום אחד' : n === 2 ? 'יומיים' : `${n} ימים`
  if (language === 'ar') return n === 1 ? 'يوم واحد' : n === 2 ? 'يومين' : n <= 10 ? `${n} أيام` : `${n} يومًا`
  return n === 1 ? '1 day' : `${n} days`
}

/** barcode → name, from the catalogue the page was given. A barcode stands in for a missing name. */
export function namesFrom(catalogue, extra = []) {
  const names = new Map()
  for (const p of catalogue?.products || []) if (p.barcode) names.set(String(p.barcode), p.product_name)
  for (const p of extra) if (p.barcode && p.product_name) names.set(String(p.barcode), p.product_name)
  return (barcode) => names.get(String(barcode)) || String(barcode)
}

/** One of his rules, in his words (F12-S1 FR-188). */
export function ruleText(t, rule, nameOf) {
  const name = rule.barcode ? nameOf(rule.barcode) : null
  if (rule.kind === 'together') {
    return rule.department
      ? t('shelf.rule.togetherDepartment', { department: rule.department })
      : t('shelf.rule.together', { names: (rule.barcodes || []).map(nameOf).join(' · ') })
  }
  return t(`shelf.rule.${rule.kind}`, { name, n: rule.facings, fixture: rule.fixture })
}
