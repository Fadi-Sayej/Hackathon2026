#!/usr/bin/env python3
"""Give a dateless deferral an end, so the entry returns to the daily surface.

WHY THIS EXISTS
    Until #142, `EntryCard`'s "Later" sent `{ status: 'deferred' }` with no date.
    `recordOutcome` writes `deferred_until` only when it is non-null, and `compose.js:26`
    reads a missing `deferred_until` as deferred indefinitely. So the gentlest-sounding
    button on the owner's daily screen removed the entry permanently.

    #142 fixed that forward — the surface now offers an Undo. It did nothing for records
    already written. This repairs those.

    Measured on the live store 2026-09-22, the pilot's outcomes document held exactly one
    record in ten days, and it was this failure in miniature:

        entry   53de0bd7ec5d5e1b
        barcode 7290111567759 — עוגת הבית דבש קלאסית 400 גרם
        signal  price.inverted · confirmed_loss · ₪4 per sale
        status  deferred, no deferred_until, 2026-09-17 09:47

    Still published five days later: the price is still inverted, and the entry has been
    invisible to the owner since the tap.

REPAIR, NOT ERASURE
    Sets `deferred_until` instead of deleting the outcome. Both restore the entry; only this
    one keeps the fact that the owner deferred it, which is the pilot's behavioural record
    and the thing F13 will eventually count.

    The value is NOW, not a duration. That deliberately decides nothing about OQ-604 — how
    long "later" should mean is still the PM's, and picking 4 hours or a week here would
    close it by the back door. This says only that a deferral which was never given an end,
    ends today.

    A record that already carries `deferred_until` is left alone, whatever its value.

USAGE
    python3 scripts/lapse_dateless_deferral.py                 # dry run, every dateless one
    python3 scripts/lapse_dateless_deferral.py --apply
    python3 scripts/lapse_dateless_deferral.py --entry <id> --apply

    Needs FIREBASE_SERVICE_ACCOUNT_JSON or _PATH plus VITE_FIREBASE_PROJECT_ID and
    VITE_STORE_ID, read from the repo root `.env` the same way the nightly does.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


def main() -> int:
    apply = "--apply" in sys.argv
    only = None
    if "--entry" in sys.argv:
        only = sys.argv[sys.argv.index("--entry") + 1]

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
    ref = firestore.client().document(f"stores/{store}/ownerState/outcomes")
    outcomes = ref.get().to_dict() or {}

    targets = []
    for key, record in outcomes.items():
        if not isinstance(record, dict) or record.get("status") != "deferred":
            continue
        if "deferred_until" in record:
            continue
        if only and key != only:
            continue
        targets.append((key, record))

    print(f"store             : {store}")
    print(f"outcomes          : {len(outcomes)}")
    print(f"dateless deferrals: {len(targets)}")
    for key, record in targets:
        snap = record.get("snapshot") or {}
        at = record.get("at")
        when = f"{datetime.fromtimestamp(at / 1000, timezone.utc):%Y-%m-%d %H:%M}" if at else "?"
        print(f"    {key}  {snap.get('signal_family', '?')}  "
              f"barcode={snap.get('barcode', '?')}  deferred {when} UTC")

    if not targets:
        print("\nNothing to do.")
        return 0

    now_ms = int(time.time() * 1000)
    print(f"\nwould set deferred_until = {now_ms} "
          f"({datetime.fromtimestamp(now_ms / 1000, timezone.utc):%Y-%m-%d %H:%M} UTC)")
    print("effect: compose stops suppressing the entry; the deferral stays on the record")

    if not apply:
        print("\nDRY RUN — nothing written. Re-run with --apply.")
        return 0

    ref.update({f"{key}.deferred_until": now_ms for key, _ in targets})
    print(f"\nAPPLIED to {len(targets)} record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
