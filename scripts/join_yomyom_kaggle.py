"""
join_yomyom_kaggle.py — match YomYom barcodes against competitor prices (task A-5).

Output: data/matching/barcode_matches.parquet

Sources, in order of freshness:
  - data/external/silver/products/delivery_catalog/  live Wolt scrapes, refreshed on demand
  - data/external/silver/products/kaggle_*/          static Kaggle dump, prices span 2013-2026

WHY THIS SCRIPT CARES SO MUCH ABOUT DATES
-----------------------------------------
We tell a store manager "Shufersal sells this for X". If X is three years old we have
not helped them, we have misled them — and one wrong claim about a competitor costs
more trust than every correct one earns. Stale prices are worse than no prices.

So this join:
  1. carries observed_at through (the previous version dropped it, which made price
     age unknowable downstream and impossible to label in the UI),
  2. keeps only the MOST RECENT observation per (barcode, chain) — the previous
     version emitted every barcode x store x date combination, ~4.7 rows per barcode,
     any one of which might be the decade-old one,
  3. records price_age_days and is_stale on every row,
  4. drops observations older than --max-age-days by default.

Run:
    python3 scripts/join_yomyom_kaggle.py
    python3 scripts/join_yomyom_kaggle.py --max-age-days 180
    python3 scripts/join_yomyom_kaggle.py --include-stale   # keep them, still flagged
"""

from __future__ import annotations

import argparse
import glob
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

EXTERNAL_SILVER = Path("data/external/silver/products")
YOMYOM_SILVER = Path("data/internal/silver_pos/yomyom_products.parquet")
OUTPUT = Path("data/matching/barcode_matches.parquet")

KAGGLE_CHAINS = ["kaggle_dor_alon", "kaggle_rami_levy", "kaggle_shufersal"]
DELIVERY_DIR = "delivery_catalog"

# A year-old shelf price is a weak claim; older than that we will not show at all.
DEFAULT_MAX_AGE_DAYS = 365

# Our own listings are not a competitor. The Wolt gap is a separate signal.
OWN_CHAIN_MARKERS = {"yom yom", "yomyom", "yom-yom"}


def normalize_barcode(expr: pl.Expr) -> pl.Expr:
    return expr.cast(pl.Utf8).str.strip_chars().str.replace_all(r"^0+", "")


def _parquets_with_barcode(root: Path) -> list:
    """Silver dirs accumulate empty placeholder parquets; skip anything without a barcode."""
    found = []
    for path in sorted(glob.glob(str(root / "**" / "*.parquet"), recursive=True)):
        try:
            if "barcode" in pl.read_parquet_schema(path):
                found.append(path)
        except Exception:
            continue
    return found


def _load(paths: list, chain_expr: pl.Expr) -> pl.DataFrame:
    frames = []
    for path in paths:
        try:
            df = pl.read_parquet(path)
            frames.append(
                df.select(
                    [
                        normalize_barcode(pl.col("barcode")).alias("barcode_norm"),
                        pl.col("product_name").cast(pl.Utf8).alias("competitor_product_name"),
                        pl.col("price").cast(pl.Float64, strict=False).alias("competitor_price"),
                        pl.col("observed_at").cast(pl.Utf8).alias("observed_at"),
                        chain_expr.alias("chain"),
                    ]
                )
            )
        except Exception as exc:  # a malformed file must not sink the whole join
            print("  skipped %s (%s)" % (path, exc))
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="vertical_relaxed")


def load_sources() -> pl.DataFrame:
    frames = []

    delivery_paths = _parquets_with_barcode(EXTERNAL_SILVER / DELIVERY_DIR)
    if delivery_paths:
        live = _load(delivery_paths, pl.col("store_chain").cast(pl.Utf8))
        if len(live):
            live = live.filter(
                pl.col("chain").is_not_null()
                & ~pl.col("chain").str.to_lowercase().str.strip_chars().is_in(list(OWN_CHAIN_MARKERS))
            )
            frames.append(live)
            print("  delivery_catalog : %d rows (live)" % len(live))

    for chain in KAGGLE_CHAINS:
        paths = _parquets_with_barcode(EXTERNAL_SILVER / chain)
        if not paths:
            continue
        df = _load(paths, pl.lit(chain))
        if len(df):
            frames.append(df)
            print("  %-17s: %d rows (static dump)" % (chain, len(df)))

    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="vertical_relaxed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    parser.add_argument(
        "--include-stale",
        action="store_true",
        help="keep observations older than --max-age-days (still flagged is_stale)",
    )
    args = parser.parse_args()

    if not YOMYOM_SILVER.exists():
        print("ERROR: %s not found. Run the POS import first." % YOMYOM_SILVER)
        return 1

    yomyom = (
        pl.read_parquet(YOMYOM_SILVER)
        .select(
            [
                normalize_barcode(pl.col("barcode")).alias("barcode_norm"),
                pl.col("product_name").alias("yomyom_product_name"),
                pl.col("selling_price").cast(pl.Float64, strict=False).alias("yomyom_selling_price"),
                pl.col("cost_price").cast(pl.Float64, strict=False).alias("yomyom_cost_price"),
            ]
        )
        .drop_nulls("barcode_norm")
        .filter(pl.col("barcode_norm") != "")
        .unique(subset=["barcode_norm"], keep="first")
    )

    print("Loading competitor sources:")
    competitors = load_sources()
    if competitors.is_empty():
        print("ERROR: no competitor silver data found.")
        return 1

    competitors = competitors.drop_nulls(["barcode_norm", "competitor_price"]).filter(
        (pl.col("barcode_norm") != "") & (pl.col("competitor_price") > 0)
    )

    # Most recent observation per (barcode, chain). Without this the join emits every
    # barcode x store x date combination and may surface a decade-old price when a
    # current one exists for the same product.
    competitors = competitors.sort("observed_at", descending=True).unique(
        subset=["barcode_norm", "chain"], keep="first"
    )

    matched = yomyom.join(competitors, on="barcode_norm", how="inner")
    if matched.is_empty():
        print("ERROR: no barcode overlap between YomYom and competitor data.")
        return 1

    today = datetime.now(timezone.utc).date()
    matched = matched.with_columns(
        pl.col("observed_at")
        .str.slice(0, 10)
        .str.strptime(pl.Date, "%Y-%m-%d", strict=False)
        .alias("observed_date")
    ).with_columns(
        (pl.lit(today) - pl.col("observed_date")).dt.total_days().alias("price_age_days")
    )

    matched = matched.with_columns(
        [
            (pl.col("price_age_days") > args.max_age_days).fill_null(True).alias("is_stale"),
            (pl.col("yomyom_selling_price") - pl.col("competitor_price")).alias("price_gap_ils"),
            (
                (pl.col("yomyom_selling_price") - pl.col("competitor_price"))
                / pl.col("competitor_price")
                * 100
            ).alias("price_gap_pct"),
            pl.col("barcode_norm").alias("barcode"),
            # Kept so export_competitor_market_data.py keeps working unchanged.
            pl.col("competitor_product_name").alias("kaggle_product_name"),
            pl.col("competitor_price").alias("kaggle_price"),
        ]
    )

    total = len(matched)
    stale = int(matched["is_stale"].sum())

    if not args.include_stale:
        matched = matched.filter(~pl.col("is_stale"))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    matched.write_parquet(OUTPUT)

    print()
    print("Matched %d barcode/chain pairs before filtering." % total)
    print("  stale (>%dd): %d (%.1f%%) — %s" % (
        args.max_age_days, stale, (stale / total * 100) if total else 0.0,
        "kept, flagged is_stale" if args.include_stale else "EXCLUDED from output"))
    print("  written: %d rows across %d distinct products -> %s" % (
        len(matched), matched["barcode"].n_unique(), OUTPUT))

    if len(matched):
        print()
        print("Age of prices in the output:")
        ages = (
            matched.with_columns(pl.col("observed_date").dt.year().alias("year"))
            .group_by("year").len().sort("year", descending=True)
        )
        for year, count in ages.iter_rows():
            print("   %s: %d" % (year, count))
        print()
        print("By chain:")
        for chain, count in matched.group_by("chain").len().sort("len", descending=True).iter_rows():
            print("   %-22s %d" % (chain, count))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
