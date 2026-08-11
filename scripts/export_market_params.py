"""
export_market_params.py — generate the JS the frontend imports from the YAML configs.

configs/*.yaml is the source of truth; Vite cannot import YAML, so this mirrors it
into src/data/. Same pattern the repo already uses for marketData.js and
storeTypes.js: edit the YAML, re-run this, never hand-edit the generated file.

Only the fields the engine actually reads are carried across. The YAML keeps its
comments and provenance notes; the bundle stays small.

Usage
-----
    python3 scripts/export_market_params.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml

from src.common.paths import PROJECT_ROOT

PARAMS_YAML = PROJECT_ROOT / "configs" / "market_params.yaml"
ARCHETYPES_YAML = PROJECT_ROOT / "configs" / "archetypes.yaml"
OUTPUT = PROJECT_ROOT / "src" / "data" / "marketParams.js"

HEADER = """// GENERATED — do not edit by hand.
// Source: configs/market_params.yaml + configs/archetypes.yaml
// Regenerate: python3 scripts/export_market_params.py
// Generated: %s
"""


def camel(key: str) -> str:
    head, *rest = key.split("_")
    return head + "".join(part.title() for part in rest)


def build_registry(raw: dict) -> dict:
    families = {}
    for name, family in (raw.get("families") or {}).items():
        params = []
        for param in family.get("params") or []:
            params.append({
                "id": param["id"],
                "type": param["type"],
                "active": bool(param.get("active", False)),
            })
        families[name] = {"weight": family.get("weight", 1.0), "params": params}

    gates = {}
    for name, gate in (raw.get("gates") or {}).items():
        gates[name] = {
            "requiresFlag": gate.get("requires_flag"),
            "requiresHumanReview": bool(gate.get("requires_human_review", False)),
        }

    return {"clamp": raw.get("clamp", [0.2, 3.0]), "families": families, "gates": gates}


def build_archetypes(raw: dict) -> dict:
    out = {}
    for name, spec in (raw.get("archetypes") or {}).items():
        spec = spec or {}
        out[name] = {
            "labelAr": spec.get("label_ar", name),
            "flags": {camel(k): v for k, v in (spec.get("flags") or {}).items()},
            "sensitivities": spec.get("sensitivities") or {},
            "confidence": spec.get("confidence", raw.get("defaults", {}).get("confidence", "assumed")),
        }
    return out


def main() -> int:
    params_raw = yaml.safe_load(PARAMS_YAML.read_text(encoding="utf-8"))
    arch_raw = yaml.safe_load(ARCHETYPES_YAML.read_text(encoding="utf-8"))

    registry = build_registry(params_raw)
    archetypes = build_archetypes(arch_raw)

    total = sum(len(f["params"]) for f in registry["families"].values())
    active = sum(1 for f in registry["families"].values() for p in f["params"] if p["active"])

    body = HEADER % datetime.now(timezone.utc).isoformat(timespec="seconds")
    body += f"\n// {total} parameters across {len(registry['families'])} families, {active} active.\n"
    body += "// Inactive parameters sit at neutral 1.0 and change nothing.\n\n"
    body += "export const MARKET_PARAM_REGISTRY = "
    body += json.dumps(registry, ensure_ascii=False, indent=2)
    body += "\n\nexport const PRODUCT_ARCHETYPES = "
    body += json.dumps(archetypes, ensure_ascii=False, indent=2)
    body += "\n\nexport const MARKET_PARAM_STATS = "
    body += json.dumps({"total": total, "active": active,
                        "families": len(registry["families"]),
                        "archetypes": len(archetypes)}, indent=2)
    body += "\n"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(body, encoding="utf-8")

    print("=== market params exported ===")
    print(f"  parameters   {total:>5}  ({active} active)")
    print(f"  families     {len(registry['families']):>5}")
    print(f"  archetypes   {len(archetypes):>5}")
    print(f"  gates        {len(registry['gates']):>5}  {', '.join(registry['gates'])}")
    print(f"\n  written → {OUTPUT.relative_to(PROJECT_ROOT)} ({OUTPUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
