"""
import_kaggle_supermarkets.py — run the Kaggle Israeli supermarkets importer.

By default imports all configured chains. Pass --chain to import one.

Usage
-----
    python scripts/import_kaggle_supermarkets.py
    python scripts/import_kaggle_supermarkets.py --chain dor_alon
    python scripts/import_kaggle_supermarkets.py --chain dor_alon --chain rami_levy
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.external.kaggle_supermarket_importer import CHAIN_CONFIG, import_chain


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Kaggle Israeli supermarket prices into bronze/silver.")
    parser.add_argument(
        "--chain",
        action="append",
        dest="chains",
        choices=list(CHAIN_CONFIG),
        help="Chain to import (repeat for multiple). Defaults to all.",
    )
    args = parser.parse_args()

    chains = args.chains or list(CHAIN_CONFIG)
    observed_at = datetime.now(timezone.utc)

    logger.info("Starting Kaggle supermarket import: {}", chains)

    results = []
    for chain in chains:
        result = import_chain(chain, observed_at=observed_at)
        results.append(result)
        if result.status == "ok":
            logger.success(
                "{}: {:,} rows → {:,} observations",
                chain, result.total_rows, result.observations,
            )
        else:
            logger.error("{}: {} — {}", chain, result.status, result.errors)

    print("\n── Summary ────────────────────────────────")
    for r in results:
        status_icon = "✓" if r.status == "ok" else "✗"
        print(f"  {status_icon} {r.chain:<15} {r.observations:>8,} observations  ({r.total_rows:,} raw rows)")
    print()

    report_path = _ROOT / "reports" / "kaggle_import" / f"kaggle_import_{observed_at.strftime('%Y%m%dT%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps([vars(r) for r in results], indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Import report: {}", report_path)


if __name__ == "__main__":
    main()
