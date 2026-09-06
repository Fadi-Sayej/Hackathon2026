"""
download_kaggle_datasets.py — download configured Kaggle datasets into data/raw/kaggle/.

Reads KAGGLE_API_TOKEN from .env (or the environment).
Uses the Kaggle HTTP API directly with a Bearer token — no kaggle CLI needed.
Downloaded files are unzipped in place. Already-downloaded files are skipped
unless --force is passed.

Usage
-----
    python scripts/download_kaggle_datasets.py
    python scripts/download_kaggle_datasets.py --force
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path

from loguru import logger

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

import httpx


# ── Dataset registry ──────────────────────────────────────────────────────────

DATASETS = [
    {
        "owner": "erlichsefi",
        "name": "israeli-supermarkets-2024",
        "description": "Israeli supermarket prices 2024 (price-transparency aggregation)",
        "dest": _ROOT / "data" / "raw" / "kaggle" / "israeli-supermarkets-2024",
    },
]

KAGGLE_API_BASE = "https://www.kaggle.com/api/v1"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _token() -> str:
    token = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    if not token:
        logger.error(
            "KAGGLE_API_TOKEN must be set in .env\n"
            "Get it at: kaggle.com → Settings → API Tokens → Generate New Token"
        )
        sys.exit(1)
    return token


def _already_downloaded(dest: Path) -> bool:
    if not dest.exists():
        return False
    return any(dest.iterdir())


def _download_dataset(owner: str, name: str, dest: Path, token: str) -> None:
    url = f"{KAGGLE_API_BASE}/datasets/download/{owner}/{name}"
    headers = {"Authorization": f"Bearer {token}"}

    logger.info("Downloading {}/{} from Kaggle API...", owner, name)

    with httpx.Client(follow_redirects=True, timeout=300.0, headers=headers) as client:
        response = client.get(url)

    if response.status_code == 401:
        logger.error("Authentication failed — check your KAGGLE_API_TOKEN in .env")
        sys.exit(1)
    if response.status_code == 403:
        logger.error(
            "Access denied — you may need to accept the dataset rules at:\n"
            "  https://www.kaggle.com/datasets/{}/{}", owner, name
        )
        sys.exit(1)
    if response.status_code != 200:
        logger.error("Download failed with HTTP {}: {}", response.status_code, response.text[:200])
        sys.exit(1)

    dest.mkdir(parents=True, exist_ok=True)

    content_type = response.headers.get("content-type", "")
    if "zip" in content_type or response.content[:4] == b"PK\x03\x04":
        logger.info("Extracting zip ({:.1f} MB)...", len(response.content) / 1_000_000)
        with zipfile.ZipFile(BytesIO(response.content)) as zf:
            zf.extractall(dest)
        files = list(dest.rglob("*.*"))
        logger.info("Extracted {} file(s) to {}", len(files), dest)
    else:
        out_path = dest / f"{name}.csv"
        out_path.write_bytes(response.content)
        logger.info("Saved {:.1f} MB to {}", len(response.content) / 1_000_000, out_path)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Download Kaggle datasets for the pipeline.")
    parser.add_argument("--force", action="store_true", help="Re-download even if files already exist.")
    args = parser.parse_args()

    token = _token()

    for dataset in DATASETS:
        dest: Path = dataset["dest"]
        if not args.force and _already_downloaded(dest):
            logger.info("Already downloaded, skipping: {}/{}", dataset["owner"], dataset["name"])
            continue
        _download_dataset(dataset["owner"], dataset["name"], dest, token)

    logger.info("All datasets ready in data/raw/kaggle/")


if __name__ == "__main__":
    main()
