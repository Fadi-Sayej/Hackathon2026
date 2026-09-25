#!/usr/bin/env python3
"""
set_user_role.py — give a SmartShelf account its role, or take it away (ADR-029 §2).

    python3 scripts/set_user_role.py EMAIL owner
    python3 scripts/set_user_role.py EMAIL team
    python3 scripts/set_user_role.py EMAIL --revoke
    python3 scripts/set_user_role.py EMAIL --show

The role is a Firebase custom claim, `role: owner | team`. It is the single source that the edge
gate (middleware.ts) and the Firestore rules both read. That is why no email is written into the
code, the rules or any committed file: the account carries its own role.

The person signs in once first, with Google or an email link, and sees "This account has no
access". This script then attaches the role to that account. It creates no accounts.

When it applies: an account that had no role gets it when the page is reloaded, because the
app refreshes a role-less token once. Changing an existing role takes effect at the next token
refresh, within the hour. `--revoke` also stops the person's sessions renewing, so their
access ends within the hour: a token already issued stays valid until it expires.

Credentials are the same as the nightly's owner-state pull: FIREBASE_SERVICE_ACCOUNT_JSON (the
key file's contents) or FIREBASE_SERVICE_ACCOUNT_PATH, plus FIREBASE_PROJECT_ID (default
hackathon26-a6ebd).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ROLES = ("owner", "team")


def _real_auth():
    import firebase_admin
    from firebase_admin import auth, credentials

    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    if raw:
        cred = credentials.Certificate(json.loads(raw))
    elif path:
        cred = credentials.Certificate(path)
    else:
        raise SystemExit("no service account: set FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_PATH")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"projectId": os.environ.get("FIREBASE_PROJECT_ID", "hackathon26-a6ebd")})
    return auth


def main(argv=None, auth=None) -> int:
    parser = argparse.ArgumentParser(description="Give a SmartShelf account its role (ADR-029).")
    parser.add_argument("email")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("role", nargs="?", choices=ROLES)
    action.add_argument("--revoke", action="store_true", help="remove the role; access ends within the hour")
    action.add_argument("--show", action="store_true", help="print the account's role and change nothing")
    args = parser.parse_args(argv)

    auth = auth or _real_auth()
    try:
        user = auth.get_user_by_email(args.email)
    except auth.UserNotFoundError:
        print(f"{args.email}: no such account. They sign in once first (Google or email link), "
              "then run this again.", file=sys.stderr)
        return 1

    claims = dict(user.custom_claims or {})
    if args.show:
        print(f"{args.email}: role {claims.get('role') or '(none)'}")
        return 0

    if args.revoke:
        claims.pop("role", None)
        auth.set_custom_user_claims(user.uid, claims or None)
        auth.revoke_refresh_tokens(user.uid)
        print(f"{args.email}: role removed; sessions will not renew, so access ends within the hour")
        return 0

    claims["role"] = args.role
    auth.set_custom_user_claims(user.uid, claims)
    print(f"{args.email}: role {args.role}. A first role applies when they reload the page; "
          "a changed role at their next token refresh, within the hour.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
