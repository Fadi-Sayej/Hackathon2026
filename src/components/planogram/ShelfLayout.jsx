import { ShelfTier } from './ShelfTier.jsx'

const VISUAL_SHELF_ORDER = ['TOP', 'EYE_LEVEL', 'MIDDLE', 'BOTTOM']

export function ShelfLayout({ activeItem, complianceMap, onSelectItem, shelfGroups }) {
  const orderedGroups = shelfGroups
    .slice()
    .sort(
      (a, b) =>
        VISUAL_SHELF_ORDER.indexOf(a.shelfLevel) - VISUAL_SHELF_ORDER.indexOf(b.shelfLevel),
    )

  return (
    <div className="retail-fixture">
      {orderedGroups.map((group) => (
        <ShelfTier
          key={group.shelfLevel}
          group={group}
          activeItem={activeItem}
          complianceMap={complianceMap}
          onSelectItem={onSelectItem}
        />
      ))}
    </div>
  )
}
