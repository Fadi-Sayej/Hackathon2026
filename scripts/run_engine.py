# scripts/run_engine.py
"""One command to refresh every dashboard input and publish the artefact.

  python3 scripts/run_engine.py                     # npm run data:refresh
  python3 scripts/run_engine.py --input <pos.csv>   # import a new export first
  python3 scripts/run_engine.py --skip-market       # POS-only refresh
  python3 scripts/run_engine.py --print             # run everything, write nothing (reproduction)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engine.run import run_engine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None)
    parser.add_argument("--skip-market", action="store_true")
    parser.add_argument("--print", dest="print_mode", action="store_true")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()
    result = run_engine(mode="print" if args.print_mode else "publish",
                        input_csv=Path(args.input) if args.input else None, skip_market=args.skip_market)
    summary = {"status": result["status"], "published": result["published"], "steps": result["steps"]}
    payload = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    print(payload)
    # The exit code answers ONE question: did this run produce what it was asked for?
    # In publish mode that is "is there a fresh artefact?" — not "was the day perfect?".
    #
    # `degraded` and `partial` are honest states of a PUBLISHED artefact: owner state
    # unavailable, sales continued on evidence already on disk (ADR-017), a capability that
    # raised. Every one is already reported four ways — printed above, written to
    # --json-out, warned about by collect-daily.yml's next step, and carried in the
    # artefact's own run.status where the data page renders it.
    #
    # Exiting 1 for them cost the thing the nightly exists to do. That step has no
    # continue-on-error, so a degraded run aborted the job BEFORE "Commit the owner's
    # artefact": the artefact was written into the runner's workspace and thrown away.
    # Rule 12 at the top of the pipeline, and the same shape as the 2026-09-13 incident
    # that the engine step's own comment describes — "the gate that followed exited 1, so
    # this step never ran and the owner's artefact was never rebuilt".
    #
    # It also made the NEXT step's promise unreachable on precisely the runs it was written
    # for: "ADR-017: a run that continued on older sales evidence is never 'ok'. This does
    # NOT fail the build." It did, one step earlier.
    #
    # Print mode publishes nothing by design, so it keeps the old meaning: there is no
    # artefact to ask about, and a reproduction that degrades should still say so.
    if args.print_mode:
        return 0 if result["status"] == "ok" else 1
    return 0 if result["published"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
