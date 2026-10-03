"""build_order_example.py — the example shop behind the order pages' preview (D-29).

    python3 scripts/build_order_example.py          # rewrites public/examples/order-example.json

While Reorder and Approved orders wait for daily sales reports, each offers "See how this
page looks". D-29 allows example data there and nowhere else, so it is built here, from the
order probe's fixture world (tests/fixtures/order_signals/build.py), and never from or into
the store's own data:
- the engine runs in print mode over a test shop, as the approved F8 mockups were drawn
  (docs/reviews/F8-screens-mockups.md);
- the result is written to public/examples/, which no engine step, loader, probe or
  measurement reads;
- the pages show it under a banner saying it is an example and not the store's data, with
  every button disabled.

The test shop has five departments, so the preview shows every kind of line the page can:
- drinks: the probe's own four products: a boosted suggestion, an unboosted one, a product
  that does not sell every week, and one never stocked;
- bakery: a two-day shelf life that caps a weekly order;
- snacks: one count the page cannot use (the product is on Records to fix), and one product
  its stock already covers;
- dairy: no shelf life stated, so no quantity;
- cleaning: no order days stated, so no quantity.

Every figure on the preview is the engine's own over this shop. tests/test_order_example.py
fails when the committed file differs from a fresh build.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests.fixtures.order_signals.build as world  # noqa: E402

OUT = ROOT / "public" / "examples" / "order-example.json"

# barcode: (name, department, sold a day, delivered a day, counted stock, weeks it sold in)
EXTRA = {
    "7290101": ("לחם אחיד", "מאפים", 8, 8, 10.0, 4),
    "7290102": ("פיתות", "מאפים", 5, 5, 6.0, 4),
    "7290201": ("במבה", "חטיפים", 5, 4, 20.0, 4),
    "7290202": ("ביסלי גריל", "חטיפים", 4, 4, -4.0, 4),      # negative: on Records to fix
    "7290203": ("פרינגלס", "חטיפים", 1, 0, 300.0, 4),        # its stock covers the order
    "7290301": ("חלב 3%", "מוצרי חלב", 6, 6, 12.0, 4),
    "7290401": ("אקונומיקה", "ניקיון", 1, 0, 15.0, 4),
}
FACTS = {
    world.DEPT: "    order_schedule: {weekdays: [sun]}\n    shelf_life_days: 30\n",
    "מאפים": "    order_schedule: {weekdays: [sun]}\n    shelf_life_days: 2\n",
    "חטיפים": "    order_schedule: {weekdays: [tue]}\n    shelf_life_days: 120\n",
    "מוצרי חלב": "    order_schedule: {weekdays: [sun, wed]}\n",                # no shelf life stated
}                                                                            # cleaning: nothing stated
APPROVED = {"7290001": None, "7290101": 14, "7290201": None}              # None: as suggested


def _silver(silver: Path) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    world._silver(silver)
    base = {"_source_file": "inv.csv", "_as_of": world.COUNTED, "_as_of_source": "declared"}
    prod = pq.read_table(silver / "products.parquet").to_pylist()
    inv = pq.read_table(silver / "inventory.parquet").to_pylist()
    for barcode, (name, dept, _, _, stock, _) in EXTRA.items():
        prod.append({"barcode": barcode, "product_name": name, "category": dept, "selling_price": 6.0,
                     "wolt_price": 0.0, "cost_price": 3.0, **base})
        inv.append({"barcode": barcode, "product_name": name, "current_stock": stock, **base})
    pq.write_table(pa.Table.from_pylist(prod), silver / "products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "inventory.parquet")


def _daily(folder: Path) -> None:
    world._daily(folder)
    for back in range(28):
        day = world.LAST - timedelta(days=back)
        path = folder / f"דוח מכירות יום {day.isoformat()}.csv"
        lines = [f"{name},{barcode},{sold},3,6,{sold * 3},{delivered},3,0,1,"
                 for barcode, (name, _, sold, delivered, _, weeks) in EXTRA.items() if back < weeks * 7]
        path.write_text(path.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")


def _facts(path: Path) -> None:
    body = "".join(f"  {dept}:\n{facts}    stated_by: owner\n    stated_on: 2026-08-01\n    recorded_by: team\n"
                   for dept, facts in FACTS.items())
    path.write_text("departments:\n" + body, encoding="utf-8")


def _approvals(entries: list) -> dict:
    """The owner state the Approved orders preview shows: three suggestions approved, one changed."""
    out = {}
    for entry in entries:
        if entry["barcode"] not in APPROVED:
            continue
        ev = entry["evidence"]
        snapshot = {"signal_family": entry["signal_family"], "capability": "order_quantity",
                    "barcode": entry["barcode"], "order_day": ev["order_day"], "kind": ev["kind"],
                    "suggested_quantity": ev["quantity"]}
        if APPROVED[entry["barcode"]] is not None:
            snapshot["approved_quantity"] = APPROVED[entry["barcode"]]
        out[entry["id"]] = {"status": "acted", "at": 1787799600000, "reason": None, "snapshot": snapshot}
    return out


def build() -> dict:
    import src.engine.run as run_mod
    from src.engine.market_boost import KEY_ENV
    with tempfile.TemporaryDirectory() as tmp:
        paths = world.roots(Path(tmp))
        _silver(paths["silver_dir"])
        _daily(paths["daily_sales_dir"])
        world._monthly(paths["sales_dir"])
        _facts(paths["store_facts_path"])
        world._snapshots(paths["snapshots_root"])
        saved = os.environ.get(KEY_ENV)
        os.environ[KEY_ENV] = "example-key"
        try:
            run_mod.run_engine(mode="publish", skip_market=True, now=world.RUN_AT,
                               artefact_path=Path(tmp) / "out" / "dashboard.json",
                               boost_transport=world.FakeModel(), **paths)        # seals the picks
            art = run_mod.run_engine(mode="print", skip_market=True, now=world.RUN_AT,
                                     boost_transport=world.FakeModel(), **paths)["artefact"]
        finally:
            if saved is None:
                os.environ.pop(KEY_ENV, None)
            else:
                os.environ[KEY_ENV] = saved
    caps = art["capabilities"]
    names = {b: n for b, n in [(world.BOOSTED, "מים"), (world.STEADY, "קולה"), (world.SLOW, "סודה"),
                                (world.UNSTOCKED, "מיץ")]}
    catalogue = [{"barcode": b, "product_name": n, "department": world.DEPT} for b, n in names.items()]
    catalogue += [{"barcode": b, "product_name": n, "department": d} for b, (n, d, *_) in EXTRA.items()]
    return {
        "_example": "A test shop, not any store's data (D-29). Built by scripts/build_order_example.py "
                    "from the order probe's fixture world. Nothing reads it but the order pages' preview.",
        "now": world.RUN_AT.isoformat(),
        "artefact": {"generated_at": art["generated_at"], "thresholds": art["thresholds"],
                     "capabilities": {k: caps[k] for k in ("order_quantity", "market_running_out", "market_boost")}},
        "catalogue": {"products": catalogue},
        "owner_state": {"outcomes": _approvals(caps["order_quantity"]["entries"])},
    }


def render(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(build()), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
