"""
init_storage.py — create the full YomYom storage folder tree.

Run once to bootstrap the project before any collector runs:

    python scripts/init_storage.py

All folders are created idempotently (already-existing folders are left
untouched).  A .gitkeep file is placed in each leaf directory so git
tracks the empty folders.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root (one level above scripts/) is on sys.path so that
# `from src.common...` imports work regardless of the working directory.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from loguru import logger

# ── Import canonical paths ─────────────────────────────────────────────────────
from src.common.paths import (
    DATA_ROOT,
    EXTERNAL_BRONZE_ROOT,
    EXTERNAL_RAW_ROOT,
    EXTERNAL_ROOT,
    EXTERNAL_SILVER_ROOT,
    INTERNAL_ROOT,
    LOGS_ROOT,
    MATCHING_ROOT,
    QUALITY_ROOT,
    RAW_POS_ROOT,
    RECOMMENDATIONS_ROOT,
    SIGNALS_ROOT,
    SILVER_POS_ROOT,
)

# ── Folder manifest ────────────────────────────────────────────────────────────
FOLDERS: list[Path] = [
    # Internal data
    RAW_POS_ROOT,
    SILVER_POS_ROOT,
    # External data
    EXTERNAL_RAW_ROOT,
    EXTERNAL_BRONZE_ROOT,
    EXTERNAL_SILVER_ROOT,
    # Derived datasets
    MATCHING_ROOT,
    SIGNALS_ROOT,
    RECOMMENDATIONS_ROOT,
    # Reports & logs
    QUALITY_ROOT,
    LOGS_ROOT,
]


def create_folders(folders: list[Path]) -> None:
    created: list[Path] = []
    skipped: list[Path] = []

    for folder in folders:
        if folder.exists():
            skipped.append(folder)
        else:
            folder.mkdir(parents=True, exist_ok=True)
            created.append(folder)

        # Always ensure .gitkeep exists (idempotent)
        gitkeep = folder / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    if created:
        logger.success("Created {} folder(s):", len(created))
        for f in created:
            logger.info("  + {}", f)
    if skipped:
        logger.info("Already existed ({} folder(s)) — skipped.", len(skipped))


def main() -> None:
    logger.info("Initialising YomYom storage layer…")
    create_folders(FOLDERS)
    logger.success("Storage initialisation complete.")
    logger.info("Root: {}", DATA_ROOT.parent)


if __name__ == "__main__":
    main()
