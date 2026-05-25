"""
import_yomyom_pos.py — CLI entry point for the YomYom POS importer.

Usage
-----
  python scripts/import_yomyom_pos.py \\
      --input data/internal/raw_pos/yomyom/sample_yomyom_pos.csv

  # custom config
  python scripts/import_yomyom_pos.py \\
      --input  data/internal/raw_pos/yomyom/sample_yomyom_pos.csv \\
      --config configs/pos_schema_mapping.yaml

  # fix the import timestamp (useful for backfills)
  python scripts/import_yomyom_pos.py \\
      --input       data/internal/raw_pos/yomyom/sample_yomyom_pos.csv \\
      --imported-at 2025-05-25T08:00:00+00:00
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── project root on sys.path ──────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from loguru import logger

# ── loguru — clean terminal format ────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
)
# also write to logs/
from src.common.paths import LOGS_ROOT
LOGS_ROOT.mkdir(parents=True, exist_ok=True)
logger.add(
    LOGS_ROOT / "pos_import_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
)

from src.internal.pos_importer import run_import, CONFIG_PATH


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="import_yomyom_pos",
        description="Import a YomYom POS CSV into silver Parquet + signals.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        type=Path,
        metavar="CSV_PATH",
        help="Path to the raw POS CSV file.",
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        default=CONFIG_PATH,
        metavar="YAML_PATH",
        help=f"Schema-mapping YAML (default: {CONFIG_PATH.relative_to(_ROOT)})",
    )
    parser.add_argument(
        "--imported-at",
        type=str,
        default=None,
        metavar="ISO8601",
        help="Override import timestamp (ISO-8601). Default: now (UTC).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # validate input path
    if not args.input.exists():
        logger.error("Input file not found: {}", args.input)
        sys.exit(1)

    if not args.config.exists():
        logger.error("Config file not found: {}", args.config)
        sys.exit(1)

    # parse optional timestamp
    imported_at: str | None = None
    if args.imported_at:
        try:
            imported_at = datetime.fromisoformat(args.imported_at).isoformat()
        except ValueError:
            logger.error("Invalid --imported-at value: '{}' (expected ISO-8601)", args.imported_at)
            sys.exit(1)

    # run the pipeline
    result = run_import(
        input_path=args.input,
        config_path=args.config,
        imported_at=imported_at,
    )

    if result.get("status") != "ok":
        logger.error("Import failed: {}", result.get("reason"))
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
