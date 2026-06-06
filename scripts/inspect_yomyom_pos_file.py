from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.internal_pos.pos_importer import CONFIG_PATH
from src.internal_pos.pos_normalizer import inspect_pos_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a YomYom POS CSV before import.")
    parser.add_argument("--input", required=True, type=Path, help="Path to the POS CSV file.")
    parser.add_argument("--config", default=CONFIG_PATH, type=Path, help="Schema mapping YAML.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1
    if not args.config.exists():
        print(f"Config file not found: {args.config}", file=sys.stderr)
        return 1

    report = inspect_pos_file(args.input, args.config)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

