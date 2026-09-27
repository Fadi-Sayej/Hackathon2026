"""The pilot measurement the engine publishes (F13-S1, ADR-023 as revised 2026-09-27).

It counts what this run shows and what the owner decided, and states money only where a
decision's snapshot froze the value the engine published (ADR-016). No target (D-24), no
history (D-23), and no rate that divides decisions by one run's entries.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import json  # noqa: E402

import pytest  # noqa: E402

from src.engine.measurement import build_measurement, measure, write_measurement  # noqa: E402
from src.engine.model import CapabilityOutput, Entry  # noqa: E402
from src.owner_state.model import OwnerState  # noqa: E402

AT = 1790000000000          # 2026-09-21T14:13:20Z


def _entry(eid, family, capability="price_consistency"):
    return Entry(id=eid, signal_family=family, capability=capability, barcode="1", product_name="p",
                 department="d", action="a", characterisation="c", evidence={}, value=None,
                 ordering_key={})


def _run(*entries):
    out = CapabilityOutput(id="price_consistency", spec="SPEC-001", status="available")
    out.entries = list(entries)
    return [out, CapabilityOutput(id="hygiene", spec="SPEC-002", status="unavailable",
                                  unavailable_reason="no_inventory")]


def _decision(status, family, *, at=AT, value=None, kind="per_sale", certainty="confirmed", reason=None):
    snap = {"signal_family": family, "capability": "x", "barcode": "1"}
    if value is not None:
        snap.update(value=value, kind=kind, certainty=certainty)
    return {"status": status, "reason": reason, "at": at, "snapshot": snap}


def _owner(outcomes):
    return OwnerState.from_dict({"status": "available", "pulled_at": "2026-09-27T03:06:42Z", "outcomes": outcomes})


def test_without_the_owner_state_it_is_unavailable_and_states_no_count():
    m = measure(_run(_entry("e1", "price.inverted")), OwnerState.unavailable("pull_failed: RuntimeError"))
    assert m["status"] == "unavailable"
    assert m["unavailable_reason"] == "pull_failed: RuntimeError"
    assert "totals" not in m and "money" not in m          # FR-142: never zeros in its place


def test_nothing_decided_reads_as_nothing_decided_not_as_everything_dismissed():
    m = measure(_run(_entry("e1", "price.inverted"), _entry("e2", "price.inverted")), _owner({}))
    assert m["status"] == "available"
    assert m["totals"] == {"shown": 2, "decided": 0, "acted": 0, "declined": 0, "deferred": 0, "not_in_this_run": 0}
    assert m["window"] == {"first": None, "last": None, "pulled_at": "2026-09-27T03:06:42Z"}
    assert m["money"] == []
    assert m["by_family"]["price.inverted"]["shown"] == 2      # INV-068


def test_it_counts_each_status_per_family_and_in_total():
    outcomes = {
        "e1": _decision("acted", "price.inverted", value=3.5),
        "e2": _decision("declined", "price.inverted", reason="wrong_data"),
        "e3": _decision("deferred", "price.inverted"),
        "h1": _decision("declined", "hygiene.duplicate_barcode"),
    }
    m = measure(_run(_entry("e1", "price.inverted"), _entry("e2", "price.inverted"), _entry("e3", "price.inverted")),
                _owner(outcomes))
    assert m["totals"] == {"shown": 3, "decided": 4, "acted": 1, "declined": 2, "deferred": 1, "not_in_this_run": 1}
    assert m["by_family"]["price.inverted"] == {"shown": 3, "decided": 3, "acted": 1, "declined": 1,
                                                "deferred": 1, "not_in_this_run": 0}
    assert m["by_family"]["hygiene.duplicate_barcode"]["not_in_this_run"] == 1     # SCN-130: counted, not dropped
    assert m["declined_reasons"] == {"wrong_data": 1, "none": 1}


def test_money_comes_only_from_acted_decisions_that_froze_one():
    outcomes = {
        "e1": _decision("acted", "price.inverted", value=3.5),
        "e2": _decision("acted", "price.inverted", value=2.25),
        "e3": _decision("declined", "price.inverted", value=9.0),          # dismissed: no money
        "e4": _decision("acted", "reconciliation.gap"),                    # no value: a count only
        "o1": _decision("acted", "order.suggestion"),                      # D-1: an order carries none
    }
    m = measure(_run(), _owner(outcomes))
    assert m["money"] == [{"kind": "per_sale", "certainty": "confirmed", "amount": 5.75, "decisions": 2}]
    assert m["totals"]["acted"] == 4


def test_it_never_sums_two_kinds_or_two_certainties():
    outcomes = {
        "a": _decision("acted", "price.inverted", value=1.0),
        "b": _decision("acted", "price.inverted", value=2.0, certainty="estimated"),
        "c": _decision("acted", "margin.below_cost", value=4.0, kind="one_off"),
    }
    m = measure(_run(), _owner(outcomes))
    assert m["money"] == [
        {"kind": "one_off", "certainty": "confirmed", "amount": 4.0, "decisions": 1},
        {"kind": "per_sale", "certainty": "confirmed", "amount": 1.0, "decisions": 1},
        {"kind": "per_sale", "certainty": "estimated", "amount": 2.0, "decisions": 1},
    ]


def test_the_window_is_the_span_of_the_decisions():
    outcomes = {"a": _decision("acted", "price.inverted", at=AT),
                "b": _decision("declined", "price.inverted", at=AT + 86_400_000)}
    m = measure(_run(), _owner(outcomes))
    assert m["window"]["first"] == "2026-09-21T14:13:20Z"
    assert m["window"]["last"] == "2026-09-22T14:13:20Z"


def test_a_decision_without_its_family_is_kept_under_unknown():
    m = measure(_run(), _owner({"x": {"status": "acted", "at": AT, "snapshot": {}}}))
    assert m["by_family"]["unknown"]["acted"] == 1


def test_the_file_names_the_run_it_was_computed_with_and_validates():
    devices = {"status": "available", "reason": None, "count": 4, "last_seen_at": []}
    m = build_measurement(_run(_entry("e1", "price.inverted")), _owner({}), generated_at="g",
                          run_id="r", inputs_digest="d", devices=devices)
    assert (m["schema_version"], m["generated_at"], m["run_id"], m["inputs_digest"]) == (1, "g", "r", "d")
    assert m["devices"] == devices
    assert m["totals"]["shown"] == 1


def test_a_payload_that_breaches_the_schema_never_replaces_the_last_good_file(tmp_path):
    path = tmp_path / "measurement.json"
    good = build_measurement(_run(), _owner({}), generated_at="g", run_id="r", inputs_digest="d", devices=None)
    write_measurement(good, path)
    bad = {**good, "totals": {"shown": -1}}
    with pytest.raises(Exception):
        write_measurement(bad, path)
    assert json.loads(path.read_text(encoding="utf-8")) == good


def test_an_unavailable_measurement_is_a_valid_file_with_no_counts(tmp_path):
    m = build_measurement(_run(), OwnerState.unavailable("mirror_missing"), generated_at="g", run_id="r",
                          inputs_digest="d", devices=None)
    write_measurement(m, tmp_path / "m.json")
    assert m["status"] == "unavailable" and "totals" not in m
