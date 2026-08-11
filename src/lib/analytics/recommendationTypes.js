export const RECOMMENDATION_TYPES = Object.freeze({
  REORDER: 'REORDER',
  REDUCE_STOCK: 'REDUCE_STOCK',
  PROMOTION: 'PROMOTION',
  SHELF_INCREASE: 'SHELF_INCREASE',
  SHELF_DECREASE: 'SHELF_DECREASE',
  BELOW_COST: 'BELOW_COST',
  PRICE_GAP: 'PRICE_GAP',
  NEGATIVE_STOCK: 'NEGATIVE_STOCK',
  THIN_MARGIN: 'THIN_MARGIN',
  ASSORTMENT_GAP: 'ASSORTMENT_GAP',
})

export const RECOMMENDATION_TYPE_METADATA = Object.freeze({
  [RECOMMENDATION_TYPES.REORDER]: Object.freeze({
    label: 'Reorder stock',
    defaultUrgency: 'HIGH',
    valueAtStakeField: 'recommendedOrderQuantity',
  }),
  [RECOMMENDATION_TYPES.REDUCE_STOCK]: Object.freeze({
    label: 'Reduce stock',
    defaultUrgency: 'MEDIUM',
    valueAtStakeField: 'currentStock',
  }),
  [RECOMMENDATION_TYPES.PROMOTION]: Object.freeze({
    label: 'Promote stock',
    defaultUrgency: 'LOW',
    valueAtStakeField: 'currentStock',
  }),
  [RECOMMENDATION_TYPES.SHELF_INCREASE]: Object.freeze({
    label: 'Increase shelf space',
    defaultUrgency: 'MEDIUM',
    valueAtStakeField: 'recommendedShelfQuantity',
  }),
  [RECOMMENDATION_TYPES.SHELF_DECREASE]: Object.freeze({
    label: 'Decrease shelf space',
    defaultUrgency: 'LOW',
    valueAtStakeField: 'recommendedShelfQuantity',
  }),
  [RECOMMENDATION_TYPES.BELOW_COST]: Object.freeze({
    label: 'Selling below cost',
    defaultUrgency: 'HIGH',
    valueAtStakeField: 'margin',
  }),
  [RECOMMENDATION_TYPES.PRICE_GAP]: Object.freeze({
    label: 'Priced above competitor',
    defaultUrgency: 'MEDIUM',
    valueAtStakeField: 'competitorPrice',
  }),
  [RECOMMENDATION_TYPES.NEGATIVE_STOCK]: Object.freeze({
    label: 'Negative stock count',
    defaultUrgency: 'HIGH',
    valueAtStakeField: 'currentStock',
  }),
  [RECOMMENDATION_TYPES.THIN_MARGIN]: Object.freeze({
    label: 'Thin margin',
    defaultUrgency: 'MEDIUM',
    valueAtStakeField: 'marginRate',
  }),
  // The only type that is about a product we do NOT stock. Every other type
  // describes something already on our shelves, so `productId` here is a barcode
  // from the competitor feed and there is no stock, cost or margin of our own to
  // reason about — see docs/UI_DATA_CONTRACT.md §4.1.
  [RECOMMENDATION_TYPES.ASSORTMENT_GAP]: Object.freeze({
    label: 'Add to assortment',
    defaultUrgency: 'MEDIUM',
    valueAtStakeField: 'gapScore',
  }),
})
