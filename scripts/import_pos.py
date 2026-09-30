"""import_pos.py — the store's POS inventory export → silver tables.

The export is configs/store.yaml's `pos.export` (ADR-036). `--input` imports another file,
for inspecting one; the nightly never passes it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.store import get_store
from src.internal_pos.pos_importer import CONFIG_PATH, import_pos_file


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import the store's POS export into silver parquet outputs.")
    parser.add_argument("--input", default=None, type=Path,
                        help="The POS CSV file (default: configs/store.yaml's pos.export).")
    parser.add_argument("--config", default=CONFIG_PATH, type=Path, help="Schema mapping YAML.")
    parser.add_argument("--imported-at", default=None, help="Optional ISO timestamp override.")
    parser.add_argument("--as-of", default=None, help="YYYY-MM-DD the export was taken (default: file mtime)")
    args = parser.parse_args(argv)
    args.input = args.input or get_store().pos_export
    return args


def main() -> int:
    args = parse_args()
    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1
    if not args.config.exists():
        print(f"Config file not found: {args.config}", file=sys.stderr)
        return 1

    result = import_pos_file(args.input, args.config, imported_at=args.imported_at, as_of=args.as_of)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ok", "not_ready"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

