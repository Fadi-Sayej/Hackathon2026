"""
Export competitor price data to src/data/marketData.js.
Reads: data/matching/barcode_matches.parquet
       data/external/silver/products/delivery_catalog/
Writes: src/data/marketData.js
"""
import polars as pl
import json
from pathlib import Path
from datetime import datetime

MATCHES = Path("data/matching/barcode_matches.parquet")
DELIVERY_SILVER = Path("data/external/silver/products/delivery_catalog")
OUTPUT = Path("src/data/marketData.js")

CHAIN_META = {
    "kaggle_dor_alon": {
        "brand": "Dor Alon",
        "storeName": "Alonit Kafr Qasim",
        "storeId": "dor-alon-kq-01",
        "coords": {"lat": 32.114, "lon": 34.978},
        "distance_m": 1400,
    },
    "kaggle_rami_levy": {
        "brand": "Rami Levy",
        "storeName": "Rami Levy Petah Tikva",
        "storeId": "rami-levy-pt-01",
        "coords": {"lat": 32.089, "lon": 34.887},
        "distance_m": 2100,
    },
    "kaggle_shufersal": {
        "brand": "Shufersal",
        "storeName": "Shufersal Deal Petah Tikva",
        "storeId": "shufersal-pt-01",
        "coords": {"lat": 32.093, "lon": 34.890},
        "distance_m": 1800,
    },
}

OUR_STORE = {
    "brand": "YomYom",
    "storeName": "YomYom Kafr Qasim",
    "storeId": "yomyom-kq-01",
    "coords": {"lat": 32.114, "lon": 34.972},
}

# Live Wolt scrapes label chains by their trading name. Map the ones that correspond
# to a store we already have real coordinates for; a live price beats a static one for
# the same brand.
#
# Chains NOT listed here (Victory, King Store, Wolt Market) are deliberately skipped:
# we have no verified branch or distance for them, and inventing coordinates so a
# store appears on the map would be fabricating the exact kind of detail a manager
# would reasonably trust.
CHAIN_ALIASES = {
    "super alonit": "kaggle_dor_alon",
    "rami levy": "kaggle_rami_levy",
    "shufersal": "kaggle_shufersal",
}


def load_wolt_availability() -> set:
    available = set()
    parquet_files = list(DELIVERY_SILVER.rglob("*.parquet"))
    if not parquet_files:
        return available
    # Skip malformed files — failed scrapes produce single-column _empty files
    valid = [pl.read_parquet(f) for f in parquet_files if len(pl.read_parquet(f).columns) > 1]
    if not valid:
        return available
    # Use diagonal_relaxed to handle column type mismatches across scrape batches
    df = pl.concat(valid, how="diagonal_relaxed")
    if "barcode" in df.columns and "is_online_available" in df.columns:
        online = df.filter(
            pl.col("is_online_available") == True,
            pl.col("barcode").is_not_null(),
        )
        available = set(online["barcode"].cast(pl.Utf8).to_list())
    return available


def main():
    if not MATCHES.exists():
        print("ERROR: data/matching/barcode_matches.parquet not found. Run join_yomyom_kaggle.py first.")
        return

    matches = pl.read_parquet(MATCHES)
    wolt_available = load_wolt_availability()

    has_age = "price_age_days" in matches.columns
    if not has_age:
        print("WARNING: barcode_matches.parquet has no price_age_days column.")
        print("         Re-run scripts/join_yomyom_kaggle.py — without it the UI cannot")
        print("         tell the manager how old a competitor price is.")

    # Resolve every row to a store we have real metadata for.
    def resolve(chain: str) -> str:
        if chain in CHAIN_META:
            return chain
        return CHAIN_ALIASES.get(str(chain).strip().lower(), "")

    matches = matches.with_columns(
        pl.col("chain")
        .map_elements(resolve, return_dtype=pl.Utf8)
        .alias("store_key")
    )

    skipped = matches.filter(pl.col("store_key") == "")
    if len(skipped):
        names = sorted(set(skipped["chain"].to_list()))
        print("Skipped %d rows from chains with no verified branch: %s" % (len(skipped), ", ".join(names)))

    competitor_stores = []
    barcode_to_product_id = {}
    product_id_to_barcode = {}
    all_ages = []

    for chain, meta in CHAIN_META.items():
        chain_rows = matches.filter(pl.col("store_key") == chain)
        if len(chain_rows) == 0:
            continue

        # Freshest observation wins when a live scrape and the static dump disagree.
        if has_age:
            chain_rows = chain_rows.sort("price_age_days").unique(subset=["barcode"], keep="first")

        snapshot = {}
        for row in chain_rows.iter_rows(named=True):
            barcode = str(row["barcode"])
            price = row["kaggle_price"]
            if price is None or price <= 0:
                continue

            # UNKNOWN (null) is not the same as OUT OF STOCK (false).
            #
            # We only have availability observations for the barcodes seen in a Wolt
            # scrape — 427 of them, every one of which was observed AS AVAILABLE. We
            # have never once observed a competitor to be out of stock. Emitting False
            # for "we didn't look" caused three separate failures:
            #   - ~1,860 products were flagged "competitor out of stock" on no evidence,
            #   - those fabricated stockouts granted up to a 25% demand boost,
            #   - competitorEngine excludes isAvailable === false from price comparison,
            #     so the invented stockouts were suppressing the real price gaps that
            #     are the strongest thing this product has.
            # null passes the engine's `!== false` check, so prices compare normally
            # while nothing claims a stockout we never saw.
            entry = {
                "price": round(float(price), 2),
                "isAvailable": True if barcode in wolt_available else None,
            }
            if has_age:
                age = row.get("price_age_days")
                observed = row.get("observed_date")
                if age is not None:
                    entry["ageDays"] = int(age)
                    all_ages.append(int(age))
                if observed is not None:
                    entry["observedAt"] = str(observed)
            snapshot[barcode] = entry

            if barcode not in barcode_to_product_id:
                product_id = f"ym-{barcode}"
                barcode_to_product_id[barcode] = product_id
                product_id_to_barcode[product_id] = barcode

        competitor_stores.append({**meta, "snapshot": snapshot})

    # Every competitor price the UI shows is a claim about another business. This block
    # gives the UI what it needs to qualify that claim instead of stating it flatly.
    data_freshness = {
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "priceCount": len(all_ages),
        "oldestPriceAgeDays": max(all_ages) if all_ages else None,
        "newestPriceAgeDays": min(all_ages) if all_ages else None,
        "medianPriceAgeDays": sorted(all_ages)[len(all_ages) // 2] if all_ages else None,
        "note": (
            "Competitor prices are reference observations, not live quotes. "
            "Show ageDays alongside any price shown to the store."
        ),
    }

    js_content = f"""// AUTO-GENERATED by scripts/export_competitor_market_data.py
// Generated: {datetime.utcnow().isoformat()}Z
// Source: data/matching/barcode_matches.parquet

export const OUR_STORE = {json.dumps(OUR_STORE, ensure_ascii=False, indent=2)}

export const COMPETITOR_STORES = {json.dumps(competitor_stores, ensure_ascii=False, indent=2)}

export const BARCODE_TO_PRODUCT_ID = {json.dumps(barcode_to_product_id, ensure_ascii=False, indent=2)}

export const PRODUCT_ID_TO_BARCODE = {json.dumps(product_id_to_barcode, ensure_ascii=False, indent=2)}

// How old these prices are. The UI must label competitor prices with `ageDays`
// rather than presenting them as today's shelf price.
export const DATA_FRESHNESS = {json.dumps(data_freshness, ensure_ascii=False, indent=2)}
"""

    OUTPUT.write_text(js_content, encoding="utf-8")
    total_barcodes = sum(len(s["snapshot"]) for s in competitor_stores)
    print(f"Wrote {OUTPUT}: {len(competitor_stores)} stores, {total_barcodes} barcode entries")
    if all_ages:
        print("  price age (days): newest %d, median %d, oldest %d" % (
            min(all_ages), sorted(all_ages)[len(all_ages) // 2], max(all_ages)))


if __name__ == "__main__":
    main()
