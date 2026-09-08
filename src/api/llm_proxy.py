"""
LLM proxy — receives explanation payloads from the frontend, calls Gemini, and
returns structured explanation fields.

Run:  uvicorn src.api.llm_proxy:app --port 8000 --reload
      pip install fastapi uvicorn google-generativeai python-dotenv

Design notes (nagham.md B-4):
  • Graceful startup. The module imports even when VITE_GEMINI_API_KEY is unset
    or the google-generativeai SDK is absent — it no longer raises at import, so
    /health works for deploy checks and the app is testable without the SDK. When
    the key is missing, /explain and /report return 503 rather than 500.
  • Caching. Identical payloads are served from an in-memory TTL/LRU cache, so a
    deployed frontend that re-renders the same product does not re-bill Gemini on
    every render. (In-memory ⇒ per warm process; good enough to stop render-loop
    billing. Swap in a shared cache if the proxy ever scales to many instances.)
  • Timeouts on BOTH endpoints, and CORS origins read from LLM_ALLOWED_ORIGINS so
    a deploy can point it off localhost.

Still blocked before this can serve real explanations: the Gemini key needs
prepayment credits (429), and the frontend async bug in explanationProvider.js
is Anas's (Track C) — coordinate, don't both fix it. VITE_LLM_PROXY_URL stays
commented out until both are resolved.
"""
import os
import json
import time
import asyncio
import hashlib
import textwrap
from collections import OrderedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# google-api-core ships with google-generativeai. Guard the import so the module
# still loads (and stays testable) in an environment where it is not installed;
# the fallback class simply never matches a real rate-limit error.
try:
    from google.api_core.exceptions import TooManyRequests
except Exception:  # pragma: no cover - only hit without the SDK installed
    class TooManyRequests(Exception):
        """Fallback so `except TooManyRequests` is always valid."""

load_dotenv()

# The key is read ONLY from the un-prefixed name, and the VITE_-prefixed one is a
# hard startup error rather than a fallback.
#
# Vite inlines every VITE_* variable into the client bundle at build time, so a key
# stored under VITE_GEMINI_API_KEY is compiled into dist/ and served to every
# visitor. That is not hypothetical: it was verified in this repo on 2026-09-08,
# with a live key found in plain text in dist/assets/main-*.js. Accepting the name
# as a fallback is what made storing it there look harmless, so the fallback is
# gone. The browser talks to this proxy; only this proxy holds the key.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY and os.environ.get("VITE_GEMINI_API_KEY"):
    raise RuntimeError(
        "Refusing to start: the Gemini key is set as VITE_GEMINI_API_KEY. Any "
        "VITE_-prefixed variable is compiled into the browser bundle, so that name "
        "publishes your key to every visitor. Move it to GEMINI_API_KEY (no prefix) "
        "and rotate the old one — it must be treated as compromised."
    )
# Cost note. gemini-2.5-flash bills output at $2.50/1M and has thinking ON by
# default — thinking tokens are billed as output, and the pinned (deprecated)
# google-generativeai SDK exposes no way to switch it off. flash-lite is $0.10 in
# / $0.40 out with thinking off by default, which is ample for turning structured
# product metrics into four short sentences. Override with GEMINI_MODEL if a
# harder task ever justifies the 6x output price.
# Un-prefixed name wins here too: VITE_GEMINI_MODEL taking precedence meant the
# server followed a variable that only exists to be shipped to the browser.
#
# Default verified against the live model list on 2026-09-08 rather than taken from
# memory: gemini-2.5-flash-lite still answers, but gemini-3.5-flash-lite is current,
# answered in ~0.9s, and keeps thinking off by default — thinking tokens bill as
# output. gemini-3.6-flash was tried and rejected: it spent its budget thinking and
# returned a 3-token fragment for the same prompt.
GEMINI_MODEL = os.environ.get("GEMINI_MODEL") or "gemini-3.5-flash-lite"
UPSTREAM_TIMEOUT_SECONDS = float(os.environ.get("LLM_UPSTREAM_TIMEOUT_SECONDS", "3"))

# Output is the expensive half of the bill. Asking for a JSON mime type drops the
# ```json fence the model would otherwise wrap the answer in, and the ceiling
# bounds a runaway answer — four short fields need nowhere near 400 tokens.
EXPLAIN_GENERATION_CONFIG = {
    "response_mime_type": "application/json",
    "max_output_tokens": 400,
}

# Module-level handle. Left as None and built lazily so importing this module
# never requires the SDK or a key; tests also override it directly.
model = None


def _import_genai():
    """Import google-generativeai lazily; return None if unavailable."""
    try:
        import google.generativeai as genai

        return genai
    except Exception:
        return None


def _ensure_model():
    """
    Return a usable model, or None when the LLM is not configured.

    Prefers an already-set module-level `model` (production after first use, and
    the object tests inject), then falls back to building one from the API key.
    """
    global model
    if model is not None:
        return model
    if not GEMINI_API_KEY:
        return None
    genai = _import_genai()
    if genai is None:
        return None
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    return model


# ── Response cache (TTL + LRU) ───────────────────────────────────────────────

CACHE_TTL_SECONDS = float(os.environ.get("LLM_CACHE_TTL_SECONDS", "3600"))
# Must stay comfortably above one pass over the recommendation list. At 500 the
# LRU evicted the head of a pass before the next pass got back to it, so the hit
# rate was ~0 and every pass re-billed in full. Entries are four short strings;
# 3,000 of them is a couple of MB.
CACHE_MAX_ENTRIES = int(os.environ.get("LLM_CACHE_MAX_ENTRIES", "3000"))
_cache = OrderedDict()


def _cache_key(kind, payload):
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return f"{kind}:{hashlib.sha256(blob.encode('utf-8')).hexdigest()}"


def _cache_get(key):
    item = _cache.get(key)
    if item is None:
        return None
    stored_at, value = item
    if CACHE_TTL_SECONDS > 0 and (time.time() - stored_at) > CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    _cache.move_to_end(key)
    return value


def _cache_set(key, value):
    _cache[key] = (time.time(), value)
    _cache.move_to_end(key)
    while len(_cache) > CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)


# ── App ──────────────────────────────────────────────────────────────────────


def _allowed_origins():
    raw = os.environ.get("LLM_ALLOWED_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="SmartShelf LLM Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an AI assistant for SmartShelf, a smart inventory management tool for Israeli convenience stores.
    Given product metrics, a reorder recommendation, and optional market context, produce a short business-oriented explanation.
    Reply ONLY with a JSON object (no markdown, no extra text) with exactly these four string fields:
    {
      "shortExplanation": "1-2 sentence summary of why this action is recommended",
      "riskReason": "the main risk if action is not taken",
      "businessImpact": "expected business impact if action is taken",
      "confidenceNote": "one sentence on confidence level and caveats"
    }
""")


@app.get("/health")
def health():
    # Reports readiness without leaking the key, so ops can see whether the proxy
    # will actually serve explanations or fall back to the frontend's mock.
    return {"status": "ok", "llm_configured": bool(GEMINI_API_KEY)}


def _strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


@app.post("/explain")
async def explain(payload: dict):
    key = _cache_key("explain", payload)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    active_model = _ensure_model()
    if active_model is None:
        raise HTTPException(status_code=503, detail="LLM not configured (no API key)")

    prompt = SYSTEM_PROMPT + "\n\nPayload:\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        response = await asyncio.wait_for(
            active_model.generate_content_async(
                prompt,
                request_options={"timeout": UPSTREAM_TIMEOUT_SECONDS},
                generation_config=EXPLAIN_GENERATION_CONFIG,
            ),
            timeout=UPSTREAM_TIMEOUT_SECONDS,
        )
        result = json.loads(_strip_code_fence(response.text))
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Gemini request timed out") from exc
    except TooManyRequests as exc:
        retry_after = _retry_after(exc)
        headers = {"Retry-After": retry_after} if retry_after else None
        raise HTTPException(
            status_code=429,
            detail="Gemini rate limit exceeded",
            headers=headers,
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Gemini returned non-JSON: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    required = {"shortExplanation", "riskReason", "businessImpact", "confidenceNote"}
    missing = required - result.keys()
    if missing:
        raise HTTPException(status_code=502, detail=f"Gemini response missing fields: {missing}")

    _cache_set(key, result)
    return result


def _retry_after(exc):
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    return headers.get("Retry-After") or headers.get("retry-after")


REPORT_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a retail analyst for an Israeli convenience store.
    Given a summary of the store's inventory, alerts, and competitor signals, write a concise
    executive report in markdown (use ## headers, bullet points, bold for key numbers).
    Cover: inventory health, top reorder priorities, competitor positioning, and 3 actionable
    recommendations. Keep it under 400 words. Use ILS (₪) for currency.
""")


@app.post("/report")
def generate_report(payload: dict):
    key = _cache_key("report", payload)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    active_model = _ensure_model()
    if active_model is None:
        raise HTTPException(status_code=503, detail="LLM not configured (no API key)")

    prompt = REPORT_SYSTEM_PROMPT + "\n\nStore data summary:\n" + json.dumps(
        payload, ensure_ascii=False, indent=2
    )
    try:
        response = active_model.generate_content(
            prompt,
            request_options={"timeout": UPSTREAM_TIMEOUT_SECONDS},
        )
        result = {"report": response.text.strip()}
    except TooManyRequests as exc:
        retry_after = _retry_after(exc)
        headers = {"Retry-After": retry_after} if retry_after else None
        raise HTTPException(
            status_code=429, detail="Gemini rate limit exceeded", headers=headers
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    _cache_set(key, result)
    return result
