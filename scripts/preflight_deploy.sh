#!/usr/bin/env bash
#
# preflight_deploy.sh — run this BEFORE `vercel deploy --prod` (B-1 / B-2).
#
#   bash scripts/preflight_deploy.sh
#
# Checks the things that actually break a first deploy, in the order they bite:
#   1. a clean build from a clean install (Vercel runs `npm ci`, not `npm install`)
#   2. the data the app reads is committed, not sitting untracked on this laptop
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
if [ -f public/data/operational.json ]; then
  if git ls-files --error-unmatch public/data/operational.json >/dev/null 2>&1; then
    COUNT=$(python3 -c "import json;print(len(json.load(open('public/data/operational.json'))['recommendations']))" 2>/dev/null || echo 0)
    if [ "$COUNT" -gt 0 ]; then
      ok "operational.json committed, $COUNT recommendations"
    else
      bad "operational.json is committed but EMPTY — the app will show 'No actions yet'"
    fi
  else
    bad "operational.json exists but is NOT COMMITTED — Vercel builds from git, so the deploy would ship without it"
  fi
else
  bad "public/data/operational.json missing — run: bash scripts/pilot_daily.sh"
fi

if git ls-files --error-unmatch src/data/marketData.js >/dev/null 2>&1; then
  if git diff --quiet src/data/marketData.js 2>/dev/null; then
    ok "marketData.js committed and matches the working tree"
  else
    warn "marketData.js has uncommitted changes — deployed price ages will be older than local"
  fi
else
  bad "src/data/marketData.js not committed — competitor prices would be missing"
fi

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
    2. log in                            → "Today's Actions" with Hebrew product names
    3. open /telemetry.html              → must ask for the SAME login
    4. reload a page directly            → must not 404 (SPA rewrite)
    5. open it on your phone             → cards readable, buttons tappable

  If step 1 does NOT prompt, stop and remove the deployment: the env vars did not
  apply and a real store's cost data is public.
NEXT
fi

exit $([ "$FAIL" -gt 0 ] && echo 1 || echo 0)
