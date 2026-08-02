/**
 * Hebrew and RTL direction utilities.
 * Framework-agnostic primitives for handling RTL text, direction detection,
 * component props, and locale sorting.
 */

// Hebrew Unicode block range: U+0590 to U+05FF (Hebrew characters, points, accents)
const HEBREW_REGEX = /[\u0590-\u05FF]/;

/**
 * Checks whether a given string contains Hebrew characters.
 * @param {string|null|undefined} text
 * @returns {boolean}
 */
export function containsHebrew(text) {
  if (text === null || text === undefined) return false;
  return HEBREW_REGEX.test(String(text));
}

/**
 * Determines text direction ('rtl', 'ltr', or 'auto') based on content.
 * @param {string|null|undefined} text
 * @returns {'rtl' | 'ltr' | 'auto'}
 */
export function textDirection(text) {
  if (text === null || text === undefined) return 'auto';
  const str = String(text).trim();
  if (!str) return 'auto';
  return containsHebrew(str) ? 'rtl' : 'ltr';
}

/**
 * Returns spreadable props `{ dir: 'auto' }` for elements rendering dynamic text.
 * Enables semantic browser BiDi auto-detection. Always returns `{ dir: 'auto' }`.
 * @param {string|null|undefined} [_text]
 * @returns {{ dir: 'auto' }}
 */
export function dirProps() {
  return { dir: 'auto' };
}

/**
 * Compares two Hebrew strings using Hebrew locale ordering ('he').
 * Ensures correct Hebrew alphabetical sorting over code-point default sorting.
 * @param {string|null|undefined} a
 * @param {string|null|undefined} b
 * @returns {number}
 */
export function compareHebrew(a, b) {
  const strA = a === null || a === undefined ? '' : String(a);
  const strB = b === null || b === undefined ? '' : String(b);

  if (strA === strB) return 0;
  if (!strA) return 1;
  if (!strB) return -1;

  return strA.localeCompare(strB, 'he', {
    sensitivity: 'base',
    numeric: true,
  });
}
