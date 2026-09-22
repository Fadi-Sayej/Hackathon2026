#!/usr/bin/env python3
"""Remove Playwright-written device records from the pilot's device register.

WHY THIS EXISTS
    Until #134 the e2e suite built the app with the repo root's `.env`, so it pointed at the
    pilot's own Firebase project. Playwright gives each test a fresh browser context, and
    every context mints an ADR-021 device id and writes it to the owner's live store.

    Measured on 2026-09-22: 48 device records where the truth is two. Forty-six are single
    browser contexts from two test-run windows — 26 on 2026-09-17 and 19 on 2026-09-21.

    The leak is closed (#134 added `.env.e2e`, loaded by `vite build --mode e2e`, which
    blanks the keys `isFirebaseConfigured()` gates on). This removes what it already wrote.

    It matters because the register is the cheapest evidence the pilot has about whether the
    owner is actually opening the app, and at 48-where-two-is-true it cannot answer that. It
    is also the number Phase 4 Task 4.3's precondition rests on (ADR-021).

WHAT IT DELETES, AND WHAT IT REFUSES TO
    Deletes only a record it can positively identify as one browser context inside a known
    test window: `first_seen_at` and `last_seen_at` less than an hour apart, AND first seen
    on a day in TEST_DAYS.

    Keeps everything else, including:
      - any device seen across more than an hour. A device that came back is a device
        someone owns, and there is no undo for this.
      - records from outside the test windows, whatever they look like.
      - the `outcomes` document, entirely. It is never opened by this script. On 2026-09-22
        it held exactly one record, and that record is real: a `price.inverted`
        `confirmed_loss` worth ₪4 per sale, deferred on 2026-09-17 by a returning device
        rather than a fresh test context. Deleting an owner's decision to make a count
        tidier is not a trade this script is willing to make.

USAGE
    python3 scripts/clean_test_devices.py            # dry run, prints the plan
    python3 scripts/clean_test_devices.py --apply    # performs the deletion

    Needs FIREBASE_SERVICE_ACCOUNT_JSON or _PATH plus VITE_FIREBASE_PROJECT_ID and
    VITE_STORE_ID, read from the repo root `.env` the same way the nightly does.

    There is no undo. Run it without --apply first and read the KEEP lines.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The two windows in which the suite is known to have run against the live project. Extend
# this rather than widening the span rule: a day is checkable against CI history, "looks
# automated" is not.
TEST_DAYS = {"2026-09-17", "2026-09-21"}

# Below this, a record is one browser context. Above it, someone came back.
RETURNING_SECONDS = 3600


def env(name: str) -> str | None:
    """Prefer the real environment; fall back to the repo root .env, like the nightly."""
    if os.environ.get(name):
        return os.environ[name]
    path = ROOT / ".env"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def as_utc(value) -> datetime | None:
    """Milliseconds since the epoch, or a Firestore timestamp, or neither."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, timezone.utc)
    if hasattr(value, "timestamp"):
        return datetime.fromtimestamp(value.timestamp(), timezone.utc)
    return None


def main() -> int:
    apply = "--apply" in sys.argv

    import firebase_admin
    from firebase_admin import credentials, firestore

    raw = env("FIREBASE_SERVICE_ACCOUNT_JSON")
    path = env("FIREBASE_SERVICE_ACCOUNT_PATH")
    if not raw and not path:
        print("no service account: set FIREBASE_SERVICE_ACCOUNT_JSON or _PATH", file=sys.stderr)
        return 2
    cred = credentials.Certificate(json.loads(raw)) if raw else credentials.Certificate(path)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"projectId": env("VITE_FIREBASE_PROJECT_ID")})

    store = env("VITE_STORE_ID")
    ref = firestore.client().document(f"stores/{store}/ownerState/devices")
    devices = ref.get().to_dict() or {}

    doomed: list[tuple[str, str]] = []
    kept: list[tuple[str, str]] = []
    for key, record in devices.items():
        if not isinstance(record, dict):
            kept.append((key, "not a record"))
            continue
        first, last = as_utc(record.get("first_seen_at")), as_utc(record.get("last_seen_at"))
        if not first or not last:
            kept.append((key, "no timestamps — cannot classify, so not touched"))
            continue
        span = (last - first).total_seconds()
        if span > RETURNING_SECONDS:
            kept.append((key, f"returning device, span {span / 86400:.1f}d"))
            continue
        day = f"{first:%Y-%m-%d}"
        if day not in TEST_DAYS:
            kept.append((key, f"outside the known test windows ({day})"))
            continue
        doomed.append((key, f"{first:%Y-%m-%d %H:%M}"))

    print(f"store               : {store}")
    print(f"devices in register : {len(devices)}")
    print(f"to keep             : {len(kept)}")
    for key, why in kept:
        print(f"    KEEP   {key[:20]:22} {why}")
    print(f"to delete           : {len(doomed)} single-session records from "
          f"{', '.join(sorted(TEST_DAYS))}")

    if not doomed:
        print("\nNothing to do.")
        return 0
    if not apply:
        print("\nDRY RUN — nothing written. Re-run with --apply to delete. There is no undo.")
        return 0

    from firebase_admin.firestore import DELETE_FIELD

    # Chunked well under Firestore's 500-operation limit; a partial failure leaves the rest
    # of the register untouched rather than the document half-written.
    for start in range(0, len(doomed), 400):
        ref.update({key: DELETE_FIELD for key, _ in doomed[start:start + 400]})

    remaining = ref.get().to_dict() or {}
    print(f"\nAPPLIED. devices now: {len(remaining)} (was {len(devices)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
