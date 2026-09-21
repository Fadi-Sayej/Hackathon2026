# tests/test_e2e_never_touches_production.py
"""The e2e suite must not be able to reach the pilot's Firestore.

Vite loads the repo root's `.env` on every build, and the documented developer setup puts
the real `VITE_FIREBASE_*` values and `VITE_STORE_ID=yomyom-kafr-qasim` there. Playwright
serves a build and gives each test a fresh browser context, so each one mints an ADR-021
device id and `pushAll` writes it to the owner's live store — and `daily-surface.spec.js`'s
AC-105 test clicks Done on a real recommendation and records a real `acted` outcome against
its real entry id.

Measured on 2026-09-21 before this was fixed: `vintages.owner_state.devices.count` was 29,
of which 25 arrived between 14:58 and 15:04 on 2026-09-17, several inside the same second.
One suite run, counted as twenty-five devices, in the number Task 4.3's precondition rests
on.

Two mechanisms, asserted here because both are one careless edit from gone and neither
announces itself when it breaks — the suite goes green either way.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: What `isFirebaseConfigured()` in src/firebase.js gates on. Empty means unconfigured,
#: which means no init, no anonymous sign-in, no network.
GATED_KEYS = ("VITE_FIREBASE_API_KEY", "VITE_FIREBASE_PROJECT_ID", "VITE_FIREBASE_APP_ID")
PRODUCTION_STORE = "yomyom-kafr-qasim"


def _env_e2e() -> dict:
    values = {}
    for line in (ROOT / ".env.e2e").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def test_the_e2e_mode_file_leaves_the_app_unconfigured():
    env = _env_e2e()
    for key in GATED_KEYS:
        assert key in env, f"{key} must be assigned in .env.e2e, or .env's value survives"
        assert env[key] == "", f"{key} must be EMPTY — a placeholder passes isFirebaseConfigured()"


def test_the_e2e_store_is_not_the_pilot_store():
    """The second layer. Even if the keys above were repopulated, `firestore.rules` allows
    only `stores/yomyom-kafr-qasim/**`, so a sandbox id turns a write into a denial rather
    than into the owner's data. Same mechanism that protects Vercel previews."""
    store = _env_e2e().get("VITE_STORE_ID", "")
    assert store, "VITE_STORE_ID must be set, or src/firebase.js defaults it to the pilot store"
    assert store != PRODUCTION_STORE


def test_playwright_builds_in_that_mode():
    """The file is inert unless the build asks for it. `npm run build` does not."""
    config = (ROOT / "playwright.config.js").read_text(encoding="utf-8")
    command = config[config.index("command:"):]
    command = command[:command.index("\n")]
    assert "--mode e2e" in command, (
        "playwright's webServer must build with `--mode e2e`; without it Vite loads the "
        "repo root .env and the suite writes to the pilot's Firestore")


def test_the_mode_file_is_not_gitignored():
    """It carries no secret and it has to travel: a developer who does not have it builds
    the e2e app against whatever their own .env holds, which is the defect."""
    import subprocess

    result = subprocess.run(["git", "check-ignore", "-q", ".env.e2e"], cwd=ROOT)
    assert result.returncode != 0, ".env.e2e is gitignored; it must be committed"
