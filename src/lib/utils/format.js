/**
 * Formatting utilities for locale-correct value rendering.
 * All functions return Unicode LTR-isolated strings (LRI \u2066 ... PDI \u2069)
 * safe to place or embed next to Hebrew text without direction corruption.
 */

// Unicode BiDi Isolation Constants
// LRI (Left-to-Right Isolate): U+2066 - Starts an LTR directional isolate
// PDI (Pop Directional Isolate): U+2069 - Ends a directional isolate boundary
const LRI = '\u2066';
const PDI = '\u2069';

/**
 * Helper to determine if an input value is invalid for formatting.
 * Considers null, undefined, NaN, Infinity, -Infinity, empty strings, and whitespace.
 * @param {any} value
 * @returns {boolean}
 */
function isInvalidValue(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === 'number') {
    return !Number.isFinite(value);
  }
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (
      trimmed === '' ||
      trimmed === 'NaN' ||
      trimmed === 'null' ||
      trimmed === 'undefined' ||
      trimmed === 'Infinity' ||
      trimmed === '-Infinity'
    ) {
      return true;
    }
  }
  return false;
}

/**
 * Formats a numeric value into Shekels (₪).
 * Returns an em-dash ('—') if value is null, undefined, NaN, or invalid.
 * @param {number|string|null|undefined} value
 * @returns {string} LTR-isolated currency string or '—'
 */
export function formatShekel(value) {
  if (isInvalidValue(value)) return '—';
  const num = Number(value);
  if (!Number.isFinite(num)) return '—';

  const absNum = Math.abs(num);
  const formatted = absNum.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  if (num < 0) {
    return `${LRI}-₪${formatted}${PDI}`;
  }
  return `${LRI}₪${formatted}${PDI}`;
}

/**
 * Formats a percentage value.
 * Automatically converts 0..1 decimal ratios to percentage values unless specified.
 * Returns an em-dash ('—') for null, undefined, NaN, or invalid inputs.
 * @param {number|string|null|undefined} value
 * @param {number} [decimals=0]
 * @param {boolean} [isDecimalRate=false]
 * @returns {string} LTR-isolated percentage string or '—'
 */
export function formatPercent(value, decimals = 0, isDecimalRate = false) {
  if (isInvalidValue(value)) return '—';
  let num = Number(value);
  if (!Number.isFinite(num)) return '—';

  if (isDecimalRate || (Math.abs(num) <= 1 && num !== 0 && num !== 1 && num !== -1)) {
    num = num * 100;
  }

  const formatted = num.toFixed(decimals);
  return `${LRI}${formatted}%${PDI}`;
}

/**
 * Formats a date value safely into an LTR-isolated string.
 * Returns an em-dash ('—') for null, undefined, or invalid dates.
 * @param {string|Date|number|null|undefined} dateVal
 * @returns {string} LTR-isolated date string or '—'
 */
export function formatDate(dateVal) {
  if (isInvalidValue(dateVal)) return '—';

  if (typeof dateVal === 'string') {
    const trimmed = dateVal.trim();
    if (isInvalidValue(trimmed)) return '—';
    if (/^\d{4}-\d{2}-\d{2}/.test(trimmed)) {
      return `${LRI}${trimmed.slice(0, 10)}${PDI}`;
    }
  }

  const d = new Date(dateVal);
  if (isNaN(d.getTime())) {
    return '—';
  }

  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');

  return `${LRI}${year}-${month}-${day}${PDI}`;
}

/**
 * Formats a GTIN, SKU, or barcode identifier safely as an LTR-isolated string.
 * Prevents numeric digits from reversing in RTL layout contexts.
 * Returns an em-dash ('—') for null, undefined, NaN, Infinity, empty/whitespace strings.
 * @param {string|number|null|undefined} barcode
 * @returns {string} LTR-isolated barcode string or '—'
 */
export function formatBarcode(barcode) {
  if (isInvalidValue(barcode)) return '—';
  const str = String(barcode).trim();
  if (isInvalidValue(str)) return '—';
  return `${LRI}${str}${PDI}`;
}
