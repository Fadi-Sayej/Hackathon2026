# tests/fixtures/order_signals/build.py
"""The fixture world F8's boundary probe runs over (Phase 5 Task 5.11, CLAUDE.md rule 12).

Built, not committed as files: `*.parquet` is ignored repository-wide, and a builder states
what each product is for, which a directory of binary files cannot. `build(root)` writes:

- silver POS tables for four products in one department, counted on 2026-08-24 (declared);
- 28 daily sales reports ending 2026-08-26, with deliveries, and one monthly report;
- the store facts for that department (Sundays, 30 days);
- a shelf layout (F12, ADR-037): one fixture holding the department, two shelves, and widths for
  two of the products, so the third stocked one has none;
- 30 days of delivery-catalogue snapshots at Wolt Market, a store above the format floor;
- the boost picks, sealed by the real live step with a fake model that picks 10%.

The run is Thursday 2026-08-27. On it:

| Product | Sales | The market | So |
|---|---|---|---|
| 7290001 | 3 a day, 2 delivered a day | out 3 days | a suggestion, net, boosted 10% |
| 7290002 | 2 a day, 1 delivered a day | listed | a suggestion, net, unboosted |
| 7290003 | 1 a day, oldest week only | out 3 days | not moving: a disagreement question |
| 7290004 | none, never delivered | out 3 days | not stocked: nothing at all |

Every date is fixed, so the probe is the same probe on any day it runs.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RUN_AT = datetime(2026, 8, 27, 3, 0, tzinfo=timezone.utc)
LAST = date(2026, 8, 26)
COUNTED = "2026-08-24"
DEPT = "משקאות"
WOLT = "65daeb8779ca7f0a9bf964f3"
BOOSTED, STEADY, SLOW, UNSTOCKED = "7290001", "7290002", "7290003", "7290004"
# F9-S1: a product the market sells and runs out of that is not in his catalogue at all, so
# the probe's baseline shows an assortment-gap finding and withholding the market removes it.
NOT_CARRIED = "7291000"
HEADER = "תאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n"
PICK = '{"boost_pct": 10, "reason": "المحلات القريبة نفدت منها"}'


def _silver(silver: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    names = {BOOSTED: "מים", STEADY: "קולה", SLOW: "סודה", UNSTOCKED: "מיץ"}
    base = {"_source_file": "inv.csv", "_as_of": COUNTED, "_as_of_source": "declared"}
    prod = [{"barcode": b, "product_name": n, "category": DEPT, "selling_price": 4.0, "wolt_price": 0.0,
             "cost_price": 1.0, **base} for b, n in names.items()]
    inv = [{"barcode": b, "product_name": n, "current_stock": 12.0, **base} for b, n in names.items()]
    silver.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(prod), silver / "products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "inventory.parquet")


def _daily(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for back in range(28):
        day = LAST - timedelta(days=back)
        lines = [f"מים,{BOOSTED},3,1,4,3,2,1,0,1,", f"קולה,{STEADY},2,1,4,2,1,1,0,1,"]
        if back >= 21:
            lines.append(f"סודה,{SLOW},1,1,4,1,0,1,0,1,")
        (folder / f"דוח מכירות יום {day.isoformat()}.csv").write_text(
            "﻿" + HEADER + "\n".join(lines) + "\n", encoding="utf-8")


def _monthly(folder: Path) -> None:
    """A monthly report: it itemises the department, and supplies no quantity (INV-070)."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "דוח מכירות חודש יולי 2026.csv").write_text(
        "﻿" + HEADER + f"מים,{BOOSTED},90,1,4,90,60,1,0,1,\nקולה,{STEADY},60,1,4,60,30,1,0,1,\n",
        encoding="utf-8")


def _facts(path: Path) -> None:
    path.write_text(f"departments:\n  {DEPT}:\n    order_schedule: {{weekdays: [sun]}}\n    shelf_life_days: 30\n"
                    "    stated_by: owner\n    stated_on: 2026-08-01\n    recorded_by: team\n", encoding="utf-8")


def _layout(path: Path) -> None:
    """One fixture, F1, holding the department. 7290003 is stocked and has no recorded width."""
    measured = "measured_by: team, measured_on: 2026-08-01"
    path.write_text(
        "fixtures:\n  F1:\n"
        f"    departments: [{DEPT}]\n    chilled: true\n    eye_level_shelf: 1\n"
        "    stated_by: owner\n    stated_on: 2026-08-01\n    recorded_by: team\n"
        f"    shelves:\n      - {{length_cm: 100, {measured}}}\n      - {{length_cm: 90, {measured}}}\n"
        "widths:\n"
        f'  "{BOOSTED}": {{width_mm: 80, {measured}}}\n  "{STEADY}": {{width_mm: 70, {measured}}}\n',
        encoding="utf-8")


def _snapshots(root: Path) -> None:
    import polars as pl
    first = RUN_AT.date() - timedelta(days=29)
    for i in range(30):
        day = first + timedelta(days=i)
        # Forty other listings: four products going at once is then 4 of 45 steady listings,
        # a stockout's scatter under catalogue_change_pct. With twenty it was 3 of 24, 12.5%,
        # and ADR-031's guard rightly read the day as a catalogue change and excluded it.
        rows = [{"barcode": f"7280{j:03d}", "store_id": WOLT, "is_online_available": True} for j in range(40)]
        rows.append({"barcode": STEADY, "store_id": WOLT, "is_online_available": True})
        if i < 27:
            rows += [{"barcode": b, "store_id": WOLT, "is_online_available": True}
                     for b in (BOOSTED, SLOW, UNSTOCKED, NOT_CARRIED)]
        folder = root / day.isoformat() / "delivery_catalog" / "01"
        folder.mkdir(parents=True, exist_ok=True)
        pl.DataFrame(rows).write_parquet(folder / "products_silver.parquet")
        (root / day.isoformat() / "_manifest.json").write_text(json.dumps(
            {"date": day.isoformat(), "status": "ok", "sources": {"delivery_catalog": {"status": "ok"}}}))


def roots(root: Path) -> dict:
    return {"silver_dir": root / "silver", "daily_sales_dir": root / "daily", "sales_dir": root / "monthly",
            "store_facts_path": root / "store_facts.yaml", "store_layout_path": root / "store_layout.yaml",
            "snapshots_root": root / "snapshots",
            "signals_dir": root / "signals", "matches_path": root / "matches.parquet"}


def owner(answered=()):
    from src.owner_state.model import OwnerState
    return OwnerState.from_dict({"status": "available", "pulled_at": "2026-08-27T03:00:00Z", "answers": {
        b: {"market_disagreement": {"status": "answered", "value": "weak_market"}} for b in answered}})


class FakeModel:
    """Answers every request with the same pick, and counts the requests."""

    def __init__(self, answer: str = PICK):
        self.answer, self.calls = answer, 0

    def __call__(self, url, headers, body, timeout):
        self.calls += 1
        return 200, json.dumps({"content": [{"type": "text", "text": self.answer}]}).encode()


def build(root: Path) -> dict:
    """Write the world under `root`, seal tonight's picks through the live step, return its paths."""
    import os
    import src.engine.run as run_mod
    from src.engine.market_boost import KEY_ENV

    paths = roots(root)
    _silver(paths["silver_dir"])
    _daily(paths["daily_sales_dir"])
    _monthly(paths["sales_dir"])
    _facts(paths["store_facts_path"])
    _layout(paths["store_layout_path"])
    _snapshots(paths["snapshots_root"])
    saved = os.environ.get(KEY_ENV)
    os.environ[KEY_ENV] = "fixture-key"
    try:
        run_mod.run_engine(mode="publish", skip_market=True, now=RUN_AT, artefact_path=root / "out" / "dashboard.json",
                           boost_transport=FakeModel(), **paths)
    finally:
        if saved is None:
            os.environ.pop(KEY_ENV, None)
        else:
            os.environ[KEY_ENV] = saved
    return paths
