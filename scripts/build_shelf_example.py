#!/usr/bin/env python3
"""build_shelf_example.py — the example behind Shelf plan's preview (D-31, F12-S1 FR-200).

    python3 scripts/build_shelf_example.py            # rewrites public/examples/shelf-plan-example.json
    python3 scripts/build_shelf_example.py --explain  # once, by hand, with the model key: seals its explanation

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
new store's would.

Its explanation (F12-S1 FR-215, D-32) is the real step's answer for this shop. Print mode never asks
the model, so the team asks once, by hand, with `--explain` and the key, and the answer is sealed in
tests/fixtures/shelf_example/explanations.json. Until then the builder gives the engine an empty
snapshot, so each fixture says its explanation has not been written; "no model key" would be wrong
for a page the team may well have a key for. tests/test_shelf_example.py fails when the committed file differs from a fresh
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
SEALED = ROOT / "tests" / "fixtures" / "shelf_example" / "explanations.json"
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


def _seal_snapshot(snapshots_root: Path) -> None:
    """The example's explanations, or an empty snapshot: present, so "not written", never "no key"."""
    from src.engine.shelf_explanation import folder
    target = folder(snapshots_root, world.RUN_AT.date().isoformat())
    target.mkdir(parents=True, exist_ok=True)
    explanations = SEALED.read_text(encoding="utf-8") if SEALED.exists() else "{}"
    (target / "explanations.json").write_text(explanations, encoding="utf-8")
    (target / "_manifest.json").write_text(json.dumps({"runs": [], "example": True}), encoding="utf-8")


def explain() -> int:
    """Ask the model once for the example's plans, with the key, and seal the answers (FR-215)."""
    import os
    import src.engine.run as run_mod
    from src.engine.model_client import KEY_ENV
    from src.engine.shelf_explanation import read
    if not os.environ.get(KEY_ENV):
        print(f"{KEY_ENV} is not set: the example's explanation needs the model key", file=sys.stderr)
        return 1
    shop = _order_example()
    with tempfile.TemporaryDirectory() as tmp:
        paths = _shop(shop, Path(tmp))
        saved = run_mod._pull_owner_state
        run_mod._pull_owner_state = lambda: world.owner()
        try:
            run_mod.run_engine(mode="publish", skip_market=True, now=world.RUN_AT,
                               artefact_path=Path(tmp) / "out" / "dashboard.json",
                               boost_transport=world.FakeModel(), **paths)
        finally:
            run_mod._pull_owner_state = saved
        sealed = read(paths["snapshots_root"], world.RUN_AT.date().isoformat())
    if not sealed or not sealed["explanations"]:
        print("the model was not asked, or answered nothing: nothing sealed (see the run's steps)", file=sys.stderr)
        return 1
    SEALED.parent.mkdir(parents=True, exist_ok=True)
    SEALED.write_text(json.dumps(sealed["explanations"], ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"Sealed {len(sealed['explanations'])} explanations in {SEALED.relative_to(ROOT)}")
    return 0


def _shop(shop, root: Path) -> dict:
    paths = world.roots(root)
    shop._silver(paths["silver_dir"])
    shop._daily(paths["daily_sales_dir"])
    world._monthly(paths["sales_dir"])
    shop._facts(paths["store_facts_path"])
    _layout(paths["store_layout_path"])
    world._snapshots(paths["snapshots_root"])
    return paths


def build() -> dict:
    import src.engine.run as run_mod
    shop = _order_example()
    with tempfile.TemporaryDirectory() as tmp:
        paths = _shop(shop, Path(tmp))
        _seal_snapshot(paths["snapshots_root"])
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
                     "capabilities": {k: caps[k] for k in ("layout_facts", "shelf_plan", "shelf_measurement",
                                                          "shelf_explanation")}},
        "catalogue": {"products": catalogue},
        "owner_state": {"outcomes": {}},
    }


def render(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main() -> int:
    if "--explain" in sys.argv[1:]:
        return explain()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(build()), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
