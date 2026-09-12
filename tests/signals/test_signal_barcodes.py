# tests/signals/test_signal_barcodes.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.signals.competitor_product_signals import _map_alonit_row, _map_wolt_row


def test_alonit_and_wolt_barcodes_are_zero_stripped():
    a = _map_alonit_row({"barcode": "0007290000041445", "product_name": "x", "price": "1", "store_id": "657",
                         "store_chain": "Alonit", "store_name": "s", "observed_at": "2026-09-08T00:00:00Z"}, "t")
    w = _map_wolt_row({"barcode": "7290000041445", "product_name": "x", "price": "1", "store_id": "abc",
                       "store_chain": "super alonit", "store_name": "s", "observed_at": "2026-09-08T00:00:00Z",
                       "is_online_available": True}, "t")
    assert a["barcode"] == w["barcode"] == "7290000041445"
