# scripts/run_engine.py
"""One command to refresh every dashboard input and publish the artefact.

  python3 scripts/run_engine.py                     # npm run data:refresh
  python3 scripts/run_engine.py --input <pos.csv>   # import a new export first
  python3 scripts/run_engine.py --skip-market       # POS-only refresh
  python3 scripts/run_engine.py --print             # run everything, write nothing (reproduction)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engine.run import run_engine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None)
    parser.add_argument("--skip-market", action="store_true")
    parser.add_argument("--print", dest="print_mode", action="store_true")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()
    result = run_engine(mode="print" if args.print_mode else "publish",
                        input_csv=Path(args.input) if args.input else None, skip_market=args.skip_market)
    summary = {"status": result["status"], "published": result["published"], "steps": result["steps"]}
    payload = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
