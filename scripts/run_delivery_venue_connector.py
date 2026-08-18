"""
run_delivery_venue_connector.py - CLI for delivery venue catalog collection.

Usage
-----
  # Every enabled target in configs/delivery_targets.yaml (what the daily
  # collector runs).
  python scripts/run_delivery_venue_connector.py

  # One target by key, or an arbitrary URL.
  python scripts/run_delivery_venue_connector.py --key yomyom_kafr_qasim
  python scripts/run_delivery_venue_connector.py --url https://wolt.com/en/isr/petah-tikva/venue/super-alonit-kibbutz-einat

  # Accepts Easy pages too; Wolt venue links are discovered from the page HTML.
  python scripts/run_delivery_venue_connector.py --url https://easy.co.il/en/page/26797254

  # Faster smoke test: only fetch the first 3 Wolt categories.
  python scripts/run_delivery_venue_connector.py --max-categories 3 --url ...

WHY THE TARGETS COME FROM THE CONFIG
------------------------------------
This script used to default to ONE hardcoded Wolt URL while
`configs/delivery_targets.yaml` listed nine enabled venues that nothing in the
daily path ever read. The daily snapshot therefore carried a single competitor
venue, and — worse — never carried `yomyom_kafr_qasim`, which is our own store
and the labelled ground truth #49 Step 5 is built on.

VENUES ARE COLLECTED ONE AT A TIME, ON PURPOSE
----------------------------------------------
`run_delivery_venue_collection()` loops over its URLs without per-URL error
handling, so a single 503 aborts every venue after it. Calling it once per venue
costs nothing (each writes its own dated silver file, and every reader globs the
day's folder) and buys two things the manifest spec in #46 Step 3 asks for
directly: `venues` vs `expected`, and a per-venue error list.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from loguru import logger

from src.common.paths import LOGS_ROOT
from src.external.delivery_venue_connector import run_delivery_venue_collection

DEFAULT_TARGETS_PATH = _ROOT / "configs" / "delivery_targets.yaml"


def load_targets(path: Path, keys: list[str] | None = None,
                 include_disabled: bool = False) -> list[dict]:
    """Enabled targets from delivery_targets.yaml, optionally filtered by key.

    A target with no URL is skipped rather than crashing the run — one
    malformed config entry must not cost a day of everyone else's history.

    `include_disabled` re-tests targets switched off for a known cause (see
    `disabled_reason`). A disabled venue is not forgotten, it is quarantined:
    a nightly alert for a cause nobody intends to act on tonight is how alerts
    stop being read.
    """
    if not path.exists():
        raise FileNotFoundError("delivery targets config not found: %s" % path)
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    targets = config.get("targets") or []

    out = []
    for target in targets:
        if not isinstance(target, dict) or not target.get("url"):
            continue
        if not include_disabled and not target.get("enabled", True):
            continue
        if keys and target.get("key") not in keys:
            continue
        out.append(target)
    return out


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
        help="Venue or linked order URL. May be passed multiple times. "
             "Overrides the targets config entirely.",
    )
    parser.add_argument(
        "--key",
        action="append",
        default=[],
        help="Collect only these target keys from the config. May be repeated.",
    )
    parser.add_argument(
        "--include-disabled",
        action="store_true",
        help="also collect targets with enabled: false, to re-test a quarantined venue",
    )
    parser.add_argument(
        "--targets",
        type=Path,
        default=DEFAULT_TARGETS_PATH,
        help=f"Path to delivery_targets.yaml (default: {DEFAULT_TARGETS_PATH})",
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
    observed_at = parse_collected_at(args.collected_at)

    if args.url:
        targets = [{"key": url, "url": url} for url in args.url]
    else:
        try:
            targets = load_targets(args.targets, args.key or None,
                                   include_disabled=args.include_disabled)
        except Exception as exc:
            logger.exception("Could not read delivery targets: {}", exc)
            sys.exit(1)

    if not targets:
        logger.error("No enabled delivery targets to collect.")
        sys.exit(1)

    results, errors = [], []
    for target in targets:
        key, url = target.get("key") or target["url"], target["url"]
        try:
            result = run_delivery_venue_collection(
                [url],
                observed_at=observed_at,
                max_categories=args.max_categories,
            )
        except Exception as exc:
            # One venue's outage must not cost the other eight. The failure is
            # recorded by key so the manifest can name it rather than reporting
            # a smaller number with no explanation.
            logger.error("venue {} failed: {}", key, exc)
            errors.append(f"{key}: {type(exc).__name__}: {exc}")
            continue

        if result.total_observations == 0:
            # A venue that resolves cleanly and returns nothing is not a
            # collected venue. Counting it as one is how `shuk_bair_rosh_haayin`
            # sat at zero products inside an "ok" run — the same shape as the
            # 31-branch price file that also finished without complaint.
            logger.error("venue {} resolved but returned 0 products", key)
            errors.append(f"{key}: resolved but returned 0 products")
            continue

        results.append((key, result))

    payload = {
        "status": "ok" if not errors else ("failed" if not results else "partial"),
        "expected": len(targets),
        "venues": len(results),
        "errors": errors,
        "total_observations": sum(r.total_observations for _k, r in results),
        "collected": [
            {
                "key": key,
                "observations": result.total_observations,
                "resolved_venue_urls": result.resolved_venue_urls,
                "store_infos": [
                    {k: v for k, v in store.items() if k != "raw"}
                    for store in result.store_infos
                ],
                "bronze_path": result.bronze_path,
                "silver_path": result.silver_path,
            }
            for key, result in results
        ],
    }

    logger.info(
        "Done - {} observations from {} of {} venue(s).{}",
        payload["total_observations"],
        payload["venues"],
        payload["expected"],
        " FAILED: " + "; ".join(errors) if errors else "",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    # Non-zero only when nothing at all was collected. A partial run still has
    # to reach the sealing step, or one dead venue discards eight good ones.
    if not results:
        sys.exit(1)


if __name__ == "__main__":
    main()
