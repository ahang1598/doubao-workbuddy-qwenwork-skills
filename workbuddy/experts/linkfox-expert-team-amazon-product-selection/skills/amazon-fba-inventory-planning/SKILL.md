---
name: amazon-fba-inventory-planning
description: Plan FBA restocks, safety stock, and inbound shipments for Amazon sellers. Use when the user mentions inventory planning, restock recommendations, FBA prep, overstock, stockouts, seasonal inventory, days of cover, reorder point, demand forecast, or cash tied up in inventory. Also trigger on requests for safety-stock calculation, inbound shipment plans, aged inventory risk, or “how much should I send to FBA this week”. Prefer automated data pull via available report skills (e.g. 亚马逊-店铺报表) when the user wants full automation.
---

# Amazon FBA Inventory Planning

## Overview

Produces weekly or monthly FBA restock plans that balance stockout risk (and low-inventory fees), aged-inventory surcharges, peak storage costs, and cash flow. Focuses on actionable unit quantities, shipment timing, and cash impact.

Supports two modes:
1. **Automated mode** (preferred): Pull live data via available report skills, then forecast and calculate.
2. **Manual mode**: User provides inventory/sales data or CSV.

## Instructions

### 0. Data Acquisition (Automated Mode)

When the user requests a restock plan without providing data (e.g. “帮我做美国站本周 FBA 补货计划”):

1. Check if a data-fetching skill is available (priority order):
   - **亚马逊-店铺报表** (LinkFox) — preferred for inventory, FBA, sales, aged inventory reports
   - Any other installed skill that can pull FBA Inventory, Inventory Age, Business Report, or Restock Inventory reports
   - Lingxing / other ERP OpenAPI skills if present

2. If a suitable skill is available and authorized:
   - Call it to fetch the latest relevant reports for the requested marketplace (default US).
   - Required / highly preferred reports:
     - FBA Inventory / 管理亚马逊物流库存
     - Inventory Age / 库龄报告 (or Aged Inventory)
     - Sales & Traffic / Business Report (for velocity)
     - Inbound / Restock Inventory (if available)
   - Extract key fields per ASIN/FNSKU:
     - Sellable quantity
     - Inbound quantity
     - Days of supply / inventory age buckets
     - Recent sales velocity (7/30-day preferred)
     - Volume / dimensions if available

3. Map pulled fields to the canonical contract in references/data-contract.md; apply COMPLETE/DEGRADED/BLOCKED degradation.
4. If no data skill is available or authorization fails:
   - Fall back to Manual mode and clearly ask the user for the required inputs.
   - Do not invent inventory or sales numbers.

### 1. Demand Forecast (before restock math)

For each FNSKU/ASIN, establish a planning demand rate \( \hat{D} \) and an uncertainty measure:

- Choose method by profile (see references/demand-forecasting.md):
  - Stable → moving average / single exponential smoothing
  - Trend → Holt
  - Strong seasonality → Holt-Winters or seasonal index (scripts/seasonal_index.py)
  - Intermittent / long-tail → Croston-style, Poisson-Gamma Bayesian, or conservative rule
  - Explicit uncertainty needed → Bayesian (scripts/forecast_bayesian.py)
  - New ASIN → analog + small test quantity; follow references/new-asin-ramp.md (TEST → LEARN → SCALE)
- Apply causal uplifts explicitly when ads, promos, or events matter (see references/promo-demand-lock.md for event multipliers, lock windows, and sellable deadlines).
- Horizon should cover lead time + review period (and peak window for seasonal builds).
- Pass `daily_sales` ≈ \( \hat{D} \) and `std_demand` (forecast error or historical σ) into the restock calculation.
- Do not skip straight to a gut-feel order quantity when history exists.
- For new ASINs still in TEST/LEARN, prefer capped test/top-up quantities over full mature safety-stock builds.

### 2. Collect required inputs for each FNSKU/ASIN

(Use data from steps 0–1 when available; otherwise ask user)

- Current sellable inventory + inbound (or estimated)
- Forecast daily demand + uncertainty (from step 1)
- Lead time in days (PO to sellable in FBA) and its variability — prefer lane P50/std from references/lead-time-decomposition.md, not a silent scalar
- Unit dimensions / cubic feet (or weight + size tier)
- Target service level or days-of-cover preference
- Marketplace (default US)
- Optional economics: unit cost, net price, expected sell-through (for H(Q) / L(Q))

### 3. Calculate key metrics

- Days of cover = current inventory ÷ forecast daily demand
- Reorder point = (forecast daily demand × lead time) + safety stock
- Recommended order quantity = target cover − current − inbound, then apply supplier constraints (MOQ / multiple / max; see references/supplier-constraints.md)
- Flag items already or soon to hit aged inventory surcharge thresholds:
  - US, CA & MX ≈ 181+ days
  - UK & EU ≈ 241+ days
  - JP, AU, AE & SA ≈ 271+ days
  - IN ≈ 5 months (≈150+ days)
  - BR, SG, TR & EG ≈ 365+ days
- When cost inputs exist, estimate H(Q) holding cost and L(Q) expected unsold/liquidation loss; surface expected net profit and risk flags.
- Cap FBA inbound by IPI/storage/restock headroom (references/ipi-capacity-limits.md).
- Use sellable inventory only for cover; route returns/unfulfillable via references/returns-reverse-logistics.md.
- Explode kits through BOM before publishing ATP or buying components (references/kits-bom-inventory.md).

### 4. Apply 2026 fee awareness (see references/fba-fees.md)

- Prefer more frequent smaller shipments over aging past the marketplace threshold
- Avoid Q4 peak storage when possible by timing inbound for Jan–Sep
- Watch storage utilization surcharge (weeks of supply > 22) where applicable
- Note low-inventory-level fee risk if days of cover drops too low (mainly US)
- Use correct volume unit (cu ft / m³ / liters / dm³) and local currency for cash impact

### 5. Destination allocation (FBA / AWD / hub)

After total quantity is set, choose **where** units should go (see references/multi-warehouse.md):

- Default stockout / lean Priority A → **FBA 100%**
- Bulk pre-peak or high-cube builds → keep FBA at policy cover (e.g. 30–45d), park remainder in **AWD or hub** (SPLIT)
- Post-peak / weak LEARN / aged risk → avoid adding FBA; upstream only or no inbound
- New ASIN TEST → **FBA only** (need Amazon velocity signal)

Record `destination`, `qty_fba`, `qty_upstream` on the plan.

When the SKU also sells outside Amazon (DTC, TikTok, eBay, wholesale, etc.), apply **multi-channel shared inventory** rules (references/multi-channel-inventory.md):

- Compute ATP = on-hand − commitments − reserves − quality hold − FBA-dedicated
- Treat FBA as a **static ring-fence**; shared pool is for hub/local/MFN/other channels only
- Publish channel qty with buffers (Amazon MFN often 10–15% holdback)
- Replenish hub from **combined** non-FBA demand; do not blindly follow Amazon restock tips for shared SKUs

### 5b. Ads–inventory linkage check

When ad status or spend is available, classify cover vs ads (see references/ads-inventory-linkage.md):

- **A Ads high / Cover low** → prioritize FBA inbound; flag ads throttle until ETA
- **B Cover high / Ads low** → no restock; promo/ads or hold_vs_remove
- **C Both high** → freeze extra inbound unless peak justifies it
- **D Both low** → relaunch deliberately or exit

Record `ads_inventory_pattern` and a short `ads_action_note` on the plan when relevant.

### 5c. Exception priority queue

Score and rank SKUs for action (see references/exception-priority.md; scripts/priority_score.py):

- Assign exception codes (E1 stockout, E2 aged, E3/E4 ads mismatch, …)
- Compute priority_score (0–100) and severity S1–S4
- Sort queue by score; attach one next_action per SKU
- Daily: clear S1–S2; Weekly: full S1–S4 in the published plan

### 6. Output a clear plan per SKU

- Forecast daily demand used (and method)
- Recommended units to ship now (total + by destination)
- Suggested inbound date / week
- Expected days of cover after arrival (FBA-facing)
- Age risk (OK / WATCH / CRITICAL) and hold_vs_remove when near threshold
- Estimated monthly storage + aged surcharge exposure
- Cash impact (units × unit cost)
- Optional: H(Q), L(Q), expected net profit
- Priority rank (A-items / high velocity first)

For multi-SKU deliverables, use the column structure in `assets/weekly-plan-template.csv` and the narrative order in `assets/weekly-plan-output-guide.md`.

### 7. Multi-SKU / Portfolio

Group by urgency (stockout risk > aged risk > normal restock > dead-stock removal) and summarize total cash required. Lead with an executive summary: SKU counts by action, total units, total cash, top risks, and destination mix (FBA vs upstream).

### 8. Incomplete data (data contract)

Follow references/data-contract.md:

- Classify each SKU **COMPLETE / DEGRADED / BLOCKED**
- BLOCKED (no sellable or no demand signal): do not recommend a firm PO
- DEGRADED: run allowed subset only; print named defaults (LT, inbound=0, economics skipped, capacity uncapped, etc.)
- Never invent sellable qty or velocity
- Prefer Amazon reports for FBA sellable/age; WMS for hub ATP; log conflicts

## Resources

- references/demand-forecasting.md — model selection, methods, metrics, and handoff to restock math
- references/data-contract.md — report field contract, missing-data degradation, conflicts
- references/lead-time-decomposition.md — LT legs, variance shares, P50/P90, σ_LT monitoring
- references/new-asin-ramp.md — new ASIN test → learn → scale inventory rules
- references/supplier-constraints.md — MOQ, order multiples, max qty, lead-time constraints
- references/multi-warehouse.md — FBA vs AWD vs hub allocation and split rules
- references/multi-channel-inventory.md — shared pool, ATP, channel buffers, FBA ring-fence, multi-platform
- references/inventory-reservation.md — reservation state machine, TTL, idempotent ledger
- references/inventory-concurrency.md — high-concurrency atomic deduct, buckets, rate limits
- references/returns-reverse-logistics.md — returns grading, unfulfillable, impact on cover/ATP
- references/ipi-capacity-limits.md — IPI bands, storage/restock capacity caps on FBA qty
- references/kits-bom-inventory.md — kit/bundle BOM, max buildable, component restock
- references/promo-demand-lock.md — event uplift, inventory lock windows, ads/capacity alignment
- references/ads-inventory-lock-linkage.md — ads↔inventory dual gates during lock/event windows
- references/ads-inventory-linkage.md — ads vs cover mismatch patterns and planner actions
- references/exception-priority.md — exception codes, severity, priority scoring, action queue
- references/fba-fees.md — 2026 storage, aged, utilization and peak rates for US, UK, EU, CA, JP, AU, MX, IN, AE, BR, SG, SA, TR and EG
- references/safety-stock.md — formulas, Z-scores, service-level guidance, and seasonal safety-stock adjustments
- references/seasonal-calendar.md — Q4 peak windows and typical category seasonality
- references/storage-optimization.md — storage fee reduction, holding cost, cash timing, turnover, slow-moving clearance
- scripts/forecast_demand.py — moving average / weighted MA / exponential smoothing → daily demand + std
- scripts/forecast_bayesian.py — Poisson-Gamma and Bayesian ES demand forecasts with posterior uncertainty
- scripts/calculate_restock.py — safety stock, reorder point, H(Q), L(Q), expected profit
- scripts/hold_vs_remove.py — near-threshold hold vs remove economic decision
- scripts/priority_score.py — exception priority score 0–100 + severity
- scripts/atp_calculate.py — ATP from on-hand/holds/FBA ring-fence + channel publish buffers
- scripts/seasonal_index.py — Ratio-to-Moving-Average seasonal index (monthly / weekly) + peak coefficient
- assets/restock-template.csv — simple input/output template
- assets/weekly-plan-template.csv — SKU-level weekly plan columns (forecast → qty → age risk → cash)
- assets/weekly-plan-output-guide.md — how to structure the planner deliverable

## Integration Notes

This skill is designed to consume structured output from report-pulling skills (especially LinkFox 亚马逊-店铺报表).  
When those skills return inventory + sales data, treat them as the primary source of truth, run the demand-forecast step, then proceed to restock calculation.  
Do not ask the user for data that has already been successfully retrieved.
