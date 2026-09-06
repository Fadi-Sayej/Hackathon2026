import { ProductCard } from './ProductCard.jsx'

const TIER_CLASS = {
  TOP: 'fixture-shelf-top',
  EYE_LEVEL: 'fixture-shelf-premium',
  MIDDLE: 'fixture-shelf-mid',
  BOTTOM: 'fixture-shelf-base',
}

const TIER_PRIORITY_LABEL = {
  TOP: 'Top reach',
  EYE_LEVEL: 'Premium',
  MIDDLE: 'Standard',
  BOTTOM: 'Low reach',
}

export function ShelfTier({ group, activeItem, complianceMap, onSelectItem }) {
  const tierClass = TIER_CLASS[group.shelfLevel] ?? ''
  const priorityLabel = TIER_PRIORITY_LABEL[group.shelfLevel] ?? ''

  return (
    <section className={`fixture-shelf ${tierClass}`}>
      <div className="fixture-tier-accent" aria-hidden="true" />
      <div className="fixture-label">
        <strong>{group.shelfLabel}</strong>
        <span>{group.items.length} products</span>
        <span className="fixture-tier-priority">{priorityLabel}</span>
      </div>
      <div className="fixture-products">
        {group.items.map((item) => (
          <ProductCard
            key={item.productId}
            item={item}
            isActive={activeItem?.productId === item.productId}
            complianceState={complianceMap?.get(item.productId)}
            onSelect={onSelectItem}
          />
        ))}
      </div>
    </section>
  )
}
