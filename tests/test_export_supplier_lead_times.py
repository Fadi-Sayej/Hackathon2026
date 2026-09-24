"""The JSON contract of the lead-time export. Its reader, scripts/normalize-datasets.mjs,
was removed on 2026-09-24 (ADR-028); see scripts/export_supplier_lead_times.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.export_supplier_lead_times import build_lead_time_export, main  # noqa: E402
from src.internal.receiving import add_receipt  # noqa: E402


def _seed(ledger: Path) -> None:
    for day in ("2026-08-01", "2026-08-08", "2026-08-15"):
        add_receipt(barcode="7290000066318", quantity=12, supplier="Tempo",
                    received_at=day, path=ledger)
    add_receipt(barcode="111", quantity=6, supplier="Osem",
                received_at="2026-08-02", path=ledger)


def test_export_shape_is_the_documented_contract(tmp_path: Path) -> None:
    ledger = tmp_path / "receipts.csv"
    _seed(ledger)

    from src.internal.receiving import load_receipts

    payload = build_lead_time_export(load_receipts(ledger))

    assert set(payload) == {
        "generatedAt", "defaultLeadTimeDays", "minDeliveriesForLeadTime",
        "leadTimes", "supplierByBarcode", "totals",
    }
    assert payload["defaultLeadTimeDays"] == 3
    assert payload["leadTimes"]["Tempo"]["median_days"] == 7
    assert payload["leadTimes"]["Osem"]["median_days"] is None
    assert payload["supplierByBarcode"]["7290000066318"] == "Tempo"
    assert payload["totals"] == {"receipts": 4, "suppliers": 2, "barcodes": 2}


def test_empty_ledger_still_writes_a_valid_file(tmp_path: Path) -> None:
    out = tmp_path / "supplier_lead_times.json"
    exit_code = main(["--receipts", str(tmp_path / "absent.csv"), "--output", str(out)])
    assert exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["leadTimes"] == {}
    assert payload["supplierByBarcode"] == {}
    assert payload["totals"]["receipts"] == 0


def test_main_writes_the_export_to_disk(tmp_path: Path) -> None:
    ledger = tmp_path / "receipts.csv"
    _seed(ledger)
    out = tmp_path / "nested" / "supplier_lead_times.json"

    assert main(["--receipts", str(ledger), "--output", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["leadTimes"]["Tempo"]["confidence"] == "medium"
