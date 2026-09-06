/**
 * Single source of truth for category accent colors used across the app.
 * Muted palette tuned for the dark planogram surface but readable anywhere.
 * Keep this list aligned with the categories present in demoProducts.js.
 */
export const CATEGORY_COLORS = Object.freeze({
  'Cold Drinks': '#5fa8ff',
  'Water': '#7dcfe0',
  'Energy Drinks': '#e98a4f',
  'Snacks': '#f0c14a',
  'Chocolate': '#b9744d',
  'Gum & Candy': '#e08fbf',
  'Dairy': '#e8e2c7',
  'Bakery': '#d6a96b',
  'Ice Cream': '#bfd6ec',
  'Coffee': '#9b6f3a',
  'Cigarettes': '#8c8c8c',
  'Car Accessories': '#8aa0b3',
})

export const FALLBACK_CATEGORY_COLOR = '#94a3b8'

export function getCategoryColor(category) {
  return CATEGORY_COLORS[category] ?? FALLBACK_CATEGORY_COLOR
}
