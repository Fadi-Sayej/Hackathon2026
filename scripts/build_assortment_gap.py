"""
build_assortment_gap.py — what competitors carry and we do not (issue #48, track T3).

The manager cannot know what he does not know. His POS only ever reports products he
already stocks, so an item every shop around him sells is invisible to him forever.
This script produces that list.

WHY A SEPARATE DATASET
    data/matching/barcode_matches.parquet is an INNER join — every row must have a
    YomYom side, so a competitor item we do not carry cannot exist in it. The gap was
    not filtered out at export; it was discarded upstream. This writes a new, parallel
    dataset and leaves barcode_matches.parquet untouched, because price-gap and
    price-age logic depend on its inner-join semantics.

SOURCE
    The daily collector (T1) lands per-branch price-transparency observations under
    data/external/snapshots/<date>/price_transparency/. That is fresher and far wider
    than the Kaggle chain dumps, and it carries real per-branch identity, which is what
    makes coverage ("12 of 156 branches carry this") meaningful rather than a guess.

Usage
-----
    python3 scripts/build_assortment_gap.py
    python3 scripts/build_assortment_gap.py --min-coverage 0.25 --top 50
    python3 scripts/build_assortment_gap.py --json
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import polars as pl
import yaml

from src.common.paths import EXTERNAL_ROOT, MATCHING_ROOT, PROJECT_ROOT, SNAPSHOTS_ROOT

EXTERNAL_SNAPSHOTS = EXTERNAL_ROOT / "snapshots"
OUTPUT = MATCHING_ROOT / "assortment_gap.parquet"
SEGMENTS_CONFIG = PROJECT_ROOT / "configs" / "product_segments.yaml"

# Our own margin, used to value a product we have never sold. Deliberately
# conservative: a gap recommendation that oversells its upside is worse than one
# that undersells it, because the manager only has to be burned once.
DEFAULT_MARGIN_RATE = 0.25


def normalize_barcode(expr: pl.Expr) -> pl.Expr:
    """Identical to scripts/join_yomyom_kaggle.py:54.

    Kept byte-for-byte the same on purpose. Two different normalisers across the
    codebase would silently produce two different match rates and nobody would
    notice until the numbers disagreed.
    """
    return expr.cast(pl.Utf8).str.strip_chars().str.replace_all(r"^0+", "")


def load_competitor_observations() -> pl.DataFrame:
    """Every collected price-transparency observation, newest snapshot wins."""
    files = sorted(glob.glob(
        str(EXTERNAL_SNAPSHOTS / "*" / "price_transparency" / "**" / "*_silver.parquet"),
        recursive=True,
    ))
    if not files:
        raise SystemExit(
            "No collected snapshots found under data/external/snapshots/.\n"
            "Run scripts/collect_daily.sh first (see issue #46)."
        )

    frames = []
    for path in files:
        try:
            if "barcode" in pl.read_parquet_schema(path):
                frames.append(pl.read_parquet(path))
        except Exception:
            # Silver dirs accumulate placeholder parquets from failed scrapes.
            continue
    if not frames:
        raise SystemExit("Snapshots exist but none carry a barcode column.")

    df = pl.concat(frames, how="diagonal_relaxed")
    df = df.filter(pl.col("barcode").is_not_null() & (pl.col("barcode") != ""))
    return df.with_columns(normalize_barcode(pl.col("barcode")).alias("barcode_norm"))


def tag_segments(gap: pl.DataFrame) -> pl.DataFrame:
    """Tag each product with the segments it belongs to. Tags only — never filters.

    Whether a store carries a segment is decided per store in configs/store_policy.yaml
    and defaults to carrying everything. This function must stay free of any judgement
    about what a shop *should* sell: it answers "what is this?" and stops there.
    """
    if not SEGMENTS_CONFIG.exists():
        return gap.with_columns(
            pl.lit(None, dtype=pl.Utf8).alias("segments"),
            pl.lit(None, dtype=pl.Utf8).alias("segments_review"),
        )

    cfg = yaml.safe_load(SEGMENTS_CONFIG.read_text(encoding="utf-8")) or {}
    name = pl.col("product_name").fill_null("")

    confident, review = [], []
    for seg, spec in (cfg.get("segments") or {}).items():
        spec = spec or {}
        if kws := spec.get("match_any"):
            hit = name.str.contains("|".join(kws))
            # A price rule alone is enough for segments like high_ticket.
            confident.append((seg, hit))
        if (floor := spec.get("price_above")) is not None:
            confident.append((seg, pl.col("competitor_price_median") >= float(floor)))
        if kws := spec.get("review_any"):
            review.append((seg, name.str.contains("|".join(kws))))

    def collect(pairs):
        if not pairs:
            return pl.lit(None, dtype=pl.Utf8)
        parts = [pl.when(cond).then(pl.lit(seg)).otherwise(pl.lit(None)) for seg, cond in pairs]
        return pl.concat_list(parts).list.drop_nulls().list.unique().list.join(",")

    return gap.with_columns(
        collect(confident).alias("segments"),
        collect(review).alias("segments_review"),
    ).with_columns(
        pl.when(pl.col("segments") == "").then(None).otherwise(pl.col("segments")).alias("segments"),
        pl.when(pl.col("segments_review") == "").then(None)
          .otherwise(pl.col("segments_review")).alias("segments_review"),
    )


def load_our_catalogue() -> pl.DataFrame:
    """YomYom's own products, from the most recent internal snapshot."""
    snapshots = sorted(p for p in SNAPSHOTS_ROOT.glob("*") if (p / "products.parquet").exists())
    if not snapshots:
        raise SystemExit("No internal snapshot with products.parquet found.")
    df = pl.read_parquet(snapshots[-1] / "products.parquet")
    df = df.filter(pl.col("barcode").is_not_null() & (pl.col("barcode") != ""))
    return df.with_columns(normalize_barcode(pl.col("barcode")).alias("barcode_norm"))


def build_gap(competitor: pl.DataFrame, ours: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """Anti-join, then aggregate to one row per product with branch coverage."""
    total_branches = competitor["store_id"].n_unique()

    # ── the anti-join this whole track turns on ──────────────────────────────
    gap_rows = competitor.join(
        ours.select("barcode_norm").unique(),
        on="barcode_norm",
        how="anti",
    )

    # Latest observation per (branch, product); a branch may appear in several
    # snapshots and we only want to count it once.
    latest = (
        gap_rows.sort("observed_at", descending=True)
        .unique(subset=["store_id", "barcode_norm"], keep="first")
    )

    # Price arrives as text from the XML price files, and sale_price is all-null in
    # the current feed. Cast rather than assume: strict=False turns an unparseable
    # price into null instead of killing the whole run.
    price_col = pl.coalesce([
        pl.col("sale_price").cast(pl.Float64, strict=False),
        pl.col("price").cast(pl.Float64, strict=False),
    ])

    gap = (
        latest.group_by("barcode_norm")
        .agg(
            pl.col("product_name").drop_nulls().first().alias("product_name"),
            pl.col("brand").drop_nulls().first().alias("brand"),
            pl.col("category").drop_nulls().first().alias("category"),
            pl.col("store_id").n_unique().alias("branches_carrying"),
            price_col.median().alias("competitor_price_median"),
            price_col.min().alias("competitor_price_min"),
            price_col.max().alias("competitor_price_max"),
            pl.col("observed_at").max().alias("last_seen_at"),
        )
        .with_columns(
            (pl.col("branches_carrying") / total_branches).alias("coverage_ratio"),
        )
        .with_columns(
            # What one unit would earn us, at a conservative assumed margin.
            (pl.col("competitor_price_median") * DEFAULT_MARGIN_RATE).alias("estimated_unit_margin"),
            pl.when(pl.col("competitor_price_median") < 15).then(pl.lit("impulse"))
              .when(pl.col("competitor_price_median") < 40).then(pl.lit("everyday"))
              .when(pl.col("competitor_price_median") < 100).then(pl.lit("considered"))
              .otherwise(pl.lit("high_ticket"))
              .alias("price_band"),
        )
        .with_columns(
            # ── Two rankings, kept side by side on purpose ───────────────────
            #
            # Issue #48 requires beating a naive baseline before shipping anything
            # clever, so both live in the data and scripts/measure_gap_ranking.py
            # compares them instead of us asserting which is better.
            #
            # rank_value: coverage × √margin. Damping the margin with a square root
            # was still not enough — a ₪350 projector in 97 branches outranks a ₪6
            # snack in 155. For a forecourt shop that is backwards: the projector
            # sells a few times a year, the snack sells daily.
            (pl.col("coverage_ratio") * pl.col("estimated_unit_margin").sqrt()).alias("score_value"),
            # rank_coverage: coverage alone, which is the DEFAULT.
            # Without sales history, price is not evidence of anything. Coverage is:
            # a product carried by 155 of 156 comparable branches is carried because
            # it turns. That inference rests on observed behaviour across a whole
            # chain rather than on an assumed margin we invented.
            pl.col("coverage_ratio").alias("score_coverage"),
        )
        .with_columns(
            pl.col("score_coverage").alias("gap_score"),
        )
        .sort(["gap_score", "estimated_unit_margin"], descending=True)
    )

    stats = {
        "competitor_rows": len(competitor),
        "competitor_branches": total_branches,
        "competitor_distinct_products": competitor["barcode_norm"].n_unique(),
        "our_distinct_products": ours["barcode_norm"].n_unique(),
        "gap_products": len(gap),
        "overlap_products": competitor["barcode_norm"].n_unique() - len(gap),
    }
    return gap, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-coverage", type=float, default=0.0,
                        help="drop products carried by fewer than this fraction of branches")
    parser.add_argument("--band", choices=["impulse", "everyday", "considered", "high_ticket"],
                        help="restrict to one price band")
    parser.add_argument("--top", type=int, default=20, help="how many rows to print")
    parser.add_argument("--json", action="store_true", help="emit stats as JSON")
    parser.add_argument("--dry-run", action="store_true", help="do not write the parquet")
    args = parser.parse_args()

    competitor = load_competitor_observations()
    ours = load_our_catalogue()
    gap, stats = build_gap(competitor, ours)
    gap = tag_segments(gap)

    # The parquet always holds the COMPLETE gap. --min-coverage and --band shape what
    # is printed, never what is stored: a stored file that silently depends on the
    # flags of whoever ran it last is a trap for everything downstream.
    if not args.dry_run:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        gap.write_parquet(OUTPUT)

    view = gap
    if args.min_coverage > 0:
        view = view.filter(pl.col("coverage_ratio") >= args.min_coverage)
        stats["after_min_coverage"] = len(view)
    if args.band:
        view = view.filter(pl.col("price_band") == args.band)
        stats["after_band"] = len(view)

    if args.json:
        print(json.dumps(stats, indent=2))
        return 0

    print("=== assortment gap ===")
    print(f"  competitor branches      {stats['competitor_branches']:>9,}")
    print(f"  competitor observations  {stats['competitor_rows']:>9,}")
    print(f"  competitor products      {stats['competitor_distinct_products']:>9,}")
    print(f"  our products             {stats['our_distinct_products']:>9,}")
    print(f"  we already carry         {stats['overlap_products']:>9,}")
    print(f"  GAP — they carry, we do not  {stats['gap_products']:>9,}")
    if "after_min_coverage" in stats:
        print(f"  after --min-coverage     {stats['after_min_coverage']:>9,}")
    if not args.dry_run:
        print(f"\n  written → {OUTPUT}")

    print("\n  by price band (full dataset):")
    for band in ("impulse", "everyday", "considered", "high_ticket"):
        n = len(gap.filter(pl.col("price_band") == band))
        wide = len(gap.filter((pl.col("price_band") == band) & (pl.col("coverage_ratio") >= 0.5)))
        print(f"    {band:<12} {n:>7,}   of which >=50% of branches: {wide:>5,}")

    tagged = gap.filter(pl.col("segments").is_not_null())
    print(f"\n  segment tags (no product is excluded here — see configs/store_policy.yaml):")
    if len(tagged):
        counts: dict[str, int] = {}
        for row in tagged["segments"].to_list():
            for seg in row.split(","):
                counts[seg] = counts.get(seg, 0) + 1
        for seg, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"    {seg:<16} {n:>7,}")
    else:
        print("    none")
    flagged = len(gap.filter(pl.col("segments_review").is_not_null()))
    if flagged:
        print(f"    {'(needs review)':<16} {flagged:>7,}  ambiguous keyword match — resolved by #51")

    print(f"\n=== top {args.top} by gap score ===")
    with pl.Config(tbl_rows=args.top, fmt_str_lengths=30, tbl_width_chars=160):
        print(view.head(args.top).select(
            "product_name", "branches_carrying", "coverage_ratio",
            "competitor_price_median", "price_band", "segments", "gap_score",
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
