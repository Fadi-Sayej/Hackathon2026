"""shelf_measurement — what his recorded arrangements changed, in units, in his own store
(F12-S1 FR-202 … FR-209).

It requires the catalogue, the layout file and the daily reports. Its own reasons are
`layout_all_rejected`, `owner_state_unavailable` (his arrangements are never treated as absent
because they could not be read, CLAUDE.md rule 10) and `no_arrangement_recorded`. It runs before
`shelf_plan`, which reads the elasticity from it (FR-206).

Per arrangement, the `acted` outcome on a `shelf.plan` entry (ADR-038), which carries everything
needed, so no past artefact is read:
- **Windows** (FR-202), held to F8's rules by `order_evidence.window_between`: the before window
  ends the day before the plan's window begins, and the after window starts the day after
  `arranged_on`. It is not measurable with no full before window ("history_too_short") or
  another arrangement of its fixture inside its span ("rearranged_again"). It is waiting until
  its after window is over.
- **Who is measured** (FR-204): a product that sold in the plan's window, arranged or comparison
  alike. That window shares no day with either measured window.
- **Comparison products** (FR-203): the products of fixtures with no arrangement anywhere in the
  span.
- **The fit** (FR-205): `shelf_stats`. The before facings and shelf are the later-dated of the
  team's count (ADR-037) and his previous arrangement of the fixture, provided it is no later
  than this one. A product whose before facings are unknown or zero stays in its net change but
  is left out of the estimate.
- **The placebo** (FR-209): the same regression on two earlier windows, the same distance apart,
  testing the "arranged at all" term and the facing term.

Everything is in units, never in ₪ (FR-207, INV-087), and no figure adds a fixture's products
together.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Optional

from src.engine.model import CapabilityOutput
from src.engine.order_evidence import product_evidence, window_between
from src.engine.registry import derive_status
from src.engine.shelf_population import population
from src.engine.shelf_stats import Unit, bootstrap, fit, terms_with_variation, usable

CAP, SPEC = "shelf_measurement", "F12-S1"
FAMILY = "shelf.plan"


def _d(text) -> date:
    return date.fromisoformat(str(text))


def arrangements(owner) -> tuple:
    """(readable arrangements, unreadable ones), from the owner's acted shelf.plan outcomes."""
    out, unreadable = [], []
    for entry_id, record in sorted((owner.outcomes or {}).items()):
        record = record or {}            # an undo reaches the engine as a null tombstone (clearOutcome)
        snap = record.get("snapshot") or {}
        if record.get("status") != "acted" or snap.get("signal_family") != FAMILY:
            continue
        try:
            placements = {}
            for b, p in (snap.get("placements") or {}).items():
                facings = p.get("facings")
                if not isinstance(facings, int) or isinstance(facings, bool) or facings < 1:
                    raise ValueError(f"product {b} has facings {facings!r}")
                placements[str(b)] = {"shelf": p.get("shelf"), "facings": facings, "eye_level": bool(p.get("eye_level"))}
            if not placements:
                raise ValueError("it places no product")
            window = snap["plan_window"]
            out.append({"entry_id": entry_id, "fixture": str(snap["fixture"]),
                        "plan_date": _d(snap["plan_date"]).isoformat(),
                        "plan_window": {"first_day": _d(window["first_day"]).isoformat(),
                                        "last_day": _d(window["last_day"]).isoformat()},
                        "arranged_on": _d(snap["arranged_on"]).isoformat(), "placements": placements})
        except (KeyError, TypeError, ValueError, AttributeError) as err:
            # Named, never guessed at: an arrangement the measurement cannot read is not one it measures.
            unreadable.append({"entry_id": entry_id, "reason": f"unreadable arrangement: {err}"})
    return sorted(out, key=lambda a: (a["arranged_on"], a["fixture"], a["entry_id"])), unreadable


def _members(layout: dict, products: list) -> dict:
    """{fixture: [barcodes]} as the layout holds them today: the one definition, statuses aside."""
    pop = population(layout, products, None, None, set())
    return {name: sorted(b for b, m in members.items() if m["status"] not in ("kept_off", "rejected"))
            for name, members in pop.items()}


def _sold_in(rows: list, first: str, last: str) -> bool:
    return any(first <= r["day"] <= last and (r.get("units") or 0) > 0 for r in rows)


def _before_record(arr: dict, barcode: str, layout: dict, earlier: list) -> Optional[dict]:
    """What stood on the shelf before: the later-dated of the team's count and his previous
    arrangement of the fixture, dated no later than this one (FR-205).

    The latest record is chosen first and the product read from it. A previous arrangement that did
    not place the product does not say what stood there: kept off and unstocked mean none, but no
    width or too wide mean a facing of unknown size (FR-186). So it is unknown, never 0 and never an
    older count (rule 8: no number rather than a wrong one)."""
    current = (layout.get("current") or {}).get(barcode)
    fixture = (layout.get("fixtures") or {}).get(arr["fixture"])
    count = None
    if current and fixture and current["fixture"] == arr["fixture"] and current["measured_on"] <= arr["arranged_on"]:
        count = (current["measured_on"], {"facings": current["facings"],
                                          "eye_level": current["shelf"] == fixture.get("eye_level_shelf"),
                                          "from": "count"})
    previous = max((p for p in earlier if p["fixture"] == arr["fixture"] and p["arranged_on"] < arr["arranged_on"]),
                   key=lambda p: (p["arranged_on"], p["entry_id"]), default=None)
    if previous is not None and (count is None or previous["arranged_on"] >= count[0]):
        placed = previous["placements"].get(barcode)
        if placed is None:
            return None
        return {"facings": placed["facings"], "eye_level": bool(placed["eye_level"]), "from": "previous_arrangement"}
    return count[1] if count else None


def _evidence(rows: list, window) -> tuple:
    ev = product_evidence(rows, window)
    return ev["units_in_window"], ev["report_days"], ev["daily_mean"]


def _units_for(arr: dict, first_window, second_window, *, arranged: list, comparison: dict, rows: dict,
               layout: dict, earlier: list) -> tuple:
    """Units for one pair of windows, and the published per-product records."""
    units, records = [], []
    for barcode in arranged:
        b, eb, mb = _evidence(rows.get(barcode, []), first_window)
        a, ea, ma = _evidence(rows.get(barcode, []), second_window)
        after = arr["placements"][barcode]
        before = _before_record(arr, barcode, layout, earlier)
        if before is None:
            lf, why = None, "before_facings_unknown"
        elif not before["facings"]:
            lf, why = None, "not_on_the_shelf_before"
        else:
            lf, why = math.log(after["facings"] / before["facings"]), None
        eye = (int(bool(after.get("eye_level"))) - int(before["eye_level"])) if before else 0
        units.append(Unit(arr["entry_id"], arr["fixture"], b, a, eb, ea, 1.0, lf, float(eye)))
        records.append({"barcode": barcode, "before_daily_mean": mb, "after_daily_mean": ma,
                        "before_units": b, "after_units": a,
                        "before_facings": before["facings"] if before else None,
                        "before_from": before["from"] if before else None,
                        "after_facings": after["facings"], "eye_level_change": eye,
                        "in_estimate": lf is not None, "why_not_in_estimate": why})
    for fixture, barcodes in comparison.items():
        for barcode in barcodes:
            b, eb, _ = _evidence(rows.get(barcode, []), first_window)
            a, ea, _ = _evidence(rows.get(barcode, []), second_window)
            units.append(Unit(arr["entry_id"], fixture, b, a, eb, ea, 0.0, 0.0, 0.0))
    return units, records


def _verdict(units: list, policy, watch: tuple) -> dict:
    """Fit, bootstrap and the counts the minimums apply to. `watch` names the terms to interval."""
    rows = usable(units)
    arranged = [u for u in rows if u.arranged]
    fixtures = sorted({u.cluster for u in arranged})
    out = {"arrangements": len({u.arrangement for u in arranged}), "fixtures": len(fixtures),
           "products": len(arranged), "terms": None, "estimate": None, "intervals": None, "draws": None,
           "redrawn": None, "why_not": None}
    if not arranged:
        return {**out, "why_not": "no_arranged_product"}
    if not any(not u.arranged for u in rows):
        return {**out, "why_not": "no_comparison"}
    if len(fixtures) < policy.shelf_min_arrangements or len(arranged) < policy.shelf_min_products:
        return {**out, "why_not": "too_few_arrangements_or_products"}
    terms = terms_with_variation(rows)
    if "log_facings" not in terms:
        return {**out, "terms": list(terms), "why_not": "no_variation_in_facings"}
    full = fit(rows, terms)
    if full is None:
        return {**out, "terms": list(terms), "why_not": "could_not_be_fitted"}
    watched = tuple(t for t in watch if t in terms)
    boot = bootstrap(rows, terms, draws=policy.shelf_bootstrap_draws, seed=policy.shelf_bootstrap_seed,
                     level=policy.shelf_interval_level, watch=watched)
    if boot is None:
        return {**out, "terms": list(terms), "estimate": full.terms, "why_not": "too_few_fixtures_to_resample"}
    return {**out, "terms": list(terms), "estimate": full.terms, "intervals": boot["intervals"],
            "draws": boot["draws"], "redrawn": boot["redrawn"]}


def measure(inputs) -> dict:
    """The whole measurement, computed once per run and read by both capabilities (FR-206)."""
    cached = getattr(inputs, "_shelf_measurement", None)
    if cached is not None:
        return cached
    result = _measure(inputs)
    inputs._shelf_measurement = result
    return result


def _measure(inputs) -> dict:
    status, reason = derive_status(CAP, inputs)
    if status == "unavailable":
        return {"status": "unavailable", "reason": reason}
    layout, policy = inputs.store_layout, inputs.policy
    if not layout.get("fixtures"):
        return {"status": "unavailable", "reason": "layout_all_rejected"}
    if inputs.owner.status != "available":
        return {"status": "unavailable", "reason": "owner_state_unavailable"}
    arranged_all, unreadable = arrangements(inputs.owner)
    if not arranged_all:
        return {"status": "unavailable", "reason": "no_arrangement_recorded", "unreadable": unreadable}

    run_day = inputs.run_at.date()
    span = timedelta(days=policy.order_window_days)
    report_days = sorted({r["day"] for r in inputs.sales_daily})
    rows = defaultdict(list)
    for r in inputs.sales_daily:
        rows[r["barcode"]].append(r)
    members = _members(layout, inputs.products)
    names = {p["barcode"]: p.get("product_name") for p in inputs.products if p.get("barcode")}

    def arranged_between(fixture: Optional[str], first: date, last: date, skip: str) -> bool:
        return any(a["entry_id"] != skip and (fixture is None or a["fixture"] == fixture)
                   and first <= _d(a["arranged_on"]) <= last for a in arranged_all)

    published, main_units, placebo_units = [], [], []
    for arr in arranged_all:
        p0 = _d(arr["plan_window"]["first_day"])
        before_first, before_last = p0 - span, p0 - timedelta(days=1)
        after_first = _d(arr["arranged_on"]) + timedelta(days=1)
        after_last = after_first + span - timedelta(days=1)
        record = {"entry_id": arr["entry_id"], "fixture": arr["fixture"], "arranged_on": arr["arranged_on"],
                  "plan_date": arr["plan_date"], "plan_window": arr["plan_window"],
                  "before_window": {"first_day": before_first.isoformat(), "last_day": before_last.isoformat()},
                  "after_window": {"first_day": after_first.isoformat(), "last_day": after_last.isoformat()},
                  "status": None, "reason": None, "waiting": None, "comparison": None, "products": [], "left_out": []}
        published.append(record)
        if arranged_between(arr["fixture"], before_first, after_last, arr["entry_id"]):
            record.update(status="not_measurable", reason="rearranged_again")
            continue
        before = window_between(before_first, before_last, report_days, policy)
        if before is None:
            record.update(status="not_measurable", reason="history_too_short")
            continue
        if after_last >= run_day:
            so_far = sum(1 for d in report_days if after_first.isoformat() <= d <= after_last.isoformat())
            record.update(status="waiting", waiting={"report_days_so_far": so_far,
                                                     "report_days_needed": policy.order_min_report_days,
                                                     "days_left": (after_last - run_day).days + 1})
            continue
        after = window_between(after_first, after_last, report_days, policy)
        if after is None:
            record.update(status="not_measurable", reason="after_window_too_thin")
            continue
        comparison_fixtures = [f for f in members if f != arr["fixture"]
                               and not arranged_between(f, before_first, after_last, "")]
        if not comparison_fixtures:
            record.update(status="not_measurable", reason="no_unchanged_fixture")
            continue
        plan_first, plan_last = arr["plan_window"]["first_day"], arr["plan_window"]["last_day"]
        eligible = lambda b: _sold_in(rows.get(b, []), plan_first, plan_last)            # noqa: E731
        arranged = sorted(b for b in arr["placements"] if eligible(b))
        record["left_out"] = [{"barcode": b, "reason": "no_sale_in_plan_window"}
                              for b in sorted(arr["placements"]) if not eligible(b)]
        comparison = {f: [b for b in members[f] if eligible(b)] for f in comparison_fixtures}
        units, products = _units_for(arr, before, after, arranged=arranged, comparison=comparison, rows=rows,
                                     layout=layout, earlier=arranged_all)
        comp = [u for u in units if not u.arranged]
        if not comp or not sum(u.before for u in comp) or not sum(u.after for u in comp):
            record.update(status="not_measurable", reason="comparison_did_not_sell")
            continue
        # FR-204 for the yardstick too: a comparison product that did not sell in the plan's window
        # is named, as an arranged one is (AC-193).
        not_eligible = sorted(b for f in comparison_fixtures for b in members[f] if not eligible(b))
        record.update(status="measured",
                      comparison={"fixtures": comparison_fixtures, "products": len(comp),
                                  "left_out": [{"barcode": b, "reason": "no_sale_in_plan_window"} for b in not_eligible]},
                      products=[{**p, "product_name": names.get(p["barcode"])} for p in products])
        main_units += units

        # FR-209: the placebo, on two earlier windows as far apart as these, while nothing changed.
        distance = after_first - before_first
        early_first = before_first - distance
        early_last = early_first + span - timedelta(days=1)
        record["placebo_windows"] = {"earlier": {"first_day": early_first.isoformat(), "last_day": early_last.isoformat()},
                                     "later": record["before_window"], "used": False, "why_not": None}
        early = window_between(early_first, early_last, report_days, policy)
        if early is None:
            record["placebo_windows"]["why_not"] = "history_too_short"
        elif arranged_between(arr["fixture"], early_first, before_last, arr["entry_id"]):
            record["placebo_windows"]["why_not"] = "rearranged_inside"
        else:
            placebo_comparison = {f: [b for b in members[f] if eligible(b)] for f in members
                                  if f != arr["fixture"] and not arranged_between(f, early_first, before_last, "")}
            if not placebo_comparison:
                record["placebo_windows"]["why_not"] = "no_unchanged_fixture"
            else:
                p_units, _ = _units_for(arr, early, before, arranged=arranged, comparison=placebo_comparison,
                                        rows=rows, layout=layout, earlier=arranged_all)
                placebo_units += p_units
                record["placebo_windows"]["used"] = True

    main = _verdict(main_units, policy, ("log_facings",))
    full = fit(usable(main_units), tuple(main["terms"] or terms_with_variation(usable(main_units)))) if main_units else None
    for record in published:
        if record["status"] != "measured":
            continue
        delta = full.window.get(record["entry_id"]) if full else None
        record["comparison"]["change"] = math.exp(delta) if delta is not None else None
        for p in record["products"]:
            mb, ma = p["before_daily_mean"], p["after_daily_mean"]
            if delta is None:
                p["net_change"], p["why_no_net_change"] = None, "could_not_be_fitted"
            elif not mb:
                p["net_change"], p["why_no_net_change"] = None, "no_sale_in_before_window"
            else:
                p["net_change"], p["why_no_net_change"] = (ma or 0.0) / mb / math.exp(delta), None

    placebo = _placebo(placebo_units, policy, main)
    estimate = (main["estimate"] or {}).get("log_facings")
    interval = (main["intervals"] or {}).get("log_facings")
    if main["why_not"] is not None or interval is None:
        verdict, why = "not_measurable", main["why_not"]
    elif placebo["status"] == "failed":
        verdict, why = "not_measurable", "placebo_failed"
    elif interval[0] > 0 or interval[1] < 0:
        verdict, why = "measured", None
    else:
        verdict, why = "measured_and_not_significant", None
    elasticity = {"estimate": estimate, "interval": interval, "level": policy.shelf_interval_level,
                  "verdict": verdict, "why_not_measurable": why, "arrangements": main["arrangements"],
                  "fixtures": main["fixtures"], "products": main["products"], "terms": main["terms"],
                  "draws": main["draws"], "redrawn": main["redrawn"]}
    return {"status": "available", "arrangements": published, "unreadable": unreadable,
            "elasticity": elasticity, "placebo": placebo, "plan_uses": _plan_uses(elasticity, placebo, policy)}


def _placebo(units: list, policy, main: dict) -> dict:
    v = _verdict(units, policy, ("arranged", "log_facings"))
    base = {"arrangements": v["arrangements"], "fixtures": v["fixtures"], "products": v["products"],
            "intervals": v["intervals"]}
    if v["intervals"] is None:
        return {**base, "status": "not_run", "why_not_run": v["why_not"] or "too_few_fixtures_to_resample"}
    failed = [t for t, (lo, hi) in v["intervals"].items() if lo > 0 or hi < 0]
    return {**base, "status": "failed" if failed else "passed", "failed_on": failed}


def _plan_uses(elasticity: dict, placebo: dict, policy) -> dict:
    """FR-206: his own value only when measured, between 0 and 1, with a passed placebo."""
    research = {"value": policy.shelf_elasticity, "source": "research"}
    if elasticity["verdict"] == "measured_and_not_significant":
        return {**research, "why": "his_own_not_significant"}
    if elasticity["verdict"] != "measured":
        return {**research, "why": "placebo_failed" if elasticity["why_not_measurable"] == "placebo_failed"
                else "his_own_not_yet_measured"}
    if not 0 < elasticity["estimate"] < 1:
        return {**research, "why": "his_own_outside_range"}
    if placebo["status"] != "passed":
        return {**research, "why": "placebo_not_run"}
    return {"value": elasticity["estimate"], "source": "his_store", "why": "his_own_measured"}


def plan_elasticity(inputs) -> dict:
    """What shelf_plan uses, and why (FR-206). Never silent about an unavailable measurement.

    The plan never fails because the measurement did: they are two capabilities (ADR-014), and a
    defect in the measurement must leave the plan on the research value, saying so."""
    try:
        m = measure(inputs)
    except Exception:                       # noqa: BLE001 — isolation is the point
        return {"value": inputs.policy.shelf_elasticity, "source": "research", "why": "measurement_unavailable",
                "measurement_reason": "capability_error"}
    if m["status"] != "available":
        return {"value": inputs.policy.shelf_elasticity, "source": "research", "why": "measurement_unavailable",
                "measurement_reason": m["reason"]}
    return m["plan_uses"]


def run(inputs) -> CapabilityOutput:
    m = measure(inputs)
    if m["status"] != "available":
        out = CapabilityOutput.unavailable(CAP, SPEC, m["reason"])
        if m.get("unreadable"):
            out.extras = {"unreadable": m["unreadable"]}
        return out
    states = [a["status"] for a in m["arrangements"]]
    counts = {"arrangements": len(states), "measured": states.count("measured"),
              "waiting": states.count("waiting"), "not_measurable": states.count("not_measurable")}
    return CapabilityOutput(id=CAP, spec=SPEC, status="available", counts=counts,
                            thresholds=inputs.policy.as_dict()["shelf_measurement"],
                            extras={"arrangements": m["arrangements"], "elasticity": m["elasticity"],
                                    "placebo": m["placebo"], "plan_uses": m["plan_uses"],
                                    "unreadable": m["unreadable"]})
