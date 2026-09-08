# SmartShelf AI — Safe Demo Flow

The exact sequence of clicks to use during the presentation. Follow this path; do not improvise unless specifically asked.

---

## Pre-Demo

- Reset demo state (click "Reset Demo State" button or clear localStorage)
- Confirm Dashboard is the active page
- Browser zoom at 100%, DevTools closed, only one tab open

---

## Step 1 — Dashboard

**Action:** App is already on Dashboard. Point to the screen.

**Say:** "This is what the store owner sees every morning — stockout risks, reorder count, the estimated cost of acting today, and overstocked items. One screen to understand the store's situation."

**Point to:** The six KPI metric cards across the top.

**Also point to:** The Market Context panel ("weather, holidays, local events — the system adjusts urgency based on these signals").

**Also point to:** The Market Intelligence panel ("competitor pricing context — which nearby stores are out of stock on which products").

**Fallback if Dashboard shows 0 stockouts or 0 reorder suggestions:** "The dataset is populated — let me navigate to Smart Reorder to show the active recommendations." [proceed to Step 2 immediately]

---

## Step 2 — Recommendations

**Action:** Click "Smart Reorder" in the left navigation.

**Say:** "Here's the core workflow. Every product is ranked by urgency. This one — [point to the top HIGH card] — has a critical stockout risk."

**Point to:** The urgency badge (HIGH), the product name, and the AI explanation text block.

**Say:** "The explanation tells the manager exactly why: stock level, sales velocity, and market context. The manager can adjust the quantity [touch the quantity field] or just click Approve."

**Action:** Click "Approve" on the top recommendation card.

**Observe:** Badge changes to APPROVED (green), card fades slightly, Approve button becomes disabled.

**Say:** "Done. That decision took four seconds."

**Fallback if Approve button is disabled:** The quantity field may be at 0. Type "24" in the quantity field first, then click Approve.

**Fallback if no cards appear:** Navigate to Data Source page, click "Load Demo Data", return to Smart Reorder.

---

## Step 3 — Approved Orders

**Action:** Click "Approved Orders" in the left navigation.

**Say:** "The approved item appears immediately, grouped by supplier. Unit cost, quantity, and total are already calculated. No spreadsheet needed."

**Point to:** The supplier block, the product row, the subtotal, and the grand total.

**Action:** Point to the "Export CSV" button and the "Print" button.

**Say:** "The manager exports a CSV for the supplier's order system, or prints a one-page purchase order."

**Optionally demonstrate:** Click Export CSV (file downloads). Do NOT click Print unless you have already confirmed the browser print dialog works on this machine.

**Fallback if Approved Orders is empty:** "I need to approve one item first — let me do that." [Navigate back to Smart Reorder, approve one card, return to Approved Orders]

---

## Step 4 — Planogram

**Action:** Click "Shelf Optimization" in the left navigation.

**Say:** "The same product data — stock, velocity, margin, shelf capacity — is used to generate a visual planogram. Eye-level shelf gets the fastest, highest-margin products. Bottom shelf gets bulk and slow-movers."

**Action:** Click one product slot in the middle (eye-level) shelf row.

**Observe:** Placement Reason panel appears on the right.

**Say:** "Click any slot and you see exactly why that product is placed there — the scoring factors are visible."

**Point to:** The Cross-Merchandising panel below the shelf layout.

**Say:** "And the system identifies cross-merchandising opportunities — products that sell together and should be placed near each other."

**Fallback if planogram shows EmptyState:** "The demo dataset is large enough that this shouldn't happen. Let me check the data source." [Navigate to Data Source, reload demo data, return to Planogram]

---

## Step 5 — Closing

**Say:** "SmartShelf AI replaces the morning shelf walk, the supplier phone call, and the expiry-date guessing. It runs on a real inventory dataset from an Israeli convenience store — 7,674 products. After the hackathon: three-store pilot, then a Supabase-backed SaaS for the Israeli market."

**Stop here.** Open for questions.

---

## Pages NOT to visit unless asked

| Page | Why to avoid unless asked |
|---|---|
| Data Source | Shows mock/error state for Comax; switching data source resets all overrides |
| Operational Risks | Safe to show, but not needed in the core story |
| Expiry Tracking | Safe to show, but not needed in the core story |
| AI Report | Safe to show, but not a core demo beat |

If a judge asks about any of these pages, navigate to it and explain what they see. If Comax is clicked on Data Source, say: "That's the integration slot for the Comax POS system — the connector is the next engineering step."
