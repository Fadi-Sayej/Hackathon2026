"""
smoke_test_pipeline.py — fast end-to-end sanity check of the internal pipeline.

Runs the chain that feeds the dashboard and asserts each stage produced what the next
stage expects, so a silent breakage is caught before a demo. Does NOT require a POS
CSV argument — it exercises whatever silver data already exists.

Exit code 0 = all checks passed, 1 = at least one failed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    CHECKS.append((name, passed, detail))


def main() -> int:
    # 1. Operational recommendations generate
    try:
        from src.recommendations.operational_recommendations import generate_operational_recommendations

        gen = generate_operational_recommendations()
        check(
            "operational_recommendations",
            gen.get("status") in {"ok", "readiness_only"},
            f"status={gen.get('status')} count={gen.get('recommendation_count')}",
        )
    except Exception as exc:
        check("operational_recommendations", False, f"{type(exc).__name__}: {exc}")

    # 2. Expiry report builds
    try:
        from src.expiry.expiry_tracking import build_expiry_report

        rep = build_expiry_report()
        check("expiry_report", rep.get("status") == "ok", f"scans={rep['summary']['total_scans']}")
    except Exception as exc:
        check("expiry_report", False, f"{type(exc).__name__}: {exc}")

    # 3. Dashboard export
    try:
        from scripts.export_dashboard_data import export

        result = export()
        check("dashboard_export", result.get("status") == "ok", f"recs={result.get('recommendation_count')}")
    except Exception as exc:
        check("dashboard_export", False, f"{type(exc).__name__}: {exc}")

    # 4. operational.json well-formed
    try:
        payload = json.loads((ROOT / "public" / "data" / "operational.json").read_text(encoding="utf-8"))
        ok = (
            isinstance(payload.get("recommendations"), list)
            and "posHealth" in payload
            and "sources" in payload
            and "expiry" in payload
        )
        check("operational_json", ok, f"keys={sorted(payload.keys())}")
    except Exception as exc:
        check("operational_json", False, f"{type(exc).__name__}: {exc}")

    # 5. sources.json well-formed
    try:
        from src.common.source_status import load_sources

        sources = load_sources()
        check("sources_contract", len(sources) > 0 and all("status" in s for s in sources.values()),
              f"sources={len(sources)}")
    except Exception as exc:
        check("sources_contract", False, f"{type(exc).__name__}: {exc}")

    # 6. Snapshot comparison runs (ok OR need_two_snapshots are both valid)
    try:
        from src.snapshots.pos_snapshots import build_snapshot_comparison_report

        snap = build_snapshot_comparison_report()
        check("snapshot_comparison", snap.get("status") in {"ok", "need_two_snapshots"}, f"status={snap.get('status')}")
    except Exception as exc:
        check("snapshot_comparison", False, f"{type(exc).__name__}: {exc}")

    failed = [c for c in CHECKS if not c[1]]
    print("\nSmoke test results")
    print("=" * 50)
    for name, passed, detail in CHECKS:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name:24} {detail}")
    print("=" * 50)
    print(f"{len(CHECKS) - len(failed)}/{len(CHECKS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
