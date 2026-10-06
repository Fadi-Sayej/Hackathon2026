"""read_shelves.py — the shelf reader, run when a store's shelf photos arrive (npm run read:shelves).

    python3 scripts/read_shelves.py --day 2026-10-10            read that day's photos, asking the model
    python3 scripts/read_shelves.py --day 2026-10-10 --no-ask   only the sealed answers: reproduce a reading

F12-S1 FR-218 … FR-223, D-34, ADR-041. It reads `data/internal/shelf_photos/<day>/<fixture>/`,
asks the pinned model once a photo (with SMARTSHELF_ANTHROPIC_API_KEY, within the policy's ceiling
and time budget), seals each answer in `data/external/snapshots/<day>/shelf_readings/`, measures
the photos, and writes `configs/shelf_readings.yaml` and one picture a product in
`public/store/shelf-pictures/`. Commit those with the photos and the sealed answers.

It never runs in the nightly. The nightly reads what it wrote, and uses its widths only once its
acceptance run has passed (FR-223).
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
from src.engine.shelf_reader.reading import read, write  # noqa: E402
from src.engine.store_layout import DEFAULT_PATH, PICTURES_DIR, READINGS_PATH, load_store_layout  # noqa: E402

PHOTOS = ROOT / "data" / "internal" / "shelf_photos"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read a day's shelf photos (F12-S1 FR-218 … FR-223).")
    parser.add_argument("--day", required=True, help="the photos' folder under data/internal/shelf_photos/")
    parser.add_argument("--no-ask", action="store_true", help="use the sealed answers only; ask the model nothing")
    args = parser.parse_args(argv)

    from datetime import datetime, timezone

    from src.engine.inputs import load_inputs
    from src.owner_state.model import OwnerState

    policy = load_policy()
    if not DEFAULT_PATH.exists():
        print(f"✗ {DEFAULT_PATH.relative_to(ROOT)} is not committed: the reader needs each unit's shelves and "
              "their lengths (ADR-037)", file=sys.stderr)
        return 1
    inputs = load_inputs(policy=policy, owner=OwnerState.unavailable("not_needed"), run_at=datetime.now(timezone.utc))
    layout = load_store_layout(DEFAULT_PATH, inputs.products or [])
    prompt_path = ROOT / policy.shelf_reader_prompt
    asker = Asker(folder=EXTERNAL_SNAPSHOTS_ROOT / args.day / "shelf_readings", prompt=prompt_path.read_text(encoding="utf-8"),
                  prompt_version=prompt_path.stem, model=policy.boost_model, key=os.environ.get(KEY_ENV) or None,
                  transport=urllib_transport, policy=policy, ask_missing=not args.no_ask)
    result = read(day=args.day, photo_root=PHOTOS, layout=layout, products=inputs.products or [],
                  sales_daily=inputs.sales_daily or [], sales_monthly=inputs.sales_monthly or [], policy=policy, asker=asker)
    write(result, day=args.day, model=policy.boost_model, prompt=prompt_path.stem,
          readings_path=READINGS_PATH, pictures_dir=PICTURES_DIR)

    print(f"\nShelf reading of {args.day}: {asker.requests} requests to the model")
    print(f"  widths read: {len(result['widths'])} (used only once the acceptance run passes)")
    print(f"  current facings: {len(result['current'])}   pictures: {len(result['pictures'])}")
    reasons = Counter(r["why"].split(":")[0] for r in result["report"])
    for why, n in reasons.most_common():
        print(f"  not read, {why}: {n}")
    sealed = (EXTERNAL_SNAPSHOTS_ROOT / args.day / "shelf_readings").relative_to(ROOT)
    print(f"\nWrote {READINGS_PATH.relative_to(ROOT)} and {len(result['pictures'])} pictures in "
          f"{PICTURES_DIR.relative_to(ROOT)}/. Commit them with the photos and the sealed answers:")
    print(f"  git add {READINGS_PATH.relative_to(ROOT)} {PICTURES_DIR.relative_to(ROOT)} "
          f"{PHOTOS.relative_to(ROOT)}/{args.day}")
    print(f"  git add -f {sealed}      # data/external is ignored; the nightly force-adds its snapshots the same way")
    return 0


if __name__ == "__main__":
    sys.exit(main())
