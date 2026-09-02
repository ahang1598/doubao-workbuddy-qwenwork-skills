# Safety Stock & Reorder Point Guidance for Amazon FBA

## Core Formula (recommended)

```
Safety Stock = Z × √( LT_avg × σ_d² + D_avg² × σ_LT² )
```

Where:
- `Z` = service-level factor (Z-score)
- `LT_avg` = average lead time in days (PO placement → sellable in FBA)
- `σ_d` = standard deviation of daily demand
- `D_avg` = average daily demand (units)
- `σ_LT` = standard deviation of lead time in days

Reorder Point = (D_avg × LT_avg) + Safety Stock

## Common Z-scores (service level)

| Target Service Level | Z     |
|----------------------|-------|
| 90%                  | 1.28  |
| 95%                  | 1.65  |
| 97%                  | 1.88  |
| 98%                  | 2.05  |
| 99%                  | 2.33  |

## Recommended Service Levels by SKU Tier

- **A / Hero SKUs** (top ~15–20% of revenue, high velocity): 97–99% (Z 1.88–2.33). Stockouts destroy ranking and Buy Box share.
- **B / Mid-tier**: 95% (Z 1.65)
- **C / Long-tail or low-margin**: 90–93% (Z 1.28–1.48). Avoid tying up cash.

## Practical 2026 Days-of-Cover Targets

Given aged-inventory surcharges starting at 181 days (US) and low-inventory fees at the low end:

- Stable, predictable SKUs: **30–45 days** of cover (including safety stock)
- High-variability or long-lead-time SKUs: **45–60 days**
- Avoid routinely exceeding 60–70 days on most items unless demand is highly seasonal and you have a clear sell-through plan before 180 days.

## Simplified Heuristics (when full stats unavailable)

1. Safety stock ≈ 1.5–2.5 weeks of average daily sales for mid-tier.
2. Use 95th-percentile historical lead time instead of average if variability is high.
3. For new ASINs with little history: start with 45 days cover and tighten after 60–90 days of sales data.
4. Always calculate at FNSKU (variation) level when sizes/colors have different velocities.

## Seasonal Product Safety Stock Adjustments

Do **not** use full-year average demand for highly seasonal items. Adjust both demand inputs and target cover by phase.

### Phase-based cover targets

| Phase                        | Target cover (incl. safety stock) | Notes |
|-----------------------------|-----------------------------------|-------|
| Pre-peak (6–10 weeks before) | 60–90 days                       | Build for the entire peak window |
| During peak                 | Dynamic weekly review            | Recalculate remaining days of cover |
| Post-peak (first 2–4 weeks) | Quickly drop to 20–30 days       | Prevent aged inventory |
| Off-season                  | 15–30 days                       | Maintain base demand only |

### Seasonal coefficient method

```
Adjusted Safety Stock = Base Safety Stock × Seasonal Coefficient
```

| Timing                     | Suggested coefficient range |
|----------------------------|-----------------------------|
| 8–10 weeks before peak     | 1.8 – 2.5                  |
| 4–6 weeks before peak      | 1.5 – 2.0                  |
| During peak                | 1.2 – 1.5                  |
| 0–2 weeks after peak       | 0.6 – 0.8                  |
| Off-season                 | 0.5 – 0.7                  |

### How to calculate the seasonal coefficient

**Method 1 – Simple ratio (minimum data)**

```
Seasonal Coefficient = Peak-period average daily sales ÷ Full-year average daily sales
```

Example: Peak daily sales 19.6, full-year average 8.2 → coefficient ≈ 2.39.

**Method 2 – Robust ratio (recommended when data is noisy)**

- Use median or trimmed mean (drop top/bottom 10%) instead of simple average.
- Or use percentile form: Peak 75th-percentile daily sales ÷ Full-year 50th-percentile daily sales.

**Method 3 – Multi-year average**

```
Coefficient = (Avg peak sales Year1 + Year2 + Year3) / 3
              ÷ Overall multi-year average daily sales
```

Smooths single-year anomalies.

**Method 4 – Growth-adjusted**

```
Final Coefficient = Historical Coefficient × (1 + Expected Growth Rate)
```

Only apply growth when there is concrete evidence (ads plan, traffic forecast, etc.).

**Important**
- The coefficient multiplies the safety-stock component. Also replace \(D_{avg}\) in the reorder-point cycle stock with peak-period demand, otherwise total inventory will still be too low.
- Always check the resulting days of cover against the marketplace aged threshold (e.g. 181 days US).

### Classic time-series seasonal index (multi-year)

When 2–3+ years of monthly or weekly data are available, use the Ratio-to-Moving-Average method to extract a proper seasonal index.

**Steps (monthly data):**

1. Compute a 12-month centered moving average to estimate the trend \(T_t\).
2. Calculate the seasonal ratio for each period: \(Y_t / T_t\).
3. Average the ratios for the same month across all years → preliminary monthly indices.
4. Normalize so the 12 indices sum to 12 (average index = 1.0).

```
Final Seasonal Index_m = Preliminary Index_m × (12 / Σ Preliminary Indices)
```

**Usage with safety stock:**

- Adjusted daily demand = deseasonalized base demand × Seasonal Index for the target month(s).
- Or treat the average index of the peak months as the seasonal coefficient.

**Weekly data:** same logic with a 52-week moving average; produces 52 weekly indices. Higher precision but more data required.

**Practical notes:**
- Minimum 2 full years; 3 years preferred.
- Update the indices after every major season.
- For strong on/off seasonal items (near-zero off-season), it is often cleaner to recalculate the entire safety-stock formula using peak-window demand and σ rather than forcing a full-year base.

### Demand input rules for seasonal SKUs

- Pre-peak planning: use prior-year peak daily sales + expected growth, and the corresponding σ_d from the peak window.
- Off-season: switch to actual off-season daily sales and σ_d.
- Never blend full-year averages into peak safety-stock calculations.

### Hard constraints for seasonal items

- US aged threshold starts at 181 days — peak inventory received in October must normally be sold or removed by late March / early April.
- Prefer removal or aggressive liquidation over paying high aged surcharges.
- Factor Q4 peak storage rates into the margin model for any units expected to remain after the peak.

## Notes

- Lead time must include Amazon check-in / receiving time (often 3–14+ days depending on FC congestion and appointment).
- Demand should be Amazon channel only when possible (exclude other sales channels).
- Re-evaluate after major events (Prime Day, Q4, viral spikes, supply disruptions).
