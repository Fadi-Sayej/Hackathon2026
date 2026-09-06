"""
shelf_life.py — category shelf-life defaults, for capping reorder quantities.

Nothing in the POS export records shelf life, so these are crude category-level
defaults the store owner is expected to correct (configs/shelf_life.yaml). They are
published into public/data/market-context.json so the browser — where the order
quantity is decided — reads exactly the same numbers the pipeline did, and so a
correction lands in one place rather than two.

`None` means not perishable: no cap. An unlisted category also gets no cap, because
suppressing a real order on a guess is the worse error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.common.paths import PROJECT_ROOT
from src.context.owner_answers import SOURCE_OWNER, load_owner_answers

CONFIG_PATH = PROJECT_ROOT / "configs" / "shelf_life.yaml"

# Marks the provenance of every number below, so the explanation can say "default"
# rather than implying a measurement. Becomes 'owner' once he corrects a line.
SOURCE_CONFIG_DEFAULT = "config_default"


def load_shelf_life(path: Optional[Path] = None) -> Dict[str, Any]:
    """{category: days|None} plus the fallback for unlisted categories."""
    path = path or CONFIG_PATH
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {"categories": {}, "defaultDays": None, "source": SOURCE_CONFIG_DEFAULT}

    categories = loaded.get("categories") or {}
    answers = load_owner_answers()
    # What he told us beats what we guessed, and is published separately so the
    # explanation can say "you told us" rather than "system default".
    return {
        "categories": {str(k): v for k, v in categories.items()},
        "defaultDays": loaded.get("default_days"),
        "source": SOURCE_CONFIG_DEFAULT,
        "ownerCategories": {
            k: (v.get("days") if isinstance(v, dict) else v)
            for k, v in (answers.get("shelfLifeCategories") or {}).items()
        },
        "ownerProducts": {
            k: (v.get("days") if isinstance(v, dict) else v)
            for k, v in (answers.get("shelfLifeDays") or {}).items()
        },
        "ownerSource": SOURCE_OWNER,
    }


def shelf_life_for(category: Optional[str], table: Dict[str, Any]) -> Optional[int]:
    """Days this category keeps, or None for no cap."""
    if not category:
        return table.get("defaultDays")
    categories = table.get("categories") or {}
    return categories.get(category, table.get("defaultDays"))
