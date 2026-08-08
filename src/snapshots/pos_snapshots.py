"""
pos_snapshots.py — POS snapshot archiving + comparison (Steps 6 & 7).

Each POS import is archived as a point-in-time snapshot of the silver catalog. Comparing
the two most recent snapshots yields:

  - added / removed products
  - selling-price changes
  - WOLT-price changes
  - stock changes  → an inventory MOVEMENT PROXY (we have no sales columns, so the
                     stock delta between snapshots is the best available demand signal)

Snapshots live under:  data/internal/snapshots/<timestamp>/{products,inventory}.parquet
Reports go to:         reports/snapshots/snapshot_comparison_<timestamp>.{json,md}

This is intentionally a PROXY: a stock drop usually means sales, but can also be
shrinkage, returns, or a manual correction — it is a movement signal, not exact sales.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from src.common.paths import PROJECT_ROOT, SILVER_POS_ROOT, SNAPSHOTS_ROOT

SNAPSHOT_REPORTS_DIR = PROJECT_ROOT / "reports" / "snapshots"

# Movement-proxy thresholds (units of stock delta between snapshots)
FAST_DROP = 20      # stock fell by at least this many → likely fast mover
SOLD_DROP = 1       # any negative delta → some movement


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return pq.read_table(path).to_pylist()


def _num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _latest_import_id() -> str | None:
    """Which import the most recent snapshot came from, or None."""
    from src.snapshots.velocity import list_usable_snapshots, snapshot_import_id

    snapshots = list_usable_snapshots()
    if not snapshots:
        return None
    return snapshot_import_id(snapshots[-1][1])


def _current_import_id() -> str | None:
    """Import identity of the LIVE silver tables.

    Deliberately not snapshot_import_id(): inside a snapshot the files are named
    products/inventory.parquet, but in the silver root they are yomyom_*.parquet,
    so that helper finds nothing and returns None — which silently disabled the
    duplicate check and let another full copy be archived every run.
    """
    for name in ("yomyom_products.parquet", "yomyom_inventory.parquet"):
        path = SILVER_POS_ROOT / name
        if not path.exists():
            continue
        try:
            schema = pq.read_schema(path)
            wanted = [c for c in ("_source_file", "_imported_at") if c in schema.names]
            if not wanted:
                continue
            rows = pq.read_table(path, columns=wanted).to_pylist()
        except Exception:
            continue
        if rows:
            return "%s@%s" % (rows[0].get("_source_file"), rows[0].get("_imported_at"))
    return None


def archive_current_silver(imported_at: str | None = None, force: bool = False) -> Path | None:
    """Copy the current silver products + inventory tables into a new snapshot dir.

    Skips when the silver tables come from the SAME import as the last snapshot.
    pilot_daily.sh runs this every time, so without the check a re-run with no new
    POS export produces another full copy of identical data: pure repo weight that
    can never yield velocity, because velocity.py rejects same-import pairs anyway.
    (This is exactly how 8 snapshots accumulated from a single import.)

    Pass force=True to archive regardless.
    """
    products = SILVER_POS_ROOT / "yomyom_products.parquet"
    inventory = SILVER_POS_ROOT / "yomyom_inventory.parquet"
    if not products.exists():
        return None

    if not force:
        current = _current_import_id()
        if current is not None and current == _latest_import_id():
            return None

    ts = _now().strftime("%Y%m%dT%H%M%SZ")
    dest = SNAPSHOTS_ROOT / ts
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(products, dest / "products.parquet")
    if inventory.exists():
        shutil.copy2(inventory, dest / "inventory.parquet")
    (dest / "meta.json").write_text(
        json.dumps({"snapshot_ts": ts, "imported_at": imported_at}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return dest


def list_snapshots() -> list[Path]:
    if not SNAPSHOTS_ROOT.exists():
        return []
    return sorted((p for p in SNAPSHOTS_ROOT.iterdir() if p.is_dir()), key=lambda p: p.name)


def _index(snapshot_dir: Path) -> dict[str, dict[str, Any]]:
    """barcode → merged product+inventory row for a snapshot."""
    products = _read_rows(snapshot_dir / "products.parquet")
    inventory = {
        str(r.get("barcode")): r
        for r in _read_rows(snapshot_dir / "inventory.parquet")
        if r.get("barcode")
    }
    index: dict[str, dict[str, Any]] = {}
    for row in products:
        bc = str(row.get("barcode") or "")
        if not bc:
            continue
        merged = dict(row)
        inv = inventory.get(bc)
        if inv:
            merged["current_stock"] = inv.get("current_stock")
        index.setdefault(bc, merged)
    return index


def _movement_label(delta: float) -> str:
    if delta <= -FAST_DROP:
        return "fast_mover"
    if delta <= -SOLD_DROP:
        return "moved"
    if delta > 0:
        return "restocked"
    return "stagnant"


def compare_snapshots(old_dir: Path, new_dir: Path) -> dict[str, Any]:
    old = _index(old_dir)
    new = _index(new_dir)

    old_bcs, new_bcs = set(old), set(new)
    added = sorted(new_bcs - old_bcs)
    removed = sorted(old_bcs - new_bcs)

    price_changes: list[dict[str, Any]] = []
    wolt_changes: list[dict[str, Any]] = []
    stock_changes: list[dict[str, Any]] = []
    movement: dict[str, int] = {"fast_mover": 0, "moved": 0, "restocked": 0, "stagnant": 0}

    for bc in sorted(new_bcs & old_bcs):
        o, n = old[bc], new[bc]
        name = n.get("product_name")

        op, np_ = _num(o.get("selling_price")), _num(n.get("selling_price"))
        if op is not None and np_ is not None and op != np_:
            price_changes.append({"barcode": bc, "productName": name, "old": op, "new": np_, "delta": round(np_ - op, 2)})

        ow, nw = _num(o.get("wolt_price")), _num(n.get("wolt_price"))
        if ow is not None and nw is not None and ow != nw:
            wolt_changes.append({"barcode": bc, "productName": name, "old": ow, "new": nw, "delta": round(nw - ow, 2)})

        os_, ns_ = _num(o.get("current_stock")), _num(n.get("current_stock"))
        if os_ is not None and ns_ is not None and os_ != ns_:
            delta = ns_ - os_
            label = _movement_label(delta)
            movement[label] += 1
            stock_changes.append(
                {"barcode": bc, "productName": name, "old": os_, "new": ns_, "delta": delta, "movement": label}
            )

    return {
        "added": added,
        "removed": removed,
        "price_changes": price_changes,
        "wolt_changes": wolt_changes,
        "stock_changes": stock_changes,
        "movement": movement,
        "counts": {
            "added": len(added),
            "removed": len(removed),
            "price_changes": len(price_changes),
            "wolt_changes": len(wolt_changes),
            "stock_changes": len(stock_changes),
        },
    }


def build_snapshot_comparison_report() -> dict[str, Any]:
    snapshots = list_snapshots()
    generated_at = _now()
    ts = generated_at.strftime("%Y%m%dT%H%M%SZ")
    SNAPSHOT_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if len(snapshots) < 2:
        report = {
            "status": "need_two_snapshots",
            "generated_at": generated_at.isoformat(),
            "snapshot_count": len(snapshots),
            "message": "Need at least two POS snapshots to compare. Import another POS export.",
        }
        (SNAPSHOT_REPORTS_DIR / f"snapshot_comparison_{ts}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report

    old_dir, new_dir = snapshots[-2], snapshots[-1]
    diff = compare_snapshots(old_dir, new_dir)
    report = {
        "status": "ok",
        "generated_at": generated_at.isoformat(),
        "old_snapshot": old_dir.name,
        "new_snapshot": new_dir.name,
        "counts": diff["counts"],
        "movement": diff["movement"],
        "diff": diff,
    }

    json_path = SNAPSHOT_REPORTS_DIR / f"snapshot_comparison_{ts}.json"
    md_path = SNAPSHOT_REPORTS_DIR / f"snapshot_comparison_{ts}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_build_markdown(report), encoding="utf-8")
    report["json_path"] = str(json_path)
    report["markdown_path"] = str(md_path)
    return report


def _build_markdown(report: dict[str, Any]) -> str:
    c = report["counts"]
    m = report["movement"]
    diff = report["diff"]
    lines = [
        "# POS Snapshot Comparison",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Old snapshot: {report['old_snapshot']}",
        f"- New snapshot: {report['new_snapshot']}",
        "",
        "## Changes",
        "",
        f"- Added products: {c['added']}",
        f"- Removed products: {c['removed']}",
        f"- Price changes: {c['price_changes']}",
        f"- WOLT price changes: {c['wolt_changes']}",
        f"- Stock changes: {c['stock_changes']}",
        "",
        "## Inventory movement proxy (stock delta)",
        "",
        f"- Fast movers (large drop): {m['fast_mover']}",
        f"- Moved (any drop): {m['moved']}",
        f"- Restocked (increase): {m['restocked']}",
        f"- Stagnant: {m['stagnant']}",
        "",
        "> Movement is inferred from stock deltas between snapshots — a proxy for sales,"
        " not exact (it also captures shrinkage, returns, and corrections).",
        "",
        "## Top price changes",
        "",
    ]
    for row in sorted(diff["price_changes"], key=lambda r: -abs(r["delta"]))[:10]:
        lines.append(f"- {row['productName'] or row['barcode']}: {row['old']} → {row['new']} ({row['delta']:+})")
    return "\n".join(lines) + "\n"
