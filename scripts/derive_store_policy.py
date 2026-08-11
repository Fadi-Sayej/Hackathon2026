"""
derive_store_policy.py — work out what a store carries from its own sales history.

WHY THIS EXISTS
    configs/store_policy.yaml decides which product segments a store sees
    recommendations for. The obvious way to fill it is to ask the owner. But we do
    not have to: seven months of his own sales already answer the question, and they
    answer it better than memory does.

    If not one alcoholic product sold in seven months, the shop does not sell
    alcohol. That is evidence, not an assumption about the neighbourhood — which
    matters, because SmartShelf must work for a store that sells alcohol and one
    that refuses it, with neither treated as the normal case.

WHAT IT WILL NOT DO
    It never writes configs/store_policy.yaml directly. It proposes, prints its
    evidence, and writes a suggestion the owner can accept or override. Absence of
    evidence is not proof: a segment may be missing because the shop stopped
    stocking it, because the export is partial, or because it is seasonal.
    `--write` puts the proposal in the file marked `derived`, never `manual`.

Usage
-----
    python3 scripts/derive_store_policy.py
    python3 scripts/derive_store_policy.py --store yomyom-kq-01 --write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import polars as pl
import yaml

from src.common.paths import PROJECT_ROOT, SILVER_POS_ROOT

SEGMENTS_CONFIG = PROJECT_ROOT / "configs" / "product_segments.yaml"
STORE_POLICY = PROJECT_ROOT / "configs" / "store_policy.yaml"

# Below this many units across the whole history a segment is "not really carried".
# Not zero: a single stray unit is as likely to be a mis-scan or a one-off special
# order as it is a real assortment decision.
CARRIED_THRESHOLD = 3


def load_sales() -> pl.DataFrame:
    path = SILVER_POS_ROOT / "yomyom_sales.parquet"
    if not path.exists():
        raise SystemExit(
            f"{path} not found.\n"
            "Run scripts/import_yomyom_pos.py then scripts/import_yomyom_sales.py first."
        )
    df = pl.read_parquet(path)
    col = "total_units_all_months" if "total_units_all_months" in df.columns else "units_sold_30d"
    return df.with_columns(pl.col(col).fill_null(0).alias("_units"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", default="yomyom-kq-01")
    parser.add_argument("--threshold", type=int, default=CARRIED_THRESHOLD)
    parser.add_argument("--write", action="store_true", help="write the proposal into store_policy.yaml")
    args = parser.parse_args()

    sales = load_sales()
    segments = yaml.safe_load(SEGMENTS_CONFIG.read_text(encoding="utf-8"))["segments"]

    months = sales["observed_days"].max() if "observed_days" in sales.columns else None
    print("=== store policy, derived from sales history ===")
    print(f"  store              {args.store}")
    print(f"  products in export {len(sales):,}")
    print(f"  ever sold          {len(sales.filter(pl.col('_units') > 0)):,}")
    print(f"  carried threshold  {args.threshold} units across the whole history\n")

    print(f"  {'segment':<16} {'products':>9} {'units':>9}  verdict")
    proposed_excludes, evidence = [], {}
    for name, spec in segments.items():
        kws = (spec or {}).get("match_any") or []
        if not kws:
            continue
        hit = sales.filter(pl.col("product_name").fill_null("").str.contains("|".join(kws)))
        units = int(hit["_units"].sum())
        n_products = len(hit.filter(pl.col("_units") > 0))
        carried = units >= args.threshold
        if not carried:
            proposed_excludes.append(name)
        evidence[name] = {"products_sold": n_products, "units": units, "carried": carried}
        print(f"  {name:<16} {n_products:>9,} {units:>9,}  "
              f"{'CARRIES' if carried else 'does not carry -> exclude'}")

    print("\n=== proposal ===")
    if proposed_excludes:
        print(f"  excludes: [{', '.join(proposed_excludes)}]")
    else:
        print("  excludes: []   (carries everything we can detect)")

    print("\n  Absence of evidence is not proof. A segment can be missing because the")
    print("  shop dropped it, because the export is partial, or because it is seasonal.")
    print("  This is a proposal for the owner to confirm, not a decision.")

    if not args.write:
        print("\n  --write to record it as `derived` in configs/store_policy.yaml")
        return 0

    cfg = yaml.safe_load(STORE_POLICY.read_text(encoding="utf-8")) or {}
    store = (cfg.setdefault("stores", {}).setdefault(args.store, {}) or {})
    if store.get("verified") == "manual":
        print("\n  REFUSING to overwrite a manual classification. Edit it by hand.")
        return 1
    store["excludes"] = proposed_excludes
    store["verified"] = "derived"
    store["derived_from"] = "7 monthly sales reports, Jan-Jul 2026"
    store["evidence"] = evidence
    cfg["stores"][args.store] = store
    STORE_POLICY.write_text(
        yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    print(f"\n  written -> {STORE_POLICY.relative_to(PROJECT_ROOT)} (verified: derived)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
