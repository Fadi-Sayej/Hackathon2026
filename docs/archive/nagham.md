> # ⚠ LEGACY — NON-AUTHORITATIVE
>
> Retained for history. Describes modules that no longer exist, or designs superseded
> on 2026-09-08 by the System Design. Do not act on it.
>
> **Canonical sources:** [`docs/README.md`](../README.md)

---

# Nagham — Track B: Deployment, Persistence & Pilot Instrumentation

> 📋 **Read `PLAN.md` first** — phases, integration gates, go/no-go criteria, and the cut line.
> This file is only your slice of it. **You also own release: nothing deploys that fails
> `npm run lint && npm run build`.**

> **You own (nobody else edits):** `src/api/`, `src/firebase.js`, `vite.config.js`,
> deployment config (`netlify.toml` / `vercel.json` / CI), `requirements.txt`, `.env.example`
> **Never touch:** `src/pages/`, `src/components/`, `src/lib/analytics/`, `scripts/*.py`

Read first: `CLAUDE.md`, `src/api/llm_proxy.py`, `src/lib/persistence/persistence.js`,
`src/lib/persistence/localStorageAdapter.js`, `docs/TECH_PERSISTENCE_AND_SUPABASE.md`

---

## 📊 Status at a glance (2026-08-07)

| Task | State | What's left |
|---|---|---|
| **B-1** deploy | ⏸ code done, gate green | Live `vercel deploy --prod` on a teammate's Vercel account |
| **B-2** persistence | ⏸ code done | Activate: `VITE_FIREBASE_*` config + Anonymous auth in Firebase console |
| **B-3** telemetry | ✅ **done & verified** | — (cross-device view lights up when B-2 is active) |
| **B-4** LLM proxy | 🟡 partial | Gemini billing (429), proxy deploy, Anas's Track-C async bug |
| **B-5** env hygiene | ✅ **done** | Mirror coord fix into local `.env` if one exists |
| **B-6** snapshot durability | ✅ **done** | Fadi to confirm option 1 vs Firestore mirror |

Everything buildable without other people's credentials is done and green
(`npm run lint`, 117 JS tests, 6 Python proxy tests, two-entry build). The three
open items each need someone else: Firebase console (B-2), Gemini key + Anas (B-4),
the teammate's Vercel account (B-1). Per-task detail below.

---

## What we are handing YomYom

A deployed web app a store manager opens each morning that says **what to act on today**, computed
from their own real data. The pilot measures whether acting on those alerts makes money.

## Your mission

**Right now this product cannot be handed to anyone.** It runs only on `npm run dev` at
`localhost:5173`, and every decision the store makes is written to `localStorage` — a single
browser profile, wiped by a cache clear, invisible to us. You own the two things that turn a demo
into a pilot: **it has to be reachable, and we have to be able to measure it.**

> **Update (2026-08-07):** both are now solved in code. Persistence has a Firestore adapter behind
> the same interface (B-2) — decisions sync to the cloud and survive a cache clear once the Firebase
> config is set; and the telemetry dashboard (B-3) is built and verified. What remains is
> activation, not implementation — see the status table above.

---

### B-1 (P0) — Ship it to a URL

> **STATUS (2026-08-07) — ⏸ code done, deploy blocked externally.** `vercel.json`, `middleware.ts`
> (Basic Auth, fails closed with 503) and `.vercelignore` are committed; clean `npm ci` → lint +
> build pass (release gate green). The live `vercel deploy --prod` is being run from another
> teammate's Vercel account, so the deploy itself sits with them — not re-run here.

There is no deployment config in the repo at all.

- Deploy the Vite build to Netlify or Vercel (either is fine; pick one and move).
- **Password-protect it** — this is a real store's cost and margin data. Basic auth or a simple
  gate is enough for a pilot, but it must not be publicly indexable.
- Custom subdomain, HTTPS, and a build that runs from a clean clone.
- `public/data/operational.json` is a build artifact. Decide with Fadi whether the deploy
  regenerates it or ships a committed copy — **the pilot cannot depend on someone's laptop.**
- Verify on an actual phone and an actual tablet before calling this done. Store staff will not be
  at a desk.

### B-2 (P0) — Real persistence

> **STATUS (2026-08-07) — ⏸ code done, blocked on Firebase credentials.** Built:
> `src/firebase.js` (client init + anonymous auth + offline cache), `firestoreAdapter.js`
> (local-first, same 6 sync methods, localStorage fallback, two-way last-write-wins reconcile on
> load/reconnect, first-load migration), adapter selection in `persistence.js`, and
> `firestore.rules`. Lint + tests + build pass. **Not activated:** needs the `VITE_FIREBASE_*`
> web-config values + Anonymous sign-in enabled in the Firebase console (`hackathon26-a6ebd`), which
> depends on console access. Until then persistence stays on localStorage automatically.

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

> **STATUS (2026-08-07) — ✅ built & verified.** Recording was already in place: every
> operational decision persists `type`, `productName`, ₪ `impactIls`, status, dismissal reason and
> timestamp (`toDecisionRecord` → `saveRecommendationDecision`), and B-2 mirrors those to Firestore
> so the team sees the manager's real decisions, not one browser's. The missing piece — the
> read-only dashboard — is now built, entirely within B-track ownership (no Track C/D files touched):
>
> - `src/telemetry/telemetryModel.js` — pure aggregation. Joins the shown set (operational.json,
>   scored by the same `actionPriority` engine the store-floor screen uses, so ₪ figures can't
>   disagree with what the manager saw) against decisions. Computes shown vs acted-on, acceptance
>   rate by type, ₪ impact captured, and the dismissal-reason breakdown (WRONG_DATA rate vs the
>   <10% target — PLAN §5's most important row).
> - `src/telemetry/TelemetryDashboard.jsx` + `main.jsx` + `telemetry.html` — the dashboard, a
>   second Vite entry (`vite.config.js` multi-page) served behind the same Basic Auth gate.
> - `src/telemetry/__tests__/telemetryModel.test.js` — unit tests for the aggregation.
>
> **View it:** `npm run dev` → `http://localhost:5173/telemetry.html`; in prod, `/telemetry.html`
> behind the login. **Verified:** `npm run lint`, 117 tests, and a clean two-entry build all pass.
>
> Two honesty decisions (documented in the dashboard footer): acceptance is reported as
> **done ÷ decided** with backlog coverage shown alongside (we don't log per-alert impressions, so
> raw done ÷ 2,183 would read ~0% and make a trusted tool look broken); ₪ is per-sale, not
> multiplied by volume (stock counts are unreliable).
>
> **Dependency:** cross-device aggregation lights up only once **B-2 is activated** (Firebase
> config from the console). Until then the dashboard reads this device's localStorage — same numbers,
> single device.

### B-4 (P1) — LLM proxy, properly

> **STATUS (2026-08-07) — 🟡 credential-free parts done; still blocked on the key.** Done in
> `src/api/llm_proxy.py` (6 pytest cases pass, `tests/test_llm_proxy.py`):
> - **Caching** — TTL/LRU in-memory cache on `/explain` and `/report`, keyed by payload hash, so an
>   identical payload is not re-billed on every render (item 4). Test proves a repeat payload makes
>   one upstream call.
> - **Timeouts on both endpoints** — `/report` now has the same upstream timeout + 429 handling as
>   `/explain` (item 4).
> - **Configurable CORS** — origins from `LLM_ALLOWED_ORIGINS` (default `localhost:5173`) so a deploy
>   points it off localhost (item 3, code side).
> - **Graceful startup** — no longer raises at import when the key/SDK is missing; `/health` reports
>   `llm_configured`, and endpoints return 503 (not 500) when unconfigured. Makes it deployable and
>   testable without the key.
>
> **Still blocked (needs credentials / others):** (1) the Gemini key has no credits — 429; (2) the
> actual deploy of the proxy + setting `VITE_LLM_PROXY_URL`; (3) Anas's async bug in
> `explanationProvider.js` (Track C). `VITE_LLM_PROXY_URL` stays commented out until (1) and (3) land.

`src/api/llm_proxy.py` is correct and starts cleanly (`/health` returns 200), but it is blocked:

1. **The Gemini key has no prepayment credits** — the API returns 429. Fix billing, or swap to a
   funded provider. Nothing else about the LLM matters until this is resolved.
2. Anas owns the frontend async bug in `explanationProvider.js`. **Coordinate — don't both fix it.**
3. The proxy must be deployed too. `localhost:8000` is useless to a deployed frontend. Deploy it and
   update `VITE_LLM_PROXY_URL`, then tighten the CORS `allow_origins` off `localhost:5173`.
4. Add a server-side timeout and a **cache** — do not re-bill a Gemini call for the same product on
   every page render.

### 🔴 B-6 (P0 — from Fadi) — Snapshot durability

> **STATUS (2026-08-07) — ✅ done (option 1).** Took the `.gitignore` exception path (Fadi's first
> option): appended end-of-file negations un-ignoring the `data/internal/snapshots/` subtree so
> `products.parquet` / `inventory.parquet` / `meta.json` are committed to git, overriding the
> `snapshots/` and global `*.parquet` ignores. Verified with `git check-ignore` / `git add -n`:
> snapshot parquet is now committable, other parquet (e.g. `silver_pos`) stays ignored. Full write-up
> in `docs/SNAPSHOT_DURABILITY.md` (incl. the daily commit step and the privacy caveat: keep the
> repo private). **Coordinate check for Fadi:** confirm option 1 is acceptable vs mirroring to
> Firestore (option 2) once B-2 is live — either works; git already gives a durable, continuous
> series.

**`*.parquet` is globally gitignored** (`.gitignore:28`), so POS snapshots under
`data/internal/snapshots/` are **never committed**. Those snapshots are the *only* source of
sales velocity — the POS export has no sales history, so velocity is reconstructed entirely
from stock differences between them.

That means the pilot's most valuable dataset currently lives on one laptop, is not backed up,
and dies with a reformat. It also cannot accumulate: if Malik receives the CSV on his machine
and Fadi runs the pipeline on his, neither builds a continuous history.

Velocity needs a **continuous, durable** series. Decide with Fadi and implement:

- a `.gitignore` exception for `data/internal/snapshots/**/*.parquet` (they are small), **or**
- push snapshots to Firestore / object storage alongside B-2, **or**
- one designated machine owns ingestion, with a scheduled backup.

Any of the three works. Doing none of them means that on 13/08 we hand YomYom a product whose
core feature quietly resets whenever a laptop does.

### B-5 (P1) — Environment hygiene

> **STATUS (2026-08-07) — ✅ done, with one bullet superseded.** Fixed the geo config in
> `.env.example`: weather coords corrected from Amman (31.95/35.93) to **Kafr Qasim (32.114/34.972)**;
> `VITE_HOLIDAY_COUNTRY=IL` and the news query were already Israel. Added an optional
> `VITE_COMAX_PROXY_URL` placeholder so the template covers every var the code reads.
> `.env` is not present in the repo (correctly gitignored via `.env` / `.env*`); if a local `.env`
> exists on the run machine, mirror the coord fix there before enabling live context.
> **Superseded:** the "add `data/internal/snapshots/` and `public/data/operational.json` to
> `.gitignore`" bullet is intentionally NOT done — B-6 commits snapshots for velocity durability, and
> `docs/DEPLOYMENT.md` commits `operational.json` (Vercel can't regenerate it). Verified both are
> still un-ignored correctly.

- `.env` currently has `VITE_HOLIDAY_COUNTRY=AT` (Austria) and weather coords `31.95/35.93` (Amman,
  Jordan) with `VITE_NEWS_QUERY=Jordan`. The store is **Kafr Qasim, Israel (32.114/34.972)**.
  Harmless today only because `VITE_ENABLE_LIVE_MARKET_CONTEXT=false`. Fix before enabling.
- `.env.example` must match reality so a teammate can clone and run.
- `.env` is correctly gitignored and has never been committed — **keep it that way.** It holds a
  live Gemini key and a Kaggle token.
- Add `data/internal/snapshots/` and `public/data/operational.json` to `.gitignore`.

---

## Done when

- ⏸ A teammate on another machine opens the URL on their phone, logs in, and sees real YomYom data.
  — _config done; waiting on the live Vercel deploy (B-1)._
- ⏸ A decision made in that browser is still there after clearing cache and reopening.
  — _Firestore adapter written (B-2); waiting on Firebase console activation._
- ✅ You can answer "how many alerts did the manager act on this week, worth how many ₪?" from the
  telemetry dashboard, without opening a terminal. — _built and verified (B-3)._
