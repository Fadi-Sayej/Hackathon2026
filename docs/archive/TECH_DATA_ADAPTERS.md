> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# SmartShelf AI Data Adapters

Sprint C2 adds a small adapter layer so the UI and analytics engines can keep using one normalized product shape while future data may come from local files, CSV imports, or a backend.

## Runtime Path

The app now loads demo products through:

```txt
src/lib/dataAdapters/loadDemoStoreData.js
  -> productAdapter.js
  -> inventoryAdapter.js
  -> salesAdapter.js
  -> validation.js
```

`App.jsx` consumes `loadDemoStoreData().products` and passes normalized products into the existing recommendation, inventory, and planogram engines.

## Accepted Normalized Product Schema

```js
{
  id: string,
  name: string,
  category: string,
  currentStock: number,
  shelfQuantity: number,
  shelfCapacity: number,
  salesLast7Days: number,
  salesLast30Days: number,
  price: number,
  cost: number,
  expiryDate?: string,
  supplier: string,
  leadTimeDays: number,
  returnedUnits: number,
  damagedUnits: number
}
```

## Supported Raw Aliases

The adapters accept the current flat demo product shape and tolerate common future aliases:

- Product identity: `id`, `sku`, `productId`
- Product name: `name`, `productName`
- Category: `category`, `department`
- Inventory: flat fields or nested `inventory`
- Stock: `currentStock`, `stock`, `onHand`
- Shelf quantity: `shelfQuantity`, `onShelf`
- Shelf capacity: `shelfCapacity`, `capacity`
- Sales: flat fields or nested `sales`
- 7-day sales: `salesLast7Days`, `last7Days`, `units7d`
- 30-day sales: `salesLast30Days`, `last30Days`, `units30d`
- Price: `price`, `unitPrice`
- Cost: `cost`, `unitCost`
- Supplier: `supplier`, `vendor`
- Lead time: `leadTimeDays`, `leadTime`

## Validation Behavior

Validation is intentionally demo-safe:

- Missing product names become `Unnamed Product #`.
- Missing categories become `Uncategorized`.
- Invalid stock, shelf, sales, returned, or damaged counts become `0`.
- Invalid price becomes `1` so margin math does not divide by zero.
- Invalid cost becomes `0`.
- Invalid expiry dates are removed.
- Shelf capacity is raised to at least `1` when missing.
- Shelf quantity is capped at shelf capacity.

Each correction produces a validation issue with:

```js
{
  field: string,
  code: string,
  message: string,
  severity: 'warning' | 'info',
  value: unknown,
  productId: string,
  rowIndex: number
}
```

## Future Backend Path

When a backend or CSV import is added, the source should feed raw rows into `normalizeProducts()` or `loadDemoStoreData(rawRows)` first. UI pages and analytics engines should continue receiving normalized products only.
