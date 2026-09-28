# tests/test_check_v1_signals.py
"""The V1 boundary probe must withhold every input a capability declares (rule 12).

It withheld only products, inventory, sales_summary and window. competitor_position declares
`observations` and `matches` too, and neither was ever withheld, so the probe said "every
capability depends on exactly what it declares" without having looked at F3's market half
(F3 validation record, "boundary probe" row, 2026-09-28).

The guard below is what would have caught that: every input a registered capability
requires is withheld by this probe, or named with the probe that withholds it instead.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import check_v1_signals as probe  # noqa: E402
from src.engine.inputs import load_inputs  # noqa: E402
from src.engine.policy import load_policy  # noqa: E402
from src.engine.registry import CAPABILITIES  # noqa: E402
from src.owner_state.model import OwnerState  # noqa: E402

REQUIRED = {key for cap in CAPABILITIES.values() for key in cap.requires}


def test_every_required_input_is_withheld_here_or_by_a_named_probe():
    assert probe.unprobed_inputs() == [], (
        "a capability requires an input that no probe withholds: add it to check_v1_signals.py's "
        "SILVER_FILES or MARKET_SOURCES, or to PROBED_ELSEWHERE with the probe that withholds it")


def test_the_guard_would_have_caught_the_market_half():
    """Demonstrated, not described: with the two market inputs taken back out, the guard names
    exactly them, which is the state the probe was in until 2026-09-28."""
    withheld = set(probe.WITHHELD) - {"observations", "matches"}
    assert probe.unprobed_inputs(withheld=withheld) == ["matches", "observations"]


def test_an_input_is_probed_in_one_place_only():
    assert not set(probe.WITHHELD) & set(probe.PROBED_ELSEWHERE)


def test_every_exemption_is_required_by_something_and_names_a_real_probe():
    """A stale exemption would read as coverage for an input nothing declares any more."""
    for key, where in probe.PROBED_ELSEWHERE.items():
        assert key in REQUIRED, f"{key} is exempted but no capability requires it"
        assert (ROOT / where).exists(), f"{key} names {where}, which does not exist"


# check_order_signals.py describes what it withholds in the owner's terms. Each exempted input
# is named here with the words that probe uses for it.
_F8_WORDING = {"sales_daily": "report days", "running_out": "market snapshots",
               "boost_picks": "boost picks", "store_facts": "store facts",
               # F9-S1: the same snapshots, withheld in the same case (AC-165).
               "market_recent": "F9's assortment gap goes unavailable"}


def test_the_f8_probe_withholds_each_input_exempted_to_it():
    text = (ROOT / "scripts" / "check_order_signals.py").read_text(encoding="utf-8")
    for key, where in probe.PROBED_ELSEWHERE.items():
        if where.endswith("check_order_signals.py"):
            assert _F8_WORDING[key] in text, f"check_order_signals.py does not withhold {key}"


def test_the_market_half_is_withheld_through_run_engines_own_paths(tmp_path):
    """Not a silver file: run_engine reads observations from signals_dir and matches from
    matches_path, so the probe points those at nothing and load_inputs must see None."""
    silver = tmp_path / "silver"
    silver.mkdir()
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    for key in ("observations", "matches"):
        sources = probe.withheld_sources(key, silver, tmp_path / key)
        assert sources["silver_dir"].is_dir()
        inputs = load_inputs(policy=load_policy(), owner=OwnerState.unavailable("test"),
                             run_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
                             silver_dir=sources["silver_dir"],
                             signals_dir=sources.get("signals_dir", tmp_path / "unused-signals"),
                             matches_path=sources.get("matches_path", tmp_path / "unused.parquet"),
                             snapshots_root=snapshots)
        assert getattr(inputs, key) is None
    assert probe.withheld_sources("observations", silver, tmp_path / "o2")["signals_dir"].is_dir()
    assert not any(probe.withheld_sources("observations", silver, tmp_path / "o3")["signals_dir"].iterdir())
    assert not probe.withheld_sources("matches", silver, tmp_path / "m2")["matches_path"].exists()
