#!/usr/bin/env python3
"""Prove the two halves of SPEC-002 fail independently, across the real boundary.

SPEC-002 §11: when the sales reports do not arrive, detection is unavailable and the hygiene
signals are unaffected. ADR-014 makes that a computed consequence of two `requires` lists. This
probe shows the computation survives contact with `inputs.py` and `run.py` — the place where a
signal quietly stops arriving (CLAUDE.md rule 12). It runs the engine twice over copies of the
data and reads the published artefact, never a module's return value."""
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.engine.run as run_mod


def _fail(message: str) -> None:
    print(f"FAIL  {message}")
    sys.exit(1)


def _run(silver_dir: Path, sales_dir: Path) -> dict:
    result = run_mod.run_engine(mode="print", skip_market=True, silver_dir=silver_dir,
                                sales_dir=sales_dir, now=datetime.now(timezone.utc))
    return result["artefact"]["capabilities"]


def _ids(capability: dict) -> set:
    return {e["id"] for e in capability["entries"]}


def _total(capability: dict) -> int:
    return sum(v for v in capability["counts"].values() if isinstance(v, int))


def main() -> None:
    if not (run_mod.SILVER_DIR / "yomyom_products.parquet").exists():
        _fail(f"no silver tables under {run_mod.SILVER_DIR}: import the POS export first "
              f"(python3 scripts/import_yomyom_pos.py --input <csv>)")

    with tempfile.TemporaryDirectory() as tmp:
        whole_silver = Path(tmp) / "silver_whole"
        withheld_silver = Path(tmp) / "silver_withheld"
        no_reports = Path(tmp) / "sales_none"
        shutil.copytree(run_mod.SILVER_DIR, whole_silver)
        shutil.copytree(run_mod.SILVER_DIR, withheld_silver)
        no_reports.mkdir()                       # the seven monthly reports simply did not arrive
        # ...and so the tables DERIVED from them do not exist either. Withholding only the
        # raw reports proves nothing: import_sales leaves a previous run's sales_summary /
        # sales_monthly in place (it reports monthly_rows: 0 and writes nothing), so
        # load_inputs would still find evidence and detection would still run. Removing the
        # derived tables here is what "the reports did not arrive" means for a clean run.
        # NOTE: on a real pipeline the stale tables DO survive a missing report day, and
        # detection then runs on last week's evidence without saying so. That is a separate
        # finding, raised for the architect; it is not what this probe measures.
        for derived in ("sales_summary.parquet", "sales_monthly.parquet"):
            (withheld_silver / derived).unlink(missing_ok=True)

        whole = _run(whole_silver, run_mod.SALES_DIR)
        withheld = _run(withheld_silver, no_reports)

    recon_w, hyg_w = whole["reconciliation"], whole["hygiene"]
    if recon_w["status"] != "available" or not recon_w["counts"].get("flagged"):
        _fail(f"detection should be available with findings on the real data, got "
              f"{recon_w['status']} / {recon_w['counts']}")
    if hyg_w["status"] != "available" or not _total(hyg_w):
        _fail(f"hygiene should be available with findings on the real data, got "
              f"{hyg_w['status']} / {hyg_w['counts']}")

    recon, hyg = withheld["reconciliation"], withheld["hygiene"]
    if recon["status"] != "unavailable" or recon["unavailable_reason"] != "no_sales_evidence":
        _fail(f"detection must be unavailable without the reports, got {recon['status']} "
              f"/ {recon['unavailable_reason']}")
    if recon["entries"]:
        _fail(f"an unavailable capability published {len(recon['entries'])} entries")
    if hyg["status"] != "available":
        _fail(f"hygiene must survive a missing sales report, got {hyg['status']} "
              f"/ {hyg['unavailable_reason']} — this is the coupling SPEC-002 §11 forbids")
    if not _total(hyg):
        _fail("hygiene is available but publishes nothing without the reports")
    lost = _ids(hyg_w) - _ids(hyg)
    if lost:
        _fail(f"{len(lost)} hygiene findings disappeared when the reports were withheld, "
              f"e.g. {sorted(lost)[:3]} — the owner's recorded outcomes would stop matching "
              f"on a day a report is late")

    print(f"OK    detection {recon_w['counts']['flagged']} flagged with the reports, "
          f"unavailable ({recon['unavailable_reason']}) without them")
    print(f"OK    hygiene {_total(hyg_w)} records with the reports, {_total(hyg)} without, "
          f"none lost (the withheld run excludes no withdrawn products, INV-036)")
    _f8_independence()


def _f8_independence() -> None:
    """F8-S1 §20: the quantity and the boost fail independently. Real data has no daily
    reports yet, so this runs over check_order_signals' fixture world, and it warns rather
    than fails until the committed artefact first carries a real order_quantity, as that
    probe does."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_order_signals as f8

    with tempfile.TemporaryDirectory() as tmp:
        built = Path(tmp) / "world"
        f8.world.build(built)
        no_picks = f8._copy(built, Path(tmp) / "no_picks")
        for folder in no_picks["snapshots_root"].glob("*/boost_picks"):
            shutil.rmtree(folder)
        no_daily = f8._copy(built, Path(tmp) / "no_daily")
        for path in no_daily["daily_sales_dir"].glob("*.csv"):
            path.unlink()
        problems = f8.independence_problems(f8._run(no_picks)[0], f8._run(no_daily)[0])
    if not problems:
        print("OK    order quantity and boost fail independently (F8 fixture world)")
        return
    if f8.blocking():
        _fail(problems[0])
    for line in problems:
        print(f"::warning::F8 independence  {line}")


if __name__ == "__main__":
    main()
