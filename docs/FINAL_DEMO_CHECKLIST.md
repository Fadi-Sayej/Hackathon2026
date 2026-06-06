# SmartShelf AI — Final Demo Checklist

Run this checklist in order on the demo machine before presenting. Check each item.

---

## 1. Machine Setup

- [ ] Node.js is installed (`node --version` shows v18 or later)
- [ ] `npm install` has been run in the project root (no errors)
- [ ] `.env` file exists (copy from `.env.example` if missing)
- [ ] `VITE_ENABLE_LIVE_MARKET_CONTEXT` is set to `false` in `.env` (ensures stable static market context during demo)
- [ ] `VITE_LLM_PROXY_URL` is either unset (rule-based explanations) OR proxy is running on port 8000 and tested
- [ ] No other process is using port 5173

---

## 2. Start the App

```bash
npm run dev
```

- [ ] Terminal shows "Local: http://localhost:5173/"
- [ ] No build errors in terminal

---

## 3. Browser Setup

- [ ] Use Chrome or Safari (not Firefox — print dialog behavior may differ)
- [ ] Navigate to `http://localhost:5173`
- [ ] Browser DevTools are closed (right-click → close, or F12)
- [ ] Browser zoom is at 100% (Cmd+0 on Mac / Ctrl+0 on Windows)
- [ ] Only one tab open (the app)
- [ ] Browser popup blocker is disabled for localhost (needed for print dialog)
- [ ] Bookmarks bar is hidden for a clean screen (Cmd+Shift+B to toggle)

---

## 4. App Reset (Clean Demo State)

To ensure a clean demo state with no lingering approvals from previous runs:

- [ ] Look for the "Reset Demo State" button in the top navigation bar
- [ ] If the button is visible (appears when overrides exist), click it
- [ ] Confirm the app returns to: Dashboard → all recommendations show as pending → Approved Orders shows EmptyState

Alternatively, clear localStorage manually:
1. Open DevTools → Application tab → Local Storage → `http://localhost:5173`
2. Click "Clear All"
3. Refresh the page

---

## 5. Pre-Demo Smoke Test

Walk the safe click path once before the presentation:

- [ ] Dashboard loads with 6 KPI cards showing non-zero values
- [ ] "Reorder Suggestions" KPI shows a number > 0
- [ ] Navigate to Smart Reorder — at least 3 recommendation cards appear
- [ ] First card shows HIGH urgency badge and non-empty AI explanation text
- [ ] Edit quantity on the first card (change to any valid number)
- [ ] Click Approve on the first card → badge changes to APPROVED, opacity drops
- [ ] Navigate to Approved Orders → approved item appears, total is non-zero
- [ ] Click Export CSV → file downloads (check Downloads folder)
- [ ] Click Print → browser print dialog opens → cancel the dialog
- [ ] Navigate to Shelf Optimization → shelf layout renders (not EmptyState)
- [ ] Click one product slot → Placement Reason panel appears
- [ ] **Reset Demo State** (click the reset button or clear localStorage) → everything back to pending

---

## 6. If Something Goes Wrong

| Problem | Fix |
|---|---|
| Port 5173 already in use | `lsof -ti:5173 | xargs kill -9` then `npm run dev` |
| App loads blank page | Hard refresh (Cmd+Shift+R), then check terminal for errors |
| KPI cards show NaN or 0 | Data load failed — reset demo state, refresh, check console |
| No recommendations appear | Data may be empty — switch to Demo Data connector via Data Source page |
| Print dialog doesn't open | Check browser popup blocker settings for localhost |
| CSV download doesn't start | Check browser download permissions for localhost |
| Proxy not responding | Set `VITE_LLM_PROXY_URL=` (empty) in `.env` to fall back to rule-based explanations, then restart dev server |

---

## 7. Safe Click Path (exact sequence for the demo)

1. Start at Dashboard — point to 6 KPI cards
2. Navigate to Smart Reorder — walk through one recommendation card
3. Edit quantity (optional) → Click Approve
4. Navigate to Approved Orders — show total, Export CSV, Print
5. Navigate to Shelf Optimization — click one shelf slot
6. END — do not navigate beyond this unless specifically asked

---

## 8. Risky Click Paths to Avoid

| Action | Risk | Severity |
|---|---|---|
| Click "Comax" on Data Source page | Shows error message immediately | MEDIUM |
| Upload a CSV during demo | May show validation warnings or break data | HIGH |
| Click "Analyze" on Shelf Compliance and explain it as real vision AI | The analysis is simulated | MEDIUM |
| Open browser DevTools during presentation | Shows internal state, may alarm judges | LOW |
| Try to approve a recommendation with quantity 0 | Approve button is disabled — may need explaining | LOW |
| Refresh page during demo without resetting first | May show unexpected state from prior run | MEDIUM |
