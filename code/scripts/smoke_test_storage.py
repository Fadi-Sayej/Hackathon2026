"""
smoke_test_storage.py — end-to-end smoke test of the storage layer.

Simulates a single collector run without any real network calls:
  1. Builds a fake JSON HTTP response.
  2. Saves it via save_raw_response().
  3. Writes a bronze Parquet file via write_bronze_parquet().
  4. Writes a silver Parquet file via write_silver_parquet().
  5. Generates a quality report via generate_basic_quality_report().
  6. Reads back the metadata JSON and the quality report and prints them.

Run with:
    python scripts/smoke_test_storage.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the project root is on sys.path so `from src.common...` works.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from loguru import logger

# ── configure loguru to look nice on the terminal ─────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
)

from src.common.parquet_writer import write_bronze_parquet, write_silver_parquet
from src.common.quality import generate_basic_quality_report
from src.common.raw_storage import save_raw_response

# ── Constants ──────────────────────────────────────────────────────────────────
SOURCE_ID = "smoke_test"
OBSERVED_AT = datetime(2025, 5, 25, 14, 0, 0, tzinfo=timezone.utc)

# ── Fake data ──────────────────────────────────────────────────────────────────

FAKE_PRODUCTS = [
    {
        "barcode": "7290000000001",
        "product_name": "Tnuva Full-Fat Milk 3% 1L",
        "category": "dairy",
        "price": 6.90,
        "store_id": "wolt_kafr_qasim_001",
        "store_name": "YomYom",
    },
    {
        "barcode": "7290000000002",
        "product_name": "Elite Instant Coffee 200g",
        "category": "beverages",
        "price": 24.50,
        "store_id": "wolt_kafr_qasim_001",
        "store_name": "YomYom",
    },
    {
        "barcode": None,            # intentional missing barcode
        "product_name": "Mystery Snack",
        "category": "snacks",
        "price": None,              # intentional missing price
        "store_id": "wolt_kafr_qasim_001",
        "store_name": "YomYom",
    },
    {
        "barcode": "7290000000001", # duplicate of first
        "product_name": "Tnuva Full-Fat Milk 3% 1L",
        "category": "dairy",
        "price": 6.90,
        "store_id": "wolt_kafr_qasim_001",
        "store_name": "YomYom",
    },
]

FAKE_BODY = json.dumps(
    {"source": SOURCE_ID, "products": FAKE_PRODUCTS},
    ensure_ascii=False,
    indent=2,
).encode("utf-8")

FAKE_HEADERS = {
    "Content-Type": "application/json",
    "X-Request-Id": "smoke-test-001",
}


# ── Runner ─────────────────────────────────────────────────────────────────────

def run() -> None:
    separator = "─" * 60

    logger.info(separator)
    logger.info("YomYom Storage Layer — Smoke Test")
    logger.info(separator)

    # 1. Save raw response ─────────────────────────────────────────────────────
    logger.info("[1/4] Saving fake raw HTTP response …")
    data_path, meta_path = save_raw_response(
        source_id=SOURCE_ID,
        url="https://fake-wolt-api.local/venues/yomyom/products",
        method="GET",
        status_code=200,
        headers=FAKE_HEADERS,
        body=FAKE_BODY,
        content_type="application/json",
        observed_at=OBSERVED_AT,
    )
    logger.success("  raw data     → {}", data_path)
    logger.success("  raw metadata → {}", meta_path)

    # 2. Write bronze Parquet ──────────────────────────────────────────────────
    logger.info("[2/4] Writing bronze Parquet …")
    bronze_path = write_bronze_parquet(FAKE_PRODUCTS, SOURCE_ID, OBSERVED_AT)
    logger.success("  bronze parquet → {}", bronze_path)

    # 3. Write silver Parquet ──────────────────────────────────────────────────
    logger.info("[3/4] Writing silver Parquet …")
    silver_path = write_silver_parquet(
        FAKE_PRODUCTS, "products", OBSERVED_AT, source_id=SOURCE_ID
    )
    logger.success("  silver parquet → {}", silver_path)

    # 4. Quality report ────────────────────────────────────────────────────────
    logger.info("[4/4] Generating quality report …")
    report_path = generate_basic_quality_report(
        FAKE_PRODUCTS, SOURCE_ID, OBSERVED_AT
    )
    logger.success("  quality report → {}", report_path)

    # ── Summary ───────────────────────────────────────────────────────────────
    logger.info(separator)
    logger.info("Smoke test completed.  Written files:")
    for label, path in [
        ("Raw data      ", data_path),
        ("Raw metadata  ", meta_path),
        ("Bronze parquet", bronze_path),
        ("Silver parquet", silver_path),
        ("Quality report", report_path),
    ]:
        exists_mark = "✔" if path.exists() else "✘ MISSING"
        logger.info("  [{}] {} → {}", exists_mark, label, path)

    # ── Print quality report content ──────────────────────────────────────────
    logger.info(separator)
    logger.info("Quality report contents:")
    print(report_path.read_text(encoding="utf-8"))

    # ── Print metadata content ────────────────────────────────────────────────
    logger.info(separator)
    logger.info("Raw metadata contents:")
    print(meta_path.read_text(encoding="utf-8"))

    logger.info(separator)
    logger.success("All assertions passed — storage layer is healthy.")


if __name__ == "__main__":
    run()
