"""
owner_answers.py — what the store owner told the system, and how it overrides guesses.

The pipeline guesses shelf life from a category table and cannot tell a genuine
stockout from a line the shop dropped on purpose. Both guesses drive real orders. This
module loads his answers (configs/owner_answers.yaml) and gives the rest of the
pipeline a single place to ask "did he tell us about this one?".

An answer always wins over a default, and it is marked `owner` so nothing downstream
describes it as a system assumption — that distinction is the whole point of asking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.common.paths import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "configs" / "owner_answers.yaml"

SOURCE_OWNER = "owner"

CARRIED_YES = "yes"
CARRIED_NO = "no"
CARRIED_SEASONAL = "seasonal"

# Answers that mean "do not put this on an order list". `seasonal` is deliberately
# not the same as `no`: the product comes back, so it must not be treated as a
# permanent delisting, but ordering it now is still wrong.
NOT_ORDERABLE = {CARRIED_NO, CARRIED_SEASONAL}


def load_owner_answers(path: Optional[Path] = None) -> Dict[str, Any]:
    """Everything the owner has answered. Empty structures when nothing yet."""
    path = path or CONFIG_PATH
    empty = {"carried": {}, "shelfLifeDays": {}, "shelfLifeCategories": {}}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return empty
    return {
        "carried": {str(k): v for k, v in (loaded.get("carried") or {}).items()},
        "shelfLifeDays": {str(k): v for k, v in (loaded.get("shelf_life_days") or {}).items()},
        "shelfLifeCategories": {
            str(k): v for k, v in (loaded.get("shelf_life_categories") or {}).items()
        },
    }


def carried_answer(barcode: Optional[str], answers: Dict[str, Any]) -> Optional[str]:
    entry = (answers.get("carried") or {}).get(str(barcode or ""))
    if isinstance(entry, dict):
        return entry.get("answer")
    return entry if isinstance(entry, str) else None


def is_orderable(barcode: Optional[str], answers: Dict[str, Any]) -> bool:
    """False only when he has actually said not to order it."""
    return carried_answer(barcode, answers) not in NOT_ORDERABLE


def shelf_life_answer(
    barcode: Optional[str],
    category: Optional[str],
    answers: Dict[str, Any],
) -> Optional[int]:
    """Owner-set shelf life for this product: per-product first, then category."""
    per_product = (answers.get("shelfLifeDays") or {}).get(str(barcode or ""))
    days = per_product.get("days") if isinstance(per_product, dict) else per_product
    if isinstance(days, (int, float)) and days > 0:
        return int(days)

    per_category = (answers.get("shelfLifeCategories") or {}).get(str(category or ""))
    days = per_category.get("days") if isinstance(per_category, dict) else per_category
    if isinstance(days, (int, float)) and days > 0:
        return int(days)
    return None
