"""
alonit_signal_pipeline.py - discovery-first Alonit product signal pipeline.

This module orchestrates targeted evidence collection for:
  - Alonit Kafr Qasim / כפר קאסם / Al-Madina 2
  - Super Alonit Einat / עינת

The pipeline deliberately separates price-file price signals from delivery
catalog availability signals:
  - PriceFull / PromoFull files prove branch-level prices/promos, not stock.
  - Delivery catalog presence is a stronger online availability signal.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from loguru import logger

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.common.paths import PROJECT_ROOT
from src.external import alonit_connector
from src.external.alonit_connector import (
    discover_portal_price_files,
    run_alonit_portal_collection,
)
from src.external.delivery_venue_connector import run_delivery_venue_collection


DEFAULT_NETWORK_URLS = {
    "alonit_kafr_qasim_easy_list": "https://easy.co.il/en/list/Alonit?region=1058",
    "super_alonit_einat_easy": "https://easy.co.il/en/page/26797254",
    "super_alonit_einat_wolt": "https://wolt.com/en/isr/petah-tikva/venue/super-alonit-kibbutz-einat",
}

DEFAULT_DELIVERY_URLS = [
    "https://wolt.com/en/isr/petah-tikva/venue/super-alonit-kibbutz-einat",
]


@dataclass
class PhaseStatus:
    status: str
    detail: str
    data: dict


def _report_path(observed_at: datetime) -> Path:
    ts = observed_at.strftime("%Y%m%dT%H%M%S")
    return PROJECT_ROOT / "reports" / "discovery" / "alonit" / f"alonit_signal_pipeline_{ts}.json"


def _discover_price_files() -> PhaseStatus:
    try:
        discovery = discover_portal_price_files()
    except Exception as exc:
        return PhaseStatus(
            status="failed",
            detail=f"Dor Alon Cerberus portal discovery failed: {exc}",
            data={"portal_base_url": alonit_connector.PORTAL_BASE_URL},
        )

    found = bool(discovery["stores_files_count"] and discovery["pricefull_files_count"])
    status = "ok" if found else "missing"
    detail = "Dor Alon price-transparency files discovered."
    if not found:
        detail = "No usable Stores + PriceFull combination found on Dor Alon Cerberus portal."
    return PhaseStatus(
        status=status,
        detail=detail,
        data=discovery,
    )


def _run_price_collection(observed_at: datetime) -> PhaseStatus:
    result = run_alonit_portal_collection(save_raw=True, observed_at=observed_at)
    if result.get("status") != "ok":
        return PhaseStatus(
            status="failed",
            detail=f"Price-file collection failed: {result.get('reason')}",
            data=result,
        )

    total = result.get("total_observations", 0)
    stores = result.get("stores_found", [])
    return PhaseStatus(
        status="ok" if total else "empty",
        detail=(
            "PriceFull/PromoFull parsed into ExternalProductObservation records. "
            "These records are price/promo signals only, not real-stock availability."
            if total
            else "Price files were reachable, but no matching target-store observations were produced."
        ),
        data=result | {
            "target_store_count": len(stores),
            "availability_interpretation": "price_file_presence_is_not_real_stock",
        },
    )


def _run_network_discovery(
    *,
    max_linked_pages: int,
    wait_ms: int,
) -> PhaseStatus:
    args = [
        "node",
        "scripts/discover-alonit-network.mjs",
        "--max-linked",
        str(max_linked_pages),
        "--wait-ms",
        str(wait_ms),
    ]
    for source_id, url in DEFAULT_NETWORK_URLS.items():
        args.extend(["--url", f"{source_id}={url}"])

    completed = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=240,
    )
    data = {
        "command": args,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "output_root": str(PROJECT_ROOT / "data" / "debug" / "network"),
        "availability_interpretation": "candidate_catalog_apis_need_connector_validation",
    }
    return PhaseStatus(
        status="ok" if completed.returncode == 0 else "failed",
        detail=(
            "Targeted Playwright network discovery completed for relevant Alonit/Super Alonit/Easy/Wolt pages."
            if completed.returncode == 0
            else "Targeted Playwright network discovery failed."
        ),
        data=data,
    )


def _run_delivery_catalog(
    observed_at: datetime,
    delivery_urls: list[str],
    max_categories: Optional[int],
) -> PhaseStatus:
    if not delivery_urls:
        return PhaseStatus(
            status="skipped",
            detail="No delivery venue URLs were provided or discovered.",
            data={"delivery_urls": []},
        )

    result = run_delivery_venue_collection(
        delivery_urls,
        observed_at=observed_at,
        max_categories=max_categories,
    )
    result_data = asdict(result)
    result_data["store_infos"] = [
        {key: value for key, value in store.items() if key != "raw"}
        for store in result_data.get("store_infos", [])
    ]
    result_data["availability_interpretation"] = (
        "delivery_catalog_presence_is_stronger_online_availability_signal_when_is_online_available_true"
    )

    return PhaseStatus(
        status="ok" if result.total_observations else "empty",
        detail=(
            "Delivery venue catalog parsed into ExternalProductObservation records."
            if result.total_observations
            else "Delivery venue pages were checked but no catalog observations were produced."
        ),
        data=result_data,
    )


def run_alonit_signal_pipeline(
    *,
    observed_at: Optional[datetime] = None,
    need_availability: bool = True,
    run_network: bool = True,
    run_delivery: bool = True,
    delivery_urls: Optional[list[str]] = None,
    network_max_linked_pages: int = 2,
    network_wait_ms: int = 1500,
    delivery_max_categories: Optional[int] = None,
) -> dict:
    observed_at = observed_at or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)

    report: dict = {
        "pipeline": "alonit_product_signal_discovery",
        "observed_at": observed_at.isoformat(),
        "targets": [
            "Alonit Kafr Qasim / כפר קאסם / Al-Madina 2",
            "Super Alonit Einat / עינת",
        ],
        "rules": {
            "do_not_assume_accessibility_or_easy_pages_contain_products": True,
            "price_file_presence_is_not_real_stock": True,
            "delivery_catalog_presence_is_stronger_availability_signal": True,
            "do_not_invent_product_availability": True,
            "do_not_scrape_all_sites_blindly": True,
        },
        "phases": {},
        "summary": {},
    }

    phase1 = _discover_price_files()
    report["phases"]["phase_1_price_file_discovery"] = asdict(phase1)

    if phase1.status == "ok":
        phase23 = _run_price_collection(observed_at)
    else:
        phase23 = PhaseStatus(
            status="skipped",
            detail="Skipped store matching and price/promo parsing because price files were not discovered.",
            data={},
        )
    report["phases"]["phase_2_3_store_match_and_price_promo_parse"] = asdict(phase23)

    if run_network and (need_availability or phase1.status != "ok"):
        phase4 = _run_network_discovery(
            max_linked_pages=network_max_linked_pages,
            wait_ms=network_wait_ms,
        )
    else:
        phase4 = PhaseStatus(
            status="skipped",
            detail="Network discovery skipped by configuration.",
            data={},
        )
    report["phases"]["phase_4_targeted_network_discovery"] = asdict(phase4)

    if run_delivery and need_availability:
        phase5 = _run_delivery_catalog(
            observed_at,
            delivery_urls or DEFAULT_DELIVERY_URLS,
            delivery_max_categories,
        )
    else:
        phase5 = PhaseStatus(
            status="skipped",
            detail="Delivery venue catalog collection skipped by configuration.",
            data={},
        )
    report["phases"]["phase_5_delivery_venue_catalog"] = asdict(phase5)

    price_rows = phase23.data.get("total_observations", 0)
    delivery_rows = phase5.data.get("total_observations", 0)
    report["summary"] = {
        "price_file_source_worked": phase23.status == "ok" and price_rows > 0,
        "delivery_catalog_source_worked": phase5.status == "ok" and delivery_rows > 0,
        "price_observation_rows": price_rows,
        "delivery_observation_rows": delivery_rows,
        "availability_source": (
            "delivery_catalog"
            if delivery_rows
            else "none_verified"
        ),
        "price_source": "dor_alon_price_transparency" if price_rows else "none_verified",
        "notes": [
            "PriceFull/PromoFull rows are branch-level price/promo signals, not stock.",
            "Delivery catalog observations set online availability only from explicit catalog availability fields.",
            "Easy/accessibility pages are treated as discovery pages only, not product sources.",
        ],
    }

    path = _report_path(observed_at)
    report["report_path"] = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Alonit discovery-first report written: {}", path)
    return report
