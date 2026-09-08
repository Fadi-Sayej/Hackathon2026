# V1 Phase 0 — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put in place everything every capability depends on: the typed contract and JSON schema, the policy file, the owner-state model with its Firestore pull and committed mirror, the ingestion fixes (month-grained sales, POS vintage, barcode normalisation, per-store matches, client-store role), the engine orchestrator and atomic publisher, and CI that runs tests on every push.

**Architecture:** New package `src/engine/` (pure functions over `EngineInputs`), new package `src/owner_state/` (read-only in Python), refactored ingestion under `src/internal_pos/` and `scripts/run_engine.py` as the single orchestrator. At the end of this phase a run publishes a schema-valid `public/data/dashboard.json` whose `capabilities` block is empty — the frame the capabilities plug into.

**Tech Stack:** Python 3.9 (`.venv/bin/python`), pyarrow, pyyaml, jsonschema, firebase-admin, pytest; GitHub Actions.

**Spec:** [`docs/architecture/system-design.md`](../architecture/system-design.md) §7.1–7.3, §10, §11, §12, §13, §20.2, §23 Phase 0.

## Global Constraints

See [`2026-09-08-v1-00-index.md`](plan.md) — applies in full. Additionally for this phase:

- New Python modules use plain `list[dict]` rows read with `pyarrow.parquet.read_table(...).to_pylist()` (the existing engine convention), not polars.
- Every new module gets a test under `tests/` before its implementation (TDD), run with `.venv/bin/python -m pytest tests/<file> -q`.
- Barcode normalisation is one function, `src/engine/model.py::norm_barcode`, used everywhere: `str(value or '').strip().lstrip('0')`; empty → `None`.

## File structure (this phase)

| File | Responsibility |
|---|---|
| `configs/policy.yaml` | Every declared constant (design §10.4) |
| `src/engine/__init__.py` | empty |
| `src/engine/policy.py` | `Policy` dataclass + `load_policy()` |
| `src/engine/model.py` | `Value`, `Entry`, `Figure`, `EvidenceWindow`, `CapabilityOutput`, `entry_id`, `norm_barcode` |
| `src/engine/registry.py` | capability ids, spec ids, value policies |
| `schemas/dashboard.schema.json` | artefact contract (shared with JS) |
| `src/engine/publish.py` | `build_artefact`, `validate_artefact`, `PublishRefused`, `write_atomic` |
| `src/engine/inputs.py` | `EngineInputs` + `load_inputs()` |
| `src/engine/run.py` | `run_engine(mode)` orchestration, step isolation, verdict |
| `scripts/run_engine.py` | CLI: `npm run data:refresh` |
| `src/owner_state/__init__.py` | empty |
| `src/owner_state/model.py` | `OwnerState`, parsing, `unavailable()` |
| `src/owner_state/pull.py` | Firestore pull via firebase-admin, mirror read/write |
| `src/internal_pos/sales_importer.py` | monthly + summary tables + evidence window |
| `src/internal_pos/pos_importer.py` | `--as-of`; stop writing the sales table |
| `src/signals/competitor_product_signals.py`, `src/matching/product_matching.py` | barcode zero-strip; keep every store's row |
| `configs/store_types.yaml`, `src/common/store_types.py` | `role: client`; Einat venue; `client_store_ids()` |
| `.github/workflows/ci.yml` | lint · vitest · pytest · build on push/PR |
| `tests/engine/…`, `tests/owner_state/…`, `tests/internal_pos/…` | tests |

---

### Task 0.1: Policy file and loader

**Files:**
- Create: `configs/policy.yaml`
- Create: `src/engine/__init__.py` (empty)
- Create: `src/engine/policy.py`
- Test: `tests/engine/test_policy.py`

**Interfaces:**
- Produces: `load_policy(path: Path | None = None) -> Policy`; `Policy` fields: `version: int`, `price_policy_pct: float`, `attention_pct: float`, `cost_floor_pct: float`, `freshness_days: int`, `artefact_min_price: float`, `artefact_cost_ratio: float`, `max_credible_gap_pct: float`, `surface_bound: int`, `surface_unvalued_places: int`, `question_limit: int`, `ceiling_band_pct: float`, `ceiling_drop_ratio: float`, `ceiling_min_band_count: int`, `implausible_revenue_share: float`, `full_annual_cycle_months: int`, `withdraw_with_stock: bool`, `as_dict() -> dict` (for `meta.thresholds`).

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_policy.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.engine.policy import load_policy


def test_policy_loads_declared_constants():
    p = load_policy()
    assert p.price_policy_pct == 60
    assert p.attention_pct == 100
    assert p.cost_floor_pct == 10
    assert p.surface_bound == 10
    assert p.surface_unvalued_places == 3
    assert p.question_limit == 3
    assert p.withdraw_with_stock is False


def test_policy_refuses_withdraw_with_stock(tmp_path):
    bad = tmp_path / "policy.yaml"
    bad.write_text("version: 1\nwithdraw_with_stock: true\n", encoding="utf-8")
    try:
        load_policy(bad)
    except ValueError as err:
        assert "OQ-409" in str(err)
    else:
        raise AssertionError("withdraw_with_stock: true must be refused until OQ-409 is answered")


def test_policy_as_dict_is_json_serialisable():
    import json
    json.dumps(load_policy().as_dict())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/engine/test_policy.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.engine'`

- [ ] **Step 3: Write the policy file and loader**

```yaml
# configs/policy.yaml — every declared constant in one place (design.md §10.4).
# Published verbatim into dashboard.json → meta.thresholds. Change a value here,
# never in code. Provisional values are marked with the open question they await.
version: 1

# SPEC-003 — declared, never derived (FR-045, FR-045b, FR-043a)
price_policy_pct: 60          # owner's stated maximum premium over the balanced reference
attention_pct: 100            # same-day attention above this premium
cost_floor_pct: 10            # reference must exceed our cost by this margin
freshness_days: 14            # OQ-306 provisional: observations older than this drive nothing

# D-4 data-entry artefacts (SPEC-001 FR-010)
artefact_min_price: 0.5
artefact_cost_ratio: 2
max_credible_gap_pct: 300     # legacy credibility.js guard, kept as a COUNTED exclusion (design §22.2)

# SPEC-006
surface:
  bound: 10
  unvalued_places: 3          # OQ-602 provisional

# SPEC-005 D-8
question_limit: 3

# SPEC-001 FR-004 ceiling derivation (reproduces 18% on the pilot distribution)
ceiling_derivation:
  band_pct: 2
  drop_ratio: 0.75
  min_band_count: 20

# SPEC-004
implausible_revenue_share: 0.10   # OQ-405 provisional
full_annual_cycle_months: 12      # OQ-408 provisional
withdraw_with_stock: false        # OQ-409 — must stay false; the loader refuses true
```

```python
# src/engine/policy.py
"""Declared constants for the engine. One file, published with every figure."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "configs" / "policy.yaml"


@dataclass(frozen=True)
class Policy:
    version: int
    price_policy_pct: float
    attention_pct: float
    cost_floor_pct: float
    freshness_days: int
    artefact_min_price: float
    artefact_cost_ratio: float
    max_credible_gap_pct: float
    surface_bound: int
    surface_unvalued_places: int
    question_limit: int
    ceiling_band_pct: float
    ceiling_drop_ratio: float
    ceiling_min_band_count: int
    implausible_revenue_share: float
    full_annual_cycle_months: int
    withdraw_with_stock: bool

    def as_dict(self) -> dict:
        return asdict(self)


def load_policy(path: Path | str | None = None) -> Policy:
    raw = yaml.safe_load(Path(path or DEFAULT_PATH).read_text(encoding="utf-8")) or {}
    surface = raw.get("surface", {}) or {}
    ceiling = raw.get("ceiling_derivation", {}) or {}
    policy = Policy(
        version=int(raw.get("version", 1)),
        price_policy_pct=float(raw.get("price_policy_pct", 60)),
        attention_pct=float(raw.get("attention_pct", 100)),
        cost_floor_pct=float(raw.get("cost_floor_pct", 10)),
        freshness_days=int(raw.get("freshness_days", 14)),
        artefact_min_price=float(raw.get("artefact_min_price", 0.5)),
        artefact_cost_ratio=float(raw.get("artefact_cost_ratio", 2)),
        max_credible_gap_pct=float(raw.get("max_credible_gap_pct", 300)),
        surface_bound=int(surface.get("bound", 10)),
        surface_unvalued_places=int(surface.get("unvalued_places", 3)),
        question_limit=int(raw.get("question_limit", 3)),
        ceiling_band_pct=float(ceiling.get("band_pct", 2)),
        ceiling_drop_ratio=float(ceiling.get("drop_ratio", 0.75)),
        ceiling_min_band_count=int(ceiling.get("min_band_count", 20)),
        implausible_revenue_share=float(raw.get("implausible_revenue_share", 0.10)),
        full_annual_cycle_months=int(raw.get("full_annual_cycle_months", 12)),
        withdraw_with_stock=bool(raw.get("withdraw_with_stock", False)),
    )
    if policy.withdraw_with_stock:
        raise ValueError(
            "withdraw_with_stock must be false: extending automatic withdrawal to "
            "stock-carrying entries is OQ-409 and is not authorised (SPEC-004 INV-030)."
        )
    if policy.question_limit > 3:
        raise ValueError("question_limit may not exceed 3 (D-8)")
    if policy.surface_bound > 10:
        raise ValueError("surface.bound may not exceed 10 (D-9)")
    return policy
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/engine/test_policy.py -q`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add configs/policy.yaml src/engine/__init__.py src/engine/policy.py tests/engine/test_policy.py
git commit -m "Declare every engine constant in configs/policy.yaml

The loader refuses withdraw_with_stock=true (OQ-409), a question limit above
three (D-8) and a surface bound above ten (D-9), so a config edit cannot
silently reopen a settled decision."
```

---

### Task 0.2: Engine model — values, entries, figures, windows, ids

**Files:**
- Create: `src/engine/model.py`
- Test: `tests/engine/test_model.py`

**Interfaces:**
- Produces:
  - `norm_barcode(value) -> str | None`
  - `entry_id(capability: str, barcode: str | None, variant: str = '') -> str` (16 hex chars)
  - `@dataclass Value(amount: float, kind: str, certainty: str)`; `VALUE_KINDS = ('per_sale',)`; `CERTAINTIES = ('confirmed', 'estimated')`
  - `@dataclass Entry(id, capability, barcode, product_name, department, action, characterisation, evidence: dict, value: Value | None, ordering_key: dict, actionable: bool, not_actionable_reason: str | None, attention: str)` with `to_dict()`
  - `@dataclass Figure(name, value, unit, inputs: list[str], thresholds: dict)` with `to_dict()`
  - `@dataclass EvidenceWindow(months: list[str], first, last, count, full_annual_cycle: bool)` with `to_dict()`, `window_id` property (`f"{first}..{last}"`)
  - `@dataclass CapabilityOutput(id, spec, status, unavailable_reason, window, thresholds, counts, entries, figures, notes)` with `to_dict()` (figures excluded) and classmethod `unavailable(id, spec, reason)`

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_model.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.engine.model import (
    CapabilityOutput, Entry, EvidenceWindow, Figure, Value, entry_id, norm_barcode,
)


def test_norm_barcode_strips_leading_zeros_and_blanks():
    assert norm_barcode("0007290000041445") == "7290000041445"
    assert norm_barcode("  12 ") == "12"
    assert norm_barcode("") is None
    assert norm_barcode(None) is None
    assert norm_barcode("000") is None


def test_entry_id_is_stable_and_independent_of_thresholds():
    a = entry_id("price_consistency", "7290000041445")
    b = entry_id("price_consistency", "07290000041445")
    assert a == b and len(a) == 16
    assert entry_id("reconciliation", "1", "negative_stock") != entry_id("reconciliation", "1", "no_identifier")


def test_value_rejects_unknown_kind():
    try:
        Value(amount=1.0, kind="one_off", certainty="confirmed")
    except ValueError:
        pass
    else:
        raise AssertionError("one_off is not a V1 value kind")


def test_capability_output_unavailable_has_no_entries_and_none_counts():
    out = CapabilityOutput.unavailable("reconciliation", "SPEC-002", "no_sales_evidence")
    d = out.to_dict()
    assert d["status"] == "unavailable"
    assert d["unavailable_reason"] == "no_sales_evidence"
    assert d["entries"] == []
    assert "figures" not in d


def test_window_id_and_serialisation():
    w = EvidenceWindow(months=["2026-01", "2026-02"], first="2026-01", last="2026-02", count=2, full_annual_cycle=False)
    assert w.window_id == "2026-01..2026-02"
    assert w.to_dict()["full_annual_cycle"] is False


def test_entry_to_dict_serialises_value_and_none():
    e = Entry(id="x", capability="price_consistency", barcode="1", product_name="n", department="d",
              action="verify_price", characterisation="confirmed_loss", evidence={"shelf": 10.0},
              value=Value(2.0, "per_sale", "confirmed"), ordering_key={"name": "loss", "value": 2.0},
              actionable=True, not_actionable_reason=None, attention="today")
    d = e.to_dict()
    assert d["value"] == {"amount": 2.0, "kind": "per_sale", "certainty": "confirmed"}
    e2 = Entry(**{**e.__dict__, "value": None})
    assert e2.to_dict()["value"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/engine/test_model.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the model**

```python
# src/engine/model.py
"""The engine's vocabulary (design.md §10, §11.2, §11.3). Pure data, no I/O."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

VALUE_KINDS = ("per_sale",)
CERTAINTIES = ("confirmed", "estimated")
STATUSES = ("available", "unavailable")
ACTIONS = ("verify_price", "count_product", "fix_record", "decide_idle", "review_policy", "check_purchase_cost")


def norm_barcode(value: Any) -> Optional[str]:
    text = str(value or "").strip().lstrip("0")
    return text or None


def entry_id(capability: str, barcode: Optional[str], variant: str = "") -> str:
    key = "|".join([capability, norm_barcode(barcode) or "", variant])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Value:
    amount: float
    kind: str
    certainty: str

    def __post_init__(self) -> None:
        if self.kind not in VALUE_KINDS:
            raise ValueError(f"unknown value kind {self.kind!r}; V1 kinds: {VALUE_KINDS}")
        if self.certainty not in CERTAINTIES:
            raise ValueError(f"unknown certainty {self.certainty!r}")

    def to_dict(self) -> dict:
        return {"amount": float(self.amount), "kind": self.kind, "certainty": self.certainty}


@dataclass
class Entry:
    id: str
    capability: str
    barcode: Optional[str]
    product_name: Optional[str]
    department: Optional[str]
    action: str
    characterisation: str
    evidence: dict
    value: Optional[Value]
    ordering_key: dict
    actionable: bool = False
    not_actionable_reason: Optional[str] = None
    attention: str = "today"

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["value"] = self.value.to_dict() if self.value else None
        return d


@dataclass
class Figure:
    name: str
    value: Optional[float]
    unit: str
    inputs: list
    thresholds: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"value": self.value, "unit": self.unit, "inputs": list(self.inputs), "thresholds": dict(self.thresholds)}


@dataclass
class EvidenceWindow:
    months: list
    first: Optional[str]
    last: Optional[str]
    count: int
    full_annual_cycle: bool

    @property
    def window_id(self) -> str:
        return f"{self.first}..{self.last}"

    def to_dict(self) -> dict:
        return {"months": list(self.months), "first": self.first, "last": self.last,
                "count": self.count, "full_annual_cycle": self.full_annual_cycle, "window_id": self.window_id}


@dataclass
class CapabilityOutput:
    id: str
    spec: str
    status: str
    unavailable_reason: Optional[str] = None
    window: Optional[EvidenceWindow] = None
    thresholds: dict = field(default_factory=dict)
    counts: dict = field(default_factory=dict)
    entries: list = field(default_factory=list)
    figures: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @classmethod
    def unavailable(cls, id: str, spec: str, reason: str) -> "CapabilityOutput":
        return cls(id=id, spec=spec, status="unavailable", unavailable_reason=reason)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "spec": self.spec, "status": self.status,
            "unavailable_reason": self.unavailable_reason,
            "window": self.window.to_dict() if self.window else None,
            "thresholds": dict(self.thresholds), "counts": dict(self.counts),
            "entries": [e.to_dict() for e in self.entries], "notes": list(self.notes),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/engine/test_model.py -q`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/engine/model.py tests/engine/test_model.py
git commit -m "Add the engine vocabulary: typed values, entries, windows, stable entry ids"
```

---

### Task 0.3: Capability registry with value policies

**Files:**
- Create: `src/engine/registry.py`
- Test: `tests/engine/test_registry.py`

**Interfaces:**
- Produces: `CAPABILITIES: dict[str, CapabilitySpec]` with `CapabilitySpec(id, spec, value_policy: 'per_sale' | 'none', admitted: bool, ordering_key: str)`; `value_policy_for(capability_id) -> str`; `ADMITTED_ORDER: list[str]` (unvalued precedence: `reconciliation`, `catalogue_lifecycle`).

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_registry.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.engine.registry import CAPABILITIES, value_policy_for


def test_stock_derived_capabilities_carry_no_value():
    assert value_policy_for("reconciliation") == "none"
    assert value_policy_for("catalogue_lifecycle") == "none"
    assert value_policy_for("competitor_position") == "none"


def test_price_consistency_may_carry_per_sale():
    assert value_policy_for("price_consistency") == "per_sale"


def test_margin_below_cost_is_not_admitted_to_the_surface():
    assert CAPABILITIES["margin_below_cost"].admitted is False


def test_every_capability_names_its_spec():
    for cap in CAPABILITIES.values():
        assert cap.spec.startswith("SPEC-") or cap.spec == "UNSPECIFIED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/engine/test_registry.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the registry**

```python
# src/engine/registry.py
"""What each capability is allowed to publish (design.md §10.2, ADR-012)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilitySpec:
    id: str
    spec: str
    value_policy: str      # 'per_sale' | 'none'
    admitted: bool         # may its entries reach the daily surface?
    ordering_key: str      # name of the per-capability ordering key


CAPABILITIES = {
    "price_consistency":   CapabilitySpec("price_consistency",   "SPEC-001", "per_sale", True,  "loss_per_sale"),
    "reconciliation":      CapabilitySpec("reconciliation",      "SPEC-002", "none",     True,  "gap_ratio"),
    "competitor_position": CapabilitySpec("competitor_position", "SPEC-003", "none",     True,  "premium_pct"),
    "catalogue_lifecycle": CapabilitySpec("catalogue_lifecycle", "SPEC-004", "none",     True,  "unit_cost"),
    "owner_questions":     CapabilitySpec("owner_questions",     "SPEC-005", "none",     False, "expected_value"),
    "margin_below_cost":   CapabilitySpec("margin_below_cost",   "UNSPECIFIED", "per_sale", False, "loss_per_sale"),
}

# Unvalued precedence for one-product-one-place and interleaving (OQ-601 provisional).
UNVALUED_PRECEDENCE = ["reconciliation", "catalogue_lifecycle", "competitor_position"]


def value_policy_for(capability_id: str) -> str:
    return CAPABILITIES[capability_id].value_policy
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/engine/test_registry.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/engine/registry.py tests/engine/test_registry.py
git commit -m "Register the six capabilities with their value policies and admission"
```

---

### Task 0.4: Artefact schema and publisher validation

**Files:**
- Create: `schemas/dashboard.schema.json`
- Create: `src/engine/publish.py`
- Modify: `requirements.txt` (add `jsonschema>=4.0`)
- Test: `tests/engine/test_publish.py`

**Interfaces:**
- Produces: `build_artefact(outputs: list[CapabilityOutput], *, vintages: dict, thresholds: dict, run: dict, catalogue: dict | None, questions: dict | None, generated_at: str, run_id: str) -> dict`; `validate_artefact(artefact: dict) -> None` (raises `PublishRefused`); `write_atomic(path: Path, artefact: dict) -> Path`; `PublishRefused(RuntimeError)`.
- The schema is the contract both sides validate (design §11.4).

- [ ] **Step 1: Install jsonschema and write the failing test**

Run: `echo 'jsonschema>=4.0' >> requirements.txt && .venv/bin/pip install -q 'jsonschema>=4.0'`

```python
# tests/engine/test_publish.py
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from src.engine.model import CapabilityOutput, Entry, Value
from src.engine.publish import PublishRefused, build_artefact, validate_artefact, write_atomic

VINTAGES = {"pos": {"file": "x.csv", "as_of": "2026-08-02"},
            "sales": {"months": ["2026-01"], "first": "2026-01", "last": "2026-01", "full_annual_cycle": False},
            "competitor": {"snapshot_date": None, "sources": []},
            "owner_state": {"pulled_at": None, "status": "unavailable"}}
RUN = {"status": "ok", "steps": []}


def _artefact(outputs):
    return build_artefact(outputs, vintages=VINTAGES, thresholds={"surface": {"bound": 10, "unvalued_places": 3}},
                          run=RUN, catalogue=None, questions=None,
                          generated_at="2026-09-08T00:00:00+00:00", run_id="r1")


def test_empty_capability_set_is_a_valid_artefact():
    art = _artefact([])
    validate_artefact(art)
    assert art["schema_version"] == 2
    assert art["value_kinds_present"] == []


def test_refuses_a_capability_without_status():
    art = _artefact([CapabilityOutput.unavailable("reconciliation", "SPEC-002", "x")])
    art["capabilities"]["reconciliation"]["status"] = None
    with pytest.raises(PublishRefused):
        validate_artefact(art)


def test_refuses_value_on_a_none_policy_capability():
    e = Entry(id="a", capability="reconciliation", barcode="1", product_name=None, department=None,
              action="count_product", characterisation="inconsistent", evidence={},
              value=Value(5.0, "per_sale", "confirmed"), ordering_key={"name": "gap_ratio", "value": 1.0})
    out = CapabilityOutput(id="reconciliation", spec="SPEC-002", status="available", entries=[e])
    with pytest.raises(PublishRefused, match="value_policy"):
        validate_artefact(_artefact([out]))


def test_value_kinds_present_is_derived():
    e = Entry(id="a", capability="price_consistency", barcode="1", product_name=None, department=None,
              action="verify_price", characterisation="confirmed_loss", evidence={},
              value=Value(5.0, "per_sale", "confirmed"), ordering_key={"name": "loss_per_sale", "value": 5.0})
    out = CapabilityOutput(id="price_consistency", spec="SPEC-001", status="available", entries=[e])
    assert _artefact([out])["value_kinds_present"] == ["per_sale"]


def test_write_atomic_never_leaves_a_torn_file(tmp_path):
    target = tmp_path / "dashboard.json"
    target.write_text("OLD", encoding="utf-8")
    write_atomic(target, _artefact([]))
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == 2
    assert not (tmp_path / "dashboard.json.tmp").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/engine/test_publish.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "smartshelf/dashboard.schema.json",
  "title": "SmartShelf dashboard artefact v2",
  "type": "object",
  "required": ["schema_version", "generated_at", "run_id", "run", "vintages", "thresholds",
               "value_kinds_present", "capabilities", "catalogue", "questions", "figures"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "const": 2 },
    "generated_at": { "type": "string" },
    "run_id": { "type": "string" },
    "run": {
      "type": "object", "required": ["status", "steps"],
      "properties": {
        "status": { "enum": ["ok", "partial", "degraded"] },
        "steps": { "type": "array", "items": { "type": "object", "required": ["step", "status"],
          "properties": { "step": {"type": "string"}, "status": {"enum": ["ok", "error", "skipped", "degraded"]},
                          "ms": {"type": ["number", "null"]}, "error": {"type": ["string", "null"]} } } }
      }
    },
    "vintages": {
      "type": "object", "required": ["pos", "sales", "competitor", "owner_state"],
      "properties": {
        "pos": { "type": "object", "required": ["file", "as_of"],
                 "properties": { "file": {"type": ["string", "null"]}, "as_of": {"type": ["string", "null"]} } },
        "sales": { "type": "object", "required": ["months", "first", "last", "full_annual_cycle"],
                   "properties": { "months": {"type": "array", "items": {"type": "string"}},
                                   "first": {"type": ["string", "null"]}, "last": {"type": ["string", "null"]},
                                   "full_annual_cycle": {"type": "boolean"} } },
        "competitor": { "type": "object", "required": ["snapshot_date", "sources"],
                        "properties": { "snapshot_date": {"type": ["string", "null"]},
                                        "sources": {"type": "array", "items": {"type": "string"}} } },
        "owner_state": { "type": "object", "required": ["pulled_at", "status"],
                         "properties": { "pulled_at": {"type": ["string", "null"]},
                                         "status": {"enum": ["available", "unavailable"]} } }
      }
    },
    "thresholds": { "type": "object" },
    "value_kinds_present": { "type": "array", "items": { "enum": ["per_sale"] } },
    "capabilities": {
      "type": "object",
      "additionalProperties": { "$ref": "#/$defs/capability" }
    },
    "catalogue": { "type": ["object", "null"] },
    "questions": { "type": ["object", "null"] },
    "figures": {
      "type": "object",
      "additionalProperties": { "type": "object", "required": ["value", "unit", "inputs", "thresholds"],
        "properties": { "value": {"type": ["number", "null"]}, "unit": {"type": "string"},
                        "inputs": {"type": "array", "items": {"type": "string"}}, "thresholds": {"type": "object"} } }
    }
  },
  "$defs": {
    "value": {
      "type": ["object", "null"],
      "required": ["amount", "kind", "certainty"],
      "properties": { "amount": {"type": "number"}, "kind": {"enum": ["per_sale"]},
                      "certainty": {"enum": ["confirmed", "estimated"]} }
    },
    "entry": {
      "type": "object",
      "required": ["id", "capability", "barcode", "product_name", "department", "action", "characterisation",
                   "evidence", "value", "ordering_key", "actionable", "not_actionable_reason", "attention"],
      "properties": {
        "id": { "type": "string", "pattern": "^[0-9a-f]{16}$" },
        "capability": { "type": "string" },
        "barcode": { "type": ["string", "null"] },
        "product_name": { "type": ["string", "null"] },
        "department": { "type": ["string", "null"] },
        "action": { "enum": ["verify_price", "count_product", "fix_record", "decide_idle", "review_policy", "check_purchase_cost"] },
        "characterisation": { "type": "string" },
        "evidence": { "type": "object" },
        "value": { "$ref": "#/$defs/value" },
        "ordering_key": { "type": "object", "required": ["name", "value"],
                          "properties": { "name": {"type": "string"}, "value": {"type": ["number", "null"]} } },
        "actionable": { "type": "boolean" },
        "not_actionable_reason": { "type": ["string", "null"] },
        "attention": { "enum": ["today", "review"] }
      }
    },
    "capability": {
      "type": "object",
      "required": ["id", "spec", "status", "unavailable_reason", "window", "thresholds", "counts", "entries", "notes"],
      "properties": {
        "id": { "type": "string" },
        "spec": { "type": "string" },
        "status": { "enum": ["available", "unavailable"] },
        "unavailable_reason": { "type": ["string", "null"] },
        "window": { "type": ["object", "null"] },
        "thresholds": { "type": "object" },
        "counts": { "type": "object", "additionalProperties": { "type": ["integer", "null"] } },
        "entries": { "type": "array", "items": { "$ref": "#/$defs/entry" } },
        "notes": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

- [ ] **Step 4: Write the publisher**

```python
# src/engine/publish.py
"""Build, validate and atomically write the artefact (design.md §7.3, §11.4, ADR-005)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import jsonschema

from src.engine.model import CapabilityOutput
from src.engine.registry import CAPABILITIES

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "dashboard.schema.json"
ARTEFACT_PATH = ROOT / "public" / "data" / "dashboard.json"


class PublishRefused(RuntimeError):
    """Raised BEFORE any write. The previous artefact survives."""


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def value_kinds_present(outputs: list[CapabilityOutput]) -> list[str]:
    kinds = set()
    for out in outputs:
        for e in out.entries:
            if e.value is not None:
                kinds.add(e.value.kind)
    return sorted(kinds)


def build_artefact(outputs, *, vintages, thresholds, run, catalogue, questions, generated_at, run_id) -> dict:
    figures = {}
    for out in outputs:
        for f in out.figures:
            figures[f"{out.id}.{f.name}"] = f.to_dict()
    return {
        "schema_version": 2,
        "generated_at": generated_at,
        "run_id": run_id,
        "run": run,
        "vintages": vintages,
        "thresholds": thresholds,
        "value_kinds_present": value_kinds_present(outputs),
        "capabilities": {out.id: out.to_dict() for out in outputs},
        "catalogue": catalogue,
        "questions": questions,
        "figures": figures,
    }


def validate_artefact(artefact: dict) -> None:
    try:
        jsonschema.validate(artefact, _schema())
    except jsonschema.ValidationError as err:
        raise PublishRefused(f"artefact violates schema: {err.message} at {list(err.absolute_path)}") from err
    for cap_id, cap in artefact["capabilities"].items():
        if cap.get("status") not in ("available", "unavailable"):
            raise PublishRefused(f"capability {cap_id} has no status")
        spec = CAPABILITIES.get(cap_id)
        if spec is None:
            raise PublishRefused(f"unregistered capability {cap_id}")
        if spec.value_policy == "none":
            for e in cap["entries"]:
                if e.get("value") is not None:
                    raise PublishRefused(f"value_policy none: {cap_id} entry {e['id']} carries a value (D-1)")
    # FR-105: the single-kind premise is derived, and V1 permits at most one kind.
    if len(artefact["value_kinds_present"]) > 1:
        raise PublishRefused("more than one value kind present; FR-106 allocation must be re-derived (GAP-002)")


def write_atomic(path: Path, artefact: dict) -> Path:
    validate_artefact(artefact)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(artefact, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    return path
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/engine/test_publish.py -q`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add schemas/dashboard.schema.json src/engine/publish.py tests/engine/test_publish.py requirements.txt
git commit -m "Add the artefact schema and a publisher that refuses before writing

Missing status, a value on a stock-derived capability, or more than one value
kind all refuse the publish. The write is tmp+rename so a reader never sees a
torn file and the last good artefact survives every failure."
```

---

### Task 0.5: Owner-state model, mirror, and Firestore pull

**Files:**
- Create: `src/owner_state/__init__.py` (empty)
- Create: `src/owner_state/model.py`
- Create: `src/owner_state/pull.py`
- Test: `tests/owner_state/test_model.py`, `tests/owner_state/test_pull.py`

**Interfaces:**
- Produces:
  - `@dataclass OwnerState(status: str, pulled_at: str | None, answers: dict, outcomes: dict, revivals: dict, schema: int)`; `OwnerState.unavailable(reason) -> OwnerState` (status `unavailable`, empty maps, `reason` attribute); `OwnerState.from_dict(d)`; `to_dict()`.
  - `answered_cost(state, barcode) -> float | None` (only `status == 'answered'` records; value > 0).
  - `standing_outcome(state, entry_id, now_ms) -> dict | None`.
  - `revival_active(state, barcode, window_id) -> bool`.
  - `pull(*, project_id, store_id, credentials_json: str | None, credentials_path: str | None, client=None) -> OwnerState` — `client` is an injected object with `.collection(path).stream()`-like interface for tests; production builds it from firebase-admin.
  - `write_mirror(state, path) -> Path`; `read_mirror(path) -> OwnerState` (status `unavailable` with reason `mirror_missing` when absent).
- Firestore layout (design §11.5): `stores/{store_id}/ownerState/{answers|outcomes|revivals|meta}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/owner_state/test_model.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.owner_state.model import OwnerState, answered_cost, revival_active, standing_outcome


def _state():
    return OwnerState.from_dict({
        "schema": 1, "status": "available", "pulled_at": "2026-09-08T00:00:00+00:00",
        "answers": {"123": {"cost_price": {"value": 4.5, "at": 1, "status": "answered"}},
                    "456": {"cost_price": {"value": None, "at": 1, "status": "deferred", "reason": "unknown"}}},
        "outcomes": {"e1": {"status": "acted", "at": 1}, "e2": {"status": "deferred", "at": 1, "deferred_until": 100}},
        "revivals": {"789": {"at": 1, "window_id": "2026-01..2026-07"}},
    })


def test_answered_cost_ignores_deferrals():
    s = _state()
    assert answered_cost(s, "123") == 4.5
    assert answered_cost(s, "0123") == 4.5      # normalised barcode
    assert answered_cost(s, "456") is None


def test_standing_outcome_respects_deferral_deadline():
    s = _state()
    assert standing_outcome(s, "e1", now_ms=50)["status"] == "acted"
    assert standing_outcome(s, "e2", now_ms=50)["status"] == "deferred"
    assert standing_outcome(s, "e2", now_ms=101) is None


def test_revival_is_window_bound():
    s = _state()
    assert revival_active(s, "789", "2026-01..2026-07") is True
    assert revival_active(s, "789", "2026-01..2026-08") is False


def test_unavailable_state_is_empty_and_says_why():
    s = OwnerState.unavailable("pull_failed")
    assert s.status == "unavailable" and s.reason == "pull_failed"
    assert s.answers == {} and s.outcomes == {} and s.revivals == {}
```

```python
# tests/owner_state/test_pull.py
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.owner_state.model import OwnerState
from src.owner_state.pull import pull, read_mirror, write_mirror


class _Doc:
    def __init__(self, id, data): self.id, self._data = id, data
    def to_dict(self): return self._data


class _Col:
    def __init__(self, docs): self._docs = docs
    def stream(self): return iter(self._docs)


class _Client:
    """Stands in for firestore.Client: collection('stores/x/ownerState')."""
    def __init__(self, docs): self._docs = docs
    def collection(self, path):
        assert path == "stores/yomyom-kafr-qasim/ownerState"
        return _Col(self._docs)


def test_pull_reads_the_four_documents():
    client = _Client([
        _Doc("answers", {"123": {"cost_price": {"value": 2.0, "at": 1, "status": "answered"}}}),
        _Doc("outcomes", {"e1": {"status": "acted", "at": 1}}),
        _Doc("revivals", {}),
        _Doc("meta", {"schema": 1, "updated_at": 5}),
    ])
    s = pull(project_id="p", store_id="yomyom-kafr-qasim", credentials_json=None, credentials_path=None, client=client)
    assert s.status == "available"
    assert s.answers["123"]["cost_price"]["value"] == 2.0
    assert s.outcomes["e1"]["status"] == "acted"


def test_pull_failure_is_unavailable_not_empty():
    class Broken:
        def collection(self, path): raise RuntimeError("network")
    s = pull(project_id="p", store_id="yomyom-kafr-qasim", credentials_json=None, credentials_path=None, client=Broken())
    assert s.status == "unavailable" and s.reason == "pull_failed: RuntimeError"


def test_pull_rejects_unknown_schema():
    client = _Client([_Doc("meta", {"schema": 99})])
    s = pull(project_id="p", store_id="yomyom-kafr-qasim", credentials_json=None, credentials_path=None, client=client)
    assert s.status == "unavailable" and s.reason == "owner_state_schema"


def test_mirror_round_trip(tmp_path):
    s = OwnerState.from_dict({"schema": 1, "status": "available", "pulled_at": "t",
                              "answers": {"1": {}}, "outcomes": {}, "revivals": {}})
    p = write_mirror(s, tmp_path / "owner_state.json")
    back = read_mirror(p)
    assert back.status == "available" and back.answers == {"1": {}}
    assert json.loads(p.read_text())["schema"] == 1


def test_missing_mirror_is_unavailable(tmp_path):
    assert read_mirror(tmp_path / "nope.json").reason == "mirror_missing"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/owner_state -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the model**

```python
# src/owner_state/model.py
"""The only mutable state in the system, read-only in Python (design.md §10.3, ADR-003)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.engine.model import norm_barcode

SCHEMA = 1


@dataclass
class OwnerState:
    status: str
    pulled_at: Optional[str]
    answers: dict = field(default_factory=dict)
    outcomes: dict = field(default_factory=dict)
    revivals: dict = field(default_factory=dict)
    schema: int = SCHEMA
    reason: Optional[str] = None

    @classmethod
    def unavailable(cls, reason: str) -> "OwnerState":
        return cls(status="unavailable", pulled_at=None, reason=reason)

    @classmethod
    def from_dict(cls, d: dict) -> "OwnerState":
        answers = {norm_barcode(k) or k: v for k, v in (d.get("answers") or {}).items()}
        revivals = {norm_barcode(k) or k: v for k, v in (d.get("revivals") or {}).items()}
        return cls(status=d.get("status", "available"), pulled_at=d.get("pulled_at"),
                   answers=answers, outcomes=dict(d.get("outcomes") or {}), revivals=revivals,
                   schema=int(d.get("schema", SCHEMA)), reason=d.get("reason"))

    def to_dict(self) -> dict:
        return {"schema": self.schema, "status": self.status, "pulled_at": self.pulled_at,
                "reason": self.reason, "answers": self.answers, "outcomes": self.outcomes,
                "revivals": self.revivals}


def answered_cost(state: OwnerState, barcode) -> Optional[float]:
    rec = (state.answers.get(norm_barcode(barcode) or "") or {}).get("cost_price") or {}
    if rec.get("status") != "answered":
        return None
    value = rec.get("value")
    return float(value) if isinstance(value, (int, float)) and value > 0 else None


def standing_outcome(state: OwnerState, entry_id: str, now_ms: int) -> Optional[dict]:
    rec = state.outcomes.get(entry_id)
    if not rec:
        return None
    status = rec.get("status")
    if status in ("acted", "declined"):
        return rec
    if status == "deferred" and (rec.get("deferred_until") or 0) > now_ms:
        return rec
    return None


def revival_active(state: OwnerState, barcode, window_id: str) -> bool:
    rec = state.revivals.get(norm_barcode(barcode) or "")
    return bool(rec) and rec.get("window_id") == window_id
```

- [ ] **Step 4: Write the pull and mirror**

```python
# src/owner_state/pull.py
"""Pull owner state from Firestore at run start; mirror it for reproduction.

The engine only READS. firebase-admin is imported lazily so tests and local runs
without a service account never touch it (ADR-003)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.owner_state.model import SCHEMA, OwnerState

ROOT = Path(__file__).resolve().parents[2]
MIRROR_PATH = ROOT / "data" / "owner" / "owner_state.json"
DOCS = ("answers", "outcomes", "revivals", "meta")


def _admin_client(project_id: str, credentials_json: Optional[str], credentials_path: Optional[str]):
    import firebase_admin
    from firebase_admin import credentials, firestore

    if credentials_json:
        cred = credentials.Certificate(json.loads(credentials_json))
    elif credentials_path:
        cred = credentials.Certificate(credentials_path)
    else:
        raise RuntimeError("no service account: set FIREBASE_SERVICE_ACCOUNT_JSON or _PATH")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {"projectId": project_id})
    return firestore.client()


def pull(*, project_id: str, store_id: str, credentials_json: Optional[str],
         credentials_path: Optional[str], client=None, now: Optional[datetime] = None) -> OwnerState:
    try:
        client = client or _admin_client(project_id, credentials_json, credentials_path)
        docs = {d.id: d.to_dict() or {} for d in client.collection(f"stores/{store_id}/ownerState").stream()}
    except Exception as exc:  # noqa: BLE001 — any failure is 'unavailable', never 'empty'
        return OwnerState.unavailable(f"pull_failed: {type(exc).__name__}")
    meta = docs.get("meta") or {}
    if int(meta.get("schema", SCHEMA)) != SCHEMA:
        return OwnerState.unavailable("owner_state_schema")
    pulled_at = (now or datetime.now(timezone.utc)).isoformat()
    return OwnerState.from_dict({
        "schema": SCHEMA, "status": "available", "pulled_at": pulled_at,
        "answers": docs.get("answers") or {}, "outcomes": docs.get("outcomes") or {},
        "revivals": docs.get("revivals") or {},
    })


def write_mirror(state: OwnerState, path: Path = MIRROR_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return path


def read_mirror(path: Path = MIRROR_PATH) -> OwnerState:
    if not path.exists():
        return OwnerState.unavailable("mirror_missing")
    state = OwnerState.from_dict(json.loads(path.read_text(encoding="utf-8")))
    state.reason = state.reason or "from_mirror"
    return state
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/owner_state -q`
Expected: 9 passed

- [ ] **Step 6: Add the mirror path to git's force-add rule and commit**

Edit `.gitignore`: after the existing `data/**` ignore, add the exception lines:

```
# The owner-state mirror is committed by CI, like the market snapshots (ADR-003).
!data/owner/
!data/owner/owner_state.json
```

```bash
git add src/owner_state tests/owner_state .gitignore
git commit -m "Add the owner-state model and a read-only Firestore pull with a committed mirror

A failed pull is 'unavailable', never an empty state, so a network error cannot
masquerade as 'the owner answered nothing' (D-3)."
```

---

### Task 0.6: Month-grained sales importer with the evidence window

**Files:**
- Create: `src/internal_pos/sales_importer.py`
- Test: `tests/internal_pos/test_sales_importer.py`
- Modify: `scripts/import_yomyom_sales.py` → thin wrapper calling the new module (keep the CLI name for CI)

**Interfaces:**
- Consumes: `norm_barcode` (Task 0.2), `EvidenceWindow` (Task 0.2).
- Produces: `import_sales(directory: Path, *, inventory_as_of: date | None, full_cycle_months: int = 12, silver_dir: Path = SILVER_POS_ROOT, imported_at: str | None = None) -> dict` writing
  - `sales_monthly.parquet`: columns `barcode, month (YYYY-MM), product_name, units, receipts, revenue, cost_price, selling_price, _imported_at, _source_file` — one row per (barcode, month) present in a report; **no row is written for a product absent from a report**.
  - `sales_summary.parquet`: one row per barcode present in ≥1 report: `barcode, product_name, months_present (int), units_total, receipts_total, last_month_with_units (YYYY-MM | null), observed_zero (bool: appeared with 0 units in some month), reconcile_units, reconcile_receipts, reconcile_months`.
  - returns `{"window": EvidenceWindow.to_dict(), "monthly_rows": n, "products": n, "reconcile_before": "YYYY-MM" | None}`.
- `evidence_window(months: list[str], full_cycle_months) -> EvidenceWindow` — `full_annual_cycle` is true when `count >= full_cycle_months` **and** the months are consecutive (OQ-408 provisional).

- [ ] **Step 1: Write the failing test**

```python
# tests/internal_pos/test_sales_importer.py
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyarrow.parquet as pq

from src.internal_pos.sales_importer import evidence_window, import_sales

HEADER = "תאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n"


def _write(dirpath: Path, name: str, rows: list[str]):
    (dirpath / name).write_text("﻿" + HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")


def test_writes_one_row_per_barcode_per_month_and_a_summary(tmp_path):
    reports = tmp_path / "sales"; reports.mkdir()
    _write(reports, "דוח מכירות חודש ינואר 2026.csv", ["מים,00123,10,2,4,20,12,2,0,1,", "קפה,555,0,1,3,0,0,1,0,1,"])
    _write(reports, "דוח מכירות חודש פברואר 2026.csv", ["מים,123,5,2,4,10,0,2,0,1,"])
    silver = tmp_path / "silver"
    result = import_sales(reports, inventory_as_of=date(2026, 3, 1), silver_dir=silver, imported_at="t")

    monthly = pq.read_table(silver / "sales_monthly.parquet").to_pylist()
    assert sorted((r["barcode"], r["month"]) for r in monthly) == [("123", "2026-01"), ("123", "2026-02"), ("555", "2026-01")]
    summary = {r["barcode"]: r for r in pq.read_table(silver / "sales_summary.parquet").to_pylist()}
    assert summary["123"]["units_total"] == 15 and summary["123"]["receipts_total"] == 12
    assert summary["123"]["last_month_with_units"] == "2026-02"
    assert summary["555"]["observed_zero"] is True and summary["555"]["last_month_with_units"] is None
    assert result["window"]["months"] == ["2026-01", "2026-02"]
    assert result["window"]["full_annual_cycle"] is False


def test_reconcile_window_stops_before_the_inventory_month(tmp_path):
    reports = tmp_path / "sales"; reports.mkdir()
    _write(reports, "דוח מכירות חודש ינואר 2026.csv", ["a,1,10,1,1,0,7,1,0,1,"])
    _write(reports, "דוח מכירות חודש פברואר 2026.csv", ["a,1,20,1,1,0,9,1,0,1,"])
    silver = tmp_path / "silver"
    import_sales(reports, inventory_as_of=date(2026, 2, 15), silver_dir=silver, imported_at="t")
    row = pq.read_table(silver / "sales_summary.parquet").to_pylist()[0]
    assert row["reconcile_units"] == 10 and row["reconcile_receipts"] == 7 and row["reconcile_months"] == 1


def test_evidence_window_requires_consecutive_months():
    w = evidence_window([f"2025-{m:02d}" for m in range(1, 13)], 12)
    assert w.full_annual_cycle is True
    gap = evidence_window(["2025-01", "2025-03"] + [f"2025-{m:02d}" for m in range(4, 14) if m <= 12], 12)
    assert gap.full_annual_cycle is False


def test_no_reports_means_no_window(tmp_path):
    reports = tmp_path / "sales"; reports.mkdir()
    result = import_sales(reports, inventory_as_of=None, silver_dir=tmp_path / "silver", imported_at="t")
    assert result["window"] is None and result["monthly_rows"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/internal_pos/test_sales_importer.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Write the importer**

```python
# src/internal_pos/sales_importer.py
"""Monthly sales reports → month-grained evidence (design.md §7.1, ADR-011).

Measured: units and receipts per product per calendar month. The month comes
from the FILENAME — the reports carry no date column (CLAUDE.md rule 13).
A product absent from a report gets NO row: absence is `none`, never zero."""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

from src.common.paths import SILVER_POS_ROOT
from src.engine.model import EvidenceWindow, norm_barcode

HEBREW_MONTHS = {"ינואר": 1, "פברואר": 2, "מרץ": 3, "אפריל": 4, "מאי": 5, "יוני": 6,
                 "יולי": 7, "אוגוסט": 8, "ספטמבר": 9, "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12}
COL = {"name": "תאור פריט", "barcode": "ברקוד/קוד", "units": "מכר", "cost": "מחיר קניה",
       "price": "מחיר מכירה", "receipts": "כניסות מלאי"}


def _num(value) -> float:
    text = str(value or "").replace(",", "").strip()
    try:
        return float(text) if text else 0.0
    except ValueError:
        return 0.0


def month_from_filename(path: Path) -> Optional[str]:
    year = re.search(r"(20\d{2})", path.stem)
    for hebrew, number in HEBREW_MONTHS.items():
        if hebrew in path.stem and year:
            return f"{year.group(1)}-{number:02d}"
    return None


def _consecutive(months: list[str]) -> bool:
    for a, b in zip(months, months[1:]):
        ya, ma = map(int, a.split("-")); yb, mb = map(int, b.split("-"))
        if (yb * 12 + mb) - (ya * 12 + ma) != 1:
            return False
    return True


def evidence_window(months: list[str], full_cycle_months: int) -> EvidenceWindow:
    months = sorted(set(months))
    full = len(months) >= full_cycle_months and _consecutive(months)
    return EvidenceWindow(months=months, first=months[0] if months else None,
                         last=months[-1] if months else None, count=len(months), full_annual_cycle=full)


def read_report(path: Path) -> tuple[Optional[str], list[dict]]:
    month = month_from_filename(path)
    if month is None:
        return None, []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return month, []
    keys = {str(k).strip(): k for k in rows[0]}
    if COL["units"] not in keys or COL["barcode"] not in keys:
        return month, []
    out = []
    for row in rows:
        barcode = norm_barcode(row.get(keys[COL["barcode"]]))
        if not barcode:
            continue
        units = _num(row.get(keys[COL["units"]]))
        price = _num(row.get(keys.get(COL["price"], "")))
        out.append({"barcode": barcode, "month": month,
                    "product_name": str(row.get(keys.get(COL["name"], ""), "") or "").strip(),
                    "units": units, "receipts": _num(row.get(keys.get(COL["receipts"], ""))),
                    "revenue": units * price, "cost_price": _num(row.get(keys.get(COL["cost"], ""))),
                    "selling_price": price, "_source_file": path.name})
    return month, out


MONTHLY_SCHEMA = pa.schema([("barcode", pa.string()), ("month", pa.string()), ("product_name", pa.string()),
                            ("units", pa.float64()), ("receipts", pa.float64()), ("revenue", pa.float64()),
                            ("cost_price", pa.float64()), ("selling_price", pa.float64()),
                            ("_imported_at", pa.string()), ("_source_file", pa.string())])
SUMMARY_SCHEMA = pa.schema([("barcode", pa.string()), ("product_name", pa.string()), ("months_present", pa.int64()),
                            ("units_total", pa.float64()), ("receipts_total", pa.float64()),
                            ("last_month_with_units", pa.string()), ("observed_zero", pa.bool_()),
                            ("reconcile_units", pa.float64()), ("reconcile_receipts", pa.float64()),
                            ("reconcile_months", pa.int64()), ("_imported_at", pa.string())])


def import_sales(directory: Path, *, inventory_as_of: Optional[date], full_cycle_months: int = 12,
                 silver_dir: Path = SILVER_POS_ROOT, imported_at: Optional[str] = None) -> dict:
    imported_at = imported_at or datetime.now(timezone.utc).isoformat()
    monthly: list[dict] = []
    months: list[str] = []
    for path in sorted(directory.glob("*.csv")):
        month, rows = read_report(path)
        if month is None or not rows:
            continue
        months.append(month)
        monthly.extend(rows)
    if not months:
        return {"window": None, "monthly_rows": 0, "products": 0, "reconcile_before": None}

    window = evidence_window(months, full_cycle_months)
    reconcile_before = f"{inventory_as_of.year}-{inventory_as_of.month:02d}" if inventory_as_of else None

    by_barcode: dict[str, list[dict]] = defaultdict(list)
    for row in monthly:
        by_barcode[row["barcode"]].append(row)
    summary = []
    for barcode in sorted(by_barcode):
        rows = sorted(by_barcode[barcode], key=lambda r: r["month"])
        with_units = [r["month"] for r in rows if r["units"] > 0]
        in_window = [r for r in rows if reconcile_before is None or r["month"] < reconcile_before]
        summary.append({
            "barcode": barcode, "product_name": rows[-1]["product_name"], "months_present": len(rows),
            "units_total": sum(r["units"] for r in rows), "receipts_total": sum(r["receipts"] for r in rows),
            "last_month_with_units": max(with_units) if with_units else None,
            "observed_zero": any(r["units"] == 0 for r in rows),
            "reconcile_units": sum(r["units"] for r in in_window),
            "reconcile_receipts": sum(r["receipts"] for r in in_window),
            "reconcile_months": len(in_window), "_imported_at": imported_at,
        })

    silver_dir.mkdir(parents=True, exist_ok=True)
    for row in monthly:
        row["_imported_at"] = imported_at
    pq.write_table(pa.Table.from_pylist(sorted(monthly, key=lambda r: (r["barcode"], r["month"])), schema=MONTHLY_SCHEMA),
                   silver_dir / "sales_monthly.parquet", compression="snappy")
    pq.write_table(pa.Table.from_pylist(summary, schema=SUMMARY_SCHEMA),
                   silver_dir / "sales_summary.parquet", compression="snappy")
    return {"window": window.to_dict(), "monthly_rows": len(monthly), "products": len(summary),
            "reconcile_before": reconcile_before}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/internal_pos/test_sales_importer.py -q`
Expected: 4 passed

- [ ] **Step 5: Replace the CLI body with a wrapper**

Replace the whole of `scripts/import_yomyom_sales.py` with:

```python
"""import_yomyom_sales.py — monthly sales reports → silver evidence tables.

Thin wrapper over src/internal_pos/sales_importer.py so CI keeps its script name.
The old per-product velocity table (units_sold_7d synthesised from a monthly mean)
is gone: V1 reads sales_monthly / sales_summary (design.md §7.1)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import SILVER_POS_ROOT  # noqa: E402
from src.internal_pos.pos_importer import read_pos_vintage  # noqa: E402
from src.internal_pos.sales_importer import import_sales  # noqa: E402

DEFAULT_DIR = ROOT / "data" / "internal" / "raw_pos" / "yomyom" / "sales"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.dir.exists():
        print(f"Sales report directory not found: {args.dir}", file=sys.stderr)
        return 1
    vintage = read_pos_vintage(SILVER_POS_ROOT)
    as_of = date.fromisoformat(vintage["as_of"][:10]) if vintage and vintage.get("as_of") else None
    result = import_sales(args.dir, inventory_as_of=as_of)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result)
    return 0 if result["window"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

(`read_pos_vintage` is created in Task 0.7; run the two tasks together before executing this CLI.)

- [ ] **Step 6: Commit**

```bash
git add src/internal_pos/sales_importer.py tests/internal_pos/test_sales_importer.py scripts/import_yomyom_sales.py
git commit -m "Import sales as one row per product per month, with the evidence window

SPEC-004 FR-060b needs to know whether the evidence spans a full annual cycle
and rule 13 needs 'no row' kept distinct from 'zero'; a per-product velocity
table with a synthesised 7-day figure could express neither."
```

---

### Task 0.7: POS importer vintage; stop writing the sales table

**Files:**
- Modify: `src/internal_pos/pos_importer.py:50-60` (signature) and the `silver_tables` loop
- Modify: `configs/pos_schema_mapping.yaml` — remove the `sales` entry from `silver_tables`; correct the comment claiming negative stock is clamped
- Modify: `scripts/import_yomyom_pos.py` — add `--as-of YYYY-MM-DD`
- Test: `tests/internal_pos/test_pos_importer.py`

**Interfaces:**
- Produces: `import_pos_file(input_path, config_path=CONFIG_PATH, imported_at=None, as_of: str | None = None) -> dict` — `as_of` defaults to the file's mtime date (`YYYY-MM-DD`); written into every silver row as `_as_of`; and `read_pos_vintage(silver_dir) -> {"file": str, "as_of": str} | None` reading `yomyom_inventory.parquet`.
- Negative stock is preserved raw (already true; now documented and tested).

- [ ] **Step 1: Write the failing test**

```python
# tests/internal_pos/test_pos_importer.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyarrow.parquet as pq

import src.internal_pos.pos_importer as imp

HEADER = "קוד פריט ,ברקוד ,תאור פריט ,סוג פריט ,מלאי נוכחי ,מחיר קניה ,מחיר מכירה ,WOLT,שם מחלקה ,יחידת מידה ,שם מחלקה ,\n"


def test_import_preserves_negative_stock_and_records_vintage(tmp_path, monkeypatch):
    csv = tmp_path / "yomyom-inventory.csv"
    csv.write_text("﻿" + HEADER + "1,0012,מים,רגיל,-5,2.00,4.00,4.00,משקאות,יח',משקאות,\n", encoding="utf-8")
    silver = tmp_path / "silver"
    monkeypatch.setattr(imp, "SILVER_POS_DIR", silver)
    monkeypatch.setattr(imp, "QUALITY_REPORT_DIR", tmp_path / "q")
    result = imp.import_pos_file(csv, as_of="2026-08-02")
    assert result["status"] == "ok"
    inv = pq.read_table(silver / "yomyom_inventory.parquet").to_pylist()[0]
    assert inv["current_stock"] == -5
    assert inv["_as_of"] == "2026-08-02"
    assert not (silver / "yomyom_sales.parquet").exists()
    assert imp.read_pos_vintage(silver) == {"file": "yomyom-inventory.csv", "as_of": "2026-08-02"}


def test_missing_silver_has_no_vintage(tmp_path):
    assert imp.read_pos_vintage(tmp_path) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/internal_pos/test_pos_importer.py -q`
Expected: FAIL — `TypeError: unexpected keyword 'as_of'`

- [ ] **Step 3: Implement**

In `src/internal_pos/pos_importer.py`:

```python
from datetime import date, datetime, timezone   # replace the existing datetime import line

def import_pos_file(
    input_path: Path,
    config_path: Path = CONFIG_PATH,
    imported_at: str | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    imported_at = imported_at or datetime.now(timezone.utc).isoformat()
    # The POS vintage is the day the export was taken, not the day we imported it
    # (SPEC-007 FR-120). Default: the file's modification date.
    as_of = as_of or date.fromtimestamp(input_path.stat().st_mtime).isoformat()
    ...
```

In `_build_table_rows`, add a parameter `as_of: str` and set `subset["_as_of"] = as_of`; pass it from the loop. Add at the end of the module:

```python
def read_pos_vintage(silver_dir: Path = SILVER_POS_DIR) -> dict[str, Any] | None:
    path = silver_dir / "yomyom_inventory.parquet"
    if not path.exists():
        return None
    rows = pq.read_table(path, columns=["_source_file", "_as_of"]).slice(0, 1).to_pylist()
    if not rows:
        return None
    return {"file": rows[0].get("_source_file"), "as_of": rows[0].get("_as_of")}
```

In `configs/pos_schema_mapping.yaml`: delete the `sales:` block under `silver_tables:` (the `yomyom_sales.parquet` entry), and replace the comment block that says negative stock rows "are clamped to 0 during import" with:

```yaml
# Negative stock is PRESERVED as recorded. Nothing in the importer clamps it:
# SPEC-004 C-32 requires the lifecycle rule to see the raw value, and SPEC-002
# reports negative stock as a hygiene record with no money attached.
```

In `scripts/import_yomyom_pos.py`, add `parser.add_argument("--as-of", default=None, help="YYYY-MM-DD the export was taken (default: file mtime)")` and pass `as_of=args.as_of` to `import_pos_file`.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/internal_pos -q`
Expected: all pass (6)

- [ ] **Step 5: Commit**

```bash
git add src/internal_pos/pos_importer.py configs/pos_schema_mapping.yaml scripts/import_yomyom_pos.py tests/internal_pos/test_pos_importer.py
git commit -m "Record the POS export vintage and stop the POS importer rewriting the sales table

With --input, refresh_pipeline re-ran the POS importer and wiped the reconcile
columns, silently zeroing the stock-discrepancy signal. The sales tables now
have exactly one writer."
```

---

### Task 0.8: Barcode normalisation and per-store matches in the market chain

**Files:**
- Modify: `src/signals/competitor_product_signals.py` (`_map_alonit_row`, `_map_wolt_row`: normalise `barcode` via `norm_barcode`)
- Modify: `src/matching/product_matching.py:254-284` (`_dedup_competitors` → dedupe on `(barcode|external_product_key, competitor_store_id)`), `:370-395` (`_pass_barcode_exact` compares normalised barcodes), `load_internal_products` (normalise `barcode`)
- Test: `tests/matching/test_product_matching_norm.py`, `tests/signals/test_signal_barcodes.py`

**Interfaces:**
- Consumes: `src.engine.model.norm_barcode`.
- Produces: `product_matches.parquet` now holds one row per (internal barcode, competitor store) for barcode-exact matches; a new column `competitor_store_id`.

- [ ] **Step 1: Write the failing tests**

```python
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
```

```python
# tests/matching/test_product_matching_norm.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import polars as pl

from src.matching.product_matching import _dedup_competitors, _pass_barcode_exact


def test_dedup_keeps_one_row_per_store_not_per_product():
    df = pl.DataFrame({
        "barcode": ["1", "1", "2"], "external_product_key": ["1", "1", "2"],
        "competitor_store_id": ["s1", "s2", "s1"], "raw_product_name": ["a", "a", "b"],
        "normalized_product_name": ["a", "a", "b"], "brand": [None, None, None],
        "category": [None, None, None], "size": ["", "", ""], "unit": [None, None, None],
        "source_types": [["price_file"], ["delivery"], ["price_file"]],
    })
    rows = _dedup_competitors(df)
    assert sorted((r["barcode"], r["competitor_store_id"]) for r in rows) == [("1", "s1"), ("1", "s2"), ("2", "s1")]


def test_barcode_exact_ignores_leading_zeros():
    internal = [{"internal_product_id": "p1", "barcode": "0000123", "product_name": "x", "category": "c",
                 "brand": None, "size": "", "unit": None}]
    competitors = [{"barcode": "123", "external_product_key": "123", "competitor_store_id": "s1",
                    "raw_product_name": "x", "normalized_product_name": "x", "brand": None, "category": None,
                    "size": "", "unit": None, "source_types": ["price_file"]}]
    matches, unmatched = _pass_barcode_exact(internal, competitors, "2026-09-08T00:00:00+00:00")
    assert len(matches) == 1 and matches[0]["match_method"] == "barcode_exact"
    assert matches[0]["competitor_store_id"] == "s1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/signals tests/matching -q`
Expected: FAIL (barcode `0007290000041445` kept as-is; dedupe drops `("1","s2")`; `competitor_store_id` missing)

- [ ] **Step 3: Implement**

In `competitor_product_signals.py`, import `from src.engine.model import norm_barcode` and in both `_map_alonit_row` and `_map_wolt_row` set `"barcode": norm_barcode(_col(row, "barcode"))` (keep the raw value in `external_product_key` when barcode is empty).

In `product_matching.py`:

```python
from src.engine.model import norm_barcode

def _dedup_competitors(df: pl.DataFrame) -> list[dict]:
    """One row per (product key, store) — every store's price must survive to the
    reference step (SPEC-003 FR-044 needs the cheapest per format)."""
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for row in df.to_dicts():
        key = norm_barcode(row.get("barcode")) or row.get("external_product_key")
        if not key:
            continue
        store = str(row.get("competitor_store_id") or "")
        if (key, store) in seen:
            continue
        seen.add((key, store))
        row["barcode"] = norm_barcode(row.get("barcode"))
        deduped.append(row)
    logger.info("Competitor corpus: {} (product, store) rows (from {} signals)", len(deduped), len(df))
    return deduped
```

In `_pass_barcode_exact`, build the index as `by_barcode: dict[str, list[dict]]` keyed by `norm_barcode(c["barcode"])`, iterate all competitor rows for the internal product's normalised barcode, and emit one match per competitor row; in `_make_match` add `"competitor_store_id": competitor.get("competitor_store_id")` to the record and to the parquet schema. In `load_internal_products`, add a column `barcode_norm` = `norm_barcode(barcode)` and use it for the exact pass.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/signals tests/matching -q`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/signals/competitor_product_signals.py src/matching/product_matching.py tests/signals tests/matching
git commit -m "Normalise barcodes in the market chain and keep one match per competitor store

Zero-padded barcodes missed exact matches, and the global one-row-per-product
dedupe threw away every store's price but one — the balanced reference needs
the cheapest per format."
```

---

### Task 0.9: Store registry — client role and the unclassified venue

**Files:**
- Modify: `configs/store_types.yaml` (add `role: client` to `yomyom-kq-01` and `68e64a15ddc7ae17b6279458`; add `689d9d1ea1357c9968d6850f` Super Alonit Einat as `gas_convenience`, `verified: manual`, `basis: branch_known`)
- Modify: `src/common/store_types.py` — `StoreRecord.role: str = 'competitor'`; `StoreTypeConfig.client_store_ids() -> list[str]`; `StoreTypeConfig.context_only_stores(our_type) -> list[str]` (0 < affinity < floor)
- Test: `tests/test_store_types.py` (extend)

- [ ] **Step 1: Write the failing test** (append to `tests/test_store_types.py`)

```python
def test_client_stores_are_never_references():
    cfg = load_store_types()
    assert set(cfg.client_store_ids()) == {"yomyom-kq-01", "68e64a15ddc7ae17b6279458"}


def test_einat_venue_is_classified_same_format():
    cfg = load_store_types()
    assert cfg.store_type("689d9d1ea1357c9968d6850f") == "gas_convenience"


def test_context_only_and_comparable_partition_the_non_excluded():
    cfg = load_store_types()
    ctx = set(cfg.context_only_stores("gas_convenience"))
    comp = set(cfg.comparable_stores("gas_convenience"))
    assert ctx.isdisjoint(comp)
    assert "rami-levy-pt-01" in ctx and "dor-alon-kq-01" in comp
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_store_types.py -q`
Expected: FAIL — `AttributeError: client_store_ids`

- [ ] **Step 3: Implement**

`src/common/store_types.py`: add `role: str = "competitor"` to `StoreRecord` (read from the YAML key `role`, default `competitor`); add

```python
    def client_store_ids(self) -> list[str]:
        return sorted(s.store_id for s in self.stores.values() if s.role == "client")

    def context_only_stores(self, our_type: str) -> list[str]:
        floor = self.min_affinity
        return sorted(s.store_id for s in self.stores.values()
                      if 0.0 < self.affinity(our_type, s.store_type) < floor)
```

`configs/store_types.yaml`: add `role: client` under `yomyom-kq-01` and under `68e64a15ddc7ae17b6279458`; add:

```yaml
  689d9d1ea1357c9968d6850f:
    name: Super Alonit Einat (Wolt)
    store_type: gas_convenience
    verified: manual
    basis: branch_known
    notes: Dor Alon forecourt shop, the reference venue in delivery_targets.yaml; collected daily since 2026-08-11 but unclassified until 2026-09-08.
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_store_types.py -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add configs/store_types.yaml src/common/store_types.py tests/test_store_types.py
git commit -m "Mark the client's own venues and classify the Einat forecourt

D-5: the store's own price is never its own benchmark, so the registry must
know which observations are ours."
```

---

### Task 0.10: `EngineInputs` loader

**Files:**
- Create: `src/engine/inputs.py`
- Test: `tests/engine/test_inputs.py`

**Interfaces:**
- Consumes: `Policy`, `OwnerState`, `EvidenceWindow`, `norm_barcode`, `read_pos_vintage`, `load_store_types`.
- Produces:

```python
@dataclass
class EngineInputs:
    products: list[dict] | None      # barcode (normalised), product_name, department, shelf_price, delivery_price, cost_price, cost_source, recorded_stock, has_identifier
    sales_monthly: list[dict] | None
    sales_summary: dict[str, dict] | None   # by barcode
    window: EvidenceWindow | None
    observations: list[dict] | None  # barcode, price, store_id, store_format, affinity, observed_at, source_type — affinity-0 and client stores ALREADY removed
    matches: list[dict] | None
    stores: StoreTypeConfig
    withdrawn: set[str] | None
    vintages: dict
    owner: OwnerState
    policy: Policy
    run_at: datetime
```

- `load_inputs(*, policy, owner, run_at, silver_dir=SILVER_POS_ROOT, signals_dir=..., matches_path=..., stores=None) -> EngineInputs`
- Product shaping rules: `delivery_price = wolt_price if wolt_price > 0 else None`; `cost_price = owner answer if answered else (pos cost if > 0 else None)`, `cost_source ∈ {'owner','pos',None}`; `recorded_stock` raw float or `None`; `department` = `category`.

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_inputs.py
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pyarrow as pa
import pyarrow.parquet as pq

from src.engine.inputs import load_inputs
from src.engine.policy import load_policy
from src.owner_state.model import OwnerState


def _silver(tmp_path):
    silver = tmp_path / "silver"; silver.mkdir()
    prod = [{"barcode": "0012", "product_name": "מים", "category": "משקאות", "selling_price": 4.0, "wolt_price": 0.0,
             "cost_price": 0.0, "_source_file": "inv.csv", "_as_of": "2026-08-02"},
            {"barcode": None, "product_name": "אייס", "category": "c", "selling_price": 1.0, "wolt_price": 2.0,
             "cost_price": 0.5, "_source_file": "inv.csv", "_as_of": "2026-08-02"}]
    inv = [{"barcode": "0012", "current_stock": -5.0, "_source_file": "inv.csv", "_as_of": "2026-08-02"},
           {"barcode": None, "current_stock": 3.0, "_source_file": "inv.csv", "_as_of": "2026-08-02"}]
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "yomyom_inventory.parquet")
    pq.write_table(pa.Table.from_pylist(prod), silver / "yomyom_margins.parquet")
    return silver


def test_products_are_shaped_and_owner_cost_wins(tmp_path):
    silver = _silver(tmp_path)
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t",
                                  "answers": {"12": {"cost_price": {"value": 2.5, "at": 1, "status": "answered"}}}})
    inputs = load_inputs(policy=load_policy(), owner=owner, run_at=datetime(2026, 9, 8, tzinfo=timezone.utc),
                         silver_dir=silver, signals_dir=tmp_path / "nosignals", matches_path=tmp_path / "nomatches.parquet")
    p = {r["barcode"]: r for r in inputs.products}
    assert p["12"]["delivery_price"] is None          # zero Wolt price is absent, not zero
    assert p["12"]["cost_price"] == 2.5 and p["12"]["cost_source"] == "owner"
    assert p["12"]["recorded_stock"] == -5.0           # raw, never clamped
    assert p[None]["has_identifier"] is False
    assert inputs.sales_summary is None and inputs.window is None
    assert inputs.observations is None and inputs.matches is None
    assert inputs.vintages["pos"] == {"file": "inv.csv", "as_of": "2026-08-02"}
    assert inputs.vintages["owner_state"]["status"] == "available"


def test_missing_silver_yields_none_products(tmp_path):
    inputs = load_inputs(policy=load_policy(), owner=OwnerState.unavailable("x"),
                         run_at=datetime(2026, 9, 8, tzinfo=timezone.utc), silver_dir=tmp_path / "none",
                         signals_dir=tmp_path / "nosignals", matches_path=tmp_path / "nomatches.parquet")
    assert inputs.products is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/engine/test_inputs.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/engine/inputs.py
"""Everything a capability may read, loaded once per run (design.md §11.1)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import pyarrow.parquet as pq

from src.common.paths import MATCHING_ROOT, SIGNALS_ROOT, SILVER_POS_ROOT
from src.common.store_types import StoreTypeConfig, load_store_types
from src.engine.model import EvidenceWindow, norm_barcode
from src.engine.policy import Policy
from src.internal_pos.pos_importer import read_pos_vintage
from src.owner_state.model import OwnerState, answered_cost

OUR_FORMAT = "gas_convenience"


@dataclass
class EngineInputs:
    products: Optional[list]
    sales_monthly: Optional[list]
    sales_summary: Optional[dict]
    window: Optional[EvidenceWindow]
    observations: Optional[list]
    matches: Optional[list]
    stores: StoreTypeConfig
    withdrawn: Optional[set]
    vintages: dict
    owner: OwnerState
    policy: Policy
    run_at: datetime


def _rows(path: Path) -> Optional[list]:
    return pq.read_table(path).to_pylist() if path.exists() else None


def _pos(v) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None


def _num(v) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _shape_products(products, inventory, owner: OwnerState) -> list:
    stock = {}
    for r in inventory or []:
        stock[(norm_barcode(r.get("barcode")), r.get("product_name"))] = _num(r.get("current_stock"))
    out = []
    for r in products:
        barcode = norm_barcode(r.get("barcode"))
        owner_cost = answered_cost(owner, barcode) if barcode else None
        pos_cost = _pos(r.get("cost_price"))
        out.append({
            "barcode": barcode, "has_identifier": barcode is not None,
            "product_name": r.get("product_name"), "department": r.get("category"),
            "shelf_price": _pos(r.get("selling_price")), "delivery_price": _pos(r.get("wolt_price")),
            "cost_price": owner_cost if owner_cost is not None else pos_cost,
            "cost_source": "owner" if owner_cost is not None else ("pos" if pos_cost is not None else None),
            "recorded_stock": stock.get((barcode, r.get("product_name"))),
        })
    return sorted(out, key=lambda p: (p["barcode"] or "", p["product_name"] or ""))


def _window_from_summary(monthly, policy: Policy) -> Optional[EvidenceWindow]:
    from src.internal_pos.sales_importer import evidence_window
    months = sorted({r["month"] for r in monthly})
    return evidence_window(months, policy.full_annual_cycle_months) if months else None


def _shape_observations(signals, stores: StoreTypeConfig) -> Optional[list]:
    if signals is None:
        return None
    excluded = set(stores.excluded_stores(OUR_FORMAT)) | set(stores.client_store_ids())
    out = []
    for s in signals:
        store_id = str(s.get("competitor_store_id") or "")
        if store_id in excluded:
            continue                       # INV-020 / D-5: dropped before any capability sees it
        price = _pos(s.get("delivery_catalog_price")) or _pos(s.get("price_file_price"))
        if price is None or not s.get("barcode"):
            continue
        fmt = stores.store_type(store_id)
        out.append({"barcode": norm_barcode(s.get("barcode")), "price": price, "store_id": store_id,
                    "store_name": s.get("competitor_store_name"), "store_format": fmt,
                    "affinity": stores.affinity(OUR_FORMAT, fmt), "observed_at": s.get("observed_at"),
                    "source_type": "delivery" if _pos(s.get("delivery_catalog_price")) else "price_file"})
    return sorted(out, key=lambda o: (o["barcode"], o["store_id"], o["price"]))


def load_inputs(*, policy: Policy, owner: OwnerState, run_at: datetime, silver_dir: Path = SILVER_POS_ROOT,
                signals_dir: Path = SIGNALS_ROOT / "competitor_product_signals",
                matches_path: Path = MATCHING_ROOT / "product_matches.parquet",
                stores: Optional[StoreTypeConfig] = None) -> EngineInputs:
    stores = stores or load_store_types()
    products_raw = _rows(silver_dir / "yomyom_products.parquet")
    inventory = _rows(silver_dir / "yomyom_inventory.parquet")
    products = _shape_products(products_raw, inventory, owner) if products_raw else None
    monthly = _rows(silver_dir / "sales_monthly.parquet")
    summary_rows = _rows(silver_dir / "sales_summary.parquet")
    summary = {r["barcode"]: r for r in summary_rows} if summary_rows else None
    window = _window_from_summary(monthly, policy) if monthly else None
    latest_signal = sorted(signals_dir.glob("*.parquet")) if signals_dir.exists() else []
    signals = _rows(latest_signal[-1]) if latest_signal else None
    observations = _shape_observations(signals, stores)
    matches = _rows(matches_path)
    if matches:
        for m in matches:
            m["internal_barcode"] = norm_barcode(m.get("internal_barcode"))
    snapshot_date = None
    if observations:
        snapshot_date = max((o["observed_at"] or "")[:10] for o in observations) or None
    vintages = {
        "pos": read_pos_vintage(silver_dir) or {"file": None, "as_of": None},
        "sales": (window.to_dict() if window else {"months": [], "first": None, "last": None, "full_annual_cycle": False}),
        "competitor": {"snapshot_date": snapshot_date, "sources": sorted({o["store_id"] for o in observations or []})},
        "owner_state": {"pulled_at": owner.pulled_at, "status": owner.status},
    }
    vintages["sales"] = {k: vintages["sales"][k] for k in ("months", "first", "last", "full_annual_cycle")}
    return EngineInputs(products=products, sales_monthly=monthly, sales_summary=summary, window=window,
                        observations=observations, matches=matches, stores=stores, withdrawn=None,
                        vintages=vintages, owner=owner, policy=policy, run_at=run_at)
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/engine/test_inputs.py -q`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/engine/inputs.py tests/engine/test_inputs.py
git commit -m "Load EngineInputs once per run: shaped products, month evidence, format-gated observations

Absent tables are None, never empty; excluded and client stores are removed
before any capability can see them; an owner's cost answer beats the export."
```

---

### Task 0.11: Orchestrator, publisher wiring, CLI

**Files:**
- Create: `src/engine/run.py`
- Create: `scripts/run_engine.py`
- Modify: `package.json` — `"data:refresh": "python3 scripts/run_engine.py"`, add `"engine:print": "python3 scripts/run_engine.py --print"`
- Test: `tests/engine/test_run.py`

**Interfaces:**
- Produces: `run_engine(*, mode: str = 'publish', input_csv: Path | None = None, skip_market: bool = False, artefact_path: Path = ARTEFACT_PATH, capability_runners: dict | None = None, now: datetime | None = None) -> dict` returning `{"status": "ok"|"partial"|"degraded", "steps": [...], "artefact": dict | None, "published": bool}`.
- Step order: `owner_state_pull` → `pos_import` (only with `--input`) → `sales_import` → `market_context` (V2, kept) → `rehydrate_silver` → `competitor_signals` → `product_matching` → `load_inputs` → `capabilities` (each isolated) → `publish`.
- `capability_runners` maps capability id → `callable(inputs) -> CapabilityOutput`; default is the registry's modules (empty in this phase). A runner that raises is recorded as `error` and its capability published as `unavailable: capability_error`.
- Verdict: `partial` if any step `error`; `degraded` if owner state unavailable or any capability `unavailable` due to `capability_error`; else `ok`. Publish happens in `publish` mode unless every capability is unavailable (then `PublishRefused`, recorded, `partial`).

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_run.py
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

import src.engine.run as run_mod
from src.engine.model import CapabilityOutput
from src.owner_state.model import OwnerState


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: OwnerState.unavailable("no_credentials"))
    monkeypatch.setattr(run_mod, "_sales_import", lambda: {"window": None})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "SILVER_DIR", tmp_path / "silver")


def test_empty_capability_set_publishes_a_valid_artefact(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    target = tmp_path / "dashboard.json"
    result = run_mod.run_engine(mode="publish", artefact_path=target, capability_runners={},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result["published"] is True
    art = json.loads(target.read_text())
    assert art["schema_version"] == 2 and art["capabilities"] == {}
    assert result["status"] == "degraded"          # owner state unavailable is visible, not hidden


def test_a_raising_capability_is_unavailable_not_fatal(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    def boom(inputs): raise RuntimeError("bug")
    def fine(inputs): return CapabilityOutput(id="reconciliation", spec="SPEC-002", status="available")
    result = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json",
                                capability_runners={"price_consistency": boom, "reconciliation": fine},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    caps = result["artefact"]["capabilities"]
    assert caps["price_consistency"]["status"] == "unavailable"
    assert caps["price_consistency"]["unavailable_reason"] == "capability_error"
    assert caps["reconciliation"]["status"] == "available"
    assert any(s["step"] == "capability:price_consistency" and s["status"] == "error" for s in result["steps"])


def test_print_mode_writes_nothing(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    target = tmp_path / "dashboard.json"
    result = run_mod.run_engine(mode="print", artefact_path=target, capability_runners={},
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    assert result["published"] is False and not target.exists() and result["artefact"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/engine/test_run.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/engine/run.py
"""The one orchestrator (design.md §7.3, §9.1). Steps are isolated; the verdict is honest."""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from src.common.paths import SILVER_POS_ROOT
from src.engine.inputs import load_inputs
from src.engine.model import CapabilityOutput
from src.engine.policy import load_policy
from src.engine.publish import ARTEFACT_PATH, PublishRefused, build_artefact, validate_artefact, write_atomic
from src.engine.registry import CAPABILITIES
from src.owner_state.model import OwnerState
from src.owner_state.pull import MIRROR_PATH, pull, read_mirror, write_mirror

SILVER_DIR = SILVER_POS_ROOT
SALES_DIR = Path(__file__).resolve().parents[2] / "data" / "internal" / "raw_pos" / "yomyom" / "sales"

# Filled by Phase 1: capability id -> callable(inputs) -> CapabilityOutput
DEFAULT_RUNNERS: dict[str, Callable] = {}


def _pull_owner_state() -> OwnerState:
    project = os.environ.get("FIREBASE_PROJECT_ID") or os.environ.get("VITE_FIREBASE_PROJECT_ID") or ""
    store = os.environ.get("VITE_STORE_ID", "yomyom-kafr-qasim")
    cred_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON") or None
    cred_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH") or None
    if not (cred_json or cred_path):
        state = read_mirror(MIRROR_PATH)          # reproduction on a laptop: the committed replica, flagged
        state.reason = state.reason or "no_credentials"
        return state
    state = pull(project_id=project, store_id=store, credentials_json=cred_json, credentials_path=cred_path)
    if state.status == "available":
        write_mirror(state, MIRROR_PATH)
    return state


def _sales_import() -> dict:
    from datetime import date
    from src.internal_pos.pos_importer import read_pos_vintage
    from src.internal_pos.sales_importer import import_sales
    vintage = read_pos_vintage(SILVER_DIR)
    as_of = date.fromisoformat(vintage["as_of"][:10]) if vintage and vintage.get("as_of") else None
    return import_sales(SALES_DIR, inventory_as_of=as_of, silver_dir=SILVER_DIR)


def _market_chain(skip: bool) -> list:
    steps = []
    from src.context.build import write_market_context
    steps.append(("market_context", write_market_context))
    if not skip:
        from scripts.rehydrate_silver import rehydrate
        from src.signals.competitor_product_signals import build_competitor_product_signals
        from src.matching.product_matching import run_product_matching
        steps += [("rehydrate_silver", rehydrate), ("competitor_signals", build_competitor_product_signals),
                  ("product_matching", run_product_matching)]
    return steps


def _step(steps: list, name: str, fn: Callable):
    t0 = time.monotonic()
    try:
        result = fn()
        steps.append({"step": name, "status": "ok", "ms": int((time.monotonic() - t0) * 1000), "error": None})
        return result
    except Exception as exc:  # noqa: BLE001 — isolate, record, continue
        steps.append({"step": name, "status": "error", "ms": int((time.monotonic() - t0) * 1000),
                      "error": f"{type(exc).__name__}: {exc}"})
        return None


def run_engine(*, mode: str = "publish", input_csv: Optional[Path] = None, skip_market: bool = False,
               artefact_path: Path = ARTEFACT_PATH, capability_runners: Optional[dict] = None,
               now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    runners = DEFAULT_RUNNERS if capability_runners is None else capability_runners
    steps: list = []
    policy = load_policy()

    owner = _step(steps, "owner_state_pull", _pull_owner_state) or OwnerState.unavailable("pull_step_failed")
    if input_csv:
        from src.internal_pos.pos_importer import import_pos_file
        _step(steps, "pos_import", lambda: import_pos_file(Path(input_csv)))
    _step(steps, "sales_import", _sales_import)
    for name, fn in _market_chain(skip_market):
        _step(steps, name, fn)

    inputs = _step(steps, "load_inputs", lambda: load_inputs(policy=policy, owner=owner, run_at=now, silver_dir=SILVER_DIR))
    outputs: list[CapabilityOutput] = []
    catalogue = questions = None
    if inputs is not None:
        # catalogue_lifecycle runs first so its withdrawn set reaches the others (FR-074).
        order = ["catalogue_lifecycle"] + [c for c in runners if c != "catalogue_lifecycle"]
        for cap_id in order:
            if cap_id not in runners:
                continue
            spec = CAPABILITIES[cap_id].spec
            out = _step(steps, f"capability:{cap_id}", lambda cap_id=cap_id: runners[cap_id](#inputs))
            if out is None:
                out = CapabilityOutput.unavailable(cap_id, spec, "capability_error")
            outputs.append(out)
            if cap_id == "catalogue_lifecycle" and out.status == "available":
                inputs.withdrawn = set(out.counts.get("_withdrawn_barcodes", []) or [])
                catalogue = getattr(out, "catalogue", None)
            if cap_id == "owner_questions":
                questions = getattr(out, "questions", None)

    status = "ok"
    if any(s["status"] == "error" for s in steps):
        status = "partial"
    elif owner.status != "available" or any(o.unavailable_reason == "capability_error" for o in outputs):
        status = "degraded"

    artefact = build_artefact(outputs, vintages=inputs.vintages if inputs else _no_inputs_vintages(owner),
                              thresholds=policy.as_dict(), run={"status": status, "steps": steps},
                              catalogue=catalogue, questions=questions, generated_at=now.isoformat(),
                              run_id=uuid.uuid4().hex[:12])
    published = False
    if mode == "publish":
        try:
            if outputs and all(o.status == "unavailable" for o in outputs):
                raise PublishRefused("every capability is unavailable — refusing to overwrite the last good artefact")
            write_atomic(artefact_path, artefact)
            published = True
        except PublishRefused as exc:
            steps.append({"step": "publish", "status": "error", "ms": 0, "error": str(exc)})
            status = "partial"
    else:
        validate_artefact(artefact)
    artefact["run"]["status"] = status
    return {"status": status, "steps": steps, "artefact": artefact, "published": published}


def _no_inputs_vintages(owner: OwnerState) -> dict:
    return {"pos": {"file": None, "as_of": None},
            "sales": {"months": [], "first": None, "last": None, "full_annual_cycle": False},
            "competitor": {"snapshot_date": None, "sources": []},
            "owner_state": {"pulled_at": owner.pulled_at, "status": owner.status}}
```

```python
# scripts/run_engine.py
"""One command to refresh every dashboard input and publish the artefact.

  python3 scripts/run_engine.py                     # npm run data:refresh
  python3 scripts/run_engine.py --input <pos.csv>   # import a new export first
  python3 scripts/run_engine.py --skip-market       # POS-only refresh
  python3 scripts/run_engine.py --print             # run everything, write nothing (reproduction)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.engine.run import run_engine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None)
    parser.add_argument("--skip-market", action="store_true")
    parser.add_argument("--print", dest="print_mode", action="store_true")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()
    result = run_engine(mode="print" if args.print_mode else "publish",
                        input_csv=Path(args.input) if args.input else None, skip_market=args.skip_market)
    summary = {"status": result["status"], "published": result["published"], "steps": result["steps"]}
    payload = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and the CLI in print mode**

Run: `.venv/bin/python -m pytest tests/engine/test_run.py -q` → 3 passed
Run: `.venv/bin/python scripts/run_engine.py --print --skip-market | tail -5` → prints a summary; exit code may be 1 (`degraded`, no credentials) — that is the honest state.

- [ ] **Step 5: Commit**

```bash
git add src/engine/run.py scripts/run_engine.py package.json tests/engine/test_run.py
git commit -m "Add the engine orchestrator: fixed step order, isolated steps, honest verdict, one publish

Replaces refresh_pipeline.py's ordering (the sales importer now runs inside the
chain, never after a POS import wipes its work). An unreachable owner state
makes the run 'degraded' and visible instead of silently empty."
```

---

### Task 0.12: CI on push and pull request

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the workflow**

```yaml
# ci.yml — tests run before a merge, for the first time (design.md ADR-013).
name: ci

on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: npm }
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: pip }
      - run: npm ci
      - run: pip install -r requirements.txt
      - name: Lint
        run: npm run lint
      - name: JS unit and component tests
        run: npx vitest run
      - name: Python tests
        run: python3 -m pytest tests -q
      - name: Build
        run: npm run build
      - name: Artefact contract (schema validates the committed artefact when present)
        run: |
          if [ -f public/data/dashboard.json ]; then
            python3 -c "import json,sys; sys.path.insert(0,'.'); from src.engine.publish import validate_artefact; validate_artefact(json.load(open('public/data/dashboard.json'))); print('artefact valid')"
          else
            echo "no dashboard.json yet"
          fi
```

- [ ] **Step 2: Verify locally that each command passes**

Run: `npm run lint && npx vitest run && .venv/bin/python -m pytest tests -q && npm run build`
Expected: all green

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "Run lint, both test suites, the build and the artefact contract on every push and PR"
```

---

### Task 0.13: Prerequisite checkpoint 0-A — Firebase end to end

**Files:** none in git (`.env` is ignored). This task verifies the operational prerequisites in the index.

- [ ] **Step 1: Config values present**

Run: `npm run check:firebase`
Expected: exit 0 — all six `VITE_FIREBASE_*` set, `VITE_STORE_ID` matches `firestore.rules`.

- [ ] **Step 2: Anonymous sign-in and rules**

Run: `npm run check:firebase-live`
Expected: `STEP 1 anonymous sign-in : ✅` and `STEP 2 write + read back : ✅`.

- [ ] **Step 3: The engine can pull with the service account**

Run (with the service-account path exported): `FIREBASE_SERVICE_ACCOUNT_PATH=./secrets/firebase-service-account.json .venv/bin/python -c "import sys; sys.path.insert(0,'.'); from src.engine.run import _pull_owner_state; s=_pull_owner_state(); print(s.status, s.reason, s.pulled_at)"`
Expected: `available None 2026-…` and `data/owner/owner_state.json` written.

- [ ] **Step 4: CI secret present**

Run: `gh secret list | grep FIREBASE_SERVICE_ACCOUNT_JSON`
Expected: one line. Then add to `collect-daily.yml` (Phase 3 finalises this workflow) the env for the refresh step:

```yaml
        env:
          FIREBASE_SERVICE_ACCOUNT_JSON: ${{ secrets.FIREBASE_SERVICE_ACCOUNT_JSON }}
          FIREBASE_PROJECT_ID: hackathon26-a6ebd
          VITE_STORE_ID: yomyom-kafr-qasim
```

- [ ] **Step 5: Checkpoint 0-B**

Run: `.venv/bin/python scripts/run_engine.py --skip-market`
Expected: `public/data/dashboard.json` written, `schema_version: 2`, `capabilities: {}`, `run.status: ok` (or `degraded` with `owner_state.status: unavailable` if Step 3 was skipped). Commit nothing from `public/data` yet — the artefact is committed by CI from Phase 3 on.
