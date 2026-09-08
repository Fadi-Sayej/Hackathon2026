"""
analyse_sales_movement.py — T8 / #53, all six steps, with the limits stated.

    python3 scripts/analyse_sales_movement.py
    python3 scripts/analyse_sales_movement.py --json

Emits `configs/measured_weights.yaml` for #50 to consume, carrying `n_obs` and a
confidence band per entry so a weakly-measured effect cannot override a
hand-set default with the same authority as a well-measured one.

Read src/market/sales_movement.py before quoting anything from this. Two of the
six steps are NOT possible on monthly data, and the report says which and why
rather than quietly skipping them.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import SILVER_POS_ROOT
from src.market.sales_movement import (
    department_shares,
    estimate_effect,
    load_departments,
    load_panel,
    load_windows,
    product_velocity,
)

SALES_DIR = ROOT / "data" / "internal" / "raw_pos" / "yomyom" / "sales"
CALENDARS = ROOT / "configs" / "calendars.yaml"
OUT_WEIGHTS = ROOT / "configs" / "measured_weights.yaml"

# Departments below this share of total volume are too thin to carry a calendar
# effect worth publishing; a 0.2%-share department moves on a handful of units.
MIN_DEPARTMENT_SHARE = 0.01


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", default=str(OUT_WEIGHTS))
    args = parser.parse_args()

    departments = load_departments(SILVER_POS_ROOT / "yomyom_products.parquet")
    panel = load_panel(SALES_DIR, departments)
    if panel.empty:
        print("No sales reports found in %s" % SALES_DIR)
        return 1

    months = sorted(panel["month"].unique())
    total_units = float(panel["units"].sum())
    matched = float(panel["department"].notna().mean())

    # ---- Step 1: coverage -------------------------------------------------
    catalogue = len(departments)
    sold_barcodes = panel.loc[panel["units"] > 0, "barcode"].nunique()
    coverage = {
        "months": [str(m)[:7] for m in months],
        "product_months": int(len(panel)),
        "total_units": int(total_units),
        "distinct_barcodes_with_any_sale": int(sold_barcodes),
        "catalogue_size": catalogue,
        "catalogue_coverage_pct": round(100 * sold_barcodes / catalogue, 1) if catalogue else None,
        "rows_matched_to_department_pct": round(100 * matched, 1),
        "grain": "one row per product per calendar month; no date column exists",
    }

    # ---- Step 2: honest velocity -----------------------------------------
    velocity = product_velocity(panel)
    bands = velocity["velocity_confidence"].value_counts().to_dict()
    never_sold = catalogue - int(sold_barcodes)
    step2 = {
        "bands": {k: int(v) for k, v in bands.items()},
        "products_with_no_sales_rows": never_sold,
        "none_share_pct": round(100 * never_sold / catalogue, 1) if catalogue else None,
        "note": ("products with no rows are reported as 'none', never as zero sales — "
                 "dead, never-stocked and missed-by-export are indistinguishable here"),
    }

    # ---- Steps 3 and 5: what monthly data cannot answer -------------------
    not_possible = {
        "step_3_stl_decomposition": {
            "possible": False,
            "reason": ("STL needs at least two full seasonal cycles. Seven monthly points "
                       "cannot separate an annual cycle from a trend; fitting one anyway "
                       "produces an authoritative-looking decomposition of noise."),
            "what_would_fix_it": "a sales export with transaction or daily grain",
        },
        "step_5_weekday_and_payday": {
            "possible": False,
            "reason": ("There is no day-of-week information in any of the seven files — "
                       "no date column at all. This is NOT 'measured and found not "
                       "significant'; it is not measurable."),
            "what_would_fix_it": "a sales export with a date per transaction or per day",
        },
    }

    # ---- Step 4: calendar effects ----------------------------------------
    windows = load_windows(CALENDARS)
    calendars_config = yaml.safe_load(CALENDARS.read_text(encoding="utf-8")) or {}
    shares = department_shares(panel)
    big = {d: s for d, s in shares.items()
           if sum(s.values()) / max(len(s), 1) >= MIN_DEPARTMENT_SHARE}

    effects = []
    for window in windows:
        for dept, series in sorted(big.items()):
            effects.append(estimate_effect(series, window, dept))

    measurable = [e for e in effects if e.effect is not None]
    # Only `medium` is published. #53: "Where measurement is too weak, keep the
    # existing default and say so. A documented guess beats a badly-measured
    # number presented as fact."
    publishable = [e for e in measurable if e.confidence == "medium"]
    seen_but_weak = [e for e in measurable if e.confidence == "low"]

    record = {
        "measured_on": date.today().isoformat(),
        "issue": "#53 T8 — local market movement",
        "coverage": coverage,
        "velocity": step2,
        "not_possible": not_possible,
        "calendar_dates_verified_by": calendars_config.get("verified_by"),
        "effects": [e.to_dict() for e in effects],
    }

    write_weights(Path(args.out), record, publishable, calendars_config)

    if args.json:
        print(json.dumps(record, ensure_ascii=False, indent=2, default=str))
        return 0

    print("T8 — local market movement, from YomYom's own seven months")
    print()
    print("STEP 1  coverage")
    print("  months            : %s" % ", ".join(coverage["months"]))
    print("  product-months    : %d   units: %d" % (coverage["product_months"], coverage["total_units"]))
    print("  barcodes sold     : %d of %d catalogue (%.1f%%)"
          % (sold_barcodes, catalogue, coverage["catalogue_coverage_pct"]))
    print("  dept name matched : %.1f%% of rows" % coverage["rows_matched_to_department_pct"])
    print("  ⚠️  grain          : %s" % coverage["grain"])
    print()
    print("STEP 2  velocity confidence, counted honestly")
    for band in ("high", "medium", "low"):
        print("  %-7s : %d products" % (band, bands.get(band, 0)))
    print("  none    : %d products (%.1f%% of catalogue) — no sales rows, NOT zero sales"
          % (never_sold, step2["none_share_pct"]))
    print()
    print("STEPS 3 & 5  not possible on this data")
    for key, entry in not_possible.items():
        print("  ✗ %s" % key)
        print("      %s" % entry["reason"])
        print("      fix: %s" % entry["what_would_fix_it"])
    print()
    print("STEP 4  calendar effects on department share of monthly volume")
    if calendars_config.get("verified_by") is None:
        print("  ⚠️  configs/calendars.yaml is UNVERIFIED. Every number below is")
        print("      attached to dates nobody has confirmed. Check them first.")
    print("  departments measured: %d (>= %.0f%% share)" % (len(big), 100 * MIN_DEPARTMENT_SHARE))
    print()
    if not publishable:
        print("  Nothing measured well enough to publish as a weight.")
        print("  With seven monthly points that is an expected outcome, not a null result.")
    else:
        print("  PUBLISHED to measured_weights.yaml:")
        for e in sorted(publishable, key=lambda x: -abs((x.effect or 1) - 1)):
            print("    %-10s %-22s x%.2f  [%.2f, %.2f]  n=%d exposed=%d"
                  % (e.window, e.department[:22], e.effect, e.ci_low, e.ci_high,
                     e.n_obs, e.n_exposed))

    if seen_but_weak:
        print()
        print("  SEEN BUT NOT PUBLISHED — too weak to override a hand-set default:")
        for e in sorted(seen_but_weak, key=lambda x: -abs((x.effect or 1) - 1))[:8]:
            print("    %-10s %-22s x%.2f  [%.2f, %.2f]  %s"
                  % (e.window, e.department[:22], e.effect, e.ci_low, e.ci_high,
                     (e.reason or "")[:44]))

    inconclusive = [e for e in measurable if e.confidence == "inconclusive"]
    unmeasurable = [e for e in effects if e.effect is None]
    print()
    print("  inconclusive (interval spans 1.0) : %d of %d measurable" % (len(inconclusive), len(measurable)))
    print("  unmeasurable (window too short)   : %d" % len(unmeasurable))
    print()
    print("STEP 6  wrote %s" % args.out)
    return 0


def write_weights(path: Path, record: dict, notable, calendars_config: dict) -> None:
    """configs/measured_weights.yaml — what #50 consumes.

    Only effects whose interval excludes 1.0 are published. Where measurement is
    too weak the entry is omitted and the omission is recorded, because #53 is
    explicit that a documented guess beats a badly-measured number presented as
    fact: "Where measurement is too weak, keep the existing default and say so."
    """
    by_window: dict = {}
    for e in notable:
        # The published number is the TREND-CONTROLLED one. The uncontrolled
        # figure is kept beside it because the gap between them is the size of
        # the confound, and #50 should be able to see it.
        published = e.effect_trend_adjusted if e.effect_trend_adjusted else e.effect
        by_window.setdefault(e.window, {})[e.department] = {
            "effect": round(published, 3),
            "effect_uncontrolled": round(e.effect, 3),
            "ci_uncontrolled": [round(e.ci_low, 3), round(e.ci_high, 3)],
            "n_obs": e.n_obs,
            "n_exposed_months": e.n_exposed,
            "confidence": e.confidence,
            "survives_trend_control": e.survives_trend_control,
        }

    header = (
        "# measured_weights.yaml — GENERATED by scripts/analyse_sales_movement.py\n"
        "# Do not hand-edit; rerun the script.\n"
        "#\n"
        "# Derived from YomYom's seven monthly sales reports (T8 / #53).\n"
        "#\n"
        "# HOW TO READ `effect`\n"
        "#   A multiplier on the DEPARTMENT'S SHARE of monthly store volume, not on\n"
        "#   its unit count. Store-wide volume swings ~40%% month to month, so raw\n"
        "#   units would measure how busy the shop was rather than what the customer\n"
        "#   chose.\n"
        "#\n"
        "# HOW MUCH TO TRUST IT\n"
        "#   Every entry carries `n_obs` and `confidence`. There are SEVEN monthly\n"
        "#   observations in total and calendar windows straddle month boundaries, so\n"
        "#   no entry here can be better than `medium`. #50 must weight these by how\n"
        "#   well measured they are; an effect from 7 points should not override a\n"
        "#   hand-set default with the same authority as one from 300.\n"
        "#\n"
        "# WHAT IS DELIBERATELY ABSENT\n"
        "#   Weekday and payday cycles: not measurable. The reports carry no date\n"
        "#   column, so there is no day-of-week signal to find. Keep the existing\n"
        "#   defaults in #50 and treat them as documented guesses.\n"
        "#   Effects whose confidence interval spans 1.0 are omitted rather than\n"
        "#   published at their point estimate.\n"
        "#   Effects that vanish once a linear time trend is controlled for are\n"
        "#   omitted as `confounded`. The seven months run Jan-Jul and Ramadan\n"
        "#   falls in months 2-3, so calendar exposure is nearly collinear with\n"
        "#   seasonal drift. Beverages looked like a x0.82 Ramadan suppression and\n"
        "#   were simply rising into summer.\n"
        "#\n"
        "# ⚠️ The calendar windows in configs/calendars.yaml are %s.\n"
        % ("VERIFIED by " + str(calendars_config.get("verified_by"))
           if calendars_config.get("verified_by") else "NOT YET VERIFIED")
    )

    body = {
        "generated_on": record["measured_on"],
        "source": "YomYom monthly sales reports 2026-01..2026-07",
        "grain": record["coverage"]["grain"],
        "catalogue_coverage_pct": record["coverage"]["catalogue_coverage_pct"],
        "calendar_dates_verified_by": calendars_config.get("verified_by"),
        "calendar_effects": by_window or None,
        "not_measurable": {
            key: entry["reason"] for key, entry in record["not_possible"].items()
        },
    }
    path.write_text(header + yaml.safe_dump(body, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
