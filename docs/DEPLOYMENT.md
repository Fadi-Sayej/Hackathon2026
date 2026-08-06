# SmartShelf Deployment

This is the B-1 deployment runbook for the current Vite app.

## Decision

- Provider: Vercel.
- Release source: `main`.
- Build command: `npm run build`.
- Install command: `npm ci`.
- Output directory: `dist`.
- Access protection: Vercel Routing Middleware with HTTP Basic Auth.
- Production deploy command: `vercel deploy --prod`.
- Rollback command: `vercel rollback <deployment-url-or-id>`.

Vercel was chosen because this repository is a static Vite app, the Vercel CLI is already available
on the deployment machine, and Vercel supports Vite builds, SPA rewrites, environment variables,
HTTPS, deployment URLs, and rollbacks.

## Required Vercel Environment Variables

Set these in Vercel before any preview or production deployment:

| Name | Environment | Purpose |
|---|---|---|
| `BASIC_AUTH_USER` | Preview and Production | Login username for the pilot URL. |
| `BASIC_AUTH_PASSWORD` | Preview and Production | Login password for the pilot URL. |
| `VITE_LLM_PROXY_URL` | Optional | HTTPS URL for the deployed LLM proxy. Leave unset to use rule-based explanations. |

The middleware fails closed: if either Basic Auth variable is absent, every request returns HTTP 503
instead of serving store data publicly.

Do not commit passwords, API keys, cookies, Vercel project metadata, `.env`, `.env.local`,
service-account files, or `.vercel/`.

## Data Refresh

The committed bundle already contains the real YomYom product catalog in `src/data/demoProducts.js`.
That is enough for the deployed app to show real product names, categories, prices, and inventory.

The daily operational export lives at `public/data/operational.json`, but that file is generated and
gitignored. A clean Vercel build will not include it unless the deployment owner first chooses one of
these B-1 data-shipping paths:

1. Run `npm run data:refresh`, inspect `public/data/operational.json`, and intentionally commit the
   generated `public/data/*.json` files for each release.
2. Add a provider-side build step that can regenerate the JSON from available committed or hosted
   data.
3. Serve the JSON from durable storage after B-2/B-6 decides where pilot data lives.

Do not implement the runtime-fetch split from Issue #24 as part of B-1.

## Verification Checklist

Before promoting a production deployment:

- `npm ci`
- `npm test`
- `npm run test:py`
- `npm run test:pipeline`
- `npm run lint`
- `npm run build`
- `git diff --check`
- `vercel deploy --dry`
- `vercel deploy --prod`

After deployment:

- Unauthenticated request returns `401` when auth is configured.
- Missing auth variables return `503`, never public app data.
- Authenticated request returns the app HTML.
- HTTPS is active.
- Browser refresh and direct routes load the SPA.
- Static assets load behind auth.
- No `localhost` URLs are present in built client assets.
- Real YomYom data is visible.
- Phone QA passes on a real phone.
- Tablet QA passes on a real tablet.
- Rollback is tested with `vercel rollback <deployment-url-or-id>`.

## Custom Domain

Use the default Vercel deployment URL until the DNS owner confirms a custom subdomain. Do not point
customer traffic at an unprotected or unverified domain.
