"""Edges, widths and the checks, on the full-resolution photo (F12-S1 FR-221; ADR-041 Decisions 5, 6).

The AI's boxes only say where to look: the model sees a reduced copy of the photo, about 1.3 mm a
pixel across a 2 m unit before any error in its box. Here the photo is read at full resolution:
along a band of rows, how sharply brightness changes from one column to the next. A product's
edge, the gap between two facings, and the side of the unit are each a column where it changes
sharply.

    width_mm = run width ÷ facings ÷ shelf span × the shelf's stated length

A width is recorded only when every check passes. Otherwise it is unknown, with its reason (D-3).
"""
from __future__ import annotations

import io
from typing import Optional

import numpy as np
from PIL import Image

PICTURE_MAX_BYTES = 150 * 1024        # ADR-040's limit, checked again by the loader
PICTURE_HEIGHT = 360                  # pixels: a tile is 76 px tall on the page, at most 3× that on a screen


def gray(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L"), dtype=np.float32)


def _profile(g: np.ndarray, x0: int, x1: int, y0: int, y1: int) -> np.ndarray:
    """profile[i]: how sharply brightness changes between columns x0 + i and x0 + i + 1, averaged
    over rows y0 … y1. A vertical edge is a high value."""
    h, w = g.shape
    x0, x1 = max(0, x0), min(w - 1, x1)
    y0, y1 = max(0, y0), min(h, y1)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return np.zeros(0, dtype=np.float32)
    return np.abs(np.diff(g[y0:y1, x0:x1 + 1], axis=1)).mean(axis=0)


def _edges(g: np.ndarray, lo: float, hi: float, y0: int, y1: int) -> list:
    """The sharp edges between `lo` and `hi`: at least half the sharpest, and an edge a few pixels
    wide counted once."""
    lo, hi = int(lo), int(hi)
    p = _profile(g, lo, hi, y0, y1)
    if len(p) < 3 or float(p.max()) <= 0:
        return []
    floor = 0.5 * float(p.max())
    peaks = [i for i in range(len(p)) if p[i] >= floor and p[i] >= p[max(0, i - 1)] and p[i] >= p[min(len(p) - 1, i + 1)]]
    merged: list = []
    for i in peaks:
        if merged and i - merged[-1][-1] <= 4:
            merged[-1].append(i)
        else:
            merged.append([i])
    return [max(0, lo) + max(group, key=lambda i: p[i]) + 1 for group in merged]


def _columns(g: np.ndarray, x0: int, x1: int, y0: int, y1: int) -> np.ndarray:
    """The mean brightness of each column: a run's picture, flattened to one line."""
    return g[max(0, y0):y1, max(0, x0):x1].mean(axis=0)


def _match(q: np.ndarray, lag: int) -> float:
    """How closely the line matches itself shifted by `lag` pixels: 1 is identical."""
    a, b = q[:-lag], q[lag:]
    a, b = a - a.mean(), b - b.mean()
    denominator = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum()) / denominator if denominator > 0 else 0.0


def _repeats(q: np.ndarray, most: int = 6, floor: float = 0.6) -> bool:
    """Whether the run repeats itself at width ÷ m for some m from 2 to `most`, as identical
    facings do."""
    return any(1 <= int(round(len(q) / m)) < len(q) and _match(q, int(round(len(q) / m))) >= floor
               for m in range(2, most + 1))


REPEAT_FLOOR = 0.6       # how closely neighbouring facings must match to count as the same product


def _junction(g: np.ndarray, end_a: float, start_b: float, reach_a: float, reach_b: float, y0: int, y1: int) -> tuple:
    """Where one thing ends and the next begins: (a's end, b's start, ambiguous).

    Between two products, or a side of the unit and a product, there are two edges with a gap
    between them, or one shared edge where they touch. The edges are searched for together, so
    the next product's edge is never taken for this one's."""
    lo, hi = min(end_a - reach_a, start_b - reach_b), max(end_a + reach_a, start_b + reach_b)
    edges = _edges(g, lo, hi, y0, y1)
    if not edges:
        return None, None, True
    if len(edges) == 1:
        return edges[0], edges[0], False
    if len(edges) == 2:
        return edges[0], edges[1], False
    pairs = [(a, b) for a in edges for b in edges if a < b]
    a, b = min(pairs, key=lambda ab: abs(ab[0] - end_a) + abs(ab[1] - start_b))
    return a, b, True


def read_shelf(g: np.ndarray, shelf: dict) -> tuple:
    """(span, [(boundaries, why), ...]) for one shelf: the unit's sides at the line of the product
    fronts, and each run's edges and facing boundaries, or why not."""
    h, w = g.shape
    runs = shelf["runs"]
    y0, y1 = int(shelf["y_top"] * h), int(shelf["y_bottom"] * h)
    starts = [r["box"][0] * w for r in runs]
    ends = [r["box"][2] * w for r in runs]
    pitches = [(e - s) / r["facings"] for s, e, r in zip(starts, ends, runs)]
    # The junctions, left to right: the left side and the first run, each pair of neighbours, the
    # last run and the right side. A run's edge is searched within a fifth of its pitch; a side of
    # the unit, a thin straight line, within 1% of the photo's width, so the side's outer edge and
    # the products near it stay out of its search.
    side = 0.01 * w + 3
    run_reach = [0.2 * p + 3 for p in pitches]
    marks = [shelf["left_x"] * w] + [x for pair in zip(starts, ends) for x in pair] + [shelf["right_x"] * w]
    reaches = [(side, run_reach[0] if runs else side)] + [(run_reach[i], run_reach[i + 1]) for i in range(len(runs) - 1)] \
        + [(run_reach[-1] if runs else side, side)]
    # Each run's middle rows: its top is uneven, and its bottom touches the shelf's edge. A
    # junction is read on the rows both its neighbours fill, so a short product's edge is not
    # outweighed by the unit's full-height side.
    bands = [(int(r["box"][1] * h + 0.15 * (r["box"][3] - r["box"][1]) * h),
              int(r["box"][3] * h - 0.15 * (r["box"][3] - r["box"][1]) * h)) for r in runs]
    rows = ([bands[0]] if runs else [(y0, y1)]) + [(max(bands[i][0], bands[i + 1][0]), min(bands[i][1], bands[i + 1][1]))
                                                   for i in range(len(runs) - 1)] + ([bands[-1]] if runs else [])
    found, ambiguous = [], []
    for i in range(len(runs) + 1):
        a, b, unsure = _junction(g, marks[2 * i], marks[2 * i + 1], *reaches[i], *rows[min(i, len(rows) - 1)])
        found += [a, b]
        ambiguous.append(unsure)
    left_side, right_side = found[0], found[-1]
    span = (left_side, right_side) if (left_side is not None and right_side is not None
                                       and not ambiguous[0] and not ambiguous[-1]
                                       and right_side - left_side >= 0.2 * w) else None
    results = []
    for i, run in enumerate(runs):
        left, right = found[2 * i + 1], found[2 * i + 2]
        results.append(_facings(g, left, right, run["facings"], ambiguous[i] or ambiguous[i + 1], *bands[i]))
    return span, results


def _facings(g: np.ndarray, left, right, facings: int, unsure: bool, band0: int, band1: int) -> tuple:
    """(boundaries, None) or (None, why). Identical facings repeat the same picture, so the facing
    width is the shift at which the run matches itself best, within a fifth of the AI's pitch.
    That shift also counts the facings independently of the AI. One facing has no repetition to
    check its edges by, so a junction with more than two edges leaves its width unknown, and it
    must not repeat itself at all."""
    if left is None or right is None or right - left < 4 * facings:
        return None, "edges_not_found"
    line = _columns(g, left, right, band0, band1)
    if facings == 1:
        if unsure:
            return None, "edges_ambiguous"
        return ([left, right], None) if not _repeats(line) else (None, "facing_count_differs")
    pitch = (right - left) / facings
    scored = [(_match(line, lag), lag) for lag in range(max(2, int(0.8 * pitch)), min(len(line) - 2, int(1.2 * pitch)) + 1)]
    if not scored:
        return None, "facing_count_differs"
    score, period = max(scored)
    if score < REPEAT_FLOOR or round((right - left) / period) != facings:
        return None, "facing_count_differs"
    return [left + k * period for k in range(facings)] + [right], None


def width_mm(boundaries: list, span: tuple, length_mm: float, tolerance_mm: float) -> tuple:
    """(width, None), or (None, why): the facings' mean width in whole millimetres, if they agree."""
    mm_per_px = length_mm / (span[1] - span[0])
    widths = [(b - a) * mm_per_px for a, b in zip(boundaries, boundaries[1:])]
    if max(widths) - min(widths) > tolerance_mm:
        return None, "facings_disagree"
    return int(round(sum(widths) / len(widths))), None


def runs_fit(edges: list, span: tuple, length_mm: float, tolerance_mm: float) -> bool:
    """The runs stand within the shelf's span, in order, without overlapping, within the tolerance."""
    slack = tolerance_mm * (span[1] - span[0]) / length_mm
    if not edges:
        return True
    if edges[0][0] < span[0] - slack or edges[-1][-1] > span[1] + slack:
        return False
    return all(a[-1] <= b[0] + slack for a, b in zip(edges, edges[1:]))


def picture(image: Image.Image, boundaries: list, box: list) -> bytes:
    """One facing, the middle one, cut from the full photo as a JPEG within ADR-040's limit."""
    h = image.size[1]
    middle = len(boundaries) // 2 - (1 if len(boundaries) % 2 == 0 else 0)
    left, right = boundaries[middle], boundaries[middle + 1]
    face = image.crop((left, int(box[1] * h), right, int(box[3] * h))).convert("RGB")
    if face.size[1] > PICTURE_HEIGHT:
        face = face.resize((max(1, round(face.size[0] * PICTURE_HEIGHT / face.size[1])), PICTURE_HEIGHT))
    for quality in (85, 75, 65, 50):
        out = io.BytesIO()
        face.save(out, format="JPEG", quality=quality)
        if out.tell() <= PICTURE_MAX_BYTES:
            return out.getvalue()
    return out.getvalue()
