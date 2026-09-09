# src/engine/model.py
"""The engine's vocabulary (design.md §10, §11.2, §11.3). Pure data, no I/O."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

VALUE_KINDS = ("per_sale",)
CERTAINTIES = ("confirmed", "estimated")
STATUSES = ("available", "unavailable")
ACTIONS = ("verify_price", "count_product", "fix_record", "decide_idle", "review_policy", "check_purchase_cost")

# Permanent identity strings (design §10.1, ADR-009). FROZEN: never rename, never reuse,
# never delete one that has reached a run. The owner's outcomes in Firestore are keyed on
# hashes of these, so a change here silently orphans his recorded decisions. Adding a new
# family is safe; editing an existing one is not.
#
# What this key deliberately does NOT carry: an episode. A record that is fixed, breaks again
# and returns keeps the same id, so a `declined` recorded in the first episode still suppresses
# the second one. That is OQ-605, left open by both runs of the readiness gate (§19, "Two things
# the peer review raised that neither run resolved"), and it is a spec-layer question — not a
# licence to add a dimension here without one.
SIGNAL_FAMILIES = (
    "recon.impossible_opening",
    "hygiene.negative_stock",
    "hygiene.no_identifier",
    "hygiene.absent_price",
    "price.inverted",
    "price.above_ceiling",
    "competitor.policy_breach",
    "competitor.purchase_cost",
    "catalogue.idle",
    "catalogue.implausible_quantity",
    "margin.below_cost",
)


def norm_barcode(value: Any) -> Optional[str]:
    text = str(value or "").strip().lstrip("0")
    return text or None


def entry_id(signal_family: str, barcode: Optional[str], variant: str = "") -> str:
    """Identity of one finding about one product, stable across runs, thresholds and any
    future re-carving of the capabilities (ADR-009). The capability id is deliberately
    NOT part of the key: it is a routing label and may change."""
    if signal_family not in SIGNAL_FAMILIES:
        raise ValueError(f"unknown signal_family {signal_family!r}; enumerate it in SIGNAL_FAMILIES first")
    key = "|".join([signal_family, norm_barcode(barcode) or "", variant])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Value:
    amount: float
    kind: str
    certainty: str

    def __post_init__(self) -> None:
        if self.kind not in VALUE_KINDS:
            raise ValueError(f"unknown value kind {self.kind!r}; V1 kinds: {VALUE_KINDS}")
        if self.certainty not in CERTAINTIES:
            raise ValueError(f"unknown certainty {self.certainty!r}")

    def to_dict(self) -> dict:
        return {"amount": float(self.amount), "kind": self.kind, "certainty": self.certainty}


@dataclass
class Entry:
    id: str
    signal_family: str
    capability: str
    barcode: Optional[str]
    product_name: Optional[str]
    department: Optional[str]
    action: str
    characterisation: str
    evidence: dict
    value: Optional[Value]
    ordering_key: dict
    actionable: bool = False
    not_actionable_reason: Optional[str] = None
    attention: str = "today"

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["value"] = self.value.to_dict() if self.value else None
        return d


@dataclass
class Figure:
    name: str
    value: Optional[float]
    unit: str
    inputs: list
    thresholds: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"value": self.value, "unit": self.unit, "inputs": list(self.inputs), "thresholds": dict(self.thresholds)}


@dataclass
class EvidenceWindow:
    months: list
    first: Optional[str]
    last: Optional[str]
    count: int
    full_annual_cycle: bool

    @property
    def window_id(self) -> str:
        return f"{self.first}..{self.last}"

    def to_dict(self) -> dict:
        return {"months": list(self.months), "first": self.first, "last": self.last,
                "count": self.count, "full_annual_cycle": self.full_annual_cycle, "window_id": self.window_id}


@dataclass
class CapabilityOutput:
    id: str
    spec: str
    status: str
    requires: list = field(default_factory=list)
    unavailable_reason: Optional[str] = None
    window: Optional[EvidenceWindow] = None
    thresholds: dict = field(default_factory=dict)
    counts: dict = field(default_factory=dict)
    entries: list = field(default_factory=list)
    figures: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    extras: dict = field(default_factory=dict)      # capability-specific fields (design §11.4)

    def __post_init__(self) -> None:
        # `requires` is published beside the status so a reader can see what it was derived
        # from. It comes from the registry, never from the module: a capability that could
        # state its own dependencies could state them wrongly.
        if not self.requires:
            from src.engine.registry import CAPABILITIES    # local: registry imports nothing
            if self.id in CAPABILITIES:
                self.requires = list(CAPABILITIES[self.id].requires)

    @classmethod
    def unavailable(cls, id: str, spec: str, reason: str) -> "CapabilityOutput":
        return cls(id=id, spec=spec, status="unavailable", unavailable_reason=reason)

    def to_dict(self) -> dict:
        d = {
            "id": self.id, "spec": self.spec, "requires": list(self.requires), "status": self.status,
            "unavailable_reason": self.unavailable_reason,
            "window": self.window.to_dict() if self.window else None,
            "thresholds": dict(self.thresholds), "counts": dict(self.counts),
            "entries": [e.to_dict() for e in self.entries], "notes": list(self.notes),
        }
        for key, value in self.extras.items():
            if key in d:
                raise ValueError(f"extra {key!r} would shadow a contract field of {self.id}")
            d[key] = value
        return d
