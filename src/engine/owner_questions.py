# src/engine/owner_questions.py
"""SPEC-005 — the few facts only the owner holds.

V1 asks exactly one kind of question: a missing purchase cost on a LIVING product.
Suppression does the work (NFR-040): withdrawn and idle products are never asked
about, so 1,270 missing costs become the handful the intent names.

V2 adds a second kind, `market_disagreement` (F8-S1 FR-158, ADR-034): the nearby market is
running out of a product he stocks that does not sell here. It is asked once, ever (D-20),
it changes no quantity, and it is published only while `order.publish_disagreement_questions`
is on, because until Task 5.14 the panel renders every question as a cost question."""
from __future__ import annotations

import hashlib
from collections import defaultdict

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Figure
from src.engine.registry import derive_status

CAP, SPEC = "owner_questions", "SPEC-005"
FACT = "cost_price"
DISAGREEMENT = "market_disagreement"
# Permanent, like every name in design §10.1: an answer is stored under the fact.
FACTS = (FACT, DISAGREEMENT)
# FR-158: why it does not sell here. Only he knows; nothing consumes the answer but retirement.
DISAGREEMENT_ANSWERS = ("shelf_place", "price", "weak_market", "sells_elsewhere")


def _question_id(barcode: str, fact: str = FACT) -> str:
    return hashlib.sha256(f"{fact}|{barcode}".encode("utf-8")).hexdigest()[:16]


def _record(owner, barcode: str, fact: str = FACT) -> dict:
    return (owner.answers.get(barcode) or {}).get(fact) or {}


def _deferred(owner, barcode: str, fact: str = FACT) -> bool:
    return _record(owner, barcode, fact).get("status") == "deferred"


def _answered(owner, barcode: str, fact: str = FACT) -> bool:
    return _record(owner, barcode, fact).get("status") == "answered"


def _disagreements(inputs: EngineInputs) -> list:
    """FR-158: the market is running out of a product he stocks, and it is not moving.

    - Not asked without a window, because "not moving" is measured over one, except in a
      department no evidence itemises at all (FR-156), where it says there is no sales row.
    - Not asked without a market signal, or with a stale one (AC-142).
    - Never suppressed as idle or withdrawn (C-67): the test is his stocking, read from the
      window (Task 5.5), and a product he does not stock is never asked about (FR-082).
    - Answered is retired for good, whatever the facts later say (D-20 over FR-089).
    - Its `why` says only what was observed. It never claims the market sells a lot (§21).
    """
    from src.engine.market_running_out import is_stale
    from src.engine.order_evidence import evidence_window, product_evidence, stocks
    from src.engine.order_quantity import itemised_departments

    signal, policy = inputs.running_out, inputs.policy
    if signal is None or is_stale(signal, inputs.run_at, policy):
        return []
    daily = inputs.sales_daily or []
    window = evidence_window({r["day"] for r in daily}, policy, inputs.run_at) if daily else None
    itemised = itemised_departments(inputs)
    rows = defaultdict(list)
    for r in daily:
        rows[r["barcode"]].append(r)
    items = []
    for p in inputs.products:
        b = p["barcode"]
        market = signal["products"].get(b) if b else None
        if market is None:
            continue
        status = _record(inputs.owner, b, DISAGREEMENT).get("status")
        if status in ("answered", "deferred"):
            continue                                   # retired for good, or open and not presented
        why = {"stores_out": len(market["stores_out"]), "days_absent": sorted(market["days_absent"].values())}
        if p["department"] in itemised:
            if window is None or not stocks(rows.get(b, []), window, p["recorded_stock"], itemised=True):
                continue
            evidence = product_evidence(rows.get(b, []), window)
            if evidence["moving"]:
                continue                               # it gets a quantity instead (D-19)
            why.update(units_in_window=evidence["units_in_window"], weekly_units=evidence["weekly_units"],
                       report_days=evidence["report_days"], no_sales_row=False)
        else:
            if not stocks([], None, p["recorded_stock"], itemised=False):
                continue
            why.update(units_in_window=None, weekly_units=None, report_days=None, no_sales_row=True)
        items.append({"question_id": _question_id(b, DISAGREEMENT), "barcode": b,
                      "product_name": p["product_name"], "department": p["department"],
                      "fact": DISAGREEMENT, "why": why, "answers": list(DISAGREEMENT_ANSWERS),
                      "expected_value": None})
    # C-68: among its own kind, by units sold in the window, then barcode (ADR-027's tiebreak).
    return sorted(items, key=lambda i: (-(i["why"]["units_in_window"] or 0.0), i["barcode"]))


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
    if inputs.policy.order_publish_disagreement_questions:
        # After every question above, whose order is untouched: none of these carries a ₪
        # figure (C-68, ADR-027). Off, nothing is even computed, so the items are byte for
        # byte what V1 publishes.
        disagreements = _disagreements(inputs)
        items.extend(disagreements)
        counts["open_disagreement"] = len(disagreements)
    out = CapabilityOutput(id=CAP, spec=SPEC, status="available",
                           thresholds={"question_limit": inputs.policy.question_limit}, counts=counts,
                           entries=[], figures=[Figure(k, v, "questions", ["pos", "sales", "owner_state"]) for k, v in counts.items()])
    out.extras = {"limit": inputs.policy.question_limit, "items": items, "suppressed": suppressed}
    return out
