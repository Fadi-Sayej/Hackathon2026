# TECH — POS Connectors

**Sprint C7 — POS Connector Readiness**

SmartShelf is engine-driven: every page renders from a single normalized product
array. The POS connector layer is the *only* component that knows where that
array comes from. By codifying a single connector contract we can switch between
local demo data, a CSV upload, and a future Comax backend feed without touching
the analytics engines or any UI page.

## Goals

- Keep the demo stable. The bundled demo dataset remains the default and is
  always available offline.
- Allow CSV uploads to be parsed in the browser and fed through the existing
  validation/adapter pipeline.
- Represent Comax honestly: connector-ready, but **not callable** from the
  frontend until a backend proxy exists. No API key is permitted in client code.

## Connector Contract

Every connector implements the following methods. See
`src/lib/posConnectors/posConnectorInterface.js` for the JSDoc shape.

| Method | Returns | Purpose |
|--------|---------|---------|
| `connect()` | `{ ok, message, hint? }` | Probe / handshake. Validates that the source is reachable and well-formed. |
| `fetchProducts()` | raw rows | Catalog dimension (id, name, category, price, supplier, …). |
| `fetchInventory()` | raw rows | Stock + shelf state (currentStock, shelfQuantity, shelfCapacity). |
| `fetchSales()` | raw rows | Recent velocity (salesLast7Days, salesLast30Days). |
| `normalizeToSmartShelfSchema({ products, inventory, sales })` | `{ products, validationIssues, source }` | Merge feeds by id, run them through the standard product adapter, return the SmartShelf-shaped output. |
| `load()` | `{ products, validationIssues, source }` | Convenience: runs `connect → fetch* → normalize` in one call. Used by `App.jsx`. |

`mergeFeedsById` in the interface module handles the join between three feeds.
A connector that returns a single denormalized feed (CSV, demo) simply returns
the same rows from all three `fetchX` calls — the merge collapses them by id.

## Modes

### 1. Demo Data Connector — `demoDataConnector.js`

Wraps the bundled `demoProducts` array. Always returns `{ ok: true }` from
`connect()`. This is the default mode the app boots into and the path the
hackathon judge sees out of the box.

### 2. CSV Connector — `csvConnector.js`

Functional, browser-only.

- Accepts a `File` (from `<input type="file">`) or raw `csvText`.
- Parses with an RFC 4180-lite parser (`parseCsv`) that handles quoted fields,
  embedded commas/newlines, and `""` escaped quotes.
- Coerces known numeric columns (`currentStock`, `salesLast7Days`, `price`, …)
  to numbers before normalization.
- Hands rows to the same `normalizeProducts` adapter used by the demo data, so
  field aliases (`stock` vs `currentStock`, `vendor` vs `supplier`) and
  validation warnings work identically.
- Validation issues surface in the Data Source page's "Data quality warnings"
  list.

### 3. Comax Connector Stub — `comaxConnectorStub.js`

Inert by design.

- `connect()` always returns `{ ok: false, message: 'Backend proxy required …' }`
  unless `VITE_COMAX_PROXY_URL` is set. Even then the live path is not yet wired.
- `fetchProducts`, `fetchInventory`, `fetchSales`, `normalizeToSmartShelfSchema`
  all throw a clear error. The frontend cannot mint POS API calls.
- The stub exposes `expectedFields` (see below) so that whoever builds the
  backend proxy knows exactly what schema the SmartShelf adapter expects.

## Expected POS Fields

Defined in `EXPECTED_POS_FIELDS` and rendered in the Data Source page's schema
table. A Comax (or any other POS) backend proxy must produce rows in this shape:

| Field | Aliases | Required |
|-------|---------|----------|
| `id` | `sku`, `productId`, `barcode` | ✅ |
| `barcode` | `ean`, `upc` | optional |
| `name` | `productName`, `description` | ✅ |
| `category` | `department`, `group` | ✅ |
| `currentStock` | `stock`, `onHand`, `qty` | ✅ |
| `salesLast7Days` | `sales7d`, `weeklySales` | optional |
| `salesLast30Days` | `sales30d`, `monthlySales` | optional |
| `price` | `unitPrice`, `sellPrice` | ✅ |
| `cost` | `unitCost` | optional |
| `supplier` | `vendor` | optional |
| `leadTimeDays` | `leadTime` | optional |
| `expiryDate` | `expiry` | optional |
| `shelfQuantity` | `onShelf` | optional |
| `shelfCapacity` | `capacity` | optional |

## Security Posture

- **No secrets in the frontend.** The Comax stub does not accept an API key,
  and there is no code path in the bundle that could send one to a POS host.
- **Backend proxy is the only sanctioned live path.** When that proxy is built,
  it should expose its own URL (configurable via `VITE_COMAX_PROXY_URL`) and
  the stub should be replaced with a thin `fetch` adapter that hits it.
- **CSV parsing stays client-side.** No file upload leaves the browser.

## UI Surface

`src/pages/DataSourcePage.jsx` renders three cards: Demo, CSV, Comax. The active
mode is highlighted, the Comax button is permanently disabled with a
"Backend proxy required" label, and a schema reference table plus validation
issue feed are shown beneath. The page is reachable from the sidebar nav at
`Data Source`.

`App.jsx` holds `storeData` and `connectorStatus` state. Switching connectors
calls `applyConnector(connector)` which probes, loads, and replaces store data
in one transition; recommendation overrides are reset to keep approval state
consistent with the new source.

## File Map

```
src/lib/posConnectors/
├── posConnectorInterface.js   ← contract, modes, mergeFeedsById, EXPECTED_POS_FIELDS
├── demoDataConnector.js       ← bundled SKUs (default)
├── csvConnector.js            ← parseCsv + CSV upload connector
├── comaxConnectorStub.js      ← safe stub, no live calls
└── index.js                   ← createConnector factory + CONNECTOR_CATALOG

src/pages/DataSourcePage.jsx   ← Data Source UI
src/App.jsx                    ← connector state, applyConnector dispatcher
src/components/layout/AppShell.jsx ← adds "Data Source" nav item
```

## Done Criteria — Sprint C7

- ✅ Generic POS connector contract defined and shared between three modes.
- ✅ Demo dataset continues to load by default and remains the offline fallback.
- ✅ CSV upload parses locally and runs through the standard adapter pipeline,
  surfacing validation warnings.
- ✅ Comax is represented honestly: visible card, disabled action, expected
  field schema documented, no API key in frontend.
- ✅ No secrets exposed in client code.
- ✅ `npm run lint` and `npm run build` pass.
