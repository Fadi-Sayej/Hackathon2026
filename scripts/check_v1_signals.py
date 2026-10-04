#!/usr/bin/env python3
"""check_v1_signals.py — does each capability actually depend on what it declares?

The registry says which inputs each capability requires, and `derive_status` turns that
list into a published status. This proves the claim across the real boundary: the engine is
driven over a copy of the data with one input withheld at source, and the PUBLISHED artefact
is read — never a capability's return value.

Two failures are possible and both are silent without this:

  - a capability declares an input it does not actually need, so withholding it takes a
    working signal off the owner's screen for no reason;
  - a capability needs an input it does NOT declare, so on a day that input is missing it
    publishes a figure computed from nothing and calls it available.

The second is CLAUDE.md rule 12 in its exact form. It has happened four times here.

Replaced the reorder-era probes in `scripts/check_signals_live.mjs`, which exercised the
reorder engine. Both were removed on 2026-09-24 (Phase 4, #77 and ADR-028).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.engine.run as run_mod  # noqa: E402
from src.engine.registry import CAPABILITIES  # noqa: E402
from src.common.store import INVENTORY_TABLE, PRODUCTS_TABLE

# How to withhold each input AT SOURCE. Nothing here reaches into EngineInputs: the point is
# to cross inputs.py and run.py, which is where four signals in this repository were lost.
SILVER_FILES = {
    "products": [PRODUCTS_TABLE],
    "inventory": [INVENTORY_TABLE],
    "sales_summary": ["sales_summary.parquet", "sales_monthly.parquet"],
    "window": ["sales_summary.parquet", "sales_monthly.parquet"],
}
# The market half is not in silver. run_engine reads observations from `signals_dir` and
# matches from `matches_path` (run.py), so each is withheld by pointing that argument at
# nothing: an empty signals directory has no signal file to read, and a matches path that does
# not exist is a missing table. Until 2026-09-28 neither was withheld, so competitor_position's
# two market inputs went unprobed (F3 validation record, "boundary probe" row).
MARKET_SOURCES = {
    "observations": "signals_dir",
    "matches": "matches_path",
}
WITHHELD = sorted(SILVER_FILES.keys() | MARKET_SOURCES.keys())

# Inputs a registered capability requires that THIS probe does not withhold, each with the
# probe that withholds it instead. An input that is required and on neither list is unprobed,
# and the probe refuses to pass (unprobed_inputs, tests/test_check_v1_signals.py).
PROBED_ELSEWHERE = {
    # F8 (ADR-030 … ADR-035). Real data has no daily report and no store facts, so on it these
    # capabilities are unavailable at baseline and withholding here would prove nothing.
    # check_order_signals.py withholds each over the fixture world it builds.
    "sales_daily": "scripts/check_order_signals.py",
    "store_facts": "scripts/check_order_signals.py",
    "running_out": "scripts/check_order_signals.py",
    # F9-S1: replayed from the same market snapshots as running_out, so withheld with them.
    "market_recent": "scripts/check_order_signals.py",
    "boost_picks": "scripts/check_order_signals.py",
    # F12-S1 §20: no store has a layout file, so on real data it is withheld at baseline.
    "store_layout": "scripts/check_order_signals.py",
}

failures: list[str] = []


def unprobed_inputs(withheld=None, elsewhere=None) -> list:
    """Required inputs that no probe withholds. Empty, or rule 12 can pass unexamined."""
    withheld = set(WITHHELD if withheld is None else withheld)
    elsewhere = set(PROBED_ELSEWHERE if elsewhere is None else elsewhere)
    required = {key for cap in CAPABILITIES.values() for key in cap.requires}
    return sorted(required - withheld - elsewhere)


def withheld_sources(input_name: str, source_silver: Path, workdir: Path) -> dict:
    """run_engine's keyword arguments for a run with `input_name` withheld at source."""
    workdir.mkdir(parents=True, exist_ok=True)
    silver = workdir / "silver"
    shutil.copytree(source_silver, silver)
    for name in SILVER_FILES.get(input_name, []):
        (silver / name).unlink(missing_ok=True)
    sources = {"silver_dir": silver}
    if MARKET_SOURCES.get(input_name) == "signals_dir":
        empty = workdir / "signals"
        empty.mkdir()
        sources["signals_dir"] = empty
    elif MARKET_SOURCES.get(input_name) == "matches_path":
        sources["matches_path"] = workdir / "product_matches.parquet"
    return sources


def _run(silver_dir: Path, **sources) -> dict:
    result = run_mod.run_engine(mode="print", skip_market=True, silver_dir=silver_dir,
                                sales_dir=ROOT / "does-not-exist",
                                now=datetime.now(timezone.utc), **sources)
    return result["artefact"]["capabilities"]


def main() -> int:
    source = run_mod.SILVER_DIR
    if not (source / PRODUCTS_TABLE).exists():
        print(f"FAIL  no silver tables under {source}: import the POS export first", file=sys.stderr)
        return 1

    unprobed = unprobed_inputs()
    if unprobed:
        print(f"FAIL  required but withheld by no probe: {', '.join(unprobed)} — add each to "
              f"SILVER_FILES, MARKET_SOURCES or PROBED_ELSEWHERE", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        whole_dir = Path(tmp) / "whole"
        shutil.copytree(source, whole_dir)
        whole = _run(whole_dir)

        available = sorted(cid for cid, c in whole.items() if c["status"] == "available")
        print(f"baseline: {len(available)} of {len(whole)} capabilities available")

        for input_name in WITHHELD:
            dependants = sorted(cid for cid, cap in CAPABILITIES.items() if input_name in cap.requires)
            if not dependants:
                continue
            withheld = _run(**withheld_sources(input_name, source, Path(tmp) / f"without_{input_name}"))

            silent = [cid for cid in dependants if whole[cid]["status"] != "available"]
            for cid in dependants:
                if whole[cid]["status"] != "available":
                    continue                      # it was not speaking to begin with
                if withheld[cid]["status"] != "unavailable":
                    failures.append(
                        f"{cid} declares '{input_name}' but still published without it — "
                        f"either the requires list is wrong or the capability is reading "
                        f"something it did not declare (rule 12)")

            # …and the ones that do NOT declare it must be untouched.
            for cid, cap in sorted(CAPABILITIES.items()):
                if input_name in cap.requires or whole[cid]["status"] != "available":
                    continue
                if withheld[cid]["status"] != "available":
                    failures.append(
                        f"{cid} does not declare '{input_name}' yet went "
                        f"{withheld[cid]['status']} ({withheld[cid]['unavailable_reason']}) "
                        f"without it — an undeclared dependency")

            proven = [cid for cid in dependants if cid not in silent]
            # Named, not folded in: a dependant unavailable at baseline proves nothing about
            # this input, and the line must not read as though it did.
            note = f" (not available at baseline, so unproven: {', '.join(silent)})" if silent else ""
            print(f"withholding {input_name:14} → {', '.join(proven) or 'nothing'} unavailable, "
                  f"others unaffected{note}")

        # The stock-count date is not a declared input, so the loop above cannot reach
        # it: it is a rule-level unavailability, derived from vintages.pos.as_of rather
        # than from a file landing. It still needs a probe, and for the reason rule 12
        # exists — the real silver layer always carries `_as_of`, so the guard that
        # refuses to reconcile without it would never fire in CI, and nothing would
        # notice if it stopped working. Withheld at source like everything else here.
        undated_dir = Path(tmp) / "without_as_of"
        shutil.copytree(source, undated_dir)
        inventory = undated_dir / INVENTORY_TABLE
        table = pq.read_table(inventory)
        dated = [c for c in table.schema.names if c in ("_as_of", "_as_of_source")]
        if not dated:
            failures.append(f"{INVENTORY_TABLE} carries no _as_of, so this probe "
                            "proves nothing — re-import the POS export")
        else:
            pq.write_table(table.select([c for c in table.schema.names if c not in dated]),
                           inventory, compression="snappy")
            undated = _run(undated_dir)
            recon = undated["reconciliation"]
            if whole["reconciliation"]["status"] == "available":
                if recon["status"] != "unavailable" or recon["unavailable_reason"] != "unknown_stock_date":
                    failures.append(
                        f"reconciliation published {recon['status']} "
                        f"({recon['unavailable_reason']}) with no stock-count date — it must "
                        f"refuse rather than reconcile against every month (rule 12)")
            for cid in sorted(CAPABILITIES):
                if cid == "reconciliation" or whole[cid]["status"] != "available":
                    continue
                if undated[cid]["status"] != "available":
                    failures.append(
                        f"{cid} went {undated[cid]['status']} "
                        f"({undated[cid]['unavailable_reason']}) without the stock-count date, "
                        f"which it does not use")
            print("withholding _as_of         → reconciliation unavailable, others unaffected")

    for line in failures:
        print(f"FAIL  {line}", file=sys.stderr)
    if failures:
        return 1
    print("\nOK    every capability depends on exactly what it declares")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
