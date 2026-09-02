"""
Probability of Backtest Overfitting (PBO) via Combinatorially-Symmetric
Cross-Validation (CSCV).

Reference
---------
Bailey, D. H., Borwein, J., Lopez de Prado, M., & Zhu, Q. J. (2017).
    "The Probability of Backtest Overfitting." Journal of Computational
     Finance, 20(4), 39-69.

Idea
----
Given a performance matrix M (T observations x N strategy configurations),
CSCV splits the T rows into S disjoint, contiguous, equal blocks. For every
way of choosing S/2 blocks as the in-sample (IS) set (the complement is the
out-of-sample, OOS set):

  1. rank the N strategies by an IS performance metric (default Sharpe);
  2. take the IS-best strategy n*;
  3. find the OOS rank of n* among the N strategies;
  4. map it to a relative rank w in (0, 1) and a logit lambda = ln(w/(1-w)).

PBO = fraction of splits where the IS-best strategy lands at or below the
OOS median (lambda <= 0). A high PBO means "the configuration that looked
best in-sample is no better than a coin flip out-of-sample" -> overfit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Callable

import numpy as np


def _sharpe_cols(block: np.ndarray) -> np.ndarray:
    """Per-period Sharpe of each column of a (rows x N) block."""
    mu = np.nanmean(block, axis=0)
    sd = np.nanstd(block, axis=0, ddof=1)
    sd = np.where(sd == 0, np.nan, sd)
    return mu / sd


@dataclass
class PBOResult:
    pbo: float
    n_splits: int
    n_strategies: int
    n_blocks: int
    logits: list[float] = field(default_factory=list)
    oos_ranks: list[float] = field(default_factory=list)
    # OOS performance of the IS-selected strategy vs the best possible OOS,
    # useful to visualise performance degradation.
    is_best_oos_perf: list[float] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "pbo": self.pbo,
            "n_splits": self.n_splits,
            "n_strategies": self.n_strategies,
            "n_blocks": self.n_blocks,
            "median_logit": float(np.median(self.logits)) if self.logits else float("nan"),
        }


def probability_of_backtest_overfitting(
    perf_matrix: np.ndarray,
    n_blocks: int = 16,
    metric: Callable[[np.ndarray], np.ndarray] = _sharpe_cols,
) -> PBOResult:
    """
    Parameters
    ----------
    perf_matrix : np.ndarray, shape (T, N)
        Per-period PnL / returns. Columns are competing strategy configs,
        rows are time. N should be >= 2 and reasonably large for PBO to mean
        anything (you are estimating overfitting *across* configurations).
    n_blocks : int
        Number of contiguous blocks S (must be even). C(S, S/2) splits are
        evaluated, so keep S modest (16 -> 12,870 splits).
    metric : callable
        Maps a (rows x N) block to an array of N performance scores.
    """
    M = np.asarray(perf_matrix, dtype=float)
    if M.ndim != 2:
        raise ValueError("perf_matrix must be 2D (T x N)")
    T, N = M.shape
    if N < 2:
        raise ValueError("Need at least 2 strategy configurations to assess PBO")
    if n_blocks % 2 != 0:
        raise ValueError("n_blocks (S) must be even")
    if n_blocks > T:
        raise ValueError("n_blocks cannot exceed number of observations")

    # Contiguous, (almost) equal blocks of row indices.
    block_idx = np.array_split(np.arange(T), n_blocks)
    blocks = list(range(n_blocks))

    logits: list[float] = []
    oos_ranks: list[float] = []
    is_best_oos_perf: list[float] = []

    for is_blocks in combinations(blocks, n_blocks // 2):
        is_set = set(is_blocks)
        is_rows = np.concatenate([block_idx[b] for b in blocks if b in is_set])
        oos_rows = np.concatenate([block_idx[b] for b in blocks if b not in is_set])

        is_perf = metric(M[is_rows])
        oos_perf = metric(M[oos_rows])

        if np.all(np.isnan(is_perf)):
            continue
        n_star = int(np.nanargmax(is_perf))

        # OOS rank of the IS-best strategy (1 = worst ... N = best).
        valid = ~np.isnan(oos_perf)
        # relative rank in (0,1): proportion of strategies the IS-best beats OOS
        rank = float(np.sum(oos_perf[valid] <= oos_perf[n_star]))
        w = rank / (np.sum(valid) + 1.0)
        w = min(max(w, 1e-6), 1.0 - 1e-6)
        logits.append(float(np.log(w / (1.0 - w))))
        oos_ranks.append(w)
        is_best_oos_perf.append(float(oos_perf[n_star]))

    pbo = float(np.mean([1.0 if lam <= 0 else 0.0 for lam in logits])) if logits else float("nan")
    return PBOResult(
        pbo=pbo,
        n_splits=len(logits),
        n_strategies=N,
        n_blocks=n_blocks,
        logits=logits,
        oos_ranks=oos_ranks,
        is_best_oos_perf=is_best_oos_perf,
    )


if __name__ == "__main__":
    rng = np.random.default_rng(1)
    T, N = 1000, 50
    # Pure-noise strategies: by construction the IS winner is luck -> PBO ~ 0.5
    noise = rng.normal(0, 1, size=(T, N))
    res = probability_of_backtest_overfitting(noise, n_blocks=14)
    print("Pure-noise strategies  PBO =", round(res.pbo, 3), "(expect ~0.5)")

    # One genuinely good strategy among noise -> PBO should drop sharply.
    edge = noise.copy()
    edge[:, 0] += 0.15  # column 0 has real positive drift
    res2 = probability_of_backtest_overfitting(edge, n_blocks=14)
    print("One real edge          PBO =", round(res2.pbo, 3), "(expect low)")
