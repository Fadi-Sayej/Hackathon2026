"""
export_assortment_gap.py — turn the assortment gap into UI recommendations (issue #48).

Reads  data/matching/assortment_gap.parquet  (produced by build_assortment_gap.py)
Writes public/data/assortment_gap.json       (read by the web app)

WHAT THIS ADDS ON TOP OF THE PARQUET
    1. Applies the store's own policy from configs/store_policy.yaml. The parquet
       holds every gap product with no judgement applied; this step is where a store
       that does not carry a segment stops seeing it. The default is to carry
       everything — no assumption is made for any store.
    2. Emits the canonical recommendation shape from docs/UI_DATA_CONTRACT.md §4.

THE §4.2 RULE THIS FILE MUST NEVER BREAK
    These are products we have NEVER stocked. There is no sales history, so
    velocityConfidence is 'none' and the card must not carry a velocity claim of any
    kind — no units per day, no days-until-stockout, no projected revenue. The
    evidence is branch coverage and the competitor price, and nothing else.

Usage
-----
    python3 scripts/export_assortment_gap.py
    python3 scripts/export_assortment_gap.py --store yomyom-kq-01 --limit 200
    python3 scripts/export_assortment_gap.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import polars as pl
import yaml

from src.common.paths import MATCHING_ROOT, PROJECT_ROOT

GAP_PARQUET = MATCHING_ROOT / "assortment_gap.parquet"
STORE_POLICY = PROJECT_ROOT / "configs" / "store_policy.yaml"
SEGMENTS_CONFIG = PROJECT_ROOT / "configs" / "product_segments.yaml"
OUTPUT = PROJECT_ROOT / "public" / "data" / "assortment_gap.json"

DEFAULT_STORE = "yomyom-kq-01"

# A gap product needs to be carried by a meaningful share of comparable branches
# before it is worth a manager's attention. One branch stocking something is noise.
MIN_COVERAGE = 0.25


def load_policy(store_id: str) -> dict:
    """Resolve the effective policy for a store. Absent config ⇒ carry everything."""
    policy = {"excludes": [], "flag_for_review": []}
    if not STORE_POLICY.exists():
        return policy
    cfg = yaml.safe_load(STORE_POLICY.read_text(encoding="utf-8")) or {}
    defaults = cfg.get("defaults") or {}
    policy["excludes"] = list(defaults.get("excludes") or [])
    policy["flag_for_review"] = list(defaults.get("flag_for_review") or [])

    store = (cfg.get("stores") or {}).get(store_id) or {}
    # A store's own list replaces the default rather than adding to it: a store that
    # declares `excludes: []` is explicitly saying "I carry everything", and that must
    # not be silently overridden by a default written for someone else.
    if "excludes" in store:
        policy["excludes"] = list(store.get("excludes") or [])
    if "flag_for_review" in store:
        policy["flag_for_review"] = list(store.get("flag_for_review") or [])
    return policy


def segment_labels() -> dict[str, dict]:
    if not SEGMENTS_CONFIG.exists():
        return {}
    cfg = yaml.safe_load(SEGMENTS_CONFIG.read_text(encoding="utf-8")) or {}
    return cfg.get("segments") or {}


def split_segments(value: str | None) -> list[str]:
    return [s for s in (value or "").split(",") if s]


def build_reason(row: dict, total_branches: int) -> str:
    """Display-ready, and deliberately free of any velocity claim (§4.2)."""
    n = row["branches_carrying"]
    price = row.get("competitor_price_median")
    parts = [f"{n} of {total_branches} comparable branches carry this. You don't."]
    if price is not None:
        parts.append(f"They sell it at about ₪{price:.2f}.")
    return " ".join(parts)


def to_recommendation(row: dict, total_branches: int, review: list[str]) -> dict:
    segs = split_segments(row.get("segments"))
    flagged = sorted(set(segs) & set(review))
    coverage = row["coverage_ratio"]

    return {
        # Barcode, not one of our product ids — we do not stock this yet.
        "productId": row["barcode_norm"],
        "productName": row.get("product_name") or row["barcode_norm"],
        "category": row.get("category"),
        "type": "ASSORTMENT_GAP",
        # Coverage is the only honest urgency signal available: the more branches
        # carry it, the more established the demand. It is not a velocity claim.
        "urgency": "HIGH" if coverage >= 0.75 else "MEDIUM" if coverage >= 0.5 else "LOW",
        "status": "PENDING",
        # Confidence in the *observation*, not in a forecast. Capped at 0.7: one
        # snapshot proves they stock it, never that it sells.
        "confidence": round(min(0.7, 0.35 + coverage * 0.35), 2),
        "reason": build_reason(row, total_branches),
        "velocityConfidence": "none",
        "valueAtStake": round(row["gap_score"], 3),

        "evidence": {
            "branchesCarrying": row["branches_carrying"],
            "branchesCompared": total_branches,
            "coverageRatio": round(coverage, 4),
            "competitorPriceMedian": row.get("competitor_price_median"),
            "competitorPriceMin": row.get("competitor_price_min"),
            "competitorPriceMax": row.get("competitor_price_max"),
            "priceBand": row.get("price_band"),
            "lastSeenAt": row.get("last_seen_at"),
        },
        "segments": segs,
        "reviewRequired": flagged or None,
        # No metrics block: every field in §4's `metrics` is about a product we
        # already stock. Emitting zeros there would read as measured facts.
        "metrics": None,
        "context": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", default=DEFAULT_STORE)
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--min-coverage", type=float, default=MIN_COVERAGE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not GAP_PARQUET.exists():
        raise SystemExit(f"{GAP_PARQUET} not found. Run scripts/build_assortment_gap.py first.")

    gap = pl.read_parquet(GAP_PARQUET)
    total_in = len(gap)
    total_branches = int(round(gap["branches_carrying"].max() / max(gap["coverage_ratio"].max(), 1e-9)))

    policy = load_policy(args.store)
    excludes, review = policy["excludes"], policy["flag_for_review"]

    gap = gap.filter(pl.col("coverage_ratio") >= args.min_coverage)
    after_coverage = len(gap)

    excluded_count = 0
    if excludes:
        pattern = "|".join(excludes)
        excluded_count = len(gap.filter(pl.col("segments").fill_null("").str.contains(pattern)))
        gap = gap.filter(~pl.col("segments").fill_null("").str.contains(pattern))

    gap = gap.sort("gap_score", descending=True).head(args.limit)
    rows = [to_recommendation(r, total_branches, review) for r in gap.iter_rows(named=True)]

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "storeId": args.store,
        "source": "price_transparency_snapshots",
        "branchesCompared": total_branches,
        "policy": {
            "excludes": excludes,
            "flagForReview": review,
            # Stated explicitly so the UI can say "no policy set" rather than
            # implying the owner has approved seeing everything.
            "configured": bool(excludes),
        },
        "counts": {
            "gapTotal": total_in,
            "afterMinCoverage": after_coverage,
            "excludedByPolicy": excluded_count,
            "emitted": len(rows),
        },
        "recommendations": rows,
    }

    if args.dry_run:
        print(json.dumps({k: v for k, v in payload.items() if k != "recommendations"}, indent=2))
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== assortment gap export ===")
    print(f"  store                {args.store}")
    print(f"  branches compared    {total_branches:>7,}")
    print(f"  gap products         {total_in:>7,}")
    print(f"  >= {args.min_coverage:.0%} coverage       {after_coverage:>7,}")
    print(f"  excluded by policy   {excluded_count:>7,}  ({', '.join(excludes) if excludes else 'no exclusions set'})")
    print(f"  emitted              {len(rows):>7,}")
    if not args.dry_run:
        print(f"\n  written → {OUTPUT.relative_to(PROJECT_ROOT)}")
    if rows:
        print(f"\n  top: {rows[0]['productName']}")
        print(f"       {rows[0]['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
