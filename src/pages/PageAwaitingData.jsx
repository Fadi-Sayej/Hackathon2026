import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'

/**
 * A restored page that has nothing honest to show yet, saying exactly what it is waiting for.
 *
 * WHY A PAGE LIKE THIS EXISTS AT ALL
 *   The twelve-page nav came back on 2026-09-16 because the ten-page V1 surface had dropped
 *   Reorder and the two planogram screens — the features the business is being built around.
 *   Bringing the pages back was the right call. Filling them was not available: every one of
 *   them reads `product.salesLast7Days` / `salesLast30Days`, and outside
 *   `src/data/demoProducts.js` those fields cannot be computed honestly. Not for want of a
 *   column — `sales_monthly.parquet` carries units, receipts and revenue. For want of a
 *   DATE: the seven reports are monthly, one row per product per month, none with a date
 *   column, so a daily rate is not measurable (rule 13). The repository already built the
 *   table that would supply one and deleted it — `yomyom_sales.parquet`, whose
 *   `units_sold_30d` came from a monthly mean (rule 5).
 *
 *   So these pages only ever ran on demo data — which is why the old score-ranked planogram
 *   put all 7,451 products on the bottom shelf with two facings each the first time it met
 *   the real catalogue. Restoring them on demo data was offered to the owner and declined.
 *
 *   This is the third option, and the honest one: the page is present, reachable, named in
 *   the nav he asked for, and it says what it needs instead of showing a confident layout
 *   built on numbers nobody can source. CLAUDE.md rule 8 in page form — when a figure cannot
 *   be stated honestly, show no figure rather than a plausible one.
 *
 * WHAT UNBLOCKS EACH
 *   `demand`     real units-sold per product per day. Arrives with V2 (INT-004/INT-007).
 *                The seven monthly reports cannot supply it: they are monthly and cover
 *                24.3% of the catalogue (rule 13), and deriving a daily rate from a monthly
 *                mean is exactly what Task 0.6 deleted `yomyom_sales.parquet` for.
 *   `catalogue`  a per-product list in the artefact. The data exists — 7,674 rows in
 *                `yomyom_products.parquet` with name, category, supplier and prices — but
 *                `dashboard.json` publishes per-signal findings, not a catalogue. This one
 *                is engineering, not missing data.
 *   `expiry`     shelf-life dates. The engine publishes no expiry capability; capture began
 *                on 2026-09-12 and `expiry_scans.csv` holds one row.
 *   `decision`   nothing is missing. The RULE is missing, and deliberately so: F9 is
 *                `Registered — not specified`, which the handover protocol defines as "writing
 *                a spec is deliberately forbidden until a named decision is taken". GAP-009 is
 *                the blocker. Publishing a catalogue would make this page render, and that is
 *                precisely why it must not — a screen that looks finished on an undecided rule
 *                is rule 8 one level up: a plausible answer where there is no honest one.
 *   `withdrawn`  removed on purpose, not pending. Design §20.1 marks the LLM layer REMOVE;
 *                D-12 forbids a runtime server for one store, and no document ever stated what
 *                the generated report should claim or how it would be checked.
 *
 * `decision` and `withdrawn` were split out of `catalogue` on 2026-09-16, after review pointed
 * out that grouping them there said "waiting for the product list" about two screens that are
 * not waiting for data at all. Both would have lit up the moment the catalogue shipped.
 */
export function PageAwaitingData({ pageId, needs }) {
  const { t } = useI18n()

  return (
    <section className="page page--awaiting" data-page={pageId} data-needs={needs} {...dirProps()}>
      <div className="awaiting">
        <h2 className="awaiting__title">{t(`awaiting.${needs}.title`)}</h2>
        <p className="awaiting__what">{t(`awaiting.${needs}.what`)}</p>
        <p className="awaiting__why">{t(`awaiting.${needs}.why`)}</p>
        {/* Named rather than implied: a page that says "coming soon" teaches the reader to
            stop looking. A page that says which input is missing can be argued with. */}
        <p className="awaiting__when">{t(`awaiting.${needs}.when`)}</p>
      </div>
    </section>
  )
}
