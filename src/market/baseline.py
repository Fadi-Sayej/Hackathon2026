"""
baseline.py — the naive rules, measured before any model (T4 / #49, Step 2).

The issue is blunt about why this exists:

    "Implement and score the naive rule first: *present in the price file ⇒
    available*. Every later model is judged against this number. If the HMM does
    not beat it, the complexity is not justified — and you will only know that if
    you measured it first. This step saves weeks."

So this module scores rules, not products. It contains no inference. Its whole
job is to produce a number that a later model has to beat by ≥ +0.15 F1.

TWO RULES, AND THEY ARE NOT THE SAME RULE
-----------------------------------------
N1  "listed in the catalogue ⇒ available"
    Measurable today against YomYom, the one store whose stock we actually know.
    Thousands of labelled items, a large real negative class.

N2  "present in TODAY's price file ⇒ available"
    The exact rule the issue names. Needs a per-day availability label, which
    only the delivery catalogue provides, and only for venues that appear in
    both sources.

N1 is the weaker claim — an item master keeps discontinued rows forever, while a
price file is re-published daily — so N1's error rate is an upper bound on N2's,
not a substitute for it. They are reported separately and never averaged.

WHY THE INTERVALS ARE NOT DECORATION
------------------------------------
A rule scored on 3 days of a 274-item catalogue can read 100% and mean nothing.
Every figure here carries a Wilson interval so a small denominator is visible in
the number itself rather than buried in a footnote.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, Optional, Set, Tuple


@dataclass
class Score:
    """One rule, scored against one label source.

    `positive` is the AVAILABLE class throughout. The interesting failure is a
    false positive: the rule claims a product is there and it is not, which is
    what sends a manager to an empty shelf.
    """

    rule: str
    label_source: str
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int

    @property
    def total(self) -> int:
        return (
            self.true_positive + self.false_positive
            + self.true_negative + self.false_negative
        )

    @property
    def predicted_positive(self) -> int:
        return self.true_positive + self.false_positive

    @property
    def actual_positive(self) -> int:
        return self.true_positive + self.false_negative

    @property
    def actual_negative(self) -> int:
        return self.true_negative + self.false_positive

    @property
    def precision(self) -> Optional[float]:
        """Of the products the rule called available, how many were.

        None when the rule predicted nothing — reporting 0.0 there would claim a
        measurement that was never made.
        """
        if self.predicted_positive == 0:
            return None
        return self.true_positive / self.predicted_positive

    @property
    def recall(self) -> Optional[float]:
        if self.actual_positive == 0:
            return None
        return self.true_positive / self.actual_positive

    @property
    def f1(self) -> Optional[float]:
        p, r = self.precision, self.recall
        if p is None or r is None or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    @property
    def accuracy(self) -> Optional[float]:
        if self.total == 0:
            return None
        return (self.true_positive + self.true_negative) / self.total

    @property
    def false_positive_rate(self) -> Optional[float]:
        """Of the products that were NOT available, how many the rule claimed were.

        This is the number the issue is really about: "items linger for weeks
        after selling out". A rule that never sees a negative cannot report it.
        """
        if self.actual_negative == 0:
            return None
        return self.false_positive / self.actual_negative

    @property
    def precision_interval(self) -> Optional[Tuple[float, float]]:
        if self.predicted_positive == 0:
            return None
        return wilson_interval(self.true_positive, self.predicted_positive)

    @property
    def has_negative_class(self) -> bool:
        """Whether anything was actually unavailable in the evaluation window.

        Without a negative class, precision is 1.0 by construction and the score
        is not evidence of anything. Callers must check this before quoting a
        figure — `to_dict()` carries it for exactly that reason.
        """
        return self.actual_negative > 0

    def to_dict(self) -> Dict[str, object]:
        d = asdict(self)
        d.update(
            total=self.total,
            predicted_positive=self.predicted_positive,
            actual_positive=self.actual_positive,
            actual_negative=self.actual_negative,
            precision=self.precision,
            recall=self.recall,
            f1=self.f1,
            accuracy=self.accuracy,
            false_positive_rate=self.false_positive_rate,
            precision_interval=self.precision_interval,
            has_negative_class=self.has_negative_class,
        )
        return d


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> Tuple[float, float]:
    """95% Wilson score interval for a proportion.

    Wilson rather than normal-approximation because every interesting case here
    is near 0 or near 1 with a small denominator, which is exactly where the
    normal approximation returns bounds outside [0, 1].
    """
    if trials <= 0:
        return (0.0, 1.0)
    p = successes / trials
    denom = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def score_rule(
    predicted_available: Iterable[bool],
    actually_available: Iterable[bool],
    rule: str,
    label_source: str,
) -> Score:
    """Confusion matrix for one rule over one aligned set of observations.

    Both iterables must be in the same order and the same length; zipping silently
    truncates, so the length is checked rather than assumed.
    """
    predicted = list(predicted_available)
    actual = list(actually_available)
    if len(predicted) != len(actual):
        raise ValueError(
            "predicted (%d) and actual (%d) must align one-to-one"
            % (len(predicted), len(actual))
        )

    tp = fp = tn = fn = 0
    for p, a in zip(predicted, actual):
        if p and a:
            tp += 1
        elif p and not a:
            fp += 1
        elif not p and a:
            fn += 1
        else:
            tn += 1
    return Score(rule, label_source, tp, fp, tn, fn)


def score_membership_rule(
    universe: Set[str],
    predicted_present: Set[str],
    actually_available: Set[str],
    rule: str,
    label_source: str,
) -> Score:
    """Score a set-membership rule over an explicit universe.

    The universe matters more than the rule. Scoring "in the price file ⇒
    available" over every barcode in the price file makes the negative class
    unmeasurable, because nothing outside the delivery catalogue has a label at
    all. The caller must pass the set of products for which the label is
    *defined*, and both other sets are intersected down to it here.
    """
    keys = sorted(universe)
    return score_rule(
        [k in predicted_present for k in keys],
        [k in actually_available for k in keys],
        rule=rule,
        label_source=label_source,
    )
