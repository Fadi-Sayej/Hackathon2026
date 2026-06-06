# SmartShelf AI — QA Checklist

Version: P2 / Pre-Demo
Last updated: 2026-06-06

---

## Dashboard

| # | Test | Expected | Pass? |
|---|---|---|---|
| D-01 | App loads at `http://localhost:5173` | Dashboard renders, no blank screen, no console errors | |
| D-02 | Six KPI metric cards appear | Total Products, High Risk Stockouts, Reorder Suggestions, Estimated Order Cost, Overstocked Items, Waste Risk | |
| D-03 | KPI values are numbers (not NaN, undefined, or null) | All 6 cards show numeric or currency values | |
| D-04 | Category bars render | At least one bar visible in the Sales Distribution panel | |
| D-05 | Market Context panel appears | Panel visible with weather, holiday, and/or news data | |
| D-06 | Market context source label is visible | Label shows "live" or "static fallback" or "mock" | |
| D-07 | Market Intelligence panel appears | Shows competitor intelligence section | |
| D-08 | Highest Risk Products list renders | Up to 6 products listed with status badges | |
| D-09 | Urgent Recommendations panel renders | Shows items or EmptyState ("No urgent recommendations") | |
| D-10 | EmptyState shows if no urgent items | "No urgent recommendations" message visible | |

---

## Products Page

| # | Test | Expected | Pass? |
|---|---|---|---|
| P-01 | Products page loads | Product list renders with at least one row | |
| P-02 | Search field is visible | Text input present | |
| P-03 | Type in search field | List filters to matching product names | |
| P-04 | Clear search field | All products reappear | |
| P-05 | Category filter dropdown works | Selecting a category shows only matching products | |
| P-06 | Status filter works | Filtering by status (e.g., CRITICAL) shows matching subset | |
| P-07 | Search with no matches | EmptyState message appears ("No products match") | |
| P-08 | Product rows show stock, price, status | Data columns visible per row | |

---

## Recommendations Page

| # | Test | Expected | Pass? |
|---|---|---|---|
| R-01 | Recommendations page loads | Cards appear or EmptyState shows | |
| R-02 | Each card shows urgency badge | HIGH / MEDIUM / LOW badge visible | |
| R-03 | Each card shows AI explanation | Explanation text block visible | |
| R-04 | Quantity field has a default value > 0 | Non-zero integer pre-filled | |
| R-05 | Edit quantity to a new value | Quantity field updates | |
| R-06 | Edit quantity to 0 | Approve button becomes disabled | |
| R-07 | Edit quantity to negative number | Stored as 1 (normalizeOrderQuantity clamps to min 1) | |
| R-08 | Click Approve | Card switches to APPROVED badge, opacity drops to 0.65, Approve button shows "Approved" (disabled) | |
| R-09 | Approved card Reject button is disabled | Reject button cannot be clicked on an approved card | |
| R-10 | Click Reject | Card disappears from the pending list | |
| R-11 | Rejected item does not reappear | After reject, item is gone for the session | |
| R-12 | Summary metrics update after approve | Approved count and Estimated Cost increase | |
| R-13 | EmptyState if no recommendations | "No recommendations pending" message shows | |

---

## Planogram Page

| # | Test | Expected | Pass? |
|---|---|---|---|
| PL-01 | Planogram page loads | Shelf layout renders or EmptyState appears | |
| PL-02 | EmptyState if no items | "No planogram placements" message with description | |
| PL-03 | Metric cards show: Planogram Items, Eye Level, Total Facings | Three cards visible | |
| PL-04 | Shelf grid renders multiple shelves | At least 2 shelf rows visible | |
| PL-05 | Click a product slot | Placement Reason panel appears with product detail | |
| PL-06 | Cross-Merchandising panel appears | Affinity suggestions section visible | |
| PL-07 | Shelf Compliance section appears | Photo upload UI is visible | |
| PL-08 | Click "Analyze" on compliance | Spinner runs ~1.8 seconds, compliance report appears | |

---

## Approved Orders Page

| # | Test | Expected | Pass? |
|---|---|---|---|
| AO-01 | Orders page loads with no approvals | EmptyState "No approved purchase orders yet" visible | |
| AO-02 | After approving items in Recommendations, revisit Orders page | Approved items appear grouped by supplier | |
| AO-03 | Supplier subtotal is correct | Sum of (qty × unit cost) per supplier matches displayed subtotal | |
| AO-04 | Grand total is correct | Sum of all supplier subtotals matches "Estimated total" | |
| AO-05 | "Export CSV" button present | Button visible in toolbar | |
| AO-06 | Click Export CSV | File download triggers (`smartshelf-approved-orders.csv`) | |
| AO-07 | Exported CSV is valid | Opens in spreadsheet, rows match on-screen data | |
| AO-08 | "Print" button present | Button visible in toolbar | |
| AO-09 | Click Print | Browser print dialog opens | |
| AO-10 | "Send to [Supplier]" button fires toast | Success toast appears and disappears after ~3 seconds | |

---

## Navigation

| # | Test | Expected | Pass? |
|---|---|---|---|
| N-01 | Dashboard link reachable | Clicking Dashboard in nav loads Dashboard page | |
| N-02 | Products link reachable | Clicking Products loads Products page | |
| N-03 | Recommendations link reachable | Clicking Smart Reorder loads Recommendations page | |
| N-04 | Planogram link reachable | Clicking Shelf Optimization loads Planogram page | |
| N-05 | Approved Orders link reachable | Clicking Approved Orders loads Orders page | |
| N-06 | Report link reachable | Clicking AI Report loads Report page | |
| N-07 | Data Source link reachable | Clicking Data Source loads Data Source page | |
| N-08 | Operational link reachable | Clicking Operational Risks loads Operational page | |
| N-09 | Expiry link reachable | Clicking Expiry Tracking loads Expiry page | |
| N-10 | No page throws a JS error on load | Browser console shows no uncaught errors on any page | |
| N-11 | Reset Demo State button visible (when overrides exist) | Button appears in top bar after any approve/reject action | |
| N-12 | Click Reset Demo State | App returns to clean state, all recommendations back to pending | |

---

## Overall Verdict

```
QA PASS: P2 / Pre-Demo

VERDICT: [ READY | READY WITH NOTES | NOT READY ]

TESTED:
-

PASS:
-

FAIL:
-

RISKS:
-

DEMO SAFE FLOW:
-

AVOID:
-

RECOMMENDED CODEX FIXES:
-
```
