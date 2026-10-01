# tests/engine/test_market_boost.py
"""Phase 5 Task 5.6: the model-picked boost (ADR-032) and its sealed snapshot (ADR-035).

Every test uses a fake transport. The real one is never constructed here: a test that could
reach the network could also spend the owner's money.
"""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from helpers import make_inputs, product
from src.engine import market_boost as mb
from src.engine import market_running_out as mro
from src.engine.policy import load_policy
from src.engine.registry import CAPABILITIES, INPUT_REASONS

POLICY = load_policy()
LAST = date(2026, 10, 28)
RUN_AT = datetime(2026, 10, 28, 3, tzinfo=timezone.utc)
DAYS = [(LAST - timedelta(days=i)).isoformat() for i in range(28)]
DEPT, NO_FACTS = "משקאות", "מאפים"
FACTS = {"facts": {DEPT: {"order_schedule": {"form": "weekdays", "weekdays": ["sun"]},
                          "shelf_life": {"days": 30}, "stated_by": "owner",
                          "stated_on": "2026-10-01", "recorded_by": "team"}},
         "rejected": []}


def daily(barcode, units=2.0, days=DAYS):
    return [{"barcode": barcode, "day": d, "units": units, "receipts": 0.0} for d in days]


def signal(*barcodes, on_day=LAST.isoformat()):
    return {"on_day": on_day, "stores": ["s1", "s2"], "excluded": [],
            "products": {b: {"stores_out": ["s1"], "days_absent": {"s1": 3}} for b in barcodes}}


def inputs(*, products=None, rows=None, running=None, picks=None, policy=POLICY, facts=FACTS):
    products = products if products is not None else [product("a", name="מים", department=DEPT)]
    return make_inputs(products=products, sales_daily=rows if rows is not None else daily("a"),
                       running_out=running if running is not None else signal("a"),
                       store_facts=facts, boost_picks=picks, policy=policy, run_at=RUN_AT)


class Fake:
    """Answers per barcode; an Exception instance is raised instead of answering."""

    def __init__(self, answers=None, default='{"boost_pct": 10, "reason": "المحلات القريبة نفدت منها"}'):
        self.answers, self.default, self.calls = answers or {}, default, []

    def __call__(self, url, headers, body, timeout):
        request = json.loads(body)
        facts = json.loads(request["messages"][0]["content"])
        self.calls.append({"url": url, "headers": headers, "request": request, "facts": facts})
        answer = self.answers.get(facts["barcode"], self.default)
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, tuple):
            return answer
        return 200, json.dumps({"content": [{"type": "text", "text": answer}]}).encode()


# ── The check (ADR-032 Decision 4) ───────────────────────────────────────────

@pytest.mark.parametrize("raw,accepted,because", [
    ('{"boost_pct": 10, "reason": "ok"}', True, None),
    ('{"boost_pct": 0, "reason": "ok"}', True, None),
    ('{"boost_pct": 25, "reason": "ok"}', True, None),
    ('{"boost_pct": 25.5, "reason": "ok"}', False, "above_limit"),
    ('{"boost_pct": 40, "reason": "ok"}', False, "above_limit"),
    ('{"boost_pct": -1, "reason": "ok"}', False, "below_zero"),
    ('{"boost_pct": "abc", "reason": "ok"}', False, "not_a_number"),
    ('{"boost_pct": true, "reason": "ok"}', False, "not_a_number"),
    ('{"boost_pct": NaN, "reason": "ok"}', False, "not_a_number"),
    ('{"reason": "ok"}', False, "not_a_number"),
    ("not json", False, "unparseable"),
    ('```json\n{"boost_pct": 10}\n```', False, "unparseable"),
    ("[10]", False, "unparseable"),
])
def test_a_pick_is_accepted_only_from_0_to_25_and_never_clipped(raw, accepted, because):
    out = mb.check(raw, POLICY.boost_max_pct)
    assert out["accepted"] is accepted and out.get("rejected_because") == because
    if because == "above_limit":
        assert out["boost_pct"] > 25                     # what the model said, never 25


@pytest.mark.parametrize("reason", ["نفدت منذ 3 أيام", "نفدت منذ ٣ أيام", "نفدت منذ ۳ أيام", "up 10%"])
def test_a_reason_stating_a_figure_is_withheld_and_the_pick_stands(reason):
    out = mb.check(json.dumps({"boost_pct": 10, "reason": reason}), POLICY.boost_max_pct)
    assert out["accepted"] is True and out["boost_pct"] == 10
    assert out["reason"] is None and out["reason_withheld_because"] == "states_a_figure"


def test_a_reason_too_long_is_withheld():
    out = mb.check(json.dumps({"boost_pct": 5, "reason": "أ" * 161}), POLICY.boost_max_pct)
    assert out["reason"] is None and out["reason_withheld_because"] == "too_long"


def test_a_plain_reason_is_kept():
    out = mb.check('{"boost_pct": 5, "reason": "المحلات القريبة نفدت منها"}', POLICY.boost_max_pct)
    assert out["reason"] == "المحلات القريبة نفدت منها" and out.get("reason_withheld_because") is None


# ── Who is asked, with what, in which order ──────────────────────────────────

def test_only_moving_running_out_products_with_stated_facts_are_asked():
    rows = (daily("a") + daily("b", days=DAYS[7:]) + daily("c") + daily("d"))    # b: not in the newest week
    prods = [product("a", department=DEPT), product("b", department=DEPT),
             product("c", department=DEPT), product("d", department=NO_FACTS)]
    got = mb.candidates(inputs(products=prods, rows=rows, running=signal("a", "b", "d")))
    # b is not moving, c is not running out, d's department has no schedule or shelf life.
    assert [f["barcode"] for f in got] == ["a"]


def test_the_request_holds_exactly_the_published_facts(tmp_path):
    """FR-164: nothing the model sees is absent from the artefact. No price, cost or stock."""
    fake = Fake()
    mb.live_step(inputs(), snapshots_root=tmp_path, key="k", transport=fake, now=RUN_AT)
    (call,) = fake.calls
    assert call["facts"] == {"barcode": "a", "product_name": "מים", "department": DEPT,
                             "weekly_units": [14.0, 14.0, 14.0, 14.0], "daily_mean": 2.0,
                             "stores_out": 1, "days_absent": [3], "shelf_life": {"days": 30}}
    request = call["request"]
    assert request["model"] == "claude-sonnet-5"
    assert not {"temperature", "top_p", "top_k"} & set(request)
    assert request["system"] == (Path(__file__).resolve().parents[2] / POLICY.boost_prompt).read_text(encoding="utf-8")
    assert call["headers"]["x-api-key"] == "k" and "anthropic-version" in call["headers"]
    assert call["url"] == "https://api.anthropic.com/v1/messages"


def test_requests_go_in_a_fixed_order_and_stop_at_the_ceiling(tmp_path):
    rows = daily("a", 1.0) + daily("b", 3.0) + daily("c", 3.0)
    prods = [product(b, department=DEPT) for b in "abc"]
    fake = Fake()
    out = mb.live_step(inputs(products=prods, rows=rows, running=signal("a", "b", "c"),
                              policy=replace(POLICY, boost_request_ceiling=2)),
                       snapshots_root=tmp_path, key="k", transport=fake, now=RUN_AT)
    assert [c["facts"]["barcode"] for c in fake.calls] == ["b", "c"]     # most units first, then barcode
    manifest = json.loads((tmp_path / LAST.isoformat() / "boost_picks" / "_manifest.json").read_text())
    assert manifest["runs"][-1]["ceiling_reached"] == ["a"]
    assert manifest["runs"][-1]["requests_made"] == 2 and out["requests_made"] == 2


# ── The snapshot (ADR-035) ───────────────────────────────────────────────────

def test_the_picks_are_sealed_and_the_day_manifest_is_untouched(tmp_path):
    day = tmp_path / LAST.isoformat()
    day.mkdir()
    (day / "_manifest.json").write_text('{"status": "ok", "sources": {}}', encoding="utf-8")
    before = (day / "_manifest.json").read_bytes()
    mb.live_step(inputs(), snapshots_root=tmp_path, key="k", transport=Fake(), now=RUN_AT)
    assert (day / "_manifest.json").read_bytes() == before
    picks = json.loads((day / "boost_picks" / "picks.json").read_text(encoding="utf-8"))
    pick = picks["a"]
    assert pick["accepted"] is True and pick["boost_pct"] == 10
    assert pick["model"] == "claude-sonnet-5" and pick["prompt"] == POLICY.boost_prompt
    assert pick["inputs_digest"] == mb.facts_digest(mb.candidates(inputs())[0])


def test_merge_never_replace(tmp_path):
    """A same-day re-run asks only for what has no pick yet, and replaces nothing sealed."""
    two = dict(products=[product("a", department=DEPT), product("b", department=DEPT)],
               rows=daily("a") + daily("b"), running=signal("a", "b"))
    mb.live_step(inputs(**{**two, "running": signal("a")}), snapshots_root=tmp_path, key="k",
                 transport=Fake(default='{"boost_pct": 7, "reason": "أول"}'), now=RUN_AT)
    second = Fake(default='{"boost_pct": 20, "reason": "ثان"}')
    mb.live_step(inputs(**two), snapshots_root=tmp_path, key="k", transport=second,
                 now=RUN_AT + timedelta(hours=1))
    assert [c["facts"]["barcode"] for c in second.calls] == ["b"]
    picks = json.loads((tmp_path / LAST.isoformat() / "boost_picks" / "picks.json").read_text())
    assert (picks["a"]["boost_pct"], picks["b"]["boost_pct"]) == (7, 20)
    manifest = json.loads((tmp_path / LAST.isoformat() / "boost_picks" / "_manifest.json").read_text())
    assert len(manifest["runs"]) == 2


def test_no_key_writes_nothing_and_asks_nothing(tmp_path):
    fake = Fake()
    out = mb.live_step(inputs(), snapshots_root=tmp_path, key=None, transport=fake, now=RUN_AT)
    assert fake.calls == [] and out["skipped"] == "no_boost_key"
    assert not (tmp_path / LAST.isoformat()).exists()


def test_a_failure_keeps_the_picks_already_paid_for(tmp_path):
    prods = [product("a", department=DEPT), product("b", department=DEPT)]
    fake = Fake(answers={"a": OSError("connection reset")})
    mb.live_step(inputs(products=prods, rows=daily("a", 1.0) + daily("b", 3.0), running=signal("a", "b")),
                 snapshots_root=tmp_path, key="k", transport=fake, now=RUN_AT)
    folder = tmp_path / LAST.isoformat() / "boost_picks"
    assert set(json.loads((folder / "picks.json").read_text())) == {"b"}
    run = json.loads((folder / "_manifest.json").read_text())["runs"][-1]
    assert run["completed"] is False and "connection reset" in run["error"]
    # One retry, then it stops rather than burning the ceiling on a dead API.
    assert [c["facts"]["barcode"] for c in fake.calls] == ["b", "a", "a"]


def test_a_client_error_is_not_retried():
    fake = Fake(default=(400, b'{"error": "bad"}'))
    with pytest.raises(mb.BoostUnavailable):
        mb.ask({"system": "s", "user": '{"barcode": "a"}'}, model="m", key="k", transport=fake)
    assert len(fake.calls) == 1


# ── Replay: what the capability applies (ADR-035 Decisions 3 and 4) ─────────

def _sealed(tmp_path, answer='{"boost_pct": 10, "reason": "نفدت"}'):
    mb.live_step(inputs(), snapshots_root=tmp_path, key="k", transport=Fake(default=answer), now=RUN_AT)
    return mb.read_picks(tmp_path, LAST.isoformat())


def test_a_recorded_pick_is_applied_when_its_facts_still_match(tmp_path):
    out = mb.run(inputs(picks=_sealed(tmp_path))).to_dict()
    assert out["status"] == "available"
    pick = out["picks"]["a"]
    assert pick["applied"] is True and pick["boost_pct"] == 10 and pick["model"] == "claude-sonnet-5"
    assert pick["facts"]["daily_mean"] == 2.0          # what it was asked with is published (FR-164)


def test_a_recorded_pick_is_not_applied_to_different_facts(tmp_path):
    out = mb.run(inputs(picks=_sealed(tmp_path), rows=daily("a", 3.0))).to_dict()
    assert out["picks"]["a"]["applied"] is False
    assert out["picks"]["a"]["not_applied_because"] == "facts_changed"


def test_a_rejected_pick_is_published_as_rejected_and_not_applied(tmp_path):
    out = mb.run(inputs(picks=_sealed(tmp_path, '{"boost_pct": 40, "reason": "كثير"}'))).to_dict()
    pick = out["picks"]["a"]
    assert pick["applied"] is False and pick["not_applied_because"] == "above_limit"
    assert pick["model_pick_pct"] == 40 and pick["boost_pct"] is None


def test_a_candidate_with_no_pick_says_so(tmp_path):
    two = inputs(products=[product("a", department=DEPT), product("b", department=DEPT)],
                 rows=daily("a") + daily("b"), running=signal("a", "b"), picks=_sealed(tmp_path))
    assert mb.run(two).to_dict()["picks"]["b"]["not_applied_because"] == "no_pick"


# ── The capability's own availability ───────────────────────────────────────

def test_it_is_registered_as_an_input_the_quantity_reads():
    spec = CAPABILITIES["market_boost"]
    assert spec.requires == ("running_out", "boost_picks")
    assert spec.value_policy == "none" and spec.admitted is False and spec.published_from
    assert INPUT_REASONS["boost_picks"] == "no_boost_key"


def test_no_snapshot_is_unavailable_with_no_boost_key():
    out = mb.run(inputs(picks=None)).to_dict()
    assert (out["status"], out["unavailable_reason"]) == ("unavailable", "no_boost_key")


def test_a_night_whose_step_failed_is_unavailable(tmp_path):
    mb.live_step(inputs(), snapshots_root=tmp_path, key="k", transport=Fake(default=OSError("down")), now=RUN_AT)
    out = mb.run(inputs(picks=mb.read_picks(tmp_path, LAST.isoformat()))).to_dict()
    assert (out["status"], out["unavailable_reason"]) == ("unavailable", "boost_unavailable")


def test_a_stale_market_signal_is_stale_here_too():
    old = signal("a", on_day=(LAST - timedelta(days=3)).isoformat())
    out = mb.run(inputs(running=old, picks={"on_day": old["on_day"], "picks": {}, "manifest": {"runs": []}})).to_dict()
    assert out["unavailable_reason"] == "market_signal_stale"


# ── Across the boundary: files on disk → the live run → the artefact → print mode ─

WOLT = "65daeb8779ca7f0a9bf964f3"


def _world(tmp_path):
    """Silver, 28 daily reports, stated facts and 30 days of market snapshots, on disk."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    import polars as pl
    from src.internal_pos.sales_daily_importer import import_sales_daily

    silver = tmp_path / "silver"; silver.mkdir()
    prod = [{"barcode": "7290999", "product_name": "מים", "category": DEPT, "selling_price": 4.0,
             "wolt_price": 0.0, "cost_price": 1.0, "_source_file": "inv.csv", "_as_of": "2026-10-01"}]
    inv = [{"barcode": "7290999", "product_name": "מים", "current_stock": 5.0,
            "_source_file": "inv.csv", "_as_of": "2026-10-01"}]
    pq.write_table(pa.Table.from_pylist(prod), silver / "products.parquet")
    pq.write_table(pa.Table.from_pylist(inv), silver / "inventory.parquet")
    reports = tmp_path / "daily"; reports.mkdir()
    header = "תאור פריט,ברקוד/קוד,מכר,מחיר קניה,מחיר מכירה,עלות המכר (חנות),כניסות מלאי,מחיר קניה נטו,הנחה,קוד מחלקה,\n"
    for d in DAYS:
        (reports / f"דוח מכירות יום {d}.csv").write_text("﻿" + header + "מים,7290999,2,1,4,2,0,1,0,1,\n",
                                                        encoding="utf-8")
    import_sales_daily(reports, silver_dir=silver)
    facts = tmp_path / "store_facts.yaml"
    facts.write_text(f"departments:\n  {DEPT}:\n    order_schedule: {{weekdays: [sun]}}\n    shelf_life_days: 30\n"
                     "    stated_by: owner\n    stated_on: 2026-10-01\n    recorded_by: team\n", encoding="utf-8")
    snaps = tmp_path / "snapshots"
    first = LAST - timedelta(days=29)
    for i in range(30):
        day = first + timedelta(days=i)
        rows = [{"barcode": f"72900{j:03d}", "store_id": WOLT, "is_online_available": True} for j in range(20)]
        if i < 27:
            rows.append({"barcode": "7290999", "store_id": WOLT, "is_online_available": True})
        folder = snaps / day.isoformat() / "delivery_catalog" / "01"
        folder.mkdir(parents=True)
        pl.DataFrame(rows).write_parquet(folder / "products_silver.parquet")
        (snaps / day.isoformat() / "_manifest.json").write_text(json.dumps(
            {"date": day.isoformat(), "status": "ok", "sources": {"delivery_catalog": {"status": "ok"}}}))
    return dict(silver_dir=silver, daily_sales_dir=reports, store_facts_path=facts, snapshots_root=snaps,
                sales_dir=tmp_path / "nomonthly", signals_dir=tmp_path / "nosig",
                matches_path=tmp_path / "nomatch.parquet")


def test_the_live_run_asks_seals_and_publishes_and_print_mode_replays_it(tmp_path, monkeypatch):
    import src.engine.run as run_mod
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setenv(mb.KEY_ENV, "test-key")
    world = _world(tmp_path)
    fake = Fake()
    live = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "out" / "dashboard.json",
                              now=RUN_AT, boost_transport=fake, **world)
    assert [c["facts"]["barcode"] for c in fake.calls] == ["7290999"]
    assert (world["snapshots_root"] / LAST.isoformat() / "boost_picks" / "picks.json").exists()
    live_cap = live["artefact"]["capabilities"]["market_boost"]
    assert live_cap["status"] == "available" and live_cap["picks"]["7290999"]["applied"] is True
    assert live["status"] != "partial"

    replay_fake = Fake()
    replay = run_mod.run_engine(mode="print", now=RUN_AT, boost_transport=replay_fake, **world)
    assert replay_fake.calls == []                                    # print mode never calls the model
    assert replay["artefact"]["capabilities"]["market_boost"] == live_cap
    assert replay["artefact"]["inputs_digest"] == live["artefact"]["inputs_digest"]


def test_with_no_key_the_boost_is_unavailable_and_the_run_is_not_degraded_by_it(tmp_path, monkeypatch):
    import src.engine.run as run_mod
    from src.owner_state.model import OwnerState
    monkeypatch.setattr(run_mod, "_market_chain", lambda skip: [])
    monkeypatch.setattr(run_mod, "_pull_owner_state",
                        lambda: OwnerState.from_dict({"status": "available", "pulled_at": "t"}))
    monkeypatch.setattr(run_mod, "_sales_import", lambda *a, **k: {"window": None, "monthly_rows": 42})
    monkeypatch.delenv(mb.KEY_ENV, raising=False)
    world = _world(tmp_path)
    fake = Fake()
    result = run_mod.run_engine(mode="publish", artefact_path=tmp_path / "out" / "dashboard.json", now=RUN_AT,
                                boost_transport=fake, **world,
                                # With the market signal beside it: the publisher refuses an
                                # artefact in which every capability is unavailable.
                                capability_runners={"market_boost": mb.run, "market_running_out": mro.run})
    cap = result["artefact"]["capabilities"]["market_boost"]
    assert (cap["status"], cap["unavailable_reason"]) == ("unavailable", "no_boost_key")
    assert fake.calls == [] and result["status"] == "ok"
    assert not (world["snapshots_root"] / LAST.isoformat() / "boost_picks").exists()
