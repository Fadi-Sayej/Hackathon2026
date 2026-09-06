Read these files before doing anything:
- CLAUDE.md
- STATUS.md
- sprint_plan.md
- src/App.jsx
- src/data/mockMarketData.js
- src/data/marketContext.js
- src/lib/ai/gemini.js
- .env.example

You are working on Person C's tasks from sprint_plan.md: frontend wiring, dead code removal, and stale defaults. C-4 and C-2 have zero dependencies — start there immediately.

YOUR TASKS IN ORDER:

C-4 (do first — no dependencies):
  C-4a: Verify gemini.js is not imported anywhere: grep -r "gemini" src/ --include="*.js" --include="*.jsx"
        Expected: zero results. Then delete src/lib/ai/gemini.js.
  C-4b: Verify these assets are not referenced anywhere: grep -r "hero.png\|react.svg\|vite.svg" src/
        Expected: zero results. Then delete src/assets/hero.png, src/assets/react.svg, src/assets/vite.svg.
  C-4c: Remove the line VITE_LLM_EXPLANATIONS_ENABLED=false from .env.example (Person D is adding a proper block for it).
  After all three: run npm run lint and npm run build — both must pass.

C-2 (no dependencies):
  In src/data/marketContext.js, find the line with currentDate: '2026-05-15' and change it to:
    currentDate: new Date().toISOString().split('T')[0],
  In .env.example, change VITE_HOLIDAY_COUNTRY=AT to VITE_HOLIDAY_COUNTRY=IL
  and VITE_NEWS_QUERY=Jordan to VITE_NEWS_QUERY=Israel supermarket prices

C-1 (wait for Person B to finish B-3 before running this):
  Step 1: Create src/data/marketData.js as a stub right now so builds never break:
    // Stub — overwritten by scripts/export_competitor_market_data.py when real data is available
    export { COMPETITOR_STORES, OUR_STORE, BARCODE_TO_PRODUCT_ID, PRODUCT_ID_TO_BARCODE } from './mockMarketData.js'
  Step 2: In src/App.jsx line 18, change the import from './data/mockMarketData.js' to './data/marketData.js'
  Step 3: Add src/data/marketData.js to .gitignore so the generated file is never committed.
  Run npm run build to confirm it passes.
  Once Person B says B-3 is done and src/data/marketData.js has real data, reload the dev server and verify real competitor prices appear in the UI.

C-3 (wait for Person A to finish A-2 — already done, so you can start this now):
  Read scripts/normalize-datasets.mjs first, then add the YomYom Parquet loader as described in sprint_plan.md. The silver Parquet is at data/internal/silver_pos/yomyom_products.parquet. Map fields as: barcode→id, product_name→name, category→category, selling_price→price, cost_price→cost, current_stock→currentStock (clamp to 0). Use defaults for missing fields (shelfQuantity:0, shelfCapacity:10, salesLast7Days:0, salesLast30Days:0, supplier:'Unknown', leadTimeDays:3, returnedUnits:0, damagedUnits:0).
  Done when: npm run sprint7 completes and src/data/demoProducts.js contains 7,000+ products with Hebrew names.

Only work on frontend files and the files mentioned here. Do not touch Python pipeline scripts.