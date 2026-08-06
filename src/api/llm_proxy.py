"""
LLM proxy — receives explanation payloads from the frontend,
calls Gemini, returns structured explanation fields.

Run:  uvicorn src.api.llm_proxy:app --port 8000 --reload
Requires: VITE_GEMINI_API_KEY env var (or GEMINI_API_KEY as fallback)
      pip install fastapi uvicorn google-generativeai
"""
import os
import json
import asyncio
import textwrap
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from google.api_core.exceptions import TooManyRequests

load_dotenv()

GEMINI_API_KEY = os.environ.get("VITE_GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("VITE_GEMINI_API_KEY (or GEMINI_API_KEY) is not set in the environment.")

genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = (
    os.environ.get("VITE_GEMINI_MODEL")
    or os.environ.get("GEMINI_MODEL")
    or "gemini-2.0-flash"
)
model = genai.GenerativeModel(GEMINI_MODEL)
UPSTREAM_TIMEOUT_SECONDS = float(os.environ.get("LLM_UPSTREAM_TIMEOUT_SECONDS", "3"))

app = FastAPI(title="SmartShelf LLM Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
    return {"status": "ok"}


@app.post("/explain")
async def explain(payload: dict):
    prompt = SYSTEM_PROMPT + "\n\nPayload:\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        response = await asyncio.wait_for(
            model.generate_content_async(
                prompt,
                request_options={"timeout": UPSTREAM_TIMEOUT_SECONDS},
            ),
            timeout=UPSTREAM_TIMEOUT_SECONDS,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
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
    try:
        prompt = REPORT_SYSTEM_PROMPT + "\n\nStore data summary:\n" + json.dumps(payload, ensure_ascii=False, indent=2)
        response = model.generate_content(prompt)
        text = response.text.strip()
        return {"report": text}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
