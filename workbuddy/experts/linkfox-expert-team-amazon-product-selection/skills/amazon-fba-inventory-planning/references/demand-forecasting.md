# Demand Forecasting for Amazon FBA Inventory Planning

Demand forecasting sits upstream of safety stock and restock quantity.  
A usable forecast of daily demand (\( \hat{D} \)) and its uncertainty feeds every downstream calculation.

## Role in the Planning Chain

```
History + signals  →  Demand forecast (D̂, σ)
                           ↓
              Safety stock + reorder point + target cover
                           ↓
                    Recommended order qty Q
```

Forecast answers “how much will we sell?”  
Safety stock answers “how wrong might that forecast be?”

## Model Selection Rules (Practical)

| SKU profile | Recommended approach | Notes |
|-------------|----------------------|-------|
| Stable, low noise | Moving average or single exponential smoothing | Simple, robust |
| Clear trend (up/down) | Holt (double exponential smoothing) | Captures level + trend |
| Strong seasonality | Holt-Winters or seasonal index + deseasonalized forecast | Use 2–3 years history when possible |
| Long-tail / intermittent | Croston or SBA, or conservative rule-of-thumb | Standard smoothing underestimates |
| Promo / ad driven | Base forecast × causal uplift factors | Keep factors explicit and reviewable |
| New ASIN (little history) | Analog SKU + small test quantity | Tighten after 60–90 days of data |

**Default for most mid-tier SKUs:** single exponential smoothing or 7/14/30-day weighted average, then apply seasonal coefficient when seasonality is material.

## Core Methods (Seller-Practical)

### 1. Moving / Weighted Moving Average

```
D̂_t = average of last n periods
```

Weighted version gives more weight to recent weeks.  
Good baseline for stable items. Slow to react to trend or season.

### 2. Single Exponential Smoothing

```
D̂_t = α · D_{t-1} + (1 − α) · D̂_{t-1}
```

- Typical α: 0.1–0.3 (lower = smoother, higher = more reactive)
- Use when no strong trend or season

### 3. Holt (Level + Trend)

Extends smoothing to include a trend component.  
Use when the SKU is steadily growing or declining.

### 4. Holt-Winters / Seasonal Index

For products with repeating intra-year patterns (fans, heaters, holiday, apparel seasons):

- Prefer **multiplicative** form when seasonal swings scale with volume
- Seasonal index method (already in this skill) is transparent and easy to explain to ops
- Minimum practical history: 2 full seasonal cycles; 3 is better

### 5. Intermittent Demand (Croston / SBA)

Many long-tail FNSKUs show long zero streaks with occasional orders.  
Ordinary averaging understates true demand rate.  
Croston (and Syntetos-Boylan Approximation) separately smooth demand size and inter-demand interval.

### 6. Causal / Uplift Overlay

Start with a statistical base, then adjust with explicit factors:

```
D̂_final = D̂_base × (1 + ad_uplift + promo_uplift + price_effect + event_effect + …)
```

Keep each factor documented so it can be reviewed and later measured.

### 7. Bayesian Methods (implemented in scripts/forecast_bayesian.py)

Use when you want an explicit posterior on the demand rate and a coherent uncertainty measure for safety stock.

**Poisson–Gamma (conjugate rate model)**  
- Likelihood: daily counts ~ Poisson(λ)  
- Prior: λ ~ Gamma(a₀, b₀) (shape–rate)  
- Posterior: Gamma(a₀ + Σx, b₀ + n)  
- Forecast daily demand = E[λ] = aₙ / bₙ  
- Uncertainty: use predictive std √(E[λ] + Var[λ]) as `std_demand` input  
- Best for count-like daily sales; works reasonably on intermittent series with a weakly informative prior (e.g. a₀=b₀=1)

**Bayesian exponential smoothing (scalar level)**  
- Level ~ Normal(μ₀, P₀), observations ~ Normal(level, R)  
- Sequential Bayesian update (scalar Kalman form)  
- Posterior mean = forecast daily demand; posterior std = uncertainty proxy  
- Better when sales are noisy continuous values rather than pure counts  

**Practical notes**
- Start with weakly informative priors; let data dominate after 2–4 weeks of observations.
- For strong seasonality, deseasonalize first (seasonal_index.py) or run Bayesian methods inside seasonal windows.
- Always pass both mean and std into calculate_restock.py (`--daily-sales`, `--std-demand`).
- Bayesian outputs do not replace promo/event judgment — apply causal uplifts after the base posterior mean if needed.

## Forecasting Horizon

Align horizon with decision lead time:

- Short-term restock: cover lead time + review period (often 30–60 days)
- Seasonal build: cover the entire peak window you intend to stock for
- Always add a short buffer for Amazon receiving variability

## Uncertainty and Link to Safety Stock

- Use forecast error (or residual dispersion) as input to σ_d when possible
- High MAPE / unstable SKUs → higher service level or larger safety stock
- Stable, low-error SKUs → can run tighter cover

If formal error history is unavailable, fall back to historical daily demand standard deviation (as in the existing safety-stock formula).

## Accuracy Metrics (Keep Simple)

| Metric | Use |
|--------|-----|
| WMAPE | Primary for multi-SKU portfolios (volume-weighted) |
| Bias | Detect systematic over/under forecasting |
| MAPE | OK for higher-volume SKUs; unstable when demand ≈ 0 |
| RMSE | Sensitive to large misses; useful for model comparison |

Review monthly. Persistent bias is more dangerous than random noise.

## Operating Rules for FBA Planners

1. Forecast at **FNSKU** level when size/color velocities differ.
2. Separate Amazon-channel demand from other channels when data allows.
3. Rebuild seasonal factors after each major season.
4. Do not blend full-year averages into peak-season forecasts for strongly seasonal items.
5. For new ASINs: start small, re-forecast after 60–90 days of real sales.
6. Always pass the chosen \( \hat{D} \) (and an uncertainty measure) into the restock calculator rather than jumping straight to a gut-feel quantity.

## Handoff to Restock Calculation

Minimum outputs to feed `calculate_restock.py` / safety-stock logic:

- `daily_sales` ← forecast mean demand per day for the planning horizon
- `std_demand` ← forecast error or historical daily σ
- Optional: seasonal coefficient or phase-specific cover target

Then apply the existing reorder-point, target-cover, H(Q), and L(Q) steps.

## What This Module Does Not Replace

- Judgment on promo calendar and competitive events
- Explicit capacity / MOQ / cash constraints
- Multi-warehouse or AWD allocation logic

Those remain planner overrides on top of the statistical baseline.
