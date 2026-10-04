#!/usr/bin/env python3
"""build_shelf_example.py — the example behind Shelf plan's preview (D-31, F12-S1 FR-200).

    python3 scripts/build_shelf_example.py          # rewrites public/examples/shelf-plan-example.json

While Shelf plan waits, D-31 lets it show a clearly marked example of itself, as Reorder does under
D-29. The owner approved its source with the Phase 8 plan on 2026-10-04: **the same test shop as
Reorder's example**, with a shelf layout added for its departments. So the shop is built by
scripts/build_order_example.py's own functions, and only the layout is added here:
- a fridge holding the drinks and the dairy, its lower shelf at eye level. The soda has no recorded
  width, so the fridge gets first facings only, and its plan says why (FR-186);
- a dry-goods unit holding the bread and the snacks, with his rule "at most 2 facings" of the
  Bamba, where the spare length on the eye-level shelf goes to the products that earn most from
  it (FR-185);
- a cleaning shelf with its one product;
- one width for a barcode the shop does not sell, which the loader rejects by name (FR-178).

The engine runs in print mode over it, as the approved F8 mockups were drawn, and the result goes to
public/examples/, which no engine step, loader other than its own, probe or measurement reads.
The shop has 28 days of reports and no arrangement, so its measurement shows the waiting state a
new store's would. tests/test_shelf_example.py fails when the committed file differs from a fresh
build.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests.fixtures.order_signals.build as world  # noqa: E402

OUT = ROOT / "public" / "examples" / "shelf-plan-example.json"
MEASURED = "measured_by: team, measured_on: 2026-08-01"
STATED = "stated_by: owner\n    stated_on: 2026-08-01\n    recorded_by: team"
# barcode: facing width in mm, chosen for the test shop (a store's are read from its shelf photographs)
WIDTHS = {world.BOOSTED: 80, world.STEADY: 75, "7290301": 90, "7290101": 200, "7290102": 180,
          "7290201": 120, "7290202": 130, "7290203": 85, "7290401": 110}       # the soda: none recorded


def _order_example():
    spec = importlib.util.spec_from_file_location("build_order_example", ROOT / "scripts" / "build_order_example.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _layout(path: Path) -> None:
    shelf = lambda cm: f"      - {{length_cm: {cm}, {MEASURED}}}\n"          # noqa: E731
    body = ("fixtures:\n"
            f"  מקרר:\n    departments: [{world.DEPT}, מוצרי חלב]\n    chilled: true\n    eye_level_shelf: 2\n"
            f"    {STATED}\n    shelves:\n" + shelf(25) + shelf(20) +
            "  מדף יבש:\n    departments: [מאפים, חטיפים]\n    chilled: false\n    eye_level_shelf: 1\n"
            f"    {STATED}\n    shelves:\n" + shelf(80) + shelf(60) +
            "  ניקיון:\n    departments: [ניקיון]\n    chilled: false\n"
            f"    {STATED}\n    shelves:\n" + shelf(40) +
            "widths:\n" + "".join(f'  "{b}": {{width_mm: {w}, {MEASURED}}}\n' for b, w in WIDTHS.items()) +
            # One entry the loader rejects, as Store layout must show (FR-178): a barcode the
            # shop's catalogue does not have.
            f'  "7299999": {{width_mm: 60, {MEASURED}}}\n' +
            "rules:\n"
            f'  - {{at_most: {{barcode: "7290201", facings: 2}}, stated_by: owner, stated_on: 2026-08-01, recorded_by: team}}\n')
    path.write_text(body, encoding="utf-8")


def build() -> dict:
    import src.engine.run as run_mod
    shop = _order_example()
    with tempfile.TemporaryDirectory() as tmp:
        paths = world.roots(Path(tmp))
        shop._silver(paths["silver_dir"])
        shop._daily(paths["daily_sales_dir"])
        world._monthly(paths["sales_dir"])
        shop._facts(paths["store_facts_path"])
        _layout(paths["store_layout_path"])
        world._snapshots(paths["snapshots_root"])
        saved = run_mod._pull_owner_state
        run_mod._pull_owner_state = lambda: world.owner()          # the shop's owner: no arrangement yet
        try:
            art = run_mod.run_engine(mode="print", skip_market=True, now=world.RUN_AT,
                                     boost_transport=world.FakeModel(), **paths)["artefact"]
        finally:
            run_mod._pull_owner_state = saved
    caps = art["capabilities"]
    names = {world.BOOSTED: "מים", world.STEADY: "קולה", world.SLOW: "סודה", world.UNSTOCKED: "מיץ"}
    catalogue = [{"barcode": b, "product_name": n, "department": world.DEPT} for b, n in names.items()]
    catalogue += [{"barcode": b, "product_name": n, "department": d} for b, (n, d, *_) in shop.EXTRA.items()]
    return {
        "_example": "A test shop, not any store's data (D-31). Built by scripts/build_shelf_example.py from "
                    "Reorder's example shop with a shelf layout added. Nothing reads it but Shelf plan's preview.",
        "now": world.RUN_AT.isoformat(),
        "artefact": {"generated_at": art["generated_at"], "thresholds": art["thresholds"],
                     "capabilities": {k: caps[k] for k in ("layout_facts", "shelf_plan", "shelf_measurement")}},
        "catalogue": {"products": catalogue},
        "owner_state": {"outcomes": {}},
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
