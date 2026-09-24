#!/usr/bin/env python3
"""
check_deploy_data.py — is the data the deploy will serve committed, and would the engine
publish it? Section 2 of scripts/preflight_deploy.sh.

The owner's app reads two files: public/data/dashboard.json (every page, through
loadDashboard.js) and public/data/catalogue.json (Products). Each is checked three ways:

  - it exists;
  - it is committed, because a git deploy ships what is committed, and it carries no local
    edits, because a CLI deploy would then ship something git does not have;
  - it passes the validation the engine itself applies before publishing:
    validate_artefact() with the complete registry (ADR-014), and validate_catalogue().

public/data/operational.json is checked too, as the telemetry page's frozen input until
F13 (#83). Nothing regenerates it since the legacy chain went on 2026-09-24.

Until 2026-09-24 the preflight checked only operational.json, which no owner page has read
since the 2026-09-12 cut-over. So a deploy with dashboard.json missing, uncommitted or
refused by the engine's own validator passed.

Prints one line per finding, `OK|WARN|BAD <message>`, for the shell script to count, and
exits 1 when anything is BAD.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engine.catalogue import validate_catalogue  # noqa: E402
from src.engine.publish import PublishRefused, validate_artefact  # noqa: E402

Finding = Tuple[str, str]

DASHBOARD = "public/data/dashboard.json"
CATALOGUE = "public/data/catalogue.json"
OPERATIONAL = "public/data/operational.json"

# The nightly commits the artefact every day. Older than this means at least one nightly
# did not: worth a look before deploying, not a reason to refuse.
STALE_AFTER = timedelta(days=2)


def _git_ok(root: Path, *args: str) -> bool:
    return subprocess.run(["git", *args], cwd=root, capture_output=True).returncode == 0


def _load(root: Path, rel: str, missing: str) -> Tuple[List[Finding], Optional[Any]]:
    """The file's content if it exists and is committed, and what was wrong if not."""
    path = root / rel
    if not path.exists():
        return [("BAD", f"{rel} missing — {missing}")], None
    if not _git_ok(root, "ls-files", "--error-unmatch", rel):
        return [("BAD", f"{rel} exists but is NOT COMMITTED — Vercel builds from git, "
                        "so the deploy would ship without it")], None
    findings: List[Finding] = []
    if not _git_ok(root, "diff", "--quiet", "HEAD", "--", rel):
        findings.append(("WARN", f"{rel} has uncommitted changes — a git deploy ships the "
                                 "committed version, a CLI deploy ships this one"))
    try:
        return findings, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        return findings + [("BAD", f"{rel} is not valid JSON: {err}")], None


def _when(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def _check_dashboard(root: Path, now: datetime) -> List[Finding]:
    findings, doc = _load(root, DASHBOARD, "the owner's app would ship with nothing to read; "
                                           "run `npm run data:refresh` and commit it")
    if doc is None:
        return findings
    try:
        validate_artefact(doc, require_complete_registry=True)
    except (PublishRefused, KeyError, TypeError) as err:
        return findings + [("BAD", f"{DASHBOARD} would be refused by the engine's own publisher: {err}")]

    caps = doc["capabilities"]
    available = [c for c, cap in caps.items() if cap["status"] == "available"]
    generated = _when(doc["generated_at"])
    run_status = (doc.get("run") or {}).get("status")
    findings.append(("OK", f"{DASHBOARD} passes the engine's validation: {len(available)} of "
                           f"{len(caps)} capabilities available, generated "
                           f"{generated:%Y-%m-%d %H:%M} UTC, run {run_status}"))
    unavailable = {c: cap.get("unavailable_reason") for c, cap in caps.items() if cap["status"] != "available"}
    if unavailable:
        listed = ", ".join(f"{c} ({reason})" for c, reason in sorted(unavailable.items()))
        findings.append(("WARN", f"{DASHBOARD}: unavailable, and each page will say why: {listed}"))
    if run_status != "ok":
        findings.append(("WARN", f"{DASHBOARD} came from a run whose status was {run_status}"))
    age = now - generated
    if age > STALE_AFTER:
        findings.append(("WARN", f"{DASHBOARD} was generated {age.days} days ago — "
                                 "the nightly has not committed a newer one"))
    return findings


def _check_catalogue(root: Path) -> List[Finding]:
    findings, doc = _load(root, CATALOGUE, "the Products page would ship with nothing to read; "
                                           "run `npm run data:refresh` and commit it")
    if doc is None:
        return findings
    try:
        validate_catalogue(doc)
    except (PublishRefused, KeyError, TypeError) as err:
        return findings + [("BAD", f"{CATALOGUE} would be refused by the engine's own publisher: {err}")]
    products = doc.get("products")
    if products is None:
        return findings + [("WARN", f"{CATALOGUE} says the engine does not know the products; "
                                    "the Products page will say so")]
    if not products:
        # Rule 10: an empty export is a failure, not a result.
        return findings + [("BAD", f"{CATALOGUE} lists no products — the Products page would be empty")]
    return findings + [("OK", f"{CATALOGUE} passes the engine's validation: {len(products):,} products")]


def _check_operational(root: Path) -> List[Finding]:
    findings, doc = _load(root, OPERATIONAL, "nothing regenerates it since 2026-09-24; restore it: "
                                             "git checkout -- public/data/operational.json")
    if doc is None:
        return findings
    count = len(doc.get("recommendations") or []) if isinstance(doc, dict) else 0
    if count == 0:
        return findings + [("BAD", f"{OPERATIONAL} is committed but EMPTY — the telemetry page, "
                                   "its one reader until F13 (#83), will show nothing")]
    return findings + [("OK", f"{OPERATIONAL} committed, {count:,} recommendations "
                              "(the telemetry page's frozen input until F13, #83)")]


def check(root: Path, now: datetime) -> List[Finding]:
    return _check_dashboard(root, now) + _check_catalogue(root) + _check_operational(root)


def main() -> int:
    findings = check(ROOT, datetime.now(timezone.utc))
    for level, message in findings:
        print(f"{level} {message}")
    return 1 if any(level == "BAD" for level, _ in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
