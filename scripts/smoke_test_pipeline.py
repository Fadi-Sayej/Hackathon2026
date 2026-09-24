"""
smoke_test_pipeline.py — fast sanity check of the pipeline stages outside the engine.

Asserts that the expiry report builds and that the POS snapshot comparison runs, so a
silent breakage in either is caught before a demo. Does NOT require a POS CSV argument —
it exercises whatever silver data already exists. The engine has its own gates
(`npm run check:signals`, `npm run figures`); this covers what they do not reach.

It used to check the legacy chain too: operational recommendations, the dashboard export,
`operational.json` and `sources.json`. That chain was deleted on 2026-09-24 (Phase 4
Task 4.2), and the `sources.json` check had been failing since the file was retired on
2026-09-13, unnoticed, because nothing runs this in CI.

Exit code 0 = all checks passed, 1 = at least one failed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    CHECKS.append((name, passed, detail))


def main() -> int:
    # 1. Expiry report builds
    try:
        from src.expiry.expiry_tracking import build_expiry_report

        rep = build_expiry_report()
        check("expiry_report", rep.get("status") == "ok", f"scans={rep['summary']['total_scans']}")
    except Exception as exc:
        check("expiry_report", False, f"{type(exc).__name__}: {exc}")

    # 2. Snapshot comparison runs (ok OR need_two_snapshots are both valid)
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
