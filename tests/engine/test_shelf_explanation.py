"""Phase 8 Task 8.10: the AI's explanation of each fixture's plan (D-32; F12-S1 FR-210 … FR-215,
INV-096, INV-097, NFR-077; AC-199 … AC-204). The model is a fake transport: no test calls a network."""
from __future__ import annotations

import json
import textwrap
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import pytest
from helpers import make_inputs, product

from src.engine import shelf_explanation as se
from src.engine import shelf_plan
from src.engine.store_layout import load_store_layout

RUN_AT = datetime(2026, 10, 12, 3, 0, tzinfo=timezone.utc)
LAST = date(2026, 10, 11)
GOOD = json.dumps({"he": "המוצרים שמרוויחים הכי הרבה עומדים בגובה העיניים.",
                   "ar": "المنتجات الأكثر ربحاً في مستوى النظر.",
                   "en": "The products that earn the most stand at eye level."}, ensure_ascii=False)


class Fake:
    def __init__(self, answers=(GOOD,), status=200):
        self.answers, self.status, self.calls = list(answers), status, 0

    def __call__(self, url, headers, body, timeout):
        self.calls += 1
        self.last = json.loads(body)
        text = self.answers[min(self.calls - 1, len(self.answers) - 1)]
        return self.status, json.dumps({"content": [{"type": "text", "text": text}]}).encode()


CAT = [product("1", name="Cola 1.5L", department="drinks", shelf=10.0, cost=4.0, stock=5.0),
       product("2", name="Water", department="drinks", shelf=10.0, cost=6.0, stock=5.0),
       product("3", name="Soap", department="cleaning", shelf=10.0, cost=6.0, stock=5.0)]


def _daily(last=LAST):
    return [{"barcode": b, "day": (last - timedelta(days=k)).isoformat(), "units": 2.0, "receipts": None}
            for k in range(28) for b in ("1", "2", "3")]


def _inputs(tmp_path, *, run_at=RUN_AT, explanations=None, policy=None, last=LAST):
    measured = "measured_by: team, measured_on: 2026-10-01"
    body = textwrap.dedent(f"""\
        fixtures:
          F1:
            departments: [drinks]
            chilled: true
            eye_level_shelf: 1
            stated_by: owner
            stated_on: 2026-10-01
            recorded_by: team
            shelves:
              - {{length_cm: 100, {measured}}}
          F2:
            departments: [cleaning]
            chilled: false
            stated_by: owner
            stated_on: 2026-10-01
            recorded_by: team
            shelves:
              - {{length_cm: 100, {measured}}}
        widths:
          "1": {{width_mm: 100, {measured}}}
          "2": {{width_mm: 100, {measured}}}
          "3": {{width_mm: 100, {measured}}}
        """)
    path = tmp_path / "store_layout.yaml"
    path.write_text(body, encoding="utf-8")
    inputs = make_inputs(products=CAT, sales_daily=_daily(last), run_at=run_at,
                         store_layout=load_store_layout(path, CAT), policy=policy)
    inputs.shelf_explanations = explanations
    return inputs


def _seal(tmp_path, inputs, transport, **kw):
    return se.live_step(inputs, snapshots_root=tmp_path / "snap", key="k", transport=transport, now=inputs.run_at, **kw)


def _published(tmp_path, inputs):
    inputs.shelf_explanations = se.read(tmp_path / "snap", inputs.run_at.date().isoformat())
    return se.run(inputs)


# ── What the model is given (FR-211, AC-202) ─────────────────────────────────

def _numbers(obj, path=""):
    if isinstance(obj, bool):
        return []
    if isinstance(obj, (int, float)):
        return [path]
    if isinstance(obj, dict):
        return [p for k, v in obj.items() for p in _numbers(v, k)]
    if isinstance(obj, list):
        return [p for v in obj for p in _numbers(v, path)]
    return []


def test_the_request_carries_only_the_plans_facts_and_its_only_numbers_are_allowed_ones(tmp_path):
    inputs = _inputs(tmp_path)
    entry = shelf_plan.run(inputs).entries[0].to_dict()
    f = se.facts(entry, {p["barcode"]: p["product_name"] for p in CAT})
    assert set(_numbers(f)) <= {"facings", "shelf", "value"}            # facings, shelf positions, the elasticity
    text = json.dumps(f, ensure_ascii=False)
    for word in ("margin", "price", "cost", "daily_mean", "barcode", "₪"):
        assert word not in text
    assert f["earnings_order"] and "Cola 1.5L" in f["earnings_order"]


def test_the_prompt_asks_for_the_four_parts(tmp_path):
    # AC-204's request half: why eye level, why more facings, why not placed, on which rule.
    prompt = (se.ROOT / "configs" / "prompts" / "shelf_explanation.v1.md").read_text(encoding="utf-8")
    for part in ("at eye level", "more facings", "not on the plan", "rule or research finding"):
        assert part in prompt


# ── The check (FR-212, AC-200, SCN-177) ──────────────────────────────────────

def test_a_digit_inside_a_product_name_passes_and_one_outside_withholds_it_whole():
    names = ["Cola 1.5L", "Cola"]
    ok = json.dumps({"he": "Cola 1.5L בגובה העיניים", "ar": "Cola 1.5L", "en": "Cola 1.5L earns most"})
    assert se.check(ok, names, 600)["accepted"] is True
    bad = json.dumps({"he": "ימכור 20% יותר", "ar": "حسن", "en": "fine"})
    assert se.check(bad, names, 600) == {"accepted": False, "text": None, "withheld_because": "stated_a_figure"}
    arabic_digit = json.dumps({"he": "טוב", "ar": "٢٠ أكثر", "en": "fine"})
    assert se.check(arabic_digit, names, 600)["withheld_because"] == "stated_a_figure"


def test_a_changed_name_keeps_its_digits_and_fails():
    names = ["Cola 1.5L"]
    changed = json.dumps({"he": "Cola 1.5 L", "ar": "x", "en": "x"})
    assert se.check(changed, names, 600)["withheld_because"] == "stated_a_figure"


def test_an_answer_that_does_not_parse_or_is_too_long_is_withheld():
    assert se.check("not json", [], 600)["withheld_because"] == "did_not_parse"
    assert se.check(json.dumps({"he": "x", "en": "y"}), [], 600)["withheld_because"] == "did_not_parse"
    assert se.check(json.dumps({"he": "x" * 601, "ar": "x", "en": "x"}), [], 600)["withheld_because"] == "too_long"


# ── Sealed, reproduced, reused (FR-213, INV-097, AC-201, AC-203) ─────────────

def test_it_is_written_once_a_night_and_shown_in_three_languages(tmp_path):
    inputs, fake = _inputs(tmp_path), Fake()
    assert _seal(tmp_path, inputs, fake)["requests_made"] == 2 and fake.calls == 2
    assert fake.last["max_tokens"] == 1200 and fake.last["model"] == inputs.policy.boost_model
    _seal(tmp_path, inputs, fake)                                         # merge never replace
    assert fake.calls == 2
    out = _published(tmp_path, inputs)
    assert out.status == "available" and out.counts["explained"] == 2
    assert set(out.extras["explanations"][0]["text"]) == {"he", "ar", "en"}


def test_an_unchanged_plan_is_not_paid_for_twice_and_a_withheld_answer_is_asked_again(tmp_path):
    day1 = _inputs(tmp_path)
    _seal(tmp_path, day1, Fake([GOOD, "not json"]))                       # F1 accepted, F2 withheld
    day2 = _inputs(tmp_path, run_at=RUN_AT + timedelta(days=1), last=LAST)
    fake = Fake()
    result = _seal(tmp_path, day2, fake)
    assert result["reused"] == 1 and fake.calls == 1                     # F2 asked again
    out = _published(tmp_path, day2)
    reused = [e for e in out.extras["explanations"] if e["reused_from"]]
    assert len(reused) == 1 and reused[0]["reused_from"] == RUN_AT.date().isoformat()


def test_a_new_prompt_asks_again(tmp_path):
    day1 = _inputs(tmp_path)
    _seal(tmp_path, day1, Fake())
    path = se.folder(tmp_path / "snap", RUN_AT.date().isoformat()) / "explanations.json"
    sealed = json.loads(path.read_text(encoding="utf-8"))
    for record in sealed.values():
        record["prompt_sha256"] = "an-older-prompt"
    path.write_text(json.dumps(sealed), encoding="utf-8")
    fake = Fake()
    _seal(tmp_path, _inputs(tmp_path, run_at=RUN_AT + timedelta(days=1)), fake)
    assert fake.calls == 2


def test_an_explanation_written_for_other_facts_is_not_shown(tmp_path):
    inputs = _inputs(tmp_path)
    _seal(tmp_path, inputs, Fake())
    path = se.folder(tmp_path / "snap", RUN_AT.date().isoformat()) / "explanations.json"
    sealed = json.loads(path.read_text(encoding="utf-8"))
    next(iter(sealed.values()))["inputs_digest"] = "facts-of-another-plan"
    path.write_text(json.dumps(sealed), encoding="utf-8")
    out = _published(tmp_path, inputs)
    assert sorted(e["why_none"] or "" for e in out.extras["explanations"]) == ["", "out_of_date"]


# ── Bounded (FR-214, NFR-077, AC-203) ────────────────────────────────────────

def test_past_the_ceiling_the_rest_wait_for_another_night(tmp_path):
    policy = replace(_inputs(tmp_path).policy, shelf_explanation_request_ceiling=1)
    inputs, fake = _inputs(tmp_path, policy=policy), Fake()
    result = _seal(tmp_path, inputs, fake)
    assert fake.calls == 1 and result["requests_made"] == 1
    assert {e["why_none"] for e in _published(tmp_path, inputs).extras["explanations"]} == {None, "not_written_tonight"}


def test_past_the_time_budget_nothing_more_is_asked(tmp_path):
    ticks = iter([0.0, 0.0, 10_000.0, 10_000.0])
    inputs, fake = _inputs(tmp_path), Fake()
    _seal(tmp_path, inputs, fake, clock=lambda: next(ticks))
    assert fake.calls == 1


def test_a_request_that_fails_twice_ends_the_nights_asking(tmp_path, monkeypatch):
    import src.engine.model_client as mc
    monkeypatch.setattr(mc, "RETRY_PAUSE_S", 0.0)
    inputs, fake = _inputs(tmp_path), Fake(status=500)
    result = _seal(tmp_path, inputs, fake)
    assert fake.calls == 2 and result["requests_made"] == 0 and result["error"]   # one request, retried once
    assert {e["why_none"] for e in _published(tmp_path, inputs).extras["explanations"]} == {"not_written_tonight"}


# ── Never an input to the plan (FR-214, INV-096, AC-199) ─────────────────────

def test_without_the_snapshot_it_says_no_model_key_and_every_plan_is_unchanged(tmp_path):
    inputs = _inputs(tmp_path)
    _seal(tmp_path, inputs, Fake())
    with_text = _inputs(tmp_path, explanations=se.read(tmp_path / "snap", RUN_AT.date().isoformat()))
    without = _inputs(tmp_path)
    assert se.run(without).unavailable_reason == "no_model_key"
    strip = lambda out: [e.to_dict() for e in out.entries]              # noqa: E731
    assert strip(shelf_plan.run(with_text)) == strip(shelf_plan.run(without))


def test_it_is_unavailable_with_the_plans_own_reason():
    inputs = make_inputs(products=CAT, sales_daily=_daily(LAST - timedelta(days=30)), run_at=RUN_AT)
    assert se.run(inputs).unavailable_reason == "no_store_layout"


def test_print_mode_never_asks(tmp_path):
    # AC-201: no key, no request; the live step is publish mode's alone, and without a key writes nothing.
    fake = Fake()
    assert se.live_step(_inputs(tmp_path), snapshots_root=tmp_path / "snap", key=None, transport=fake,
                        now=RUN_AT)["skipped"] == "no_model_key"
    assert fake.calls == 0 and not (tmp_path / "snap").exists()
