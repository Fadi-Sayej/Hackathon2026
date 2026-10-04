# src/engine/market_boost.py
"""The market boost: a model's pick, checked, sealed, and replayed (ADR-032, ADR-035).

When the nearby market is running out of a product the store sells steadily, a language model
picks how much to raise that product's expected sales, from 0% to 25% (D-21). This module:

- decides **who is asked**: products that are moving (FR-145), that the market is running out
  of (ADR-031), and whose department has the facts a quantity needs (a schedule with fixed
  days, and a stated shelf life). Asking about a product that cannot get a quantity would
  spend the owner's money on a pick nothing uses, and would give the model facts the artefact
  never publishes (FR-164);
- **asks** once per product, with only those published facts, over HTTPS through `urllib`
  (no SDK, no new dependency), one retry, a timeout, and no sampling parameter;
- **checks** the answer mechanically: it must parse, and the pick must be a number from 0 to
  25, or it is rejected and never clipped (FR-147). A reason stating any figure is withheld;
- **seals** each night's picks as a snapshot under `snapshots/<on_day>/boost_picks/`, merge
  never replace, and never touches the day's own manifest (ADR-035);
- **replays** a recorded pick only onto the facts it was given (ADR-035 Decision 4).

The live step runs only in publish mode and only with a key. Print mode reads the snapshot
and never calls the model, so reproduction is committed inputs to the same artefact.

The key is read from `SMARTSHELF_ANTHROPIC_API_KEY`, which the nightly sets from the
`ANTHROPIC_API_KEY` secret. It is deliberately not `ANTHROPIC_API_KEY` itself: a developer
with that set for their own tools would otherwise spend it on every local `data:refresh`, and
write the picks into the committed snapshot directories.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from src.engine.inputs import EngineInputs
from src.engine.market_running_out import is_stale
from src.engine.model import CapabilityOutput
from src.engine.order_evidence import evidence_window, product_evidence
from src.engine.registry import derive_status

CAP, SPEC = "market_boost", "F8-S1"
ROOT = Path(__file__).resolve().parents[2]

MAX_TOKENS = 300
MAX_REASON_CHARS = 160
# ADR-039 Decision 3: the request, the key, the figure check and the digest are shared with the
# shelf explanation, and live in model_client. These names stay here for the boost's readers.
from src.engine.model_client import (DIGIT, KEY_ENV, ModelUnavailable, Transport,  # noqa: E402
                                     facts_digest, urllib_transport)
from src.engine.model_client import ask as _ask  # noqa: E402

BoostUnavailable = ModelUnavailable


# ── Who is asked ─────────────────────────────────────────────────────────────

def _department_ready(fact: Optional[dict]) -> bool:
    """Whether a department's stated facts are enough for a quantity (FR-155)."""
    if not fact:
        return False
    schedule, shelf = fact.get("order_schedule"), fact.get("shelf_life")
    if not schedule or schedule.get("form") == "no_fixed_days" or not shelf:
        return False
    return bool(shelf.get("does_not_spoil")) or (shelf.get("days") or 0) >= 1


def candidates(inputs: EngineInputs) -> list:
    """The facts each product is asked with, in request order (NFR-066).

    Most units in the window first, then barcode: when more products are running out than the
    night's ceiling, the ones that matter most to the shop are asked (ADR-032 Decision 5).
    """
    signal, rows_all = inputs.running_out, inputs.sales_daily
    if not signal or not rows_all or not inputs.products:
        return []
    window = evidence_window({r["day"] for r in rows_all}, inputs.policy, inputs.run_at)
    if window is None:
        return []
    facts_by_dept = (inputs.store_facts or {}).get("facts") or {}
    rows = defaultdict(list)
    for r in rows_all:
        rows[r["barcode"]].append(r)
    out = []
    for p in inputs.products:
        barcode = p["barcode"]
        market = signal["products"].get(barcode) if barcode else None
        if market is None or barcode not in rows:
            continue
        dept = facts_by_dept.get(p["department"])
        if not _department_ready(dept):
            continue
        evidence = product_evidence(rows[barcode], window)
        if not evidence["moving"]:
            continue
        out.append((evidence["units_in_window"], {
            "barcode": barcode, "product_name": p["product_name"], "department": p["department"],
            "weekly_units": evidence["weekly_units"], "daily_mean": evidence["daily_mean"],
            "stores_out": len(market["stores_out"]), "days_absent": sorted(market["days_absent"].values()),
            "shelf_life": dept["shelf_life"],
        }))
    out.sort(key=lambda pair: (-pair[0], pair[1]["barcode"]))
    return [facts for _units, facts in out]


# ── Asking ───────────────────────────────────────────────────────────────────

def ask(payload: dict, *, model: str, key: str, transport: Transport) -> str:
    """One Messages API call for a pick, a short answer (ADR-032)."""
    return _ask(payload, model=model, key=key, transport=transport, max_tokens=MAX_TOKENS)


# ── Checking (ADR-032 Decision 4) ────────────────────────────────────────────

def check(raw: str, max_pct: float) -> dict:
    """The mechanical check. Only `boost_pct` is ever used as a figure (INV-079)."""
    try:
        answer = json.loads(raw)
    except (ValueError, TypeError):
        return {"accepted": False, "rejected_because": "unparseable", "boost_pct": None, "reason": None}
    if not isinstance(answer, dict):
        return {"accepted": False, "rejected_because": "unparseable", "boost_pct": None, "reason": None}
    pct = answer.get("boost_pct")
    if not isinstance(pct, (int, float)) or isinstance(pct, bool) or not math.isfinite(pct):
        return {"accepted": False, "rejected_because": "not_a_number", "boost_pct": None, "reason": None}
    if pct < 0 or pct > max_pct:
        # Never clipped: a pick of 40 is a pick of 40, and it is not used at all (FR-147).
        return {"accepted": False, "rejected_because": "below_zero" if pct < 0 else "above_limit",
                "boost_pct": pct, "reason": None}
    reason, withheld = answer.get("reason"), None
    if not isinstance(reason, str) or not reason.strip():
        reason, withheld = None, "missing"
    elif DIGIT.search(reason):
        reason, withheld = None, "states_a_figure"
    elif len(reason) > MAX_REASON_CHARS:
        reason, withheld = None, "too_long"
    return {"accepted": True, "rejected_because": None, "boost_pct": pct,
            "reason": reason.strip() if reason else None, "reason_withheld_because": withheld}


# ── The snapshot (ADR-035) ───────────────────────────────────────────────────

def picks_dir(snapshots_root: Path, on_day: str) -> Path:
    return Path(snapshots_root) / on_day / "boost_picks"


def read_picks(snapshots_root: Path, on_day: str) -> Optional[dict]:
    """The day's sealed picks, or None when nothing was sealed for that day."""
    folder = picks_dir(snapshots_root, on_day)
    manifest = folder / "_manifest.json"
    if not manifest.exists():
        return None
    picks = folder / "picks.json"
    return {"on_day": on_day,
            "picks": json.loads(picks.read_text(encoding="utf-8")) if picks.exists() else {},
            "manifest": json.loads(manifest.read_text(encoding="utf-8"))}


def _write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _prompt(policy) -> Tuple[str, str]:
    text = (ROOT / policy.boost_prompt).read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def live_step(inputs: EngineInputs, *, snapshots_root: Path, key: Optional[str], transport: Transport,
              now: datetime) -> dict:
    """Ask for tonight's picks and seal them. Publish mode only (run.py decides).

    Writes nothing without a key: the absence of the day's snapshot is then what says so, in
    the live artefact and in any reproduction of it alike. With a key it always writes the
    manifest, even when nobody needed asking, so a reproduction can tell "nothing to ask"
    from "never asked".

    Merge never replace: a product already holding a pick for the day is not asked again,
    and its pick is not rewritten. The night's ceiling counts every request made that day.
    Each pick is written as it arrives, so a failure part-way keeps what was paid for.
    """
    signal, policy = inputs.running_out, inputs.policy
    if not signal:
        return {"skipped": "no_market_signal", "requests_made": 0}
    if is_stale(signal, inputs.run_at, policy):
        return {"skipped": "market_signal_stale", "requests_made": 0}
    if not key:
        return {"skipped": "no_boost_key", "requests_made": 0}
    folder = picks_dir(snapshots_root, signal["on_day"])
    sealed = read_picks(snapshots_root, signal["on_day"]) or {"picks": {}, "manifest": {"runs": []}}
    picks, manifest = dict(sealed["picks"]), sealed["manifest"]
    manifest.setdefault("runs", [])
    system, prompt_sha = _prompt(policy)
    todo = [f for f in candidates(inputs) if f["barcode"] not in picks]
    budget = max(0, policy.boost_request_ceiling - sum(r.get("requests_made", 0) for r in manifest["runs"]))
    run = {"requested_at": now.isoformat(), "model": policy.boost_model, "prompt": policy.boost_prompt,
           "prompt_sha256": prompt_sha, "ceiling": policy.boost_request_ceiling, "requests_made": 0,
           "ceiling_reached": [f["barcode"] for f in todo[budget:]], "completed": False, "error": None}
    for facts in todo[:budget]:
        try:
            raw = ask({"system": system, "user": json.dumps(facts, ensure_ascii=False, sort_keys=True)},
                      model=policy.boost_model, key=key, transport=transport)
        except BoostUnavailable as err:
            run["error"] = str(err)
            break
        run["requests_made"] += 1
        result = check(raw, policy.boost_max_pct)
        picks[facts["barcode"]] = {
            "barcode": facts["barcode"], "model": policy.boost_model, "prompt": policy.boost_prompt,
            "prompt_sha256": prompt_sha, "requested_at": now.isoformat(), "inputs_digest": facts_digest(facts),
            **result,
            # Kept for audit, never shown and never used: what the model actually said.
            "raw": raw[:1000] if not result["accepted"] or result.get("reason_withheld_because") else None,
        }
        _write(folder / "picks.json", picks)
    else:
        run["completed"] = True
    manifest["runs"].append(run)
    _write(folder / "picks.json", picks)
    _write(folder / "_manifest.json", manifest)
    return {"skipped": None, "requests_made": run["requests_made"], "completed": run["completed"],
            "error": run["error"], "wrote": True}


# ── Replay: what is applied (ADR-035 Decision 4) ─────────────────────────────

def resolve(inputs: EngineInputs) -> dict:
    """{barcode: what the boost is for it tonight}, for every product that would be asked.

    The one derivation of "is a boost applied": the capability publishes it, and the quantity
    (Task 5.8) reads it, so the two can never disagree about a product's boost.
    """
    sealed = inputs.boost_picks or {"picks": {}, "manifest": {"runs": []}}
    runs = (sealed.get("manifest") or {}).get("runs") or []
    beyond = set(runs[-1].get("ceiling_reached") or []) if runs else set()
    out = {}
    for facts in candidates(inputs):
        barcode = facts["barcode"]
        pick = sealed["picks"].get(barcode)
        entry = {"facts": facts, "applied": False, "boost_pct": None, "reason": None,
                 "reason_withheld_because": None, "model": None, "model_pick_pct": None,
                 "not_applied_because": None}
        if pick is None:
            entry["not_applied_because"] = "ceiling_reached" if barcode in beyond else "no_pick"
        else:
            entry.update(model=pick["model"], model_pick_pct=pick.get("boost_pct"))
            if pick["inputs_digest"] != facts_digest(facts):
                entry["not_applied_because"] = "facts_changed"
            elif not pick["accepted"]:
                entry["not_applied_because"] = pick["rejected_because"]
            else:
                entry.update(applied=True, boost_pct=pick["boost_pct"], reason=pick.get("reason"),
                             reason_withheld_because=pick.get("reason_withheld_because"))
        out[barcode] = entry
    return out


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    if is_stale(inputs.running_out, inputs.run_at, inputs.policy):
        return CapabilityOutput.unavailable(CAP, SPEC, "market_signal_stale")
    runs = (inputs.boost_picks.get("manifest") or {}).get("runs") or []
    if runs and not runs[-1].get("completed"):
        # ADR-032 Decision 6: an API failure or a timeout makes the boost unavailable tonight.
        out = CapabilityOutput.unavailable(CAP, SPEC, "boost_unavailable")
        out.extras = {"on_day": inputs.boost_picks["on_day"], "error": runs[-1].get("error")}
        return out
    picks = resolve(inputs)
    applied = [p for p in picks.values() if p["applied"]]
    counts = {"asked_about": len(picks), "applied": len(applied),
              "reason_withheld": sum(1 for p in applied if p["reason_withheld_because"]),
              "not_applied": len(picks) - len(applied)}
    policy = inputs.policy
    return CapabilityOutput(
        id=CAP, spec=SPEC, status="available", thresholds=policy.as_dict()["market_boost"], counts=counts,
        extras={"on_day": inputs.boost_picks["on_day"], "model": policy.boost_model,
                "prompt": policy.boost_prompt, "picks": picks,
                # D-10, D-21: what this is, in the artefact itself.
                "label": "model_estimate"})
