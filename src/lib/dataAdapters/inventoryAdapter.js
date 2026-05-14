import { nonNegativeNumber } from './validation.js'

export function normalizeInventory(rawProduct, issues = []) {
  const inventory = rawProduct.inventory ?? rawProduct

  return {
    currentStock: nonNegativeNumber(
      inventory.currentStock ?? inventory.stock ?? inventory.onHand,
      0,
      'currentStock',
      issues,
    ),
    shelfQuantity: nonNegativeNumber(
      inventory.shelfQuantity ?? inventory.onShelf,
      0,
      'shelfQuantity',
      issues,
    ),
    shelfCapacity: nonNegativeNumber(
      inventory.shelfCapacity ?? inventory.capacity,
      0,
      'shelfCapacity',
      issues,
    ),
    returnedUnits: nonNegativeNumber(
      inventory.returnedUnits ?? inventory.returns,
      0,
      'returnedUnits',
      issues,
    ),
    damagedUnits: nonNegativeNumber(
      inventory.damagedUnits ?? inventory.damages,
      0,
      'damagedUnits',
      issues,
    ),
  }
}
