"""
run_delivery_to_firestore.py — orchestrate the delivery-catalog scrape
across all targets in configs/delivery_targets.yaml and push the results to
Firestore.

Usage
-----
  # Dry-run all enabled targets, print first 10 items per venue, no Firestore writes.
  python scripts/run_delivery_to_firestore.py --dry-run

  # Run a single target by key (matches configs/delivery_targets.yaml > targets[].key)
  python scripts/run_delivery_to_firestore.py --target yomyom_kafr_qasim

  # Full run (writes to Firestore).
  python scripts/run_delivery_to_firestore.py

  # Limit Wolt category fetches (speeds up smoke tests).
  python scripts/run_delivery_to_firestore.py --dry-run --max-categories 3

Environment
-----------
  FIREBASE_SERVICE_ACCOUNT_PATH / FIREBASE_SERVICE_ACCOUNT_JSON — required
    unless --dry-run is passed.

  TENBIS_BEARER_TOKEN — optional. Without it, 10bis targets capture only
    store metadata (no menu items).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.paths import LOGS_ROOT
from src.external.delivery_venue_connector import run_delivery_venue_collection


DEFAULT_TARGETS_PATH = _ROOT / "configs" / "delivery_targets.yaml"


# ── Logging ──────────────────────────────────────────────────────────────────

def configure_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )
    LOGS_ROOT.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOGS_ROOT / "delivery_to_firestore_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        encoding="utf-8",
    )


# ── Config loading ───────────────────────────────────────────────────────────

def load_targets(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Targets config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    targets = (data or {}).get("targets") or []
    if not isinstance(targets, list):
        raise ValueError(f"`targets` in {path} must be a list")
    return targets


def filter_targets(
    targets: list[dict[str, Any]],
    *,
    only: str | None,
) -> list[dict[str, Any]]:
    selected = []
    for tgt in targets:
        if not tgt.get("enabled", True):
            continue
        if only and tgt.get("key") != only:
            continue
        selected.append(tgt)
    return selected


# ── Arg parsing ──────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run_delivery_to_firestore",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_TARGETS_PATH,
        help=f"Path to delivery_targets.yaml (default: {DEFAULT_TARGETS_PATH})",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Run only the target whose `key` matches this string.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and write Parquet/quality reports, but skip Firestore.",
    )
    parser.add_argument(
        "--max-categories",
        type=int,
        default=None,
        help="Cap Wolt category page fetches per venue. Omit for full catalog.",
    )
    parser.add_argument(
        "--preview-items",
        type=int,
        default=10,
        help="In dry-run, print this many sample items per venue (default: 10).",
    )
    return parser.parse_args()


# ── Main ─────────────────────────────────────────────────────────────────────

def _preview_observation(obs: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": obs.get("product_name"),
        "category": obs.get("category"),
        "price": obs.get("price"),
        "sale_price": obs.get("sale_price"),
        "barcode": obs.get("barcode") or obs.get("sku"),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    configure_logging()
    args = parse_args()

    targets = filter_targets(load_targets(args.config), only=args.target)
    if not targets:
        logger.error("No enabled targets selected. Check --target and config.")
        sys.exit(2)

    observed_at = datetime.now(timezone.utc)
    summary: list[dict[str, Any]] = []

    # Defer Firestore writer import until after --dry-run check so a
    # missing firebase-admin doesn't break the dry-run path.
    write_target_to_firestore = None
    if not args.dry_run:
        from src.external.firestore_writer import write_target_to_firestore  # noqa: E402

    for target in targets:
        key = target["key"]
        url = target["url"]
        chain = target["chain"]
        role = target.get("role", "competitor")

        logger.info("──── Target: {} ({}) ────", key, chain)
        logger.info("URL: {}", url)

        try:
            result = run_delivery_venue_collection(
                [url],
                observed_at=observed_at,
                max_categories=args.max_categories,
            )
        except Exception as exc:
            logger.exception("Scrape failed for {}: {}", key, exc)
            summary.append({
                "key": key,
                "chain": chain,
                "status": "scrape_error",
                "error": str(exc),
            })
            continue

        store_infos = result.store_infos
        primary_store = store_infos[0] if store_infos else {}

        # Override / enrich with target metadata (overrides win for fields
        # we explicitly mark as authoritative in the YAML).
        primary_store = {
            **primary_store,
            "city": primary_store.get("city") or target.get("city"),
        }

        # Load silver parquet back as records for Firestore.
        observations: list[dict[str, Any]] = []
        if result.silver_path:
            try:
                import pyarrow.parquet as pq

                table = pq.read_table(result.silver_path)
                observations = table.to_pylist()
            except Exception as exc:
                logger.warning("Could not re-read silver parquet ({}): {}",
                               result.silver_path, exc)

        logger.info(
            "Scrape ok — {} observations, silver={}",
            len(observations),
            result.silver_path,
        )

        # Dry-run: print a sample and continue.
        if args.dry_run:
            preview = [
                _preview_observation(o)
                for o in observations[: args.preview_items]
            ]
            print(json.dumps({
                "key": key,
                "chain": chain,
                "city": primary_store.get("city"),
                "store_name": primary_store.get("store_name"),
                "store_id": primary_store.get("store_id"),
                "observations_count": len(observations),
                "preview": preview,
                "notes": (primary_store.get("raw") or {}).get("collection_notes") or [],
            }, ensure_ascii=False, indent=2))
            summary.append({
                "key": key,
                "chain": chain,
                "status": "dry_run_ok",
                "observations_count": len(observations),
            })
            continue

        # Real write.
        write_summary = write_target_to_firestore(
            chain=chain,
            role=role,
            target_key=key,
            store_info=primary_store,
            observations=observations,
            observed_at=observed_at,
        )
        summary.append({
            "key": key,
            "chain": chain,
            "status": "ok" if not write_summary.errors else "partial",
            "stores_written": write_summary.stores_written,
            "products_written": write_summary.products_written,
            "price_snapshots_written": write_summary.price_snapshots_written,
            "errors": write_summary.errors,
        })

    logger.info("─── Run complete ───")
    print(json.dumps({"summary": summary, "observed_at": observed_at.isoformat()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
