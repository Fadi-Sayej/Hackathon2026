"""The export must refuse to publish an empty dashboard.

Both pipeline bugs found on 2026-09-05 shared one shape: a glob over a directory
that did not exist returned nothing, which looks exactly like a successful run
that found nothing. The export wrote a valid, empty JSON file and exited 0 — on a
clean clone it overwrote a committed 3,035-recommendation file with 0.

The guard therefore has to do two things, and both are asserted here: fail loudly,
and fail *before* writing, so the last good export survives.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.export_dashboard_data as ex  # noqa: E402
from scripts.export_dashboard_data import EmptyExportError, export  # noqa: E402


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Point the exporter at empty directories and a sentinel output file."""
    out_dir = tmp_path / "public_data"
    out_dir.mkdir()
    sentinel = out_dir / "operational.json"
    sentinel.write_text('{"recommendations": ["PREVIOUS GOOD EXPORT"]}', encoding="utf-8")

    monkeypatch.setattr(ex, "PUBLIC_DATA_DIR", out_dir)
    for name in ("OPERATIONAL_DIR", "PRODUCT_RECS_DIR", "COMPETITOR_DIR",
                 "EXPIRY_SIGNALS_DIR", "SILVER_POS_ROOT"):
        monkeypatch.setattr(ex, name, tmp_path / "missing")

    monkeypatch.setattr(ex, "generate_operational_recommendations", lambda: {"status": "ok"})
    monkeypatch.setattr(ex, "_reconcile_sources_from_disk", lambda products: None)
    monkeypatch.setattr(ex, "write_summary", lambda: {"scraping_status": "complete"})
    monkeypatch.setattr(ex, "load_sources", dict)
    return sentinel


def test_zero_operational_recommendations_raises(isolated):
    with pytest.raises(EmptyExportError) as err:
        export()
    assert "zero operational recommendations" in str(err.value)


def test_failure_does_not_overwrite_the_previous_export(isolated):
    """The point of the guard: an empty run must not destroy the last good file."""
    with pytest.raises(EmptyExportError):
        export()
    assert json.loads(isolated.read_text())["recommendations"] == ["PREVIOUS GOOD EXPORT"]


def test_zero_competitor_recommendations_raises(isolated, monkeypatch):
    """Operational data present, market half absent — the seam-3 failure."""
    monkeypatch.setattr(ex, "_read_rows", lambda path: [])
    monkeypatch.setattr(
        ex, "_latest",
        lambda root, pattern: Path("x") if "operational" in pattern else None,
    )
    monkeypatch.setattr(ex, "_map_recommendation", lambda r: r)
    monkeypatch.setattr(
        ex, "_read_rows",
        lambda path: [{"type": "CHECK_MARGIN", "family": "operational"}] if path == Path("x") else [],
    )
    with pytest.raises(EmptyExportError) as err:
        export()
    assert "zero competitor recommendations" in str(err.value)


def test_allow_no_competitor_permits_the_pos_only_case(isolated, monkeypatch):
    """--allow-no-competitor is the deliberate POS-only escape hatch."""
    monkeypatch.setattr(
        ex, "_latest",
        lambda root, pattern: Path("x") if "operational" in pattern else None,
    )
    monkeypatch.setattr(ex, "_map_recommendation", lambda r: r)
    monkeypatch.setattr(
        ex, "_read_rows",
        lambda path: [{"type": "CHECK_MARGIN", "family": "operational"}] if path == Path("x") else [],
    )
    monkeypatch.setattr(ex, "_pos_health", lambda p, i, m: {})
    monkeypatch.setattr(ex, "_expiry_summary", lambda: {})

    result = export(allow_no_competitor=True)

    assert result["status"] == "ok"
    assert result["operational_count"] == 1
    assert result["competitor_count"] == 0
    assert json.loads(isolated.read_text())["recommendations"] != ["PREVIOUS GOOD EXPORT"]


def test_main_exits_nonzero_on_empty_export(isolated, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["export_dashboard_data.py"])
    assert ex.main() == 1
