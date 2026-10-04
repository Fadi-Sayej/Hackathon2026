"""The statistics behind F12-S1's measurement (FR-203, FR-205, FR-209). Pure functions, numpy only.

**The model.** FR-205 specifies a Poisson regression of each product's units in each window, with
the window's report days as exposure, a term per product and arrangement, and a term per window.
Conditional on a product's units over its two windows, `n = before + after`, its after units are
binomial with log-odds:

    log(after report days ÷ before report days)       the exposure, as an offset
    + δ[arrangement]                                   the arrangement's window term
    + β_arranged · arranged                            having been arranged at all
    + β_facings  · log(after facings ÷ before facings) the space elasticity
    + β_eye      · eye-level change                    +1, 0 or −1

The product terms cancel, so the fit is a logistic regression with one intercept per arrangement.
For Poisson this gives the same estimates of δ and β as the full fit (Hausman, Hall and Griliches,
1984). A unit that sold nothing in both windows carries no information, and drops out of both.

**The interval** is a bootstrap that resamples whole fixtures, because the products on one fixture
share whatever happened there (FR-205). A fixture drawn twice enters twice. A draw that leaves an
arrangement without a comparison unit drops that arrangement's arranged units, and a draw with no
arranged unit left, or no variation in its facing ratios, is drawn again.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

COVARIATES = ("arranged", "log_facings", "eye_change")


@dataclass(frozen=True)
class Unit:
    """One product in one arrangement's pair of windows."""
    arrangement: str        # the arrangement's key
    cluster: str            # the fixture the product stands on, the bootstrap's unit
    before: float           # units sold in the earlier window
    after: float            # units sold in the later window
    exposure_before: int    # report days its units are known on, in each window
    exposure_after: int
    arranged: float         # 1 for an arranged product, 0 for a comparison one
    log_facings: Optional[float]   # None: before facings unknown or zero (left out of the fit)
    eye_change: float


@dataclass(frozen=True)
class Fit:
    terms: dict             # {"arranged": β, "log_facings": β, "eye_change": β}, the terms fitted
    window: dict            # {arrangement: δ}
    used: int               # units in the fit


def usable(units: Sequence[Unit]) -> list:
    return [u for u in units if u.before + u.after > 0 and u.exposure_before > 0 and u.exposure_after > 0
            and u.log_facings is not None]


def terms_with_variation(units: Sequence[Unit]) -> tuple:
    """The covariates the data can estimate. A term no arranged unit varies is dropped, decided once
    on the full sample so every bootstrap draw fits the same model (FR-205)."""
    arranged = [u for u in units if u.arranged]
    if not arranged:
        return ()
    out = ["arranged"]
    if len({round(u.log_facings, 12) for u in arranged}) > 1:
        out.append("log_facings")
    if any(u.eye_change for u in arranged):
        out.append("eye_change")
    return tuple(out)


def fit(units: Sequence[Unit], terms: tuple, *, max_iter: int = 60, tol: float = 1e-10) -> Optional[Fit]:
    """Iteratively reweighted least squares on the conditional logit. None when it cannot be fitted."""
    rows = usable(units)
    arrangements = sorted({u.arrangement for u in rows})
    if not rows or not arrangements:
        return None
    col = {a: i for i, a in enumerate(arrangements)}
    k = len(arrangements) + len(terms)
    X = np.zeros((len(rows), k))
    for r, u in enumerate(rows):
        X[r, col[u.arrangement]] = 1.0
        for j, t in enumerate(terms):
            X[r, len(arrangements) + j] = getattr(u, t)
    y = np.array([u.after for u in rows], dtype=float)
    n = np.array([u.before + u.after for u in rows], dtype=float)
    offset = np.log(np.array([u.exposure_after / u.exposure_before for u in rows], dtype=float))
    beta = np.zeros(k)
    with np.errstate(all="ignore"):     # numpy 2.0 with Accelerate warns on finite matmuls; checked below
        return _irls(X, y, n, offset, beta, arrangements, col, terms, rows, max_iter, tol)


def _irls(X, y, n, offset, beta, arrangements, col, terms, rows, max_iter, tol) -> Optional[Fit]:
    for _ in range(max_iter):
        eta = offset + X @ beta
        p = 1.0 / (1.0 + np.exp(-np.clip(eta, -30, 30)))
        w = n * p * (1 - p)
        if not np.all(np.isfinite(w)) or w.sum() == 0:
            return None
        grad = X.T @ (y - n * p)
        hess = X.T @ (X * w[:, None])
        try:
            step = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            return None
        beta = beta + step
        if np.max(np.abs(step)) < tol:
            break
    else:
        return None
    if not np.all(np.isfinite(beta)) or np.max(np.abs(beta)) > 25:
        return None                                   # separation: a term ran away, not an estimate
    return Fit(terms={t: float(beta[len(arrangements) + j]) for j, t in enumerate(terms)},
               window={a: float(beta[i]) for a, i in col.items()}, used=len(rows))


def _draw(rng: np.random.Generator, clusters: list, by_cluster: dict) -> list:
    """Whole fixtures, with replacement. The product terms have cancelled (see the module), so a
    fixture drawn twice is simply its rows twice, sharing their arrangement's window term."""
    picked = rng.choice(len(clusters), size=len(clusters), replace=True)
    sample = [u for i in picked for u in by_cluster[clusters[i]]]
    with_comparison = {u.arrangement for u in sample if not u.arranged}
    # An arrangement whose comparison fixtures were all left out has no yardstick in this draw.
    return [u for u in sample if not u.arranged or u.arrangement in with_comparison]


def bootstrap(units: Sequence[Unit], terms: tuple, *, draws: int, seed: int, level: float,
              watch: Sequence[str]) -> Optional[dict]:
    """Percentile intervals for the `watch` terms, or None when too few draws can be fitted."""
    rows = usable(units)
    clusters = sorted({u.cluster for u in rows})
    by_cluster: dict = {}
    for u in rows:
        by_cluster.setdefault(u.cluster, []).append(u)
    rng = np.random.default_rng(seed)
    kept: dict = {t: [] for t in watch}
    redrawn, attempts = 0, 0
    while len(kept[watch[0]]) < draws and attempts < draws * 5:
        attempts += 1
        sample = _draw(rng, clusters, by_cluster)
        arranged = [u for u in sample if u.arranged]
        if not arranged or ("log_facings" in terms and len({round(u.log_facings, 12) for u in arranged}) < 2):
            redrawn += 1
            continue
        result = fit(sample, terms)
        if result is None:
            redrawn += 1
            continue
        for t in watch:
            kept[t].append(result.terms[t])
    if len(kept[watch[0]]) < draws:
        return None
    tail = (1 - level) / 2 * 100
    return {"intervals": {t: [float(np.percentile(v, tail)), float(np.percentile(v, 100 - tail))]
                          for t, v in kept.items()},
            "draws": draws, "redrawn": redrawn}
