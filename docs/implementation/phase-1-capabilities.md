# V1 Phase 1 — Capabilities Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the seven registered capabilities across six modules, the surface producer and provenance so that a run publishes every V1 signal — each as a pure function of `EngineInputs`, each passing its SPEC's acceptance criteria as named tests. SPEC-002 produces two capabilities (`reconciliation` and `hygiene`), which is why capabilities outnumber modules (ADR-014).

**Architecture:** Every capability is a `callable(inputs: EngineInputs) -> CapabilityOutput` under `src/engine/`; a module may provide two of them (`reconciliation.run` and `reconciliation.run_hygiene`), and each is stepped separately so one can be unavailable while the other keeps emitting. No module reads a file or a clock. No module sets its own `status`: it calls `registry.derive_status`, which computes it from the capability's `requires` against the inputs that landed (ADR-014). `catalogue_lifecycle` runs first and hands its withdrawn/idle sets to the others through `inputs`. `surface_candidates.stamp()` marks admission conditions after all capabilities ran; `publish` asserts money policy, registry completeness and schema.

**Tech Stack:** Python 3.9+ run as `python3` (no virtualenv — CLAUDE.md rule 2), pyarrow (inputs only), pytest.

**Spec:** [`docs/architecture/system-design.md`](../architecture/system-design.md) §7.3, §9.6, §10.1–10.2, §14, §21 (per-spec matrices); the feature specs SPEC-001…SPEC-005 acceptance criteria.

## Global Constraints

See [`2026-09-08-v1-00-index.md`](plan.md). Additionally:

- Tests are named after acceptance criteria: `test_ac_021_no_money_on_flagged_products`. The matrix in `docs/architecture/system-design.md` §21 is the index of what must exist.
- Tasks 1.1, 1.2, 1.3→1.4, 1.5 and 1.6–1.7 are independent once Phase 0 is merged; two people can work them in parallel. Task 1.8 wires everything and needs all of them; Task 1.9 is the boundary probe and needs 1.8.
- Every entry carries a `signal_family` from the frozen enumeration in `model.py` and its `id` is `entry_id(family, barcode, variant)`. The capability id is never part of an entry id (ADR-009).
- Shared test helper: `tests/engine/helpers.py::make_inputs(**overrides)` builds an `EngineInputs` from plain lists so tests never touch parquet.

## File structure (this phase)

| File | Responsibility |
|---|---|
| `tests/engine/helpers.py` | `make_inputs`, `product(...)`, `summary(...)`, `observation(...)`, `match(...)` factories |
| `src/engine/reconciliation.py` | SPEC-002 — two capabilities: `run` (detection) and `run_hygiene` |
| `src/engine/price_consistency.py` | SPEC-001 four states + ceiling derivation |
| `src/engine/catalogue_lifecycle.py` | SPEC-004 classification, withdrawal, idle ranking, implausible questions |
| `src/engine/owner_questions.py` | SPEC-005 cost questions, suppression, ordering |
| `src/engine/competitor_position.py` | SPEC-003 reference, allowance, cost floor, policy, coverage, position |
| `src/engine/margin_below_cost.py` | unspecified; browse-only |
| `src/engine/surface_candidates.py` | FR-103 (1)(2)(4) stamping; `value_kinds_present` |
| `src/engine/provenance.py` | `figure()` helper, `counts_as_figures()` |
| `src/engine/run.py` | `DEFAULT_RUNNERS`, idle/withdrawn hand-off, stamping before publish |
| `scripts/check_independence.py` | the rule-12 boundary probe: reconciliation unavailable, hygiene unaffected |

---

### Task 1.0: Test helpers

**Files:**
- Create: `tests/engine/helpers.py`

**Interfaces:**
- Produces: `make_inputs(products=None, inventory=<present iff products>, sales_summary=None, sales_monthly=None, window=None, observations=None, matches=None, withdrawn=None, idle=None, owner=None, policy=None, run_at=None) -> EngineInputs`; factories `product(barcode, **kw)`, `summary(barcode, **kw)`, `observation(barcode, price, store_id, store_format, affinity, observed_at='2026-09-08T00:00:00Z', source_type='price_file')`, `match(internal_barcode, external_barcode, store_id, method='barcode_exact', confidence=1.0)`; `window_of(months: list[str], full=False) -> EvidenceWindow`.

- [ ] **Step 1: Write the helper**

```python
# tests/engine/helpers.py
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.store_types import load_store_types
from src.engine.inputs import EngineInputs
from src.engine.model import EvidenceWindow
from src.engine.policy import load_policy
from src.owner_state.model import OwnerState

RUN_AT = datetime(2026, 9, 8, 6, 0, tzinfo=timezone.utc)


def product(barcode, *, name="p", department="d", shelf=None, delivery=None, cost=None, cost_source=None, stock=None):
    return {"barcode": barcode, "has_identifier": barcode is not None, "product_name": name, "department": department,
            "shelf_price": shelf, "delivery_price": delivery, "cost_price": cost,
            "cost_source": cost_source or ("pos" if cost is not None else None), "recorded_stock": stock}


def summary(barcode, *, units=0.0, receipts=0.0, months=1, last=None, observed_zero=False,
            reconcile_units=None, reconcile_receipts=None, reconcile_months=None, name="p"):
    return {"barcode": barcode, "product_name": name, "months_present": months, "units_total": units,
            "receipts_total": receipts, "last_month_with_units": last, "observed_zero": observed_zero,
            "reconcile_units": units if reconcile_units is None else reconcile_units,
            "reconcile_receipts": receipts if reconcile_receipts is None else reconcile_receipts,
            "reconcile_months": months if reconcile_months is None else reconcile_months}


def observation(barcode, price, store_id, store_format, affinity, observed_at="2026-09-08T00:00:00Z",
                source_type="price_file", store_name=None):
    return {"barcode": barcode, "price": price, "store_id": store_id, "store_name": store_name or store_id,
            "store_format": store_format, "affinity": affinity, "observed_at": observed_at, "source_type": source_type}


def match(internal_barcode, external_barcode, store_id, method="barcode_exact", confidence=1.0):
    return {"internal_barcode": internal_barcode, "external_barcode": external_barcode,
            "competitor_store_id": store_id, "match_method": method, "match_confidence": confidence, "approved": True}


def window_of(months, full=False):
    return EvidenceWindow(months=list(months), first=months[0], last=months[-1], count=len(months), full_annual_cycle=full)


def make_inputs(**kw):
    owner = kw.get("owner") or OwnerState.from_dict({"status": "available", "pulled_at": "t"})
    sales_summary = kw.get("sales_summary")
    return EngineInputs(
        products=kw.get("products"),
        # inventory defaults to present whenever products are: a test that says nothing about
        # the stock table is not a test about the stock table being absent.
        inventory=kw.get("inventory", [] if kw.get("products") is not None else None),
        sales_monthly=kw.get("sales_monthly"),
        sales_summary={s["barcode"]: s for s in sales_summary} if sales_summary is not None else None,
        window=kw.get("window"), observations=kw.get("observations"), matches=kw.get("matches"),
        stores=load_store_types(), withdrawn=kw.get("withdrawn"), idle=kw.get("idle"),
        vintages={"pos": {"file": "f", "as_of": "2026-08-02"},
                  "sales": {"months": [], "first": None, "last": None, "full_annual_cycle": False},
                  "competitor": {"snapshot_date": "2026-09-08", "sources": []},
                  "owner_state": {"pulled_at": owner.pulled_at, "status": owner.status}},
        owner=owner, policy=kw.get("policy") or load_policy(), run_at=kw.get("run_at") or RUN_AT)
```

- [ ] **Step 2: Add `idle` to `EngineInputs`**

In `src/engine/inputs.py`, add the field `idle: Optional[set]` after `withdrawn`, and pass `idle=None` in `load_inputs`. (`inventory` was added in Task 0.10.) Run `python3 -m pytest tests/engine -q` → still green.

- [ ] **Step 3: Commit**

```bash
git add tests/engine/helpers.py src/engine/inputs.py
git commit -m "Add engine test factories and the idle hand-off field"
```

---

### Task 1.1: Reconciliation and hygiene — two capabilities from one module (SPEC-002)

**Files:**
- Create: `src/engine/reconciliation.py`
- Test: `tests/engine/test_reconciliation.py`

**Interfaces:**
- Consumes: `EngineInputs.products`, `.sales_summary`, `.window`, `.withdrawn`.
- Produces **two capabilities from one module** (ADR-014), each with its own entry point so the orchestrator steps, isolates and reports them separately:
  - `run(inputs) -> CapabilityOutput` — `id='reconciliation'`, `requires=('products','sales_summary','window')`; entries `characterisation='inconsistent'`, family `recon.impossible_opening`, action `count_product`, ordering `gap_ratio`; `counts: {flagged}`.
  - `run_hygiene(inputs) -> CapabilityOutput` — `id='hygiene'`, `requires=('products',)`; entries `characterisation='hygiene'`, families `hygiene.negative_stock` / `hygiene.no_identifier` / `hygiene.absent_price`, action `fix_record`, ordering `hygiene_order`; `counts: {negative_stock, no_identifier, absent_price}`.
- Neither sets its own status; both call `registry.derive_status`. That is what makes SPEC-002 §11 — the reports do not arrive, detection is unavailable, hygiene is unaffected — a computed consequence instead of a sentence someone remembered to write. The old `notes: ['detection_unavailable:no_sales_evidence']` and `counts.flagged = None` are gone: the state they described is now the capability's own `status`.
- Neither ever attaches money (D-1, FR-023, INV-010, INV-013).

- [ ] **Step 1: Write the failing tests**

```python
# tests/engine/test_reconciliation.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product, summary, window_of
from src.engine.model import entry_id
from src.engine.reconciliation import run, run_hygiene

W = window_of(["2026-01", "2026-02"])


def test_ac_020_detection_flags_negative_implied_opening_and_orders_by_gap_ratio():
    inputs = make_inputs(
        products=[product("1", stock=10.0), product("2", stock=-716.0), product("3", stock=5.0), product("4", stock=-3.0)],
        sales_summary=[summary("1", units=5, receipts=100),            # implied 105 → consistent
                       summary("2", units=663, receipts=62),           # implied -115 → flagged, ratio 1.85
                       summary("3", units=50, receipts=10),            # implied 45 → consistent
                       summary("4", units=0, receipts=0)],             # no receipts → never flagged
        window=W)
    out = run(inputs)
    assert [e.barcode for e in out.entries] == ["2"]
    assert out.entries[0].ordering_key == {"name": "gap_ratio", "value": round(115 / 62, 4)}
    assert out.counts["flagged"] == 1


def test_ac_020_ordering_is_by_gap_ratio_descending():
    inputs = make_inputs(
        products=[product("a", stock=0.0), product("b", stock=0.0)],
        sales_summary=[summary("a", units=20, receipts=10), summary("b", units=200, receipts=10)], window=W)
    assert [e.barcode for e in run(inputs).entries] == ["b", "a"]


def test_ac_021_ac_022_no_money_anywhere():
    inputs = make_inputs(products=[product("2", stock=1533.0, cost=3.15)],
                         sales_summary=[summary("2", units=5000, receipts=200)], window=W)
    out = run(inputs)
    assert all(e.value is None for e in out.entries)
    assert all(isinstance(v, (int, type(None))) for v in out.counts.values())
    assert "cost_price" not in out.entries[0].evidence
    assert all(e.value is None for e in run_hygiene(inputs).entries)


def test_ac_024_evidence_carries_the_three_quantities():
    inputs = make_inputs(products=[product("2", stock=-716.0)],
                         sales_summary=[summary("2", units=663, receipts=62, months=2)], window=W)
    e = run(inputs).entries[0]
    assert e.evidence["recorded_stock"] == -716.0 and e.evidence["receipts"] == 62 and e.evidence["units_sold"] == 663
    assert e.evidence["unaccounted"] == 115 and e.evidence["window_id"] == "2026-01..2026-02"
    assert e.action == "count_product"


def test_ac_025_hygiene_records_without_money_and_with_reasons():
    inputs = make_inputs(products=[product("9", stock=-1.0, shelf=2.0), product(None, name="אייס", shelf=1.0),
                                   product("8", stock=0.0, shelf=None)], sales_summary=[], window=W)
    out = run_hygiene(inputs)
    hyg = {(e.barcode, e.evidence["reason"]) for e in out.entries}
    assert hyg == {("9", "negative_stock"), (None, "no_identifier"), ("8", "absent_price")}
    assert out.counts == {"negative_stock": 1, "no_identifier": 1, "absent_price": 1}
    assert all(e.action == "fix_record" for e in out.entries)


def test_spec_002_s11_detection_unavailable_leaves_hygiene_untouched():
    """The rule the split exists for (AC-107). The inventory CSV always arrives; the seven
    monthly reports may not. Detection cannot close its arithmetic without receipts, and
    says so; a negative stock figure is still wrong on its own evidence."""
    inputs = make_inputs(products=[product("9", stock=-1.0, shelf=2.0)], sales_summary=None, window=None)
    detection, hygiene = run(inputs), run_hygiene(inputs)
    assert detection.status == "unavailable" and detection.unavailable_reason == "no_sales_evidence"
    assert detection.entries == []
    assert hygiene.status == "available" and hygiene.counts["negative_stock"] == 1
    assert len(hygiene.entries) == 1


def test_withdrawn_products_are_excluded_from_hygiene_counts():
    inputs = make_inputs(products=[product("8", stock=0.0, shelf=None)], sales_summary=[], window=W, withdrawn={"8"})
    assert run_hygiene(inputs).counts["absent_price"] == 0


def test_entry_ids_are_keyed_on_the_signal_family_not_the_capability():
    """ADR-009. These ids key the owner's outcomes in Firestore; hygiene moving out of
    reconciliation must not have changed a single one of them."""
    inputs = make_inputs(products=[product("9", stock=-1.0, shelf=2.0)], sales_summary=[], window=W)
    e = run_hygiene(inputs).entries[0]
    assert e.signal_family == "hygiene.negative_stock"
    assert e.id == entry_id("hygiene.negative_stock", "9")


def test_no_pos_data_makes_both_unavailable():
    assert run(make_inputs(products=None)).status == "unavailable"
    assert run_hygiene(make_inputs(products=None)).unavailable_reason == "no_pos_data"


def test_a_missing_stock_table_makes_hygiene_unavailable_not_zero():
    """Without the inventory table every product shapes with recorded_stock None, and a
    count of negative-stock records would come out 0. Zero is a finding; this is an absence
    (ARCH-DRIVER-002, INV-057). `inventory` is in hygiene's requires so the run says so."""
    out = run_hygiene(make_inputs(products=[product("9", shelf=2.0)], inventory=None))
    assert out.status == "unavailable" and out.unavailable_reason == "no_inventory_data"
    assert out.counts == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/engine/test_reconciliation.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/engine/reconciliation.py
"""SPEC-002 — two capabilities, one module.

`reconciliation` needs the monthly reports to close the arithmetic:

    implied_opening = recorded_stock − receipts + units_sold

A negative implied opening is arithmetically impossible, so the three numbers cannot all
be true. `hygiene` needs only the inventory: negative stock, no usable barcode or an
absent price is wrong on its own evidence.

They are two capabilities because they fail on different days — the inventory CSV always
arrives, the seven monthly reports may not (ADR-014, SPEC-002 §11). Neither attaches money
(FR-023, INV-010, INV-013); the ordering key is the gap ratio (FR-024)."""
from __future__ import annotations

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, entry_id
from src.engine.registry import derive_status

SPEC = "SPEC-002"
RECON, HYGIENE = "reconciliation", "hygiene"
HYGIENE_ORDER = {"negative_stock": 0, "no_identifier": 1, "absent_price": 2}


def _hygiene_entries(inputs: EngineInputs) -> list:
    withdrawn = inputs.withdrawn or set()
    out = []
    for p in inputs.products:
        if p["barcode"] in withdrawn:
            continue
        reasons = []
        if p["recorded_stock"] is not None and p["recorded_stock"] < 0:
            reasons.append("negative_stock")
        if not p["has_identifier"]:
            reasons.append("no_identifier")
        if p["shelf_price"] is None:
            reasons.append("absent_price")
        for reason in reasons:
            family = f"hygiene.{reason}"
            out.append(Entry(
                id=entry_id(family, p["barcode"] or p["product_name"]), signal_family=family,
                capability=HYGIENE, barcode=p["barcode"], product_name=p["product_name"],
                department=p["department"], action="fix_record", characterisation="hygiene",
                evidence={"reason": reason,
                          "recorded_stock": p["recorded_stock"] if reason == "negative_stock" else None},
                value=None, ordering_key={"name": "hygiene_order", "value": HYGIENE_ORDER[reason]}))
    return sorted(out, key=lambda e: (e.ordering_key["value"], e.product_name or "", e.barcode or ""))


def _detection_entries(inputs: EngineInputs) -> list:
    withdrawn = inputs.withdrawn or set()
    out = []
    for p in inputs.products:
        b = p["barcode"]
        if not b or b in withdrawn or p["recorded_stock"] is None:
            continue
        s = inputs.sales_summary.get(b)
        receipts = float(s["reconcile_receipts"]) if s else 0.0
        if receipts <= 0:
            continue                                     # FR-021: nothing to close without receipts
        units = float(s["reconcile_units"])
        implied = p["recorded_stock"] - receipts + units
        if implied >= 0:
            continue
        missing = -implied
        out.append(Entry(
            id=entry_id("recon.impossible_opening", b), signal_family="recon.impossible_opening",
            capability=RECON, barcode=b, product_name=p["product_name"],
            department=p["department"], action="count_product", characterisation="inconsistent",
            evidence={"recorded_stock": p["recorded_stock"], "receipts": receipts, "units_sold": units,
                      "unaccounted": round(missing, 2), "window_id": inputs.window.window_id,
                      "reconcile_months": int(s["reconcile_months"])},
            value=None, ordering_key={"name": "gap_ratio", "value": round(missing / receipts, 4)}))
    return sorted(out, key=lambda e: (-e.ordering_key["value"], e.barcode))


def run(inputs: EngineInputs) -> CapabilityOutput:
    """The detection half. Unavailable without receipts — never 'available with zero'."""
    status, reason = derive_status(RECON, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(RECON, SPEC, reason)
    flagged = _detection_entries(inputs)
    return CapabilityOutput(
        id=RECON, spec=SPEC, status="available", window=inputs.window,
        thresholds={}, counts={"flagged": len(flagged)}, entries=flagged,
        figures=[Figure("flagged", len(flagged), "products", ["pos", "sales"],
                        {"window": inputs.window.window_id})])


def run_hygiene(inputs: EngineInputs) -> CapabilityOutput:
    """The hygiene half. Depends on the inventory alone, so it survives a missing report."""
    status, reason = derive_status(HYGIENE, inputs)
    if status == "unavailable":
        return CapabilityOutput.unavailable(HYGIENE, SPEC, reason)
    entries = _hygiene_entries(inputs)
    counts = {reason_name: sum(1 for e in entries if e.evidence["reason"] == reason_name)
              for reason_name in HYGIENE_ORDER}
    return CapabilityOutput(
        id=HYGIENE, spec=SPEC, status="available",
        thresholds={}, counts=counts, entries=entries,
        figures=[Figure(name, counts[name], "records", ["pos"]) for name in HYGIENE_ORDER])
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/engine/test_reconciliation.py -q`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add src/engine/reconciliation.py tests/engine/test_reconciliation.py
git commit -m "Split SPEC-002 into two capabilities that fail on different days

The arithmetic is unchanged from operational_recommendations.py and the cost
price no longer travels with the row, so nothing downstream can price a quantity.
What changed is the shape: detection needs the monthly reports, hygiene needs only
the inventory, so hygiene is its own capability with its own status (ADR-014).
Neither declares that status — derive_status computes it from requires, which is
why 'reports missing, hygiene unaffected' cannot be got wrong by declaration."
```

---

### Task 1.2: Delivery-platform price consistency (SPEC-001)

**Files:**
- Create: `src/engine/price_consistency.py`
- Test: `tests/engine/test_price_consistency.py`

**Interfaces:**
- Produces: `derive_ceiling(markups: list[float], *, band_pct, drop_ratio, min_band_count) -> CeilingResult(pct: float | None, method: str, bands: list[dict])`; `classify(shelf, delivery, ceiling_pct) -> 'identical'|'inverted'|'within'|'above'|'undetermined'`; `run(inputs) -> CapabilityOutput` with `id='price_consistency'`, entries `confirmed_loss` (inverted; value per_sale; action `verify_price`; ordering `loss_per_sale`) and `question` (above; no value; ordering `markup_pct`), `thresholds: {ceiling_pct, ceiling_method, ceiling_bands}`, `counts: {population, identical, within, above (None when undetermined), inverted, excluded_artefact, excluded_gap}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/engine/test_price_consistency.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product
from src.engine.price_consistency import classify, derive_ceiling, run

P = dict(band_pct=2, drop_ratio=0.75, min_band_count=20)


def _dist():
    # 81 in 16–18, 8 in 18–20, then a small tail: the pilot's shape
    return [1.0] * 30 + [5.0] * 40 + [10.0] * 60 + [15.0] * 50 + [17.0] * 81 + [19.0] * 8 + [25.0] * 5 + [40.0] * 3


def test_ceiling_is_the_last_density_collapse():
    r = derive_ceiling(_dist(), **P)
    assert r.pct == 18.0 and r.method == "last_density_collapse"
    assert any(b["from"] == 16.0 and b["count"] == 81 for b in r.bands)


def test_ceiling_undetermined_on_a_flat_distribution():
    assert derive_ceiling([float(x) for x in range(0, 60)] * 2, **P).pct is None


def test_ceiling_undetermined_when_the_collapse_band_is_too_small():
    assert derive_ceiling([1.0] * 10 + [3.0] * 1, **P).pct is None


def test_classify_states():
    assert classify(10.0, 10.0, 18.0) == "identical"
    assert classify(10.0, 9.0, 18.0) == "inverted"
    assert classify(10.0, 11.0, 18.0) == "within"
    assert classify(10.0, 13.0, 18.0) == "above"
    assert classify(10.0, 13.0, None) == "undetermined"


def _inputs(extra=None):
    prods = [product(str(i), shelf=10.0, delivery=10.0) for i in range(100)]            # identical
    prods += [product(f"w{i}", shelf=10.0, delivery=11.0) for i in range(81)]           # 10 % markup
    prods += [product(f"x{i}", shelf=10.0, delivery=11.7) for i in range(81)]           # 17 %
    prods += [product(f"y{i}", shelf=10.0, delivery=11.9) for i in range(8)]            # 19 %  → above
    prods += [product("inv", shelf=37.9, delivery=21.9, cost=20.0)]                     # inverted
    prods += [product("art", shelf=0.01, delivery=0.02, cost=2.28)]                     # D-4 artefact
    prods += [product("nod", shelf=5.0, delivery=None)]                                 # no delivery price
    return make_inputs(products=prods + (extra or []))


def test_ac_001_identical_never_surfaces_and_ac_002_states_are_distinguishable():
    out = run(_inputs())
    ids = {e.barcode for e in out.entries}
    assert "0" not in ids and out.counts["identical"] == 100
    kinds = {e.barcode: e.characterisation for e in out.entries}
    assert kinds["inv"] == "confirmed_loss" and kinds["y0"] == "question"


def test_ac_003_above_ceiling_is_never_a_loss_and_carries_no_value():
    out = run(_inputs())
    above = [e for e in out.entries if e.characterisation == "question"]
    assert above and all(e.value is None for e in above)


def test_ac_004_ceiling_reported_with_counts():
    out = run(_inputs())
    assert out.thresholds["ceiling_pct"] == 18.0
    assert out.counts["above"] == 8 and out.counts["inverted"] == 1


def test_inverted_carries_a_recurring_confirmed_value_and_evidence():
    e = next(e for e in run(_inputs()).entries if e.barcode == "inv")
    assert e.value.kind == "per_sale" and e.value.certainty == "confirmed" and e.value.amount == 16.0
    assert e.evidence["shelf_price"] == 37.9 and e.evidence["delivery_price"] == 21.9 and e.evidence["commission_compounds"] is True
    assert e.action == "verify_price"


def test_ac_005_undetermined_ceiling_suppresses_above_keeps_inverted():
    prods = [product(f"f{i}", shelf=10.0, delivery=10.0 + i * 0.1) for i in range(1, 60)]   # flat
    prods.append(product("inv", shelf=10.0, delivery=8.0))
    out = run(make_inputs(products=prods))
    assert out.thresholds["ceiling_pct"] is None and out.counts["above"] is None
    assert [e.barcode for e in out.entries] == ["inv"]
    assert "ceiling_undetermined" in out.notes


def test_ac_006_artefacts_are_excluded_and_counted():
    out = run(_inputs())
    assert "art" not in {e.barcode for e in out.entries} and out.counts["excluded_artefact"] == 1


def test_ac_007_no_velocity_keys_in_evidence():
    for e in run(_inputs()).entries:
        assert not {"units_per_day", "days_to_stockout", "projected_revenue"} & set(e.evidence)


def test_ac_008_signal_density_guard():
    prods = [product(f"a{i}", shelf=10.0, delivery=15.0) for i in range(50)] + [product("b", shelf=10.0, delivery=10.0)]
    out = run(make_inputs(products=prods))
    assert out.counts["above"] is None and "ceiling_degenerate" in out.notes


def test_missing_delivery_prices_everywhere_is_unavailable():
    out = run(make_inputs(products=[product("1", shelf=5.0, delivery=None)]))
    assert out.status == "unavailable" and out.unavailable_reason == "no_delivery_prices"


def test_withdrawn_products_leave_the_population():
    out = run(_inputs(), ) if False else run(make_inputs(products=[product("inv", shelf=10.0, delivery=8.0), product("k", shelf=10.0, delivery=10.0)], withdrawn={"inv"}))
    assert out.counts["population"] == 1 and out.entries == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/engine/test_price_consistency.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/engine/price_consistency.py
"""SPEC-001 — the store's shelf price against its own delivery-platform price.

Four states; the ceiling is DERIVED from the store's own markup distribution
(FR-004) as the last band boundary where density collapses. Inverted = a
confirmed per-sale loss; above the ceiling = a question, never a loss (FR-008)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, Value, entry_id
from src.engine.registry import derive_status

CAP, SPEC = "price_consistency", "SPEC-001"
IDENTICAL_EPS = 0.005


@dataclass(frozen=True)
class CeilingResult:
    pct: Optional[float]
    method: str
    bands: list


def derive_ceiling(markups: list, *, band_pct: float, drop_ratio: float, min_band_count: int) -> CeilingResult:
    """Bands of `band_pct` over the positive markups. A candidate ceiling is the upper
    edge of a band whose successor holds at most (1 − drop_ratio) of its count, provided
    the band itself holds at least `min_band_count`. The LAST candidate is the ceiling —
    the highest markup still consistent with the owner's own behaviour (INV-002)."""
    positive = [m for m in markups if m > 0]
    if not positive:
        return CeilingResult(None, "last_density_collapse", [])
    top = max(positive)
    n_bands = int(top // band_pct) + 1
    counts = [0] * n_bands
    for m in positive:
        counts[int(m // band_pct)] += 1
    bands = [{"from": i * band_pct, "to": (i + 1) * band_pct, "count": c} for i, c in enumerate(counts)]
    ceiling = None
    for i in range(1, n_bands):
        prev, cur = counts[i - 1], counts[i]
        if prev >= min_band_count and cur <= (1 - drop_ratio) * prev:
            ceiling = float(i * band_pct)
    return CeilingResult(ceiling, "last_density_collapse", bands)


def markup_pct(shelf: float, delivery: float) -> float:
    return (delivery / shelf - 1.0) * 100.0


def classify(shelf: float, delivery: float, ceiling_pct: Optional[float]) -> str:
    if abs(delivery - shelf) < IDENTICAL_EPS:
        return "identical"
    if delivery < shelf:
        return "inverted"
    if ceiling_pct is None:
        return "undetermined"
    return "above" if markup_pct(shelf, delivery) > ceiling_pct else "within"


def _is_artefact(p: dict, policy) -> bool:
    if p["shelf_price"] < policy.artefact_min_price:
        return True
    return p["cost_price"] is not None and p["cost_price"] > policy.artefact_cost_ratio * p["shelf_price"]


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    policy = inputs.policy
    withdrawn = inputs.withdrawn or set()
    paired = [p for p in inputs.products
              if p["has_identifier"] and p["barcode"] not in withdrawn
              and p["shelf_price"] is not None and p["delivery_price"] is not None]
    if not paired:
        return CapabilityOutput.unavailable(CAP, SPEC, "no_delivery_prices")

    excluded_artefact = [p for p in paired if _is_artefact(p, policy)]
    kept = [p for p in paired if not _is_artefact(p, policy)]
    excluded_gap = [p for p in kept if abs(markup_pct(p["shelf_price"], p["delivery_price"])) > policy.max_credible_gap_pct]
    kept = [p for p in kept if abs(markup_pct(p["shelf_price"], p["delivery_price"])) <= policy.max_credible_gap_pct]

    markups = [markup_pct(p["shelf_price"], p["delivery_price"]) for p in kept if p["delivery_price"] > p["shelf_price"] + IDENTICAL_EPS]
    ceiling = derive_ceiling(markups, band_pct=policy.ceiling_band_pct, drop_ratio=policy.ceiling_drop_ratio,
                             min_band_count=policy.ceiling_min_band_count)
    notes: list[str] = []
    ceiling_pct = ceiling.pct
    if ceiling_pct is None:
        notes.append("ceiling_undetermined")

    states = {p["barcode"]: classify(p["shelf_price"], p["delivery_price"], ceiling_pct) for p in kept}
    # INV-003 / NFR-003: a ceiling that surfaces ≥10 % of the pair set describes normal pricing.
    if ceiling_pct is not None:
        surfaced = sum(1 for s in states.values() if s in ("above", "inverted"))
        if surfaced >= len(kept) or surfaced > 0.10 * len(kept):
            notes.append("ceiling_degenerate")
            ceiling_pct = None
            states = {p["barcode"]: classify(p["shelf_price"], p["delivery_price"], None) for p in kept}

    entries: list[Entry] = []
    for p in kept:
        s, b = states[p["barcode"]], p["barcode"]
        shelf, delivery = p["shelf_price"], p["delivery_price"]
        evidence = {"shelf_price": shelf, "delivery_price": delivery, "difference": round(delivery - shelf, 2),
                    "markup_pct": round(markup_pct(shelf, delivery), 2), "ceiling_pct": ceiling_pct}
        if s == "inverted":
            loss = round(shelf - delivery, 2)
            entries.append(Entry(id=entry_id("price.inverted", b), signal_family="price.inverted",
                                 capability=CAP, barcode=b, product_name=p["product_name"],
                                 department=p["department"], action="verify_price", characterisation="confirmed_loss",
                                 evidence={**evidence, "commission_compounds": True},
                                 value=Value(loss, "per_sale", "confirmed"),
                                 ordering_key={"name": "loss_per_sale", "value": loss}))
        elif s == "above":
            entries.append(Entry(id=entry_id("price.above_ceiling", b), signal_family="price.above_ceiling",
                                 capability=CAP, barcode=b, product_name=p["product_name"],
                                 department=p["department"], action="verify_price", characterisation="question",
                                 evidence=evidence, value=None,
                                 ordering_key={"name": "markup_pct", "value": evidence["markup_pct"]}))
    entries.sort(key=lambda e: (0 if e.characterisation == "confirmed_loss" else 1, -e.ordering_key["value"], e.barcode))

    counts = {"population": len(paired),
              "identical": sum(1 for s in states.values() if s == "identical"),
              "within": None if ceiling_pct is None else sum(1 for s in states.values() if s == "within"),
              "above": None if ceiling_pct is None else sum(1 for s in states.values() if s == "above"),
              "inverted": sum(1 for s in states.values() if s == "inverted"),
              "excluded_artefact": len(excluded_artefact), "excluded_gap": len(excluded_gap)}
    # ARCH-GATE-006: the ceiling is derived AFTER the FR-074 withdrawn exclusion — `paired`
    # already dropped them — so the published population is the live catalogue, not the whole
    # export, and a withdrawal moves the ceiling. The population travels with the figure.
    thresholds = {"ceiling_pct": ceiling_pct, "ceiling_method": ceiling.method, "ceiling_bands": ceiling.bands,
                  "ceiling_population": len(kept), "ceiling_population_excludes_withdrawn": True,
                  "artefact_min_price": policy.artefact_min_price, "artefact_cost_ratio": policy.artefact_cost_ratio,
                  "max_credible_gap_pct": policy.max_credible_gap_pct}
    figures = [Figure(k, v, "products", ["pos"], {"ceiling_pct": ceiling_pct}) for k, v in counts.items()]
    figures.append(Figure("ceiling_pct", ceiling_pct, "percent", ["pos"],
                          {"method": ceiling.method, "population": len(kept),
                           "excludes_withdrawn": True}))
    return CapabilityOutput(id=CAP, spec=SPEC, status="available", thresholds=thresholds, counts=counts,
                            entries=entries, figures=figures, notes=notes)
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/engine/test_price_consistency.py -q`
Expected: 14 passed

- [ ] **Step 5: Reproduce the pilot's 18 % on the real export (integration test, skipped when the CSV is absent)**

Append to the test file:

```python
import csv
import pytest
from src.engine.model import norm_barcode

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not (ROOT / "yomyom-inventory.csv").exists(), reason="pilot export not present")
def test_pilot_ceiling_reproduces_18_percent():
    with (ROOT / "yomyom-inventory.csv").open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    keys = {k.strip(): k for k in rows[0]}
    markups = []
    for r in rows:
        try:
            shelf, wolt = float(r[keys["מחיר מכירה"]] or 0), float(r[keys["WOLT"]] or 0)
        except ValueError:
            continue
        if shelf >= 0.5 and wolt > shelf + 0.005:
            markups.append((wolt / shelf - 1) * 100)
    assert derive_ceiling(markups, **P).pct == 18.0
```

Run: `python3 -m pytest tests/engine/test_price_consistency.py -q` → 15 passed

- [ ] **Step 6: Commit**

```bash
git add src/engine/price_consistency.py tests/engine/test_price_consistency.py
git commit -m "Price consistency as a capability: derived ceiling, four states, loss vs question

Replaces the flat 5 % rule. The ceiling is the last density collapse in the
store's own markup bands and reproduces the 18 % the intent measured; when no
collapse exists the above-ceiling signal is suppressed and inverted continues."
```

---

### Task 1.3: Catalogue lifecycle (SPEC-004)

**Files:**
- Create: `src/engine/catalogue_lifecycle.py`
- Test: `tests/engine/test_catalogue_lifecycle.py`

**Interfaces:**
- Produces: `run(inputs) -> CapabilityOutput` (`id='catalogue_lifecycle'`) with entries: `idle` (action `decide_idle`, ordering `unit_cost`, evidence `{unit_cost, cost_source, evidence_state, window_id}` — **no stock quantity**) and `implausible_quantity` (action `decide_idle`, characterisation `implausible_quantity`, evidence includes `recorded_stock` because the quantity *is* the question); `counts: {living, withdrawable, idle, excluded_negative_stock, excluded_no_identifier, excluded_stock_absent, revived_manually, implausible}`; `notes` with `provisional_window` and `seasonal_misclassification_possible` when the window is short. Hand-off attributes on the output object (not serialised): `withdrawn_barcodes: set[str]`, `idle_barcodes: set[str]`. Published extras (`out.extras`, merged into the capability by `to_dict`): `provisional: bool`, `withdrawn: [...]`, `statement: str` — `window` and `counts` are already contract fields and must not be repeated.
- `classify_evidence(summary_row | None) -> 'observed_units' | 'observed_zero' | 'no_row'`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/engine/test_catalogue_lifecycle.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product, summary, window_of
from src.engine.catalogue_lifecycle import classify_evidence, run
from src.owner_state.model import OwnerState

W7 = window_of(["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"])
W12 = window_of([f"2025-{m:02d}" for m in range(8, 13)] + [f"2026-{m:02d}" for m in range(1, 8)], full=True)
MONTHLY = [{"barcode": "L", "month": "2026-01", "units": 10, "receipts": 0, "revenue": 100.0}]


def _inputs(window=W7, owner=None, monthly=MONTHLY):
    return make_inputs(
        products=[product("L", stock=3.0, cost=1.0), product("W", stock=0.0, cost=2.0), product("I", stock=4.0, cost=34.0),
                  product("I2", stock=2.0, cost=None), product("N", stock=-2.0), product(None, name="x", stock=0.0),
                  product("Z", stock=0.0), product("A", stock=None)],
        sales_summary=[summary("L", units=10), summary("Z", units=0, observed_zero=True)],
        sales_monthly=monthly, window=window, owner=owner)


def test_evidence_states():
    assert classify_evidence({"units_total": 3, "observed_zero": False}) == "observed_units"
    assert classify_evidence({"units_total": 0, "observed_zero": True}) == "observed_zero"
    assert classify_evidence(None) == "no_row"


def test_ac_065_partition_and_ac_070_exclusions():
    out = run(_inputs())
    c = out.counts
    assert c["living"] == 1 and c["withdrawable"] == 2 and c["idle"] == 2
    assert c["excluded_negative_stock"] == 1 and c["excluded_no_identifier"] == 1 and c["excluded_stock_absent"] == 1
    assert out.withdrawn_barcodes == {"W", "Z"} and "N" not in out.withdrawn_barcodes


def test_ac_060_idle_is_never_withdrawn_and_ac_071_ranked_by_unit_cost_without_stock():
    out = run(_inputs())
    idle = [e for e in out.entries if e.characterisation == "idle"]
    assert [e.barcode for e in idle] == ["I", "I2"]                 # missing cost last
    assert idle[0].evidence["unit_cost"] == 34.0 and idle[1].evidence["unit_cost"] is None
    assert "recorded_stock" not in idle[0].evidence and all(e.value is None for e in idle)


def test_ac_063a_short_window_makes_every_withdrawal_provisional():
    out = run(_inputs())
    assert out.extras["provisional"] is True
    assert all(w["provisional"] for w in out.extras["withdrawn"])
    assert all("seasonal" in w["statement"] for w in out.extras["withdrawn"])
    assert "seasonal_misclassification_possible" in out.notes


def test_ac_063c_full_cycle_drops_the_statement():
    out = run(_inputs(window=W12))
    assert out.extras["provisional"] is False and "seasonal_misclassification_possible" not in out.notes


def test_ac_062_a_sale_revives_without_owner_action():
    inputs = _inputs()
    inputs.sales_summary["W"] = summary("W", units=1)
    assert "W" not in run(inputs).withdrawn_barcodes


def test_ac_063_manual_revival_holds_for_the_window_only():
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t",
                                  "revivals": {"W": {"at": 1, "window_id": W7.window_id}}})
    out = run(_inputs(owner=owner))
    assert "W" not in out.withdrawn_barcodes and out.counts["revived_manually"] == 1
    later = OwnerState.from_dict({"status": "available", "pulled_at": "t",
                                  "revivals": {"W": {"at": 1, "window_id": "old"}}})
    assert "W" in run(_inputs(owner=later)).withdrawn_barcodes


def test_ac_066_no_sales_evidence_means_no_classification():
    out = run(make_inputs(products=[product("W", stock=0.0)], sales_summary=None, window=None))
    assert out.status == "unavailable" and out.unavailable_reason == "no_sales_evidence"
    assert out.withdrawn_barcodes == set()


def test_ac_069_implausible_quantity_is_a_question_not_a_valuation():
    monthly = [{"barcode": "L", "month": "2026-01", "units": 10, "receipts": 0, "revenue": 1000.0}]
    inputs = make_inputs(products=[product("cups", stock=4005.0, cost=170.0), product("L", stock=1.0, cost=1.0)],
                         sales_summary=[summary("L", units=10)], sales_monthly=monthly, window=W7)
    out = run(inputs)
    q = [e for e in out.entries if e.characterisation == "implausible_quantity"]
    assert [e.barcode for e in q] == ["cups"]
    assert "valuation" not in q[0].evidence and q[0].evidence["recorded_stock"] == 4005.0 and q[0].value is None


def test_withdrawn_evidence_states_no_row_not_zero():
    out = run(_inputs())
    by = {w["barcode"]: w for w in out.extras["withdrawn"]}
    assert by["W"]["evidence_state"] == "no_row" and by["Z"]["evidence_state"] == "observed_zero"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/engine/test_catalogue_lifecycle.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/engine/catalogue_lifecycle.py
"""SPEC-004 — living / withdrawable / idle, recomputed every run (ADR-004, ADR-011).

No stored lifecycle state: withdrawn = f(evidence window, recorded stock, owner
revivals). Idle entries are ranked by UNIT cost and carry no stock quantity (D-11)."""
from __future__ import annotations

from typing import Optional

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, entry_id
from src.engine.registry import derive_status
from src.owner_state.model import revival_active

CAP, SPEC = "catalogue_lifecycle", "SPEC-004"
PROVISIONAL_STATEMENT = ("Withdrawn on {count} months of evidence ({window}), less than a full annual cycle: "
                         "the evidence cannot separate a seasonal product from a dead one, so this withdrawal "
                         "may be wrong and will be re-examined when longer evidence arrives.")
SETTLED_STATEMENT = "Withdrawn on a full annual cycle of evidence ({window})."


def classify_evidence(row: Optional[dict]) -> str:
    if row is None:
        return "no_row"
    return "observed_units" if float(row.get("units_total") or 0) > 0 else "observed_zero"


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if status == "unavailable":
        empty = CapabilityOutput.unavailable(CAP, SPEC, reason)
        empty.withdrawn_barcodes, empty.idle_barcodes = set(), set()
        return empty
    policy, window, owner = inputs.policy, inputs.window, inputs.owner
    assert not policy.withdraw_with_stock, "OQ-409: stock-carrying withdrawal is not authorised"
    provisional = not window.full_annual_cycle
    revenue_total = sum(float(r.get("revenue") or 0) for r in (inputs.sales_monthly or []))

    counts = {k: 0 for k in ("living", "withdrawable", "idle", "excluded_negative_stock", "excluded_no_identifier",
                             "excluded_stock_absent", "revived_manually", "implausible")}
    withdrawn: list[dict] = []
    idle: list[Entry] = []
    questions: list[Entry] = []
    for p in inputs.products:
        b = p["barcode"]
        if not p["has_identifier"]:
            counts["excluded_no_identifier"] += 1; continue
        stock = p["recorded_stock"]
        if stock is None:
            counts["excluded_stock_absent"] += 1; continue
        if stock < 0:
            counts["excluded_negative_stock"] += 1; continue          # FR-062: hygiene, never withdrawable
        state = classify_evidence(inputs.sales_summary.get(b))
        if state == "observed_units" or revival_active(owner, b, window.window_id):
            counts["living"] += 1
            if state != "observed_units":
                counts["revived_manually"] += 1
            continue
        if stock == 0:
            counts["withdrawable"] += 1
            withdrawn.append({"barcode": b, "product_name": p["product_name"], "department": p["department"],
                              "evidence_state": state, "recorded_stock": 0, "window_id": window.window_id,
                              "months": window.count, "provisional": provisional,
                              "statement": (PROVISIONAL_STATEMENT if provisional else SETTLED_STATEMENT)
                                            .format(count=window.count, window=window.window_id)})
            continue
        counts["idle"] += 1
        cost = p["cost_price"]
        idle.append(Entry(id=entry_id("catalogue.idle", b), signal_family="catalogue.idle",
                          capability=CAP, barcode=b, product_name=p["product_name"],
                          department=p["department"], action="decide_idle", characterisation="idle",
                          evidence={"unit_cost": cost, "cost_source": p["cost_source"], "evidence_state": state,
                                    "window_id": window.window_id},
                          value=None, ordering_key={"name": "unit_cost", "value": cost}))
        # FR-072: the implausibility TEST may use a valuation; the question never states it.
        if cost is not None and revenue_total > 0 and stock * cost > policy.implausible_revenue_share * revenue_total:
            counts["implausible"] += 1
            questions.append(Entry(id=entry_id("catalogue.implausible_quantity", b),
                                   signal_family="catalogue.implausible_quantity", capability=CAP, barcode=b,
                                   product_name=p["product_name"], department=p["department"], action="decide_idle",
                                   characterisation="implausible_quantity",
                                   evidence={"recorded_stock": stock, "unit_cost": cost, "evidence_state": state,
                                             "window_id": window.window_id, "question": "is_this_quantity_right"},
                                   value=None, ordering_key={"name": "unit_cost", "value": cost}))

    assert counts["living"] + counts["withdrawable"] + counts["idle"] == \
        len(inputs.products) - counts["excluded_no_identifier"] - counts["excluded_stock_absent"] - counts["excluded_negative_stock"], "INV-034"
    idle.sort(key=lambda e: (e.ordering_key["value"] is None, -(e.ordering_key["value"] or 0), e.barcode))
    questions.sort(key=lambda e: (-(e.ordering_key["value"] or 0), e.barcode))
    withdrawn.sort(key=lambda w: w["barcode"])

    notes = ["window:" + window.window_id]
    if provisional:
        notes += ["provisional_window", "seasonal_misclassification_possible"]
    statement = ("Classified on {n} months ({w}). Seasonal products may be misclassified as dead; every "
                 "withdrawal is provisional until a full annual cycle of evidence exists.").format(n=window.count, w=window.window_id) \
        if provisional else "Classified on a full annual cycle ({w}).".format(w=window.window_id)
    figures = [Figure(k, v, "products", ["pos", "sales"], {"window": window.window_id}) for k, v in counts.items()]
    out = CapabilityOutput(id=CAP, spec=SPEC, status="available", window=window,
                           thresholds={"implausible_revenue_share": policy.implausible_revenue_share,
                                       "full_annual_cycle_months": policy.full_annual_cycle_months,
                                       "withdraw_with_stock": policy.withdraw_with_stock},
                           counts=counts, entries=questions + idle, figures=figures, notes=notes)
    out.withdrawn_barcodes = {w["barcode"] for w in withdrawn}      # hand-off, not published
    out.idle_barcodes = {e.barcode for e in idle}
    out.extras = {"provisional": provisional, "withdrawn": withdrawn, "statement": statement}
    return out
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/engine/test_catalogue_lifecycle.py -q`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add src/engine/catalogue_lifecycle.py tests/engine/test_catalogue_lifecycle.py
git commit -m "Catalogue lifecycle as a re-evaluated rule: withdraw, revive, rank idle by unit cost

Nothing is stored: the withdrawn set is a function of the evidence window,
recorded stock and the owner's revivals. Every withdrawal on a short window
carries its provisional statement, and 'no row' is recorded as such."
```

---

### Task 1.4: Owner cost questions (SPEC-005)

**Files:**
- Create: `src/engine/owner_questions.py`
- Test: `tests/engine/test_owner_questions.py`

**Interfaces:**
- Consumes: `EngineInputs.products`, `.withdrawn`, `.idle`, `.owner`, `.policy`, and `inputs.sales_summary` (for money at stake — basis declared in `policy.question_money_basis`, ARCH-GATE-002).
- Produces: `run(inputs) -> CapabilityOutput` (`id='owner_questions'`, `admitted=False`) with an extra attribute `questions: dict` = `{status, limit, items: [...], suppressed: {withdrawn, idle, answered, no_effect}}`. Each item: `{question_id, barcode, product_name, department, fact: 'cost_price', why: {products_affected, money_at_stake}, expected_value}`. `counts: {open, suppressed_withdrawn, suppressed_idle, suppressed_answered, suppressed_no_effect}`.
- Expected value = `money_at_stake × products_affected`; in V1 a cost question resolves exactly one product, so `products_affected = 1` and `money_at_stake` = the product's seven-month revenue (`units_total × selling_price` from the summary, else `units_total × shelf_price`). Ordering is expected value descending, then barcode.
- A question exists only for a **living** product with no cost price and no recorded answer (FR-080, FR-082, FR-082a).

- [ ] **Step 1: Write the failing tests**

```python
# tests/engine/test_owner_questions.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product, summary, window_of
from src.engine.owner_questions import run
from src.owner_state.model import OwnerState

W = window_of(["2026-01", "2026-07"])


def _inputs(owner=None, withdrawn=None, idle=None):
    return make_inputs(
        products=[product("live1", shelf=10.0, cost=None, stock=5.0),      # asked (186 units)
                  product("live2", shelf=4.0, cost=None, stock=5.0),       # asked (84 units)
                  product("live3", shelf=1.0, cost=2.0, stock=5.0),        # has a cost → no question
                  product("dead", shelf=3.0, cost=None, stock=0.0),        # withdrawn → suppressed
                  product("idle1", shelf=3.0, cost=None, stock=9.0)],      # idle → suppressed
        sales_summary=[summary("live1", units=186), summary("live2", units=84), summary("live3", units=5)],
        window=W, owner=owner, withdrawn=withdrawn if withdrawn is not None else {"dead"},
        idle=idle if idle is not None else {"idle1"})


def test_ac_088_only_questions_that_change_an_output():
    q = run(_inputs()).extras
    assert [i["barcode"] for i in q["items"]] == ["live1", "live2"]
    assert q["suppressed"]["no_effect"] >= 1          # live3 already has a cost


def test_ac_081_withdrawn_and_idle_are_suppressed():
    q = run(_inputs()).extras
    assert "dead" not in {i["barcode"] for i in q["items"]}
    assert "idle1" not in {i["barcode"] for i in q["items"]}
    assert q["suppressed"]["withdrawn"] == 1 and q["suppressed"]["idle"] == 1


def test_ac_080_the_limit_is_published_and_never_above_three():
    q = run(_inputs()).extras
    assert q["limit"] == 3


def test_ac_083_ordering_is_by_expected_value():
    items = run(_inputs()).extras["items"]
    assert items[0]["barcode"] == "live1"
    assert items[0]["expected_value"] > items[1]["expected_value"]


def test_ac_082_suppressed_counts_are_reportable():
    out = run(_inputs())
    assert out.counts["open"] == 2 and out.counts["suppressed_withdrawn"] == 1 and out.counts["suppressed_idle"] == 1


def test_ac_087_an_answered_question_is_not_re_presented():
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t",
                                  "answers": {"live1": {"cost_price": {"value": 3.0, "at": 1, "status": "answered"}}}})
    # inputs.products already carries the owner's cost (load_inputs applies it), so simulate that:
    inputs = _inputs(owner=owner)
    for p in inputs.products:
        if p["barcode"] == "live1":
            p["cost_price"], p["cost_source"] = 3.0, "owner"
    q = run(inputs).extras
    assert "live1" not in {i["barcode"] for i in q["items"]}
    assert q["suppressed"]["answered"] == 1


def test_ac_086_a_deferral_leaves_the_question_open_but_unpresented():
    owner = OwnerState.from_dict({"status": "available", "pulled_at": "t",
                                  "answers": {"live1": {"cost_price": {"value": None, "at": 1, "status": "deferred"}}}})
    q = run(_inputs(owner=owner)).extras
    assert "live1" not in {i["barcode"] for i in q["items"]}    # deferred: not shown
    assert q["suppressed"]["answered"] == 0                      # and not recorded as content


def test_storage_unavailable_means_no_questions_are_presented():
    out = run(_inputs(owner=OwnerState.unavailable("pull_failed")))
    assert out.status == "unavailable" and out.unavailable_reason == "answer_storage_unavailable"
    assert out.extras["items"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/engine/test_owner_questions.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/engine/owner_questions.py
"""SPEC-005 — the few facts only the owner holds.

V1 asks exactly one kind of question: a missing purchase cost on a LIVING product.
Suppression does the work (NFR-040): withdrawn and idle products are never asked
about, so 1,270 missing costs become the handful the intent names."""
from __future__ import annotations

import hashlib

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Figure
from src.engine.registry import derive_status

CAP, SPEC = "owner_questions", "SPEC-005"
FACT = "cost_price"


def _question_id(barcode: str) -> str:
    return hashlib.sha256(f"{FACT}|{barcode}".encode("utf-8")).hexdigest()[:16]


def _deferred(owner, barcode: str) -> bool:
    rec = (owner.answers.get(barcode) or {}).get(FACT) or {}
    return rec.get("status") == "deferred"


def _answered(owner, barcode: str) -> bool:
    rec = (owner.answers.get(barcode) or {}).get(FACT) or {}
    return rec.get("status") == "answered"


def run(inputs: EngineInputs) -> CapabilityOutput:
    empty = {"limit": inputs.policy.question_limit, "items": [],
             "suppressed": {"withdrawn": 0, "idle": 0, "answered": 0, "no_effect": 0}}
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if inputs.owner.status != "available":
        # SPEC-005 §11: never present a question that cannot be recorded. A rule-level
        # reason: the input landed, the place to write the answer did not.
        status, reason = "unavailable", "answer_storage_unavailable"
    if status == "unavailable":
        out = CapabilityOutput.unavailable(CAP, SPEC, reason)
        out.extras = empty
        return out

    withdrawn, idle = inputs.withdrawn or set(), inputs.idle or set()
    suppressed = {"withdrawn": 0, "idle": 0, "answered": 0, "no_effect": 0}
    items = []
    for p in inputs.products:
        b = p["barcode"]
        if not b:
            continue
        if p["cost_price"] is not None:
            if p["cost_source"] == "owner":
                suppressed["answered"] += 1
            else:
                suppressed["no_effect"] += 1
            continue
        if b in withdrawn:
            suppressed["withdrawn"] += 1; continue
        if b in idle:
            suppressed["idle"] += 1; continue
        if _deferred(inputs.owner, b):
            continue                                   # open, not presented, not content (FR-091)
        s = (inputs.sales_summary or {}).get(b)
        units = float(s["units_total"]) if s else 0.0
        if units <= 0:
            suppressed["no_effect"] += 1; continue     # not living: answering changes nothing today
        # ARCH-GATE-002: the basis is declared in policy.yaml and published with the figure,
        # because FR-085 orders by money and never says which money.
        money = units * (p["shelf_price"] or 0.0)
        items.append({"question_id": _question_id(b), "barcode": b, "product_name": p["product_name"],
                      "department": p["department"], "fact": FACT,
                      "why": {"products_affected": 1, "money_at_stake": round(money, 2),
                              "money_basis": inputs.policy.question_money_basis,
                              "units_sold": units, "window_id": inputs.window.window_id if inputs.window else None},
                      "expected_value": round(money * inputs.policy.question_yield_factor, 2)})
    items.sort(key=lambda i: (-i["expected_value"], i["barcode"]))
    counts = {"open": len(items), "suppressed_withdrawn": suppressed["withdrawn"], "suppressed_idle": suppressed["idle"],
              "suppressed_answered": suppressed["answered"], "suppressed_no_effect": suppressed["no_effect"]}
    out = CapabilityOutput(id=CAP, spec=SPEC, status="available",
                           thresholds={"question_limit": inputs.policy.question_limit}, counts=counts,
                           entries=[], figures=[Figure(k, v, "questions", ["pos", "sales", "owner_state"]) for k, v in counts.items()])
    out.extras = {"limit": inputs.policy.question_limit, "items": items, "suppressed": suppressed}
    return out
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/engine/test_owner_questions.py -q`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/engine/owner_questions.py tests/engine/test_owner_questions.py
git commit -m "Ask the owner only for costs that change an output on a living product

Suppression, not the on-screen limit, is what bounds the ask: withdrawn and idle
products are never asked about, and a deferral leaves the question open without
recording content."
```

---

### Task 1.5: Competitor price position (SPEC-003)

**Files:**
- Create: `src/engine/competitor_position.py`
- Test: `tests/engine/test_competitor_position.py`

**Interfaces:**
- Consumes: `EngineInputs.products`, `.observations` (already format-gated and client-free), `.matches`, `.stores`, `.policy`, `.withdrawn`.
- Produces: `measure_format_allowance(pairs) -> (pct | None, basis_count)`; `balanced_reference(same_format_min, supermarket_min, allowance_pct) -> dict | None` = `{'value', 'kind': 'midpoint'|'supermarket_plus_allowance', 'same_format', 'supermarket', 'allowance_pct'}`; `run(inputs) -> CapabilityOutput` (`id='competitor_position'`) with entries of three characterisations — `policy_breach_attention` (`attention='today'`), `policy_breach_review` (`attention='review'`), `purchase_cost` (`attention='review'`, action `check_purchase_cost`) — `counts: {catalogue, comparable_population, matched, structurally_uncomparable, no_comparison, evaluated, breaches, attention, review, purchase_cost_findings, no_cost_skipped, stale_skipped}`, `thresholds: {policy_pct, attention_pct, cost_floor_pct, format_allowance_pct, format_allowance_basis_count, freshness_days}`, and `position: [{store_id, store_name, format, affinity, matched, cheaper_here, dearer_here, median_diff_pct}]` published as `out.extras["position"]`.
- Rules, in order (FR-043a…FR-046): freshness → reference → **cost floor first** → policy → attention split.

- [ ] **Step 1: Write the failing tests**

```python
# tests/engine/test_competitor_position.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, match, observation, product
from src.engine.competitor_position import balanced_reference, measure_format_allowance, run

FORECOURT = dict(store_format="gas_convenience", affinity=1.0)
SUPER = dict(store_format="supermarket", affinity=0.1)
FRESH = "2026-09-08T00:00:00Z"


def test_measure_format_allowance_is_the_median_of_products_holding_both():
    pct, n = measure_format_allowance([(10.0, 12.0), (10.0, 11.0), (10.0, 13.0)])   # (supermarket, same_format)
    assert pct == 20.0 and n == 3
    assert measure_format_allowance([]) == (None, 0)


def test_balanced_reference_prefers_the_midpoint():
    r = balanced_reference(same_format_min=4.9, supermarket_min=3.9, allowance_pct=20.0)
    assert r["value"] == 4.4 and r["kind"] == "midpoint"


def test_balanced_reference_falls_back_to_supermarket_plus_measured_allowance():
    r = balanced_reference(same_format_min=None, supermarket_min=10.0, allowance_pct=20.0)
    assert r["value"] == 12.0 and r["kind"] == "supermarket_plus_allowance"
    assert balanced_reference(None, 10.0, None) is None          # FR-044c: no invented number
    assert balanced_reference(None, None, 20.0) is None


def _inputs(products, observations, matches, **kw):
    return make_inputs(products=products, observations=observations, matches=matches, **kw)


def test_ac_049_ac_050_cost_floor_blocks_a_losing_recommendation():
    prods = [product("cheese", shelf=158.21, cost=147.11)]
    obs = [observation("cheese", 54.0, "rami-levy-pt-01", **SUPER, observed_at=FRESH),
           observation("cheese", 60.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("cheese", "cheese", "rami-levy-pt-01"), match("cheese", "cheese", "dor-alon-kq-01")]))
    kinds = {e.barcode: e.characterisation for e in out.entries}
    assert kinds["cheese"] == "purchase_cost"
    assert out.counts["purchase_cost_findings"] == 1 and out.counts["breaches"] == 0


def test_ac_051_no_cost_means_no_judgement():
    prods = [product("x", shelf=100.0, cost=None)]
    obs = [observation("x", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("x", "x", "dor-alon-kq-01")]))
    assert out.entries == [] and out.counts["no_cost_skipped"] == 1


def test_ac_054_a_breach_above_the_attention_threshold_is_same_day():
    prods = [product("bisli", shelf=13.90, cost=6.78)]
    obs = [observation("bisli", 6.50, "rami-levy-pt-01", **SUPER, observed_at=FRESH),
           observation("bisli", 7.00, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("bisli", "bisli", "rami-levy-pt-01"), match("bisli", "bisli", "dor-alon-kq-01")]))
    e = out.entries[0]
    assert e.characterisation == "policy_breach_attention" and e.attention == "today"
    assert e.evidence["reference"]["kind"] == "midpoint" and e.evidence["premium_pct"] > 100
    assert e.value is None and e.action == "review_policy"


def test_a_breach_between_the_two_thresholds_is_unhurried_review():
    prods = [product("p", shelf=17.0, cost=5.0)]
    obs = [observation("p", 10.0, "rami-levy-pt-01", **SUPER, observed_at=FRESH),
           observation("p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("p", "p", "rami-levy-pt-01"), match("p", "p", "dor-alon-kq-01")]))
    assert out.entries[0].characterisation == "policy_breach_review" and out.entries[0].attention == "review"
    assert out.entries[0].evidence["policy_pct"] == 60


def test_ac_047a_a_difference_within_the_allowance_is_not_a_fault():
    prods = [product("q", shelf=11.5, cost=5.0)]
    obs = [observation("q", 10.0, "rami-levy-pt-01", **SUPER, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("q", "q", "rami-levy-pt-01")]))
    assert out.entries == []


def test_ac_042_every_entry_names_the_store_and_its_format():
    prods = [product("p", shelf=17.0, cost=5.0)]
    obs = [observation("p", 10.0, "rami-levy-pt-01", **SUPER, observed_at=FRESH, store_name="Rami Levy PT"),
           observation("p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH, store_name="Alonit KQ")]
    e = run(_inputs(prods, obs, [match("p", "p", "rami-levy-pt-01"), match("p", "p", "dor-alon-kq-01")])).entries[0]
    sources = e.evidence["sources"]
    assert {s["format"] for s in sources} == {"supermarket", "gas_convenience"}
    assert all(s["store_name"] for s in sources)


def test_ac_045_no_comparison_is_not_a_zero_difference():
    prods = [product("alone", shelf=10.0, cost=5.0)]
    out = run(_inputs(prods, [], []))
    assert out.counts["no_comparison"] == 1 and out.entries == []


def test_ac_044_coverage_is_stated_against_the_full_catalogue():
    prods = [product("a", shelf=10.0, cost=5.0), product("svc", shelf=30.0, cost=None, name="שטיפת רכב"),
             product("b", shelf=10.0, cost=5.0)]
    obs = [observation("a", 9.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("a", "a", "dor-alon-kq-01")]))
    assert out.counts["catalogue"] == 3 and out.counts["matched"] == 1


def test_ac_048_stale_observations_drive_nothing():
    prods = [product("p", shelf=17.0, cost=5.0)]
    old = "2026-01-01T00:00:00Z"
    obs = [observation("p", 10.0, "rami-levy-pt-01", **SUPER, observed_at=old),
           observation("p", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=old)]
    out = run(_inputs(prods, obs, [match("p", "p", "rami-levy-pt-01"), match("p", "p", "dor-alon-kq-01")]))
    assert out.entries == [] and out.counts["stale_skipped"] == 1


def test_ac_046_position_is_reportable_including_when_cheaper():
    prods = [product("a", shelf=9.0, cost=2.0), product("b", shelf=8.0, cost=2.0)]
    obs = [observation("a", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH),
           observation("b", 10.0, "dor-alon-kq-01", **FORECOURT, observed_at=FRESH)]
    out = run(_inputs(prods, obs, [match("a", "a", "dor-alon-kq-01"), match("b", "b", "dor-alon-kq-01")]))
    pos = {p["store_id"]: p for p in out.extras["position"]}["dor-alon-kq-01"]
    assert pos["cheaper_here"] == 2 and pos["median_diff_pct"] < 0


def test_no_observations_at_all_is_unavailable():
    out = run(_inputs([product("a", shelf=10.0, cost=5.0)], None, None))
    assert out.status == "unavailable" and out.unavailable_reason == "no_competitor_data"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/engine/test_competitor_position.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/engine/competitor_position.py
"""SPEC-003 — is our price reasonable against the neighbours?

Order is load-bearing (FR-043b): freshness → balanced reference → COST FLOOR →
declared policy → attention split. A competitor's price is never a benchmark on
its own (INV-026) and never produces a recommendation that leaves the owner at or
below his own purchase cost (INV-025)."""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.engine.inputs import OUR_FORMAT, EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, entry_id
from src.engine.registry import derive_status

CAP, SPEC = "competitor_position", "SPEC-003"
SUPERMARKET_FORMATS = ("supermarket", "hypermarket", "midsize_grocery")


def measure_format_allowance(pairs: list) -> tuple:
    """FR-044b — the typical premium of same-format stores over supermarkets,
    measured from products holding both prices. Never an assumed constant."""
    diffs = [(same / sup - 1.0) * 100.0 for sup, same in pairs if sup and sup > 0 and same]
    if not diffs:
        return None, 0
    return round(statistics.median(diffs), 4), len(diffs)


def balanced_reference(same_format_min: Optional[float], supermarket_min: Optional[float],
                       allowance_pct: Optional[float]) -> Optional[dict]:
    if same_format_min is not None and supermarket_min is not None:
        return {"value": round((same_format_min + supermarket_min) / 2.0, 4), "kind": "midpoint",
                "same_format": same_format_min, "supermarket": supermarket_min, "allowance_pct": None}
    if same_format_min is not None and supermarket_min is None:
        return {"value": round(same_format_min, 4), "kind": "same_format_only",
                "same_format": same_format_min, "supermarket": None, "allowance_pct": None}
    if supermarket_min is not None and allowance_pct is not None:
        return {"value": round(supermarket_min * (1.0 + allowance_pct / 100.0), 4),
                "kind": "supermarket_plus_allowance", "same_format": None,
                "supermarket": supermarket_min, "allowance_pct": allowance_pct}
    return None                                                    # FR-044c: no comparison


def _fresh(observed_at: Optional[str], run_at: datetime, days: int) -> bool:
    if not observed_at:
        return False
    try:
        seen = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
    except ValueError:
        return False
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=timezone.utc)
    return seen >= run_at - timedelta(days=days)


def _is_structurally_uncomparable(p: dict, policy) -> bool:
    """Services and internal codes: a barcode shorter than the declared length is not a retail
    identifier, so no other shop can carry it and no comparison is possible (FR-052).

    The length is declared in configs/policy.yaml, not here: ARCH-GATE-004 left the predicate
    to the spec layer, so it is provisional and must move without a code change."""
    b = p["barcode"]
    return not b or len(b) < policy.uncomparable_min_barcode_digits


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    if not inputs.observations:                          # present but empty: a rule-level absence
        return CapabilityOutput.unavailable(CAP, SPEC, "no_competitor_data")
    policy, run_at, stores = inputs.policy, inputs.run_at, inputs.stores
    withdrawn = inputs.withdrawn or set()
    floor = stores.min_affinity

    approved = {m["internal_barcode"] for m in inputs.matches if m.get("approved", True)}
    by_barcode: dict = {}
    stale_only: set = set()
    for o in inputs.observations:
        if o["barcode"] not in approved and inputs.matches:
            pass                                                   # observations are already barcode-keyed
        if not _fresh(o["observed_at"], run_at, policy.freshness_days):
            stale_only.add(o["barcode"]); continue
        by_barcode.setdefault(o["barcode"], []).append(o)
    stale_only -= set(by_barcode)

    # Format allowance, measured once over products holding BOTH a supermarket and a
    # same-format price (FR-044b).
    pairs = []
    for b, obs in by_barcode.items():
        sup = [o["price"] for o in obs if o["store_format"] in SUPERMARKET_FORMATS]
        same = [o["price"] for o in obs if o["affinity"] >= floor]
        if sup and same:
            pairs.append((min(sup), min(same)))
    allowance_pct, allowance_n = measure_format_allowance(pairs)

    counts = {"catalogue": len(inputs.products), "comparable_population": 0, "matched": 0,
              "structurally_uncomparable": 0, "no_comparison": 0, "evaluated": 0, "breaches": 0,
              "attention": 0, "review": 0, "purchase_cost_findings": 0, "no_cost_skipped": 0,
              "stale_skipped": len(stale_only)}
    entries: list[Entry] = []
    position: dict = {}

    for p in inputs.products:
        b = p["barcode"]
        if b in withdrawn:
            continue
        if _is_structurally_uncomparable(p, policy):
            counts["structurally_uncomparable"] += 1
            continue
        counts["comparable_population"] += 1
        obs = by_barcode.get(b) or []
        if not obs:
            counts["no_comparison"] += 1
            continue
        counts["matched"] += 1

        for o in obs:                                              # FR-053 position, incl. cheaper
            row = position.setdefault(o["store_id"], {"store_id": o["store_id"], "store_name": o["store_name"],
                                                      "format": o["store_format"], "affinity": o["affinity"],
                                                      "matched": 0, "cheaper_here": 0, "dearer_here": 0, "_diffs": []})
            row["matched"] += 1
            if p["shelf_price"]:
                diff = (p["shelf_price"] / o["price"] - 1.0) * 100.0
                row["_diffs"].append(diff)
                if diff < 0:
                    row["cheaper_here"] += 1
                elif diff > 0:
                    row["dearer_here"] += 1

        same = [o for o in obs if o["affinity"] >= floor]
        sup = [o for o in obs if o["store_format"] in SUPERMARKET_FORMATS]
        reference = balanced_reference(min((o["price"] for o in same), default=None),
                                       min((o["price"] for o in sup), default=None), allowance_pct)
        if reference is None or not p["shelf_price"]:
            counts["no_comparison"] += 1
            continue
        if p["cost_price"] is None:
            counts["no_cost_skipped"] += 1                          # FR-043d: no judgement without a cost
            continue
        counts["evaluated"] += 1

        premium_pct = (p["shelf_price"] / reference["value"] - 1.0) * 100.0
        sources = [{"store_id": o["store_id"], "store_name": o["store_name"], "format": o["store_format"],
                    "price": o["price"], "observed_at": o["observed_at"],
                    "role": "comparable" if o["affinity"] >= floor else "context"} for o in obs]
        evidence = {"shelf_price": p["shelf_price"], "cost_price": p["cost_price"], "reference": reference,
                    "premium_pct": round(premium_pct, 2), "policy_pct": policy.price_policy_pct,
                    "attention_pct": policy.attention_pct, "cost_floor_pct": policy.cost_floor_pct,
                    "sources": sources, "format_note": "part of any difference is attributable to store format"}

        # FR-043a/b: the cost floor is evaluated BEFORE the policy and cannot be overridden.
        if reference["value"] < p["cost_price"] * (1.0 + policy.cost_floor_pct / 100.0):
            counts["purchase_cost_findings"] += 1
            entries.append(Entry(id=entry_id("competitor.purchase_cost", b),
                                 signal_family="competitor.purchase_cost", capability=CAP, barcode=b,
                                 product_name=p["product_name"], department=p["department"],
                                 action="check_purchase_cost", characterisation="purchase_cost",
                                 evidence=evidence, value=None, attention="review",
                                 ordering_key={"name": "premium_pct", "value": round(premium_pct, 2)}))
            continue
        if premium_pct <= policy.price_policy_pct:
            continue
        counts["breaches"] += 1
        attention = premium_pct > policy.attention_pct
        counts["attention" if attention else "review"] += 1
        entries.append(Entry(id=entry_id("competitor.policy_breach", b), signal_family="competitor.policy_breach",
                             capability=CAP, barcode=b, product_name=p["product_name"],
                             department=p["department"], action="review_policy",
                             characterisation="policy_breach_attention" if attention else "policy_breach_review",
                             evidence=evidence, value=None, attention="today" if attention else "review",
                             ordering_key={"name": "premium_pct", "value": round(premium_pct, 2)}))

    entries.sort(key=lambda e: (0 if e.attention == "today" else 1, -e.ordering_key["value"], e.barcode))
    for row in position.values():
        diffs = row.pop("_diffs")
        row["median_diff_pct"] = round(statistics.median(diffs), 2) if diffs else None
    thresholds = {"policy_pct": policy.price_policy_pct, "attention_pct": policy.attention_pct,
                  "cost_floor_pct": policy.cost_floor_pct, "format_allowance_pct": allowance_pct,
                  "format_allowance_basis_count": allowance_n, "freshness_days": policy.freshness_days,
                  "comparability_floor": floor}
    notes = [] if allowance_pct is not None else ["format_allowance_unmeasurable"]
    figures = [Figure(k, v, "products", ["pos", "competitor"], thresholds) for k, v in counts.items()]
    figures.append(Figure("format_allowance_pct", allowance_pct, "percent", ["competitor"],
                          {"basis_count": allowance_n}))
    out = CapabilityOutput(id=CAP, spec=SPEC, status="available", thresholds=thresholds, counts=counts,
                           entries=entries, figures=figures, notes=notes)
    out.extras = {"position": sorted(position.values(), key=lambda r: (-r["affinity"], r["store_id"]))}
    return out
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/engine/test_competitor_position.py -q`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add src/engine/competitor_position.py tests/engine/test_competitor_position.py
git commit -m "Competitor position as a capability: balanced reference, measured allowance, cost floor first

A cross-format price never stands alone, judgement is against the owner's own
declared policy, and no product whose reference sits below our purchase cost plus
the floor can produce a pricing signal — it becomes a purchase-cost finding."
```

---

### Task 1.6: Margin below cost (unspecified, browse-only)

**Files:**
- Create: `src/engine/margin_below_cost.py`
- Test: `tests/engine/test_margin_below_cost.py`

**Interfaces:**
- Produces: `run(inputs) -> CapabilityOutput` (`id='margin_below_cost'`), entries `characterisation='below_cost'` with `value=Value(cost − shelf, 'per_sale', 'confirmed')` for genuine below-cost products that pass the D-4 artefact test, `actionable=False` and `not_actionable_reason='no_producing_specification'` on **every** entry (SPEC-GAP-A), `counts: {below_cost, thin_margin, excluded_artefact}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_margin_below_cost.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product
from src.engine.margin_below_cost import run


def test_below_cost_carries_a_per_sale_loss_but_is_never_admitted():
    out = run(make_inputs(products=[product("a", shelf=10.0, cost=12.0), product("b", shelf=10.0, cost=9.5),
                                    product("art", shelf=0.01, cost=2.28)]))
    by = {e.barcode: e for e in out.entries}
    assert by["a"].value.amount == 2.0 and by["a"].value.kind == "per_sale"
    assert all(e.actionable is False for e in out.entries)
    assert all(e.not_actionable_reason == "no_producing_specification" for e in out.entries)
    assert "art" not in by and out.counts["excluded_artefact"] == 1


def test_thin_positive_margins_are_counted_not_valued():
    out = run(make_inputs(products=[product("b", shelf=10.0, cost=9.5)]))
    assert out.counts["thin_margin"] == 1
    assert next(e for e in out.entries if e.barcode == "b").value is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/engine/test_margin_below_cost.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/engine/margin_below_cost.py
"""Selling below cost — retained from the current product, admitted by nothing.

No specification produces this signal (design.md §22, SPEC-GAP-A): SPEC-001 §3
scopes it out and no SPEC-008 exists yet. FR-103 admits an entry only when its
producing capability states it is actionable today, and an unspecified capability
cannot. So every entry here is published, browsable, and NOT actionable."""
from __future__ import annotations

from src.engine.inputs import EngineInputs
from src.engine.model import CapabilityOutput, Entry, Figure, Value, entry_id
from src.engine.registry import derive_status

CAP, SPEC = "margin_below_cost", "UNSPECIFIED"
THIN_MARGIN_PCT = 10.0
REASON = "no_producing_specification"


def run(inputs: EngineInputs) -> CapabilityOutput:
    status, reason = derive_status(CAP, inputs)          # never declared (ADR-014)
    if status == "unavailable":
        return CapabilityOutput.unavailable(CAP, SPEC, reason)
    policy, withdrawn = inputs.policy, inputs.withdrawn or set()
    counts = {"below_cost": 0, "thin_margin": 0, "excluded_artefact": 0}
    entries = []
    for p in inputs.products:
        b, shelf, cost = p["barcode"], p["shelf_price"], p["cost_price"]
        if not b or b in withdrawn or shelf is None or cost is None:
            continue
        if shelf < policy.artefact_min_price or cost > policy.artefact_cost_ratio * shelf:
            counts["excluded_artefact"] += 1
            continue
        margin_pct = (shelf - cost) / shelf * 100.0
        if margin_pct >= THIN_MARGIN_PCT:
            continue
        below = cost > shelf
        counts["below_cost" if below else "thin_margin"] += 1
        entries.append(Entry(
            id=entry_id("margin.below_cost", b, "below_cost" if below else "thin_margin"),
            signal_family="margin.below_cost", capability=CAP, barcode=b,
            product_name=p["product_name"], department=p["department"], action="verify_price",
            characterisation="below_cost" if below else "thin_margin",
            evidence={"shelf_price": shelf, "cost_price": cost, "margin_pct": round(margin_pct, 2),
                      "cost_source": p["cost_source"]},
            value=Value(round(cost - shelf, 2), "per_sale", "confirmed") if below else None,
            ordering_key={"name": "loss_per_sale", "value": round(cost - shelf, 2) if below else round(margin_pct, 2)},
            actionable=False, not_actionable_reason=REASON))
    entries.sort(key=lambda e: (0 if e.characterisation == "below_cost" else 1, -e.ordering_key["value"], e.barcode))
    figures = [Figure(k, v, "products", ["pos"]) for k, v in counts.items()]
    return CapabilityOutput(id=CAP, spec=SPEC, status="available",
                            thresholds={"thin_margin_pct": THIN_MARGIN_PCT}, counts=counts,
                            entries=entries, figures=figures, notes=[f"not_admitted:{REASON}"])
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/engine/test_margin_below_cost.py -q`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/engine/margin_below_cost.py tests/engine/test_margin_below_cost.py
git commit -m "Keep below-cost as a browse-only capability until a specification exists

SPEC-GAP-A: the intent names margins as money-bearing but no spec produces the
signal, and FR-103 admits nothing whose producing capability cannot state
actionability. Published and browsable, never on the morning screen."
```

---

### Task 1.7: Surface candidates and provenance

**Files:**
- Create: `src/engine/surface_candidates.py`
- Create: `src/engine/provenance.py`
- Test: `tests/engine/test_surface_candidates.py`

**Interfaces:**
- Produces: `stamp(outputs: list[CapabilityOutput], inputs) -> list[CapabilityOutput]` — sets `actionable` on every entry per FR-103 conditions (1) present in this run, (2) evidence complete, (4) clears any materiality floor; sets `not_actionable_reason` otherwise; never touches `margin_below_cost` (already false) or `owner_questions` (no entries).
- `REQUIRED_EVIDENCE: dict[capability, tuple[str, ...]]` — the keys FR-110 demands per capability.
- `provenance.vintage_figures(inputs) -> list[Figure]` — `pos_as_of`, `sales_months`, `competitor_snapshot_age_days`, `owner_state_available`.

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_surface_candidates.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from helpers import make_inputs, product
from src.engine.model import CapabilityOutput, Entry
from src.engine.surface_candidates import stamp


def _entry(cap, evidence, **kw):
    return Entry(id="i", signal_family=kw.get("family", "price.inverted"), capability=cap,
                 barcode="1", product_name="p", department="d",
                 action=kw.get("action", "verify_price"), characterisation=kw.get("ch", "question"),
                 evidence=evidence, value=None, ordering_key={"name": "k", "value": 1.0})


def test_ac_110a_an_entry_missing_required_evidence_is_not_actionable():
    complete = _entry("price_consistency", {"shelf_price": 1.0, "delivery_price": 2.0, "difference": 1.0, "markup_pct": 100.0})
    incomplete = _entry("price_consistency", {"shelf_price": 1.0})
    out = CapabilityOutput(id="price_consistency", spec="SPEC-001", status="available", entries=[complete, incomplete])
    stamp([out], make_inputs(products=[product("1")]))
    assert complete.actionable is True
    assert incomplete.actionable is False and incomplete.not_actionable_reason == "evidence_incomplete"


def test_entries_of_an_unavailable_capability_are_never_actionable():
    e = _entry("reconciliation", {"recorded_stock": 1, "receipts": 1, "units_sold": 1, "unaccounted": 1, "window_id": "w"},
               family="recon.impossible_opening")
    out = CapabilityOutput(id="reconciliation", spec="SPEC-002", status="unavailable",
                           unavailable_reason="no_sales_evidence", entries=[e])
    stamp([out], make_inputs(products=[product("1")]))
    assert e.actionable is False and e.not_actionable_reason == "capability_unavailable"


def test_hygiene_entries_are_admitted_on_their_own_evidence():
    """Hygiene needs one key — the reason. It must not inherit reconciliation's evidence
    list, or every hygiene record would be stamped evidence_incomplete and never surface."""
    e = _entry("hygiene", {"reason": "negative_stock", "recorded_stock": -3.0},
               family="hygiene.negative_stock", action="fix_record", ch="hygiene")
    out = CapabilityOutput(id="hygiene", spec="SPEC-002", status="available", entries=[e])
    stamp([out], make_inputs(products=[product("1")]))
    assert e.actionable is True


def test_margin_below_cost_stays_unadmitted():
    e = _entry("margin_below_cost", {"shelf_price": 1.0, "cost_price": 2.0, "margin_pct": -100.0},
               family="margin.below_cost")
    e.actionable, e.not_actionable_reason = False, "no_producing_specification"
    out = CapabilityOutput(id="margin_below_cost", spec="UNSPECIFIED", status="available", entries=[e])
    stamp([out], make_inputs(products=[product("1")]))
    assert e.actionable is False and e.not_actionable_reason == "no_producing_specification"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/engine/test_surface_candidates.py -q`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/engine/surface_candidates.py
"""FR-103 conditions (1), (2) and (4), stamped by the producing side.

Condition (3) — no owner outcome still stands — is applied in the browser, where
an outcome recorded a minute ago is known (ADR-006)."""
from __future__ import annotations

from src.engine.registry import CAPABILITIES

REQUIRED_EVIDENCE = {
    "price_consistency": ("shelf_price", "delivery_price", "difference", "markup_pct"),
    "reconciliation": ("recorded_stock", "receipts", "units_sold", "unaccounted", "window_id"),
    "hygiene": ("reason",),          # the record is wrong on its own evidence; nothing else is needed
    "competitor_position": ("shelf_price", "reference", "premium_pct", "sources"),
    "catalogue_lifecycle": ("evidence_state", "window_id"),
    "margin_below_cost": ("shelf_price", "cost_price", "margin_pct"),
}


def stamp(outputs, inputs):
    for out in outputs:
        spec = CAPABILITIES.get(out.id)
        required = REQUIRED_EVIDENCE.get(out.id, ())
        for e in out.entries:
            if e.not_actionable_reason == "no_producing_specification" or (spec and not spec.admitted):
                e.actionable = False
                e.not_actionable_reason = e.not_actionable_reason or "not_admitted"
                continue
            if out.status != "available":
                e.actionable, e.not_actionable_reason = False, "capability_unavailable"
                continue
            if any(k not in e.evidence or e.evidence[k] is None for k in required):
                e.actionable, e.not_actionable_reason = False, "evidence_incomplete"
                continue
            e.actionable, e.not_actionable_reason = True, None
    return outputs
```

```python
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
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/engine/test_surface_candidates.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/engine/surface_candidates.py src/engine/provenance.py tests/engine/test_surface_candidates.py
git commit -m "Stamp admission on the producing side and register the input vintages

An entry whose own specification's evidence is incomplete never reaches the
surface: an unverifiable entry costs one of ten places."
```

---

### Task 1.8: Wire the capabilities into the run

**Files:**
- Modify: `src/engine/run.py` — populate `DEFAULT_RUNNERS`, pass `idle`, attach `position`, stamp before publishing, add vintage figures
- Test: `tests/engine/test_run_capabilities.py`

**Interfaces:**
- `DEFAULT_RUNNERS = {'catalogue_lifecycle': …, 'price_consistency': …, 'reconciliation': …, 'hygiene': …, 'competitor_position': …, 'margin_below_cost': …, 'owner_questions': …}` — seven entries, one per registry id; dict order is the run order after `catalogue_lifecycle`. `reconciliation` and `hygiene` are two entries pointing into the same module, which is what gives each its own step, its own isolation and its own status.
- Once `DEFAULT_RUNNERS` is non-empty the publisher's registry-completeness assertion turns itself on (Task 0.4): a real run that drops a capability now refuses to publish instead of rendering it as "nothing to act on".

- [ ] **Step 1: Write the failing test**

```python
# tests/engine/test_run_capabilities.py
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import src.engine.run as run_mod
from helpers import make_inputs, product, summary, window_of
from src.owner_state.model import OwnerState

W = window_of(["2026-01", "2026-02"])


def _stub_inputs(monkeypatch):
    inputs = make_inputs(
        products=[product("live", shelf=10.0, delivery=10.0, cost=4.0, stock=2.0),
                  product("dead", shelf=5.0, cost=1.0, stock=0.0),
                  product("idle", shelf=5.0, cost=None, stock=7.0)],
        sales_summary=[summary("live", units=10, receipts=5)], sales_monthly=[{"barcode": "live", "month": "2026-01",
                                                                              "units": 10, "receipts": 5, "revenue": 100.0}],
        window=W, owner=OwnerState.from_dict({"status": "available", "pulled_at": "t"}))
    monkeypatch.setattr(run_mod, "_pull_owner_state", lambda: inputs.owner)
    monkeypatch.setattr(run_mod, "_sales_import", lambda: {"window": W.to_dict()})
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "load_inputs", lambda **kw: inputs)
    return inputs


def test_the_withdrawn_set_reaches_the_other_capabilities(tmp_path, monkeypatch):
    _stub_inputs(monkeypatch)
    result = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json",
                                now=datetime(2026, 9, 8, tzinfo=timezone.utc))
    caps = result["artefact"]["capabilities"]
    assert caps["catalogue_lifecycle"]["counts"]["withdrawable"] == 1
    # 'dead' is withdrawn, so it is absent from the question suppression population…
    assert caps["owner_questions"]["suppressed"]["withdrawn"] == 1
    # …and from the idle set, which suppresses the other cost question.
    assert caps["owner_questions"]["suppressed"]["idle"] == 1


def test_the_artefact_carries_every_capability_with_its_extras_and_vintages(tmp_path, monkeypatch):
    _stub_inputs(monkeypatch)
    art = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "d.json",
                             now=datetime(2026, 9, 8, tzinfo=timezone.utc))["artefact"]
    caps = art["capabilities"]
    assert caps["catalogue_lifecycle"]["window"]["window_id"] == "2026-01..2026-02"
    assert caps["owner_questions"]["limit"] == 3
    assert "provenance.sales_months" in art["figures"]
    # Exactly the registry: catalogue and questions are capabilities like any other (ADR-014),
    # and hygiene is its own — so the publisher's status rule runs over all seven.
    assert set(caps) == {"catalogue_lifecycle", "price_consistency", "reconciliation", "hygiene",
                         "competitor_position", "margin_below_cost", "owner_questions"}
    assert all(c["status"] in ("available", "unavailable") for c in caps.values())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/engine/test_run_capabilities.py -q`
Expected: FAIL — capabilities are empty

- [ ] **Step 3: Implement**

In `src/engine/run.py`, replace `DEFAULT_RUNNERS: dict[str, Callable] = {}` with:

```python
def _runners() -> dict:
    from src.engine import (catalogue_lifecycle, competitor_position, margin_below_cost,
                            owner_questions, price_consistency, reconciliation)
    return {"catalogue_lifecycle": catalogue_lifecycle.run, "price_consistency": price_consistency.run,
            "reconciliation": reconciliation.run, "hygiene": reconciliation.run_hygiene,
            "competitor_position": competitor_position.run,
            "margin_below_cost": margin_below_cost.run, "owner_questions": owner_questions.run}


DEFAULT_RUNNERS: dict = {}          # populated lazily by run_engine
```

In `run_engine`, replace `runners = DEFAULT_RUNNERS if capability_runners is None else capability_runners` with `runners = _runners() if capability_runners is None else capability_runners`; inside the capability loop, after `catalogue_lifecycle` succeeds, set both hand-offs and the catalogue block:

```python
            if cap_id == "catalogue_lifecycle" and out.status == "available":
                inputs.withdrawn = getattr(out, "withdrawn_barcodes", set())
                inputs.idle = getattr(out, "idle_barcodes", set())
```

Before `build_artefact`, stamp and add vintage figures:

```python
    extra_figures = []
    if inputs is not None:
        from src.engine.provenance import vintage_figures
        from src.engine.surface_candidates import stamp
        stamp(outputs, inputs)
        extra_figures = vintage_figures(inputs)      # figures, NOT a capability
```

and pass them to the publisher:

```python
    artefact = build_artefact(outputs, vintages=inputs.vintages if inputs else _no_inputs_vintages(owner),
                              thresholds=policy.as_dict(), run={"status": status, "steps": steps},
                              extra_figures=extra_figures, generated_at=now.isoformat(),
                              run_id=uuid.uuid4().hex[:12])
```

Provenance is deliberately **not** registered as a capability: `capabilities{}` is exactly the
registry id set (ADR-014), and provenance has no entries, no status of its own and nothing the
owner can act on. Its output is the `figures{}` block.

- [ ] **Step 4: Run the whole engine suite**

Run: `python3 -m pytest tests/engine tests/owner_state tests/internal_pos -q`
Expected: all pass

- [ ] **Step 5: Run against the real pilot data (Checkpoint 1)**

Run: `python3 scripts/run_engine.py --skip-market --json-out /tmp/run.json && python3 -c "
import json; a=json.load(open('public/data/dashboard.json'))
print('kinds', a['value_kinds_present'])
for k,c in a['capabilities'].items(): print(k, c['status'], c['unavailable_reason'] or '', {x:y for x,y in list(c['counts'].items())[:4]})
c = a['capabilities']
print('catalogue', c['catalogue_lifecycle']['counts'])
print('questions', len(c['owner_questions'].get('items', [])))"`

Expected (design §3.5): `value_kinds_present ['per_sale']`; seven capability keys; price_consistency ceiling 18 %, inverted 68; reconciliation flagged ≈ 458 with `flagged` an integer; hygiene ≈ 625 negative stock / 307 no identifier / 223 absent price; catalogue living ≈ 1,565 / withdrawable ≈ 4,4xx / idle ≈ 1,69x; questions a single-digit list. Record the actual numbers in the commit body — they are the figures the 12/9 meeting will use, and per CLAUDE.md rule 11 they are read from the artefact, never from a document.

- [ ] **Step 6: Commit**

```bash
git add src/engine/run.py tests/engine/test_run_capabilities.py
git commit -m "Run all seven capabilities in dependency order and publish one artefact

catalogue_lifecycle runs first so its withdrawn and idle sets reach every other
capability's population and counts (FR-074), and admission is stamped before the
publisher's assertions. reconciliation and hygiene are two runners over one
module, each stepped and reported on its own — the arrangement SPEC-002 §11 needs.
With DEFAULT_RUNNERS populated, the registry-completeness assertion turns itself
on: a run that silently drops a capability now refuses to publish."
```


---

### Task 1.9: The rule-12 independence probe (Checkpoint 1)

**Files:**
- Create: `scripts/check_independence.py`
- Modify: `package.json` — `"check:independence": "python3 scripts/check_independence.py"`

**Why this exists.** Every test in Task 1.1 hands each function its inputs directly, so not one
of them crosses `inputs.py` or `run.py`. That is the boundary where four signals in this
repository have already been lost — built, unit-tested, labelled working, and changing nothing
(CLAUDE.md rule 12). The split of SPEC-002 into two capabilities would be the fifth if the only
evidence for it were a unit test. Design §14 and §18 name this probe as the proof.

**It must drive the whole engine, not the module.** Calling `reconciliation.run_hygiene(inputs)`
directly would supply the input by hand and prove nothing — the exact defect rule 12 describes.
The probe calls `run_engine(mode='print', …)` over a *copy* of the data with the monthly reports
withheld at their source, and reads `artefact['capabilities']`. That path crosses `inputs.py`,
the registry, the orchestrator and the publisher's assertions.

**What "unaffected" does and does not mean.** SPEC-002 §11 and design §14 claim exactly this:
detection goes unavailable, hygiene stays available with a non-zero count. Hygiene's counts are
**not** required to be identical, and asserting that they are would make the probe fail for a
correct reason: `_hygiene_entries` skips `inputs.withdrawn`, which `catalogue_lifecycle` produces
and which is `None` when the reports are missing (INV-036 — no set means no exclusion), so
hygiene's population *grows* to the whole catalogue. The right assertion is containment: every
hygiene finding of the full run must still be present, with the same entry id, in the withheld
run. That is what "unaffected" can honestly mean here, and it still fails loudly if the split
ever couples hygiene to the sales evidence.

**Interfaces:**
- Two `run_engine(mode='print')` runs over copied directories: one whole, one with an empty sales-report directory. Asserts, and exits 1 naming the failure:
  1. whole run — `reconciliation` available with `flagged > 0`; `hygiene` available with a non-zero count;
  2. reports withheld — `reconciliation` **unavailable** with `no_sales_evidence` and no entries, while `hygiene` is still **available** with a non-zero count;
  3. every hygiene entry id from the whole run is still present in the withheld run.

- [ ] **Step 1: Write the probe**

```python
#!/usr/bin/env python3
"""Prove the two halves of SPEC-002 fail independently, across the real boundary.

SPEC-002 §11: when the sales reports do not arrive, detection is unavailable and the hygiene
signals are unaffected. ADR-014 makes that a computed consequence of two `requires` lists. This
probe shows the computation survives contact with `inputs.py` and `run.py` — the place where a
signal quietly stops arriving (CLAUDE.md rule 12). It runs the engine twice over copies of the
data and reads the published artefact, never a module's return value."""
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import src.engine.run as run_mod


def _fail(message: str) -> None:
    print(f"FAIL  {message}")
    sys.exit(1)


def _run(silver_dir: Path, sales_dir: Path) -> dict:
    result = run_mod.run_engine(mode="print", skip_market=True, silver_dir=silver_dir,
                                sales_dir=sales_dir, now=datetime.now(timezone.utc))
    return result["artefact"]["capabilities"]


def _ids(capability: dict) -> set:
    return {e["id"] for e in capability["entries"]}


def _total(capability: dict) -> int:
    return sum(v for v in capability["counts"].values() if isinstance(v, int))


def main() -> None:
    if not (run_mod.SILVER_DIR / "yomyom_products.parquet").exists():
        _fail(f"no silver tables under {run_mod.SILVER_DIR}: import the POS export first "
              f"(python3 scripts/import_yomyom_pos.py --input <csv>)")

    with tempfile.TemporaryDirectory() as tmp:
        whole_silver = Path(tmp) / "silver_whole"
        withheld_silver = Path(tmp) / "silver_withheld"
        no_reports = Path(tmp) / "sales_none"
        shutil.copytree(run_mod.SILVER_DIR, whole_silver)
        shutil.copytree(run_mod.SILVER_DIR, withheld_silver)
        no_reports.mkdir()                       # the seven monthly reports simply did not arrive

        whole = _run(whole_silver, run_mod.SALES_DIR)
        withheld = _run(withheld_silver, no_reports)

    recon_w, hyg_w = whole["reconciliation"], whole["hygiene"]
    if recon_w["status"] != "available" or not recon_w["counts"].get("flagged"):
        _fail(f"detection should be available with findings on the real data, got "
              f"{recon_w['status']} / {recon_w['counts']}")
    if hyg_w["status"] != "available" or not _total(hyg_w):
        _fail(f"hygiene should be available with findings on the real data, got "
              f"{hyg_w['status']} / {hyg_w['counts']}")

    recon, hyg = withheld["reconciliation"], withheld["hygiene"]
    if recon["status"] != "unavailable" or recon["unavailable_reason"] != "no_sales_evidence":
        _fail(f"detection must be unavailable without the reports, got {recon['status']} "
              f"/ {recon['unavailable_reason']}")
    if recon["entries"]:
        _fail(f"an unavailable capability published {len(recon['entries'])} entries")
    if hyg["status"] != "available":
        _fail(f"hygiene must survive a missing sales report, got {hyg['status']} "
              f"/ {hyg['unavailable_reason']} — this is the coupling SPEC-002 §11 forbids")
    if not _total(hyg):
        _fail("hygiene is available but publishes nothing without the reports")
    lost = _ids(hyg_w) - _ids(hyg)
    if lost:
        _fail(f"{len(lost)} hygiene findings disappeared when the reports were withheld, "
              f"e.g. {sorted(lost)[:3]} — the owner's recorded outcomes would stop matching "
              f"on a day a report is late")

    print(f"OK    detection {recon_w['counts']['flagged']} flagged with the reports, "
          f"unavailable ({recon['unavailable_reason']}) without them")
    print(f"OK    hygiene {_total(hyg_w)} records with the reports, {_total(hyg)} without, "
          f"none lost (the withheld run excludes no withdrawn products, INV-036)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it, then break it on purpose**

Run: `npm run check:independence`
Expected: two `OK` lines with the real counts.

Then add `"sales_summary"` to `hygiene`'s `requires` in `src/engine/registry.py` and run it again: it
must fail with *hygiene must survive a missing sales report*. Revert. A probe that has never failed
is not evidence — that is the whole content of rule 12.

- [ ] **Step 3: Commit**

```bash
git add scripts/check_independence.py package.json
git commit -m "Probe that hygiene survives a missing sales report, through the whole engine

Four signals in this repository have shipped unit-tested and moved nothing, because
every test supplied the input directly and never crossed the boundary where it was
lost (rule 12). SPEC-002 §11 is exactly that shape of claim, so it gets a probe that
withholds the monthly reports at source and reads the published artefact: detection
must go unavailable and every hygiene finding must still be there under the same id."
```

**Where this runs in CI.** Not in `ci.yml`: that workflow runs on push with no `data/**`, and the
probe needs the silver tables. Its home is `collect-daily.yml`, beside `check:signals`, which
already runs there against real data before the dashboard is committed. Phase 3 wires it in
(design §14 lists it among the V1 signal probes); until then it is a Checkpoint 1 gate run by hand.

**Checkpoint 1 is met when:** every AC test for SPEC-001 … SPEC-005 passes, `npm run check:independence`
passes *and has been seen to fail* on the deliberate break above, and a real run publishes seven
capabilities each carrying a status.
