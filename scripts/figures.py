#!/usr/bin/env python3
"""figures.py — print every figure the engine published, and compute none of them.

The PRD's own banner says «لا تقرأ هذه الأرقام من الورق — شغّل `npm run figures`». This is
that command. It runs the engine in print mode and reads `artefact['figures']`.

It replaces `scripts/print_figures.py`, which computed all 46 figures a SECOND time. That
second implementation disagreed with the engine on F1's ceiling until ADR-015 — 18% against
26% — and nothing would have said which was right. One number, one implementation.

`--population whole` suppresses the catalogue hand-off so every figure counts over the
entire catalogue. D-14 forbids putting a figure that depends on automatic withdrawal in
front of the owner until GAP-009 closes, and this is where those figures come from.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engine.run import run_engine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--skip-market", action="store_true")
    parser.add_argument("--population", choices=("living", "whole"), default="living",
                        help="'whole' counts over the entire catalogue (D-14)")
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
    unavailable = sorted(
        f"{cap_id}: {cap.get('unavailable_reason')}"
        for cap_id, cap in (artefact.get("capabilities") or {}).items()
        if cap.get("status") == "unavailable"
    )

    payload = {
        "population": args.population,
        "generated_at": artefact.get("generated_at"),
        # Checkpoint 3 / AC-127: "reproduced" means the same inputs produced the same
        # output, not that the numbers look similar. Without this the comparison is by eye.
        "inputs_digest": artefact.get("inputs_digest"),
        "run": artefact.get("run", {}).get("status"),
        "vintages": artefact.get("vintages"),
        "figures": figures,
        "missing": missing,
        "unavailable": unavailable,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_human(payload)

    if missing or unavailable:
        for name in missing:
            print(f"FAIL  {name} has no value", file=sys.stderr)
        for line in unavailable:
            print(f"FAIL  {line}", file=sys.stderr)
        return 1
    return 0


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


if __name__ == "__main__":
    raise SystemExit(main())
