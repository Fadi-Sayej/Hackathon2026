# SmartShelf AI — Acceptance Criteria

Each criterion below defines exactly what must happen for a user action to be considered working. These are the pass/fail bars for QA.

---

## Approve a Recommendation

**Action:** Manager clicks "Approve" on a recommendation card.

**Pass conditions (all must hold):**
1. The card's urgency badge changes to "APPROVED" (green tone).
2. The card's visual opacity drops to ~65% to signal it is no longer pending.
3. The "Approve" button label changes to "Approved" and becomes disabled.
4. The "Reject" button on the same card becomes disabled.
5. The recommendation appears in the Approved Orders page on next visit.
6. The "Approved" count KPI card at the top of the Recommendations page increments by 1.
7. The "Estimated Cost" KPI card increases by `recommendedOrderQuantity × product.cost`.
8. The decision persists in localStorage — refreshing the page preserves the APPROVED state.

**Fail conditions:**
- Approve button remains active after clicking.
- Approved card still appears as pending (badge unchanged).
- Approved item does not appear in Approved Orders.
- Cost KPI does not update.
- Decision lost on refresh.

---

## Reject a Recommendation

**Action:** Manager clicks "Reject" on a pending recommendation card.

**Pass conditions (all must hold):**
1. The card disappears from the visible recommendation list immediately.
2. The rejected item does not reappear after navigating away and returning to the page.
3. The rejected item does not reappear after a page refresh.
4. The "Approved" count and cost KPI are unchanged (reject does not affect approved totals).

**Fail conditions:**
- Card remains visible after rejection.
- Card reappears after navigation.
- Card reappears after refresh.

---

## Edit Order Quantity

**Action:** Manager changes the quantity field on a recommendation card.

**Pass conditions (all must hold):**
1. The field accepts positive integers.
2. Entering a value of 0 disables the Approve button (title shows "Enter a quantity above zero to approve").
3. Entering a negative number is clamped to 1 on save (the `normalizeOrderQuantity` function enforces `Math.max(1, Math.round(parsed))`).
4. Entering non-numeric text (e.g., "abc") is clamped to 1 on save.
5. The displayed line-item cost (`qty × unit cost`) updates in real time as the field changes.
6. If the item is already APPROVED, editing quantity keeps the APPROVED status and updates the Approved Orders total.

**Fail conditions:**
- Quantity field accepts 0 and lets the user approve.
- Quantity field accepts negative numbers without correction.
- NaN is stored or displayed.
- Cost display does not update after quantity change.

---

## Export CSV from Approved Orders

**Action:** Manager clicks "Export CSV" button.

**Pass conditions (all must hold):**
1. A file download triggers with filename `smartshelf-approved-orders.csv`.
2. The CSV contains a header row: `Supplier, Product, Quantity, Unit Cost, Total`.
3. Every approved line item appears as a row with correct values.
4. Supplier subtotal rows appear after each supplier block.
5. A grand total row appears at the end.
6. Values with commas or quotes are properly escaped (wrapped in double quotes).
7. The file opens correctly in Excel / Google Sheets.

**Fail conditions:**
- No download triggers.
- Download triggers but file is empty.
- Columns are misaligned or truncated.
- Totals do not match on-screen values.

---

## Print Approved Orders

**Action:** Manager clicks "Print" button.

**Pass conditions (all must hold):**
1. `window.print()` is called.
2. The browser print dialog opens.
3. The print preview shows the approved orders content (not a blank page).

**Fail conditions:**
- Nothing happens on click.
- Print dialog does not open.
- Print preview is blank.

---

## Select a Planogram Layout

**Action:** Manager navigates to Planogram page.

**Pass conditions (all must hold):**
1. The shelf layout renders at least one shelf row with product slots.
2. Metric cards show non-zero values for Planogram Items, Eye Level, and Total Facings.
3. Clicking a product slot opens the Placement Reason panel with that product's details.
4. The Cross-Merchandising panel shows affinity suggestions (or an empty state if no affinities exist).

**Fail conditions:**
- Planogram page is blank (no EmptyState and no layout).
- Clicking a slot does nothing.
- Metric cards show 0 for all three values (when products exist).

---

## Search / Filter Products

**Action:** Manager types in the Products page search field, or selects a category/status filter.

**Pass conditions (all must hold):**
1. Typing a product name (or partial name) filters the list to matching rows only.
2. The filter is case-insensitive.
3. Clearing the search field restores all products.
4. Selecting a category from the filter dropdown shows only that category's products.
5. Selecting a status filter shows only products with that status.
6. Combining search text with a category filter applies both constraints simultaneously.
7. When no products match, an EmptyState message appears (no blank/broken layout).

**Fail conditions:**
- Search field has no visible effect.
- Filter dropdown does nothing.
- Mixed filters do not stack.
- Zero-result state is a blank area (no EmptyState component).
