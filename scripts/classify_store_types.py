"""
classify_store_types.py — Step 3 of the store-identity track.

Counts distinct SKUs per collected source and infers a store format for any branch
that has no hand-written classification yet. Inferred entries go to
configs/store_types.inferred.yaml — a separate, machine-owned file — marked
`verified: inferred` and carrying the SKU count and confidence that produced them,
so an inferred format is never mistaken for a fact and never clobbers the
hand-edited configs/store_types.yaml.

Guarantees:
  - never overwrites an entry in the hand-written config
  - never infers from a partial scrape (see `min_skus_for_inference` in the YAML)
  - reports by default and writes nothing without --write

Usage:
    python3 scripts/classify_store_types.py            # report only
    python3 scripts/classify_store_types.py --write    # write inferred entries
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from src.common.paths import EXTERNAL_SILVER_ROOT
from src.common.store_types import INFERRED_CONFIG_PATH, UNKNOWN, load_store_types

PRODUCTS_SILVER = EXTERNAL_SILVER_ROOT / "products"

# Kaggle chain dumps are full catalogs and carry no per-branch identity, so their
# SKU count describes the chain's format. These map onto the static branch IDs in
# configs/store_types.yaml — do not invent new ones. The Kaggle importer was removed on
# 2026-09-24, so only silver data already on disk still classifies here.
CHAIN_DIR_TO_STORE_ID = {
    "kaggle_dor_alon": "dor-alon-kq-01",
    "kaggle_rami_levy": "rami-levy-pt-01",
    "kaggle_shufersal": "shufersal-pt-01",
}


def _read_products(directory: Path):
    import polars as pl

    files = sorted(directory.rglob("*.parquet"))
    frames = []
    for path in files:
        frame = pl.read_parquet(path)
        # Failed scrapes leave single-column _empty files behind.
        if len(frame.columns) > 1:
            frames.append(frame)
    if not frames:
        return None
    return pl.concat(frames, how="diagonal_relaxed")


def count_skus_by_source() -> dict[str, dict]:
    """distinct-SKU count per source, keyed by the store ID used everywhere else."""
    import polars as pl

    counts: dict[str, dict] = {}
    if not PRODUCTS_SILVER.exists():
        return counts

    for directory in sorted(p for p in PRODUCTS_SILVER.iterdir() if p.is_dir()):
        frame = _read_products(directory)
        if frame is None or "barcode" not in frame.columns:
            continue

        if directory.name in CHAIN_DIR_TO_STORE_ID:
            store_id = CHAIN_DIR_TO_STORE_ID[directory.name]
            counts[store_id] = {
                "distinct_skus": frame["barcode"].n_unique(),
                "name": directory.name,
                "sample": "full_catalog",
            }
            continue

        # Delivery catalogs carry one row per venue — count each venue separately.
        if "store_id" not in frame.columns:
            continue
        grouped = frame.group_by("store_id").agg(
            pl.col("barcode").n_unique().alias("skus"),
            pl.col("store_name").first().alias("store_name"),
            pl.col("store_chain").first().alias("store_chain"),
        )
        for row in grouped.iter_rows(named=True):
            counts[str(row["store_id"])] = {
                "distinct_skus": int(row["skus"]),
                "name": row.get("store_name"),
                "chain": row.get("store_chain"),
                "sample": "partial_scrape",
            }
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write inferred entries back to the YAML")
    args = parser.parse_args()

    config = load_store_types()
    observed = count_skus_by_source()

    if not observed:
        print("No silver product data found under %s." % PRODUCTS_SILVER)
        print("Nothing to infer. Manual classifications in the YAML are unaffected.")
        return 0

    planned: dict[str, dict] = {}
    print("%-26s %-10s %8s  %-18s %s" % ("STORE ID", "STATUS", "SKUS", "FORMAT", "NOTE"))
    for store_id, info in sorted(observed.items(), key=lambda kv: -kv[1]["distinct_skus"]):
        skus = info["distinct_skus"]
        existing = config.store(store_id)
        fmt, confidence = config.infer_store_type(skus)

        # A hand-written entry is never replaced. When the SKU count disagrees with
        # it that is worth saying out loud — it is either a mis-set format or a
        # partial catalog — but the human's answer stands until they change it.
        if existing and existing.verified in ("manual", "proposed"):
            if fmt != UNKNOWN and fmt != existing.store_type:
                note = "SKU count suggests %s — confirm on the ground" % fmt
            else:
                note = "kept — %s classification" % existing.verified
            print("%-26s %-10s %8d  %-18s %s" % (
                store_id[:26], existing.verified, skus, existing.store_type, note))
            continue

        if fmt == UNKNOWN:
            reason = (
                "sample too small to infer (<%d SKUs)" % config.min_skus_for_inference
                if skus < config.min_skus_for_inference
                else "SKU count outside every format range"
            )
            kept = existing.store_type if existing else UNKNOWN
            print("%-26s %-10s %8d  %-18s %s" % (
                store_id[:26], "skipped", skus, kept, reason))
            continue

        planned[store_id] = {
            "store_type": fmt,
            "verified": "inferred",
            "confidence": confidence,
            "distinct_skus": int(skus),
        }
        if info.get("name"):
            planned[store_id]["name"] = info["name"]
        if info.get("chain"):
            planned[store_id]["chain"] = info["chain"]
        print("%-26s %-10s %8d  %-18s confidence=%.1f" % (
            store_id[:26], "inferred", skus, fmt, confidence))

    if not planned:
        print("\nNo new inferences to write.")
        return 0

    if not args.write:
        print("\n%d entr%s would be written. Re-run with --write to apply."
              % (len(planned), "y" if len(planned) == 1 else "ies"))
        return 0

    existing_raw = {}
    if INFERRED_CONFIG_PATH.exists():
        existing_raw = yaml.safe_load(INFERRED_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    stores = existing_raw.get("stores") or {}
    stores.update(planned)

    header = (
        "# GENERATED by scripts/classify_store_types.py — do not hand-edit.\n"
        "#\n"
        "# Every entry here was inferred from a distinct-SKU count, not confirmed by\n"
        "# anyone. To correct one, add it to configs/store_types.yaml with\n"
        "# `verified: manual` — the hand-written file always wins the merge.\n\n"
    )
    INFERRED_CONFIG_PATH.write_text(
        header + yaml.safe_dump({"stores": stores}, allow_unicode=True, sort_keys=True),
        encoding="utf-8",
    )
    print("\nWrote %d inferred entr%s to %s"
          % (len(planned), "y" if len(planned) == 1 else "ies", INFERRED_CONFIG_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
