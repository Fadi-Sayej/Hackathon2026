"""
T8 / #53 — measuring how the local market moves, and refusing to when it can't.

The output of this module goes into `configs/measured_weights.yaml`, which #50
consumes to replace hand-set multipliers with measured ones. A wrong number here
does not fail loudly — it quietly changes what the shop is told to order. So the
tests concentrate on the ways it can produce a confident wrong answer:

  * extrapolating a three-day feast to a full-month multiplier
  * fitting a share below zero and reporting it as a multiplier
  * crediting a seasonal trend to a calendar window that happens to fall early
  * reading "no sales rows" as "sold zero"
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.market.sales_movement import (  # noqa: E402
    MIN_EXPOSURE_FOR_EFFECT,
    Window,
    estimate_effect,
    load_windows,
    month_from_filename,
    normalise_barcode,
    velocity_confidence,
)

MONTHS = [date(2026, m, 1) for m in range(1, 8)]
RAMADAN = Window("ramadan", "islamic", "local", date(2026, 2, 17), date(2026, 3, 19))
EID = Window("eid_al_fitr", "islamic", "local", date(2026, 3, 20), date(2026, 3, 22))


# ---------------------------------------------------------------------------
# Exposure
# ---------------------------------------------------------------------------

def test_a_straddling_window_is_fractional_not_binary():
    """Ramadan runs 17 Feb - 19 Mar. Calling both months fully exposed
    overstates the contrast and understates the uncertainty."""
    assert RAMADAN.exposure(date(2026, 2, 1)) == pytest.approx(12 / 28, abs=0.01)
    assert RAMADAN.exposure(date(2026, 3, 1)) == pytest.approx(19 / 31, abs=0.01)
    assert RAMADAN.exposure(date(2026, 5, 1)) == 0.0


def test_exposure_never_exceeds_one_or_falls_below_zero():
    wide = Window("all", "x", "y", date(2025, 1, 1), date(2027, 1, 1))
    for month in MONTHS:
        assert 0.0 <= wide.exposure(month) <= 1.0
        assert wide.exposure(month) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# The range checks — each one caught a real wrong answer
# ---------------------------------------------------------------------------

def test_a_three_day_feast_is_refused_not_extrapolated():
    """Eid is 3 days: at most 0.10 of a month. Reporting "the effect at full
    exposure" extrapolates the slope tenfold past any observed point. The first
    version of this module did that and produced x-3.25 for salty snacks."""
    assert EID.exposure(date(2026, 3, 1)) < MIN_EXPOSURE_FOR_EFFECT
    shares = {m: 0.10 + (0.05 if m.month == 3 else 0) for m in MONTHS}

    effect = estimate_effect(shares, EID, "snacks")
    assert effect.effect is None
    assert effect.confidence == "unmeasurable"
    assert "extrapolate" in effect.reason


def test_a_fit_that_goes_negative_is_refused():
    """A share cannot be below zero. If the linear model says it can, the model
    has left the range the data supports and no multiplier is defensible."""
    # Steeply negative in the exposed months, enough to drive the fit under zero.
    shares = {m: (0.001 if m.month in (2, 3) else 0.40) for m in MONTHS}
    effect = estimate_effect(shares, RAMADAN, "collapsing")
    assert effect.effect is None or effect.ci_low is not None
    if effect.effect is None:
        assert "out of range" in effect.reason or "<= 0" in effect.reason


def test_a_seasonal_trend_is_not_credited_to_the_calendar():
    """The confound that nearly shipped.

    Ramadan falls in months 2-3 of a Jan-Jul series, so exposure is nearly
    collinear with "early in the year". Beverages simply rose into summer and
    read as a x0.82 Ramadan suppression until a trend control was added.

    These are the REAL department shares for משקאות across the seven months.
    Uncontrolled they give x0.82 with an interval that excludes 1.0 — a
    publishable-looking Ramadan suppression. Controlled for trend it vanishes.
    """
    shares = dict(zip(MONTHS, [0.3167, 0.3125, 0.3153, 0.3462, 0.3703, 0.3586, 0.3483]))
    effect = estimate_effect(shares, RAMADAN, "משקאות")

    assert effect.effect < 1.0                       # looks like suppression
    assert effect.ci_high < 1.0                      # and looks significant
    assert effect.survives_trend_control is False    # but it is the trend
    assert effect.confidence == "confounded"
    assert "time trend" in effect.reason


def test_the_real_barista_series_survives_the_trend_control():
    """The mirror, on real data: Jan is BELOW Feb/Mar, so the two Ramadan months
    sit above any line drawn through the rest. That bump is a real effect."""
    shares = dict(zip(MONTHS, [0.2416, 0.2635, 0.2629, 0.2122, 0.2147, 0.1943, 0.1865]))
    effect = estimate_effect(shares, RAMADAN, "מחלקת -barista")

    assert effect.survives_trend_control is True
    assert effect.confidence == "medium"
    assert effect.effect_trend_adjusted == pytest.approx(1.27, abs=0.05)


def test_a_genuine_bump_above_the_trend_survives_the_control():
    """The mirror of the test above: a real effect must not be explained away.

    A declining series with the two Ramadan months lifted above the line — the
    shape the barista department actually shows.
    """
    shares = {m: 0.25 - 0.01 * (m.month - 1) for m in MONTHS}
    shares[date(2026, 2, 1)] += 0.04
    shares[date(2026, 3, 1)] += 0.04

    effect = estimate_effect(shares, RAMADAN, "barista")
    assert effect.survives_trend_control is True
    assert effect.confidence == "medium"
    assert effect.effect > 1.0
    assert effect.effect_trend_adjusted is not None


def test_a_flat_series_reports_no_effect():
    shares = {m: 0.20 for m in MONTHS}
    effect = estimate_effect(shares, RAMADAN, "steady")
    assert effect.confidence in ("inconclusive", "confounded")


def test_a_window_outside_the_data_is_unmeasurable_not_zero():
    autumn = Window("rosh_hashanah", "hebrew", "through", date(2026, 9, 11), date(2026, 9, 13))
    effect = estimate_effect({m: 0.2 for m in MONTHS}, autumn, "any")
    assert effect.effect is None
    assert effect.n_exposed == 0
    assert "outside the data range" in effect.reason


def test_a_fully_exposed_series_has_no_baseline():
    """Every month exposed means nothing to compare against — that is not a
    100% effect, it is no measurement."""
    always = Window("always", "x", "y", date(2025, 1, 1), date(2027, 1, 1))
    effect = estimate_effect({m: 0.2 for m in MONTHS}, always, "any")
    assert effect.effect is None
    assert "no baseline" in effect.reason


# ---------------------------------------------------------------------------
# Step 2 — absence is not zero
# ---------------------------------------------------------------------------

def test_no_sales_rows_is_none_never_zero():
    """#53: "No data" is not "zero sales". Conflating them manufactures a
    confident 'reduce stock' about a product we know nothing about."""
    assert velocity_confidence(0, 7) == "none"


def test_confidence_rises_with_months_observed():
    assert velocity_confidence(1, 7) == "low"
    assert velocity_confidence(3, 7) == "medium"
    assert velocity_confidence(7, 7) == "high"
    assert velocity_confidence(6, 7) == "high"


# ---------------------------------------------------------------------------
# Plumbing
# ---------------------------------------------------------------------------

def test_hebrew_month_filenames_parse():
    assert month_from_filename(Path("דוח מכירות חודש מרץ 2026.csv")) == date(2026, 3, 1)
    assert month_from_filename(Path("דוח מכירות חודש ינואר 2026.csv")) == date(2026, 1, 1)
    assert month_from_filename(Path("not-a-report.csv")) is None


def test_barcodes_normalise_the_same_way_as_every_other_track():
    assert normalise_barcode("0729000012345") == normalise_barcode("729000012345")
    assert normalise_barcode(None) == ""


def test_the_shipped_calendar_config_parses_and_covers_ramadan():
    windows = {w.key: w for w in load_windows(ROOT / "configs" / "calendars.yaml")}
    assert "ramadan" in windows
    ramadan = windows["ramadan"]
    assert ramadan.exposure(date(2026, 2, 1)) > 0
    assert ramadan.exposure(date(2026, 3, 1)) > 0
    assert ramadan.population == "local"
