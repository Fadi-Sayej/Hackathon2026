#!/usr/bin/env python3
"""check_order_signals.py — does F8 depend on exactly what it should? (rule 12, F8-S1 §20)

Each of F8's inputs is withheld AT SOURCE, the engine is run in print mode over a copy of a
fixture world, and the PUBLISHED artefact is read, never a capability's return value:

| Withheld | Must happen |
|---|---|
| the report days | order_quantity unavailable, with a monthly report right there to misuse |
| the deliveries | no net suggestion: a count cannot be carried without them |
| the store facts | no quantity at all |
| the market snapshots | suggestions still publish, unadjusted, and no disagreement is raised; F9's assortment gap goes unavailable |
| the boost picks | no boost, and zero calls to the model |
| an answered disagreement | it is not raised again (D-20) |
| the layout file | F12's layout_facts and shelf_plan unavailable (no_store_layout); without the report days the layout stays available and the plan does not (F12-S1 §20) |
| one product's width | the plan does not place it, and names it under "no width" (F12-S1 INV-086) |
| his arrangement records | over the planogram world: shelf_measurement unavailable (no_arrangement_recorded), the plan still published on the research value, saying why (FR-206, FR-208) |
| the owner-state pull | the same, as owner_state_unavailable: his arrangements are never read as absent (rule 10) |
| every fixture arranged at once | no net change published: there is no unchanged fixture to compare with (INV-092) |

It also proves the quantity and the boost fail independently: without the picks the quantity
still publishes, and without the report days the boost is still available.

The baseline must first show suggestions, a boost and a disagreement, or withholding an input
would remove nothing and every check would pass vacuously.

The world is built by tests/fixtures/order_signals/build.py on a fixed run date, and the
market is never collected (`skip_market=True`): a probe must not call Open-Meteo or rewrite
market-context.json. The disagreement question is published only while its policy flag is
on, and the flag is off until Task 5.14, so the probe turns it on for its own runs.

Blocking starts on its own. Until the committed artefact shows one of the capabilities it
covers (order_quantity, market_boost, assortment_gap) available on real data, a failure is
printed as a warning and the exit is 0: before then nothing the owner sees depends on them.
From that night on, a failure exits 1 and holds the artefact back.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "fixtures" / "order_signals"))

import src.engine.run as run_mod  # noqa: E402
from src.engine.policy import load_policy  # noqa: E402
import build as world  # noqa: E402
import importlib.util  # noqa: E402

# The planogram world (F12-S1 §20). Loaded under its own name: both worlds' builders are build.py.
_spec = importlib.util.spec_from_file_location("shelf_world", ROOT / "tests" / "fixtures" / "shelf_signals" / "build.py")
shelf_world = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shelf_world)

ARTEFACT = ROOT / "public" / "data" / "dashboard.json"


# ── What each case must show, as pure functions of the published artefact ────

def _cap(art: dict, cap_id: str) -> dict:
    return art["capabilities"][cap_id]


def _suggestions(art: dict) -> list:
    return _cap(art, "order_quantity")["entries"]


def _disagreements(art: dict) -> list:
    items = (_cap(art, "owner_questions").get("items") or [])
    return [q for q in items if q.get("fact") == "market_disagreement"]


def _boosted(art: dict) -> list:
    return [e for e in _suggestions(art) if (e["evidence"].get("boost") or {}).get("applied")]


def baseline_problems(art: dict) -> list:
    out = []
    if _cap(art, "order_quantity")["status"] != "available" or not _suggestions(art):
        out.append("the baseline publishes no suggestion, so withholding an input would remove nothing")
    if not [e for e in _suggestions(art) if e["evidence"]["kind"] == "net"]:
        out.append("the baseline has no net suggestion, so withholding the deliveries proves nothing")
    if not _boosted(art):
        out.append("the baseline applies no boost, so withholding the picks proves nothing")
    if not _disagreements(art):
        out.append("the baseline raises no disagreement, so withholding the market proves nothing")
    gap = _cap(art, "assortment_gap")
    if gap["status"] != "available" or not gap["entries"]:
        out.append("the baseline finds no assortment gap, so withholding the market proves nothing for F9")
    layout = _cap(art, "layout_facts")
    if layout["status"] != "available" or not layout.get("fixtures"):
        out.append("the baseline publishes no layout, so withholding the layout file proves nothing for F12")
    if not _placed(art, world.BOOSTED):
        out.append("the baseline plan does not place 7290001, so withholding its width proves nothing")
    return out


def _placed(art: dict, barcode: str) -> bool:
    plan = _cap(art, "shelf_plan")
    if plan["status"] != "available":
        return False
    return any(p["barcode"] == barcode for e in plan["entries"] for s in (e["evidence"].get("shelves") or [])
               for p in s["products"])


def withheld_width_problems(art: dict, barcode: str) -> list:
    plan = _cap(art, "shelf_plan")
    if _placed(art, barcode):
        return [f"without its width {barcode} was still placed: a width was estimated (F12-S1 INV-086)"]
    if plan["status"] != "available" or not any(barcode in e["evidence"]["unplaced"]["no_width"] for e in plan["entries"]):
        return [f"without its width {barcode} is not named under \"no width\" (F12-S1 FR-180)"]
    return []


def shelf_baseline_problems(art: dict) -> list:
    m = _cap(art, "shelf_measurement")
    if m["status"] != "available" or not any(a["status"] == "measured" for a in m.get("arrangements") or []):
        return ["the planogram world's baseline measures no arrangement, so withholding them proves nothing"]
    if (m.get("plan_uses") or {}).get("source") != "his_store":
        return ["the planogram world's baseline does not reach his own elasticity, so its withdrawal proves nothing"]
    return []


def withheld_measurement_problems(art: dict, reason: str) -> list:
    out = []
    m, plan = _cap(art, "shelf_measurement"), _cap(art, "shelf_plan")
    if m["status"] != "unavailable" or m["unavailable_reason"] != reason:
        out.append(f"shelf_measurement published {m['status']} ({m['unavailable_reason']}), not {reason}: "
                   "his arrangements were read as absent, or measured from nothing (F12-S1 FR-208)")
    uses = plan.get("elasticity") or {}
    if plan["status"] != "available" or uses.get("source") != "research" or uses.get("measurement_reason") != reason:
        out.append(f"without the measurement the plan published {plan['status']} using {uses}: it must stay up on the "
                   f"research value and say why (FR-206)")
    return out


def shelf_withheld_problems(art: dict, reason: str) -> list:
    out = []
    for cap_id in ("shelf_plan", "shelf_measurement"):
        cap = _cap(art, cap_id)
        if cap["status"] != "unavailable" or cap["unavailable_reason"] != reason:
            out.append(f"over the planogram world, without its input {cap_id} published {cap['status']} "
                       f"({cap['unavailable_reason']}), not {reason} (F12-S1 §20, FR-193, FR-208)")
    return out


def all_arranged_problems(art: dict) -> list:
    m = _cap(art, "shelf_measurement")
    published = [p for a in m.get("arrangements") or [] for p in a.get("products") or [] if p.get("net_change") is not None]
    reasons = {a.get("reason") for a in m.get("arrangements") or []}
    if published or reasons != {"no_unchanged_fixture"}:
        return [f"with every fixture arranged at once, {len(published)} net changes were published and the reasons "
                f"were {sorted(map(str, reasons))}: there is no yardstick (F12-S1 INV-092)"]
    return []


def withheld_layout_problems(art: dict) -> list:
    out = []
    for cap_id in ("layout_facts", "shelf_plan"):
        cap = _cap(art, cap_id)
        if cap["status"] != "unavailable" or cap["unavailable_reason"] != "no_store_layout":
            out.append(f"without the layout file {cap_id} published {cap['status']} ({cap['unavailable_reason']}): "
                       "the measurements were never recorded, and it must say so (F12-S1 FR-196, FR-193)")
    return out


def withheld_daily_problems(art: dict) -> list:
    cap = _cap(art, "order_quantity")
    if cap["status"] != "unavailable" or cap["unavailable_reason"] != "no_daily_sales" or cap["entries"]:
        return [f"without report days order_quantity published {cap['status']} ({cap['unavailable_reason']}) "
                f"with {len(cap['entries'])} entries: a monthly report must never stand in for them (INV-070)"]
    return []


def withheld_deliveries_problems(art: dict) -> list:
    net = [e["barcode"] for e in _suggestions(art) if e["evidence"]["kind"] == "net"]
    return [f"without deliveries {net} are still net: a count was carried across unknown deliveries (FR-149)"] if net else []


def withheld_facts_problems(art: dict) -> list:
    got = _suggestions(art)
    return [f"without the store facts {len(got)} quantities were published from a schedule or shelf life "
            f"nobody stated (INV-071)"] if got else []


def withheld_market_problems(art: dict) -> list:
    out = []
    if not _suggestions(art):
        out.append("without the market snapshots the suggestions vanished: the adjustment was wrongly required (FR-148)")
    if _boosted(art):
        out.append("without the market snapshots a boost was still applied, from nothing")
    if _disagreements(art):
        out.append("without the market snapshots a disagreement was still raised (AC-142)")
    gap = _cap(art, "assortment_gap")
    if gap["status"] != "unavailable" or gap["entries"]:
        out.append(f"without the market snapshots assortment_gap published {gap['status']} with "
                   f"{len(gap['entries'])} findings: they came from no market (F9-S1 AC-165)")
    return out


def withheld_picks_problems(art: dict, calls: int) -> list:
    out = []
    if _boosted(art):
        out.append("without the boost picks a boost was still applied: it came from no pick (ADR-035)")
    if calls:
        out.append(f"print mode called the model {calls} times: reproduction must never ask it (ADR-035)")
    if not _suggestions(art):
        out.append("without the boost picks the suggestions vanished: the boost was wrongly required (SCN-151)")
    return out


def answered_problems(art: dict, barcode: str) -> list:
    again = [q for q in _disagreements(art) if q["barcode"] == barcode]
    return [f"{barcode}'s disagreement was answered and raised again (D-20)"] if again else []


def independence_problems(without_picks: dict, without_daily: dict) -> list:
    out = []
    if _cap(without_picks, "market_boost")["status"] != "unavailable" or not _suggestions(without_picks):
        out.append("without the picks the boost must be unavailable while the quantity still publishes")
    if (_cap(without_daily, "order_quantity")["status"] != "unavailable"
            or _cap(without_daily, "market_boost")["status"] != "available"):
        out.append("without the report days the quantity must be unavailable while the boost stays available")
    if _cap(without_daily, "layout_facts")["status"] != "available":
        out.append("without the report days layout_facts must stay available: the layout needs no sales (D-30)")
    plan = _cap(without_daily, "shelf_plan")
    if plan["status"] != "unavailable" or plan["unavailable_reason"] != "no_daily_sales" or plan["entries"]:
        out.append(f"without the report days shelf_plan published {plan['status']} ({plan['unavailable_reason']}): "
                   "the plan waits for daily sales the way F8 does (D-30)")
    return out


# ── Running the engine over the world, with one input withheld ────────────────

@contextmanager
def _engine_as(owner):
    """The probe's own runs: the disagreement flag on, and a fixture owner state."""
    saved_policy, saved_owner = run_mod.load_policy, run_mod._pull_owner_state
    run_mod.load_policy = lambda: replace(load_policy(), order_publish_disagreement_questions=True)
    run_mod._pull_owner_state = lambda: owner
    try:
        yield
    finally:
        run_mod.load_policy, run_mod._pull_owner_state = saved_policy, saved_owner


def _run(paths: dict, owner=None) -> tuple:
    model = world.FakeModel()
    with _engine_as(owner or world.owner()):
        art = run_mod.run_engine(mode="print", skip_market=True, now=world.RUN_AT, boost_transport=model,
                                 **paths)["artefact"]
    return art, model.calls


def _copy(built: Path, into: Path) -> dict:
    shutil.copytree(built, into)
    return world.roots(into)


def _drop_deliveries(folder: Path) -> None:
    """The same reports with the כניסות מלאי column gone, as a POS export without it arrives."""
    for path in folder.glob("*.csv"):
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        col = lines[0].split(",").index("כניסות מלאי")
        path.write_text("﻿" + "\n".join(",".join(c for i, c in enumerate(line.split(",")) if i != col)
                                             for line in lines) + "\n", encoding="utf-8")


def probe(tmp: Path) -> tuple:
    """(problems, lines to print). Every case runs over its own copy of the world."""
    built = tmp / "world"
    world.build(built)
    problems, done = [], []

    baseline, _ = _run(world.roots(built))
    problems += baseline_problems(baseline)
    done.append(f"baseline: {len(_suggestions(baseline))} suggestions, {len(_boosted(baseline))} boosted, "
                f"{len(_disagreements(baseline))} disagreement")

    paths = _copy(built, tmp / "no_daily")
    for path in paths["daily_sales_dir"].glob("*.csv"):
        path.unlink()
    no_daily, _ = _run(paths)
    problems += withheld_daily_problems(no_daily)
    done.append("withholding the report days → order_quantity unavailable (no_daily_sales), monthly unused")

    paths = _copy(built, tmp / "no_deliveries")
    _drop_deliveries(paths["daily_sales_dir"])
    problems += withheld_deliveries_problems(_run(paths)[0])
    done.append("withholding the deliveries  → no net suggestion")

    paths = _copy(built, tmp / "no_facts")
    paths["store_facts_path"].unlink()
    problems += withheld_facts_problems(_run(paths)[0])
    done.append("withholding the store facts → no quantity")

    paths = _copy(built, tmp / "no_market")
    shutil.rmtree(paths["snapshots_root"])
    paths["snapshots_root"].mkdir()
    problems += withheld_market_problems(_run(paths)[0])
    done.append("withholding the market      → suggestions unadjusted, no disagreement")

    paths = _copy(built, tmp / "no_picks")
    for folder in paths["snapshots_root"].glob("*/boost_picks"):
        shutil.rmtree(folder)
    no_picks, calls = _run(paths)
    problems += withheld_picks_problems(no_picks, calls)
    done.append("withholding the boost picks → no boost, no model call")

    paths = _copy(built, tmp / "no_layout")
    paths["store_layout_path"].unlink()
    problems += withheld_layout_problems(_run(paths)[0])
    done.append("withholding the layout file → layout_facts and shelf_plan unavailable (no_store_layout)")

    paths = _copy(built, tmp / "no_width")
    layout = paths["store_layout_path"]
    layout.write_text("".join(line for line in layout.read_text(encoding="utf-8").splitlines(keepends=True)
                              if f'"{world.BOOSTED}"' not in line), encoding="utf-8")
    problems += withheld_width_problems(_run(paths)[0], world.BOOSTED)
    done.append("withholding one width        → that product is not placed, and is named")

    problems += _shelf_cases(tmp, done)

    answered = world.owner(answered=[world.SLOW])
    problems += answered_problems(_run(world.roots(built), owner=answered)[0], world.SLOW)
    done.append("an answered disagreement    → not raised again")

    problems += independence_problems(no_picks, no_daily)
    done.append("quantity and boost fail independently; the layout needs no sales")
    return problems, done


# The capabilities this probe covers whose publication on real data comes from F8 or F9.
# owner_questions is not one: F5's cost questions keep it available with no F8 input at all.
PROBED = ("order_quantity", "market_boost", "assortment_gap")


def _shelf_run(paths: dict, owner) -> dict:
    with _engine_as(owner):
        return run_mod.run_engine(mode="print", skip_market=True, now=shelf_world.RUN_AT, **paths)["artefact"]


def _shelf_cases(tmp: Path, done: list) -> list:
    """F12-S1 §20 over the planogram world, which has the arrangements and history the order world lacks."""
    from datetime import timedelta
    from src.owner_state.model import OwnerState
    paths, w = shelf_world.write(tmp / "shelf")
    problems = shelf_baseline_problems(_shelf_run(paths, w["owner"]))
    done.append("planogram world: his elasticity measured, and the plan uses it")
    none = OwnerState.from_dict({"status": "available", "pulled_at": "t", "outcomes": {}})
    problems += withheld_measurement_problems(_shelf_run(paths, none), "no_arrangement_recorded")
    done.append("withholding his arrangements  → no measurement, the plan on 0.17 and saying why")
    problems += withheld_measurement_problems(_shelf_run(paths, OwnerState.unavailable("no_credentials")),
                                              "owner_state_unavailable")
    done.append("withholding the owner state   → owner_state_unavailable, never 'no arrangements'")
    day = w["first_day"] + timedelta(days=150)
    every = dict(shelf_world.arrangement_record(
        f, day, {shelf_world.barcode(f, n): {"shelf": 1, "facings": 2, "eye_level": True} for n in range(1, 7)})
        for f in shelf_world.FIXTURES)
    problems += all_arranged_problems(_shelf_run(paths, OwnerState.from_dict(
        {"status": "available", "pulled_at": "t", "outcomes": every})))
    done.append("every fixture arranged at once → no net change: no yardstick")

    # §20 row 1 over this world, where the measurement has something to lose.
    copy = _copy(tmp / "shelf", tmp / "shelf_no_daily")
    for path in Path(copy["daily_sales_dir"]).glob("*.csv"):
        path.unlink()
    problems += shelf_withheld_problems(_shelf_run({**paths, **copy}, w["owner"]), "no_daily_sales")
    done.append("withholding the report days  → plan and measurement unavailable (no_daily_sales)")
    copy = _copy(tmp / "shelf", tmp / "shelf_no_layout")
    Path(copy["store_layout_path"]).unlink()
    problems += shelf_withheld_problems(_shelf_run({**paths, **copy}, w["owner"]), "no_store_layout")
    done.append("withholding the layout file  → plan and measurement unavailable (no_store_layout)")
    return problems


def blocking() -> bool:
    """From the first night the committed artefact carries any of them on real data, on.

    It used to wait for order_quantity alone, which needs daily reports. After D-23 none is
    coming, while F9's assortment gap has been available on real data since the 2026-09-29
    nightly: the probe would have warned forever about a capability the owner can see.
    """
    try:
        art = json.loads(ARTEFACT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    caps = art.get("capabilities") or {}
    return any((caps.get(cap_id) or {}).get("status") == "available" for cap_id in PROBED)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        problems, done = probe(Path(tmp))
    if not problems:
        for line in done:
            print(f"OK    {line}")
        return 0
    block = blocking()
    for line in problems:
        print(f"{'FAIL' if block else '::warning::F8 probe'}  {line}")
    if not block:
        print(f"none of {', '.join(PROBED)} is available on real data yet, so this warns rather than blocks")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
