"""read_shelves.py — the shelf reader, run when a store's shelf photos arrive (npm run read:shelves).

    python3 scripts/read_shelves.py --day 2026-10-10            read that day's photos, asking the model
    python3 scripts/read_shelves.py --day 2026-10-10 --no-ask   only the sealed answers: reproduce a reading
    python3 scripts/read_shelves.py --unread                    every photo not read yet: what the nightly runs

F12-S1 FR-218 … FR-223, D-34, ADR-041. It reads `data/internal/shelf_photos/<day>/<fixture>/`,
asks the pinned model once a photo (with SMARTSHELF_ANTHROPIC_API_KEY, within the policy's ceiling
and time budget), seals each answer in `data/external/snapshots/<day>/shelf_readings/`, measures
the photos, and writes `configs/shelf_readings.yaml` and one picture a product in
`public/store/shelf-pictures/`. Commit those with the photos and the sealed answers.

ADR-042 (2026-10-06): the nightly runs it with `--unread` after collecting the photos sent from the
app. That reads every day folder holding a photo not read yet, oldest first, within one ceiling
and one time budget for the night. With no key, or no layout file, it says so and reads nothing,
and the photos wait. Each reading adds to the earlier ones (reading.write). The engine uses the
reader's widths only once its acceptance run has passed (FR-223).
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import EXTERNAL_SNAPSHOTS_ROOT  # noqa: E402
from src.engine.model_client import KEY_ENV, urllib_transport  # noqa: E402
from src.engine.policy import load_policy  # noqa: E402
from src.engine.shelf_reader.answer import Asker  # noqa: E402
from src.engine.shelf_reader.photos import PHOTOS_ROOT as PHOTOS, unread_days  # noqa: E402
from src.engine.shelf_reader.reading import read, write  # noqa: E402
from src.engine.store_layout import DEFAULT_PATH, PICTURES_DIR, READINGS_PATH, load_store_layout  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read the store's shelf photos (F12-S1 FR-218 … FR-223, FR-226).")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--day", help="the photos' folder under data/internal/shelf_photos/")
    which.add_argument("--unread", action="store_true", help="every day folder holding a photo not read yet")
    parser.add_argument("--no-ask", action="store_true", help="use the sealed answers only; ask the model nothing")
    args = parser.parse_args(argv)

    from datetime import datetime, timezone

    from src.engine.inputs import load_inputs
    from src.owner_state.model import OwnerState

    policy = load_policy()
    key = os.environ.get(KEY_ENV) or None
    days = [args.day] if args.day else unread_days(PHOTOS, READINGS_PATH)
    if args.unread:
        # The nightly's call (ADR-042): nothing to read, no key or no layout is a normal night,
        # and the photos wait for the next one.
        if not days:
            print("No shelf photo waits to be read.")
            return 0
        if not key and not args.no_ask:
            print(f"Photos wait to be read in {len(days)} folder(s), but {KEY_ENV} is not set: nothing was asked.")
            return 0
        if not DEFAULT_PATH.exists():
            print(f"Photos wait to be read in {len(days)} folder(s), but {DEFAULT_PATH.relative_to(ROOT)} is not "
                  "committed yet: the reader needs each unit's shelves and their lengths (ADR-037).")
            return 0
    elif not DEFAULT_PATH.exists():
        print(f"✗ {DEFAULT_PATH.relative_to(ROOT)} is not committed: the reader needs each unit's shelves and "
              "their lengths (ADR-037)", file=sys.stderr)
        return 1
    now = datetime.now(timezone.utc)
    inputs = load_inputs(policy=policy, owner=OwnerState.unavailable("not_needed"), run_at=now)
    layout = load_store_layout(DEFAULT_PATH, inputs.products or [])
    prompt_path = ROOT / policy.shelf_reader_prompt
    earlier = None
    for day in days:
        asker = Asker(folder=EXTERNAL_SNAPSHOTS_ROOT / day / "shelf_readings", prompt=prompt_path.read_text(encoding="utf-8"),
                      prompt_version=prompt_path.stem, model=policy.boost_model, key=key,
                      transport=urllib_transport, policy=policy, ask_missing=not args.no_ask)
        if earlier is not None:          # one ceiling and one time budget for the whole run (NFR-079)
            asker.requests, asker.started, asker.stopped = earlier.requests, earlier.started, earlier.stopped
        result = read(day=day, photo_root=PHOTOS, layout=layout, products=inputs.products or [],
                      sales_daily=inputs.sales_daily or [], sales_monthly=inputs.sales_monthly or [], policy=policy,
                      asker=asker)
        # A folder the AI answered nothing for leaves the readings file as it was: no reading happened.
        contradicted = (write(result, day=day, model=policy.boost_model, prompt=prompt_path.stem,
                              readings_path=READINGS_PATH, pictures_dir=PICTURES_DIR,
                              tolerance_mm=policy.shelf_reader_tolerance_mm, read_on=now.date().isoformat())
                        if result["photos"] else [])
        _say(day, asker, result, contradicted)
        earlier = asker

    sealed = " ".join(str((EXTERNAL_SNAPSHOTS_ROOT / d / "shelf_readings").relative_to(ROOT)) for d in days)
    print(f"\nWrote {READINGS_PATH.relative_to(ROOT)} and the pictures in {PICTURES_DIR.relative_to(ROOT)}/. "
          "Commit them with the photos and the sealed answers:")
    print(f"  git add {READINGS_PATH.relative_to(ROOT)} {PICTURES_DIR.relative_to(ROOT)} {PHOTOS.relative_to(ROOT)}")
    print(f"  git add -f {sealed}      # data/external is ignored; the nightly force-adds its snapshots the same way")
    return 0


def _say(day: str, asker, result: dict, contradicted: list) -> None:
    print(f"\nShelf reading of {day}: {asker.requests} requests to the model so far")
    print(f"  photos read: {len(result['photos'])}   units read whole: {len(result['units'])}")
    print(f"  widths read: {len(result['widths'])} (used only once the acceptance run passes)")
    print(f"  current facings: {len(result['current'])}   pictures: {len(result['pictures'])}")
    reasons = Counter(r["why"].split(":")[0] for r in result["report"] + contradicted)
    for why, n in reasons.most_common():
        print(f"  not read, {why}: {n}")


if __name__ == "__main__":
    sys.exit(main())
