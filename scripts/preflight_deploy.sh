#!/usr/bin/env bash
#
# preflight_deploy.sh — run this BEFORE `vercel deploy --prod` (B-1 / B-2).
#
#   bash scripts/preflight_deploy.sh
#
# Checks the things that actually break a first deploy, in the order they bite:
#   1. a clean build from a clean install (Vercel runs `npm ci`, not `npm install`)
#   2. the data the app reads is committed, and would pass the engine's own validation
#   3. both entry points exist in dist/
#   4. the Basic Auth gate is covered and fails closed
#   5. whether B-2 (Firestore) will activate or silently stay on localStorage
#
# It cannot log into Vercel or Firebase for you — those need your accounts. It
# tells you exactly what to paste where, and what to expect afterwards.

set -uo pipefail
cd "$(dirname "$0")/.."

FAIL=0
WARN=0

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; WARN=$((WARN+1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

printf '\033[1m=== SmartShelf deploy preflight ===\033[0m\n'

# ---------------------------------------------------------------- 1. build
head_ "1. Clean build (Vercel runs npm ci)"
if npm ci --silent >/tmp/preflight_ci.log 2>&1; then
  ok "npm ci resolves"
else
  bad "npm ci FAILED — Vercel will fail the same way. See /tmp/preflight_ci.log"
fi

if npm run build >/tmp/preflight_build.log 2>&1; then
  ok "production build succeeds"
else
  bad "build FAILED — see /tmp/preflight_build.log"
fi

# ---------------------------------------------------------------- 2. data
head_ "2. Data the deployed app reads"
# dashboard.json and catalogue.json are what the owner's app reads; operational.json is the
# telemetry page's frozen input until F13 (#83). Until 2026-09-24 this section checked only
# operational.json, which no owner page has read since the cut-over. The checks, and why
# each exists, are in scripts/check_deploy_data.py (tests/test_check_deploy_data.py).
DATA_OUT=$(python3 scripts/check_deploy_data.py 2>&1); DATA_RC=$?
while IFS= read -r line; do
  [ -z "$line" ] && continue
  case "$line" in
    "OK "*)   ok "${line#OK }" ;;
    "WARN "*) warn "${line#WARN }" ;;
    "BAD "*)  bad "${line#BAD }" ;;
    *)        bad "check_deploy_data.py: $line" ;;
  esac
done <<< "$DATA_OUT"
if [ "$DATA_RC" -ne 0 ] && ! grep -q '^BAD ' <<< "$DATA_OUT"; then
  bad "check_deploy_data.py did not finish (exit $DATA_RC)"
fi

# src/data/marketData.js used to be checked here. It was the demo spine's frozen price file,
# removed on 2026-09-24 (ADR-028); competitor prices reach the owner through
# public/data/dashboard.json, which the engine writes and the nightly commits.

# ---------------------------------------------------------------- 3. entries
head_ "3. Build output"
for entry in dist/index.html dist/telemetry.html; do
  [ -f "$entry" ] && ok "$entry" || bad "$entry missing"
done

# ---------------------------------------------------------------- 4. auth gate
head_ "4. Access gate (this is a real store's cost data)"
if [ -f middleware.ts ]; then
  ok "middleware.ts present"
  if npx vitest run src/__tests__/middleware.test.js >/tmp/preflight_auth.log 2>&1; then
    ok "gate tests pass (blocks anonymous, rejects wrong creds, fails closed 503)"
  else
    bad "gate tests FAIL — do not deploy. See /tmp/preflight_auth.log"
  fi
else
  bad "middleware.ts missing — the URL would be wide open"
fi

# ---------------------------------------------------------------- 5. B-2
head_ "5. B-2 Firestore activation"
MISSING=""
for key in VITE_FIREBASE_API_KEY VITE_FIREBASE_PROJECT_ID VITE_FIREBASE_APP_ID; do
  if [ -f .env ] && grep -qE "^${key}=.+" .env; then :; else MISSING="$MISSING $key"; fi
done
if [ -z "$MISSING" ]; then
  ok "Firebase config present locally — persistence will use Firestore"
  warn "the SAME values must also be set in Vercel, or production stays on localStorage"
else
  warn "Firebase not configured locally (missing:$MISSING)"
  printf '      → persistence stays on localStorage. That WORKS, but decisions live on\n'
  printf '        one device and the team cannot see the manager'\''s decisions remotely.\n'
fi

# ---------------------------------------------------------------- summary
head_ "Summary"
if [ "$FAIL" -gt 0 ]; then
  printf '  \033[31m%d blocking problem(s)\033[0m — fix before deploying.\n' "$FAIL"
else
  printf '  \033[32mReady to deploy.\033[0m %d warning(s).\n' "$WARN"
  cat <<'NEXT'

  Next (needs YOUR Vercel account — nobody else can do these):

    # Use npx. `npm i -g vercel` fails on macOS with EACCES because /usr/local
    # is not user-writable, and `sudo npm i -g` is not the fix — it just puts
    # root-owned files in a system directory. npx needs no install at all.
    npx vercel login
    npx vercel link                   # connect this repo to a Vercel project

    # Set on BOTH Production and Preview. Setting only Production makes every
    # preview deploy serve the "not configured" 503 and look like a broken build.
    npx vercel env add BASIC_AUTH_USER production
    npx vercel env add BASIC_AUTH_USER preview
    npx vercel env add BASIC_AUTH_PASSWORD production
    npx vercel env add BASIC_AUTH_PASSWORD preview

    npx vercel deploy --prod

  Then check, in this order:
    1. open the URL in a private window  → must ask for username/password
    2. log in                            → "شغل اليوم" (Today's work; the app opens in Arabic)
    3. open /telemetry.html              → must ask for the SAME login
    4. reload a page directly            → must not 404 (SPA rewrite)
    5. open it on your phone             → cards readable, buttons tappable

  If step 1 does NOT prompt, stop and remove the deployment: the env vars did not
  apply and a real store's cost data is public.
NEXT
fi

exit $([ "$FAIL" -gt 0 ] && echo 1 || echo 0)
