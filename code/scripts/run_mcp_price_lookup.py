"""
run_mcp_price_lookup.py — CLI for batch MCP price lookups.

Queries price data for a list of YomYom barcodes / product names against
the available chain price data (currently Alonit / Dor Alon) without
starting the MCP server process.  Results are written as JSON and printed
as a summary table.

Usage
-----
  # Look up a few products inline
  python scripts/run_mcp_price_lookup.py --products "7290000123456" "Coca Cola 1.5L"

  # Read product identifiers from a file (one per line, # = comment)
  python scripts/run_mcp_price_lookup.py --input products.txt

  # Target specific chains
  python scripts/run_mcp_price_lookup.py --products "7290000123456" \\
      --chains alonit super_alonit

  # Skip saving raw output
  python scripts/run_mcp_price_lookup.py --products "RedBull 250ml" --no-save-raw

  # Write full results JSON to a file
  python scripts/run_mcp_price_lookup.py --products "7290000123456" \\
      --output results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── project root on sys.path ──────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from loguru import logger

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=True,
)

from src.common.paths import LOGS_ROOT
LOGS_ROOT.mkdir(parents=True, exist_ok=True)
logger.add(
    LOGS_ROOT / "mcp_price_lookup_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
)

from src.external.mcp_price_adapter import run_mcp_price_lookup, DEFAULT_CHAINS


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run_mcp_price_lookup",
        description="Batch price lookup via the MCP adapter (no MCP server needed).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--products", "-p",
        nargs="+",
        metavar="BARCODE_OR_NAME",
        help="One or more barcodes or product names (space-separated).",
    )
    src.add_argument(
        "--input", "-i",
        type=Path,
        metavar="FILE",
        help="Text file with one barcode or product name per line (# = comment).",
    )
    p.add_argument(
        "--chains", "-c",
        nargs="+",
        default=DEFAULT_CHAINS,
        metavar="CHAIN",
        help=f"Target chains. Default: {' '.join(DEFAULT_CHAINS)}",
    )
    p.add_argument(
        "--no-save-raw",
        action="store_true",
        default=False,
        help="Skip writing raw matched rows to disk.",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.72,
        metavar="0-1",
        help="Fuzzy name-match threshold (default: 0.72).",
    )
    p.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        metavar="JSON_FILE",
        help="Write full results JSON to this file (optional).",
    )
    p.add_argument(
        "--collected-at",
        type=str,
        default=None,
        metavar="ISO8601",
        help="Override lookup timestamp (ISO-8601, default: UTC now).",
    )
    return p.parse_args()


def _load_products_from_file(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        ln.strip()
        for ln in lines
        if ln.strip() and not ln.strip().startswith("#")
    ]


def _print_summary(result: dict) -> None:
    """Print a human-readable summary table to stdout."""
    cov = result.get("coverage_report", {})
    print()
    print("=" * 60)
    print("  YomYom MCP Price Lookup — Coverage Summary")
    print("=" * 60)
    print(f"  Timestamp  : {cov.get('observed_at', '—')}")
    print(f"  Chains     : {', '.join(cov.get('chains_requested', []))}")
    print(f"  Queried    : {cov.get('queried_count', 0)}")
    print(f"  Matched    : {cov.get('matched_count', 0)}  ({cov.get('match_rate_pct', 0):.1f}%)")
    print(f"  Unmatched  : {cov.get('unmatched_count', 0)}")
    print(f"  Chains found         : {', '.join(cov.get('chains_found', [])) or '—'}")
    print(f"  Branch-level pricing : {'YES' if cov.get('branch_level_available') else 'NO'}")
    print(f"  With promo price     : {cov.get('with_promo_price', 0)}/{cov.get('total_observations', 0)}")
    if cov.get("warning"):
        print(f"\n  !! {cov['warning']}")
    print()

    per_product = cov.get("per_product", {})
    if per_product:
        print(f"  {'Product':<40} {'Hits':>4}  {'Best ILS':>8}  {'Promo':>6}  Conf")
        print("  " + "-" * 72)
        for ident, detail in per_product.items():
            stores  = detail.get("stores", [])
            n_hits  = detail.get("hit_count", 0)
            prices  = [s["price"] for s in stores if s.get("price") is not None]
            promos  = [s["sale_price"] for s in stores if s.get("sale_price") is not None]
            best_p  = f"{min(prices):.2f}" if prices else "—"
            promo_p = f"{min(promos):.2f}" if promos else "—"
            confs   = [s.get("branch_confidence", "?") for s in stores]
            best_c  = (
                "high"   if "high"   in confs else
                "medium" if "medium" in confs else
                "low"    if "low"    in confs else
                "?"
            )
            label = ident[:40]
            print(f"  {label:<40} {n_hits:>4}  {best_p:>8}  {promo_p:>6}  {best_c}")
    print()
    raw_path = result.get("raw_output_path")
    if raw_path:
        print(f"  Raw output: {raw_path}")
    print("=" * 60)
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    # Collect product list
    if args.products:
        products = args.products
    else:
        if not args.input.exists():
            logger.error("Input file not found: {}", args.input)
            sys.exit(1)
        products = _load_products_from_file(args.input)
        if not products:
            logger.error("Input file is empty or has only comments: {}", args.input)
            sys.exit(1)

    # Parse optional timestamp
    observed_at: datetime | None = None
    if args.collected_at:
        try:
            observed_at = datetime.fromisoformat(args.collected_at)
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.error("Invalid --collected-at: {!r}", args.collected_at)
            sys.exit(1)

    # Run lookup
    result = run_mcp_price_lookup(
        products=products,
        chains=args.chains,
        save_raw=not args.no_save_raw,
        name_threshold=args.threshold,
        observed_at=observed_at,
    )

    if result.get("status") != "ok":
        logger.error("Lookup failed: {}", result.get("reason"))
        sys.exit(2)

    # Print summary
    _print_summary(result)

    # Write full JSON output if requested
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        logger.info("Full results written to {}", args.output)

    sys.exit(0)


if __name__ == "__main__":
    main()
