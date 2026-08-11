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
if [ -f "$MANIFEST" ] && grep -q '"status": *"ok"' "$MANIFEST"; then
  echo "Day already collected and complete. Nothing to do."
  echo "(Re-running is a no-op by design — overwriting would destroy history"
  echo " that cannot be re-fetched.)"
  exit 0
fi

mkdir -p "$SNAP_DIR"

# ── 1. Price transparency (Dor Alon / Alonit FTPS) ───────────────────────────
# Needs TLS session reuse AND trusting the PASV-reported IP; without both it
# authenticates and then hangs on NLST, which looks exactly like a firewall.
# See src/external/alonit_connector.py.
echo
echo "[1/3] Price transparency"
if $PY scripts/run_alonit_collector.py --collected-at "$COLLECTED_AT"; then
  echo "  ok"
else
  echo "  FAILED"
  ERRORS_PT+=("run_alonit_collector.py exited non-zero")
fi

# ── 2. Delivery catalog (Wolt) ───────────────────────────────────────────────
echo
echo "[2/3] Delivery catalog"
if $PY scripts/run_delivery_venue_connector.py; then
  echo "  ok"
else
  echo "  FAILED"
  ERRORS_DC+=("run_delivery_venue_connector.py exited non-zero")
fi

# ── 3. Materialise into the dated snapshot, atomically ───────────────────────
# The collectors write into their own bronze/silver trees. The snapshot is a
# separate, immutable copy keyed by day: it is the time axis #49 reads, and it
# must not move when the lakehouse layout changes.
echo
echo "[3/3] Sealing snapshot"
$PY - "$DATE" <<'PYEOF'
import shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, ".")
from src.common.paths import (
    EXTERNAL_BRONZE_ROOT, EXTERNAL_SILVER_ROOT, get_snapshot_path,
)

day = sys.argv[1]
y, m, d = day.split("-")

def materialise(source_id: str, candidates):
    dest = get_snapshot_path(source_id, day)
    present = [c for c in candidates if c.exists() and any(c.rglob("*"))]
    if not present:
        print(f"  {source_id}: nothing collected today")
        return
    # Write to a temp dir alongside, then move into place, so a crash mid-copy
    # never leaves a half-populated day that later reads as a real absence.
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=dest.parent, prefix=f".{source_id}.tmp."))
    copied = 0
    for src in present:
        for path in src.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(src)
            target = tmp / src.name / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            copied += 1
    if dest.exists():
        shutil.rmtree(dest)
    tmp.replace(dest)
    print(f"  {source_id}: {copied} files")

materialise("price_transparency", [
    EXTERNAL_BRONZE_ROOT / "alonit" / y / m / d,
    EXTERNAL_SILVER_ROOT / "alonit_prices" / "alonit" / y / m / d,
])
materialise("delivery_catalog", [
    EXTERNAL_BRONZE_ROOT / "delivery_catalog" / y / m / d,
    EXTERNAL_SILVER_ROOT / "products" / "delivery_catalog" / y / m / d,
])
PYEOF

# ── Manifest ─────────────────────────────────────────────────────────────────
ERR_JSON="{}"
if [ ${#ERRORS_PT[@]} -gt 0 ] || [ ${#ERRORS_DC[@]} -gt 0 ]; then
  ERR_JSON=$($PY - <<PYEOF
import json
errors = {}
pt = """${ERRORS_PT[*]:-}""".strip()
dc = """${ERRORS_DC[*]:-}""".strip()
if pt: errors["price_transparency"] = [pt]
if dc: errors["delivery_catalog"] = [dc]
print(json.dumps(errors))
PYEOF
)
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
