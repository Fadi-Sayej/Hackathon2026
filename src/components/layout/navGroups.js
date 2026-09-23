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
 *   it, and the engines that consume it. Not for want of a sales COLUMN: sales_monthly.parquet
 *   carries units, receipts and revenue. For want of a DATE — the seven reports are monthly,
 *   one row per product per month, so a daily rate is not measurable (rule 13), and the
 *   30-day table that would supply one was deleted for being synthesised from a monthly mean
 *   (rule 5). Both features only ever ran on demo data, which is why the old score-ranked
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
      // Kept from the cut-over surface rather than restored from the attic. The twelve pages
      // are the owner's request; this one is the pilot's acceptance criteria, and dropping it
      // was a side effect of the restore that nobody decided. Both now exist.
      { id: 'daily' },
      // `operational` — the pre-cut-over Today page — was removed on 2026-09-23 at the
      // owner's decision: "combine the first 2, i don't need 2 today work". `daily` is the
      // Today page now, and the only one.
      //
      // Safe to remove only because its findings have somewhere else to go. Until this
      // release `margin_below_cost` was reachable through it and nowhere else, so removing
      // it earlier would have taken 34 below-cost products off the product silently. That
      // capability is routed above, in this same change, deliberately.
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
    // The six capabilities, whole, behind one heading — closed until asked for.
    //
    // FR-102 needs every capability reachable on a surface other than the daily one, and
    // there are six of them. Listed flat that is eighteen nav entries against the fifteen
    // the owner asked for, and his objection was to the LENGTH rather than to the routes:
    // "15 but combine the first 2, i don't need 2 today work".
    //
    // Collapsed, the nav reads as twelve entries and one heading, and nothing is dropped to
    // get there. Opening it is one tap, and it opens itself when the active page is inside,
    // so arriving at one of these pages never shows a closed drawer with no explanation.
    id: 'group.findings',
    collapsible: true,
    items: [
      { id: 'price_consistency' },
      { id: 'margin_below_cost' },
      { id: 'reconciliation' },
      { id: 'hygiene' },
      { id: 'catalogue_lifecycle' },
      { id: 'competitor_position' },
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
 *
 * A collapsed group's items are still in here, and should be: they are rendered the moment
 * it is opened, so a missing string is a defect whether or not the drawer starts shut.
 */
export const NAV_PAGE_IDS = navGroups.flatMap((group) => group.items.map((item) => item.id))
