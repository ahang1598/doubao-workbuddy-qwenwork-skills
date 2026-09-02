# Weekly FBA Inventory Plan — Output Guide

Use this structure when delivering a weekly (or ad-hoc) restock plan to ops / finance.

## 1. Executive Summary (top of report)

- Marketplace(s) covered
- SKU count reviewed / action count (restock / hold / remove)
- Total recommended inbound units
- Total cash required for recommended shipments
- Top risks: stockout SKUs, aged-threshold SKUs, utilization pressure

## 2. SKU-Level Plan Table

Fill one row per FNSKU (preferred) or ASIN.  
CSV template: `assets/weekly-plan-template.csv`

| Column | Meaning |
|--------|---------|
| marketplace | e.g. US, UK, DE, JP |
| sku / fnsku / asin / title | Identity |
| forecast_daily | Planning demand rate \( \hat{D} \) |
| forecast_method | ma / ewma / seasonal_index / poisson_gamma / bayes-es / etc. |
| std_demand | Uncertainty passed into safety stock |
| service_level | Target service level used |
| current_sellable | FBA sellable on hand |
| inbound | Units already inbound |
| days_of_cover | current_sellable ÷ forecast_daily (or +inbound if you define that way — state it) |
| lead_time_days | PO → sellable |
| target_cover_days | Policy cover target for this SKU/phase |
| recommended_qty | Total units to ship this cycle (after MOQ/multiple) |
| destination | FBA / AWD / HUB / SPLIT |
| qty_fba | Units bound for FBA |
| qty_upstream | Units to AWD or local/overseas hub |
| fba_cover_target_days | FBA node policy cover used for split |
| suggested_inbound_week | Target arrival week |
| age_bucket_days | Representative inventory age (or oldest meaningful band) |
| aged_threshold_days | Marketplace threshold (181 US, 241 UK/EU, …) |
| age_risk | OK / WATCH / CRITICAL |
| hold_vs_remove | n/a / HOLD / REMOVE (from hold_vs_remove.py when near threshold) |
| ads_status | OFF / LOW / ON / HIGH |
| cover_class | LOW / OK / HIGH |
| ads_inventory_pattern | A / B / C / D / n/a |
| ads_action_note | Planner note for ads coordination |
| unit_cost | Cost incl. inbound freight |
| net_price | Net proceeds after Amazon fees |
| cash_impact | recommended_qty × unit_cost |
| holding_cost_est | H(Q) if computed |
| unsold_loss_est | L(Q) if computed |
| expected_net_profit | π(Q) if computed |
| priority | A / B / C (velocity & strategic importance) |
| notes | Phase, promo, supplier constraint, etc. |

## 3. Recommended Section Order in a Written Plan

1. **Stockout risk (Priority A, low cover)** — ship first  
2. **Aged / near-threshold** — HOLD vs REMOVE decisions  
3. **Normal restock** — remaining positive recommended_qty  
4. **No action** — healthy cover, no age risk  
5. **Cash & capacity summary** — total cash, optional split-inbound proposal  

## 4. Urgency Ranking Rule (default)

1. Stockout risk (days of cover below policy minimum)  
2. Aged risk (WATCH / CRITICAL)  
3. Normal restock by forecast velocity / margin  
4. Dead stock clearance (REMOVE) as a separate workstream  

## 5. Example One-Line SKU Conclusion

> **SKU-FAN-01 (US)** — Forecast 93/day (seasonal). Cover 23d. Recommend **4,330 units** to arrive W18. Cash ~$77.9k. Age OK. Priority A. Pre-peak build for Jun–Aug.

## 6. Tooling Chain (inside this skill)

```
forecast_demand.py / forecast_bayesian.py / seasonal_index.py
        → daily_sales, std_demand
calculate_restock.py
        → recommended_qty, H(Q), L(Q), profit
multi-warehouse rules (references/multi-warehouse.md)
        → destination, qty_fba, qty_upstream
hold_vs_remove.py   (when near aged threshold)
        → HOLD / REMOVE
Fill weekly-plan-template.csv → deliver
```

## 7. Notes for Planners

- Always state assumptions (forecast method, sell-through, lead time).
- For seasonal SKUs, state which phase target cover was used.
- Cash impact is purchase cash, not Amazon remittance timing.
- Split large recommended_qty when payment terms / cash peak require it (see storage-optimization.md).
