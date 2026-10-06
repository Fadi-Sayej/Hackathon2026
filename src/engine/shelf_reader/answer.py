"""The AI's reading of one shelf photo: asked, checked for shape, sealed, reused (ADR-041 Decision 3).

One request per photo. It carries the whole photo, then the same photo cut into tiles at full
resolution, so the tags' small print can be read (the API reduces any image to about 1,568 px
on its long side). Positions come back as fractions of the whole photo, rough by design: image
processing finds the exact edges (measure.py).

An answer is sealed with the model, the prompt's version and the photo's digest, and reused
while those three are unchanged (ADR-039's method). `ask_missing=False` reads sealed answers
only, so a reading can be reproduced without the model.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import time
from pathlib import Path
from typing import Optional

from PIL import Image

from src.engine.model_client import ModelUnavailable, ask

API_LONG_EDGE = 1568          # the API's largest image side; anything bigger is reduced to it
SEALED = "answers.json"


def digest(photo: Path) -> str:
    return hashlib.sha256(Path(photo).read_bytes()).hexdigest()


def _jpeg(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=88)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def images(photo: Path, shelves: int) -> list:
    """The whole photo reduced to the API's size, then full-resolution tiles: one row of tiles a
    shelf, each row overlapping its neighbours by a quarter, so every tag is whole in some tile."""
    full = Image.open(photo)
    full.load()
    whole = full.copy()
    whole.thumbnail((API_LONG_EDGE, API_LONG_EDGE))
    out = [whole]
    width, height = full.size
    band = height / shelves
    for row in range(shelves):
        top = max(0, int(row * band - band / 4))
        bottom = min(height, int((row + 1) * band + band / 4))
        columns = max(1, -(-width // API_LONG_EDGE))
        step = width / columns
        for column in range(columns):
            left = max(0, int(column * step - step / 8))
            right = min(width, int((column + 1) * step + step / 8))
            out.append(full.crop((left, top, right, bottom)))
    return out


def request(photo: Path, fixture: str, shelves: int, prompt: str) -> dict:
    blocks = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _jpeg(i)}}
              for i in images(photo, shelves)]
    blocks.append({"type": "text", "text": json.dumps({"unit": fixture, "shelves": shelves}, ensure_ascii=False)})
    return {"system": prompt, "user": blocks}


def _fraction(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0.0 <= value <= 1.0


def check(raw: str, shelves: int) -> tuple:
    """(answer, None) for a well-formed reading, or (None, why). Shape only: no figure is trusted
    from it but positions to search near, counts to compare with, and tag text to match."""
    try:
        answer = json.loads(raw)
    except ValueError:
        return None, "not_json"
    if not isinstance(answer, dict):
        return None, "not_json"
    if answer.get("problem"):
        return None, "photo_problem"
    listed = answer.get("shelves")
    if not isinstance(listed, list) or len(listed) != shelves:
        return None, "shelves_not_matched"
    for shelf in listed:
        if not isinstance(shelf, dict):
            return None, "bad_shape"
        if not all(_fraction(shelf.get(k)) for k in ("y_top", "y_bottom", "left_x", "right_x")):
            return None, "bad_shape"
        if not (shelf["y_top"] < shelf["y_bottom"] and shelf["left_x"] < shelf["right_x"]):
            return None, "bad_shape"
        runs = shelf.get("runs")
        if not isinstance(runs, list):
            return None, "bad_shape"
        for run in runs:
            box = run.get("box") if isinstance(run, dict) else None
            facings = run.get("facings") if isinstance(run, dict) else None
            if (not isinstance(box, list) or len(box) != 4 or not all(_fraction(v) for v in box)
                    or not (box[0] < box[2] and box[1] < box[3])):
                return None, "bad_shape"
            if not isinstance(facings, int) or isinstance(facings, bool) or not 1 <= facings <= 60:
                return None, "bad_shape"
            tag = run.get("tag")
            if tag is not None and not (isinstance(tag, dict) and all(
                    tag.get(k) is None or isinstance(tag.get(k), str) for k in ("name", "code", "price"))):
                return None, "bad_shape"
            package = run.get("package")
            if package is not None and not (isinstance(package, dict) and all(
                    package.get(k) is None or isinstance(package.get(k), str) for k in ("brand", "name", "size"))):
                return None, "bad_shape"
    return answer, None


def sealed(folder: Path) -> dict:
    path = Path(folder) / SEALED
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def seal(folder: Path, answers: dict) -> None:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / (SEALED + ".tmp")
    tmp.write_text(json.dumps(answers, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(folder / SEALED)


def key_of(photo_digest: str, model: str, prompt_version: str) -> str:
    return f"{photo_digest}|{model}|{prompt_version}"


class Asker:
    """Asks for each photo once, within the reading's ceiling and time budget (NFR-079)."""

    def __init__(self, *, folder: Path, prompt: str, prompt_version: str, model: str, key: Optional[str],
                 transport, policy, ask_missing: bool = True, clock=time.monotonic):
        self.folder, self.prompt, self.version, self.model = Path(folder), prompt, prompt_version, model
        self.key, self.transport, self.policy, self.ask_missing, self.clock = key, transport, policy, ask_missing, clock
        self.answers = sealed(self.folder)
        self.requests = 0
        self.started = clock()
        self.stopped: Optional[str] = None

    def read(self, photo: Path, fixture: str, shelves: int) -> tuple:
        """(answer, None), or (None, why). A sealed answer that checks is reused; one that does not
        is asked again, as ADR-039 never reuses a withheld explanation."""
        k = key_of(digest(photo), self.model, self.version)
        record = self.answers.get(k)
        if record is not None:
            answer, why = check(record["raw"], shelves)
            if answer is not None or not self.ask_missing:
                return answer, why
        elif not self.ask_missing:
            return None, "not_read"
        if not self.key:
            return None, "no_model_key"
        if self.stopped:
            return None, self.stopped
        if self.requests >= self.policy.shelf_reader_request_ceiling:
            self.stopped = "request_ceiling"
            return None, self.stopped
        if self.clock() - self.started >= self.policy.shelf_reader_time_budget_s:
            self.stopped = "time_budget"
            return None, self.stopped
        self.requests += 1
        try:
            raw = ask(request(photo, fixture, shelves, self.prompt), model=self.model, key=self.key,
                      transport=self.transport, max_tokens=self.policy.shelf_reader_max_tokens,
                      timeout=self.policy.shelf_reader_timeout_s)
        except ModelUnavailable as err:
            return None, f"model_unavailable: {err}"
        self.answers[k] = {"raw": raw, "photo": Path(photo).name, "fixture": fixture, "model": self.model,
                           "prompt": self.version}
        seal(self.folder, self.answers)
        return check(raw, shelves)
