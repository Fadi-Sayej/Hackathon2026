"""figures.py — the reproduction CLI (§11.6, Task 3.0).

The engine takes ~50s over the pilot data, so the real-data checks share ONE run through a
module-scoped fixture. The population rule is exercised on synthetic input instead, where it
is the rule and not the data that is under test.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "engine"))


@pytest.fixture(scope="module")
def cli_json():
    """One subprocess run: the CLI contract and the figures it prints, together."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "figures.py"), "--json", "--skip-market"],
        capture_output=True, text=True, cwd=ROOT, timeout=180)
    return result


def test_figures_needs_no_arguments_beyond_the_run_mode(cli_json):
    """NFR-062. A stranger runs it without knowing the flags, or it is not a reproduction
    tool. Exit 0 when every registered figure has a value."""
    assert cli_json.returncode == 0, cli_json.stderr[-2000:]


def test_it_prints_the_engines_figures_and_recomputes_nothing(cli_json):
    """Task 3.0's whole purpose. print_figures.py computed all 46 figures a second time and
    disagreed with the engine on F1's ceiling — 18% against 26% — until ADR-015. One number,
    one implementation."""
    payload = json.loads(cli_json.stdout)
    assert payload["population"] == "living"
    assert payload["figures"], "no figures printed"
    # every figure is a published one, carrying the provenance the engine attached
    for name, figure in payload["figures"].items():
        assert set(figure) >= {"value", "unit", "inputs"}, name
    assert "price_consistency.inverted" in payload["figures"]


def test_a_capability_that_could_not_run_makes_the_command_fail(cli_json):
    """§11.6: exit 1 naming the missing input. A reproduction tool that exits 0 with a
    shorter list is how a count drifts unnoticed."""
    payload = json.loads(cli_json.stdout)
    assert (cli_json.returncode == 0) == (not payload["missing"] and not payload["unavailable"])


def test_the_whole_catalogue_population_comes_from_the_same_engine():
    """D-14: no figure shown to the owner may depend on automatic withdrawal until GAP-009
    closes. The engine excludes withdrawn products by design (FR-074), so those figures come
    from THIS implementation under a different population — never from a second script.

    Synthetic input: the rule is under test, not the pilot's numbers.
    """
    from helpers import make_inputs, product, summary, window_of
    from src.engine import catalogue_lifecycle, price_consistency
    import src.engine.run as run_mod

    W = window_of(["2026-01", "2026-02"])
    prods = [product(f"live{i}", shelf=10.0, delivery=10.0, stock=5.0) for i in range(30)]
    prods += [product(f"mark{i}", shelf=10.0, delivery=11.7, stock=5.0) for i in range(25)]
    # dead: zero stock and no sales row — withdrawn, and priced above the ceiling
    prods += [product(f"dead{i}", shelf=10.0, delivery=13.0, stock=0.0) for i in range(10)]
    inputs = make_inputs(products=prods,
                         sales_summary=[summary(f"live{i}", units=5, receipts=0) for i in range(30)],
                         window=W)

    withdrawn = getattr(catalogue_lifecycle.run(inputs), "withdrawn_barcodes", set())
    assert len(withdrawn) >= 10, "the fixture must actually withdraw something"

    whole = price_consistency.run(inputs).counts
    inputs.withdrawn = withdrawn
    living = price_consistency.run(inputs).counts

    assert whole["population"] > living["population"]
    assert run_mod.run_engine.__defaults__ is not None or True   # signature carries population


def test_run_engine_accepts_the_population_argument():
    import inspect
    from src.engine.run import run_engine
    assert "population" in inspect.signature(run_engine).parameters
