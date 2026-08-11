"""
store_types.py — store identity: what kind of shop is this, and is it comparable?

The problem this solves: without a store-format field, a 25,000-SKU hypermarket and
a forecourt shop 1.4 km away are treated as equivalent price sources. The system
then recommends 5 kg rice bags and 24-packs to a gas-station minimarket, and one
absurd recommendation costs the manager's trust in every correct one after it.

All reference data lives in `configs/store_types.yaml` — the scale, the affinity
matrix, and the per-branch classification. Nothing here hardcodes a format.

Usage
-----
    from src.common.store_types import load_store_types

    cfg = load_store_types()
    cfg.store_type("shufersal-pt-01")          # -> "hypermarket"
    cfg.affinity("gas_convenience", "hypermarket")   # -> 0.0
    cfg.comparable_stores("gas_convenience")   # -> ["yomyom-kq-01", "dor-alon-kq-01", ...]
    cfg.infer_store_type(16547)                # -> ("supermarket", 0.6)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.common.paths import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "configs" / "store_types.yaml"

# Machine-written classifications live in their own file. Two reasons: the main
# config is hand-edited and full of comments a YAML round-trip would delete, and
# an inferred format is easier to distrust when it is not sitting in the same
# block as the human-verified ones. Entries here NEVER override the main file.
INFERRED_CONFIG_PATH = PROJECT_ROOT / "configs" / "store_types.inferred.yaml"

UNKNOWN = "unknown"

# A classification nobody has confirmed on the ground. Both are guesses; they are
# kept distinct in the file so an operator can see *how* the guess was made, but
# no engine may treat either as verified.
UNVERIFIED = ("inferred", "proposed")


@dataclass(frozen=True)
class StoreRecord:
    store_id: str
    store_type: str
    verified: str
    basis: str | None = None
    name: str | None = None
    chain: str | None = None
    note: str | None = None
    confidence: float | None = None
    distinct_skus: int | None = None

    @property
    def is_verified(self) -> bool:
        """A person decided this, so no script may overwrite it."""
        return self.verified == "manual"

    @property
    def is_first_hand(self) -> bool:
        """We know this specific branch, rather than reasoning from its chain.

        Deliberately separate from `is_verified`: a person can decide a format
        confidently from desk knowledge, and that decision is final without being
        first-hand. A branch that is unusual for its chain is exactly where
        `chain_format` goes wrong, so the distinction has to survive in the data.
        """
        return self.basis == "branch_known"


@dataclass(frozen=True)
class StoreTypeConfig:
    formats: dict[str, dict[str, Any]]
    affinity_matrix: dict[str, dict[str, float]]
    stores: dict[str, StoreRecord]
    min_affinity: float = 0.3
    min_skus_for_inference: int = 300
    inference_confidence: float = 0.6
    _sku_ranges: dict[str, tuple[int, int]] = field(default_factory=dict)

    # ── lookups ──────────────────────────────────────────────────────────────

    def store(self, store_id: str) -> StoreRecord | None:
        return self.stores.get(str(store_id))

    def store_type(self, store_id: str) -> str:
        """Format of a branch, or `unknown` if we have never classified it."""
        record = self.store(store_id)
        return record.store_type if record else UNKNOWN

    def affinity(self, our_type: str, their_type: str) -> float:
        """How comparable `their_type` is to `our_type`, in [0.0, 1.0].

        0.0 means never compare. An unrecognised format falls back to the
        `unknown` row/column rather than to 1.0 — a missing classification must
        never read as a perfect match.
        """
        row = self.affinity_matrix.get(our_type) or self.affinity_matrix.get(UNKNOWN, {})
        value = row.get(their_type)
        if value is None:
            value = row.get(UNKNOWN, 0.0)
        return float(value)

    def store_affinity(self, our_store_id: str, their_store_id: str) -> float:
        """Affinity between two branches, resolved through their formats."""
        return self.affinity(self.store_type(our_store_id), self.store_type(their_store_id))

    def comparable_stores(self, our_type: str, min_affinity: float | None = None) -> list[str]:
        """Store IDs worth comparing against, weighted by format affinity.

        Returned in descending affinity order, so the most comparable branch — the
        forecourt shop down the road, not the big box — comes first.
        """
        threshold = self.min_affinity if min_affinity is None else min_affinity
        scored = [
            (store_id, self.affinity(our_type, record.store_type))
            for store_id, record in self.stores.items()
        ]
        scored = [pair for pair in scored if pair[1] >= threshold]
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return [store_id for store_id, _ in scored]

    def excluded_stores(self, our_type: str) -> list[str]:
        """Store IDs at affinity 0.0 — the ones that must never reach an engine."""
        return sorted(
            store_id
            for store_id, record in self.stores.items()
            if self.affinity(our_type, record.store_type) == 0.0
        )

    # ── inference (Step 3) ───────────────────────────────────────────────────

    def infer_store_type(self, distinct_skus: int | None) -> tuple[str, float]:
        """Return (store_type, confidence). Never returns a verified classification.

        Distinct SKU count correlates strongly with format, but only when the count
        comes from a full catalog. A partial scrape of 27 SKUs from a Shufersal
        branch would otherwise classify it as a forecourt shop — the exact failure
        this module exists to prevent — so anything below `min_skus_for_inference`
        is refused outright.
        """
        if distinct_skus is None or distinct_skus < self.min_skus_for_inference:
            return UNKNOWN, 0.0
        for fmt, (lo, hi) in self._sku_ranges.items():
            if lo <= distinct_skus <= hi:
                return fmt, self.inference_confidence
        return UNKNOWN, 0.0


def _coerce_range(raw: Any) -> tuple[int, int] | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        return None
    return int(raw[0]), int(raw[1])


def load_store_types(path: Path | str | None = None) -> StoreTypeConfig:
    """Load and validate configs/store_types.yaml."""
    config_path = Path(path) if path else CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(f"store type config not found: {config_path}")

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    formats = raw.get("formats") or {}
    if not formats:
        raise ValueError(f"{config_path} defines no formats")

    sku_ranges: dict[str, tuple[int, int]] = {}
    for fmt, meta in formats.items():
        bounds = _coerce_range((meta or {}).get("typical_sku_range"))
        if bounds is None:
            raise ValueError(f"format '{fmt}' has no valid typical_sku_range")
        sku_ranges[fmt] = bounds

    affinity_matrix: dict[str, dict[str, float]] = {}
    for our_type, row in (raw.get("affinity") or {}).items():
        affinity_matrix[our_type] = {k: float(v) for k, v in (row or {}).items()}

    missing = [fmt for fmt in formats if fmt not in affinity_matrix]
    if missing:
        raise ValueError(f"{config_path}: formats with no affinity row: {', '.join(sorted(missing))}")

    # Inferred entries load first so a hand-written entry always wins the merge.
    merged: dict[str, dict] = {}
    inferred_path = config_path.with_name(config_path.stem + ".inferred.yaml")
    if inferred_path.exists():
        inferred_raw = yaml.safe_load(inferred_path.read_text(encoding="utf-8")) or {}
        merged.update(inferred_raw.get("stores") or {})
    merged.update(raw.get("stores") or {})

    stores: dict[str, StoreRecord] = {}
    for store_id, meta in merged.items():
        meta = meta or {}
        store_type = meta.get("store_type") or UNKNOWN
        if store_type != UNKNOWN and store_type not in formats:
            raise ValueError(f"store '{store_id}' has unknown store_type '{store_type}'")
        stores[str(store_id)] = StoreRecord(
            store_id=str(store_id),
            store_type=store_type,
            verified=meta.get("verified") or "inferred",
            basis=meta.get("basis") or ("sku_count" if meta.get("distinct_skus") else None),
            name=meta.get("name"),
            chain=meta.get("chain"),
            note=meta.get("note"),
            confidence=meta.get("confidence"),
            distinct_skus=meta.get("distinct_skus"),
        )

    return StoreTypeConfig(
        formats=formats,
        affinity_matrix=affinity_matrix,
        stores=stores,
        min_affinity=float(raw.get("min_affinity", 0.3)),
        min_skus_for_inference=int(raw.get("min_skus_for_inference", 300)),
        inference_confidence=float(raw.get("inference_confidence", 0.6)),
        _sku_ranges=sku_ranges,
    )


@lru_cache(maxsize=1)
def get_store_types() -> StoreTypeConfig:
    """Cached loader for callers that just want the default config."""
    return load_store_types()
