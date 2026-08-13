"""
T4 / #49 Step 2 — the naive baselines.

These numbers decide whether a later model ships at all ("if the HMM does not
beat it, the complexity is not justified"), so the arithmetic is checked against
values worked out by hand, not against whatever the implementation returns.

The cases that matter most are the degenerate ones. A rule scored on a window
with no negatives reads as near-perfect, and a baseline that is silently
unbeatable — or silently trivial — wastes exactly the weeks this step exists to
save.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.market.baseline import (  # noqa: E402
    Score,
    score_membership_rule,
    score_rule,
    wilson_interval,
)


def make(tp=0, fp=0, tn=0, fn=0):
    return Score("rule", "labels", tp, fp, tn, fn)


# ---------------------------------------------------------------------------
# The arithmetic, against hand-worked values
# ---------------------------------------------------------------------------

def test_metrics_match_hand_calculation():
    s = make(tp=6, fp=2, tn=10, fn=2)
    assert s.precision == pytest.approx(6 / 8)
    assert s.recall == pytest.approx(6 / 8)
    assert s.f1 == pytest.approx(0.75)
    assert s.accuracy == pytest.approx(16 / 20)
    assert s.false_positive_rate == pytest.approx(2 / 12)
    assert s.total == 20


def test_f1_is_the_harmonic_mean_not_the_average():
    # precision 1.0, recall 0.5 -> arithmetic mean 0.75, harmonic 0.667.
    s = make(tp=5, fp=0, tn=5, fn=5)
    assert s.precision == pytest.approx(1.0)
    assert s.recall == pytest.approx(0.5)
    assert s.f1 == pytest.approx(2 / 3)


def test_confusion_matrix_counts_each_cell_correctly():
    s = score_rule(
        predicted_available=[True, True, False, False],
        actually_available=[True, False, True, False],
        rule="r", label_source="l",
    )
    assert (s.true_positive, s.false_positive, s.false_negative, s.true_negative) == (1, 1, 1, 1)


# ---------------------------------------------------------------------------
# Undefined is not zero
# ---------------------------------------------------------------------------

def test_undefined_metrics_report_none_rather_than_zero():
    """A rule that predicted nothing has no precision. Reporting 0.0 would claim
    a measurement that was never made, and 0.0 is a number a model can 'beat'."""
    assert make(tn=10).precision is None
    assert make(fp=1, tn=10).recall is None          # nothing was actually available
    assert make(tn=10).f1 is None
    assert make().accuracy is None
    assert make(tp=5).false_positive_rate is None    # nothing was actually unavailable


def test_a_window_with_no_negatives_is_flagged():
    """Precision is 1.0 by construction when nothing was unavailable. Callers must
    be able to see that before quoting the figure."""
    s = make(tp=100, fn=5)
    assert s.precision == 1.0
    assert s.has_negative_class is False
    assert s.to_dict()["has_negative_class"] is False

    assert make(tp=100, fp=1).has_negative_class is True


# ---------------------------------------------------------------------------
# Wilson interval
# ---------------------------------------------------------------------------

def test_wilson_interval_matches_hand_calculation():
    # 13 of 13, z=1.96: centre 0.88594, margin 0.11405 -> [0.7719, 1.0].
    lo, hi = wilson_interval(13, 13)
    assert lo == pytest.approx(0.7719, abs=1e-3)
    assert hi == pytest.approx(1.0)


def test_wilson_interval_stays_inside_zero_and_one():
    """The reason it is Wilson and not the normal approximation: every interesting
    case here sits at 0 or 1 with a small denominator, where normal returns bounds
    outside [0, 1]."""
    for successes, trials in ((0, 5), (5, 5), (0, 1), (1, 1), (0, 1000)):
        lo, hi = wilson_interval(successes, trials)
        assert 0.0 <= lo <= hi <= 1.0


def test_wilson_interval_narrows_as_evidence_accumulates():
    narrow = wilson_interval(90, 100)
    wide = wilson_interval(9, 10)
    assert (narrow[1] - narrow[0]) < (wide[1] - wide[0])


def test_wilson_interval_of_nothing_is_total_ignorance():
    assert wilson_interval(0, 0) == (0.0, 1.0)


# ---------------------------------------------------------------------------
# The universe is the part that goes wrong quietly
# ---------------------------------------------------------------------------

def test_membership_rule_scores_only_over_the_universe():
    """Products outside the universe have no label, so they must not be scored.

    Scoring a price-file rule over the whole price file instead of over the
    products the label actually covers turns thousands of never-delivered SKUs
    into false positives, which is a measurement of the SKU scheme.
    """
    s = score_membership_rule(
        universe={"a", "b", "c"},
        predicted_present={"a", "b", "c", "d", "e"},   # d, e are unlabelled
        actually_available={"a", "b", "c"},
        rule="r", label_source="l",
    )
    assert s.total == 3
    assert s.false_positive == 0


def test_membership_rule_counts_a_lingering_listing_as_a_false_positive():
    """The whole phenomenon: still listed, no longer obtainable."""
    s = score_membership_rule(
        universe={"gone", "here"},
        predicted_present={"gone", "here"},   # price file still lists both
        actually_available={"here"},          # only one is orderable
        rule="r", label_source="l",
    )
    assert s.false_positive == 1
    assert s.false_positive_rate == pytest.approx(1.0)


def test_an_always_positive_rule_reports_recall_one_and_base_rate_precision():
    """N1's shape. Recall 1.0 is not skill — it is what predicting everything does."""
    s = score_membership_rule(
        universe={"a", "b", "c", "d"},
        predicted_present={"a", "b", "c", "d"},
        actually_available={"a"},
        rule="r", label_source="l",
    )
    assert s.recall == 1.0
    assert s.precision == pytest.approx(0.25)
    assert s.true_negative == 0


def test_a_constant_rule_can_beat_a_real_rule_on_a_rare_negative_class():
    """Measured on the real 3-day window, and the reason N0 is reported.

    With 13 unavailable of 750, the price-file rule (F1 0.979) scores below
    always-available (F1 0.991). A model judged against the wrong one of those
    looks like an improvement while being a regression.
    """
    real = make(tp=719, fp=13, tn=0, fn=18)
    constant = make(tp=737, fp=13, tn=0, fn=0)
    assert real.f1 == pytest.approx(0.979, abs=5e-4)
    assert constant.f1 == pytest.approx(0.991, abs=5e-4)
    assert constant.f1 > real.f1
    assert real.true_negative == 0          # caught none of the 13


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------

def test_misaligned_inputs_raise_instead_of_truncating():
    """zip() would silently drop the tail and score a shorter window than reported."""
    with pytest.raises(ValueError):
        score_rule([True, False, True], [True, False], rule="r", label_source="l")
