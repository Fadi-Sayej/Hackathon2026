"""One reading of a day's shelf photos (F12-S1 FR-218 … FR-222; ADR-041).

    data/internal/shelf_photos/<YYYY-MM-DD>/<fixture>/<photo>.jpg     the store's photos, never published
    data/external/snapshots/<YYYY-MM-DD>/shelf_readings/answers.json  the AI's sealed answers
    configs/shelf_readings.yaml                                        what the reader read
    public/store/shelf-pictures/<barcode>.jpg                          one facing of each product read

The readings file is in the layout file's format, so the loader checks it the same way, and the
plan reads a width the same way wherever it came from. Every run that is not read says why.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from src.engine.shelf_reader import identity, measure

PHOTO_TYPES = {".jpg", ".jpeg", ".png", ".webp"}


def photos(root: Path, day: str) -> dict:
    """{fixture: [photo, ...]} for the day, by folder, in name order."""
    folder = Path(root) / day
    if not folder.is_dir():
        return {}
    return {d.name: sorted(p for p in d.iterdir() if p.suffix.lower() in PHOTO_TYPES)
            for d in sorted(folder.iterdir()) if d.is_dir()}


def read(*, day: str, photo_root: Path, layout: dict, products: list, sales_daily: list, sales_monthly: list,
         policy, asker, today: Optional[date] = None) -> dict:
    """{widths, current, pictures, report}: what was read, and why each run that was not, was not."""
    today = today or date.fromisoformat(day)
    pool = identity.candidates(products, sales_daily, sales_monthly, today, policy.shelf_reader_candidate_window_days)
    tolerance = policy.shelf_reader_tolerance_mm
    report: list = []
    reads: dict = defaultdict(list)          # barcode -> [(fixture, shelf, facings, width, why, picture)]

    for fixture, files in photos(photo_root, day).items():
        unit = (layout.get("fixtures") or {}).get(fixture)
        if unit is None:
            report.append({"fixture": fixture, "photo": None, "why": "no_such_fixture_in_the_layout_file"})
            continue
        for photo in files:
            answer, why = asker.read(photo, fixture, len(unit["shelves"]))
            if answer is None:
                report.append({"fixture": fixture, "photo": photo.name, "why": why})
                continue
            image = measure.upright(photo)
            g = measure.gray(image)
            for number, (shelf, stated) in enumerate(zip(answer["shelves"], unit["shelves"]), start=1):
                span, measured = measure.read_shelf(g, shelf)
                runs = [(position, run, *identity.identify(run.get("tag"), pool, run.get("package"), unit["departments"]),
                         *measured[position - 1])
                        for position, run in enumerate(shelf["runs"], start=1)]
                fits = span is not None and measure.runs_fit([e for *_, e, _ in runs if e], span,
                                                             stated["length_cm"] * 10, tolerance)
                for position, run, barcode, who, edges, edge_why in runs:
                    where = {"fixture": fixture, "photo": photo.name, "shelf": number, "run": position}
                    if barcode is None:
                        report.append({**where, "why": who})
                        continue
                    width, width_why = None, edge_why
                    if span is None:
                        width_why = "shelf_ends_not_found"
                    elif edges is not None and not fits:
                        width_why = "runs_do_not_fit"
                    elif edges is not None:
                        width, width_why = measure.width_mm(edges, span, stated["length_cm"] * 10, tolerance)
                    face = measure.picture(image, edges, run["box"]) if edges is not None else None
                    # The count is the AI's, confirmed by the edges found; unconfirmed, it is not recorded.
                    reads[barcode].append({**where, "facings": run["facings"], "counted": edges is not None,
                                           "width_mm": width, "width_why": width_why, "picture": face})

    widths, current, pictures = {}, {}, {}
    for barcode, seen in sorted(reads.items()):
        measured = [s["width_mm"] for s in seen if s["width_mm"] is not None]
        if measured and len(measured) == len(seen) and max(measured) - min(measured) <= tolerance:
            widths[barcode] = round(sum(measured) / len(measured))
        else:
            why = next((s["width_why"] for s in seen if s["width_why"]), None) or "read_twice_differs"
            report.append({"barcode": barcode, "why": why})
        if len(seen) > 1:
            report.append({"barcode": barcode, "why": "in_two_places"})
        elif not seen[0]["counted"]:
            report.append({"barcode": barcode, "why": "facings_not_confirmed"})
        else:
            current[barcode] = {"fixture": seen[0]["fixture"], "shelf": seen[0]["shelf"], "facings": seen[0]["facings"]}
        face = next((s["picture"] for s in seen if s["picture"]), None)
        if face:
            pictures[barcode] = face
    return {"widths": widths, "current": current, "pictures": pictures, "report": report}


def write(result: dict, *, day: str, model: str, prompt: str, readings_path: Path, pictures_dir: Path) -> None:
    """The readings file, in the layout file's format, and one picture a product (ADR-041 Decision 8)."""
    pictures_dir = Path(pictures_dir)
    pictures_dir.mkdir(parents=True, exist_ok=True)
    for barcode, face in result["pictures"].items():
        (pictures_dir / f"{barcode}.jpg").write_bytes(face)
    measured = {"measured_by": "reader", "measured_on": day}
    doc = {
        "reading": {"day": day, "model": model, "prompt": prompt},
        "widths": {b: {"width_mm": w, **measured} for b, w in sorted(result["widths"].items())},
        "current": {b: {**c, **measured} for b, c in sorted(result["current"].items())},
        "pictures": {b: {"file": f"{b}.jpg", "cropped_by": "reader", "cropped_on": day}
                     for b in sorted(result["pictures"])},
    }
    header = ("# Written by scripts/read_shelves.py, the shelf reader (F12-S1 FR-218 … FR-223, ADR-041).\n"
              "# Never edited by hand (D-34). The loader checks it as it checks the layout file.\n")
    Path(readings_path).write_text(header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
