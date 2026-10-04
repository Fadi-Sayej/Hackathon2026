# tests/engine/test_registry.py
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.engine.policy import load_policy
from src.engine.registry import (
    CAPABILITIES, UNVALUED_CAPABILITIES, check_unvalued_order, derive_status, value_policy_for,
)


@dataclass
class _Inputs:
    """Just enough of EngineInputs to derive a status from."""
    products: Any = None
    inventory: Any = None
    sales_summary: Any = None
    window: Any = None
    observations: Any = None
    matches: Any = None


def test_stock_derived_capabilities_carry_no_value():
    assert value_policy_for("reconciliation") == "none"
    assert value_policy_for("hygiene") == "none"
    assert value_policy_for("catalogue_lifecycle") == "none"
    assert value_policy_for("competitor_position") == "none"


def test_price_consistency_may_carry_per_sale():
    assert value_policy_for("price_consistency") == "per_sale"


def test_margin_below_cost_is_not_admitted_to_the_surface():
    assert CAPABILITIES["margin_below_cost"].admitted is False


def test_every_capability_names_its_spec():
    """V1's specs were numbered SPEC-NNN; since the 2026-09-08 restructure a spec is F#-S#."""
    import re
    for cap in CAPABILITIES.values():
        assert re.fullmatch(r"SPEC-\d{3}|F\d+-S\d+", cap.spec) or cap.spec == "UNSPECIFIED", cap


def test_hygiene_is_a_capability_of_its_own_and_spec_002_produces_two():
    """ADR-014: the smallest independently-unavailable unit. SPEC-002 yields two."""
    assert set(CAPABILITIES) == {"price_consistency", "reconciliation", "hygiene",
                                 "competitor_position", "catalogue_lifecycle",
                                 "owner_questions", "margin_below_cost",
                                 # Phase 5: F8's market signal (Task 5.4, ADR-031), boost
                                 # (Task 5.6, ADR-032) and quantity (Task 5.8, ADR-034)
                                 "market_running_out", "market_boost", "order_quantity", "assortment_gap",
                                 # Phase 8: F12's layout (Task 8.2) and plan (Task 8.3)
                                 "layout_facts", "shelf_plan", "shelf_measurement"}
    assert CAPABILITIES["hygiene"].spec == CAPABILITIES["reconciliation"].spec == "SPEC-002"
    assert "sales_summary" not in CAPABILITIES["hygiene"].requires


def test_status_is_derived_from_requires_not_declared():
    """SPEC-002 §11 — the seven monthly reports never arrive; hygiene is unaffected."""
    no_sales = _Inputs(products=[{"barcode": "1"}], inventory=[{"barcode": "1"}], sales_summary=None, window=None)
    assert derive_status("reconciliation", no_sales) == ("unavailable", "no_sales_evidence")
    assert derive_status("hygiene", no_sales) == ("available", None)
    no_pos = _Inputs(products=None, inventory=None)
    assert derive_status("hygiene", no_pos) == ("unavailable", "no_pos_data")
    # The reason names the input that is missing, not the capability that wanted it.
    assert derive_status("catalogue_lifecycle", no_pos) == ("unavailable", "no_pos_data")


def test_the_unvalued_order_in_policy_covers_every_unvalued_capability():
    """A capability missing from the order would never reach a reserved place (FR-106)."""
    check_unvalued_order(load_policy().surface_unvalued_order)
    assert set(UNVALUED_CAPABILITIES) == {"reconciliation", "competitor_position",
                                          "catalogue_lifecycle", "hygiene", "assortment_gap"}
    try:
        check_unvalued_order(("assortment_gap", "reconciliation", "competitor_position", "catalogue_lifecycle"))
    except ValueError as err:
        assert "hygiene" in str(err)
    else:
        raise AssertionError("an unlisted unvalued capability must be refused, not silently dropped")


def test_f12_reads_only_the_layout_file_and_the_existing_inputs():
    """F12-S1 INV-084, AC-183 (D-13): no camera, sensor or image feed is ever an input. Every F12
    capability's inputs are the layout file and inputs the engine already had."""
    allowed = {"products", "store_layout", "sales_daily"}
    f12 = {cid: set(c.requires) for cid, c in CAPABILITIES.items() if c.spec == "F12-S1"}
    assert {"layout_facts", "shelf_plan", "shelf_measurement"} <= set(f12)
    for cid, needs in f12.items():
        assert needs <= allowed, f"{cid} reads {sorted(needs - allowed)}"
