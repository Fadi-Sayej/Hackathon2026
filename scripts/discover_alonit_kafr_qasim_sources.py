from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ALONIT_ROOT = REPO_ROOT / "data" / "external" / "raw" / "alonit"
DEBUG_NETWORK_ROOT = REPO_ROOT / "data" / "debug" / "network"
ALONIT_REPORTS_ROOT = REPO_ROOT / "reports" / "discovery" / "alonit"
OUTPUT_ROOT = REPO_ROOT / "reports" / "discovery" / "alonit_kafr_qasim"
SOURCES_CONFIG = REPO_ROOT / "configs" / "sources.yaml"

TARGET_TERMS = [
    "\u05db\u05e4\u05e8 \u05e7\u05d0\u05e1\u05dd",
    "\u05e7\u05d0\u05e1\u05dd",
    "\u05d0\u05dc\u05de\u05d3\u05d9\u05e0\u05d4",
    "\u05d0\u05dc \u05de\u05d3\u05d9\u05e0\u05d4",
    "kafr qasim",
    "kfar qasem",
    "al-madina",
]

TARGET_LABELS = [
    "Alonit Kafr Qasim",
    "\u05db\u05e4\u05e8 \u05e7\u05d0\u05e1\u05dd",
    "\u05db\u05e4\u05e8 \u05e7\u05d0\u05e1\u05dd \u05d0\u05dc\u05de\u05d3\u05d9\u05e0\u05d4",
    "\u05e8\u05d7' \u05d0\u05dc\u05de\u05d3\u05d9\u05e0\u05d4 2",
    "Al-Madina 2",
    "Kafr Qasim",
    "Kfar Qasem",
]


def utc_timestamp() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%dT%H%M%SZ"), now.isoformat().replace("+00:00", "Z")


def normalize_text(value: str | None) -> str:
    text = (value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def row_value(row: dict[str, str], *keys: str) -> str:
    lowered = {key.lower(): value for key, value in row.items()}
    for key in keys:
        if key in row:
            return row[key]
        value = lowered.get(key.lower())
        if value is not None:
            return value
    return ""


def iter_raw_store_files() -> list[Path]:
    candidates: list[Path] = []
    if not RAW_ALONIT_ROOT.exists():
        return candidates
    for path in RAW_ALONIT_ROOT.rglob("*.xml"):
        if path.name.startswith("alonit_"):
            candidates.append(path)
    return sorted(candidates)


def looks_like_stores_xml(path: Path) -> bool:
    try:
        head_bytes = path.read_bytes()[:4000]
    except OSError:
        return False
    for encoding in ("utf-8", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            head = head_bytes.decode(encoding, errors="ignore")
        except LookupError:
            continue
        if "StoreId" in head or "StoreID" in head or "<Store>" in head:
            return True
    return False


def parse_store_rows(xml_path: Path) -> list[dict[str, str]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    rows: list[dict[str, str]] = []
    for store_elem in root.iter():
        if local_name(store_elem.tag).lower() != "store":
            continue
        row: dict[str, str] = {}
        for child in list(store_elem):
            row[local_name(child.tag)] = (child.text or "").strip()
        rows.append(row)
    return rows


def find_term_matches(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    normalized_terms = [normalize_text(term) for term in TARGET_TERMS]
    for row in rows:
        combined = " | ".join(
            [
                row_value(row, "StoreId", "StoreID"),
                row_value(row, "StoreName"),
                row_value(row, "Address"),
                row_value(row, "City"),
            ]
        )
        searchable = normalize_text(combined)
        row_matches = [term for term in normalized_terms if term in searchable]
        if row_matches:
            matches.append(
                {
                    "store_id": row_value(row, "StoreId", "StoreID"),
                    "store_name": row_value(row, "StoreName"),
                    "address": row_value(row, "Address"),
                    "city": row_value(row, "City"),
                    "matched_terms": row_matches,
                }
            )
    return matches


def coordinate_summary(rows: list[dict[str, str]]) -> dict[str, object]:
    coord_keys = set()
    rows_with_coords = 0
    sample_rows: list[dict[str, str]] = []
    for row in rows:
        keys = {key for key in row if "lat" in key.lower() or "lon" in key.lower()}
        if not keys:
            continue
        coord_keys.update(keys)
        has_non_empty = any((row.get(key) or "").strip() for key in keys)
        if has_non_empty:
            rows_with_coords += 1
            if len(sample_rows) < 3:
                sample_rows.append(
                    {
                        "store_id": row_value(row, "StoreId", "StoreID"),
                        "store_name": row_value(row, "StoreName"),
                        "coord_values": {key: row.get(key, "") for key in sorted(keys)},
                    }
                )
    if not coord_keys:
        return {
            "has_coordinates": False,
            "detail": "No latitude/longitude fields found in the parsed Dor Alon Stores XML evidence.",
            "rows_with_coordinates": 0,
            "sample_rows": [],
        }
    return {
        "has_coordinates": rows_with_coords > 0,
        "detail": (
            "Coordinate-like fields were present but did not yield a Kafr Qasim proximity check."
            if rows_with_coords
            else "Coordinate-like fields were present but empty in parsed samples."
        ),
        "coordinate_keys": sorted(coord_keys),
        "rows_with_coordinates": rows_with_coords,
        "sample_rows": sample_rows,
    }


def load_registry_status() -> dict[str, object]:
    if not SOURCES_CONFIG.exists():
        return {
            "exists": False,
            "detail": "No configs/sources.yaml file exists in this repository.",
            "candidate_entries": [],
        }
    text = SOURCES_CONFIG.read_text(encoding="utf-8", errors="ignore")
    searchable = normalize_text(text)
    matches = []
    for label in TARGET_LABELS + TARGET_TERMS:
        if normalize_text(label) in searchable:
            matches.append(label)
    return {
        "exists": True,
        "detail": "configs/sources.yaml exists and was searched for Kafr Qasim labels.",
        "candidate_entries": sorted(set(matches)),
    }


def canonicalize_easy_ddata(url: str) -> str:
    match = re.search(r"bizid=(\d+)", url)
    if not match:
        return url
    return f"https://easy.co.il/n/jsons/ddata?bizid={match.group(1)}"


def summarize_network_csv(path: Path) -> dict[str, object]:
    rows = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle)
        rows.extend(reader)

    interesting = []
    seen = set()
    for row in rows:
        url = row.get("url", "")
        if "easy.co.il/n/jsons/ddata" not in url:
            continue
        canonical = canonicalize_easy_ddata(url)
        if canonical in seen:
            continue
        seen.add(canonical)
        interesting.append(
            {
                "url": canonical,
                "status": row.get("status", ""),
                "matched_keys": row.get("matched_keys", ""),
                "candidate_score": int((row.get("candidate_score") or "0").strip() or "0"),
            }
        )

    return {
        "summary_path": str(path),
        "total_rows": len(rows),
        "interesting_rows": interesting[:20],
        "product_like_rows": [],
    }


def load_network_evidence() -> dict[str, object]:
    evidence: dict[str, object] = {
        "configured_sources": [],
        "candidate_urls": [],
        "product_level_found": False,
    }
    for source_id in ["alonit_kafr_qasim", "alonit_kafr_qasim_easy_list"]:
        summary_path = DEBUG_NETWORK_ROOT / source_id / "summary.csv"
        if not summary_path.exists():
            continue
        source_summary = summarize_network_csv(summary_path)
        evidence["configured_sources"].append({"source_id": source_id, **source_summary})
        for row in source_summary["interesting_rows"]:
            url = row["url"]
            if url not in evidence["candidate_urls"]:
                evidence["candidate_urls"].append(url)
    return evidence


def find_latest_pipeline_report() -> dict[str, object] | None:
    report_paths = sorted(ALONIT_REPORTS_ROOT.glob("alonit_signal_pipeline_*.json"))
    if not report_paths:
        return None
    latest = report_paths[-1]
    data = json.loads(latest.read_text(encoding="utf-8"))
    return {
        "path": str(latest),
        "missing_target_labels": (
            data.get("phases", {})
            .get("phase_2_3_store_match_and_price_promo_parse", {})
            .get("data", {})
            .get("missing_target_labels", [])
        ),
        "network_command": (
            data.get("phases", {})
            .get("phase_4_targeted_network_discovery", {})
            .get("data", {})
            .get("command", [])
        ),
    }


def build_candidate_urls() -> list[str]:
    return [
        "https://easy.co.il/en/list/Alonit?region=1058",
        "https://easy.co.il/en/page/26305054",
        "https://www.doralon.co.il/station/",
    ]


def build_next_manual_checks() -> list[str]:
    return [
        "Open the Easy business page candidate at https://easy.co.il/en/page/26305054 and confirm whether it is the Kafr Qasim / Al-Madina 2 branch.",
        "If the Easy page is correct, inspect visible external website or order links before any further crawling.",
        "Check whether the branch is published under a different Dor Alon / Alonit / Super Alonit store name in any updated store registry export.",
        "If a direct order page is confirmed, run targeted discovery only for that URL with npm run discover:alonit-network.",
        "Manually test Wolt, TenBis, and Cibus search for the confirmed branch name and address; only build a connector if a direct venue URL exists.",
    ]


def build_report() -> dict[str, object]:
    raw_store_files = [path for path in iter_raw_store_files() if looks_like_stores_xml(path)]
    latest_stores = raw_store_files[-1] if raw_store_files else None
    store_rows = parse_store_rows(latest_stores) if latest_stores else []
    term_matches = find_term_matches(store_rows)
    coords = coordinate_summary(store_rows)
    registry = load_registry_status()
    network = load_network_evidence()
    pipeline = find_latest_pipeline_report()

    for url in build_candidate_urls():
        if url not in network["candidate_urls"]:
            network["candidate_urls"].append(url)

    return {
        "target": {
            "label": "Alonit Kafr Qasim / Al-Madina 2",
            "aliases": TARGET_LABELS,
        },
        "observed_at": None,
        "status": "No product-level source found yet.",
        "product_level_source_found": False,
        "confidence": "medium-high",
        "store_registry_only": True,
        "dor_alon_store_search": {
            "latest_stores_raw_path": str(latest_stores) if latest_stores else None,
            "stores_file_found": latest_stores is not None,
            "searched_terms": TARGET_TERMS,
            "total_store_rows": len(store_rows),
            "matching_rows": term_matches,
            "result": (
                "No Dor Alon Stores match found for Kafr Qasim aliases in the latest parsed raw Stores XML."
                if not term_matches
                else "Potential store-registry matches found; manual validation required."
            ),
        },
        "coordinate_check": coords,
        "source_registry": registry,
        "existing_pipeline_context": pipeline,
        "network_discovery": {
            "configured_sources": network["configured_sources"],
            "candidate_urls": network["candidate_urls"],
            "prepared_command_examples": [
                "npm run discover:alonit-network -- --max-linked 2 --wait-ms 1500 --url alonit_kafr_qasim_easy_list=https://easy.co.il/en/list/Alonit?region=1058",
                "npm run discover:alonit-network -- --max-linked 2 --wait-ms 1500 --url alonit_kafr_qasim_easy_page=https://easy.co.il/en/page/26305054",
            ],
            "result": "Existing Kafr Qasim network discovery evidence did not reveal a clear product catalog or price API.",
        },
        "candidate_next_steps": build_next_manual_checks(),
    }


def render_markdown(report: dict[str, object], json_path: Path) -> str:
    dor = report["dor_alon_store_search"]
    coords = report["coordinate_check"]
    registry = report["source_registry"]
    network = report["network_discovery"]
    lines = [
        "# Alonit Kafr Qasim Product Source Discovery",
        "",
        f"- Status: {report['status']}",
        f"- Confidence: {report['confidence']}",
        f"- Store-registry-only: {'yes' if report['store_registry_only'] else 'no'}",
        f"- JSON report: `{json_path}`",
        "",
        "## Scope",
        "",
        "This report checks whether Alonit Kafr Qasim / Al-Madina 2 has any product-level source for price files or catalog availability.",
        "",
        "## Dor Alon Stores Search",
        "",
        f"- Latest raw Stores file used: `{dor['latest_stores_raw_path']}`",
        f"- Total parsed store rows inspected: {dor['total_store_rows']}",
        f"- Searched aliases: {', '.join(dor['searched_terms'])}",
        f"- Result: {dor['result']}",
    ]
    if dor["matching_rows"]:
        lines.extend(["", "### Matching rows", ""])
        for match in dor["matching_rows"]:
            lines.append(
                f"- `{match['store_id']}` | {match['store_name']} | {match['address']} | {match['city']} | matched: {', '.join(match['matched_terms'])}"
            )
    else:
        lines.extend(["", "- No matching rows found for Kafr Qasim aliases.", ""])

    lines.extend(
        [
            "## Coordinate Check",
            "",
            f"- {coords['detail']}",
            f"- Rows with coordinates: {coords.get('rows_with_coordinates', 0)}",
            "",
            "## Source Registry",
            "",
            f"- {registry['detail']}",
            "",
            "## Network Discovery",
            "",
            f"- Result: {network['result']}",
            "- Candidate URLs:",
        ]
    )
    for url in network["candidate_urls"]:
        lines.append(f"  - {url}")

    lines.extend(["", "- Prepared commands:"])
    for command in network["prepared_command_examples"]:
        lines.append(f"  - `{command}`")

    lines.extend(["", "## Next Manual Checks", ""])
    for item in report["candidate_next_steps"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Final Status", "", "No product-level source found yet."])
    return "\n".join(lines) + "\n"


def main() -> int:
    stamp, iso_time = utc_timestamp()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    report = build_report()
    report["observed_at"] = iso_time

    json_path = OUTPUT_ROOT / f"product_source_discovery_{stamp}.json"
    md_path = OUTPUT_ROOT / f"product_source_discovery_{stamp}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report, json_path), encoding="utf-8")

    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    print(f"Status: {report['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
