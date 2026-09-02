# FBA Storage Fee Optimization, Holding Costs & Cash Flow

## Core Principle

Reduce storage cost and free cash by: **less volume, shorter age, avoid peak windows, and smarter cash timing**.

## 1. Control Inventory Age (Highest Priority)

Aged inventory surcharges start at different thresholds by marketplace (see fba-fees.md).

| Marketplace group      | Aged threshold | Action trigger |
|------------------------|----------------|----------------|
| US, CA, MX             | 181 days       | Review at ~150 days |
| UK, EU                 | 241 days       | Review at ~210 days |
| JP, AU, AE, SA         | 271 days       | Review at ~240 days |
| BR, SG, TR, EG         | 365 days       | Review at ~300 days |
| IN                     | ~150 days      | Review earlier |

**Actions:**
- Treat the marketplace aged threshold as a hard red line.
- Create removal or liquidation plans 30–45 days before the threshold.
- Enable automatic removal rules for low-velocity units past a set age.
- Removal fees are frequently cheaper than continued aged surcharges (especially 271+ / 366+ day tiers).

## 2. Avoid Q4 Peak Storage Rates

US standard-size example (2026):
- Jan–Sep: ~$0.78 / ft³
- Oct–Dec: ~$2.40 / ft³ (≈3×)

**Tactics:**
- Complete non-critical inbound before October when possible.
- Size peak-season shipments tightly to expected sell-through.
- Keep non-seasonal / staple SKUs at lean cover during Q4.
- Include peak storage cost in margin calculations for any units that may remain after the holiday window.

## 3. Reduce Volume Footprint

- Prefer higher-density products and tighter packaging.
- Ship multi-variant assortments in true sales ratios (avoid overstocking slow colors/sizes).
- Regularly clear stranded (no active listing) inventory — it still incurs storage fees.
- Review cubic volume of top storage-cost ASINs monthly.

## 4. Manage Storage Utilization Surcharge

When overall weeks of supply exceed ~22 weeks, additional utilization surcharges can apply.

**Targets:**
- Healthy overall network cover: roughly 8–12 weeks.
- Aggressively clear slow movers rather than letting them inflate the utilization ratio.
- Control first-purchase quantities on new ASINs.

## 5. Inventory Holding Cost

Holding cost is the full economic cost of keeping inventory, not just the FBA storage fee.

### Main components

| Component              | Description                                      | Typical annualized impact |
|------------------------|--------------------------------------------------|---------------------------|
| Cost of capital        | Opportunity cost or loan interest on inventory $ | 8–15%                     |
| FBA storage fees       | Monthly + peak storage                           | Volume & age dependent    |
| Aged inventory surcharges | Extra fees past marketplace thresholds        | Can dominate for slow stock |
| Shrinkage / obsolescence | Damage, expiry, forced removal, unsellable returns | 2–5%+                   |
| Insurance & handling   | Insurance, cycle counts, ops overhead            | 1–3%                      |

Many consumer goods land in a **20–35% annualized holding cost** range. Bulky or highly seasonal items often sit at the high end or above.

### Simple estimation

```
Monthly holding cost ≈ (Inventory value × monthly capital rate)
                       + storage fees
                       + aged surcharges (if any)
                       + expected shrinkage
```

**Suggested annualized holding-cost rates for planning:**

| SKU profile                    | Use rate   |
|--------------------------------|------------|
| High-turn, small cube          | 18–22%     |
| Standard                       | 25–30%     |
| Bulky or strongly seasonal     | 30–40%+    |
| Already in aged tiers          | >> 40%     |

Always compare continued holding cost against removal + residual value loss. If holding is more expensive, act.

## 6. Cash Flow, Payment Terms & Collection Cycle

Restock decisions should consider **when cash actually leaves and returns**, not only unit quantities.

### Typical Amazon cash cycle (simplified)

- Supplier payment terms (e.g. 30 days after ship) delay the cash outflow.
- Amazon remittance lag (commonly ~14 days after order) delays the cash inflow.
- Peak cash pressure often occurs shortly after the final supplier payment and before remittances ramp up.

### Batch / split inbound for capital efficiency

Prefer smaller, more frequent shipments when logistics allow:

| Approach          | Cash peak          | Aged risk          | Stockout risk      |
|-------------------|--------------------|--------------------|--------------------|
| Single large ship | High single outflow| All units age together | Lower             |
| Split shipments   | Lower peak outflow | Later batches stay younger | Slightly higher if second leg delays |

**Practical split logic (example):**
- First tranche: 60–70% of the target quantity, timed to arrive at the start of the need window.
- Second tranche: remainder, timed 2–4 weeks later.
- Result: lower single-day cash outflow, younger average inventory age, earlier start of remittance on the first tranche.

### Decision checks before locking a large PO

1. When is the real cash outflow (ship date + payment terms)?
2. When does remittance meaningfully start (arrival + sell-through + Amazon lag)?
3. What is the expected peak cash draw and how long until cumulative cash turns positive?
4. Does splitting the inbound reduce peak cash and aged exposure without creating an unacceptable stockout risk?

## 7. Inventory Turnover Improvement

Turnover = Period sales (or COGS) ÷ Average inventory.

Higher turnover → lower cash tied up + lower storage and aged risk.

### Source control (inbound)
- Calculate at FNSKU level, not just parent ASIN.
- Prefer smaller, more frequent shipments over large infrequent ones.
- Cap maximum days of cover (typically 45–60 days for most items).
- Keep new-product first orders small until velocity is proven.

### Sales acceleration
- Protect A-item availability (stockouts hurt rank and future velocity).
- Actively discount, coupon, or advertise slow movers before they age.
- Clear stranded inventory promptly.
- Align promotions with existing high-cover SKUs when sensible.

### Clearance discipline
- Weekly review of Inventory Age buckets.
- Pre-define age + velocity rules that trigger removal or liquidation.
- For seasonal items, start post-peak clearance 3–4 weeks before the season ends.

### Practical turnover targets (annualized)

| SKU type          | Healthy turnover | Approx. cover |
|-------------------|------------------|---------------|
| High-velocity     | 8–12×            | 30–45 days    |
| Standard          | 6–8×             | 45–60 days    |
| Seasonal          | High in peak, very low off-season | Keep off-season <30 days |
| Warning zone      | <4×              | Inventory likely too high |

## 8. Weekly / Monthly Monitoring Checklist

1. Inventory Age report — focus on 90 / 180 / 270 / 365 day bands
2. Monthly Storage Fees report — rank ASINs by storage cost contribution
3. Aged Inventory Surcharge report — units already being charged
4. Storage utilization / weeks of supply
5. Restock recommendations vs. your own safety-stock logic (avoid over-following system suggestions)
6. Cash timing: upcoming supplier payments vs. expected remittance ramp

## 9. Simple Decision Framework per SKU

Ask:
1. How many days of cover remain at current velocity?
2. Will continuing to hold push the unit into the next aged surcharge tier?
3. Is the expected storage + aged + capital cost already higher than removal cost + residual value loss?
4. Does the cash timing of this inbound create an unnecessary peak draw that could be smoothed by splitting?

If holding cost or cash peak is unfavorable, redesign quantity, timing, or split before shipping.

## 10. Long-Term Slow-Moving Inventory Optimization

Long-term stagnant inventory (low velocity, rising age) is one of the largest hidden profit drains in FBA. The goal is to **stop the bleeding early**: free cash and storage space while minimizing incremental loss.

### Classify severity

| Type | Characteristics | Priority action |
|------|-----------------|-----------------|
| Mild | Some daily sales, slow turn, age 90–150 days | Promote + block further inbound |
| Moderate | Very low velocity, near or past aged threshold | Aggressive promo + formal hold-vs-remove review |
| Severe | Almost no movement, already paying aged fees or approaching next tier | Prefer removal / liquidation |
| Dead stock | No traffic, no conversion, no listing value | Remove promptly, stop all spend |

### Priority actions (in order)

1. **Stop replenishment**
   - Remove from auto-restock and system recommendations
   - Tag in internal tools so it cannot be re-ordered by mistake

2. **Accelerate sell-through while the window remains**
   - Coupons, lightning deals, price cuts, bundles with healthy SKUs
   - Controlled advertising only if ACOS stays acceptable
   - Objective: reduce units before the next aged-fee step

3. **Run the hold-vs-remove economic test**
   - Compare expected future holding + aged cost + final liquidation loss
     versus immediate removal loss (unit cost + removal fee − residual)
   - If continued holding is more expensive, remove

4. **Structured clearance**
   - Process by age band first (closest to or past threshold)
   - Then by inventory value and cubic volume (high-value / high-cube first)
   - Batch Removal Orders to reduce operational overhead

5. **Prevent new stagnant stock**
   - Keep first orders on new ASINs small
   - Plan at FNSKU level, not only parent ASIN
   - Seasonal items must have a post-peak clearance plan
   - Monthly review of low-turnover SKUs

### Operating cadence

**Weekly**
- Review Inventory Age; flag units within ~30 days of the marketplace aged threshold (e.g. 150+ days for US)
- Apply promotions on mild cases

**Monthly**
- Quantify total value and storage-cost contribution of slow movers
- Complete hold-vs-remove calculations for moderate/severe items
- Execute removals or deep clearance

**Quarterly**
- Root-cause recurring stagnant SKUs (selection, pricing, seasonality miss)
- Adjust restock rules and safety-stock parameters

### Decision thresholds (practical)

| Signal | Suggested stance |
|--------|------------------|
| Within 30 days of aged threshold | Formal review required |
| Projected unsold share in remaining window > 30–40% | Lean toward aggressive promo or removal |
| Expected continuing hold cost > removal loss | Remove |
| Already paying high aged fees with near-zero velocity | Remove promptly to avoid higher tiers |

### Principle

Do not default to “wait and see.”  
Decide with data: **pay to push it out, or pay to clear it out.**  
Delay usually increases total holding and aged cost.
