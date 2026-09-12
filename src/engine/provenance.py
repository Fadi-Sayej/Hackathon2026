# src/engine/provenance.py
"""SPEC-007 — the vintages every figure is stated with."""
from __future__ import annotations

from datetime import datetime, timezone

from src.engine.model import Figure


def vintage_figures(inputs) -> list:
    v = inputs.vintages
    age = None
    snap = v["competitor"].get("snapshot_date")
    if snap:
        try:
            seen = datetime.fromisoformat(snap).replace(tzinfo=timezone.utc)
            age = (inputs.run_at - seen).days
        except ValueError:
            age = None
    return [
        Figure("pos_as_of", None, "date", ["pos"], {"value": v["pos"].get("as_of")}),
        Figure("sales_months", len(v["sales"].get("months") or []), "months", ["sales"],
               {"first": v["sales"].get("first"), "last": v["sales"].get("last"),
                "full_annual_cycle": v["sales"].get("full_annual_cycle")}),
        Figure("competitor_snapshot_age_days", age, "days", ["competitor"], {"snapshot_date": snap}),
        Figure("owner_state_available", 1 if v["owner_state"]["status"] == "available" else 0, "boolean",
               ["owner_state"], {"pulled_at": v["owner_state"]["pulled_at"]}),
    ]
