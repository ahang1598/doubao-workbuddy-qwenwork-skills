"""
Purged & Embargoed K-Fold cross-validation.

Reference
---------
Lopez de Prado, M. (2018). "Advances in Financial Machine Learning",
    Chapter 7: Cross-Validation in Finance.

Why standard K-Fold leaks in finance
-------------------------------------
Financial labels are built from information that *spans time* (e.g. a label
computed over [t, t+h]). When a train observation's label window overlaps a
test observation's window, information leaks across the split and CV scores
become optimistically biased. Two fixes:

  * PURGE  : drop train observations whose label window overlaps any test
             observation's label window.
  * EMBARGO: additionally drop train observations that occur right *after*
             the test window, because serial correlation leaks forward.

This module provides a scikit-learn-compatible splitter operating on label
spans (each sample i is active over [t1_start[i], t1_end[i]]).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class PurgedKFold:
    """
    K-Fold splitter that purges overlapping samples and applies an embargo.

    Parameters
    ----------
    n_splits : int
        Number of folds.
    label_times : pd.Series
        Index = sample start time (t0). Values = sample end time (t1), i.e.
        when the label is finally determined. Must be sorted by index.
    embargo_pct : float
        Fraction of the total number of observations to embargo after each
        test fold (e.g. 0.01 = 1%).
    """

    def __init__(self, n_splits: int, label_times: pd.Series, embargo_pct: float = 0.0):
        if not label_times.index.is_monotonic_increasing:
            raise ValueError("label_times index must be sorted ascending")
        self.n_splits = int(n_splits)
        self.label_times = label_times
        self.embargo_pct = float(embargo_pct)

    def split(self, X=None):
        t1 = self.label_times
        n = t1.shape[0]
        indices = np.arange(n)
        embargo = int(n * self.embargo_pct)

        test_starts = [(i[0], i[-1] + 1) for i in np.array_split(indices, self.n_splits)]

        for start, end in test_starts:
            test_idx = indices[start:end]
            t0_test = t1.index[start]                  # first test start time
            t1_test_max = t1.iloc[start:end].max()     # last test label end

            # PURGE: remove train samples whose label window overlaps the test
            # window [t0_test, t1_test_max].
            train_mask = np.ones(n, dtype=bool)
            train_mask[start:end] = False
            overlap = (t1.values >= t0_test) & (t1.index.values <= t1_test_max)
            train_mask &= ~overlap

            # EMBARGO: drop the first `embargo` train samples immediately after
            # the test fold.
            if embargo > 0 and end < n:
                embargo_end = min(end + embargo, n)
                train_mask[end:embargo_end] = False

            train_idx = indices[train_mask]
            yield train_idx, test_idx


def cross_val_score_purged(estimator, X, y, label_times, n_splits=6, embargo_pct=0.01,
                           scorer=None):
    """
    Convenience wrapper: run a purged & embargoed CV and return fold scores.
    `scorer(estimator, X_test, y_test) -> float`; defaults to estimator.score.
    """
    cv = PurgedKFold(n_splits=n_splits, label_times=label_times, embargo_pct=embargo_pct)
    X = np.asarray(X)
    y = np.asarray(y)
    scores = []
    for train_idx, test_idx in cv.split(X):
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
        estimator.fit(X[train_idx], y[train_idx])
        if scorer is None:
            scores.append(float(estimator.score(X[test_idx], y[test_idx])))
        else:
            scores.append(float(scorer(estimator, X[test_idx], y[test_idx])))
    return np.array(scores)


if __name__ == "__main__":
    # Each label spans 5 observations forward; show how many train rows get purged.
    n = 100
    idx = pd.RangeIndex(n)
    label_times = pd.Series(idx + 5, index=idx)
    cv = PurgedKFold(n_splits=5, label_times=label_times, embargo_pct=0.02)
    for k, (tr, te) in enumerate(cv.split()):
        print(f"fold {k}: test={len(te):3d}  train={len(tr):3d}  "
              f"(purged+embargoed {n - len(te) - len(tr):d} rows)")
