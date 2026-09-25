---
ID: ADR-029
Title: Two roles sign in, and the edge gate enforces them
Status: Accepted
Owner: smartshelf-architect
Date: 2026-09-25
Parent: [System Design](../system-design.md) §15
Related Specs: F6-S1, F13-S1
Inputs: [the repository owner's decisions of 2026-09-25 (to be recorded as D-22), D-12, system-design.md §15, ADR-003, ADR-021, ADR-023, middleware.ts, src/firebase.js, firestore.rules]
Updated: 2026-09-25
---

# ADR-029 — Two roles sign in, and the edge gate enforces them

**Status:** Accepted (2026-09-25, by the repository owner, on PR #196). Proposed by
`smartshelf-architect` on his decisions of the same day, and held at `Ready for review` until
he accepted it (HANDOVER rule 2).

## Context

Today the pilot has one shared login. `middleware.ts` puts Basic Auth in front of every path,
and Firebase signs each browser in anonymously, so that owner state can be written to
`stores/yomyom-kafr-qasim/**` (§15, trust boundaries 1 and 2). D-12 put user accounts out of
scope: single store, single user.

That no longer fits. `/telemetry.html` is the team's instrument: it measures what the owner
did with what he was shown (F13), and anyone holding the shared login can open it, the owner
included. F13's go/no-go number should not be something the person being measured watches.
And with one login, nothing the owner records can be told apart from anything the team
presses while looking at his screen.

On 2026-09-25 the repository owner decided:

1. **Real sign-in by email** (option 2 of the two offered), not a second password at the
   Basic Auth gate.
2. **Two roles.** A *team* email sees everything, the owner's app included. An *owner* email
   sees the owner's app and not the telemetry page.
3. **Google sign-in and an email link**, both.
4. **The team is read-only in the owner's app**: nothing a team member presses may be saved
   as the owner's decision.
5. The team emails are given. The owner's email comes before launch.

D-12 changes in part, from "single user" to "single store, two roles". Recording that is
`smartshelf-pm`'s, as D-22. This ADR is how it is built.

## Decision

### 1. Identity: Firebase Authentication, two providers

Google and email link (passwordless) are enabled in the existing project
(`hackathon26-a6ebd`). **Anonymous sign-in is removed**: from the app at cut-over, and
disabled in the console afterwards. A browser that cannot sign in reads nothing and writes
nothing. It does not quietly degrade to an anonymous session.

### 2. Roles: one custom claim, set by an admin script, emails kept out of the repository

Each account carries a Firebase custom claim, `role: "owner" | "team"`. The repository owner
sets it with `scripts/set_user_role.py <email> <role>` (and `--revoke`), run locally with the
service account the nightly already uses. The script creates no accounts: a person signs in
once, and the role is then attached to that account.

The claim is the **single source** for the edge gate and the Firestore rules. No email is
written into the code, `firestore.rules` or a committed config. A signed-in account with no
role gets a "not authorised" page and no data.

### 3. The edge gate verifies the sign-in; Basic Auth is removed

`middleware.ts` stops checking Basic Auth. On every request it verifies the Firebase ID token
carried in a `__session` cookie:

- the signature, against Google's published keys (cached);
- `iss` and `aud` against the project id;
- that it has not expired, and that `email_verified` is true.

The cookie is set by the sign-in page and kept fresh by the app before the token's one-hour
expiry. When it lapses anyway, the page bounces through sign-in, where Firebase's stored
session issues a new token without anyone typing anything.

| Request | No valid token | `owner` | `team` |
|---|---|---|---|
| the sign-in page and its own assets | served | served | served |
| the owner's app (`/`, its chunks, `/data/dashboard.json`, `/data/catalogue.json`) | sent to sign-in (401 for data) | served | served |
| `/telemetry.html`, its `telemetry-*` chunks, `/data/measurement.json`, `/data/operational.json` | sent to sign-in (401 for data) | **403** | served |

A team account lands on `/telemetry.html`, with a link to the owner's app; an owner account
lands on `/`. The gate still fails closed: if the project id is not configured it returns
503, as it does today.

This keeps §15's first trust boundary on the server, not in the browser. The cost data in
`dashboard.json` stays behind a check that runs before any byte is served, and the owner
cannot fetch the telemetry page or its numbers by typing the URL.

### 4. Firestore rules check the role, and only the owner writes

```
stores/yomyom-kafr-qasim/**  read:  role in ['owner', 'team']
                              write: role == 'owner'
everything else               read, write: false
```

That covers answers, outcomes and ADR-021's device register. So the register now counts the
owner's browsers only, which is what Task 4.3 needed it to count. The engine's nightly pull
uses the service account and is unaffected. `scripts/check_firestore_rules.py` is updated
to assert the role split.

### 5. The team's view of the owner's app is read-only, twice over

The app reads the role from the token. For `team`, every control that records owner state
(Done, Later, Undo, the cost answer) is shown as read-only, and a line at the top says it is
the team's view. The rules in §4 refuse the write regardless, so a missed button cannot
record a decision under the owner's name.

What the read-only state looks like, and the sign-in and "not authorised" pages, are shown to
the repository owner as mockups before they are built. He approves anything on screen before
it is built, and the owner will see the sign-in page every day.

### 6. The pilot measurement gets its own file

ADR-023, which is still `Ready for review`, has the engine publish the measurement. It goes
to **`public/data/measurement.json`**, not into `dashboard.json`, because a figure inside a
file the owner's app downloads cannot be kept from the owner by any gate. This binds
ADR-023's file placement, and nothing else in it.

## Rejected options

**Two passwords at the existing gate.** This was the smaller change, offered first. The
owner chose real sign-in: it is per person, it can be revoked, and the email is verified.

**Sign-in inside the app only, with routing by role.** It hides the page but not the files.
With Basic Auth removed, `dashboard.json`, which carries cost prices and margins, would be
public to anyone with the URL. With Basic Auth kept, everyone signs in twice.

**Roles as an email allowlist in `firestore.rules` or a Vercel environment variable.** That
puts people's emails in the repository, or gives the rules and the gate two lists that can
drift apart. One claim on the account is read by both.

**Firebase session cookies minted by a serverless function.** That needs the Admin SDK and
a service-account secret on Vercel, a new secret on the deploy platform. An ID token checked
at the edge needs only Google's public keys.

## Consequences

**We accept:**
- The owner signs in once per device.
- The first request after the token expires takes a silent round trip through the sign-in
  page.
- The gate's first request per edge instance fetches Google's keys.
- The repository owner has console steps: enable the two providers, add the pilot domain to
  Firebase's authorised domains, run the role script for each person, and disable Anonymous
  sign-in after cut-over.
- `e2e/` runs against `vite preview`, which has no edge middleware. So the gate is tested by
  unit tests over `middleware.ts`, as it is today (`src/__tests__/middleware.test.js`), not
  by Playwright.

**We gain:**
- The telemetry page and its numbers are the team's.
- Every recorded decision is provably the owner's, so F13 measures him and not the team.
- Access can be revoked per person.
- The accepted anonymous-auth exposure in §15, where anyone who loaded the app could mint a
  token and write the store's subtree, is closed.

**We will know it was wrong if:** the owner is sent to sign-in during normal use more than
once a session, or a team member needs to act for the owner. The second would be a new
decision, with outcomes then carrying who recorded them, not a loosening of §4.

## Reversibility

Moderate. Reverting the middleware and the app's sign-in commit and re-enabling Anonymous
sign-in restores today's posture. Roles on accounts are harmless if unused. The
`measurement.json` placement costs nothing to keep.

## Binds

| | How this constrains it |
|---|---|
| D-12 | Superseded in part: one store, two roles. Recorded as D-22 by `smartshelf-pm` |
| System Design §15 | Trust boundaries 1 and 2 are rewritten to this ADR on acceptance |
| ADR-003 | The browser still writes owner state, and only as `owner` |
| ADR-021 | The device register counts owner browsers only |
| ADR-023 | The measurement is published to `public/data/measurement.json` |
| F13-S1 | The surface is team-only; FR-135's reader is the team role |
| `scripts/preflight_deploy.sh` §4 | Checks the token gate instead of Basic Auth |
| `docs/operations/deployment.md` | Basic Auth variables go; the console steps above come in |

## Open before launch

The owner's sign-in email. The build and its tests use the two team accounts; the owner's
role is set with the script before the live site switches over.
