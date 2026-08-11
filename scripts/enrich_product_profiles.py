"""
enrich_product_profiles.py — classify 7,674 Hebrew product names (issue #51).

WHAT THIS IS
    A batch classification job, run once, cached to a file in the repo, reviewed by a
    human, committed. It is NOT a runtime decision and never runs during a request.

WHY AN LLM EARNS ITS PLACE HERE
    configs/market_params.yaml is meaningless unless the system knows, per product:
    is this a cold drink? is it chametz? is it a Ramadan iftar staple? Nobody is
    going to hand-label 7,674 Hebrew names.

THE REFRAMING THAT MAKES IT RELIABLE
    The model picks ONE archetype from a closed list. It never invents numbers.
    Classification is what LLMs do well; producing 109 calibrated floats per product
    is what they do badly. The numeric vectors live in configs/archetypes.yaml,
    written and tuned by humans.

NON-NEGOTIABLE — THE CHAMETZ FLAG
    is_chametz never ships on model confidence alone. One error means a forbidden
    sale in our client's store. Every profile starts with `reviewed_by: null`, and
    the engine refuses to fire a gate on an unreviewed profile. The model proposes;
    a human approves.

Usage
-----
    python3 scripts/enrich_product_profiles.py --limit 50 --dry-run   # validate first
    python3 scripts/enrich_product_profiles.py --limit 200            # a real slice
    python3 scripts/enrich_product_profiles.py                        # the full run
    python3 scripts/enrich_product_profiles.py --review-sheet         # export for review

Costs a few dollars once. Already-classified products are skipped, so re-running is
free and a crash at product 6,000 does not restart from zero.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import polars as pl
import yaml

from src.common.paths import PROJECT_ROOT, SNAPSHOTS_ROOT

ARCHETYPES_CONFIG = PROJECT_ROOT / "configs" / "archetypes.yaml"
PROFILES_PATH = PROJECT_ROOT / "data" / "profiles" / "product_profiles.jsonl"
REVIEW_SHEET = PROJECT_ROOT / "reports" / "chametz_review.csv"

MODEL = os.environ.get("GEMINI_MODEL") or os.environ.get("VITE_GEMINI_MODEL") or "gemini-2.5-flash"
BATCH_SIZE = 50          # smaller wastes tokens re-sending instructions; larger loses accuracy
MAX_RETRIES = 4


# ── key handling ─────────────────────────────────────────────────────────────
def read_api_key() -> str | None:
    """Prefer the un-prefixed name. A VITE_ prefix is inlined by Vite into the
    browser bundle, so a key stored under that name ships to every visitor."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("VITE_GEMINI_API_KEY")
    if key:
        return key
    env = PROJECT_ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip()
    return None


# ── inputs ───────────────────────────────────────────────────────────────────
def load_archetypes() -> dict[str, str]:
    cfg = yaml.safe_load(ARCHETYPES_CONFIG.read_text(encoding="utf-8"))
    return {name: (spec or {}).get("label_ar", name) for name, spec in cfg["archetypes"].items()}


def load_products() -> pl.DataFrame:
    snaps = sorted(p for p in SNAPSHOTS_ROOT.glob("*") if (p / "products.parquet").exists())
    if not snaps:
        raise SystemExit("No internal snapshot with products.parquet found.")
    df = pl.read_parquet(snaps[-1] / "products.parquet")
    cols = [c for c in ("barcode", "product_name", "category", "brand", "selling_price") if c in df.columns]
    return df.select(cols).filter(pl.col("product_name").is_not_null())


def load_existing() -> dict[str, dict]:
    if not PROFILES_PATH.exists():
        return {}
    out = {}
    for line in PROFILES_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["barcode"]] = row
    return out


# ── prompt ───────────────────────────────────────────────────────────────────
def build_prompt(batch: list[dict], archetypes: dict[str, str]) -> str:
    listing = "\n".join(f"  - {name}: {label}" for name, label in archetypes.items())
    items = "\n".join(
        f'{i}. barcode={p["barcode"]} | name_he="{p["product_name"]}"'
        f' | dept="{p.get("category") or ""}" | price={p.get("selling_price") or "?"}'
        for i, p in enumerate(batch, 1)
    )
    return f"""You classify convenience-store products for an Israeli forecourt shop.
Product names are in Hebrew.

For each product choose EXACTLY ONE archetype from this closed list:
{listing}

Rules:
- Use only archetype names from the list above. Never invent one.
- If you are not confident, use "unclassified". An honest abstention is cheap to
  review; a confident error is not.
- is_chametz means the product contains leavened grain (wheat, barley, rye, oats,
  spelt) and may not be sold during Pesach. Bread, pasta, beer, most snacks, cakes,
  crackers, breaded items, soy sauce, malt drinks. When in doubt set it null, not false.
- is_kitniyot: legumes, rice, corn, sesame. Chametz for Ashkenazi Jews only.
- pack_class: "single" (one serving), "multipack", or "bulk".
- confidence: 0.0-1.0, your own honesty about the classification.
- For any product where is_chametz is true or null, give a one-line chametz_reason
  in English naming the ingredient you based it on.

Return ONLY a JSON array, one object per product, no prose and no code fences:
[{{"barcode":"...","archetype":"...","is_chametz":true,"is_kitniyot":false,
   "pack_class":"single","confidence":0.9,"chametz_reason":"wheat flour snack"}}]

Products:
{items}
"""


def strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def call_model(prompt: str, api_key: str) -> list[dict]:
    import urllib.error
    import urllib.request

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }).encode("utf-8")

    last = None
    for attempt in range(MAX_RETRIES):
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read())
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(strip_fence(text))
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code in (429, 500, 502, 503, 504):
                wait = 2 ** attempt
                print(f"    {last} — retrying in {wait}s")
                time.sleep(wait)
                continue
            # 400/403 are configuration errors; retrying cannot help.
            raise SystemExit(f"  {last}: {exc.read().decode('utf-8', 'replace')[:300]}")
        except Exception as exc:                        # noqa: BLE001
            last = str(exc)
            time.sleep(2 ** attempt)
    raise SystemExit(f"  giving up after {MAX_RETRIES} attempts: {last}")


# ── main ─────────────────────────────────────────────────────────────────────
def write_review_sheet(profiles: dict[str, dict]) -> int:
    """Everything a human must approve before any gate may fire."""
    rows = [p for p in profiles.values()
            if p.get("flags", {}).get("is_chametz") is not False and not p.get("reviewed_by")]
    if not rows:
        return 0
    df = pl.DataFrame([{
        "barcode": r["barcode"],
        "name_he": r.get("name_he"),
        "archetype": r.get("archetype"),
        "is_chametz": str(r.get("flags", {}).get("is_chametz")),
        "confidence": r.get("confidence"),
        "chametz_reason": r.get("chametz_reason"),
        "approve_yes_no": "",
    } for r in rows])
    REVIEW_SHEET.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(REVIEW_SHEET)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="classify at most N new products")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--dry-run", action="store_true", help="build prompts, call nothing")
    parser.add_argument("--review-sheet", action="store_true", help="only regenerate the review CSV")
    args = parser.parse_args()

    archetypes = load_archetypes()
    existing = load_existing()

    if args.review_sheet:
        n = write_review_sheet(existing)
        print(f"review sheet: {n:,} rows -> {REVIEW_SHEET.relative_to(PROJECT_ROOT)}")
        return 0

    products = load_products()
    todo = [p for p in products.iter_rows(named=True) if p["barcode"] not in existing]
    if args.limit:
        todo = todo[: args.limit]

    print("=== product profile enrichment ===")
    print(f"  archetypes          {len(archetypes):>7,}")
    print(f"  products total      {len(products):>7,}")
    print(f"  already classified  {len(existing):>7,}")
    print(f"  to classify         {len(todo):>7,}")
    if not todo:
        print("\n  nothing to do.")
        return 0

    batches = [todo[i:i + args.batch_size] for i in range(0, len(todo), args.batch_size)]
    print(f"  batches             {len(batches):>7,}  (model: {MODEL})")

    if args.dry_run:
        print("\n--- prompt preview (batch 1) ---")
        print(build_prompt(batches[0][:3], archetypes)[:1200])
        print("\n  dry run — nothing sent, nothing written.")
        return 0

    api_key = read_api_key()
    if not api_key:
        raise SystemExit(
            "\n  GEMINI_API_KEY not found in the environment or .env.\n"
            "  Put it in .env WITHOUT a VITE_ prefix — Vite inlines VITE_* variables\n"
            "  into the browser bundle, which would publish the key to every visitor."
        )

    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    written = failed = 0

    with PROFILES_PATH.open("a", encoding="utf-8") as fh:
        for n, batch in enumerate(batches, 1):
            print(f"  batch {n}/{len(batches)} ({len(batch)} products)…", flush=True)
            try:
                results = call_model(build_prompt(batch, archetypes), api_key)
            except SystemExit:
                raise
            except Exception as exc:                    # noqa: BLE001
                print(f"    batch failed, skipping: {exc}")
                failed += len(batch)
                continue

            by_barcode = {str(r.get("barcode")): r for r in results if isinstance(r, dict)}
            for product in batch:
                r = by_barcode.get(str(product["barcode"]))
                if not r:
                    failed += 1
                    continue

                archetype = r.get("archetype")
                # Reject out-of-vocabulary loudly rather than silently accepting it.
                if archetype not in archetypes:
                    print(f"    ! unknown archetype '{archetype}' -> unclassified")
                    archetype = "unclassified"

                profile = {
                    "barcode": product["barcode"],
                    "name_he": product["product_name"],
                    "department_he": product.get("category"),
                    "archetype": archetype,
                    "flags": {
                        "is_chametz": r.get("is_chametz"),
                        "is_kitniyot": r.get("is_kitniyot"),
                        "pack_class": r.get("pack_class"),
                    },
                    "chametz_reason": r.get("chametz_reason"),
                    "confidence": r.get("confidence"),
                    "source": f"llm:{MODEL}",
                    "prompt_hash": hashlib.sha256(
                        json.dumps(sorted(archetypes), ensure_ascii=False).encode()
                    ).hexdigest()[:12],
                    # Gates refuse to fire while this is null. Set only by a human.
                    "reviewed_by": None,
                    "reviewed_at": None,
                }
                fh.write(json.dumps(profile, ensure_ascii=False) + "\n")
                written += 1
            fh.flush()

    print(f"\n  written {written:,} profiles, {failed:,} failed")
    print(f"  -> {PROFILES_PATH.relative_to(PROJECT_ROOT)}")

    n = write_review_sheet(load_existing())
    print(f"\n  HUMAN REVIEW REQUIRED: {n:,} products flagged chametz or uncertain")
    print(f"  -> {REVIEW_SHEET.relative_to(PROJECT_ROOT)}")
    print("  No Pesach gate fires until these carry reviewed_by.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
