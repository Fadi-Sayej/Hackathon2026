# src/engine/owner_questions.py
"""SPEC-005 — the few facts only the owner holds.

V1 asks exactly one kind of question: a missing purchase cost on a LIVING product.
Suppression does the work (NFR-040): withdrawn and idle products are never asked
about, so 1,270 missing costs become the handful the intent names."""
from __future__ import annotations

import hashlib

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Figure
from src.engine.registry import derive_status

CAP, SPEC = "owner_questions", "SPEC-005"
FACT = "cost_price"


def _question_id(barcode: str) -> str:
    return hashlib.sha256(f"{FACT}|{barcode}".encode("utf-8")).hexdigest()[:16]


def _deferred(owner, barcode: str) -> bool:
    rec = (owner.answers.get(barcode) or {}).get(FACT) or {}
    return rec.get("status") == "deferred"


def _answered(owner, barcode: str) -> bool:
    rec = (owner.answers.get(barcode) or {}).get(FACT) or {}
    return rec.get("status") == "answered"


def run(inputs: EngineInputs) -> CapabilityOutput:
    empty = {"limit": inputs.policy.question_limit, "items": [],
             "suppressed": {"withdrawn": 0, "idle": 0, "answered": 0, "no_effect": 0}}
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if inputs.owner.status != "available":
        # SPEC-005 §11: never present a question that cannot be recorded. A rule-level
        # reason: the input landed, the place to write the answer did not.
        status, reason = "unavailable", "answer_storage_unavailable"
    if status == "unavailable":
        out = CapabilityOutput.unavailable(CAP, SPEC, reason)
        out.extras = empty
        return out

    withdrawn, idle = inputs.withdrawn or set(), inputs.idle or set()
    suppressed = {"withdrawn": 0, "idle": 0, "answered": 0, "no_effect": 0}
    items = []
    for p in inputs.products:
        b = p["barcode"]
        if not b:
            continue
        if p["cost_price"] is not None:
            if p["cost_source"] == "owner":
                suppressed["answered"] += 1
            else:
                suppressed["no_effect"] += 1
            continue
        if b in withdrawn:
            suppressed["withdrawn"] += 1; continue
        if b in idle:
            suppressed["idle"] += 1; continue
        if _deferred(inputs.owner, b):
            continue                                   # open, not presented, not content (FR-091)
        s = (inputs.sales_summary or {}).get(b)
        units = float(s["units_total"]) if s else 0.0
        if units <= 0:
            suppressed["no_effect"] += 1; continue     # not living: answering changes nothing today
        # ARCH-GATE-002: the basis is declared in policy.yaml and published with the figure,
        # because FR-085 orders by money and never says which money.
        #
        # ADR-027: with no shelf price there is no figure. Reading it as 0.0 published "₪0 at
        # stake" for a stake that is unknown, and sorted the question last for it. The basis
        # is still published, because it says which figure is missing and why.
        money = units * p["shelf_price"] if p["shelf_price"] else None
        items.append({"question_id": _question_id(b), "barcode": b, "product_name": p["product_name"],
                      "department": p["department"], "fact": FACT,
                      "why": {"products_affected": 1,
                              "money_at_stake": round(money, 2) if money is not None else None,
                              "money_missing": None if money is not None else "shelf_price",
                              "money_basis": inputs.policy.question_money_basis,
                              "units_sold": units, "window_id": inputs.window.window_id if inputs.window else None},
                      "expected_value": (round(money * inputs.policy.question_yield_factor, 2)
                                         if money is not None else None)})
    # FR-085 over exactly the questions it can be computed for, then the rest by units sold,
    # the only weight a question without a figure has. It orders them; it is never money.
    items.sort(key=lambda i: (0, -i["expected_value"], i["barcode"]) if i["expected_value"] is not None
               else (1, -i["why"]["units_sold"], i["barcode"]))
    counts = {"open": len(items), "suppressed_withdrawn": suppressed["withdrawn"], "suppressed_idle": suppressed["idle"],
              "suppressed_answered": suppressed["answered"], "suppressed_no_effect": suppressed["no_effect"]}
    out = CapabilityOutput(id=CAP, spec=SPEC, status="available",
                           thresholds={"question_limit": inputs.policy.question_limit}, counts=counts,
                           entries=[], figures=[Figure(k, v, "questions", ["pos", "sales", "owner_state"]) for k, v in counts.items()])
    out.extras = {"limit": inputs.policy.question_limit, "items": items, "suppressed": suppressed}
    return out
