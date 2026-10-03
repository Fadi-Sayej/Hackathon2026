"""new_store_copy.py — make a new store's copy of SmartShelf, or bring one's code up to date.

    python3 scripts/new_store_copy.py ../smartshelf-<store>          # a new copy
    python3 scripts/new_store_copy.py --update ../smartshelf-<store> # code only, never data

ADR-036 §3, D-28. Each store runs its own copy with only its own data. A new copy is this
repository's code, written into a new directory with a fresh history (one commit), less every
path the store-data manifest names (src/common/store.py):
- it starts without this copy's store data (its POS export, reports, snapshots, owner
  state, published artefacts, pilot documents);
- it starts with an empty template of each store setting (configs/store.yaml and the rest),
  which docs/operations/new-store.md says how to fill.

`--update` copies the code across again and removes code this repository has removed. It never
touches a manifest path, so the other store's data and settings stay exactly as they are. It
commits nothing: review `git -C <dir> diff` and commit it there.

Both refuse to finish if a manifest path in the result still holds this store's id or name.
The copy leaves out .github/workflows/ci.yml: code is tested here before an update carries
it, and a copy's own tests would read store data it does not have yet. Its nightly, and the
probes in it, run as they do here.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.store import STARTS_EMPTY, StoreSettings, get_store, is_store_data  # noqa: E402

NOT_COPIED = (".github/workflows/ci.yml",)
RULES_PLACEHOLDER = "set-to-the-id-in-configs-store-yaml"

STORE_TEMPLATE = """\
# configs/store.yaml — which store this copy of SmartShelf serves (ADR-036, D-28).
#
# Fill every key. Nothing is defaulted: until each is filled, the engine and `npm run
# check:store` stop and name the first empty one. docs/operations/new-store.md explains each.
# Paths are from the repository root.

id: ""                 # the store's id: the Firestore root, lowercase letters, digits and hyphens
name: ""               # the store's name, as the team uses it
site_title: ""         # the browser tab's title, e.g. "SmartShelf AI — <store>"
location:
  lat:                 # where the store is
  lon:
format: ""             # one of configs/store_types.yaml's formats; ask the owner, never guess
pos:
  export: ""           # the committed inventory export, e.g. <store>-inventory.csv
sales:
  monthly_dir: ""      # e.g. data/internal/raw_pos/<store>/sales
  daily_dir: ""        # e.g. data/internal/raw_pos/<store>/sales_daily
market:
  radius_km: 5         # how far scripts/find_nearby_venues.py looks
firebase:
  project_id: ""       # the copy's own Firebase project
site:
  address: ""          # the address the site is opened at, e.g. smartshelf-store.vercel.app (no https://)
"""

TARGETS_TEMPLATE = """\
# delivery_targets.yaml — the delivery venues the nightly collects (ADR-036 §4).
#
# Start from `python3 scripts/find_nearby_venues.py`: it lists the grocery venues near the
# store for a person to confirm. Add the store's own venue with `role: client`, and each
# confirmed competitor with `role: competitor`. Record every venue's format in
# configs/store_types.yaml as `verified: manual`; ask when it is not known.
#
#   - key: <short_name>
#     chain: <chain>
#     chain_display: "<Chain>"
#     provider: wolt
#     url: https://wolt.com/en/isr/<city>/venue/<slug>
#     role: client | competitor
#     enabled: true

targets: []
"""


def _header(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if not line.startswith("#") and line.strip():
            break
        lines.append(line)
    return "\n".join(lines).rstrip() + "\n\n"


def _dump(data) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def templates(store: StoreSettings) -> dict:
    """The empty template of each STARTS_EMPTY path, derived from this copy's own files."""
    read = lambda rel: (ROOT / rel).read_text(encoding="utf-8")  # noqa: E731
    types = yaml.safe_load(read("configs/store_types.yaml"))
    for fmt in (types.get("formats") or {}).values():
        fmt.pop("note", None)                     # the notes describe this copy's store
    types["stores"] = {}
    policy = yaml.safe_load(read("configs/store_policy.yaml"))
    policy["stores"] = {}
    answers = yaml.safe_load(read("configs/owner_answers.yaml")) or {}
    env_lines = []
    for line in read(".env.example").splitlines():
        key = line.split("=", 1)[0]
        if "=" in line and not line.startswith("#") and (key.startswith("VITE_FIREBASE_") or key in (
                "FIREBASE_PROJECT_ID", "VITE_STORE_ID")):
            line = f"{key}="
        env_lines.append(line)
    return {
        "configs/store.yaml": STORE_TEMPLATE,
        "configs/store_facts.yaml": _header(read("configs/store_facts.yaml")) + "departments: {}\n",
        "configs/owner_answers.yaml": _header(read("configs/owner_answers.yaml"))
        + _dump({key: {} for key in answers}),
        "configs/store_policy.yaml": "# store_policy.yaml — what the store chooses to carry. `stores` is filled for\n"
                                     "# this store once its sales are in (scripts/derive_store_policy.py).\n\n"
                                     + _dump(policy),
        "configs/delivery_targets.yaml": TARGETS_TEMPLATE,
        "configs/store_types.yaml": "# store_types.yaml — the format scale and affinity (ADR-008), and each store's\n"
                                    "# format. Fill `stores` with the store's own entries (`role: client`) and every\n"
                                    "# collected venue, `verified: manual`, asking when a format is not known.\n\n"
                                    + _dump(types),
        "firestore.rules": read("firestore.rules").replace(store.id, RULES_PLACEHOLDER),
        ".firebaserc": json.dumps({"projects": {"default": ""}}, indent=2) + "\n",
        ".env.example": "\n".join(env_lines) + "\n",
    }


def tracked_files() -> list:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def code_files(store: StoreSettings) -> list:
    return [rel for rel in tracked_files()
            if rel not in NOT_COPIED and not is_store_data(rel, store) and (ROOT / rel).is_file()]


def leaks(dest: Path, store: StoreSettings) -> list:
    """Manifest paths in `dest` that still hold this store's id or name."""
    found = []
    patterns = [re.escape(store.id), re.escape(store.name)]
    needle = re.compile("|".join(patterns), re.IGNORECASE)
    for path in dest.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(dest).as_posix()
        if not is_store_data(rel, store):
            continue
        try:
            if needle.search(path.read_text(encoding="utf-8")):
                found.append(rel)
        except UnicodeDecodeError:
            found.append(rel)                     # a binary under a manifest path is data by definition
    return found


def _copy(rel: str, dest: Path) -> None:
    target = dest / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / rel, target)


def make_copy(dest: Path, store: StoreSettings) -> int:
    if dest.exists() and any(dest.iterdir()):
        print(f"{dest} is not empty. A new copy starts in an empty directory.", file=sys.stderr)
        return 1
    dest.mkdir(parents=True, exist_ok=True)
    files = code_files(store)
    for rel in files:
        _copy(rel, dest)
    for rel, text in templates(store).items():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_text(text, encoding="utf-8")
    found = leaks(dest, store)
    if found:
        print(f"Refused: {', '.join(found)} still hold {store.name}'s id or name.", file=sys.stderr)
        return 1
    run = lambda *args: subprocess.run(["git", *args], cwd=dest, check=True, capture_output=True)  # noqa: E731
    run("init", "-q", "-b", "main")
    run("add", "-A")
    run("commit", "-q", "-m", "SmartShelf: a new store's copy, without any other store's data (ADR-036)")
    print(f"A new copy in {dest}: {len(files)} code files and {len(STARTS_EMPTY)} empty settings.")
    print("Next: docs/operations/new-store.md, starting with configs/store.yaml; then npm run check:store.")
    return 0


def update_copy(dest: Path, store: StoreSettings) -> int:
    if not (dest / ".git").is_dir():
        print(f"{dest} is not a copy (no .git).", file=sys.stderr)
        return 1
    current = set(code_files(store))
    written = removed = 0
    for rel in sorted(current):
        target = dest / rel
        if not target.exists() or target.read_bytes() != (ROOT / rel).read_bytes():
            _copy(rel, dest)
            written += 1
    theirs = subprocess.run(["git", "ls-files", "-z"], cwd=dest, capture_output=True, check=True).stdout
    for rel in [p for p in theirs.decode("utf-8").split("\0") if p]:
        if rel not in current and rel not in NOT_COPIED and not is_store_data(rel, store):
            (dest / rel).unlink(missing_ok=True)
            removed += 1
    print(f"Updated {dest}: {written} code files written, {removed} removed. No store data touched.")
    print(f"Review and commit there: git -C {dest} diff")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Make a new store's copy, or update one's code.")
    parser.add_argument("dest", type=Path)
    parser.add_argument("--update", action="store_true", help="bring an existing copy's code up to date")
    args = parser.parse_args(argv)
    dest = args.dest.resolve()
    if dest == ROOT or ROOT in dest.parents:
        print("The copy must be outside this repository.", file=sys.stderr)
        return 1
    store = get_store()
    return update_copy(dest, store) if args.update else make_copy(dest, store)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
