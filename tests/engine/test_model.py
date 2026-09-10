# tests/engine/test_model.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.engine.model import (
    CapabilityOutput, Entry, EvidenceWindow, Figure, Value, entry_id, norm_barcode,
)


def test_norm_barcode_strips_leading_zeros_and_blanks():
    assert norm_barcode("0007290000041445") == "7290000041445"
    assert norm_barcode("  12 ") == "12"
    assert norm_barcode("") is None
    assert norm_barcode(None) is None
    assert norm_barcode("000") is None


def test_entry_id_is_stable_and_independent_of_thresholds():
    a = entry_id("price.inverted", "7290000041445")
    b = entry_id("price.inverted", "07290000041445")
    assert a == b and len(a) == 16
    assert entry_id("hygiene.negative_stock", "1") != entry_id("hygiene.no_identifier", "1")


def test_entry_id_is_pinned_to_the_family_and_nothing_else():
    """ADR-009: the owner's recorded outcomes must not be orphaned by a taxonomy change.

    The digest is pinned deliberately. These sixteen characters are a key in the owner's
    Firestore document: any edit to the formula, the separator or the family string changes
    them, and an unmatched key does not error — it silently stops suppressing an entry he
    already declined. If this test fails, the change is a data migration, not a refactor."""
    assert entry_id("hygiene.negative_stock", "9") == "6713c7fd75250c38"
    assert entry_id("hygiene.negative_stock", "0009") == "6713c7fd75250c38"     # leading zeros stripped


def test_entry_id_refuses_an_unregistered_signal_family():
    try:
        entry_id("hygiene.typo", "1")
    except ValueError as err:
        assert "signal_family" in str(err)
    else:
        raise AssertionError("an unenumerated family would create ids nothing can ever match")


def test_value_rejects_unknown_kind():
    try:
        Value(amount=1.0, kind="one_off", certainty="confirmed")
    except ValueError:
        pass
    else:
        raise AssertionError("one_off is not a V1 value kind")


def test_capability_output_unavailable_has_no_entries_and_none_counts():
    out = CapabilityOutput.unavailable("reconciliation", "SPEC-002", "no_sales_evidence")
    d = out.to_dict()
    assert d["status"] == "unavailable"
    assert d["unavailable_reason"] == "no_sales_evidence"
    assert d["entries"] == []
    assert "figures" not in d


def test_window_id_and_serialisation():
    w = EvidenceWindow(months=["2026-01", "2026-02"], first="2026-01", last="2026-02", count=2, full_annual_cycle=False)
    assert w.window_id == "2026-01..2026-02"
    assert w.to_dict()["full_annual_cycle"] is False


def test_entry_to_dict_serialises_value_and_none():
    e = Entry(id="x", signal_family="price.inverted", capability="price_consistency", barcode="1", product_name="n", department="d",
              action="verify_price", characterisation="confirmed_loss", evidence={"shelf": 10.0},
              value=Value(2.0, "per_sale", "confirmed"), ordering_key={"name": "loss", "value": 2.0},
              actionable=True, not_actionable_reason=None, attention="today")
    d = e.to_dict()
    assert d["value"] == {"amount": 2.0, "kind": "per_sale", "certainty": "confirmed"}
    e2 = Entry(**{**e.__dict__, "value": None})
    assert e2.to_dict()["value"] is None
