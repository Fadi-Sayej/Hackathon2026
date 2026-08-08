#!/usr/bin/env bash
#
# pilot_daily.sh — the one command to run after a POS export arrives (task A-2).
#
#   bash scripts/pilot_daily.sh                        # re-run on the current data
#   bash scripts/pilot_daily.sh path/to/export.csv     # import a new export first
#
# Does, in order:
#   1. import the CSV into silver Parquet   (only when a CSV is given)
#   2. gate it on quality                   — STOPS if the export looks broken
#   3. archive a snapshot                   — the raw material for velocity
#   4. derive velocity from snapshot deltas
#   5. rebuild expiry + operational recommendations
#   6. re-match competitor prices          — keeps price ages honest
#   7. export public/data/operational.json  — what the web app reads
#
# Safe to run twice in one morning: importing the same file is idempotent, and a
# second snapshot taken minutes later is ignored as a duplicate (see velocity.py).
#
# Exit 0 = the app has fresh, trustworthy data. Exit 1 = do not publish; read the log.

set -uo pipefail

cd "$(dirname "$0")/.."

PY=python3
INPUT="${1:-}"
STEP=0
FAILED=0

step() {
  STEP=$((STEP + 1))
  printf '\n[%d/7] %s\n' "$STEP" "$1"
}

warn() { printf '  ! %s\n' "$1"; }

# Run a step that must not fail the whole pipeline.
soft() {
  if ! "$@"; then
    warn "step failed (continuing): $*"
    FAILED=1
  fi
}

printf '=== SmartShelf pilot daily refresh — %s ===\n' "$(date '+%Y-%m-%d %H:%M')"

# ---------------------------------------------------------------- 1. import
step "Import POS export"
if [ -n "$INPUT" ]; then
  if [ ! -f "$INPUT" ]; then
    printf '  ABORT: file not found: %s\n' "$INPUT"
    exit 1
  fi
  if ! $PY scripts/import_yomyom_pos.py --input "$INPUT"; then
    printf '  ABORT: import failed. Silver tables left untouched.\n'
    exit 1
  fi
else
  printf '  no CSV given — reusing the current silver tables\n'
fi

# ---------------------------------------------------------------- 2. quality gate
step "Quality gate"
if ! $PY scripts/check_import_quality.py; then
  printf '\n  ABORT: the import failed a quality gate.\n'
  printf '  The previous good data is still live. Fix the export before re-running.\n'
  exit 1
fi

# ---------------------------------------------------------------- 3. snapshot
step "Archive snapshot"
$PY - <<'PY'
import sys
sys.path.insert(0, ".")
from src.snapshots.pos_snapshots import archive_current_silver
from datetime import datetime, timezone
dest = archive_current_silver(imported_at=datetime.now(timezone.utc).isoformat())
print("  snapshot: %s" % (dest.name if dest else "skipped — no new POS export since the last one"))
PY

# ---------------------------------------------------------------- 4. velocity
step "Derive velocity from snapshot deltas"
soft $PY scripts/build_velocity_from_snapshots.py

# ---------------------------------------------------------------- 5. signals
step "Rebuild expiry + operational recommendations"
soft $PY scripts/build_expiry_report.py
soft $PY scripts/generate_operational_recommendations.py

# Competitor prices age every day even when no new prices arrive. Re-running the
# match and export keeps the "seen N months ago" labels honest and drops prices
# that have crossed the staleness cutoff. Without this the UI would freeze at
# whatever age it was first exported with, and quietly present year-old prices.
# Neither step needs network — the collectors do, and they are run separately.
step "Re-match competitor prices (ages them, drops stale)"
soft $PY scripts/join_yomyom_kaggle.py
soft $PY scripts/export_competitor_market_data.py

# ---------------------------------------------------------------- 6. publish
step "Export dashboard JSON"
if ! $PY scripts/export_dashboard_data.py; then
  printf '\n  ABORT: could not write public/data/operational.json — the app would show stale data.\n'
  exit 1
fi

printf '\n=== done ===\n'
if [ "$FAILED" -eq 1 ]; then
  printf 'Finished WITH WARNINGS — some non-critical steps failed (see above).\n'
  printf 'The app has fresh data, but check the warnings before the demo.\n'
else
  printf 'All steps clean. public/data/operational.json is up to date.\n'
fi
printf 'Next: commit the regenerated data, or redeploy so the store sees it.\n'
exit 0
