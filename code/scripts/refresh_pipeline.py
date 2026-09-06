"""
refresh_pipeline.py — one command to refresh every dashboard input.

Chains the whole internal pipeline so the team runs ONE command after a new POS
export or a fresh scrape, instead of remembering five scripts in the right order:

  1. (optional) Import a POS CSV          --input <path>
  2. Build the expiry report               (safe with zero scans)
  3. Generate operational recommendations  (done inside the exporter)
  4. Export dashboard JSON                  public/data/operational.json + sources.json

Every step is best-effort: a failure in one step is reported but does not abort the
rest, so a partial refresh still updates what it can while scraping is in progress.

Usage:
  python scripts/refresh_pipeline.py
  python scripts/refresh_pipeline.py --input data/internal/raw_pos/yomyom/all4shop_Mlai.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _step(name: str, fn) -> dict:
    try:
        result = fn()
        return {"step": name, "status": "ok", "result": result}
    except Exception as exc:  # noqa: BLE001 — surface, don't abort the pipeline
        return {"step": name, "status": "error", "error": f"{type(exc).__name__}: {exc}"}


def run(input_csv: str | None) -> dict:
    steps: list[dict] = []

    if input_csv:
        from src.internal_pos.pos_importer import import_pos_file

        steps.append(_step("pos_import", lambda: import_pos_file(Path(input_csv))))

    from src.expiry.expiry_tracking import build_expiry_report

    steps.append(_step("expiry_report", lambda: build_expiry_report()))

    # The exporter regenerates operational recommendations and refreshes sources.json.
    from scripts.export_dashboard_data import export

    steps.append(_step("dashboard_export", export))

    overall = "ok" if all(s["status"] == "ok" for s in steps) else "partial"
    return {"status": overall, "steps": steps}


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh all dashboard inputs in one run.")
    parser.add_argument("--input", default=None, help="Optional POS CSV to import first.")
    args = parser.parse_args()

    summary = run(args.input)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
