"""
sales_movement.py — how the local market actually moves (T8 / #53).

Seven monthly sales reports from YomYom carry something no external source has:
the real behaviour of the Kafr Qasim customer. This module measures it, and is
equally explicit about what these seven files CANNOT answer.

THE GRAIN DECIDES THE TRACK. CHECK IT FIRST.
--------------------------------------------
#53 says: *"If the sales rows are daily or weekly, decompose at that resolution
instead — you likely have far more than seven observations. Check the raw grain
before aggregating it away."*

Checked. The reports are **one row per product per month**, with columns
`מכר` (units), `כניסות מלאי` (receipts), `עלות המכר` (cost) and a department
code. **There is no date column anywhere in any of the seven files.** 3,942
product-months, 410,720 units, and 7 observations per product.

That is decisive, and it is not a defect in this module:

    Step 3  STL decomposition   NOT POSSIBLE. STL needs at least two full
                                seasonal cycles. Seven monthly points cannot
                                separate an annual cycle from a trend, and
                                fitting one anyway produces a decomposition that
                                looks authoritative and means nothing.

    Step 4  Calendar effects    POSSIBLE, WEAKLY. Ramadan straddles February and
                                March, so exposure is fractional, not binary.
                                Measured with a confidence interval, on 7 points.

    Step 5  Weekday / payday    NOT MEASURABLE AT ALL. There is no day-of-week
                                information in the data. This is different from
                                "measured and not significant", and the report
                                must say which of the two it is.

WHY SHARES, NOT UNITS
---------------------
Store-wide volume swings between 50,501 and 70,339 units a month. Comparing a
department's raw units across months therefore measures how busy the shop was,
not what the customer chose. Every effect below is computed on the department's
SHARE of that month's total, so store-wide variation cancels.

"NO DATA" IS NOT "ZERO SALES"
-----------------------------
A product with no rows might be dead, or never stocked, or missed by the export.
Treating it as having sold zero makes it look like a slow mover and produces a
confident "reduce stock" recommendation about a product we know nothing about.
`velocity_confidence` below reports absence as `none`, never as zero.
"""

from __future__ import annotations

import calendar as _calendar
import math
import re
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

HEBREW_MONTHS = {
    "ינואר": 1, "פברואר": 2, "מרץ": 3, "אפריל": 4,
    "מאי": 5, "יוני": 6, "יולי": 7, "אוגוסט": 8,
    "ספטמבר": 9, "אוקטובר": 10, "נובמבר": 11, "דצמבר": 12,
}

COL_NAME = "תאור פריט"
COL_BARCODE = "ברקוד/קוד"
COL_UNITS = "מכר"
COL_RECEIPTS = "כניסות מלאי"
COL_COST = "עלות המכר (חנות)"
COL_PRICE = "מחיר מכירה"
COL_DEPT_CODE = "קוד מחלקה"

# Below this many months of observation a per-product velocity claim is not
# supportable. Seven monthly points is the whole history, so the bands are in
# months rather than the weeks #53 writes — the data cannot resolve weeks.
CONFIDENCE_BANDS = (
    ("high", 6),      # 6-7 months
    ("medium", 3),    # 3-5 months
    ("low", 1),       # 1-2 months
)

# A window must cover at least this much of some month before a full-month
# multiplier means anything at monthly grain.
#
# This is not a tuning knob, it is a range check. Eid al-Fitr is three days: in a
# 31-day month its exposure maxes out at 0.10, so reporting "the effect at full
# exposure" extrapolates the fitted slope tenfold beyond any observed point. The
# first version of this module did exactly that and produced x-3.25 for salty
# snacks — a NEGATIVE multiplier on a quantity that is a share and cannot go
# below zero. The arithmetic was right; the question was unanswerable.
#
# Ramadan (0.43 and 0.61 exposure) clears this. Every three-day feast does not,
# and at monthly grain it never will.
MIN_EXPOSURE_FOR_EFFECT = 0.25


def normalise_barcode(value) -> str:
    """Same form as src/market/labelled_store.py, so joins agree across tracks."""
    return str(value or "").strip().lstrip("0")


def month_from_filename(path: Path) -> Optional[date]:
    """First day of the month named in a Hebrew report filename, or None."""
    name = path.stem
    year_match = re.search(r"(20\d{2})", name)
    year = int(year_match.group(1)) if year_match else None
    for hebrew, number in HEBREW_MONTHS.items():
        if hebrew in name:
            return date(year or 2026, number, 1)
    return None


def load_panel(sales_dir: Path, departments: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """One row per (month, barcode): units, receipts, revenue, department.

    `departments` maps normalised barcode -> department name. The sales reports
    carry only a numeric department code with no lookup table shipped alongside
    it, so the readable name is joined from the product catalogue and the
    unmatched share is reported rather than silently dropped.
    """
    frames = []
    for path in sorted(sales_dir.glob("*.csv")):
        month = month_from_filename(path)
        if month is None:
            continue
        raw = pd.read_csv(path)
        if COL_UNITS not in raw.columns:
            continue
        frame = pd.DataFrame({
            "month": month,
            "barcode": raw[COL_BARCODE].map(normalise_barcode),
            "product_name": raw.get(COL_NAME),
            "dept_code": pd.to_numeric(raw.get(COL_DEPT_CODE), errors="coerce"),
            "units": pd.to_numeric(raw[COL_UNITS], errors="coerce").fillna(0.0),
            "receipts": pd.to_numeric(raw.get(COL_RECEIPTS), errors="coerce").fillna(0.0),
            "cost": pd.to_numeric(raw.get(COL_COST), errors="coerce"),
            "price": pd.to_numeric(raw.get(COL_PRICE), errors="coerce"),
        })
        frames.append(frame[frame["barcode"] != ""])

    if not frames:
        return pd.DataFrame(columns=["month", "barcode", "units", "department"])

    panel = pd.concat(frames, ignore_index=True)
    panel["department"] = panel["barcode"].map(departments or {})
    return panel


def load_departments(products_parquet: Path) -> Dict[str, str]:
    frame = pd.read_parquet(products_parquet, columns=["barcode", "category"])
    frame = frame.assign(bc=frame["barcode"].map(normalise_barcode))
    frame = frame[(frame["bc"] != "") & frame["category"].notna()].drop_duplicates("bc")
    return dict(zip(frame["bc"], frame["category"]))


# ---------------------------------------------------------------------------
# Calendar exposure
# ---------------------------------------------------------------------------

@dataclass
class Window:
    key: str
    calendar: str
    population: str
    start: date
    end: date

    def days_in_month(self, month: date) -> int:
        """Days of this window falling inside the given calendar month."""
        last = _calendar.monthrange(month.year, month.month)[1]
        month_start, month_end = month.replace(day=1), month.replace(day=last)
        first = max(self.start, month_start)
        final = min(self.end, month_end)
        return max(0, (final - first).days + 1)

    def exposure(self, month: date) -> float:
        """Fraction of the month covered by the window, in [0, 1].

        Ramadan runs 17 Feb - 19 Mar, so February is ~0.43 exposed and March
        ~0.61. A binary "is this a Ramadan month" flag would call both months
        fully Ramadan and both of the other five fully normal, which overstates
        the contrast and understates the uncertainty.
        """
        last = _calendar.monthrange(month.year, month.month)[1]
        return self.days_in_month(month) / last


def load_windows(config_path: Path) -> List[Window]:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    out = []
    for entry in config.get("windows") or []:
        start, end = entry.get("start"), entry.get("end")
        if not start or not end:
            continue
        out.append(Window(
            key=entry["key"],
            calendar=entry.get("calendar", "unknown"),
            population=entry.get("population", "unknown"),
            start=start if isinstance(start, date) else date.fromisoformat(str(start)),
            end=end if isinstance(end, date) else date.fromisoformat(str(end)),
        ))
    return out


# ---------------------------------------------------------------------------
# Effect estimation
# ---------------------------------------------------------------------------

@dataclass
class Effect:
    window: str
    department: str
    effect: Optional[float]          # multiplier, 1.0 = no change
    ci_low: Optional[float]
    ci_high: Optional[float]
    n_obs: int                       # months contributing
    n_exposed: int                   # months with any exposure
    confidence: str
    reason: Optional[str] = None
    # Effect after controlling for a linear time trend. The seven months run
    # Jan-Jul, so "seasonal drift into summer" and "the two Ramadan months" are
    # nearly the same variable, and an uncontrolled fit credits the trend to the
    # calendar. None when the controlled model is not identifiable.
    effect_trend_adjusted: Optional[float] = None
    survives_trend_control: Optional[bool] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _ols(design: List[List[float]], y: List[float]):
    """(coefficients, standard errors) for an OLS fit, or None if degenerate.

    `design` includes its own intercept column. Uses numpy's least squares and
    the standard (X'X)^-1 * sigma^2 covariance, so a near-collinear design shows
    up as a huge standard error rather than a confident wrong answer — which is
    exactly what happens here when Ramadan is nearly collinear with the trend.
    """
    import numpy as np

    X = np.asarray(design, dtype=float)
    Y = np.asarray(y, dtype=float)
    n, k = X.shape
    dof = n - k
    if dof <= 0:
        return None
    if np.linalg.matrix_rank(X) < k:
        return None
    try:
        xtx_inv = np.linalg.pinv(X.T @ X)
    except np.linalg.LinAlgError:
        return None
    beta = xtx_inv @ X.T @ Y
    residuals = Y - X @ beta
    sigma2 = float(residuals @ residuals) / dof
    var = np.diag(xtx_inv) * sigma2
    se = np.sqrt(np.clip(var, 0, None))
    return beta.tolist(), se.tolist()


def estimate_effect(
    shares: Dict[date, float],
    window: Window,
    department: str,
    z: float = 1.96,
) -> Effect:
    """Multiplicative effect of a calendar window on a department's share.

    Regresses the department's share of monthly store volume on the month's
    exposure fraction. The multiplier is the fitted share at full exposure
    divided by the fitted share at zero exposure, so it reads as "×1.42 during
    Ramadan" while still resting on all seven points rather than a two-group
    comparison.
    """
    months = sorted(shares)
    x = [window.exposure(m) for m in months]
    y = [shares[m] for m in months]
    n_exposed = sum(1 for value in x if value > 0)

    if n_exposed == 0:
        return Effect(window.key, department, None, None, None, len(months), 0,
                      "unmeasurable", "window falls outside the data range")
    if n_exposed == len(months):
        return Effect(window.key, department, None, None, None, len(months), n_exposed,
                      "unmeasurable", "every month is exposed — no baseline to compare against")

    max_exposure = max(x)
    if max_exposure < MIN_EXPOSURE_FOR_EFFECT:
        return Effect(
            window.key, department, None, None, None, len(months), n_exposed,
            "unmeasurable",
            "window covers at most %.0f%% of any month; a full-month multiplier "
            "would extrapolate %.1fx beyond the largest observed exposure"
            % (100 * max_exposure, 1 / max_exposure if max_exposure else float("inf")),
        )

    fit = _ols([[1.0, xi] for xi in x], y)
    if fit is None:
        return Effect(window.key, department, None, None, None, len(months), n_exposed,
                      "unmeasurable", "degenerate design — slope not identified")

    (intercept, slope), (_se_intercept, se) = fit

    # Same fit with a linear time trend added. If the calendar coefficient does
    # not survive, what looked like a Ramadan effect was the series drifting.
    trend_effect = None
    survives = None
    trend_fit = _ols([[1.0, xi, float(i)] for i, xi in enumerate(x)], y)
    if trend_fit is not None:
        (b0, b_exposure, _b_trend), (_s0, s_exposure, _s_trend) = trend_fit
        if b0 > 1e-9:
            trend_effect = (b0 + b_exposure) / b0
            lo = (b0 + b_exposure - z * s_exposure) / b0
            hi = (b0 + b_exposure + z * s_exposure) / b0
            survives = not (lo <= 1.0 <= hi)
    if intercept <= 1e-9:
        return Effect(window.key, department, None, None, None, len(months), n_exposed,
                      "unmeasurable", "baseline share is zero — a multiplier is undefined")

    fitted_at_full = intercept + slope
    if fitted_at_full <= 0:
        # A share cannot be negative. The linear fit has left the physically
        # possible range, which means the data does not support the question.
        return Effect(
            window.key, department, None, None, None, len(months), n_exposed,
            "unmeasurable",
            "fitted share at full exposure is <= 0 — the linear model is out of "
            "range here, so no multiplier is defensible",
        )

    effect = fitted_at_full / intercept
    low = (fitted_at_full - z * se) / intercept
    high = (fitted_at_full + z * se) / intercept

    # Confidence is about how much evidence stands behind the number, not how
    # large it is. One partially-exposed month either side is not enough to
    # override a hand-set default, however clean the point estimate looks.
    spans_one = low <= 1.0 <= high
    # An interval reaching zero or below admits a negative share, which is
    # impossible. It means the fit is extrapolating past what the exposure
    # supports, so the number is reported but never published as a weight.
    unbounded_below = low <= 0

    if spans_one:
        confidence = "inconclusive"
        reason = "interval includes 1.0 — no detectable effect at this resolution"
    elif unbounded_below:
        confidence = "low"
        reason = ("interval reaches a negative share, which is impossible — the fit "
                  "is extrapolating past the observed exposure")
    elif survives is False:
        # The single most important check in this module. Ramadan falls in
        # months 2-3 of a Jan-Jul series, so calendar exposure is nearly
        # collinear with "early in the year". Without this, a department that
        # simply declines through spring reads as a strong Ramadan effect.
        confidence = "confounded"
        reason = ("effect disappears once a linear time trend is controlled for — "
                  "the window falls early in a 7-month series and cannot be "
                  "separated from seasonal drift")
    elif n_exposed >= 2:
        confidence = "medium"
        reason = None
    else:
        confidence = "low"
        reason = "only one month carries any exposure"

    return Effect(window.key, department, effect, low, high, len(months), n_exposed,
                  confidence, reason,
                  effect_trend_adjusted=trend_effect, survives_trend_control=survives)


def department_shares(panel: pd.DataFrame) -> Dict[str, Dict[date, float]]:
    """{department -> {month -> share of that month's total units}}.

    Shares rather than units because store-wide volume swings ~40% month to
    month; raw units would measure how busy the shop was.
    """
    known = panel[panel["department"].notna()]
    totals = panel.groupby("month")["units"].sum()
    out: Dict[str, Dict[date, float]] = {}
    for dept, group in known.groupby("department"):
        by_month = group.groupby("month")["units"].sum()
        out[str(dept)] = {
            m: float(by_month.get(m, 0.0) / totals[m]) if totals.get(m, 0) else 0.0
            for m in totals.index
        }
    return out


# ---------------------------------------------------------------------------
# Step 2 — velocity confidence
# ---------------------------------------------------------------------------

def velocity_confidence(months_observed: int, total_months: int) -> str:
    """Honest band for a product, from how many months carry a sales row.

    Absence is `none`, never zero. A product with no rows might be dead, never
    stocked, or missed by the export, and the three are indistinguishable here.
    """
    if months_observed <= 0:
        return "none"
    for band, minimum in CONFIDENCE_BANDS:
        if months_observed >= minimum:
            return band
    return "none"


def product_velocity(panel: pd.DataFrame, catalogue_size: Optional[int] = None) -> pd.DataFrame:
    """Per-barcode months observed, total units, and an honest confidence band."""
    if panel.empty:
        return pd.DataFrame(columns=["barcode", "months_observed", "total_units",
                                     "mean_units_per_month", "velocity_confidence"])
    total_months = panel["month"].nunique()
    sold = panel[panel["units"] > 0]
    grouped = sold.groupby("barcode").agg(
        months_observed=("month", "nunique"),
        total_units=("units", "sum"),
    ).reset_index()
    grouped["mean_units_per_month"] = grouped["total_units"] / total_months
    grouped["velocity_confidence"] = grouped["months_observed"].map(
        lambda n: velocity_confidence(int(n), total_months)
    )
    return grouped.sort_values("total_units", ascending=False)
