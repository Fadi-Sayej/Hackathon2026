"""
raw_storage.py — save raw HTTP responses and raw files with metadata.

Every future collector calls one of two functions:

  • save_raw_response() — for HTTP-fetched content (API / HTML pages / feeds).
  • save_raw_file()     — for already-downloaded binary blobs (CSVs from email,
                          government ZIP extracts, etc.).

Both functions:
  - Derive the output path from paths.py (single source of truth).
  - Detect the file extension from content_type or original_filename.
  - Compute a SHA-256 hash of the body before writing.
  - Write a companion _metadata.json next to the data file.
  - Never overwrite: if the target path already exists the file is re-named
    with its SHA-256 prefix so the original is preserved.
  - Auto-create all required parent directories.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from loguru import logger

from src.common.paths import get_raw_path, get_raw_metadata_path

# ── Content-type → extension mapping ─────────────────────────────────────────

_CONTENT_TYPE_EXT: dict[str, str] = {
    "application/json": "json",
    "text/json": "json",
    "text/html": "html",
    "application/xhtml+xml": "html",
    "text/xml": "xml",
    "application/xml": "xml",
    "text/csv": "csv",
    "application/csv": "csv",
    "text/plain": "txt",
    "application/octet-stream": "bin",
    "application/pdf": "pdf",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
    "application/gzip": "gz",
    "application/x-gzip": "gz",
}


def _ext_from_content_type(content_type: Optional[str]) -> str:
    """Map a MIME type to a file extension (defaults to 'bin')."""
    if not content_type:
        return "bin"
    mime = content_type.split(";")[0].strip().lower()
    return _CONTENT_TYPE_EXT.get(mime, "bin")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_write(path: Path, data: bytes, sha256_hash: str) -> Path:
    """
    Write *data* to *path*, avoiding overwrites.

    If the target already exists and has the same hash, the original is reused
    and the path is returned unchanged.  If the hash differs, the file is
    written to <stem>_<sha256[:8]><suffix> and that new path is returned.
    """
    if path.exists():
        existing_hash = _sha256(path.read_bytes())
        if existing_hash == sha256_hash:
            logger.debug(
                "Skipping write — identical file already exists: {}", path
            )
            return path
        # Different content: use a hash-suffixed name to avoid collision
        path = path.with_stem(f"{path.stem}_{sha256_hash[:8]}")
        logger.warning("File collision detected; writing to {}", path)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    logger.info("Raw file saved ({} bytes): {}", len(data), path)
    return path


def _write_metadata(
    metadata_path: Path,
    *,
    url: Optional[str],
    method: Optional[str],
    status_code: Optional[int],
    content_type: Optional[str],
    observed_at: str,
    file_path: Path,
    sha256: str,
    extra: Optional[dict] = None,
) -> None:
    """Serialise metadata alongside the raw data file."""
    payload: dict = {
        "url": url,
        "method": method,
        "status_code": status_code,
        "content_type": content_type,
        "observed_at": observed_at,
        "file_path": str(file_path),
        "sha256": sha256,
    }
    if extra:
        payload.update(extra)

    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.debug("Metadata written: {}", metadata_path)


# ── Public API ─────────────────────────────────────────────────────────────────

def save_raw_response(
    source_id: str,
    url: str,
    method: str,
    status_code: int,
    headers: dict,
    body: bytes,
    content_type: Optional[str],
    observed_at: str | datetime,
) -> tuple[Path, Path]:
    """
    Persist a raw HTTP response body and its metadata.

    Parameters
    ----------
    source_id    : Collector identifier, e.g. "wolt", "price_transparency".
    url          : Full request URL.
    method       : HTTP method, e.g. "GET".
    status_code  : HTTP status code, e.g. 200.
    headers      : Response headers as a plain dict.
    body         : Raw response bytes.
    content_type : Value of the Content-Type response header (may be None).
    observed_at  : ISO-8601 string or datetime of the fetch moment.

    Returns
    -------
    (data_path, metadata_path) — absolute paths to the written files.
    """
    if isinstance(observed_at, datetime):
        observed_at_str = observed_at.isoformat()
    else:
        observed_at_str = observed_at

    ext = _ext_from_content_type(content_type)
    target_path = get_raw_path(source_id, observed_at_str, ext)
    sha = _sha256(body)

    data_path = _safe_write(target_path, body, sha)

    # Derive the metadata path relative to the actual written data path
    metadata_path = data_path.parent / f"{data_path.name}_metadata.json"
    _write_metadata(
        metadata_path,
        url=url,
        method=method,
        status_code=status_code,
        content_type=content_type,
        observed_at=observed_at_str,
        file_path=data_path,
        sha256=sha,
        extra={"headers": dict(headers)},
    )

    return data_path, metadata_path


def save_raw_file(
    source_id: str,
    original_filename: str,
    file_bytes: bytes,
    observed_at: str | datetime,
    source_url: Optional[str] = None,
) -> tuple[Path, Path]:
    """
    Persist an already-downloaded file (CSV, ZIP, PDF, …) and its metadata.

    The extension is taken from *original_filename*; if missing, falls back
    to 'bin'.

    Parameters
    ----------
    source_id         : Collector identifier.
    original_filename : The original name of the file (used for extension).
    file_bytes        : Raw file bytes.
    observed_at       : ISO-8601 string or datetime of when the file was obtained.
    source_url        : Optional URL where the file originated.

    Returns
    -------
    (data_path, metadata_path) — absolute paths to the written files.
    """
    if isinstance(observed_at, datetime):
        observed_at_str = observed_at.isoformat()
    else:
        observed_at_str = observed_at

    suffix = Path(original_filename).suffix.lstrip(".") or "bin"
    target_path = get_raw_path(source_id, observed_at_str, suffix)
    sha = _sha256(file_bytes)

    data_path = _safe_write(target_path, file_bytes, sha)

    metadata_path = data_path.parent / f"{data_path.name}_metadata.json"
    _write_metadata(
        metadata_path,
        url=source_url,
        method=None,
        status_code=None,
        content_type=None,
        observed_at=observed_at_str,
        file_path=data_path,
        sha256=sha,
        extra={"original_filename": original_filename},
    )

    return data_path, metadata_path
