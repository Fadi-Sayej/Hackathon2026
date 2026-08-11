"""
run_alonit_collector.py — CLI entry point for the Alonit price-transparency collector.

Downloads Stores, PriceFull, and PromoFull XML.gz files for Alonit branches
in Kafr Qasim and Einat, then writes silver Parquet + a quality report.

Usage
-----
  python scripts/run_alonit_collector.py

  # Skip saving raw .xml.gz files (faster, less disk usage)
  python scripts/run_alonit_collector.py --no-save-raw

  # Override the collection timestamp (useful for backfills)
  python scripts/run_alonit_collector.py --collected-at 2025-05-25T08:00:00+00:00
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Project root on sys.path ──────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from loguru import logger

# ── Loguru — clean terminal format ───────────────────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
)

# Also write to logs/
from src.common.paths import LOGS_ROOT
LOGS_ROOT.mkdir(parents=True, exist_ok=True)
logger.add(
    LOGS_ROOT / "alonit_collector_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
)

from src.external.alonit_connector import run_alonit_collection


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_alonit_collector",
        description="Collect Alonit price-transparency files and write silver Parquet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--no-save-raw",
        action="store_true",
        default=False,
        help="Skip saving raw XML.gz files to disk (bronze layer only).",
    )
    parser.add_argument(
        "--all-stores",
        action="store_true",
        default=False,
        help=(
            "Collect every branch the chain publishes (156), not just the two "
            "named target locations. Needed for chain-wide inference (#49): a "
            "delisting is a chain-wide decision, and with only 3 branches 94%% "
            "of products are carried at fewer than 3 of them, leaving the "
            "concentration test no statistical power."
        ),
    )
    parser.add_argument(
        "--collected-at",
        type=str,
        default=None,
        metavar="ISO8601",
        help="Override collection timestamp (ISO-8601). Default: UTC now.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    collected_at: datetime | None = None
    if args.collected_at:
        try:
            collected_at = datetime.fromisoformat(args.collected_at)
            if collected_at.tzinfo is None:
                collected_at = collected_at.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.error(
                "Invalid --collected-at value: {!r}  (expected ISO-8601)",
                args.collected_at,
            )
            sys.exit(1)

    result = run_alonit_collection(
        save_raw=not args.no_save_raw,
        observed_at=collected_at,
        all_stores=args.all_stores,
    )

    if result.get("status") != "ok":
        logger.error("Collection failed: {}", result.get("reason"))
        sys.exit(2)

    logger.info(
        "Done — {} observations from {} stores.  Quality report: {}",
        result["total_observations"],
        len(result["stores_found"]),
        result["quality_report_path"],
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
