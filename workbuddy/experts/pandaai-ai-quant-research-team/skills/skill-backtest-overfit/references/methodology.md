# Methodology

All Sharpe ratios below are **per-period** (not annualised) unless stated.
Annualise only for display: `SR_annual = SR_period * sqrt(periods_per_year)`.

## 1. Probabilistic Sharpe Ratio (PSR)

The estimated Sharpe ratio has estimation error that grows with non-normality.
López de Prado (2012) gives its standard error:

```
sigma(SR_hat) = sqrt( (1 - g1*SR + (g2 - 1)/4 * SR^2) / (n - 1) )
```

where `g1` = skewness, `g2` = **non-excess** kurtosis (3 for a normal), `n` =
number of observations. The Probabilistic Sharpe Ratio is the probability that
the true Sharpe exceeds a benchmark `SR*`:

```
PSR(SR*) = Phi( (SR_hat - SR*) / sigma(SR_hat) )
```

Negative skew and fat tails inflate `sigma(SR_hat)` and lower PSR — exactly the
return profiles (e.g. short-vol) that look great until they don't.

## 2. Deflated Sharpe Ratio (DSR)

When you select the best of `N` trials, the benchmark must rise to the Sharpe
you'd expect from luck alone. Bailey & López de Prado (2014):

```
SR0 = sqrt(V) * [ (1 - gamma) * Z^-1(1 - 1/N) + gamma * Z^-1(1 - 1/(N*e)) ]
DSR = PSR(SR0)
```

`V` = variance of the Sharpe estimates **across the N trials**, `gamma` =
Euler–Mascheroni constant (0.5772), `Z^-1` = inverse standard-normal CDF,
`e` = Euler's number. DSR is the probability that the selected strategy's true
Sharpe beats what selection bias alone would produce. **Pass at DSR ≥ 0.95.**

> Supplying the real per-trial Sharpes (so `V` is measured, not approximated)
> is important — without them the code falls back to the single-estimate
> variance, which understates `V` and makes DSR too lenient.

## 3. Probability of Backtest Overfitting (PBO) — CSCV

Bailey, Borwein, López de Prado & Zhu (2017). Build a performance matrix
`M` (T×N: T periods, N configurations). Split the T rows into `S` disjoint,
contiguous, equal blocks. For each of the `C(S, S/2)` ways to choose S/2 blocks
as in-sample (IS) and the rest as out-of-sample (OOS):

1. pick the IS-best configuration `n*`;
2. compute its OOS relative rank `w ∈ (0,1)`;
3. logit `λ = ln(w / (1 - w))`.

```
PBO = P[ λ <= 0 ] = fraction of splits where the IS winner is below the OOS median
```

PBO ≈ 0.5 means the IS winner is a coin flip OOS (pure overfit). PBO near 0
means the winner generalises. **Flag at PBO > 0.5.** Keep `S` modest (16 →
12,870 splits) because cost grows like `C(S, S/2)`.

## 4. Purged & Embargoed K-Fold CV

López de Prado (2018), ch.7. Financial labels span time, so a naive K-Fold lets
information leak across the train/test boundary. Two corrections:

- **Purge**: drop train samples whose label window overlaps the test window.
- **Embargo**: drop train samples immediately *after* the test window (serial
  correlation leaks forward).

`scripts/purged_kfold.py` is a scikit-learn-style splitter taking per-sample
label spans `t1`. Use it for any ML-based factor / labelling pipeline.

## 5. Multiple-Testing Haircut

Harvey & Liu (2015). The best of `N` tests must clear a higher bar than the
single-test t≈1.96. Convert the Sharpe to a t-stat (`t = SR * sqrt(n)`),
adjust its p-value for multiplicity, then map back to an adjusted Sharpe:

- **Bonferroni**: `p_adj = min(1, p * N)`
- **Holm**: step-down, `p_adj = p * (N - rank + 1)`
- **BHY**: Benjamini–Hochberg–Yekutieli with the harmonic correction `c(N)`

```
haircut = 1 - SR_adjusted / SR_observed
```

## 6. Minimum Track Record Length (MinTRL)

Bailey & López de Prado (2012): the sample length needed for the observed
Sharpe to be statistically greater than `SR*` at confidence `alpha`:

```
MinTRL = 1 + (1 - g1*SR + (g2 - 1)/4 * SR^2) * ( Z_alpha / (SR - SR*) )^2
```

If `MinTRL` exceeds your actual sample, the Sharpe is not yet trustworthy.

## References

- Bailey, D. H., & López de Prado, M. (2012). *The Sharpe Ratio Efficient Frontier.* Journal of Risk 15(2).
- Bailey, D. H., & López de Prado, M. (2014). *The Deflated Sharpe Ratio.* Journal of Portfolio Management 40(5).
- Bailey, Borwein, López de Prado & Zhu (2017). *The Probability of Backtest Overfitting.* Journal of Computational Finance 20(4).
- Harvey, C. R., & Liu, Y. (2015). *Backtesting.* Journal of Portfolio Management 42(1).
- López de Prado, M. (2018). *Advances in Financial Machine Learning,* ch.7. Wiley.
