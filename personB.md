# Person B — Deployment, Persistence & Pilot Instrumentation

> 📋 **Read `PLAN.md` first** — phases, integration gates, go/no-go criteria, and the cut line.
> This file is only your slice of it. **You also own release: nothing deploys that fails
> `npm run lint && npm run build`.**

> **You own (nobody else edits):** `src/api/`, `src/firebase.js`, `vite.config.js`,
> deployment config (`netlify.toml` / `vercel.json` / CI), `requirements.txt`, `.env.example`
> **Never touch:** `src/pages/`, `src/components/`, `src/lib/analytics/`, `scripts/*.py`

Read first: `CLAUDE.md`, `src/api/llm_proxy.py`, `src/lib/persistence/persistence.js`,
`src/lib/persistence/localStorageAdapter.js`, `docs/TECH_PERSISTENCE_AND_SUPABASE.md`

---

## What we are handing YomYom

A deployed web app a store manager opens each morning that says **what to act on today**, computed
from their own real data. The pilot measures whether acting on those alerts makes money.

## Your mission

**Right now this product cannot be handed to anyone.** It runs only on `npm run dev` at
`localhost:5173`, and every decision the store makes is written to `localStorage` — a single
browser profile, wiped by a cache clear, invisible to us. You own the two things that turn a demo
into a pilot: **it has to be reachable, and we have to be able to measure it.**

---

### B-1 (P0) — Ship it to a URL

There is no deployment config in the repo at all.

- Deploy the Vite build to Netlify or Vercel (either is fine; pick one and move).
- **Password-protect it** — this is a real store's cost and margin data. Basic auth or a simple
  gate is enough for a pilot, but it must not be publicly indexable.
- Custom subdomain, HTTPS, and a build that runs from a clean clone.
- `public/data/operational.json` is a build artifact. Decide with Person A whether the deploy
  regenerates it or ships a committed copy — **the pilot cannot depend on someone's laptop.**
- Verify on an actual phone and an actual tablet before calling this done. Store staff will not be
  at a desk.

### B-2 (P0) — Real persistence

`FIREBASE_PROJECT_ID=hackathon26-a6ebd` is already configured and `src/firebase.js` exists — use it.

- Write a `firestoreAdapter.js` behind the **existing** persistence interface. The whole point of
  `persistence.js` delegating to an adapter is that callers don't change. Keep it that way.
- Same six functions: `saveApprovedOrder`, `listApprovedOrders`, `saveRecommendationDecision`,
  `loadRecommendationDecisions`, + the two others already there.
- Fall back to `localStorage` when offline, and reconcile on reconnect. **A convenience store's
  Wi-Fi will drop.** Losing a manager's morning of decisions once is enough to end the pilot.
- Migrate anything already in `localStorage` on first load — don't strand existing data.

### B-3 (P0) — Pilot telemetry (this is the deliverable)

**The pilot's entire purpose is answering "did this help?" — and we currently have no way to know.**

Record, per recommendation shown: type, product, ₪ value at stake, whether the manager approved,
dismissed, or ignored it, and the timestamp. Then build a small internal read-only dashboard for
the four of us: alerts shown vs acted on, acceptance rate by recommendation type, and estimated ₪
impact of the actions taken.

This is what you present to YomYom at the end of the pilot. Without it we hand back opinions.

### B-4 (P1) — LLM proxy, properly

`src/api/llm_proxy.py` is correct and starts cleanly (`/health` returns 200), but it is blocked:

1. **The Gemini key has no prepayment credits** — the API returns 429. Fix billing, or swap to a
   funded provider. Nothing else about the LLM matters until this is resolved.
2. Person C owns the frontend async bug in `explanationProvider.js`. **Coordinate — don't both fix it.**
3. The proxy must be deployed too. `localhost:8000` is useless to a deployed frontend. Deploy it and
   update `VITE_LLM_PROXY_URL`, then tighten the CORS `allow_origins` off `localhost:5173`.
4. Add a server-side timeout and a **cache** — do not re-bill a Gemini call for the same product on
   every page render.

### B-5 (P1) — Environment hygiene

- `.env` currently has `VITE_HOLIDAY_COUNTRY=AT` (Austria) and weather coords `31.95/35.93` (Amman,
  Jordan) with `VITE_NEWS_QUERY=Jordan`. The store is **Kafr Qasim, Israel (32.114/34.972)**.
  Harmless today only because `VITE_ENABLE_LIVE_MARKET_CONTEXT=false`. Fix before enabling.
- `.env.example` must match reality so a teammate can clone and run.
- `.env` is correctly gitignored and has never been committed — **keep it that way.** It holds a
  live Gemini key and a Kaggle token.
- Add `data/internal/snapshots/` and `public/data/operational.json` to `.gitignore`.

---

## Done when

- A teammate on another machine opens the URL on their phone, logs in, and sees real YomYom data.
- A decision made in that browser is still there after clearing cache and reopening.
- You can answer "how many alerts did the manager act on this week, worth how many ₪?" from the
  telemetry dashboard, without opening a terminal.
