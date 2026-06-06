# SmartShelf AI — Current Status

_Last updated: June 6, 2026_  
_Competitor data sources reviewed: June 6, 2026_

---

## What This App Does

SmartShelf AI is a smart inventory and shelf management tool for convenience stores. It looks at your product data and tells you:
- What's about to run out of stock
- What to reorder and how much
- How to arrange your shelves for maximum sales
- What competitors nearby are charging for the same products

---

## ✅ What Is Implemented and Actually Works

### The Web App (Frontend)

| Feature | Status | Notes |
|---|---|---|
| Dashboard | ✅ Works | Shows stock risk, reorder count, estimated order cost, waste alerts |
| Products page | ✅ Works | Search, filter by category/status, view all SKUs |
| Reorder Recommendations | ✅ Works | AI-scored suggestions with approve/reject/edit quantity |
| Planogram (shelf layout) | ✅ Works | Visual shelf map generated from sales + margin data |
| Cross-merchandising suggestions | ✅ Works | Recommends which products to place next to each other |
| Competitor intelligence | ✅ Works | Price comparison against nearby stores (mock data) |
| AI Report | ✅ Works | Generates a full text report — but using rules, not a real AI model |
| Approved Orders page | ✅ Works | Summary of all approved purchase decisions |
| Demo dataset | ✅ Works | 40+ sample products always available, no setup needed |
| CSV file upload | ✅ Works | Upload your own product export and the app will use it |
| Market context (weather/holidays/news) | ✅ Works | Pulls live data if API keys are set; falls back to static data if not |
| Reset demo state | ✅ Works | Clears all decisions and returns to fresh demo |

### The Data Pipeline (Python scripts, run manually)

| Feature | Status | Notes |
|---|---|---|
| POS CSV import (fake data) | ✅ Works | 121-row fake dataset imported into Parquet + signals |
| Real YomYom inventory CSV | ⚠️ Not imported | `yomyom-inventory.csv` exists at project root — 7,678 real products, not yet wired in |
| Inventory / sales / margin analysis | ✅ Works | Outputs structured Parquet files (on fake data) |
| Business signals (low stock, top sellers, etc.) | ✅ Works | Saved as JSON after each import |
| Quality report per import | ✅ Works | Tells you how clean the data was |
| Competitor price scraper (Alonit) | ✅ Works | Fetches prices from Alonit FTP — data in silver Parquet |
| Wolt delivery catalog | ✅ Works | 9 venues, 366 SKUs scraped — data in silver Parquet |
| Kaggle download script | ✅ Script ready | `scripts/download_kaggle_datasets.py` — needs `KAGGLE_API_TOKEN` in `.env` to run |
| Kaggle import script | ✅ Script ready | `scripts/import_kaggle_supermarkets.py` — needs Kaggle data downloaded first |
| 10bis catalog collector | ❌ Disabled | Requires bearer token; violates ToS to automate — kept for reference only |

---

## ⚠️ Real Data That Exists But Isn't Connected Yet

This is the most important gap — data has been collected but none of it reaches the frontend.

| Data | Where it lives | What's blocking it |
|---|---|---|
| Real YomYom inventory (7,678 products, Hebrew) | `yomyom-inventory.csv` at project root | Not imported into the pipeline yet |
| Wolt competitor prices (366 SKUs, 9 venues) | `data/external/silver/products/delivery_catalog/` | No script exports it to the frontend |
| Alonit competitor prices (FTP XML) | `data/external/silver/alonit_prices/` | No script exports it to the frontend |
| Kaggle supermarket prices (Shufersal, Rami Levy, Dor Alon) | Not downloaded yet | Need `KAGGLE_API_TOKEN` + run two scripts |

The frontend still shows the 40-product hardcoded demo from `src/data/demoProducts.js` and mock competitor prices from `src/data/mockMarketData.js`.

---

## ❌ What Is NOT Implemented (and What's Missing to Make It Work)

### 1. Real AI / LLM Explanations
**What you see:** The app shows explanations like _"High velocity + low stock → reorder now."_ These look like AI wrote them, but they are hand-written rules, not a language model.

**What's missing:** A backend server that calls a real LLM (like Gemini or Claude). The code for this already exists in `src/lib/ai/llmExplanationProvider.js` and is ready to be switched on — it just needs a server to talk to.

**What's needed to fix it:**
- Deploy a small backend API (Node.js or Python)
- Add a Gemini or Claude API key on that server
- Set the `VITE_LLM_PROXY_URL` environment variable to point the app at it

---

### 2. Real AI Report Generation
**What you see:** Clicking "Generate Report" waits 2 seconds then shows a report. It feels like AI is writing it.

**What's actually happening:** A timer fires and fills in a pre-written template with numbers from your data. No AI is involved.

**What's needed to fix it:** Same backend server as above — the report builder just needs to POST the data to an LLM and stream back the response.

---

### 3. Comax POS Connector (Live Store Data)
**What you see:** A "Comax POS" option in the Data Source page. Clicking it shows an error.

**What's missing:** Comax is a real Israeli POS system used in convenience stores. Connecting to it from a browser is not allowed because API credentials can't be safely stored in a web page.

**What's needed to fix it:**
- A backend server that holds the Comax API credentials
- The server fetches live product/sales/inventory data from Comax
- The app calls the server instead of Comax directly
- Set `VITE_COMAX_PROXY_URL` to point at the server

---

### 4. Shelf Image Analysis
**What you see:** A drag-and-drop image upload area on the Planogram page.

**What's actually happening:** You can upload a photo of your shelf. Nothing happens with it. The "Analyze" button exists but is not connected to anything.

**What's needed to fix it:**
- A vision AI API (e.g. Google Vision, Claude, or GPT-4o)
- A backend endpoint that receives the image, detects products on the shelf, and compares them to the expected planogram
- Wire the result back into the UI

---

### 5. Saved State Across Devices (Database)
**What you see:** Approved orders and decisions are saved. If you refresh the page, they're still there.

**What's actually happening:** Data is saved in the browser's local storage — it only exists on the one browser/device you're using. If you switch computers or clear your browser, it's gone.

**What's needed to fix it:**
- Connect to a Supabase database (the schema and plan already exist in `docs/TECH_PERSISTENCE_AND_SUPABASE.md`)
- The app's persistence layer is already designed to swap in a Supabase adapter — it just hasn't been written yet

---

### 6. 10bis Full Product Menu
**What you see:** The 10bis connector collects store info (address, hours, etc.)

**What's missing:** The actual product catalog (items + prices) is behind a login wall on 10bis's servers. Without a valid auth token, the menu comes back empty.

**What's needed to fix it:**
- Obtain a valid `TENBIS_BEARER_TOKEN` (from an authenticated 10bis session)
- Set it as an environment variable before running the collector script

---

### 7. Real Competitor Price Data (OpenIsraeliSupermarkets)
**What you see:** The competitor intelligence panel shows price comparisons (e.g. "Shufersal sells Cola at ₪6.50"). These numbers are completely made up.

**What's available:** Israeli law requires every supermarket chain to publish prices, promotions, and store locations daily as public XML files. There are three ready-made open-source repos that handle downloading and parsing all of it:

- [`israeli-supermarket-scarpers`](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers) — downloads raw XML from all chains (Shufersal, Rami Levy, Victory, Yayno Bitan, etc.). Install with `pip install il-supermarket-scraper`.
- [`israeli-supermarket-parsers`](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-parsers) — converts those XML files to structured CSV (barcode, product name, price, promotions). Install with `pip install il-supermarket-parsers`.
- [`daily-publish-supermarket-data`](https://github.com/OpenIsraeliSupermarkets/daily-publish-supermarket-data) — runs both daily and publishes to Kaggle. A ready-made dataset is already available on Kaggle if you don't want to run the scraper yourself.

**You do NOT need to run any of the repos yourself.** The daily-publish repo runs the full pipeline automatically every night and pushes clean CSVs to Kaggle. You just pull from there.

**What you need:**
- [ ] Create a free Kaggle account at kaggle.com
- [ ] Generate a Kaggle API token: kaggle.com/settings → API → "Create New Token" (downloads `kaggle.json`)
- [ ] `pip install kaggle`
- [ ] Run: `kaggle datasets download erlichsefi/israeli-supermarkets-2024`
- [ ] Write a connector in `src/external/` that reads the price CSVs and maps `barcode → price` into the existing `ExternalProductObservation` schema
- [ ] Feed it into `multiCompetitorAdapter.js` to replace the mock data in `src/data/mockMarketData.js`
- [ ] (Optional) Use their [`entity-matching`](https://github.com/OpenIsraeliSupermarkets/entity-matching) repo to handle cases where the same product has slightly different names across chains

**What the dataset contains:** PRICE_FILE (barcode + price per product per chain), PROMO_FILE (active discounts), STORE_FILE (store locations + coordinates for filtering nearby stores). Updated nightly.

**Why this is the easiest win:** one Kaggle API token and one command gives you real prices for every Israeli supermarket chain. No scraping, no XML, no infrastructure.

---

### 9. Wolt Connector
**What you see:** Nothing — there's no Wolt option in the app yet.

**What's planned:** Collect product prices from Wolt delivery to use as competitor signals.

**What's needed:** Write a connector similar to the 10bis one (`src/external/tenbis_connector.py`).

---

## Summary Table

| Capability | Works Today | What's Blocking It |
|---|---|---|
| Demo mode full walkthrough | ✅ Yes | — |
| CSV data upload | ✅ Yes | — |
| Reorder recommendations | ✅ Yes | — |
| Planogram generation | ✅ Yes | — |
| Competitor price comparison | ✅ Mock only | Real data available — see OpenIsraeliSupermarkets below |
| AI explanations | ❌ No | Need backend + LLM API key |
| AI report writing | ❌ No | Need backend + LLM API key |
| Comax live POS sync | ❌ No | Need backend proxy + Comax credentials |
| Shelf image analysis | ❌ No | Need vision AI + backend endpoint |
| Multi-device saved state | ❌ No | Need Supabase adapter |
| 10bis full menu | ❌ No | Need bearer token |
| Wolt connector | ❌ No | Not yet written |

---

## What You Need to Build to Go From Demo → Real Product

In order of priority:

1. **Real competitor prices** (OpenIsraeliSupermarkets) — free, no backend needed, biggest visible impact
2. **A backend server** (Node.js or Python/FastAPI) — unlocks Comax, LLM, and image analysis all at once
3. **LLM API key** on that server — makes explanations and reports real
4. **Supabase database** — makes saved state persist properly
5. **Comax credentials** — enables live store data
6. **Vision AI** for shelf photo analysis
7. **10bis token + Wolt connector** — enriches competitor pricing data
