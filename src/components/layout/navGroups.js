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
 * The twelve pages, restored 2026-09-16 on the repository owner's decision.
 *
 * The Task 2.7 cut-over reduced this to ten V1 ids (design §20.1) and in doing so dropped
 * REORDER and the two PLANOGRAM screens. Those are the two features the business is being
 * built around, so a nav that omits them is the wrong shape however well the ten work.
 * That is a product judgement and it is his to make; this file follows it.
 *
 * Nothing was recovered from the attic to do this. All twelve page components are still on
 * `main`, byte-identical to the tag `v1-attic`, and all 52 `page.<id>.*` strings and all
 * twelve nav icons were still in place — the cut-over stopped rendering them, it never
 * removed them.
 *
 * WHAT THE OWNER SEES ON THE TWO FEATURES HE CARES MOST ABOUT
 *   Reorder and the planogram screens come back PRESENT AND EMPTY, each saying what it is
 *   waiting for. They read `product.salesLast7Days` / `salesLast30Days`, and those fields
 *   exist in exactly three places — `src/data/demoProducts.js`, the generator that writes
 *   it, and the engines that consume it. No silver POS table carries any sales or velocity
 *   column. Both features only ever ran on demo data, which is why the old score-ranked
 *   planogram put all 7,451 products on the bottom shelf with two facings each the moment
 *   it met the real catalogue.
 *
 *   Restoring them on demo data was offered and declined. Real demand arrives with V2.
 *   Until then an empty screen that says why is worth more than a full one that is wrong.
 */
export const navGroups = [
  {
    id: 'group.daily',
    items: [
      { id: 'operational' },
      { id: 'recommendations' },
      { id: 'orders' },
    ],
  },
  {
    id: 'group.market',
    items: [
      { id: 'prices' },
      { id: 'assortment' },
    ],
  },
  {
    id: 'group.shelves',
    items: [
      { id: 'store-layout' },
      { id: 'shelf-plan' },
    ],
  },
  {
    id: 'group.inventory',
    items: [
      { id: 'products' },
      { id: 'expiry' },
    ],
  },
  {
    id: 'group.reports',
    items: [
      { id: 'dashboard' },
      { id: 'report' },
    ],
  },
  {
    id: 'group.system',
    items: [{ id: 'data-source' }],
  },
]

/**
 * Every id the nav actually renders. Exported so a test can ask the nav what it contains
 * rather than keep a second list in step by hand. AppShell renders `page.<id>.name`,
 * `.hint`, `.title` and `.description` for each of these, and a page added here with no
 * strings renders `page.<id>.title` as its heading (#90).
 */
export const NAV_PAGE_IDS = navGroups.flatMap((group) => group.items.map((item) => item.id))
