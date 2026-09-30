"""check_store.py — is this copy ready to serve its store? (npm run check:store)

    npm run check:store
    python3 scripts/check_store.py --no-github        # skip reading the secret names

ADR-036 §5. It validates configs/store.yaml (an invalid one exits 1, naming the key), then
reports each input the store supplies: present, missing, stale or not checked, and for a
missing one the capabilities that stay unavailable. It is docs/pilot/next-store.md made
executable, and docs/operations/new-store.md says how to fill each gap.

Secrets are checked by name only, through `gh secret list`, which never returns a value.
Nothing here reads or prints a secret's value. The Firebase store id and project are
checked by `npm run check:firebase`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.store import STORE_SETTINGS_PATH, StoreSettingsError, load_store  # noqa: E402
from src.common.store_readiness import readiness  # noqa: E402

MARK = {"present": "✓", "missing": "✗", "stale": "!", "not checked": "·"}


def _secret_names() -> set | None:
    """The repository's Actions secret names, or None when they cannot be read."""
    try:
        result = subprocess.run(["gh", "secret", "list", "--json", "name"], cwd=ROOT,
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return {row["name"] for row in json.loads(result.stdout or "[]")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Is this copy ready to serve its store?")
    parser.add_argument("--settings", type=Path, default=STORE_SETTINGS_PATH)
    parser.add_argument("--no-github", action="store_true", help="do not read the Actions secret names")
    args = parser.parse_args(argv)
    try:
        store = load_store(args.settings)
    except StoreSettingsError as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1

    today = datetime.now(timezone.utc).date()
    items = readiness(store, today=today, secret_names=None if args.no_github else _secret_names())
    print(f"\nStore: {store.name} ({store.id}), {today}\n")
    for item in items:
        print(f"{MARK[item['status']]} {item['label']}: {item['detail']}")
        if item["blocks"]:
            print(f"    until then unavailable: {', '.join(item['blocks'])}")
    gaps = [i for i in items if i["status"] in ("missing", "stale")]
    print(f"\n{len(gaps)} of {len(items)} still to supply." if gaps else "\nNothing blocks this store.")
    print("Also: npm run check:firebase (the store id and project the web app uses).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
