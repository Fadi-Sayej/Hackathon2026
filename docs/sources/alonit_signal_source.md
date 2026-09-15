# Alonit / Super Alonit — Signal Source Semantics

**Document scope:** What the current Alonit and Super Alonit data sources provide,
what they cannot prove, current findings, recommended field semantics, and how
the data will be used downstream.

**Do not modify collectors, parsers, or data files based on this document.**
This doc is descriptive, not prescriptive for code.

---

## 1. Source Overview

Three distinct sources currently contribute observations tagged with
`store_chain = "Alonit"` or related names.

| Source | Collector | Transport | Coverage |
|---|---|---|---|
| **Dor Alon price-transparency files** | `src/external/alonit_connector.py` | FTP / Cerberus portal | Chain-wide price list; branch-level when store_id resolves |
| **Wolt delivery catalog – Super Alonit Einat** | _(planned / external)_ | HTTPS scrape | Single-venue product listing for online delivery |
| **Easy / Dor Alon store pages** | _(not built)_ | Web scrape | Store-level descriptive data only; no product prices |

### 1a. Dor Alon Price-Transparency Files

Israeli mandatory price-transparency law (2015) requires all chains with > 1
supermarket to publish current shelf prices in XML format. Dor Alon publishes
three file types on `url.retail.publishedprices.co.il` (FTP + Cerberus web portal):

| File type | Pattern | Content |
|---|---|---|
| `Stores` | `*store*` | All branches: `StoreId`, `StoreName`, `City`, `Address` |
| `PriceFull` | `*pricef*` | Per-branch full catalogue: `ItemCode`, `ItemName`, `ItemPrice` |
| `PromoFull` | `*promof*` | Per-branch active promotions: item codes, `DiscountedPrice`, date range |

Files are gzip-compressed UTF-8 XML. The `src/external/alonit_connector.py`
connector downloads them, filters for target store IDs, and writes silver
Parquet to `data/external/silver/alonit_prices/`.

### 1b. Wolt Delivery Catalog — Super Alonit Einat

Wolt hosts a delivery menu for the Super Alonit Einat venue. This is an
independent catalog maintained by the delivery platform and may differ
from the in-store range. It provides:

- Active product listings for that specific venue on that specific day
- Visible price at time of scrape
- Category and sometimes subcategory as displayed on Wolt
- `rank_in_category` when scraped with position data
- `most_ordered` flag when Wolt surfaces a "Most ordered" badge

### 1c. Easy / Dor Alon Store Pages

The Easy/Dor Alon web presence can confirm store existence, city, and opening
hours. It does **not** provide product-level prices or stock. Treat it as a
location signal only, not a product source.

---

## 2. What Each Source Provides

### 2a. Dor Alon Price-Transparency — What It Gives You

| Signal | Field | Notes |
|---|---|---|
| Official shelf price (ILS) | `price` | The mandatory-published price. Legally the maximum the branch may charge. |
| Promotional / discounted price | `sale_price` | From PromoFull; only present when an active dated promotion exists. |
| Product name | `product_name` | As registered with the chain's ERP. May differ from shelf label. |
| Barcode / item code | `barcode`, `sku` | GTIN when available; internal code otherwise. ~10–15% of rows may lack a GTIN. |
| Branch identity | `store_id`, `store_name`, `city` | When the file header's `StoreId` resolves to a known branch. |
| Promo signal | `sale_price` is not None | Confirms a promotion exists on that item in that branch on that date. |

**Confirmed Super Alonit Einat store IDs** (as seen in the Dor Alon Stores XML):

| `store_id` | Notes |
|---|---|
| `666` | Super Alonit Einat — primary ID seen in Stores file |
| `657` | Super Alonit Einat — alternate / secondary ID |
| `649` | Super Alonit Einat — third variant |

> These IDs should be treated as the authoritative branch keys for
> Super Alonit Einat when joining price files to recommendations.

### 2b. Wolt Delivery Catalog — What It Gives You

| Signal | Field | Notes |
|---|---|---|
| Product is listed for delivery | `is_in_catalog = True` | Product appears on the Wolt menu for this venue right now. |
| Delivery price | `price` | The Wolt-displayed price. May differ from shelf price. |
| Promotional price on Wolt | `sale_price` | Only when Wolt shows a strikethrough price. |
| Category (Wolt taxonomy) | `category`, `subcategory` | Wolt's own naming, not the chain's. |
| Display rank | `rank_in_category` | Position in Wolt's category listing, 1-based. |
| "Most ordered" badge | `most_ordered = True` | Only set when Wolt explicitly surfaces this label. |
| Barcode | `barcode` | Occasionally visible; often absent from delivery catalogs. |

---

## 3. What Each Source Does NOT Prove

These are hard constraints. Do not infer or assert any of the following
from the data alone.

### 3a. Price-Transparency Files (Dor Alon FTP)

| Claim | Status |
|---|---|
| Product is physically on the shelf | ❌ **Not provable.** A product in the price file may be listed chain-wide but out of stock or delisted at a specific branch. |
| Product was sold recently | ❌ **Not provable.** Price files contain the full catalogue regardless of recent sales activity. |
| Product is currently orderable online | ❌ **Not provable.** FTP data has no online availability signal. Set `is_online_available = None`. |
| Sales volume or velocity | ❌ **Not provable.** No transaction counts exist in price-transparency files. |
| Price is identical across all branches | ❌ **Not assumed.** Each PriceFull file is per-branch. Chain-level aggregation loses branch variance. |

### 3b. Wolt Delivery Catalog

| Claim | Status |
|---|---|
| Product is in physical stock at the store | ❌ **Not guaranteed.** Wolt catalog presence means the venue has listed the item, not that it is in stock. Delivery catalog listings lag real-time inventory. |
| Product is sold in-store at the same price | ❌ **Not assumed.** Wolt prices include delivery markups and may differ from shelf prices. |
| Product is always available when listed | ❌ **Not guaranteed.** Out-of-stock items may remain listed with an "unavailable" state only visible at checkout. |
| Sales volume or velocity | ❌ **Not provable.** Rank and "Most ordered" are editorial/algorithmic signals, not transaction counts. |

> **Relative strength:** Wolt catalog presence is a *stronger* availability
> signal than price-file presence — an active Wolt listing requires the venue
> to actively maintain it — but it still falls short of confirmed physical stock.
> Do not upgrade either source to `is_online_available = True` without an
> explicit "In stock" / "Available" response from the source.

---

## 4. Current Findings

### 4a. Super Alonit Einat

- ✅ **Found in Dor Alon Stores file** under store IDs 666, 657, and 649.
- ✅ PriceFull and PromoFull files exist for these store IDs.
- ✅ Product-level price signals are available for Super Alonit Einat.
- ✅ Wolt delivery catalog for Einat is a planned secondary source.

### 4b. Alonit Kafr Qasim / Al-Madina 2

- ⚠️ **Not clearly found** in the Dor Alon Stores XML under the primary city
  field `"כפר קאסם"` (Kafr Qasim).
- The connector searches these aliases in the Stores file:
  `"כפר קאסם"`, `"kafr qasim"`, `"kfar qasim"`, `"al-madina 2"`,
  `"al madina 2"`, `"אל מדינה 2"`.
- None of these aliases returned a confirmed match in the last Stores file
  inspection.
- **Working hypothesis:** the Kafr Qasim Alonit may operate under a different
  store name in the Dor Alon system, or may not be in the current Stores file
  (e.g., it is a franchise under a different chain ID).
- **Current status:** Kafr Qasim remains a **location-level competitor** only.
  No product-level price signals from Dor Alon can be attributed to it yet.
  Do not populate `store_id`, `store_name`, or `city = "Kafr Qasim"` in
  `ExternalProductObservation` until a confirmed store match is found.

---

## 5. Recommended Field Semantics

These are the authoritative meanings for `ExternalProductObservation` fields
in the context of Alonit data. Where a field is marked **Planned**, it does
not yet exist in `src/common/schema.py` and should be added before the
relevant collector is built.

### 5a. Existing Fields

| Field | Type | Alonit Price File | Wolt Catalog |
|---|---|---|---|
| `appears_in_price_file` | `bool` | `True` — product was in FTP XML | `False` |
| `is_online_available` | `bool \| None` | `None` — price files carry no availability signal | `None` unless source explicitly says "in stock" |
| `is_in_catalog` | `bool` | `True` — product is in the chain's registered catalogue | `True` — product is listed on the Wolt menu |
| `source_type` | `str` | `"price_file"` | `"delivery_catalog"` |
| `branch_confidence` | `"high"\|"medium"\|"low"\|"unknown"` | `"high"` when store_id + store_name + city all present; `"low"` if only chain known | `"high"` — Wolt is always venue-specific |
| `price` | `Decimal \| None` | Official mandated shelf price | Wolt-displayed price |
| `sale_price` | `Decimal \| None` | From PromoFull, active promos only | Wolt strikethrough price if visible |
| `store_id` | `str \| None` | Dor Alon internal store ID (e.g. `"666"`) | Wolt venue ID |

### 5b. Planned Fields (not yet in schema)

These fields are recommended for addition before building the matching and
recommendation layers. They are named here so the team uses consistent
terminology.

| Field | Type | Default | Meaning |
|---|---|---|---|
| `appears_in_delivery_catalog` | `bool` | `False` | `True` when observation came from a delivery platform (Wolt, TenBis, Cibus). Complement of `appears_in_price_file`. |
| `explicit_online_available` | `bool \| None` | `None` | `True` **only** when the source page/API explicitly states the item is available for purchase right now. Never inferred. |
| `availability_confidence` | `"confirmed"\|"probable"\|"low"\|"unknown"` | `"unknown"` | Composite: `"confirmed"` = explicit in-stock signal; `"probable"` = active Wolt listing; `"low"` = price-file only; `"unknown"` = no signal. |
| `price_signal_confidence` | `"official"\|"platform"\|"estimated"\|"unknown"` | `"unknown"` | `"official"` = mandatory price-transparency file; `"platform"` = delivery catalog; `"estimated"` = derived/interpolated. |

> **Rule of thumb:** a product can move from `availability_confidence = "low"`
> to `"probable"` when a Wolt catalog observation exists for it. It reaches
> `"confirmed"` only when an explicit in-stock API response is captured.

---

## 6. How This Data Will Be Used Downstream

### 6a. Matching Against YomYom POS Products

~~The `src/external/mcp_price_adapter.py` adapter~~ (**removed 2026-09-16**, Phase 4 Task 4.1c — the engine's own market chain does this now) joined observations to YomYom
POS products by:

1. Exact barcode match (GTIN → GTIN)
2. Case-insensitive product name match
3. Substring match
4. Fuzzy name ratio (≥ 0.72 by default)

A match does not imply the competitor sells the same physical product —
only that the names/barcodes are consistent. Treat as a **candidate match**
until verified.

### 6b. Price Comparison

When a YomYom product matches an Alonit observation:

- Use `price` for the shelf-to-shelf comparison (official price vs. YomYom `selling_price`)
- Use `sale_price` if not None to detect if the competitor is running a promo
  that YomYom is not matching
- Do NOT compare YomYom `cost_price` against Alonit `price` — different margins

### 6c. Assortment Gap Detection

Products appearing in Alonit price files but **absent** from YomYom POS data
are candidates for assortment gap recommendations. Confidence tiers:

| Scenario | Recommendation confidence |
|---|---|
| In Alonit price file AND Wolt catalog | High — competitor actively sells and delivers it |
| In Alonit price file only | Medium — competitor has it priced, may stock it |
| In Wolt catalog only | Medium-low — could be delivery-only SKU |

### 6d. Category Gap Detection

Use `category` from Wolt observations (which maps to real consumer-facing
categories) rather than price-file product names. Price files often lack
category data; Wolt always provides a category hierarchy.

### 6e. Recommendation Evidence

When the recommendation engine cites an Alonit observation as evidence,
it must include:

```json
{
  "evidence_source":  "alonit_price_file | wolt_delivery_catalog",
  "store_id":         "666",
  "store_name":       "Super Alonit Einat",
  "observed_at":      "2025-05-25T10:00:00+00:00",
  "competitor_price": 8.90,
  "competitor_promo": 7.50,
  "branch_confidence": "high",
  "availability_note": "Appears in official price file. Physical stock not confirmed."
}
```

Do not present price-file evidence as "the competitor has this product in
stock" — always qualify with `availability_note`.

---

## 7. Assumptions and Open Questions

| # | Assumption / Question | Status |
|---|---|---|
| 1 | Kafr Qasim branch is operated by Dor Alon (not a franchise or sub-chain) | **Unconfirmed** — if it is a franchise under a different chain ID, it will not appear in the `doralon` FTP feed |
| 2 | Store IDs 666, 657, 649 all refer to the same physical location (Super Alonit Einat) | **Probable** — seen together in the Stores file but not manually verified against an address |
| 3 | PriceFull prices are shelf prices inclusive of VAT | **Assumed** — standard for Israeli price-transparency law, but not verified in the XML schema notes |
| 4 | Wolt delivery prices equal Wolt-displayed prices (no hidden fees in the item price field) | **Assumed** — to be validated on first Wolt scrape |
| 5 | PromoFull `EndDate` is reliable and correctly excludes expired promotions | **Assumed** — the parser filters `EndDate < today`; chains occasionally leave expired promos in the file |

---

*Last updated: 2025-05-25 · Maintainer: YomYom market-intelligence team*
