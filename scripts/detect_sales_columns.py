"""
detect_sales_columns.py — can this export give us real sales? (task A-3)

Run this the moment YomYom sends a sales report, BEFORE importing anything. It
answers one question: does this file contain per-item sales, and does our schema
mapping already recognise the column names?

    python3 scripts/detect_sales_columns.py --input ~/Downloads/report.csv

Exit 0 = usable sales columns found (import will pick them up).
Exit 2 = sales-like columns found but NOT mapped — the fix is adding the header
         to configs/pos_schema_mapping.yaml, no code change. The exact YAML to
         paste is printed for you.
Exit 1 = no sales data in this file; ask for a different report.

Why this exists: A-3 says adopting a real sales export must be a config change,
not a rewrite. The importer already maps several sales headers; this tells you in
seconds whether the file YomYom actually sent is one of them, instead of importing
it and wondering why every velocity column is still null.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

CONFIG = ROOT / "configs" / "pos_schema_mapping.yaml"

# Canonical fields that make velocity real rather than inferred.
SALES_FIELDS = ("units_sold_7d", "units_sold_30d", "sales_amount_30d", "last_sale_date")

# Header fragments that look like sales in Hebrew, Arabic or English. Used only to
# say "this file HAS sales, you just need to map it" — never to guess a mapping.
SALES_HINTS = (
    "נמכר", "מכירות", "כמות נמכרת", "מכר",          # Hebrew: sold / sales
    "مبيعات", "الكمية المباعة", "مباع",              # Arabic: sales / quantity sold
    "sold", "sales", "qty_sold", "quantity_sold", "units", "movement", "turnover",
)

DATE_HINTS = ("תאריך", "تاریخ", "تاريخ", "date", "last_sale")


def _load_mapped_names():
    """canonical field -> every header the importer already accepts for it."""
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    mapped = {}
    for column in config.get("columns", []):
        canonical = column.get("canonical_name")
        if canonical not in SALES_FIELDS:
            continue
        names = {str(column.get("raw_name", "")).strip().lower()}
        names.update(str(n).strip().lower() for n in column.get("candidate_names", []) or [])
        mapped[canonical] = {n for n in names if n}
    return mapped


def _read_headers(path: Path):
    """Header row of a CSV/TSV. Excel is rejected with a clear instruction."""
    if path.suffix.lower() in {".xlsx", ".xls"}:
        raise SystemExit(
            "This is an Excel file. Save it as CSV (UTF-8) and re-run — the importer reads CSV."
        )
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(8192)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(handle, dialect)
        for row in reader:
            if any(cell.strip() for cell in row):
                return [cell.strip() for cell in row], dialect.delimiter
    return [], ","


def _looks_like_sales(header: str) -> bool:
    low = header.lower()
    return any(hint.lower() in low for hint in SALES_HINTS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.input.exists():
        print("File not found: %s" % args.input, file=sys.stderr)
        return 1

    headers, delimiter = _read_headers(args.input)
    if not headers:
        print("No header row found — is this really a CSV?", file=sys.stderr)
        return 1

    mapped = _load_mapped_names()
    lowered = {h.lower(): h for h in headers}

    recognised = {}
    for canonical, accepted in mapped.items():
        for low, original in lowered.items():
            if low in accepted:
                recognised[canonical] = original
                break

    unmapped = [
        h for h in headers
        if h.lower() not in {n for names in mapped.values() for n in names}
        and (_looks_like_sales(h) or any(d in h.lower() for d in DATE_HINTS))
    ]

    result = {
        "file": str(args.input),
        "delimiter": delimiter,
        "header_count": len(headers),
        "recognised_sales_columns": recognised,
        "unmapped_sales_like_columns": unmapped,
        "has_usable_sales": bool(recognised),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Sales-column check: %s" % args.input.name)
        print("  columns in file : %d (delimiter %r)" % (len(headers), delimiter))
        if recognised:
            print("  ✅ recognised — the importer will use these as REAL sales:")
            for canonical, original in sorted(recognised.items()):
                print("       %-18s <- %s" % (canonical, original))
        else:
            print("  ❌ no recognised sales columns")
        if unmapped:
            print("  ⚠️  sales-like columns this file has but we do NOT map:")
            for header in unmapped:
                print("       %s" % header)

    if recognised:
        print()
        print("Next: python3 scripts/pilot_daily.sh <file>  — velocity switches to")
        print("      measured sales automatically and the snapshot proxy stands down.")
        return 0

    if unmapped:
        print()
        print("This file HAS sales-looking columns, they are just not mapped yet.")
        print("No code change needed — add the header to configs/pos_schema_mapping.yaml")
        print("under the matching canonical field, e.g.:")
        print()
        print("  - raw_name:       units_sold_30d")
        print("    canonical_name: units_sold_30d")
        print("    candidate_names:")
        for header in unmapped[:4]:
            print("      - %s" % header)
        print()
        print("Then re-run this script to confirm, and import.")
        return 2

    print()
    print("No sales data here. This looks like another inventory snapshot.")
    print("Ask YomYom specifically for a report with quantity sold per item.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
