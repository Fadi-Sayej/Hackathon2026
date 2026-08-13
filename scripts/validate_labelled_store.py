"""
validate_labelled_store.py — the accuracy figure #49 Step 5 asks for.

    python3 scripts/validate_labelled_store.py
    python3 scripts/validate_labelled_store.py --json

Infers our own store's availability from OUTSIDE ONLY (delivery-catalogue
orderability), then checks it against stock we actually own. Writes
data/market/labelled_store.json.

Read src/market/labelled_store.py before quoting any number from this — in
particular the staleness of the POS ground truth, which the output states.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.market.labelled_store import (
    load_our_orderability,
    load_pos_stock,
    precision_interval,
    validate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", default=str(ROOT / "data" / "market" / "labelled_store.json"))
    args = parser.parse_args()

    orderability = load_our_orderability()
    stock, imported_at = load_pos_stock()
    result = validate(orderability, stock, pos_imported_at=imported_at)

    record = {
        "measured_on": date.today().isoformat(),
        "issue": "#49 Step 5 — validation against a store whose truth we own",
        **result.to_dict(),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))

    if args.json:
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0

    print("Labelled-store validation — YomYom, inferred from outside only")
    print()
    if not result.days:
        print("  No usable delivery-catalogue day carries our own venue.")
        print("  Check configs/delivery_targets.yaml contains yomyom_kafr_qasim")
        print("  and that the collector is reading it.")
        return 1

    print("  days observed  : %d (%s → %s)" % (len(result.days), result.days[0], result.days[-1]))
    print("  offered online : %d barcodes" % result.universe)
    print("  matched to POS : %d  (%d could not be matched)"
          % (result.matched_to_pos, result.universe - result.matched_to_pos))

    if result.staleness_days is not None:
        print()
        print("  ⚠️  GROUND TRUTH IS %d DAYS OLD (POS export %s)."
              % (result.staleness_days, str(result.pos_imported_at)[:10]))
        print("      Every stock figure below is that day's. This is an indicative")
        print("      number until a fresh POS export arrives — not a headline one.")

    if result.score is None:
        print("\n  No overlap between the online assortment and the POS catalogue.")
        return 1

    s = result.score
    print()
    print("  Rule under test: %s" % s.rule)
    print("    observations : %d  (%d in stock, %d not)"
          % (s.total, s.actual_positive, s.actual_negative))
    print("    precision    : %s" % _fmt(s.precision, precision_interval(result)))
    print("    recall       : %s" % _fmt(s.recall))
    print("    F1           : %s" % _fmt(s.f1))
    print("    accuracy     : %s" % _fmt(s.accuracy))

    if result.predicts_everything:
        print()
        print("  ⚠️  NOT YET A TEST OF INFERENCE. With %d day(s) of our own venue the"
              % len(result.days))
        print("      universe IS that day's orderable set, so the rule called every")
        print("      product orderable and could not be wrong in the negative")
        print("      direction. Read the precision above as assortment overlap:")
        print("      %d of %d products offered online had stock. A second day lets"
              % (s.true_positive, s.total))
        print("      products drop off, and the number starts meaning something.")

    print()
    print("  Emission probabilities (what #49 Step 3 needs, measured not guessed):")
    print("    P(orderable | in stock)     = %s" % _fmt(result.emission_orderable_given_in_stock))
    print("    P(orderable | out of stock) = %s" % _fmt(result.emission_orderable_given_out_of_stock))
    if result.predicts_everything:
        print("    ⚠️  Both collapse to 1.0 by construction here — see above. They are")
        print("        placeholders in the record, not values to feed a model.")
    elif not s.has_negative_class:
        print("    ⚠️  Nothing in the universe was out of stock, so the second number")
        print("        is undefined rather than low. It needs a fresh export.")

    print()
    print("recorded to %s" % out_path)
    return 0


def _fmt(value, interval=None) -> str:
    if value is None:
        return "n/a"
    if interval:
        return "%.3f  [%.3f, %.3f]" % (value, interval[0], interval[1])
    return "%.3f" % value


if __name__ == "__main__":
    raise SystemExit(main())
