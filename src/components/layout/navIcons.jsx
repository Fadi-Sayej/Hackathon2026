/* eslint-disable react-refresh/only-export-components -- This is a lookup
   table of static presentational glyphs, not a component module. The rule wants
   a file that defines components to export them so Fast Refresh can swap them;
   here the only export is the `navIcons` map, and the twelve icons are private
   to it deliberately — AppShell addresses them by nav id, never by name. Fast
   Refresh falls back to a full reload for this file, which costs nothing: the
   paths are constants and hold no state. */
/**
 * Navigation icons.
 *
 * These were ASCII characters — '!', 'R', 'O', '₪', 'P', 'E', 'D', 'A', 'C' —
 * rendered inside the icon chip, so the sidebar read as a column of stray
 * letters and the app looked unfinished before a word of it was read.
 *
 * Inline SVG rather than an icon package: twelve glyphs do not justify a
 * dependency, and these inherit `currentColor` so the active, hover and dark
 * sidebar states are already handled by the existing CSS.
 *
 * Each one is drawn on the same 24×24 grid at the same stroke weight, because
 * a set that mixes weights reads as clip-art. Keep that if you add to it.
 */

const base = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.6,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: 'false',
}

/** What needs the manager now — an alert, not a calendar. */
const Today = () => (
  <svg {...base} width="20" height="20">
    <path d="M12 3.5 21 19H3L12 3.5Z" />
    <path d="M12 10v4" />
    <path d="M12 16.6h.01" />
  </svg>
)

/** Reorder — a carton going back onto the shelf. */
const Reorder = () => (
  <svg {...base} width="20" height="20">
    <path d="M3 8.5 12 4l9 4.5v7L12 20l-9-4.5v-7Z" />
    <path d="M3 8.5 12 13l9-4.5" />
    <path d="M12 13v7" />
  </svg>
)

/** Approved orders — the clipboard he has already signed off. */
const Approved = () => (
  <svg {...base} width="20" height="20">
    <path d="M9 4h6v3H9z" />
    <path d="M15 5.5h2.5A1.5 1.5 0 0 1 19 7v12a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 19V7a1.5 1.5 0 0 1 1.5-1.5H9" />
    <path d="m9 13.5 2 2 4-4" />
  </svg>
)

/** Prices — a shelf tag. */
const Prices = () => (
  <svg {...base} width="20" height="20">
    <path d="M12.5 3H20a1 1 0 0 1 1 1v7.5a1 1 0 0 1-.3.7l-8.5 8.5a1 1 0 0 1-1.4 0l-7.5-7.5a1 1 0 0 1 0-1.4l8.5-8.5a1 1 0 0 1 .7-.3Z" />
    <path d="M16.5 7.5h.01" />
  </svg>
)

/** Assortment gap — a grid with one cell missing. */
const Assortment = () => (
  <svg {...base} width="20" height="20">
    <rect x="3.5" y="3.5" width="7" height="7" rx="1" />
    <rect x="13.5" y="3.5" width="7" height="7" rx="1" />
    <rect x="3.5" y="13.5" width="7" height="7" rx="1" />
    <path d="M13.5 17h7" strokeDasharray="2 2.4" />
    <path d="M17 13.5v7" strokeDasharray="2 2.4" />
  </svg>
)

/** Store layout — the floor seen from above. */
const StoreLayout = () => (
  <svg {...base} width="20" height="20">
    <rect x="3.5" y="4.5" width="17" height="15" rx="1.5" />
    <path d="M3.5 10.5h6" />
    <path d="M14.5 10.5h6" />
    <path d="M9.5 14.5h9" />
  </svg>
)

/** Shelf plan — product faces standing on a shelf. */
const ShelfPlan = () => (
  <svg {...base} width="20" height="20">
    <path d="M3.5 9.5h17" />
    <path d="M3.5 16.5h17" />
    <path d="M6 5.5v4M9.5 6.5v3M13 5.5v4" />
    <path d="M6 12.5v4M9.5 13.5v3M13 12.5v4M16.5 13.5v3" />
  </svg>
)

/** Products — the catalogue. */
const Products = () => (
  <svg {...base} width="20" height="20">
    <path d="M4 6.5A1.5 1.5 0 0 1 5.5 5H10l1.5 2h7A1.5 1.5 0 0 1 20 8.5v9A1.5 1.5 0 0 1 18.5 19h-13A1.5 1.5 0 0 1 4 17.5v-11Z" />
    <path d="M8 12h8" />
  </svg>
)

/** Expiry — time running out. */
const Expiry = () => (
  <svg {...base} width="20" height="20">
    <circle cx="12" cy="13" r="7.5" />
    <path d="M12 9.5V13l2.5 1.5" />
    <path d="M9.5 3.5h5" />
  </svg>
)

/** Overview — the state of the store at a glance. */
const Overview = () => (
  <svg {...base} width="20" height="20">
    <path d="M4 19.5V13" />
    <path d="M9.5 19.5V8" />
    <path d="M15 19.5v-7" />
    <path d="M20.5 19.5V5" />
  </svg>
)

/** Written report — a page someone reads. */
const Report = () => (
  <svg {...base} width="20" height="20">
    <path d="M6 3.5h7.5L19 9v11.5H6z" />
    <path d="M13.5 3.5V9H19" />
    <path d="M9 13h7M9 16.5h4.5" />
  </svg>
)

/** Where the numbers come from. */
const DataSource = () => (
  <svg {...base} width="20" height="20">
    <ellipse cx="12" cy="6.5" rx="7" ry="2.8" />
    <path d="M5 6.5v11c0 1.55 3.13 2.8 7 2.8s7-1.25 7-2.8v-11" />
    <path d="M5 12c0 1.55 3.13 2.8 7 2.8s7-1.25 7-2.8" />
  </svg>
)

/** Keyed by nav item id, so AppShell stays a list of ids. */
export const navIcons = {
  operational: Today,
  recommendations: Reorder,
  orders: Approved,
  prices: Prices,
  assortment: Assortment,
  'store-layout': StoreLayout,
  'shelf-plan': ShelfPlan,
  products: Products,
  expiry: Expiry,
  dashboard: Overview,
  report: Report,
  'data-source': DataSource,
}
