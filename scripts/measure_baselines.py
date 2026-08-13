"""
measure_baselines.py — score the naive rules before any model (T4 / #49, Step 2).

    python3 scripts/measure_baselines.py
    python3 scripts/measure_baselines.py --json

Writes data/market/baselines.json so the numbers are *recorded*, which is what
the acceptance criterion asks for: "Naive baselines measured and recorded before
any model." A model that cannot beat these by +0.15 F1 is not worth its weight.

    N1  "listed in the catalogue ⇒ available"   labelled by YomYom's real stock
    N2  "present in today's price file ⇒ available"  labelled by Wolt orderability

See src/market/baseline.py for why these are two rules and not one.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import EXTERNAL_SNAPSHOTS_ROOT, SILVER_POS_ROOT
from src.market.baseline import Score, score_membership_rule

# Venues that can be scored at all: those declaring `price_file_store_id` in
# configs/delivery_targets.yaml, i.e. present in BOTH the delivery catalogue and
# the price file. Today that is one — "Super Alonit | Kibbutz Einat" <-> branch
# 657 ("עינת").
#
# The identification rests on the name match. Barcode overlap corroborates but
# does not prove it: 657 shares 239 of the venue's 273 barcodes, and the next
# two branches share 236 and 226, which is what any three branches of one chain
# would look like. If the mapping is wrong, N2 measures the wrong store — which
# is why it is declared in config rather than inferred by a join.
DELIVERY_TARGETS_PATH = ROOT / "configs" / "delivery_targets.yaml"


def venue_to_price_store() -> dict[str, str]:
    """{wolt store_name -> price-file store_id} for targets that declare one.

    Keyed on the venue's Wolt display name because that is what lands in the
    silver `store_name` column. Falls back to matching on the URL slug so a
    display-name change does not silently empty the mapping.
    """
    config = yaml.safe_load(DELIVERY_TARGETS_PATH.read_text(encoding="utf-8")) or {}
    return {
        t["url"].rstrip("/").rsplit("/", 1)[-1]: str(t["price_file_store_id"])
        for t in (config.get("targets") or [])
        if isinstance(t, dict) and t.get("price_file_store_id") and t.get("url")
        and t.get("enabled", True)
    }


def _read_day(day_dir: Path, source: str, columns):
    """Silver parquet for one source on one day, or None if that day is unusable."""
    manifest = day_dir / "_manifest.json"
    if not manifest.exists():
        return None
    status = json.loads(manifest.read_text()).get("sources", {}).get(source, {}).get("status")
    if status not in ("ok", "partial"):
        return None
    pattern = str(day_dir / source / "*" / "*_silver.parquet")
    files = sorted(glob.glob(pattern))
    frames = []
    for path in files:
        try:
            frames.append(pd.read_parquet(path, columns=columns))
        except Exception:
            # A venue that returned no products writes a schema-less file. It is
            # an absence of data, not a corrupt day — skip it and keep the rest,
            # rather than losing eight good venues to one empty one.
            continue
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def measure_n1() -> dict:
    """N1 — catalogue membership, labelled by YomYom's own stock.

    Every product in the item master is 'predicted available' by this rule, so it
    has no true negatives by construction. That is the point: it is the rule a
    system falls into by default when it treats a catalogue as a shelf.
    """
    inv = pd.read_parquet(SILVER_POS_ROOT / "yomyom_inventory.parquet",
                          columns=["barcode", "product_name", "current_stock"])
    stock = pd.to_numeric(inv["current_stock"], errors="coerce")
    inv = inv.assign(stock=stock).dropna(subset=["stock"])

    # Key on barcode where present, else product name — ~300 rows carry no barcode
    # and dropping them would quietly shrink the denominator.
    key = inv["barcode"].astype(str).where(
        inv["barcode"].notna() & (inv["barcode"].astype(str).str.strip() != ""),
        "name:" + inv["product_name"].astype(str),
    )
    inv = inv.assign(key=key).drop_duplicates(subset=["key"])

    # 625 rows read negative. That is a POS artefact (sold without a receiving
    # entry), not evidence the shelf is empty, so they are excluded from the
    # headline. Excluding them makes the baseline STRONGER, which is the
    # conservative choice: a later model has to beat the best honest version.
    primary = inv[inv["stock"] >= 0]
    universe = set(primary["key"])
    available = set(primary.loc[primary["stock"] > 0, "key"])
    score = score_membership_rule(
        universe=universe,
        predicted_present=universe,          # the rule: in the catalogue ⇒ available
        actually_available=available,
        rule="N1: listed in the catalogue ⇒ available",
        label_source="YomYom POS current_stock > 0",
    )

    # Sensitivity: count negative stock as unavailable instead of excluding it.
    all_universe = set(inv["key"])
    all_available = set(inv.loc[inv["stock"] > 0, "key"])
    sensitivity = score_membership_rule(
        universe=all_universe,
        predicted_present=all_universe,
        actually_available=all_available,
        rule="N1 (negative stock counted as unavailable)",
        label_source="YomYom POS current_stock > 0",
    )

    out = score.to_dict()
    out["excluded_negative_stock_rows"] = len(inv) - len(primary)
    out["sensitivity_negative_as_unavailable"] = sensitivity.to_dict()
    return out


def measure_n2() -> dict:
    """N2 — today's price file, labelled by today's delivery-catalogue orderability.

    The universe is the set of barcodes the venue has EVER been seen to deliver,
    MINUS those that appear nowhere in the chain's price file on any collected day.

    Both restrictions are load-bearing. Scoring over the branch's full 7,534-SKU
    price file would make absence from Wolt read as a stockout for thousands of
    products that were never orderable. And the delivery catalogue carries SKUs
    the price file cannot contain — 28 of this venue's 278 barcodes are Wolt
    multipack bundles ("2 יחידות | …") with synthetic codes that appear at no
    branch of the chain. A price-file rule cannot predict those, so counting them
    as its mistakes measures the catalogue's SKU scheme, not the rule.

    The 6 barcodes that DO appear elsewhere in the chain but not at this branch
    are kept: those are real disagreements between the two sources.
    """
    days = sorted(p for p in EXTERNAL_SNAPSHOTS_ROOT.glob("*") if p.is_dir())
    per_day = []
    universe: set[str] = set()
    chain_wide: set[str] = set()
    wolt_by_day: dict[str, set[str]] = {}
    price_by_day: dict[str, set[str]] = {}

    for day_dir in days:
        wolt = _read_day(day_dir, "delivery_catalog", ["barcode", "store_name"])
        price = _read_day(day_dir, "price_transparency", ["barcode", "store_id"])
        if wolt is None or price is None:
            continue
        # Silver carries store_name, not the URL slug, so match on a normalised
        # form of both: "Super Alonit | Kibbutz Einat" -> super-alonit-kibbutz-einat.
        def slug(name: str) -> str:
            return "-".join("".join(
                c.lower() if c.isalnum() else " " for c in str(name)
            ).split())

        mapping = venue_to_price_store()
        wolt = wolt[wolt["store_name"].map(lambda n: slug(n) in mapping)]
        if wolt.empty:
            continue
        chain_wide |= set(price["barcode"].dropna().astype(str))
        store_ids = {mapping[slug(v)] for v in wolt["store_name"].unique()}
        price = price[price["store_id"].astype(str).isin(store_ids)]

        w = set(wolt["barcode"].dropna().astype(str))
        p = set(price["barcode"].dropna().astype(str))
        wolt_by_day[day_dir.name] = w
        price_by_day[day_dir.name] = p
        universe |= w

    delivered = len(universe)
    universe &= chain_wide
    out_of_universe = delivered - len(universe)

    if not wolt_by_day:
        return {"usable_days": 0, "note": "no day carries both sources for a mapped venue"}

    total = Score(
        rule="N2: present in today's price file ⇒ available",
        label_source="delivery-catalogue orderability (venues declaring price_file_store_id)",
        true_positive=0, false_positive=0, true_negative=0, false_negative=0,
    )
    for day, w in sorted(wolt_by_day.items()):
        s = score_membership_rule(
            universe=universe,
            predicted_present=price_by_day[day],
            actually_available=w,
            rule=total.rule,
            label_source=total.label_source,
        )
        per_day.append({"day": day, **s.to_dict()})
        total.true_positive += s.true_positive
        total.false_positive += s.false_positive
        total.true_negative += s.true_negative
        total.false_negative += s.false_negative

    # N0 — the degenerate comparator: predict AVAILABLE for everything, always.
    # If the price-file rule cannot beat this, then on this data it IS this rule
    # plus noise, and any model must be measured against N0 rather than N2.
    constant = Score(
        rule="N0: always available (degenerate comparator)",
        label_source=total.label_source,
        true_positive=total.actual_positive,
        false_positive=total.actual_negative,
        true_negative=0,
        false_negative=0,
    )

    out = total.to_dict()
    out["constant_available_comparator"] = constant.to_dict()
    out["beats_constant"] = (
        total.f1 is not None and constant.f1 is not None and total.f1 > constant.f1
    )
    out["unavailability_events_caught"] = total.true_negative
    out["usable_days"] = len(wolt_by_day)
    out["universe_size"] = len(universe)
    out["delivered_barcodes"] = delivered
    out["excluded_not_in_any_price_file"] = out_of_universe
    out["per_day"] = per_day
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", default=str(ROOT / "data" / "market" / "baselines.json"))
    args = parser.parse_args()

    record = {
        "measured_on": date.today().isoformat(),
        "issue": "#49 Step 2 — baselines measured before any model",
        "n1": measure_n1(),
        "n2": measure_n2(),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2))

    if args.json:
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0

    n1 = record["n1"]
    print("Naive baselines — the numbers every later model must beat (#49 Step 2)")
    print()
    print("N1  %s" % n1["rule"])
    print("    labelled by : %s" % n1["label_source"])
    print("    products    : %d  (%d available, %d not)"
          % (n1["total"], n1["actual_positive"], n1["actual_negative"]))
    lo, hi = n1["precision_interval"]
    print("    precision   : %.3f  [%.3f, %.3f]   <- calls %d products available that are not"
          % (n1["precision"], lo, hi, n1["false_positive"]))
    print("    recall      : %.3f" % n1["recall"])
    print("    F1          : %.3f   ** the number to beat by +0.15 **" % n1["f1"])
    print("    wrong       : %.1f%% of the time" % (100 * (1 - n1["precision"])))
    sens = n1["sensitivity_negative_as_unavailable"]
    print("    sensitivity : F1 %.3f if the %d negative-stock rows count as unavailable"
          % (sens["f1"], n1["excluded_negative_stock_rows"]))
    print()

    n2 = record["n2"]
    print("N2  %s" % n2.get("rule", "(not measurable yet)"))
    if n2.get("usable_days", 0) == 0:
        print("    %s" % n2.get("note"))
    else:
        print("    labelled by : %s" % n2["label_source"])
        print("    days        : %d, universe %d barcodes, %d observations"
              % (n2["usable_days"], n2["universe_size"], n2["total"]))
        print("    excluded    : %d of %d delivered barcodes appear in no price file"
              % (n2["excluded_not_in_any_price_file"], n2["delivered_barcodes"]))
        if not n2["has_negative_class"]:
            print("    ⚠️  NOT YET A RESULT: nothing in the universe was unavailable on any")
            print("        collected day, so precision is 1.0 by construction. This needs")
            print("        elapsed time, not effort — see #46. Harness is in place.")
        else:
            lo, hi = n2["precision_interval"]
            print("    precision   : %.3f  [%.3f, %.3f] over %d predictions"
                  % (n2["precision"], lo, hi, n2["predicted_positive"]))
            print("    recall      : %.3f" % n2["recall"])
            print("    F1          : %.3f" % n2["f1"])
            if n2["false_positive_rate"] is not None:
                print("    lingering   : %.1f%% of unavailable products were still in the price file"
                      % (100 * n2["false_positive_rate"]))
            c = n2["constant_available_comparator"]
            print("    vs N0       : always-available scores F1 %.3f" % c["f1"])
            if not n2["beats_constant"]:
                print("    ⚠️  THE PRICE-FILE RULE LOSES TO A CONSTANT. It caught %d of %d"
                      % (n2["unavailability_events_caught"], n2["actual_negative"]))
                print("        unavailability events. Judge models against N0 (%.3f), not N2."
                      % c["f1"])
    print()
    print("recorded to %s" % out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
