"""
check_collection_health.py — has the collector actually been collecting? (T1 / #46 Step 5)

    python3 scripts/check_collection_health.py
    python3 scripts/check_collection_health.py --max-age-days 1 --window 30
    python3 scripts/check_collection_health.py --json

Exits non-zero when history has stopped accumulating, so a schedule can shout.

WHY THIS EXISTS
---------------
#46 Step 5 names the failure mode outright:

    "A collector that dies silently in week 3 and is noticed in week 8 has cost
     five weeks of irreplaceable history. This is the single most likely way
     this track fails."

A failing job sends an email. The dangerous cases send nothing:

    * the schedule stops firing              — no run, no failure, no email
    * the job succeeds and collects nothing  — green tick, empty day
    * a source returns a short run           — green tick, unusable day

This checks the only thing that actually matters: **is there a fresh, usable
snapshot, and are there holes behind it?** It reads the manifests and the same
usability rules the analysis uses, so it cannot disagree with them.

WHAT IT CANNOT CATCH
--------------------
If GitHub Actions stops running workflows altogether, a workflow cannot notice.
Running this at the START of the collection job narrows that to "the first run
after the outage tells us", and the separate schedule in
`.github/workflows/collection-health.yml` narrows it further, since two crons
failing silently at once is less likely than one. Neither is a substitute for
someone glancing at the snapshot count once a week.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import EXTERNAL_SNAPSHOTS_ROOT
from src.market.presence import PRICE_TRANSPARENCY, load_presence

# Yesterday is fine; the day before is not. The collector runs nightly, so by
# the time two days have passed something has been wrong for a full cycle.
DEFAULT_MAX_AGE_DAYS = 2
DEFAULT_WINDOW = 30


def assess(
    source_id: str = PRICE_TRANSPARENCY,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    window: int = DEFAULT_WINDOW,
    today: date | None = None,
    root: Path | None = None,
) -> dict:
    today = today or date.today()
    series = load_presence(root=root, source_id=source_id)
    usable = list(series.days)

    problems: list[str] = []
    latest = usable[-1] if usable else None
    age = (today - latest).days if latest else None

    if latest is None:
        problems.append("no usable snapshot exists at all")
    elif age > max_age_days:
        problems.append(
            "latest usable snapshot is %s — %d days old (limit %d). History has "
            "stopped accumulating and cannot be backfilled."
            % (latest, age, max_age_days)
        )

    # Holes inside the window. A gap is not just cosmetic: #46 asks for 30
    # CONSECUTIVE days, and a missing day breaks the run rather than delaying it.
    window_start = today - timedelta(days=window - 1)
    expected = {window_start + timedelta(days=i) for i in range(window)}
    # Only count days from the first collection onward — days before the project
    # started are not gaps.
    if usable:
        expected = {d for d in expected if d >= usable[0]}
    missing = sorted(d for d in expected if d not in set(usable) and d < today)
    if missing:
        problems.append(
            "%d day(s) missing inside the last %d: %s"
            % (len(missing), window, ", ".join(str(d) for d in missing[:10]))
        )

    # Days that exist on disk but the analysis refuses. These are the quiet ones:
    # the job was green and the day is still worthless.
    skipped = {str(day): reason for day, reason in sorted(series.skipped.items())}
    if skipped:
        problems.append(
            "%d collected day(s) are unusable: %s"
            % (len(skipped), "; ".join(f"{d} ({r})" for d, r in list(skipped.items())[:5]))
        )

    consecutive = 0
    if usable:
        consecutive = 1
        for earlier, later in zip(usable, usable[1:]):
            consecutive = consecutive + 1 if (later - earlier).days == 1 else 1

    return {
        "checked_on": today.isoformat(),
        "source": source_id,
        "usable_days": len(usable),
        "first_day": str(usable[0]) if usable else None,
        "latest_day": str(latest) if latest else None,
        "latest_age_days": age,
        "consecutive_days_to_date": consecutive,
        "target_consecutive_days": DEFAULT_WINDOW,
        "missing_days": [str(d) for d in missing],
        "unusable_days": skipped,
        "problems": problems,
        "healthy": not problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    parser.add_argument("--source", default=PRICE_TRANSPARENCY)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = assess(args.source, args.max_age_days, args.window)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["healthy"] else 1

    print("Collection health — %s" % report["source"])
    print("  snapshots root : %s" % EXTERNAL_SNAPSHOTS_ROOT)
    print("  usable days    : %d (first %s, latest %s)"
          % (report["usable_days"], report["first_day"], report["latest_day"]))
    print("  latest age     : %s day(s)" % report["latest_age_days"])
    print("  consecutive    : %d of %d"
          % (report["consecutive_days_to_date"], report["target_consecutive_days"]))

    if report["healthy"]:
        print("\n  ✅ Healthy — history is still accumulating.")
        return 0

    print("\n  ❌ PROBLEMS — a day lost here cannot be re-collected:")
    for problem in report["problems"]:
        print("     • %s" % problem)
    print("\n  The price-transparency server keeps only the current day.")
    print("  Investigate today, not next week.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
