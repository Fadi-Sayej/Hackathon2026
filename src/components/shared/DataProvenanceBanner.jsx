import { useNumbers, useT } from '../../lib/i18n/index.js'

/**
 * DataProvenanceBanner — an honest, at-a-glance summary of where the data on
 * screen actually comes from. Built so nobody mistakes real POS data for demo
 * data (or vice versa) and so known gaps are stated plainly rather than implied
 * as observed demand.
 */
export function DataProvenanceBanner({ dataProvenance }) {
  const t = useT()
  const { n } = useNumbers()

  if (!dataProvenance) return null

  const {
    catalog,
    catalogCount,
    catalogLabel,
    hasSalesHistory,
    competitor,
    competitorStoreCount,
    liveMarketContext,
  } = dataProvenance

  // A partial provenance object used to crash the whole Overview page here:
  // `catalogCount.toLocaleString()` throws on undefined. A banner that reports
  // data health must never be the thing that takes the page down.
  const skuCount = Number.isFinite(catalogCount) ? n(catalogCount.toLocaleString()) : '—'
  const label = catalogLabel ?? t('prov.unknownSource')

  const items = [
    {
      key: 'catalog',
      label: t('prov.catalog'),
      value: `${label} · ${skuCount} ${t('prov.skus')}`,
      tone: catalog === 'real' || catalog === 'uploaded' ? 'real' : 'demo',
    },
    {
      key: 'competitor',
      label: t('prov.competitorPrices'),
      value:
        competitor === 'real'
          ? t('prov.competitorReal', { n: n(competitorStoreCount ?? 0) })
          : t('prov.notAvailable'),
      tone: competitor === 'real' ? 'real' : 'demo',
    },
    {
      key: 'sales',
      label: t('prov.salesHistory'),
      value: hasSalesHistory ? t('prov.available') : t('prov.noSalesHistory'),
      tone: hasSalesHistory ? 'real' : 'partial',
    },
    {
      key: 'market',
      label: t('prov.marketContext'),
      value: liveMarketContext ? t('prov.marketLive') : t('prov.marketStatic'),
      tone: liveMarketContext ? 'real' : 'demo',
    },
  ]

  return (
    <section className="provenance-banner" aria-label={t('prov.catalog')}>
      {items.map((item) => (
        <div className={`provenance-item provenance-${item.tone}`} key={item.key}>
          <span className="provenance-dot" aria-hidden="true" />
          <div>
            <p className="provenance-label">{item.label}</p>
            <p className="provenance-value">{item.value}</p>
          </div>
        </div>
      ))}
    </section>
  )
}
