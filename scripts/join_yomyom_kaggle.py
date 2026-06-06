"""
Join YomYom barcodes against Kaggle competitor silver Parquets.
Output: data/matching/barcode_matches.parquet
"""
import polars as pl
from pathlib import Path

KAGGLE_SILVER = Path("data/external/silver/products")
YOMYOM_SILVER = Path("data/internal/silver_pos/yomyom_products.parquet")
OUTPUT = Path("data/matching/barcode_matches.parquet")

def normalize_barcode(series: pl.Series) -> pl.Series:
    return (series.cast(pl.Utf8)
            .str.strip_chars()
            .str.replace_all(r"^0+", ""))

def load_kaggle_chain(chain_dir: Path, chain_name: str) -> pl.DataFrame:
    files = list(chain_dir.rglob("*.parquet"))
    if not files:
        return pl.DataFrame()
    df = pl.concat([pl.read_parquet(f) for f in files])
    return df.select([
        pl.col("barcode").pipe(normalize_barcode).alias("barcode_norm"),
        pl.col("product_name").alias("kaggle_product_name"),
        pl.col("price").cast(pl.Float64, strict=False).alias("kaggle_price"),
        pl.lit(chain_name).alias("chain"),
    ]).drop_nulls("barcode_norm")

def main():
    yomyom = pl.read_parquet(YOMYOM_SILVER).select([
        pl.col("barcode").pipe(normalize_barcode).alias("barcode_norm"),
        pl.col("product_name").alias("yomyom_product_name"),
        pl.col("selling_price").alias("yomyom_selling_price"),
        pl.col("cost_price").alias("yomyom_cost_price"),
    ]).drop_nulls("barcode_norm").filter(pl.col("barcode_norm") != "")

    chains = []
    for chain_name in ["kaggle_dor_alon", "kaggle_rami_levy", "kaggle_shufersal"]:
        chain_dir = KAGGLE_SILVER / chain_name
        if chain_dir.exists():
            chains.append(load_kaggle_chain(chain_dir, chain_name))

    if not chains:
        print("ERROR: No Kaggle silver data found. Run import_kaggle_supermarkets.py first.")
        return

    kaggle = pl.concat(chains)
    matched = yomyom.join(kaggle, on="barcode_norm", how="inner")
    matched = matched.with_columns([
        (pl.col("yomyom_selling_price") - pl.col("kaggle_price")).alias("price_gap_ils"),
        ((pl.col("yomyom_selling_price") - pl.col("kaggle_price")) / pl.col("kaggle_price") * 100)
            .alias("price_gap_pct"),
        pl.col("barcode_norm").alias("barcode"),
    ])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    matched.write_parquet(OUTPUT)
    print(f"Wrote {len(matched)} matches to {OUTPUT}")
    print(matched.group_by("chain").len().sort("chain"))

if __name__ == "__main__":
    main()
