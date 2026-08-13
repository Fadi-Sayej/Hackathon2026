"""The operator-facing side of src/internal/restock_reconcile.py.

The reconciliation arithmetic itself is covered by tests/test_restock_reconcile.py.
What is checked here is the script that gives it a caller: that it survives the
states a real pilot machine is actually in, and that a disagreement is legible
when there is one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.reconcile_restocks import format_report, group_by_verdict, main  # noqa: E402
from src.internal.receiving import add_receipt  # noqa: E402


def _report(**verdicts: str) -> dict:
    return {
        barcode: {
            "inferred_restocked": 10.0,
            "recorded_received": 4.0,
            "delta": 6.0,
            "verdict": verdict,
        }
        for barcode, verdict in verdicts.items()
    }


def test_empty_everything_is_reported_as_normal_not_as_a_problem(tmp_path: Path, capsys) -> None:
    # A fresh clone: no ledger, no snapshots. This must not read as a fault, or
    # whoever runs it learns to ignore the output.
    exit_code = main([
        "--receipts", str(tmp_path / "absent.csv"),
        "--snapshots", str(tmp_path / "no-snapshots"),
    ])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "0 receipt lines" in out
    assert "Nothing to reconcile yet" in out
    assert "expected state" in out


def test_receipts_but_no_usable_snapshots_says_so_plainly(tmp_path: Path, capsys) -> None:
    ledger = tmp_path / "receipts.csv"
    add_receipt(barcode="111", quantity=12, supplier="Osem",
                received_at="2026-08-10", path=ledger)

    exit_code = main(["--receipts", str(ledger), "--snapshots", str(tmp_path / "none")])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "1 receipt lines" in out
    assert "fewer than two comparable POS snapshots" in out


def test_json_mode_emits_the_raw_report(tmp_path: Path, capsys) -> None:
    exit_code = main([
        "--receipts", str(tmp_path / "absent.csv"),
        "--snapshots", str(tmp_path / "none"),
        "--json",
    ])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload == {"receipts": 0, "intervals": 0, "report": {}}


def test_verdicts_are_grouped_worst_gap_first() -> None:
    report = {
        "111": {"inferred_restocked": 10.0, "recorded_received": 8.0, "delta": 2.0,
                "verdict": "under_recorded"},
        "222": {"inferred_restocked": 30.0, "recorded_received": 5.0, "delta": 25.0,
                "verdict": "under_recorded"},
        "333": {"inferred_restocked": 0.0, "recorded_received": 4.0, "delta": -4.0,
                "verdict": "unobserved"},
    }
    grouped = group_by_verdict(report)
    assert [row["barcode"] for row in grouped["under_recorded"]] == ["222", "111"]
    assert [row["barcode"] for row in grouped["unobserved"]] == ["333"]


def test_the_costly_verdict_is_printed_before_the_harmless_one() -> None:
    text = format_report(_report(aaa="matches", bbb="no_receipts"), receipt_count=5,
                         interval_count=2)
    assert text.index("no_receipts") < text.index("matches")
    assert "Barcodes compared: 2 with movement" in text


def test_barcodes_that_never_moved_are_counted_not_called_agreements() -> None:
    # Every barcode seen in two snapshots gets a zero row, so thousands arrive
    # with verdict 'matches' and nothing behind them. Listing those as
    # reconciliations would turn a one-delivery ledger into a wall of success.
    report = {
        "111": {"inferred_restocked": 10.0, "recorded_received": 10.0, "delta": 0.0,
                "verdict": "matches"},
        "222": {"inferred_restocked": 0.0, "recorded_received": 0.0, "delta": 0.0,
                "verdict": "matches"},
        "333": {"inferred_restocked": 0.0, "recorded_received": 0.0, "delta": 0.0,
                "verdict": "matches"},
    }
    text = format_report(report, receipt_count=1, interval_count=2)
    assert "Barcodes compared: 1 with movement" in text
    assert "2 with no restock and no delivery" in text
    assert "matches — agree (within tolerance) (1)" in text


def test_long_verdict_groups_are_truncated_with_a_count() -> None:
    report = _report(**{f"bc{index}": "under_recorded" for index in range(12)})
    text = format_report(report, receipt_count=12, interval_count=3, limit=10)
    assert "... and 2 more" in text
