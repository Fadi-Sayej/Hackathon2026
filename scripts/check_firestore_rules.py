#!/usr/bin/env python3
"""check_firestore_rules.py — do the DEPLOYED Firestore rules match `firestore.rules`?

Why this exists
---------------
On 2026-09-13 the pilot's data isolation came to rest entirely on one line of
`firestore.rules`:

    match /stores/yomyom-kafr-qasim/{document=**}   allow read, write: if request.auth != null
    match /{document=**}                            allow read, write: if false

Vercel Preview and Production carry the same six `VITE_FIREBASE_*` values, so while both
environments also shared a store id, a preview deployment of ANY branch could write the
pilot's owner state. The fix was to point Preview at `preview-sandbox`, which the second
rule then denies.

That fix is only as good as the rules that are actually deployed, and **nothing checked
them**. `firestore.rules` is deployed by hand (`firebase deploy --only firestore:rules`);
no workflow does it, so the committed file and the live ruleset can drift silently — and a
console edit loosening the catch-all would make the isolation decorative with nothing to
say so.

What it does NOT overlap with
-----------------------------
`npm run check:firebase-live` writes, reads and deletes a probe document against the PILOT
store. That exercises the **allow** branch for `yomyom-kafr-qasim` and says nothing about
whether any other store is denied. The isolation rests on the **deny** branch, which no
live probe here covers.

This reads the deployed ruleset text instead, which settles both branches at once: if the
deployed source is the committed source, the deny branch is whatever the file says.

Deliberately read-only. It touches no document and creates no anonymous user — it calls
`firebaserules.googleapis.com` for the released ruleset and diffs the text. That matters:
the alternative on the table was a client `getDoc` against `stores/preview-sandbox/...`,
which settles the same question but connects as a new anonymous user against the
production project.

Usage:
  FIREBASE_SERVICE_ACCOUNT_PATH=./secrets/firebase-service-account.json \\
    python3 scripts/check_firestore_rules.py

  exit 0  deployed ruleset is byte-identical to firestore.rules
  exit 1  they differ — the diff is printed, committed against deployed
  exit 2  no credential, or the API refused. NOT a drift failure, and says so:
          a missing credential and a loosened rule are different sentences.
"""
from __future__ import annotations

import difflib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES_FILE = ROOT / "firestore.rules"
RELEASE = "cloud.firestore"
API = "https://firebaserules.googleapis.com/v1"


def _credentials():
    path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    blob = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not (path or blob):
        return None, None
    from google.oauth2 import service_account
    import google.auth.transport.requests as gr

    info = json.loads(blob) if blob else json.loads(Path(path).read_text(encoding="utf-8"))
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/firebase.readonly"])
    creds.refresh(gr.Request())
    return creds, info["project_id"]


def _get(url: str, token: str) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    return json.load(urllib.request.urlopen(request, timeout=30))


def main() -> int:
    local = RULES_FILE.read_text(encoding="utf-8").strip()

    try:
        creds, project = _credentials()
    except Exception as exc:  # noqa: BLE001 — a broken credential is not drift
        print(f"SKIP  could not load a service account: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if creds is None:
        print("SKIP  no FIREBASE_SERVICE_ACCOUNT_PATH or _JSON; cannot read the deployed rules.",
              file=sys.stderr)
        print("      This is a missing credential, not a drift failure.", file=sys.stderr)
        return 2

    try:
        releases = _get(f"{API}/projects/{project}/releases", creds.token).get("releases", [])
        named = [r for r in releases if r["name"].endswith(RELEASE)]
        if not named:
            print(f"FAIL  project {project} has no {RELEASE} release — nothing is deployed.",
                  file=sys.stderr)
            return 1
        ruleset = _get(f"{API}/{named[0]['rulesetName']}", creds.token)
    except urllib.error.HTTPError as exc:
        print(f"SKIP  firebaserules API refused ({exc.code}); the service account likely "
              f"lacks firebaserules.viewer.", file=sys.stderr)
        print("      This is a permissions answer, not a drift answer.", file=sys.stderr)
        return 2

    deployed = "".join(f["content"] for f in ruleset["source"]["files"]).strip()
    print(f"project:  {project}")
    print(f"release:  {RELEASE} -> {named[0]['rulesetName'].split('/')[-1]}")
    print(f"deployed: {ruleset.get('createTime')}")

    if deployed == local:
        print("\nOK    the deployed ruleset is byte-identical to firestore.rules")
        return 0

    print("\nFAIL  the deployed ruleset differs from firestore.rules.", file=sys.stderr)
    print("      Whatever this repository says about who can read or write the pilot's",
          file=sys.stderr)
    print("      data is describing a file that is not in force.\n", file=sys.stderr)
    for line in difflib.unified_diff(local.splitlines(), deployed.splitlines(),
                                     "committed firestore.rules", "deployed ruleset",
                                     lineterm="", n=2):
        print(f"  {line}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
