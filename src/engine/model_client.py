"""The one way this engine asks a language model (ADR-032, ADR-039 Decision 3).

Shared by the market boost (F8) and the shelf explanation (F12, D-32), so the request, the key,
the figure check and the digest a sealed answer is matched by are written once:
- one Messages API call, with one retry for a transport failure, a 429 or a 5xx, and no
  sampling parameter (current models reject `temperature`; determinism comes from the sealed
  record, ADR-035);
- the key is read under the engine's own name, never ANTHROPIC_API_KEY, so a developer's
  personal key is never spent by a local data:refresh;
- `DIGIT` is D-16's figure check: Western, Arabic-Indic and Extended Arabic-Indic digits.

The token limit is the caller's: the boost answers in one short line, the explanation in three
languages (ADR-039 Decision 3).
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from typing import Callable, Tuple

KEY_ENV = "SMARTSHELF_ANTHROPIC_API_KEY"
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
TIMEOUT_S = 30.0
RETRY_PAUSE_S = 1.0
DIGIT = re.compile(r"[0-9٠-٩۰-۹]")

Transport = Callable[[str, dict, bytes, float], Tuple[int, bytes]]


class ModelUnavailable(Exception):
    """The model could not be asked: no answer, or not one the API recognises as an answer."""


def facts_digest(facts: dict) -> str:
    """What an answer was an answer to. A sealed answer is used only on the same facts."""
    return hashlib.sha256(json.dumps(facts, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def urllib_transport(url: str, headers: dict, body: bytes, timeout: float) -> Tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:     # noqa: S310 — fixed https URL
            return response.status, response.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def ask(payload: dict, *, model: str, key: str, transport: Transport, max_tokens: int) -> str:
    """One Messages API call, with one retry for a transport failure, a 429 or a 5xx."""
    body = json.dumps({"model": model, "max_tokens": max_tokens, "system": payload["system"],
                       "messages": [{"role": "user", "content": payload["user"]}]},
                      ensure_ascii=False).encode("utf-8")
    headers = {"x-api-key": key, "anthropic-version": API_VERSION, "content-type": "application/json"}
    last = "no attempt"
    for attempt in range(2):
        try:
            status, raw = transport(API_URL, headers, body, TIMEOUT_S)
        except Exception as err:  # noqa: BLE001 — any transport failure is "no answer"
            last = f"{type(err).__name__}: {err}"
        else:
            if status == 200:
                try:
                    blocks = json.loads(raw)["content"]
                    return next(b["text"] for b in blocks if b.get("type") == "text")
                except (ValueError, KeyError, TypeError, StopIteration) as err:
                    raise ModelUnavailable(f"an answer the API does not describe as text: {err}")
            last = f"http {status}"
            if status != 429 and status < 500:
                raise ModelUnavailable(last)             # a request the API refuses will not improve
        if attempt == 0:
            time.sleep(RETRY_PAUSE_S)
    raise ModelUnavailable(last)
