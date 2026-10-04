# tests/fixtures/shelf_signals/build.py
"""The planogram world F12-S1's measurement is proven on (Phase 8 Task 8.5). A test shop: no store's data.

Fourteen fixtures, one department each, six products a fixture. Eight fixtures are arranged on
staggered days, each once, so every arrangement keeps the six never-arranged fixtures as its
comparison. Sales are drawn day by day from a known model, so the measurement has a true answer
to find:

    daily units ~ Poisson(base × season(day) × facings ^ TRUE_ELASTICITY × EYE_LIFT ^ at_eye_level)

The facings and eye level are what the layout's count says until the product's fixture is
arranged, and what he recorded following after. The variants break one assumption each (F12-S1
AC-197):
- `known`: nothing else moves. AC-192's interval should hold TRUE_ELASTICITY;
- `drifting`: the arranged fixtures' departments were already rising before any arrangement, so
  the placebo's "arranged at all" term should fail;
- `rising`: the products that get more space were already rising, and the ones that get less
  falling, so the placebo's facing term should fail;
- `short`: too little history for any placebo, so it is "not run".

`world(variant)` returns the engine's inputs in memory, for the unit tests. Every number is drawn
from a seeded generator, so the world is the same world on every run.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

import numpy as np

TRUE_ELASTICITY = 0.2
EYE_LIFT = math.exp(0.25)
LAST = date(2026, 9, 30)
RUN_AT = datetime(2026, 10, 1, 3, 0, tzinfo=timezone.utc)
COUNTED = "2026-01-02"                 # the team's count, before any window
FIXTURES = [f"F{n:02d}" for n in range(1, 15)]
ARRANGED = FIXTURES[:8]
PRODUCTS_PER_FIXTURE = 6
MEASURED = "measured_by: team, measured_on: 2026-01-02"
STATED = "stated_by: owner\n    stated_on: 2026-01-02\n    recorded_by: team"
SHAPES = {   # history in days, and the day index of each arrangement (0 = the first report day)
    "known": (240, [120, 132, 144, 156, 168, 180, 192, 204]),
    "drifting": (240, [120, 132, 144, 156, 168, 180, 192, 204]),
    "rising": (240, [120, 132, 144, 156, 168, 180, 192, 204]),
    "short": (150, [60, 68, 76, 84, 92, 100, 108, 116]),
}


def barcode(fixture: str, n: int) -> str:
    return f"73{fixture[1:]}{n:02d}1"


CONTRACT = "5e1f0a9b8c7d6e5f"      # the arrangement ownerStateContract.test.js writes through recordOutcome


def arrangement_record(fixture: str, arranged_on: date, placements: dict) -> tuple:
    """(entry id, record) in the browser's own shape (F12-S1 §20 row 2, ADR-038 Decision 9).

    The record is the contract fixture's arrangement, which the real recordOutcome wrote, with only
    the fixture, its dates and its placements changed. If the browser renamed a field, this world
    would carry the new name too, and the measurement reading the old one would fail the probe."""
    import copy
    import json
    from pathlib import Path
    from src.engine.model import entry_id
    contract = json.loads((Path(__file__).resolve().parents[1] / "owner_state_firestore_contract.json")
                          .read_text(encoding="utf-8"))["outcomes"][CONTRACT]
    plan_date, plan_first, plan_last = _plan_window(arranged_on)
    record = copy.deepcopy(contract)
    record["snapshot"].update({"fixture": fixture, "plan_date": plan_date.isoformat(),
                               "plan_window": {"first_day": plan_first.isoformat(), "last_day": plan_last.isoformat()},
                               "arranged_on": arranged_on.isoformat(), "placements": placements})
    assert set(record["snapshot"]) == set(contract["snapshot"]), "the contract's arrangement changed shape"
    return entry_id("shelf.plan", None, f"{fixture}|{plan_date.isoformat()}"), record


def _plan_window(arranged_on: date) -> tuple:
    plan_date = arranged_on - timedelta(days=2)
    return plan_date, plan_date - timedelta(days=28), plan_date - timedelta(days=1)


def world(variant: str = "known", *, tmp_path=None) -> dict:
    from src.engine.store_layout import load_store_layout
    from src.owner_state.model import OwnerState

    days, arranged_at = SHAPES[variant]
    first = LAST - timedelta(days=days - 1)
    rng = np.random.default_rng({"known": 11, "drifting": 12, "rising": 13, "short": 14}[variant])
    products, before, after, base = [], {}, {}, {}
    for f_index, fixture in enumerate(FIXTURES):
        for n in range(1, PRODUCTS_PER_FIXTURE + 1):
            b = barcode(fixture, n)
            products.append({"barcode": b, "has_identifier": True, "product_name": f"{fixture}-{n}",
                             "department": f"D{fixture[1:]}", "shelf_price": 10.0, "delivery_price": None,
                             "cost_price": 6.0, "cost_source": "pos", "recorded_stock": 10.0})
            before[b] = {"shelf": 1 + (n % 2), "facings": int(rng.integers(1, 4))}
            base[b] = float(rng.uniform(6, 15))
    outcomes, arrangements = {}, {}
    for fixture, day_index in zip(ARRANGED, arranged_at):
        arranged_on = first + timedelta(days=day_index)
        plan_date, plan_first, plan_last = _plan_window(arranged_on)
        placements = {}
        for n in range(1, PRODUCTS_PER_FIXTURE + 1):
            b = barcode(fixture, n)
            facings = int(rng.integers(1, 5))
            if facings == before[b]["facings"]:
                facings = facings % 4 + 1                 # every arranged product's space changes
            shelf = 1 if n <= 3 else 2
            placements[b] = {"shelf": shelf, "facings": facings, "eye_level": shelf == 1}
            after[b] = (arranged_on, placements[b])
        arrangements[fixture] = arranged_on
        eid, record = arrangement_record(fixture, arranged_on, placements)
        outcomes[eid] = record

    sales = []
    for t in range(days):
        day = first + timedelta(days=t)
        season = 1 + 0.2 * math.sin(2 * math.pi * t / 60)
        for p in products:
            b, fixture = p["barcode"], "F" + p["department"][1:]
            state = before[b]
            facings, eye = state["facings"], state["shelf"] == 1
            if b in after and day > after[b][0]:
                facings, eye = after[b][1]["facings"], after[b][1]["eye_level"]
            lam = base[b] * season * facings ** TRUE_ELASTICITY * (EYE_LIFT if eye else 1.0)
            if variant == "drifting" and fixture in ARRANGED:
                lam *= math.exp(0.006 * t)                 # the arranged departments rise anyway
            if variant == "rising" and b in after:
                more = after[b][1]["facings"] > state["facings"]
                lam *= math.exp((0.008 if more else -0.008) * t)
            sales.append({"barcode": b, "day": day.isoformat(), "units": float(rng.poisson(lam)), "receipts": None})

    body = "fixtures:\n"
    for fixture in FIXTURES:
        body += (f"  {fixture}:\n    departments: [D{fixture[1:]}]\n    chilled: false\n    eye_level_shelf: 1\n"
                 f"    {STATED}\n    shelves:\n      - {{length_cm: 120, {MEASURED}}}\n      - {{length_cm: 120, {MEASURED}}}\n")
    body += "widths:\n" + "".join(f'  "{p["barcode"]}": {{width_mm: 100, {MEASURED}}}\n' for p in products)
    body += "current:\n" + "".join(
        f'  "{b}": {{fixture: F{b[2:4]}, shelf: {s["shelf"]}, facings: {s["facings"]}, {MEASURED}}}\n'
        for b, s in before.items())
    import tempfile
    from pathlib import Path
    folder = Path(tmp_path) if tmp_path else Path(tempfile.mkdtemp())
    (folder / "store_layout.yaml").write_text(body, encoding="utf-8")
    layout = load_store_layout(folder / "store_layout.yaml", products)
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "2026-10-01T03:00:00Z", "outcomes": outcomes})
    return {"products": products, "sales_daily": sales, "store_layout": layout, "owner": owner,
            "run_at": RUN_AT, "arrangements": arrangements, "layout_text": body, "first_day": first}


HEADER = "תאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n"


def roots(root) -> dict:
    from pathlib import Path
    root = Path(root)
    return {"silver_dir": root / "silver", "daily_sales_dir": root / "daily", "sales_dir": root / "monthly",
            "store_facts_path": root / "store_facts.yaml", "store_layout_path": root / "store_layout.yaml",
            "snapshots_root": root / "snapshots", "signals_dir": root / "signals",
            "matches_path": root / "matches.parquet"}


def write(root, variant: str = "known") -> tuple:
    """The world as the engine reads it from disk, for the probe (F12-S1 §20): silver POS tables, one
    daily report a day, and the layout file. Returns (paths, world); the owner state is the
    probe's to give the engine, as check_order_signals gives its own."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    from collections import defaultdict
    from pathlib import Path

    paths = roots(root)
    Path(root).mkdir(parents=True, exist_ok=True)
    w = world(variant, tmp_path=Path(root))
    base = {"_source_file": "inv.csv", "_as_of": COUNTED, "_as_of_source": "declared"}
    prod = [{"barcode": p["barcode"], "product_name": p["product_name"], "category": p["department"],
             "selling_price": p["shelf_price"], "wolt_price": 0.0, "cost_price": p["cost_price"], **base}
            for p in w["products"]]
    inv = [{"barcode": p["barcode"], "product_name": p["product_name"], "current_stock": p["recorded_stock"], **base}
           for p in w["products"]]
    paths["silver_dir"].mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(prod), paths["silver_dir"] / "products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), paths["silver_dir"] / "inventory.parquet")
    by_day = defaultdict(list)
    names = {p["barcode"]: p["product_name"] for p in w["products"]}
    for r in w["sales_daily"]:
        u = int(r["units"])
        # Deliveries left blank: the world has none recorded (None), and a 0 would be a statement.
        by_day[r["day"]].append(f"{names[r['barcode']]},{r['barcode']},{u},6,10,{u * 6},,6,0,1,")
    paths["daily_sales_dir"].mkdir(parents=True, exist_ok=True)
    for day, lines in by_day.items():
        (paths["daily_sales_dir"] / f"דוח מכירות יום {day}.csv").write_text(
            "﻿" + HEADER + "\n".join(lines) + "\n", encoding="utf-8")
    paths["sales_dir"].mkdir(parents=True, exist_ok=True)
    paths["snapshots_root"].mkdir(parents=True, exist_ok=True)
    paths["store_layout_path"].write_text(w["layout_text"], encoding="utf-8")
    return paths, w
