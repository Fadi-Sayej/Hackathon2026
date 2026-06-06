/**
 * DataProvenanceBanner — an honest, at-a-glance summary of where the data on
 * screen actually comes from. Built for the demo so nobody mistakes real POS
 * data for demo data (or vice versa) and so known gaps (no sales history) are
 * stated plainly instead of being implied as observed demand.
 */
export function DataProvenanceBanner({ dataProvenance }) {
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

  const items = [
    {
      key: 'catalog',
      label: 'Product catalog',
      value: `${catalogLabel} · ${catalogCount.toLocaleString()} SKUs`,
      tone: catalog === 'real' ? 'real' : catalog === 'uploaded' ? 'real' : 'demo',
    },
    {
      key: 'competitor',
      label: 'Competitor prices',
      value:
        competitor === 'real'
          ? `Real (Kaggle) · ${competitorStoreCount} chains`
          : 'Not available',
      tone: competitor === 'real' ? 'real' : 'demo',
    },
    {
      key: 'sales',
      label: 'Sales history',
      value: hasSalesHistory ? 'Available' : 'Not in POS export — velocity metrics estimated',
      tone: hasSalesHistory ? 'real' : 'partial',
    },
    {
      key: 'market',
      label: 'Market context',
      value: liveMarketContext ? 'Live (weather / holidays / news)' : 'Static demo context',
      tone: liveMarketContext ? 'real' : 'demo',
    },
  ]

  return (
    <section className="provenance-banner" aria-label="Data provenance">
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
