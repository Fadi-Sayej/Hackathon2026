"""Drawn test shelves for the shelf reader's tests (Phase 8 Task 8.12; ADR-041).

These are test fixtures, not a store's data (D-23): flat drawings of a shelving unit, with
products of known widths, so the reader's widths can be checked against the truth. A real
photo is harder: perspective, glare, products that touch. The acceptance run on the next
store's first photos is what proves the reader (F12-S1 FR-223).

`draw(path, unit)` paints the unit and returns the truth: each shelf's ends, and each run's
box, in pixels. `answer(truth, size, jitter)` is what a model might say about it: the same
positions as fractions of the photo, each moved by up to `jitter` of the run's width, and the
tags as given.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

PX_PER_MM = 1.6
UPRIGHT_MM = 30
SHELF_HEIGHT_PX = 320
MARGIN_PX = 60
COLOURS = [(192, 57, 43), (41, 128, 185), (39, 174, 96), (214, 137, 16), (142, 68, 173), (22, 160, 133),
           (176, 58, 111), (44, 62, 80), (160, 64, 0), (93, 109, 126)]


def draw(path: Path, unit: dict) -> dict:
    """unit = {"length_cm": 120, "shelves": [[{"barcode", "width_mm", "facings", "tag", "gap_mm"?}, ...], ...]}"""
    inner = int(unit["length_cm"] * 10 * PX_PER_MM)
    upright = int(UPRIGHT_MM * PX_PER_MM)
    width = inner + 2 * upright + 2 * MARGIN_PX
    height = len(unit["shelves"]) * SHELF_HEIGHT_PX + 2 * MARGIN_PX
    image = Image.new("RGB", (width, height), (232, 228, 220))
    pen = ImageDraw.Draw(image)
    left_end, right_end = MARGIN_PX + upright, MARGIN_PX + upright + inner
    pen.rectangle((MARGIN_PX, MARGIN_PX, left_end - 1, height - MARGIN_PX), fill=(70, 70, 70))
    pen.rectangle((right_end, MARGIN_PX, right_end + upright - 1, height - MARGIN_PX), fill=(70, 70, 70))
    truth = {"size": (width, height), "shelves": []}
    colour = 0
    for number, runs in enumerate(unit["shelves"]):
        top = MARGIN_PX + number * SHELF_HEIGHT_PX
        floor = top + SHELF_HEIGHT_PX - 50
        pen.rectangle((left_end, floor, right_end - 1, floor + 14), fill=(110, 110, 110))   # the shelf's edge
        x = left_end + int(12 * PX_PER_MM)
        shelf = {"y_top": top + 20, "y_bottom": floor, "left": left_end, "right": right_end, "runs": []}
        for run in runs:
            face = int(round(run["width_mm"] * PX_PER_MM))
            product_top = floor - int(run.get("height_mm", 160) * PX_PER_MM)
            fill = COLOURS[colour % len(COLOURS)]
            colour += 1
            start = x
            for _ in range(run["facings"]):
                pen.rectangle((x, product_top, x + face - 1, floor - 1), fill=fill, outline=(20, 20, 20), width=2)
                pen.rectangle((x + face // 4, product_top + 20, x + 3 * face // 4, product_top + 60), fill=(250, 250, 250))
                x += face
            pen.rectangle((start, floor + 18, min(x, start + 120), floor + 44), fill=(255, 255, 255), outline=(0, 0, 0))
            shelf["runs"].append({"box": (start, product_top, x, floor), "facings": run["facings"],
                                  "tag": run.get("tag"), "package": run.get("package"),
                                  "barcode": run.get("barcode"), "width_mm": run["width_mm"]})
            x += int(run.get("gap_mm", 15) * PX_PER_MM)
        # The prompt's y_top: the top of the tallest product standing on the shelf.
        if shelf["runs"]:
            shelf["y_top"] = min(r["box"][1] for r in shelf["runs"])
        truth["shelves"].append(shelf)
    image.save(path, format="JPEG", quality=92)
    return truth


def answer(truth: dict, *, jitter: float = 0.04, seed: int = 1, facings: dict = None, vjitter: float = 0.0) -> str:
    """A model's answer about the drawing: rough boxes, the tags as given. `facings` overrides a
    run's count by (shelf, run) index, to show what happens when the model miscounts."""
    rng = random.Random(seed)
    width, height = truth["size"]
    shelves = []
    for s_index, shelf in enumerate(truth["shelves"]):
        runs = []
        for r_index, run in enumerate(shelf["runs"]):
            x0, y0, x1, y1 = run["box"]
            wobble = jitter * (x1 - x0)
            box = [max(0.0, (x0 + rng.uniform(-wobble, wobble)) / width), y0 / height,
                   min(1.0, (x1 + rng.uniform(-wobble, wobble)) / width), y1 / height]
            if vjitter:          # D-38: a model's box is rough top and bottom too
                tall = vjitter * (y1 - y0)
                box[1] = (y0 + rng.uniform(-tall, tall)) / height
                box[3] = (y1 + rng.uniform(-tall, tall)) / height
            runs.append({"box": box, "facings": (facings or {}).get((s_index, r_index), run["facings"]),
                         "tag": run["tag"], "package": run.get("package")})
        y_top, y_bottom = shelf["y_top"], shelf["y_bottom"]
        if vjitter:
            tall = vjitter * (y_bottom - y_top)
            y_top, y_bottom = y_top + rng.uniform(-tall, tall), y_bottom + rng.uniform(-tall, tall)
        shelves.append({"y_top": y_top / height, "y_bottom": y_bottom / height,
                        "left_x": (shelf["left"] + rng.uniform(-8, 8)) / width,
                        "right_x": (shelf["right"] + rng.uniform(-8, 8)) / width, "runs": runs})
    return json.dumps({"problem": None, "shelves": shelves}, ensure_ascii=False)


class FakeReader:
    """Answers each photo from its drawing's truth, and counts the requests (no network)."""

    def __init__(self, answers: dict):
        self.answers, self.calls = answers, 0

    def __call__(self, url, headers, body, timeout):
        self.calls += 1
        sent = json.loads(body)
        unit = json.loads(sent["messages"][0]["content"][-1]["text"])["unit"]
        text = self.answers[unit]
        return 200, json.dumps({"content": [{"type": "text", "text": text}]}).encode("utf-8")
