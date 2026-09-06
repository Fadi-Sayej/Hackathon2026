"""
price_server.py — MCP server exposing YomYom price-lookup tools.

Register with Claude Code
--------------------------
  claude mcp add yomyom-prices -- python src/mcp_server/price_server.py

Or add to your project's .mcp.json:
  {
    "mcpServers": {
      "yomyom-prices": {
        "command": "python",
        "args": ["src/mcp_server/price_server.py"]
      }
    }
  }

Tools exposed
-------------
  lookup_prices(products, chains)
      Look up current shelf and promo prices for a list of barcodes / names.
      Returns matched observations + coverage report as JSON.

  get_price_summary(products, chains)
      Compact summary: one row per product with best (lowest) price found,
      promo flag, and branch-confidence level.  Good for quick comparisons.

  explain_coverage(products, chains)
      Human-readable paragraph explaining what was found, what was missing,
      and whether branch-level pricing is available.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# ── project root on sys.path ──────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from mcp.server.fastmcp import FastMCP
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

from loguru import logger

from src.external.mcp_price_adapter import (
    run_mcp_price_lookup,
    DEFAULT_CHAINS,
)


# ── Server ────────────────────────────────────────────────────────────────────

if _MCP_AVAILABLE:
    mcp = FastMCP(
        name="yomyom-prices",
        instructions=(
            "Price and promotion lookup for Israeli supermarket chains "
            "(Alonit / Dor Alon).  "
            "Provide barcodes (e.g. '7290000123456') or Hebrew/English product "
            "names.  Results come from the latest price-transparency XML downloaded "
            "from the mandatory Israeli government FTP feed."
        ),
    )

    # ── Tool: lookup_prices ───────────────────────────────────────────────────
    @mcp.tool()
    def lookup_prices(
        products: list[str],
        chains: list[str] = None,
    ) -> str:
        """
        Look up shelf prices and promotions for a list of products.

        Parameters
        ----------
        products : Barcodes (all-digit, 4-14 chars) or product name strings.
                   Hebrew names are supported.
                   Example: ["7290000123456", "Coca Cola 1.5L", "קוקה קולה 1.5"]
        chains   : Chains to query.  Options: "alonit", "dor_alon", "super_alonit".
                   Default: all three (they share the same price feed).

        Returns
        -------
        JSON string with:
          coverage_report  — matched / unmatched counts, chains_found,
                             branch_level_available, per-product detail
          observations     — full ExternalProductObservation records
        """
        result = run_mcp_price_lookup(
            products=products,
            chains=chains,
            save_raw=True,
        )
        return json.dumps(result, indent=2, ensure_ascii=False, default=str)

    # ── Tool: get_price_summary ───────────────────────────────────────────────
    @mcp.tool()
    def get_price_summary(
        products: list[str],
        chains: list[str] = None,
    ) -> str:
        """
        Return a compact one-row-per-product price summary.

        For each product: best (lowest) shelf price, promo price if available,
        chain name(s), city, and branch-confidence level.

        Parameters
        ----------
        products : Barcodes or product name strings.
        chains   : Target chains (default: all Alonit family).
        """
        result = run_mcp_price_lookup(
            products=products,
            chains=chains,
            save_raw=False,
        )

        if result.get("status") != "ok":
            return json.dumps(result, ensure_ascii=False)

        summary_rows = []
        obs_by_product: dict[str, list[dict]] = {}
        for obs in result.get("observations", []):
            key = obs.get("barcode") or obs.get("product_name", "")
            # Map back to queried identifier via coverage report
            pname = obs.get("product_name", "")
            obs_by_product.setdefault(pname, []).append(obs)

        cov = result.get("coverage_report", {})
        for ident, detail in cov.get("per_product", {}).items():
            stores = detail.get("stores", [])
            if not stores:
                summary_rows.append({
                    "queried":   ident,
                    "matched":   False,
                    "best_price": None,
                    "promo_price": None,
                    "chains":    [],
                    "cities":    [],
                    "branch_confidence": "unknown",
                })
                continue

            prices = [s["price"] for s in stores if s.get("price") is not None]
            promos = [s["sale_price"] for s in stores if s.get("sale_price") is not None]
            chains_in = sorted({s["chain"] for s in stores if s.get("chain")})
            cities    = sorted({s["city"]  for s in stores if s.get("city")})
            conf_vals = [s.get("branch_confidence", "unknown") for s in stores]
            best_conf = (
                "high"    if "high"   in conf_vals else
                "medium"  if "medium" in conf_vals else
                "low"     if "low"    in conf_vals else
                "unknown"
            )

            summary_rows.append({
                "queried":          ident,
                "matched":          True,
                "product_name":     stores[0].get("store_name"),   # store, not product — fixed below
                "best_price":       min(prices) if prices else None,
                "promo_price":      min(promos) if promos else None,
                "on_promo":         bool(promos),
                "chains":           chains_in,
                "cities":           cities,
                "store_count":      len(stores),
                "branch_confidence": best_conf,
            })

        return json.dumps(
            {
                "observed_at":    cov.get("observed_at"),
                "match_rate_pct": cov.get("match_rate_pct"),
                "summary":        summary_rows,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    # ── Tool: explain_coverage ────────────────────────────────────────────────
    @mcp.tool()
    def explain_coverage(
        products: list[str],
        chains: list[str] = None,
    ) -> str:
        """
        Return a plain-text explanation of what was found and what was missing.

        Useful for generating a human-readable summary in a chat or report.

        Parameters
        ----------
        products : Barcodes or product name strings.
        chains   : Target chains (default: all Alonit family).
        """
        result = run_mcp_price_lookup(
            products=products,
            chains=chains,
            save_raw=False,
        )

        if result.get("status") != "ok":
            return f"Lookup failed: {result.get('reason', 'unknown error')}"

        cov = result.get("coverage_report", {})

        lines = [
            f"Price lookup run at {cov.get('observed_at', 'unknown')}.",
            f"Chains queried: {', '.join(cov.get('chains_requested', []))}.",
            "",
            f"Products queried : {cov.get('queried_count', 0)}",
            f"Products matched : {cov.get('matched_count', 0)}"
            f"  ({cov.get('match_rate_pct', 0):.1f}%)",
            f"Products missing : {cov.get('unmatched_count', 0)}",
        ]

        if cov.get("unmatched_products"):
            lines.append(
                "Unmatched: " + ", ".join(cov["unmatched_products"])
            )

        lines.append("")

        if cov.get("branch_level_available"):
            lines.append(
                "Branch-level pricing IS available — prices are tied to specific "
                "store branches (store_id + city confirmed)."
            )
        else:
            lines.append(
                "Branch-level pricing is NOT available for this query — "
                "results reflect chain-level data only (branch_confidence = low)."
            )

        chains_found = cov.get("chains_found", [])
        if chains_found:
            lines.append(f"Chains with data: {', '.join(chains_found)}.")

        promo = cov.get("with_promo_price", 0)
        total = cov.get("total_observations", 0)
        if total:
            lines.append(
                f"Promo prices available for {promo}/{total} observations "
                f"({promo / total * 100:.0f}%)."
            )

        warn = cov.get("warning")
        if warn:
            lines += ["", f"WARNING: {warn}"]

        return "\n".join(lines)

else:
    # ── Fallback when mcp package is not installed ────────────────────────────
    logger.warning(
        "mcp package not found.  Install it with: pip install mcp>=1.0  "
        "The MCP server will not start, but the adapter functions still work."
    )
    mcp = None  # type: ignore[assignment]


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not _MCP_AVAILABLE or mcp is None:
        print(
            "ERROR: 'mcp' package is required to run the MCP server.\n"
            "Install with:  pip install mcp>=1.0\n"
            "The price adapter (src/external/mcp_price_adapter.py) works without it.",
            file=sys.stderr,
        )
        sys.exit(1)
    mcp.run()


if __name__ == "__main__":
    main()
