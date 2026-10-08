"""The store's shelf photos as they stand in its copy, and which the reader has read (ADR-042).

    data/internal/shelf_photos/<YYYY-MM-DD>/<unit>/<photo>.jpg            collected, or committed by hand
    data/internal/shelf_photos/<YYYY-MM-DD>/<unit>/replaced/<photo>.jpg   an earlier photo of the unit, kept

A photo is read once the AI has answered for it; the readings file lists it under `photos` with the
day it was read (reading.write). Store layout shows each photo's unit, the night it was collected,
and the night it was read (F12-S1 FR-227). Nothing here opens a photo: only names and folders.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
PHOTOS_ROOT = ROOT / "data" / "internal" / "shelf_photos"
PHOTO_TYPES = {".jpg", ".jpeg", ".png", ".webp"}


def key(day: str, unit: str, name: str) -> str:
    """How the readings file names a photo: its place under the photos' folder."""
    return f"{day}/{unit}/{name}"


def on_disk(root: Path) -> list:
    """[(day, unit, photo path)] for every photo the reader would read, oldest day first."""
    root = Path(root)
    if not root.is_dir():
        return []
    out = []
    for day in sorted(d for d in root.iterdir() if d.is_dir()):
        for unit in sorted(u for u in day.iterdir() if u.is_dir()):
            out += [(day.name, unit.name, p) for p in sorted(unit.iterdir())
                    if p.is_file() and p.suffix.lower() in PHOTO_TYPES]
    return out


def read_marks(readings_path: Path) -> dict:
    """{photo key: the day it was read}, from the readings file. Absent or unreadable: none read."""
    try:
        raw = yaml.safe_load(Path(readings_path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    marks = raw.get("photos") if isinstance(raw, dict) else None
    if not isinstance(marks, dict):
        return {}
    return {str(k): str(v.get("read_on")) for k, v in marks.items()
            if isinstance(v, dict) and v.get("read_on")}


def listed(root: Path, readings_path: Path) -> list:
    """What Store layout lists: each photo's id, unit, the night it was collected, and when it was read."""
    marks = read_marks(readings_path)
    return [{"id": p.stem, "unit": unit, "collected": day, "read": marks.get(key(day, unit, p.name))}
            for day, unit, p in on_disk(root)]


def unread_days(root: Path, readings_path: Path) -> list:
    """The day folders holding a photo the reader has not read yet, oldest first."""
    marks = read_marks(readings_path)
    return sorted({day for day, unit, p in on_disk(root) if key(day, unit, p.name) not in marks})
