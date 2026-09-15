/**
 * The nav, as data.
 *
 * Split out of AppShell.jsx so tests can read it: a page added to the nav without its
 * four i18n strings renders `page.<id>.title` as its heading, which is #90, and the check
 * for that has to start from the nav rather than from the dictionaries
 * (src/lib/i18n/__tests__/parity.test.js). A component file may not export constants —
 * react-refresh/only-export-components — so this is its own module rather than an export
 * from there.
 */

/**
 * The ten V1 pages (design §20.1: "nav reduced to 10 items"), grouped as the owner would
 * group them rather than as the codebase does.
 *
 * The V2/V4 entries — reorder, approved orders, assortment gaps, store layout, shelf plan,
 * dashboard, report — are gone from here at the cut-over. Their code stays until Phase 4 so
 * a rollback still has somewhere to land; it is simply no longer reachable.
 */
export const navGroups = [
  {
    id: 'group.daily',
    items: [
      { id: 'daily' },
      { id: 'questions' },
    ],
  },
  {
    id: 'group.market',
    items: [
      { id: 'price_consistency' },
      { id: 'competitor_position' },
    ],
  },
  {
    id: 'group.inventory',
    items: [
      { id: 'reconciliation' },
      { id: 'hygiene' },
      { id: 'catalogue_lifecycle' },
      { id: 'margin_below_cost' },
      { id: 'receiving' },
    ],
  },
  {
    id: 'group.system',
    items: [{ id: 'data' }],
  },
]

/**
 * Every id the nav actually renders. Exported so a test can ask the nav what it contains
 * rather than keep a second list in step by hand. AppShell renders `page.<id>.name`,
 * `.hint`, `.title` and `.description` for each of these, and a page added here with no
 * strings renders `page.<id>.title` as its heading (#90).
 */
export const NAV_PAGE_IDS = navGroups.flatMap((group) => group.items.map((item) => item.id))
