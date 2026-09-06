"""
run_delivery_venue_connector.py - CLI for delivery venue catalog collection.

Usage
-----
  python scripts/run_delivery_venue_connector.py --url https://wolt.com/en/isr/petah-tikva/venue/super-alonit-kibbutz-einat

  # Accepts Easy pages too; Wolt venue links are discovered from the page HTML.
  python scripts/run_delivery_venue_connector.py --url https://easy.co.il/en/page/26797254

  # Faster smoke test: only fetch the first 3 Wolt categories.
  python scripts/run_delivery_venue_connector.py --max-categories 3 --url ...
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from loguru import logger

from src.common.paths import LOGS_ROOT
from src.external.delivery_venue_connector import run_delivery_venue_collection


DEFAULT_URLS = [
    "https://wolt.com/en/isr/petah-tikva/venue/super-alonit-kibbutz-einat",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_delivery_venue_connector",
        description="Collect Wolt/TenBis/Cibus/Easy-linked delivery venue catalogs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        help="Venue or linked order URL. May be passed multiple times.",
    )
    parser.add_argument(
        "--collected-at",
        type=str,
        default=None,
        metavar="ISO8601",
        help="Override collection timestamp. Default: UTC now.",
    )
    parser.add_argument(
        "--max-categories",
        type=int,
        default=None,
        help="Optional cap for Wolt category pages. Omit for full catalog.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOGS_ROOT / "delivery_venue_connector_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        encoding="utf-8",
    )


def parse_collected_at(value: str | None) -> datetime | None:
    if not value:
        return None
    collected_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if collected_at.tzinfo is None:
        collected_at = collected_at.replace(tzinfo=timezone.utc)
    return collected_at


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    configure_logging()
    args = parse_args()
    urls = args.url or DEFAULT_URLS

    try:
        result = run_delivery_venue_collection(
            urls,
            observed_at=parse_collected_at(args.collected_at),
            max_categories=args.max_categories,
        )
    except Exception as exc:
        logger.exception("Delivery venue collection failed: {}", exc)
        sys.exit(1)

    payload = result.__dict__.copy()
    payload["store_infos"] = [
        {key: value for key, value in store.items() if key != "raw"}
        for store in result.store_infos
    ]
    logger.info(
        "Done - {} observations from {} resolved venue URL(s). Quality report: {}",
        result.total_observations,
        len(result.resolved_venue_urls),
        result.quality_report_path,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
