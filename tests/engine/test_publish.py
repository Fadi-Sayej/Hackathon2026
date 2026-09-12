# tests/engine/test_publish.py
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from src.engine.model import CapabilityOutput, Entry, Value
from src.engine.publish import PublishRefused, build_artefact, validate_artefact, write_atomic

VINTAGES = {"pos": {"file": "x.csv", "as_of": "2026-08-02"},
            "sales": {"months": ["2026-01"], "first": "2026-01", "last": "2026-01",
                      "full_annual_cycle": False, "imported_this_run": True},
            "competitor": {"snapshot_date": None, "sources": []},
            "owner_state": {"pulled_at": None, "status": "unavailable"}}
RUN = {"status": "ok", "steps": []}


def _artefact(outputs):
    return build_artefact(outputs, vintages=VINTAGES, thresholds={"surface": {"bound": 10, "unvalued_places": 3}},
                          run=RUN, generated_at="2026-09-08T00:00:00+00:00", run_id="r1",
                          inputs_digest="0" * 64)


def test_empty_capability_set_is_a_valid_artefact():
    art = _artefact([])
    validate_artefact(art)
    assert art["schema_version"] == 2
    assert art["value_kinds_present"] == []


def test_refuses_a_capability_without_status():
    art = _artefact([CapabilityOutput.unavailable("reconciliation", "SPEC-002", "x")])
    art["capabilities"]["reconciliation"]["status"] = None
    with pytest.raises(PublishRefused):
        validate_artefact(art)


def test_refuses_value_on_a_none_policy_capability():
    e = Entry(id="a1b2c3d4e5f60718", signal_family="recon.impossible_opening", capability="reconciliation", barcode="1",
              product_name=None, department=None,
              action="count_product", characterisation="inconsistent", evidence={},
              value=Value(5.0, "per_sale", "confirmed"), ordering_key={"name": "gap_ratio", "value": 1.0})
    out = CapabilityOutput(id="reconciliation", spec="SPEC-002", status="available", entries=[e])
    # The id must be a real 16-hex entry id, or the schema refuses first and this test
    # passes for the wrong reason — it would never exercise the money rule at all.
    with pytest.raises(PublishRefused, match="value_policy"):
        validate_artefact(_artefact([out]))


def test_value_kinds_present_is_derived():
    e = Entry(id="b1c2d3e4f5061728", signal_family="price.inverted", capability="price_consistency", barcode="1",
              product_name=None, department=None,
              action="verify_price", characterisation="confirmed_loss", evidence={},
              value=Value(5.0, "per_sale", "confirmed"), ordering_key={"name": "loss_per_sale", "value": 5.0})
    out = CapabilityOutput(id="price_consistency", spec="SPEC-001", status="available", entries=[e])
    assert _artefact([out])["value_kinds_present"] == ["per_sale"]


def test_a_full_run_missing_a_registry_id_is_refused():
    """ADR-014: capabilities{} is exactly the registry. A capability that silently stops
    being published reads on the page as "nothing to act on", not as "unavailable"."""
    art = _artefact([CapabilityOutput.unavailable("reconciliation", "SPEC-002", "no_sales_evidence")])
    validate_artefact(art)                                   # a partial run is fine
    with pytest.raises(PublishRefused, match="hygiene"):
        validate_artefact(art, require_complete_registry=True)


def test_write_atomic_never_leaves_a_torn_file(tmp_path):
    target = tmp_path / "dashboard.json"
    target.write_text("OLD", encoding="utf-8")
    write_atomic(target, _artefact([]))
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == 2
    assert not (tmp_path / "dashboard.json.tmp").exists()


def test_the_artefact_says_what_it_was_built_from():
    """Task 3.1. AC-127 asks whether a fresh clone reproduces the committed figures.
    Without a digest the only answer is "the numbers look the same", which is how 14,406
    became 2,848 in the documents with nobody noticing."""
    art = build_artefact([], vintages=VINTAGES, thresholds={"surface": {"bound": 10}},
                         run=RUN, generated_at="2026-09-08T00:00:00+00:00", run_id="r1",
                         inputs_digest="a" * 64)
    validate_artefact(art)
    assert art["inputs_digest"] == "a" * 64


def test_an_artefact_without_a_digest_is_refused():
    art = _artefact([])
    art.pop("inputs_digest", None)
    with pytest.raises(PublishRefused, match="inputs_digest"):
        validate_artefact(art)
