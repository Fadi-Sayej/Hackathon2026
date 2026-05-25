"""
run_alonit_signal_pipeline.py - discovery-first Alonit product signal pipeline.

Usage
-----
  python scripts/run_alonit_signal_pipeline.py

  # Faster smoke run
  python scripts/run_alonit_signal_pipeline.py --network-max-linked 0 --delivery-max-categories 2

  # Add/override delivery venue URLs
  python scripts/run_alonit_signal_pipeline.py --delivery-url https://wolt.com/en/isr/petah-tikva/venue/super-alonit-kibbutz-einat
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
from src.external.alonit_signal_pipeline import run_alonit_signal_pipeline


def configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOGS_ROOT / "alonit_signal_pipeline_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_alonit_signal_pipeline",
        description="Run discovery-first price and availability signal collection for Alonit targets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--collected-at", type=str, default=None, metavar="ISO8601")
    parser.add_argument("--no-network", action="store_true", help="Skip Playwright network discovery.")
    parser.add_argument("--no-delivery", action="store_true", help="Skip delivery venue catalog collection.")
    parser.add_argument(
        "--no-availability",
        action="store_true",
        help="Only run price-file phases; do not run availability fallbacks.",
    )
    parser.add_argument("--network-max-linked", type=int, default=2)
    parser.add_argument("--network-wait-ms", type=int, default=1500)
    parser.add_argument("--delivery-max-categories", type=int, default=None)
    parser.add_argument(
        "--delivery-url",
        action="append",
        default=None,
        help="Wolt/TenBis/Cibus venue URL. May be passed multiple times.",
    )
    return parser.parse_args()


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

    report = run_alonit_signal_pipeline(
        observed_at=parse_collected_at(args.collected_at),
        need_availability=not args.no_availability,
        run_network=not args.no_network,
        run_delivery=not args.no_delivery,
        delivery_urls=args.delivery_url,
        network_max_linked_pages=args.network_max_linked,
        network_wait_ms=args.network_wait_ms,
        delivery_max_categories=args.delivery_max_categories,
    )

    summary = {
        "report_path": report["report_path"],
        "summary": report["summary"],
        "phase_statuses": {
            name: phase["status"]
            for name, phase in report["phases"].items()
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
