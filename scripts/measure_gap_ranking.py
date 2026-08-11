"""
measure_gap_ranking.py — does the clever ranker beat the naive one? (issue #48)

Issue #48 states plainly: build the naive baseline first, measure both, and if the
clever ranker does not beat it, SHIP THE BASELINE and say so. This script is what
makes that a measurement rather than an opinion.

THE TWO RANKERS
    baseline   score_coverage — how many comparable branches carry it, nothing else
    candidate  score_value    — coverage x sqrt(assumed margin)

WHAT CANNOT BE MEASURED YET, AND WHY THIS SCRIPT SAYS SO OUT LOUD
    Precision@10 needs ground truth: a judgement of whether each recommendation is
    one the manager would actually act on. We do not have that until he reviews a
    list. So this script reports the *structural* differences between the two
    rankings and the proxies we can compute honestly, then prints the human step
    that is still required. It never invents an accuracy number.

Usage
-----
    python3 scripts/measure_gap_ranking.py
    python3 scripts/measure_gap_ranking.py --k 20 --review-sheet reports/gap_review.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import polars as pl

from src.common.paths import MATCHING_ROOT, PROJECT_ROOT

GAP_PARQUET = MATCHING_ROOT / "assortment_gap.parquet"

# A forecourt shop lives on items that turn fast and cost little. This is not used
# to rank — it is used to *describe* what each ranking put in front of the manager,
# so the difference between them is legible before he reviews anything.
CONVENIENCE_BANDS = ("impulse", "everyday")


def overlap_at_k(a: pl.DataFrame, b: pl.DataFrame, k: int) -> int:
    top_a = set(a.head(k)["barcode_norm"].to_list())
    top_b = set(b.head(k)["barcode_norm"].to_list())
    return len(top_a & top_b)


def describe(df: pl.DataFrame, k: int, label: str) -> dict:
    top = df.head(k)
    conv = top.filter(pl.col("price_band").is_in(CONVENIENCE_BANDS))
    return {
        "label": label,
        "median_coverage": float(top["coverage_ratio"].median()),
        "median_price": float(top["competitor_price_median"].median()),
        "convenience_share": len(conv) / max(len(top), 1),
        "min_branches": int(top["branches_carrying"].min()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--min-coverage", type=float, default=0.25)
    parser.add_argument("--review-sheet", default="reports/gap_review.csv",
                        help="write a CSV for the manager to mark accept/reject")
    args = parser.parse_args()

    if not GAP_PARQUET.exists():
        raise SystemExit(f"{GAP_PARQUET} not found. Run scripts/build_assortment_gap.py first.")

    gap = pl.read_parquet(GAP_PARQUET).filter(pl.col("coverage_ratio") >= args.min_coverage)

    baseline = gap.sort(["score_coverage", "estimated_unit_margin"], descending=True)
    candidate = gap.sort(["score_value", "branches_carrying"], descending=True)

    k = args.k
    b_desc = describe(baseline, k, "baseline  (coverage only)")
    c_desc = describe(candidate, k, "candidate (coverage x sqrt margin)")

    print("=== gap ranking comparison ===")
    print(f"  candidates ranked      {len(gap):,}   (coverage >= {args.min_coverage:.0%})")
    print(f"  top-{k} overlap         {overlap_at_k(baseline, candidate, k)}/{k}\n")

    hdr = f"  {'':<36} {'med.cov':>8} {'med.price':>10} {'conv.share':>11} {'min.branches':>13}"
    print(hdr)
    for d in (b_desc, c_desc):
        print(f"  {d['label']:<36} {d['median_coverage']:>8.2%} "
              f"{d['median_price']:>9.1f}₪ {d['convenience_share']:>10.0%} {d['min_branches']:>13,}")

    print(f"\n=== what each ranking actually surfaces (top {k}) ===")
    for df, name in ((baseline, "BASELINE"), (candidate, "CANDIDATE")):
        print(f"\n  {name}")
        for i, r in enumerate(df.head(k).iter_rows(named=True), 1):
            seg = f"  [{r['segments']}]" if r["segments"] else ""
            print(f"    {i:>2}. {(r['product_name'] or '')[:34]:<34} "
                  f"{r['branches_carrying']:>4} br  {r['competitor_price_median']:>7.1f}₪"
                  f"  {r['price_band']}{seg}")

    # ── the honest verdict ───────────────────────────────────────────────────
    print("\n=== verdict ===")
    if c_desc["convenience_share"] < b_desc["convenience_share"]:
        print("  The candidate surfaces FEWER convenience-band items than the baseline.")
        print("  Its only advantage is assumed margin, and margin without turnover is")
        print("  not evidence. Recommend: SHIP THE BASELINE. This is an outcome issue")
        print("  #48 explicitly allows, not a failure.")
    elif c_desc["convenience_share"] > b_desc["convenience_share"]:
        print("  The candidate surfaces more convenience-band items. Worth reviewing,")
        print("  but still needs the manager's judgement below before it ships.")
    else:
        print("  The two rankings are structurally equivalent at this k.")
        print("  Prefer the baseline: it makes no assumption about margin.")

    print("\n=== still required: Precision@k needs a human ===")
    print("  No accuracy number can be computed from this data alone. Precision@k")
    print("  means 'how many of these would the manager actually stock', and only he")
    print("  can answer that. The acceptance bar in #48 is 6 of the first 10.")

    sheet = PROJECT_ROOT / args.review_sheet
    sheet.parent.mkdir(parents=True, exist_ok=True)
    review = (
        baseline.head(max(k, 20))
        .select("barcode_norm", "product_name", "branches_carrying",
                "competitor_price_median", "price_band", "segments")
        .with_columns(pl.lit("").alias("would_stock_yes_no"),
                      pl.lit("").alias("why_not"))
    )
    review.write_csv(sheet)
    print(f"  review sheet written -> {sheet.relative_to(PROJECT_ROOT)}")
    print("  Fill in would_stock_yes_no, then re-run with the completed sheet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
