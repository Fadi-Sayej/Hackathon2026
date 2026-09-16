"""Publish the product catalogue beside the artefact (`public/data/catalogue.json`).

WHY IT IS A SEPARATE FILE
    Five of the twelve restored pages — Prices, Products, Overview, AI report and
    Assortment gaps — need every product, not only the ones with a finding against them.
    `dashboard.json` publishes findings: seven capabilities of per-signal entries. It has
    never carried a catalogue, which is why those pages came back on an awaiting state.

    Folding the catalogue into the artefact was the obvious move and it is the wrong one.
    Measured on the pilot: 7,523 products is **1.73 MB** of compact JSON against an artefact
    already at 4.40 MB — a 39% larger download on *every* page, including the daily screen
    the owner opens each morning and which needs none of it. `vercel.json` serves
    `/data/*` with `Cache-Control: no-store`, so he would pay that every time.

    So it is written alongside, in the same run, from the same inputs, by the same engine,
    and fetched only by the pages that need it. The provenance argument for one artefact
    (§20.2: a number the owner asks about has exactly one place it could have come from)
    is untouched — this carries no computed figure at all. It is the product list the
    capabilities were computed *over*, which is why it also publishes `inputs_digest`: a
    reader can prove the catalogue and the artefact came from the same run rather than
    assume it.

WHAT IS IN IT, AND WHAT IS DELIBERATELY NOT
    Exactly `EngineInputs.products` — the resolved population, after ADR-019 and ADR-022
    remove rows whose duplicates disagree. 7,523 of the export's 7,674, and the same
    population every capability counts over, so the catalogue page and the finding pages
    cannot disagree about what exists.

    Prices stay `null` where the export has none. D-3: a product with no shelf price has no
    shelf price, and a zero would read as free. `recorded_stock` is published raw, negative
    values included (F2's whole point), and carries no money — D-1.

    No velocity, and this is the honest bottom of it. Reorder and the planogram screens
    need `salesLast7Days` / `salesLast30Days`. The sales tables are not missing — but they
    are MONTHLY, one row per product per month with no date column anywhere in the seven
    reports, so a daily rate is not measurable (rule 13). The 30-day table that would
    supply one existed and was deleted: `yomyom_sales.parquet`, whose `units_sold_30d` was
    synthesised from a monthly mean (rule 5). Publishing this catalogue does not change
    that, and must not be read as a step toward it.

    So this lights Prices (F1, F3), Products (F4) and Overview — the pages behind approved
    specs that only ever needed a product list. Assortment gaps and the written report are
    NOT on this file's path: the first is blocked on an undecided rule (F9, GAP-009), the
    second is withdrawn (design §20.1, D-12).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import jsonschema

from src.engine.publish import PublishRefused

ROOT = Path(__file__).resolve().parents[2]
CATALOGUE_PATH = ROOT / "public" / "data" / "catalogue.json"
SCHEMA_PATH = ROOT / "schemas" / "catalogue.schema.json"

SCHEMA_VERSION = 1


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_catalogue(catalogue: dict) -> None:
    """Refuse BEFORE any write, the way publish.validate_artefact does (ADR-005).

    Reuses `PublishRefused` rather than inventing a sibling: the caller's handling is
    identical — record the step as an error, leave the previous file alone — and a second
    exception type would only invite one of the two to be caught and the other not.
    """
    try:
        jsonschema.validate(catalogue, _schema())
    except jsonschema.ValidationError as err:
        raise PublishRefused(
            f"catalogue violates schema: {err.message} at {list(err.absolute_path)}") from err
    if (catalogue.get("products") is None) != (catalogue.get("count") is None):
        raise PublishRefused(
            "catalogue count and products must be absent together: a count beside a null "
            "list, or a list beside a null count, states something the engine does not know")


def build_catalogue(products: list[dict[str, Any]] | None, *, generated_at: str,
                    inputs_digest: str, vintages: dict, population: str) -> dict:
    """The catalogue payload. `products=None` is published as absent, never as empty.

    An empty list would read as "the store has no products", which is a claim. `None` says
    the engine could not load them, which is what actually happened.
    """
    # Sorted by barcode, and this is not cosmetic. The nightly COMMITS this file, so git
    # only stores it once as long as the bytes repeat night to night. Emitted in
    # dict-iteration or query order the block would differ every night in a way no reader
    # could see, every commit would carry the whole 1.73 MB, and the repo would grow by
    # roughly that much per day for nothing. The repository already holds this rule in the
    # same shape — ADR-021 sorts `last_seen_at` "so the artefact stays deterministic".
    ordered = None if products is None else sorted(
        products, key=lambda row: (str(row.get("barcode") or ""), str(row.get("product_name") or "")),
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        # The same digest the artefact carries, so the two can be proved to be one run
        # rather than assumed to be. They are fetched separately and could drift.
        "inputs_digest": inputs_digest,
        "population": population,
        "pos": vintages.get("pos") if vintages else None,
        "count": None if ordered is None else len(ordered),
        "products": ordered,
    }


def write_catalogue(catalogue: dict, path: Path = CATALOGUE_PATH) -> Path:
    """Atomic, for the same reason the artefact is: a reader must never see half a file.

    Written compactly rather than indented — this is 1.73 MB of data nobody reads by eye,
    and indentation costs the owner about 400 KB of download for nothing.

    Validated first. A catalogue that breaches its schema must not replace a good one:
    the three pages that read it would rather show yesterday's list than a broken one,
    and `inputs_digest` is what tells them which they are looking at.
    """
    validate_catalogue(catalogue)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(catalogue, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    os.replace(tmp, path)
    return path
