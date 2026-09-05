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


def _inner_degraded(step: dict) -> bool:
    """A step that raised nothing but did no work.

    generate_product_recommendations() returns {"status": "readiness_only"} when its
    inputs are missing. That is not an exception, so the old code recorded it as "ok"
    and the run reported success while producing nothing. Anything whose own result
    reports a status other than "ok" is surfaced instead of hidden.
    """
    result = step.get("result")
    return isinstance(result, dict) and result.get("status") not in (None, "ok")


def _step(name: str, fn) -> dict:
    try:
        result = fn()
        return {"step": name, "status": "ok", "result": result}
    except Exception as exc:  # noqa: BLE001 — surface, don't abort the pipeline
        return {"step": name, "status": "error", "error": f"{type(exc).__name__}: {exc}"}


def run(input_csv: str | None, skip_market: bool = False) -> dict:
    steps: list[dict] = []

    if input_csv:
        from src.internal_pos.pos_importer import import_pos_file

        steps.append(_step("pos_import", lambda: import_pos_file(Path(input_csv))))

    # MARKET CHAIN. Until 2026-09-05 these three ran only by hand, so nothing ever
    # wrote data/signals/competitor_product_signals/ or
    # data/recommendations/product_recommendations/. The exporter globs both
    # directories, found nothing, and shipped "competitorSignals: 0" every time —
    # the market half of the product was absent from the dashboard, silently,
    # because a missing directory is not an exception.
    #
    # Order is a hard dependency chain: signals feed matching, matching feeds
    # recommendations. Running them out of order yields "readiness_only".
    if not skip_market:
        # silver/ is gitignored while the snapshots that contain the same files are
        # committed, so on a fresh clone or in CI the signal builder reads a silver
        # tree months out of date. Rebuild it from the snapshots first.
        from scripts.rehydrate_silver import rehydrate

        steps.append(_step("rehydrate_silver", rehydrate))

        from src.signals.competitor_product_signals import build_competitor_product_signals

        steps.append(_step("competitor_signals", build_competitor_product_signals))

        from src.matching.product_matching import run_product_matching

        steps.append(_step("product_matching", run_product_matching))

        from src.recommendations.product_recommendations import generate_product_recommendations

        steps.append(_step("product_recommendations", generate_product_recommendations))

    # Fetch weather and both calendars once, and commit the result. Previously the
    # browser fetched these at render time, so the recommender could not see them
    # and two page loads could disagree about the same day.
    from src.context.build import write_market_context

    steps.append(_step("market_context", write_market_context))

    from src.expiry.expiry_tracking import build_expiry_report

    steps.append(_step("expiry_report", lambda: build_expiry_report()))

    # The exporter regenerates operational recommendations and refreshes sources.json.
    from scripts.export_dashboard_data import export

    # A POS-only refresh legitimately has no competitor recommendations; any other
    # run with none is the seam failing again, and must not publish silently.
    steps.append(_step("dashboard_export", lambda: export(allow_no_competitor=skip_market)))

    overall = "ok" if all(s["status"] == "ok" for s in steps) else "partial"
    degraded = [s["step"] for s in steps if s["status"] == "ok" and _inner_degraded(s)]
    if degraded and overall == "ok":
        overall = "degraded"
    return {"status": overall, "steps": steps, "degraded_steps": degraded}


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh all dashboard inputs in one run.")
    parser.add_argument("--input", default=None, help="Optional POS CSV to import first.")
    parser.add_argument(
        "--skip-market",
        action="store_true",
        help="Skip the competitor signal/matching/recommendation chain (POS-only refresh).",
    )
    args = parser.parse_args()

    summary = run(args.input, skip_market=args.skip_market)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
