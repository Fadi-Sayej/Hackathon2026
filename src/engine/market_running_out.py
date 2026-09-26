# src/engine/market_running_out.py
"""The market running out of a product, as a capability (ADR-031 Decision 5, ADR-014).

A capability of its own so it can be unavailable on its own: when the market was not
observed on enough of the last fortnight (`market_signal_thin`, from the input), or its
latest observed day is too old to describe tonight (`market_signal_stale`, this rule's).
F8-S1 FR-148 then applies to the quantity, which is computed without the adjustment.

It publishes facts, not entries: which night it describes, the store-days it excluded and
why, and for each product the stores it is running out at and for how many days. It carries
no money (INV-069) and admits nothing to the daily surface. The quantity and the
disagreement question read it; the owner sees it only through them.
"""
from __future__ import annotations

from datetime import date

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput
from src.engine.registry import derive_status

CAP, SPEC = "market_running_out", "F8-S1"


def _thresholds(policy) -> dict:
    """ADR-031 Decision 6: the values are published with the signal."""
    return policy.as_dict()["market_running_out"]


def is_stale(signal: dict, run_at, policy) -> bool:
    """ADR-031 Decision 5: the latest usable day is too old to describe tonight.

    The one place this is judged. The boost (ADR-032) asks nothing on a stale night and
    publishes the same reason, so the two can never disagree about which nights are stale.
    """
    return (run_at.date() - date.fromisoformat(signal["on_day"])).days > policy.running_out_signal_max_age_days


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    policy, signal = inputs.policy, inputs.running_out
    if is_stale(signal, inputs.run_at, policy):
        out = CapabilityOutput.unavailable(CAP, SPEC, "market_signal_stale")
        out.extras = {"on_day": signal["on_day"]}
        return out
    return CapabilityOutput(
        id=CAP, spec=SPEC, status="available", thresholds=_thresholds(policy),
        counts={"running_out": len(signal["products"]), "stores": len(signal["stores"]),
                "excluded_store_days": len(signal["excluded"])},
        extras={"on_day": signal["on_day"], "stores": list(signal["stores"]),
                "excluded": list(signal["excluded"]), "products": dict(signal["products"])})
