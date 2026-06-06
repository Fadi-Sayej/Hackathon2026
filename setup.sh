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

# ── 4. Extra Python packages needed for new features ─────────────────────────
echo ""
echo "▶ Installing extra Python packages (LLM proxy + Kaggle)..."
# Prefer Google's Gemini client for LLM integration
pip install google-generative-ai fastapi uvicorn kaggle --break-system-packages -q
echo "  ✔ google-generative-ai, fastapi, uvicorn, kaggle installed"

# ── 5. Playwright (used by Wolt scraper) ─────────────────────────────────────
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
echo "    python scripts/import_yomyom_pos.py --input yomyom-inventory.csv"
echo ""
echo "  Download Kaggle competitor prices (needs KAGGLE_API_TOKEN in .env):"
echo "    python scripts/download_kaggle_datasets.py"
echo "    python scripts/import_kaggle_supermarkets.py"
echo ""
echo "  Start the LLM proxy (needs GEMINI_API_KEY in .env):"
echo "    uvicorn src.api.llm_proxy:app --port 8000 --reload"
echo ""
echo "  Keys needed in .env:"
echo "    KAGGLE_API_TOKEN     → kaggle.com → Settings → API → Create New Token"
echo "    GEMINI_API_KEY       → Google Cloud Console → APIs & Services → Credentials"
echo ""
