import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'

/**
 * A restored page that has nothing honest to show yet, saying exactly what it is waiting for.
 *
 * WHY A PAGE LIKE THIS EXISTS AT ALL
 *   The twelve-page nav came back on 2026-09-16 because the ten-page V1 surface had dropped
 *   Reorder and the two planogram screens — the features the business is being built around.
 *   Bringing the pages back was the right call. Filling them was not available: every one of
 *   them reads `product.salesLast7Days` / `salesLast30Days`, and those fields exist only in
 *   `src/data/demoProducts.js`. No silver POS table carries any sales or velocity column.
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
