#!/usr/bin/env bash
#
# collect_daily.sh — capture one day of the outside market (T1 / #46, Steps 2 & 4).
#
#   bash scripts/collect_daily.sh
#   bash scripts/collect_daily.sh --date 2026-08-11
#
# SEPARATE FROM pilot_daily.sh ON PURPOSE.
# pilot_daily.sh is POS-driven and aborts on an internal quality gate. If the
# market collectors lived inside it, a bad POS export would take the market
# collector down with it — and unlike the POS file, market data cannot be
# re-fetched tomorrow. The price-transparency server keeps only the current day
# (#46 Step 1, verified 2026-08-11), so a day missed here is gone permanently.
#
# Writes an immutable dated snapshot:
#
#   data/external/snapshots/<YYYY-MM-DD>/
#     price_transparency/…
#     delivery_catalog/…
#     _manifest.json
#
# A day whose manifest already reads "ok" is never rewritten. A partial day may
# be retried and upgraded.

set -uo pipefail
cd "$(dirname "$0")/.."

PY=python3
DATE="$(date -u +%Y-%m-%d)"
if [ "${1:-}" = "--date" ] && [ -n "${2:-}" ]; then DATE="$2"; fi

COLLECTED_AT="$(date -u +%Y-%m-%dT%H:%M:%S+00:00)"
SNAP_DIR="data/external/snapshots/${DATE}"
MANIFEST="${SNAP_DIR}/_manifest.json"

declare -a ERRORS_PT=()
declare -a ERRORS_DC=()

printf '=== market snapshot %s ===\n' "$DATE"

# ── Immutability check ───────────────────────────────────────────────────────
# Parsed, not grepped. `grep '"status": *"ok"'` matches the status of any nested
# SOURCE, so a partial day containing one good source read as complete and could
# never be retried — which is the opposite of what Step 4 asks for.
day_complete() {
  [ -f "$MANIFEST" ] || return 1
  $PY - "$MANIFEST" <<'PYEOF'
import json, sys
try:
    manifest = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(1)
sys.exit(0 if manifest.get("status") == "ok" else 1)
PYEOF
}

if day_complete; then
  echo "Day already collected and complete. Nothing to do."
  echo "(Re-running is a no-op by design — overwriting would destroy history"
  echo " that cannot be re-fetched.)"
  exit 0
fi

mkdir -p "$SNAP_DIR"

# True when this source already reads "ok" in today's manifest. Retrying a
# partial day must not re-pull a source that already succeeded: the point of the
# retry is the source that failed, and a fresh pull could return less than what
# is already safely on disk.
source_complete() {
  [ -f "$MANIFEST" ] || return 1
  $PY - "$MANIFEST" "$1" <<'PYEOF'
import json, sys
try:
    manifest = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(1)
sys.exit(0 if manifest.get("sources", {}).get(sys.argv[2], {}).get("status") == "ok" else 1)
PYEOF
}

# ── 1. Price transparency (Dor Alon / Alonit FTPS) ───────────────────────────
# --all-stores collects every branch the chain publishes (156), not just the two
# nearby target locations. A delisting is a chain-wide decision, so telling one
# apart from an ordinary stockout needs chain-wide visibility: on a 3-branch
# snapshot, 94% of products appeared at fewer than 3 branches and the
# concentration test in #49 had power over 6% of the catalog.
# Needs TLS session reuse AND trusting the PASV-reported IP; without both it
# authenticates and then hangs on NLST, which looks exactly like a firewall.
# See src/external/alonit_connector.py.
echo
echo "[1/3] Price transparency"
if source_complete price_transparency; then
  echo "  already complete for ${DATE} — skipping"
elif $PY scripts/run_alonit_collector.py --all-stores --collected-at "$COLLECTED_AT"; then
  echo "  ok"
else
  echo "  FAILED"
  ERRORS_PT+=("run_alonit_collector.py exited non-zero")
fi

# ── 2. Delivery catalog (Wolt) ───────────────────────────────────────────────
# No --url: the connector reads every enabled target from
# configs/delivery_targets.yaml (9 venues, including our own store). It used to
# default to a single hardcoded competitor URL while that config went unread.
echo
echo "[2/3] Delivery catalog"
DC_OUT="$(mktemp)"
if source_complete delivery_catalog; then
  echo "  already complete for ${DATE} — skipping"
  echo '{}' > "$DC_OUT"
elif $PY scripts/run_delivery_venue_connector.py > "$DC_OUT"; then
  echo "  ok"
else
  echo "  FAILED"
  ERRORS_DC+=("run_delivery_venue_connector.py exited non-zero")
fi

# Individual venue failures are reported in the payload even when the exit code
# is zero — a partial run must still reach the manifest, or one dead venue
# either discards eight good ones or passes as a clean day.
while IFS= read -r line; do
  [ -n "$line" ] && ERRORS_DC+=("$line")
done < <($PY - "$DC_OUT" <<'PYEOF'
import json, sys
try:
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(0)
for error in payload.get("errors", []):
    print(error)
PYEOF
)
rm -f "$DC_OUT"

# ── 3. Materialise into the dated snapshot, atomically ───────────────────────
# The collectors write into their own bronze/silver trees. The snapshot is a
# separate, immutable copy keyed by day: it is the time axis #49 reads, and it
# must not move when the lakehouse layout changes.
echo
echo "[3/3] Sealing snapshot"
$PY scripts/seal_snapshot.py --date "$DATE"

# ── Manifest ─────────────────────────────────────────────────────────────────
# Errors travel through files, one per line. Interpolating the arrays into a
# heredoc joined every message into a single string, so nine venue failures
# arrived as one unreadable line — and any message containing a quote broke the
# JSON outright.
ERR_JSON="{}"
if [ ${#ERRORS_PT[@]} -gt 0 ] || [ ${#ERRORS_DC[@]} -gt 0 ]; then
  ERR_PT_FILE="$(mktemp)"; ERR_DC_FILE="$(mktemp)"
  [ ${#ERRORS_PT[@]} -gt 0 ] && printf '%s\n' "${ERRORS_PT[@]}" > "$ERR_PT_FILE"
  [ ${#ERRORS_DC[@]} -gt 0 ] && printf '%s\n' "${ERRORS_DC[@]}" > "$ERR_DC_FILE"
  ERR_JSON=$($PY - "$ERR_PT_FILE" "$ERR_DC_FILE" <<'PYEOF'
import json, sys
from pathlib import Path

def lines(path):
    text = Path(path).read_text(encoding="utf-8") if Path(path).exists() else ""
    return [line for line in text.splitlines() if line.strip()]

errors = {}
for source, path in (("price_transparency", sys.argv[1]), ("delivery_catalog", sys.argv[2])):
    found = lines(path)
    if found:
        errors[source] = found
print(json.dumps(errors))
PYEOF
)
  rm -f "$ERR_PT_FILE" "$ERR_DC_FILE"
fi

echo
$PY scripts/write_snapshot_manifest.py --date "$DATE" --errors "$ERR_JSON"
STATUS=$?

echo
if [ "$STATUS" -eq 0 ]; then
  echo "Snapshot ${DATE} sealed."
else
  echo "Snapshot ${DATE} FAILED — no usable data collected."
  echo "This day cannot be re-collected tomorrow. Investigate now."
fi
exit "$STATUS"
