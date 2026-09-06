"""
build_product_matches.py
------------------------
CLI entry point for the YomYom product-matching pipeline.

Reads:
  data/internal/silver_pos/yomyom_products.parquet   (preferred)
  data/internal/raw_pos/yomyom/sample_yomyom_pos.csv (fallback)

  data/signals/competitor_product_signals/**/*.parquet  (preferred)
  data/external/silver/alonit_prices/**/*.parquet       (fallback)
  data/external/silver/products/delivery_catalog/**/*.parquet (fallback)

Writes:
  data/matching/product_matches.parquet
  data/matching/manual_review_queue.parquet
  reports/quality/product_matching_<ts>.json

Usage
-----
  python scripts/build_product_matches.py

  # Override run timestamp (useful for backfill / testing)
  python scripts/build_product_matches.py --run-at 2025-05-25T10:00:00+00:00

  # Print quality metrics JSON to stdout after the run
  python scripts/build_product_matches.py --print-quality
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── project root on sys.path ──────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── reconfigure stdout for Hebrew chars on Windows ────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from loguru import logger

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
)

from src.common.paths import LOGS_ROOT

LOGS_ROOT.mkdir(parents=True, exist_ok=True)
logger.add(
    LOGS_ROOT / "product_matching_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
)

from src.matching.product_matching import run_product_matching


# ─────────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="build_product_matches",
        description="Match YomYom internal products against competitor product signals.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--run-at",
        type=str,
        default=None,
        metavar="ISO8601",
        help="Override run timestamp (ISO-8601).  Default: UTC now.",
    )
    p.add_argument(
        "--print-quality",
        action="store_true",
        default=False,
        help="Print the quality report JSON to stdout after the run.",
    )
    return p.parse_args()


def _print_summary(metrics: dict) -> None:
    print()
    print("=" * 60)
    print("  Product Matching — Summary")
    print("=" * 60)
    print(f"  Internal products          : {metrics['internal_products_count']}")
    print(f"  Competitor signal corpus   : {metrics['competitor_signals_count']}")
    print()
    print(f"  Total match records        : {metrics['total_matches']}")
    print(f"  Matched internal products  : {metrics['matched_internal_products']}")
    print(f"  Unmatched internal products: {metrics['unmatched_internal_products']}")
    print(f"  Match rate                 : {metrics['match_rate_internal_pct']:.1f} %")
    print()
    print("  By method:")
    for method, count in (metrics.get("matches_by_method") or {}).items():
        print(f"    {method:20s}: {count}")
    print()
    print(f"  Auto-approved              : {metrics['auto_approved_count']}")
    print(f"  Manual review queue        : {metrics['manual_review_count']}")
    print()
    note = metrics.get("language_note", "")
    if note:
        # Wrap at ~56 chars
        words = note.split()
        line, lines = [], []
        for w in words:
            if sum(len(x) + 1 for x in line) + len(w) > 56:
                lines.append(" ".join(line))
                line = [w]
            else:
                line.append(w)
        if line:
            lines.append(" ".join(line))
        print("  Note:")
        for ln in lines:
            print(f"    {ln}")
    print("=" * 60)
    print()


def main() -> None:
    args = parse_args()

    run_at: datetime | None = None
    if args.run_at:
        try:
            run_at = datetime.fromisoformat(args.run_at)
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.error("Invalid --run-at: {!r}", args.run_at)
            sys.exit(1)

    result = run_product_matching(run_at=run_at)

    if result.get("status") != "ok":
        logger.error("Matching failed: {}", result.get("reason"))
        sys.exit(2)

    m = result["metrics"]
    _print_summary(m)

    logger.info("Matches         : {}", result["matches_path"])
    logger.info("Review queue    : {}", result["review_queue_path"])
    logger.info("Quality report  : {}", result["quality_report_path"])

    if args.print_quality:
        print(json.dumps(m, indent=2, ensure_ascii=False))

    sys.exit(0)


if __name__ == "__main__":
    main()
