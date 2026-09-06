"""
build_competitor_product_signals.py
------------------------------------
CLI entry point for the competitor-product signal builder.

Reads:
  data/external/silver/alonit_prices/**/*.parquet
  data/external/silver/products/delivery_catalog/**/*.parquet

Writes:
  data/signals/competitor_product_signals/competitor_product_signals_<ts>.parquet
  reports/quality/competitor_product_signals_<ts>.json

Usage
-----
  python scripts/build_competitor_product_signals.py

  # Override run timestamp (useful for backfill / testing)
  python scripts/build_competitor_product_signals.py --run-at 2025-05-25T10:00:00+00:00

  # Print quality metrics JSON to stdout
  python scripts/build_competitor_product_signals.py --print-quality
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
    LOGS_ROOT / "competitor_signals_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
)

from src.signals.competitor_product_signals import build_competitor_product_signals


# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="build_competitor_product_signals",
        description="Build unified competitor-product signals from Alonit + Wolt sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--run-at",
        type=str,
        default=None,
        metavar="ISO8601",
        help="Override run timestamp (ISO-8601). Default: UTC now.",
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
    print("  Competitor Product Signals — Summary")
    print("=" * 60)
    print(f"  Total signals          : {metrics['total_signals']}")
    print(f"  Unique barcodes        : {metrics['unique_barcodes']}")
    print(f"  Unique products        : {metrics['unique_products']}")
    print(f"  Categories             : {metrics['categories_count']}")
    print()
    print(f"  Price-file only        : {metrics['price_file_only_count']}")
    print(f"  Delivery-catalog only  : {metrics['delivery_catalog_only_count']}")
    print(f"  Both sources (merged)  : {metrics['both_sources_count']}")
    print()
    print(f"  Missing barcode        : {metrics['missing_barcode_count']}  ({metrics['missing_barcode_pct']:.1f}%)")
    print(f"  Missing price          : {metrics['missing_price_count']}  ({metrics['missing_price_pct']:.1f}%)")
    print(f"  Explicit availability  : {metrics['explicit_availability_count']}")
    print()
    ac = metrics.get("availability_confidence_dist", {})
    print("  Availability confidence distribution:")
    for k in ("high", "medium", "low", "unknown"):
        if k in ac:
            print(f"    {k:8s} : {ac[k]}")
    pc = metrics.get("price_signal_confidence_dist", {})
    print("  Price-signal confidence distribution:")
    for k in ("official", "platform", "estimated", "unknown"):
        if k in pc:
            print(f"    {k:8s} : {pc[k]}")
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

    result = build_competitor_product_signals(run_at=run_at)

    if result.get("status") != "ok":
        logger.error("Build failed: {}", result.get("reason"))
        sys.exit(2)

    _print_summary(result["metrics"])
    logger.info("Output  : {}", result["output_parquet"])
    logger.info("Quality : {}", result["quality_report"])

    if args.print_quality:
        print(json.dumps(result["metrics"], indent=2, ensure_ascii=False))

    sys.exit(0)


if __name__ == "__main__":
    main()
