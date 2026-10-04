"""shelf_explanation — the AI's explanation of each fixture's plan (D-32, F12-S1 FR-210 … FR-215).

The owner asked that the AI tell him why to organize the shelf the way the plan says (D-32). It is
made the way D-16 makes an AI-written reason, and the way the market boost already does
(ADR-032, ADR-035), as ADR-039 records:
- **Once a night, never on request.** The live run asks the pinned model once for each fixture
  plan it has not explained before, checks the answer, and seals it under
  `data/external/snapshots/<plan date>/shelf_explanations/`. Print mode never asks: it reads the
  night's snapshot, so a reproduction shows the same text from committed inputs.
- **Only the plan's own facts** (FR-211). The fixture's shelves and eye level, each placed product's
  name, department, facings and place in the earnings order, what is not placed and why, his
  rules, and the elasticity used and why. No price, cost, margin, demand or barcode: the only
  numbers sent are facings, shelf positions and the elasticity.
- **Checked mechanically** (FR-212). It must parse as Hebrew, Arabic and English within the length
  limit. No text may hold a digit outside the product names it was given (D-16's figure check,
  looser than the boost's only by those names). A failing answer is withheld whole.
- **Paid for once** (FR-213). A fixture whose facts, model and prompt match an accepted
  explanation in the most recent earlier snapshot reuses it, copied into tonight's.
- **Bounded** (FR-214, NFR-077). A per-night ceiling of requests and a time budget, checked before
  each request, and the night's asking stops at the first request that fails twice.

The explanation never changes the plan (INV-096): nothing reads its text back.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from src.engine.model import CapabilityOutput
from src.engine.model_client import DIGIT, ModelUnavailable, Transport, ask, facts_digest
from src.engine.registry import derive_status

CAP, SPEC = "shelf_explanation", "F12-S1"
FOLDER = "shelf_explanations"
ROOT = Path(__file__).resolve().parents[2]
LANGUAGES = ("he", "ar", "en")


# ── What the model is given (FR-211) ─────────────────────────────────────────

def facts(entry: dict, names: dict) -> dict:
    """One fixture plan's facts, from its published entry. Names, never barcodes."""
    ev = entry["evidence"]
    name = lambda b: names.get(b) or "unnamed product"           # noqa: E731

    def product(p: dict) -> dict:
        return {"product_name": p.get("product_name") or name(p["barcode"]), "department": p.get("department"),
                "facings": p["facings"], "earnings": "unknown" if p.get("rank") is None else "known",
                "unknown": p.get("unknown_parts") or [], "kept_on_by_his_rule": bool(p.get("kept_on_by_his_rule"))}

    # The earnings order, as names only: a rank is a number, and FR-211's only numbers are facings,
    # shelf positions and the elasticity (AC-202).
    placed = [p for s in ev.get("shelves") or [] for p in s["products"] if p.get("rank") is not None]
    earnings_order = [p.get("product_name") or name(p["barcode"]) for p in sorted(placed, key=lambda p: p["rank"])]

    not_placed = []
    for reason, items in sorted((ev.get("unplaced") or {}).items()):
        for item in items:
            barcode = item["barcode"] if isinstance(item, dict) else item
            not_placed.append({"product_name": name(barcode), "reason": reason})
    rules = []
    for r in ev.get("rules") or []:
        rule = {"kind": r["kind"]}
        if "barcode" in r:
            rule["product_name"] = name(r["barcode"])
        if "barcodes" in r:
            rule["product_names"] = [name(b) for b in r["barcodes"]]
        if "department" in r:
            rule["department"] = r["department"]
        if "facings" in r:
            rule["facings"] = r["facings"]
        if "fixture" in r:
            rule["fixture"] = r["fixture"]
        rules.append(rule)
    stopped = ev.get("stopped_by")
    return {
        "fixture": ev["fixture"], "state": ev["state"],
        "shelves": [{"shelf": s["shelf"], "eye_level": s["eye_level"], "products": [product(p) for p in s["products"]]}
                    for s in ev.get("shelves") or []],
        "earnings_order": earnings_order,
        "not_placed": not_placed, "rules": rules,
        "stopped_by": ({"kind": stopped["kind"], "why": stopped["why"],
                        **({"product_name": name(stopped["barcode"])} if "barcode" in stopped else {})}
                       if stopped else None),
        "elasticity": {k: v for k, v in (ev.get("elasticity") or {}).items() if k in ("value", "source", "why")},
        "extra_facings": ev.get("extra_facings"),
    }


def _names_in(f: dict) -> list:
    out = {p["product_name"] for s in f["shelves"] for p in s["products"]}
    out |= {p["product_name"] for p in f["not_placed"]}
    for r in f["rules"]:
        out |= set(r.get("product_names") or [])
        if r.get("product_name"):
            out.add(r["product_name"])
    if f["stopped_by"] and f["stopped_by"].get("product_name"):
        out.add(f["stopped_by"]["product_name"])
    return sorted(out, key=lambda n: (-len(n), n))


# ── Checking (FR-212) ────────────────────────────────────────────────────────

def check(raw: str, names: list, max_chars: int) -> dict:
    """Withheld whole on any failure, so the three languages never disagree."""
    try:
        answer = json.loads(raw)
    except (ValueError, TypeError):
        return {"accepted": False, "text": None, "withheld_because": "did_not_parse"}
    if not isinstance(answer, dict) or any(not isinstance(answer.get(lang), str) or not answer[lang].strip()
                                           for lang in LANGUAGES):
        return {"accepted": False, "text": None, "withheld_because": "did_not_parse"}
    text = {lang: answer[lang].strip() for lang in LANGUAGES}
    if any(len(t) > max_chars for t in text.values()):
        return {"accepted": False, "text": None, "withheld_because": "too_long"}
    for t in text.values():
        rest = t
        for n in sorted(names, key=lambda n: (-len(n), n)):     # longest first: "Cola 1.5L" before "Cola"
            rest = rest.replace(n, "")
        if DIGIT.search(rest):
            return {"accepted": False, "text": None, "withheld_because": "stated_a_figure"}
    return {"accepted": True, "text": text, "withheld_because": None}


# ── The snapshot (ADR-039 Decision 5) ────────────────────────────────────────

def folder(snapshots_root: Path, day: str) -> Path:
    return Path(snapshots_root) / day / FOLDER


def read(snapshots_root: Path, day: str) -> Optional[dict]:
    """The night's sealed explanations, or None when nothing was sealed for that night."""
    manifest = folder(snapshots_root, day) / "_manifest.json"
    if not manifest.exists():
        return None
    sealed = folder(snapshots_root, day) / "explanations.json"
    return {"on_day": day, "explanations": json.loads(sealed.read_text(encoding="utf-8")) if sealed.exists() else {},
            "manifest": json.loads(manifest.read_text(encoding="utf-8"))}


def _previous(snapshots_root: Path, day: str) -> Optional[dict]:
    """The most recent earlier night's snapshot, and only that one: each is complete on its own."""
    root = Path(snapshots_root)
    days = sorted((p.name for p in root.iterdir() if p.is_dir() and p.name < day
                   and (p / FOLDER / "_manifest.json").exists()), reverse=True) if root.is_dir() else []
    return read(root, days[0]) if days else None


def _write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _prompt(policy) -> tuple:
    text = (ROOT / policy.shelf_explanation_prompt).read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def _names(inputs) -> dict:
    return {p["barcode"]: p.get("product_name") for p in inputs.products or [] if p.get("barcode")}


def live_step(inputs, *, snapshots_root: Path, key: Optional[str], transport: Transport, now: datetime,
              clock: Callable[[], float] = time.monotonic) -> dict:
    """Ask for tonight's explanations and seal them. Publish mode only (run.py decides).

    Writes nothing without a key, so the absence of the night's snapshot is what says so, live and
    in reproduction alike. With a key it always writes the manifest. Merge never replace: a plan
    already explained tonight is not asked again.
    """
    from src.engine import shelf_plan
    if not key:
        return {"skipped": "no_model_key", "requests_made": 0}
    plan = shelf_plan.run(inputs)
    if plan.status != "available":
        return {"skipped": plan.unavailable_reason, "requests_made": 0}
    policy, day = inputs.policy, plan.extras["plan_date"]
    sealed = read(snapshots_root, day) or {"explanations": {}, "manifest": {"runs": []}}
    explanations, manifest = dict(sealed["explanations"]), sealed["manifest"]
    manifest.setdefault("runs", [])
    previous = _previous(snapshots_root, day)
    earlier = {}
    for record in ((previous or {}).get("explanations") or {}).values():
        if record.get("accepted"):
            earlier.setdefault((record["inputs_digest"], record["model"], record["prompt_sha256"]),
                               {**record, "reused_from": record.get("reused_from") or previous["on_day"]})
    system, prompt_sha = _prompt(policy)
    budget = max(0, policy.shelf_explanation_request_ceiling - sum(r.get("requests_made", 0) for r in manifest["runs"]))
    deadline = clock() + policy.shelf_explanation_time_budget_s
    names = _names(inputs)
    run = {"requested_at": now.isoformat(), "model": policy.boost_model, "prompt": policy.shelf_explanation_prompt,
           "prompt_sha256": prompt_sha, "ceiling": policy.shelf_explanation_request_ceiling, "requests_made": 0,
           "reused": 0, "not_asked": [], "completed": False, "error": None}
    stopped = False
    for entry in (e.to_dict() for e in plan.entries):
        if entry["id"] in explanations:
            continue
        f = facts(entry, names)
        digest = facts_digest(f)
        reuse = earlier.get((digest, policy.boost_model, prompt_sha))
        if reuse is not None:
            explanations[entry["id"]] = {**reuse, "plan_entry_id": entry["id"], "fixture": f["fixture"]}
            run["reused"] += 1
            continue
        if stopped or budget <= 0 or clock() > deadline:
            why = "a_request_failed" if stopped else "ceiling_reached" if budget <= 0 else "time_budget_spent"
            run["not_asked"].append({"fixture": f["fixture"], "why": why})
            continue
        try:
            raw = ask({"system": system, "user": json.dumps(f, ensure_ascii=False, sort_keys=True)},
                      model=policy.boost_model, key=key, transport=transport,
                      max_tokens=policy.shelf_explanation_max_tokens)
        except ModelUnavailable as err:
            run["error"], stopped = str(err), True                    # NFR-077: no more asking tonight
            run["not_asked"].append({"fixture": f["fixture"], "why": "a_request_failed"})
            continue
        budget -= 1
        run["requests_made"] += 1
        result = check(raw, _names_in(f), policy.shelf_explanation_max_chars)
        explanations[entry["id"]] = {
            "plan_entry_id": entry["id"], "fixture": f["fixture"], "model": policy.boost_model,
            "prompt": policy.shelf_explanation_prompt, "prompt_sha256": prompt_sha, "requested_at": now.isoformat(),
            "inputs_digest": digest, **result, "reused_from": None,
            # Kept for audit, never shown and never used: what the model said when it was withheld.
            "raw": raw[:2000] if not result["accepted"] else None}
        _write(folder(snapshots_root, day) / "explanations.json", explanations)
    run["completed"] = not stopped and not run["not_asked"]
    manifest["runs"].append(run)
    _write(folder(snapshots_root, day) / "explanations.json", explanations)
    _write(folder(snapshots_root, day) / "_manifest.json", manifest)
    return {"skipped": None, "requests_made": run["requests_made"], "reused": run["reused"],
            "completed": run["completed"], "error": run["error"], "wrote": True}


# ── The capability (FR-214) ──────────────────────────────────────────────────

def run(inputs) -> CapabilityOutput:
    from src.engine import shelf_plan
    plan = shelf_plan.run(inputs)
    if plan.status != "available":                       # FR-214: with shelf_plan's own reason
        return CapabilityOutput.unavailable(CAP, SPEC, plan.unavailable_reason)
    status, reason = derive_status(CAP, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    sealed = inputs.shelf_explanations
    names = _names(inputs)
    published, counts = [], {"explained": 0, "withheld": 0, "out_of_date": 0, "not_written_tonight": 0, "reused": 0}
    for entry in (e.to_dict() for e in plan.entries):
        record = (sealed.get("explanations") or {}).get(entry["id"])
        out = {"plan_entry_id": entry["id"], "fixture": entry["evidence"]["fixture"], "text": None,
               "why_none": None, "withheld_because": None, "model": None, "prompt": None, "reused_from": None}
        if record is None:
            out["why_none"] = "not_written_tonight"
        elif record.get("inputs_digest") != facts_digest(facts(entry, names)):
            out["why_none"] = "out_of_date"                 # INV-097: never beside other facts
        elif not record.get("accepted"):
            out.update(why_none="withheld", withheld_because=record.get("withheld_because"))
        else:
            out.update(text=record["text"], model=record["model"], prompt=record["prompt"],
                       reused_from=record.get("reused_from"))
        counts["explained" if out["text"] else out["why_none"]] += 1
        counts["reused"] += bool(out["reused_from"])
        published.append(out)
    runs = (sealed.get("manifest") or {}).get("runs") or []
    counts["requests_made"] = sum(r.get("requests_made", 0) for r in runs)
    return CapabilityOutput(id=CAP, spec=SPEC, status="available", counts=counts,
                            thresholds=inputs.policy.as_dict()["shelf_explanation"],
                            extras={"plan_date": plan.extras["plan_date"], "explanations": published})
