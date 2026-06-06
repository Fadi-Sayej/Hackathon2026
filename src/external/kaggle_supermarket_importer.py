"""
kaggle_supermarket_importer.py — import Israeli supermarket price data from the
Kaggle dataset (erlichsefi/israeli-supermarkets-2024) into bronze + silver layers.

Each chain's price CSV is read in chunks, joined with its store file for city/name
metadata, mapped to ExternalProductObservation, then written to Parquet.

Supported chains: dor_alon, rami_levy, shufersal (add more via CHAIN_CONFIG).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.parquet_writer import write_bronze_parquet, write_silver_parquet
from src.common.quality import generate_basic_quality_report
from src.common.schema import ExternalProductObservation

KAGGLE_RAW_DIR = _ROOT / "data" / "raw" / "kaggle" / "israeli-supermarkets-2024"
CHUNK_SIZE = 50_000

# ── Chain registry ─────────────────────────────────────────────────────────────

CHAIN_CONFIG: dict[str, dict] = {
    "dor_alon": {
        "price_file": "price_full_file_dor_alon.csv",
        "store_file": "store_file_dor_alon.csv",
        "chain_name": "Dor Alon",
        "source_id": "kaggle_dor_alon",
    },
    "rami_levy": {
        "price_file": "price_full_file_rami_levy.csv",
        "store_file": "store_file_rami_levy.csv",
        "chain_name": "Rami Levy",
        "source_id": "kaggle_rami_levy",
    },
    "shufersal": {
        "price_file": "price_full_file_shufersal.csv",
        "store_file": "store_file_shufersal.csv",
        "chain_name": "Shufersal",
        "source_id": "kaggle_shufersal",
    },
}


@dataclass
class ImportResult:
    chain: str
    source_id: str
    status: str
    total_rows: int
    observations: int
    bronze_path: Optional[str]
    silver_path: Optional[str]
    quality_path: Optional[str]
    errors: list[str] = field(default_factory=list)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean_str(value) -> Optional[str]:
    if pd.isna(value):
        return None
    s = str(value).strip().strip("'\"")
    return s if s and s.lower() not in ("nan", "none", "") else None


def _to_decimal(value) -> Optional[Decimal]:
    if pd.isna(value):
        return None
    try:
        d = Decimal(str(value))
        return d if d > 0 else None
    except InvalidOperation:
        return None


def _parse_datetime(value) -> Optional[datetime]:
    if pd.isna(value):
        return None
    s = _clean_str(value)
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _build_unit(row: pd.Series) -> Optional[str]:
    qty = _clean_str(row.get("quantity"))
    unit_qty = _clean_str(row.get("unitqty"))
    if qty and unit_qty:
        try:
            qty_num = float(qty)
            return f"{int(qty_num) if qty_num == int(qty_num) else qty_num} {unit_qty}"
        except (ValueError, TypeError):
            pass
    return _clean_str(row.get("unitofmeasure"))


def _load_store_lookup(store_file: Path, chain_name: str) -> dict[str, dict]:
    if not store_file.exists():
        logger.warning("Store file not found: {}", store_file)
        return {}
    df = pd.read_csv(store_file, dtype=str)
    lookup: dict[str, dict] = {}
    for _, row in df.iterrows():
        store_id = _clean_str(row.get("storeid"))
        if not store_id:
            continue
        # normalise store_id to int string (remove ".0")
        try:
            store_id = str(int(float(store_id)))
        except (ValueError, TypeError):
            pass
        lookup[store_id] = {
            "store_name": _clean_str(row.get("storename")),
            "city": _clean_str(row.get("city")),
            "address": _clean_str(row.get("address")),
            "chain_name": _clean_str(row.get("chainname")) or chain_name,
            "subchain_name": _clean_str(row.get("subchainname")),
        }
    logger.info("Loaded {} store entries from {}", len(lookup), store_file.name)
    return lookup


def _row_to_observation(
    row: pd.Series,
    *,
    source_id: str,
    store_lookup: dict[str, dict],
    fallback_chain: str,
    observed_at: datetime,
) -> Optional[dict]:
    barcode = _clean_str(row.get("itemcode"))
    if not barcode:
        return None
    try:
        barcode = str(int(float(barcode)))
    except (ValueError, TypeError):
        pass

    product_name = _clean_str(row.get("itemname"))
    if not product_name:
        return None

    price = _to_decimal(row.get("itemprice"))

    raw_store_id = row.get("storeid")
    try:
        store_id = str(int(float(raw_store_id))) if pd.notna(raw_store_id) else None
    except (ValueError, TypeError):
        store_id = _clean_str(raw_store_id)

    store_meta = store_lookup.get(store_id, {}) if store_id else {}

    brand = _clean_str(row.get("manufacturename")) or _clean_str(row.get("manufacturername"))

    item_observed_at = (
        _parse_datetime(row.get("priceupdatetime"))
        or _parse_datetime(row.get("priceupdatedate"))
        or observed_at
    )

    obs = ExternalProductObservation(
        source_id=source_id,
        observed_at=item_observed_at,
        barcode=barcode,
        product_name=product_name,
        brand=brand,
        unit=_build_unit(row),
        price=price,
        price_per_unit=_to_decimal(row.get("unitofmeasureprice")),
        currency="ILS",
        store_id=store_id,
        store_name=store_meta.get("store_name"),
        store_chain=store_meta.get("chain_name") or fallback_chain,
        city=store_meta.get("city"),
        source_type="price_file",
        appears_in_price_file=True,
        is_online_available=None,
        is_in_catalog=True,
    )
    return obs.model_dump(mode="json")


# ── Core import function ────────────────────────────────────────────────────────

def import_chain(chain_key: str, *, observed_at: Optional[datetime] = None) -> ImportResult:
    config = CHAIN_CONFIG.get(chain_key)
    if not config:
        raise ValueError(f"Unknown chain: {chain_key}. Available: {list(CHAIN_CONFIG)}")

    observed_at = observed_at or datetime.now(timezone.utc)
    source_id: str = config["source_id"]
    chain_name: str = config["chain_name"]

    price_path = KAGGLE_RAW_DIR / config["price_file"]
    store_path = KAGGLE_RAW_DIR / config["store_file"]

    if not price_path.exists():
        return ImportResult(
            chain=chain_key, source_id=source_id, status="missing_file",
            total_rows=0, observations=0,
            bronze_path=None, silver_path=None, quality_path=None,
            errors=[f"Price file not found: {price_path}"],
        )

    store_lookup = _load_store_lookup(store_path, chain_name)

    all_silver: list[dict] = []
    all_bronze: list[dict] = []
    total_rows = 0
    seen: set[tuple[str, str]] = set()

    logger.info("Importing {} ({})...", chain_name, price_path.name)

    for chunk in pd.read_csv(price_path, chunksize=CHUNK_SIZE, dtype=str, low_memory=False):
        total_rows += len(chunk)

        for _, row in chunk.iterrows():
            obs = _row_to_observation(
                row,
                source_id=source_id,
                store_lookup=store_lookup,
                fallback_chain=chain_name,
                observed_at=observed_at,
            )
            if obs is None:
                continue

            dedup_key = (obs["store_id"] or "", obs["barcode"] or "")
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            all_silver.append(obs)
            all_bronze.append({
                "chain": chain_key,
                "source_id": source_id,
                **{
                    k: (None if pd.isna(v) else v)
                    for k in [
                        "chainid", "storeid", "itemcode", "itemname",
                        "itemprice", "unitofmeasureprice", "priceupdatetime",
                        "priceupdatedate", "manufacturename", "manufacturername",
                        "unitqty", "quantity", "unitofmeasure", "itemstatus",
                    ]
                    if (v := row.get(k)) is not None
                },
            })

        logger.debug(
            "{}: processed {:,} rows so far, {:,} observations",
            chain_name, total_rows, len(all_silver),
        )

    if not all_silver:
        return ImportResult(
            chain=chain_key, source_id=source_id, status="empty",
            total_rows=total_rows, observations=0,
            bronze_path=None, silver_path=None, quality_path=None,
            errors=["No valid observations after parsing"],
        )

    logger.info("{}: writing {:,} observations to Parquet...", chain_name, len(all_silver))

    bronze_path = write_bronze_parquet(all_bronze, source_id, observed_at)
    silver_path = write_silver_parquet(all_silver, "products", observed_at, source_id=source_id)
    quality_path = generate_basic_quality_report(all_silver, source_id, observed_at)

    logger.info(
        "{}: done. {:,} rows → {:,} unique observations. Bronze: {} Silver: {}",
        chain_name, total_rows, len(all_silver), bronze_path.name, silver_path.name,
    )

    return ImportResult(
        chain=chain_key,
        source_id=source_id,
        status="ok",
        total_rows=total_rows,
        observations=len(all_silver),
        bronze_path=str(bronze_path),
        silver_path=str(silver_path),
        quality_path=str(quality_path),
    )
