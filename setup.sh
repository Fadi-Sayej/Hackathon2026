#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# SmartShelf AI — Full Setup Script
# Run once after cloning the repo.
# Usage: bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e  # stop on first error

echo ""
echo "════════════════════════════════════════════"
echo "  SmartShelf AI — Project Setup"
echo "════════════════════════════════════════════"
echo ""

# ── 1. Environment file ───────────────────────────────────────────────────────
echo "▶ Creating .env from .env.example..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  ✔ .env created — fill in your API keys before running scripts"
else
  echo "  ✔ .env already exists, skipping"
fi

# ── 2. Node.js dependencies ───────────────────────────────────────────────────
echo ""
echo "▶ Installing Node.js dependencies (npm install)..."
npm install
echo "  ✔ Node modules installed"

# ── 3. Python dependencies ────────────────────────────────────────────────────
echo ""
echo "▶ Installing Python dependencies (requirements.txt)..."
pip install -r requirements.txt --break-system-packages -q
echo "  ✔ Python packages installed"

# ── 4. Playwright (used by Wolt scraper) ─────────────────────────────────────
echo ""
echo "▶ Installing Playwright + Chromium browser..."
pip install playwright --break-system-packages -q
playwright install chromium
echo "  ✔ Playwright + Chromium ready"

# ── 6. Data directory structure ───────────────────────────────────────────────
echo ""
echo "▶ Creating data directory structure..."
# Use python3 for macOS systems where `python` may be absent
python3 scripts/init_storage.py
echo "  ✔ Data directories initialised"

# ── 7. Verify frontend builds ─────────────────────────────────────────────────
echo ""
echo "▶ Verifying frontend build..."
npm run build --silent
echo "  ✔ Frontend builds successfully"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "  Setup complete!"
echo "════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo ""
echo "  Start the frontend:"
echo "    npm run dev            → http://localhost:5173"
echo ""
echo "  Import real YomYom inventory (already fixed, ready to run):"
echo "    python scripts/import_pos.py            # the export named in configs/store.yaml"
echo ""
echo "  Keys needed in .env:"
echo "    GEMINI_API_KEY       → Google Cloud Console → APIs & Services → Credentials"
echo ""
