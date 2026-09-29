#!/usr/bin/env python3
"""figures.py — print every figure the engine published, and compute none of them.

The PRD's own banner says «لا تقرأ هذه الأرقام من الورق — شغّل `npm run figures`». This is
that command. It runs the engine in print mode and reads `artefact['figures']`.

It replaces `scripts/print_figures.py`, which computed all 46 figures a SECOND time. That
second implementation disagreed with the engine on F1's ceiling until ADR-015 — 18% against
26% — and nothing would have said which was right. One number, one implementation.

The population counted over comes from policy (`published_population`, ADR-020), so this
command reproduces what was actually published. It defaulted to `living` while the engine
published `whole`, which made 22 of 46 figures disagree with the committed artefact —
several by roughly 2x — while still exiting 0. Measured on a fresh clone; see
docs/reviews/checkpoint-3-reproduction.md.

`--population` still overrides, either way, for comparing the two. D-14 forbids putting a
figure that depends on automatic withdrawal in front of the owner until GAP-009 closes,
which is why the policy currently says `whole`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engine.run import run_engine  # noqa: E402

# Unavailability that says nothing about whether the figures reproduce. A reader without
# the service account cannot compute these and never could; that is not a failure of the
# data or of the engine, and reporting it as one is how a judge concludes on 12/9 that the
# numbers do not reproduce.
_CREDENTIAL_GATED = frozenset({"answer_storage_unavailable"})

# Capabilities that register no figure at all (F8, Phase 5): their suggestions are advice,
# not counts. §11.6 exits 1 when a registered figure is unavailable, and theirs being
# unavailable loses none; they are unavailable on every machine without the model key and
# the daily reports, so counting them made this command exit 1 everywhere.
# tests/engine/test_figures_verdict.py checks this list against the committed artefact.
# F9's findings are observations carried on its entries (nights, stores), not a headline count.
_REGISTERS_NO_FIGURE = frozenset({"market_running_out", "market_boost", "order_quantity", "assortment_gap"})

# AC-127 is "on the same data". The market half is rebuilt on each machine from the committed
# snapshots, so a laptop's can be older than the artefact it is compared with, and then every
# figure that reads it differs with nothing said: 15 of 47 on 2026-09-28, until the market
# half was rebuilt from the same day's snapshot (F7 validation record). A NOTE, never a FAIL:
# the engine is not wrong, the comparison is, so the exit code is what it would have been.
COMMITTED_ARTEFACT = ROOT / "public" / "data" / "dashboard.json"
# The market half without the rest of the market chain: `figures` without --skip-market would
# also call Open-Meteo and rewrite the committed public/data/market-context.json.
_REBUILD_MARKET = ("python3 scripts/rehydrate_silver.py && python3 scripts/build_competitor_product_signals.py"
                   " && python3 scripts/build_product_matches.py")

# The same data needs the same engine too. On 2026-09-29 a fresh clone reproduced 33 of 47
# figures on the very market snapshot the artefact used: #250 had reclassified 57 shops in
# configs/store_types.yaml after the night's run. With the artefact's own configs and engine
# put back, the clone reproduced 46 of 47, and the market NOTE above had said nothing, because
# the dates matched. These are the paths whose change can move a figure: the configuration,
# every Python module under src/, the one script run.py imports (rehydrate_silver, in the
# market chain), and the two imports a fresh clone runs first. The browser computes no figure,
# and neither do the probes or this command.
_ENGINE_PATHS = ("configs", ":(glob)src/**/*.py", "scripts/rehydrate_silver.py",
                 "scripts/import_yomyom_pos.py", "scripts/import_yomyom_sales.py")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--skip-market", action="store_true")
    parser.add_argument("--population", choices=("living", "whole"), default=None,
                        help="override the published population; default is policy's "
                             "published_population, so figures reproduce what shipped")
    args = parser.parse_args()

    result = run_engine(mode="print", skip_market=args.skip_market,
                        population=args.population, now=datetime.now(timezone.utc))
    artefact = result.get("artefact")
    if artefact is None:
        print("FAIL  the engine published nothing; no figure can be reproduced", file=sys.stderr)
        return 1

    figures = artefact.get("figures") or {}
    # NFR-062 / §11.6: exit 1 NAMING the missing input, rather than printing a short list
    # and exiting 0 — a figure that silently disappears is how a count drifts unnoticed.
    #
    # A null `value` is not by itself missing. Figure.value is numeric, so a non-numeric
    # figure carries its content in `thresholds` — provenance.pos_as_of is a date, and
    # publishes {"value": null, "thresholds": {"value": "2026-08-02"}}. A figure is missing
    # only when it carries nothing anywhere.
    missing = sorted(name for name, f in figures.items() if _carries_nothing(f))
    # Two different sentences, and conflating them makes this command useless to anyone
    # outside the team. "We could not compute this from the data you have" is a
    # reproduction failure. "This needs a credential you were not given" is not — and on a
    # machine without the service account the second is ALWAYS true, so exiting 1 for it
    # tells a reader the figures do not reproduce when 40 of 41 reproduce exactly.
    blocked, gated, no_figure = [], [], []
    for cap_id, cap in sorted((artefact.get("capabilities") or {}).items()):
        if cap.get("status") != "unavailable":
            continue
        reason = cap.get("unavailable_reason")
        if cap_id in _REGISTERS_NO_FIGURE:
            no_figure.append(f"{cap_id}: {reason}")
        else:
            (gated if reason in _CREDENTIAL_GATED else blocked).append(f"{cap_id}: {reason}")

    engine_state = engine_changes_since_artefact(root=ROOT, artefact=COMMITTED_ARTEFACT)
    this_run = _competitor_snapshot(artefact)
    try:
        committed = _competitor_snapshot(json.loads(Path(COMMITTED_ARTEFACT).read_text(encoding="utf-8")))
        readable = True
    except (OSError, ValueError):
        committed, readable = None, False

    payload = {
        # What the run USED, not what was asked for. With no --population the CLI passes
        # None and run_engine resolves it from policy, so reporting args.population here
        # printed "None" for the one field a reader needs to compare artefacts by.
        "population": artefact.get("population"),
        "generated_at": artefact.get("generated_at"),
        # Checkpoint 3 / AC-127: "reproduced" means the same inputs produced the same
        # output, not that the numbers look similar. Without this the comparison is by eye.
        "inputs_digest": artefact.get("inputs_digest"),
        "run": artefact.get("run", {}).get("status"),
        "vintages": artefact.get("vintages"),
        "figures": figures,
        "missing": missing,
        "unavailable": blocked,
        "needs_credentials": gated,
        "registers_no_figure": no_figure,
        "market_snapshot": {"this_run": this_run, "committed": committed},
        "engine_since_artefact": engine_state,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_human(payload)

    for line in gated:
        print(f"NOTE  {line} — needs a credential this machine does not have; every other "
              f"figure is unaffected", file=sys.stderr)
    for line in no_figure:
        print(f"NOTE  {line} — registers no figure; every figure is unaffected", file=sys.stderr)
    market_note = _market_note(figures, this_run, committed, readable)
    if market_note:
        print(f"NOTE  {market_note}", file=sys.stderr)
    engine_note = _engine_note(engine_state)
    if engine_note:
        print(f"NOTE  {engine_note}", file=sys.stderr)
    if missing or blocked:
        for name in missing:
            print(f"FAIL  {name} has no value", file=sys.stderr)
        for line in blocked:
            print(f"FAIL  {line}", file=sys.stderr)
        return 1
    return 0


def engine_changes_since_artefact(*, root: Path = ROOT, artefact: Path = COMMITTED_ARTEFACT) -> dict:
    """Whether the engine or its configuration changed since the committed artefact was built.

    `{state, built_from, changed, reason}`, with state 'same', 'changed' or 'unknown'. The
    nightly checks out main, runs the engine and commits the artefact on top, so the artefact
    was built from the parent of the commit that last committed it. That parent is compared
    with the working tree, so an uncommitted edit counts as much as a merged one. (If a merge
    lands during the run, the nightly rebases onto it, and the parent is then newer than the
    code the engine ran. That window is the length of one run.)
    """
    def git(*args) -> str:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                              check=True).stdout.strip()

    unknown = {"state": "unknown", "built_from": None, "changed": []}
    try:
        if git("rev-parse", "--is-shallow-repository") == "true":
            return {**unknown, "reason": "this is a shallow clone, without the commit that built the "
                                         "artefact (git fetch --unshallow to check)"}
        path = Path(artefact).resolve().relative_to(Path(git("rev-parse", "--show-toplevel")).resolve())
        if git("status", "--porcelain", "--", str(path)):
            return {**unknown, "reason": f"{path} has uncommitted changes, so it is not the published "
                                         f"artefact"}
        made = git("log", "-1", "--format=%H", "--", str(path))
        built_from = git("rev-parse", "--short", f"{made}^") if made else ""
        if not built_from:
            return {**unknown, "reason": f"no commit before the one that committed {path}"}
        changed = git("diff", "--name-only", built_from, "--", *_ENGINE_PATHS).splitlines()
    except (subprocess.CalledProcessError, OSError, ValueError) as exc:
        return {**unknown, "reason": f"git could not say ({type(exc).__name__})"}
    return {"state": "changed" if changed else "same", "built_from": built_from,
            "changed": changed, "reason": None}


def _engine_note(state: dict):
    if state["state"] == "same":
        return None
    if state["state"] == "unknown":
        return (f"whether the engine changed since the committed artefact was built is unknown: "
                f"{state['reason']}")
    shown = state["changed"][:8]
    more = f" and {len(state['changed']) - len(shown)} more" if len(state["changed"]) > len(shown) else ""
    return (f"the engine or its configuration changed since the committed artefact was built from "
            f"{state['built_from']}: {', '.join(shown)}{more}. Figures that read them can differ from "
            f"the published ones until the next nightly publishes them. To compare with the published "
            f"artefact itself, run this on git checkout {state['built_from']}")


def _competitor_snapshot(artefact: dict):
    return ((artefact.get("vintages") or {}).get("competitor") or {}).get("snapshot_date")


def _market_note(figures: dict, this_run, committed, readable: bool):
    """None when this run read the published market snapshot; otherwise what differs and why."""
    if not readable:
        return (f"could not read {COMMITTED_ARTEFACT}, so whether this run's market snapshot is the "
                f"published one is unknown")
    if this_run == committed:
        return None
    reading = sorted(name for name, f in figures.items() if "competitor" in (f.get("inputs") or []))
    return (f"this run's market snapshot is {this_run or 'none'} and the committed artefact's is "
            f"{committed or 'none'}, so the {len(reading)} figures that read it can differ from the "
            f"published ones: {', '.join(reading)}. To compare on the same data, rebuild the market "
            f"half from the committed snapshots: {_REBUILD_MARKET}. Not by running figures without "
            f"--skip-market, which also rewrites public/data/market-context.json")


def _carries_nothing(figure: dict) -> bool:
    if figure.get("value") is not None:
        return False
    thresholds = figure.get("thresholds") or {}
    return all(v is None for v in thresholds.values()) if thresholds else True


def _print_human(payload: dict) -> None:
    sales = (payload.get("vintages") or {}).get("sales") or {}
    print("=" * 68)
    print("  SmartShelf — الأرقام، محسوبة الآن من البيانات")
    print("=" * 68)
    print(f"  المجموعة:        {payload['population']}")
    print(f"  البيانات وُلّدت:  {payload['generated_at']}")
    print(f"  شهور المبيعات:   {sales.get('first')} … {sales.get('last')}")
    print(f"  حالة التشغيل:    {payload['run']}")
    print(f"  بصمة المدخلات:   {(payload.get('inputs_digest') or '')[:16]}")
    print("-" * 68)
    by_capability: dict = {}
    for name, figure in payload["figures"].items():
        capability, _, leaf = name.partition(".")
        by_capability.setdefault(capability, []).append((leaf, figure))
    for capability in sorted(by_capability):
        print(f"\n  {capability}")
        for leaf, figure in sorted(by_capability[capability]):
            value = figure.get("value")
            if value is None:
                # the non-numeric case: show what it does carry rather than a dash
                carried = (figure.get("thresholds") or {}).get("value")
                shown = str(carried) if carried is not None else "—"
            else:
                shown = f"{value:,}" if isinstance(value, (int, float)) else str(value)
            print(f"    {leaf:<34} {shown:>12}  {figure.get('unit','')}")
    if payload["unavailable"]:
        print("\n  غير متاح:")
        for line in payload["unavailable"]:
            print(f"    {line}")
    if payload.get("needs_credentials"):
        print("\n  يحتاج صلاحية غير متوفرة على هذا الجهاز (بقية الأرقام غير متأثرة):")
        for line in payload["needs_credentials"]:
            print(f"    {line}")
    if payload.get("registers_no_figure"):
        print("\n  غير متاح، ولا ينشر أي رقم مسجَّل (الأرقام كلها غير متأثرة):")
        for line in payload["registers_no_figure"]:
            print(f"    {line}")


if __name__ == "__main__":
    raise SystemExit(main())
