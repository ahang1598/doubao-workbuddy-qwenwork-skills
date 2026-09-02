# Ads–Inventory Linkage for FBA Planners

Advertising and inventory must move together.  
Pushing ads into low cover creates stockouts and wasted spend; heavy inventory with no ad support creates aged stock and holding cost.

This module is a **planner-side diagnostic**, not a full PPC optimization playbook.

## Core Mismatch Patterns

| Pattern | Signal | Risk | Planner action |
|---------|--------|------|----------------|
| **A. Ads high / Cover low** | Strong ad spend or high ACOS campaigns while days of cover ≪ policy | Stockout, lost rank, wasted ad $ | Prioritize inbound; optionally ask ads to pause/throttle until ETA |
| **B. Cover high / Ads low** | Healthy or excess cover, weak or zero ad support | Slow sell-through, aged fees | Do not restock; trigger promo/ads or hold_vs_remove |
| **C. Ads high / Cover high** | Both elevated | May be fine in peak; off-peak can mean oversell risk + overstock | Check sell-through vs aged window; freeze further inbound |
| **D. Ads low / Cover low** | Both weak | Either intentional harvest or neglected SKU | Decide: invest (ads + stock) or exit |

## Practical Thresholds (tune by account)

Use as starting points, not laws:

| Metric | “Low” | “Healthy” | “High” |
|--------|-------|-----------|--------|
| FBA days of cover | < 21–28 | 30–45 (stable) | > 60 (or > policy) |
| Ad intensity | Near-zero spend / no share of voice | Spend aligned with margin plan | Spend spiking while cover falling |
| ACOS / TACOS | — | Within target band | Persistently above break-even |

Define ad intensity with whatever you have: 7-day ad spend, ad-attributed units, or “campaign active Y/N”.

## Diagnostic Flow

```
1. Compute days_of_cover (FBA sellable ÷ forecast daily)
2. Classify cover: LOW / OK / HIGH
3. Classify ads: OFF-LOW / ON-OK / ON-HIGH  (from spend or status)
4. Map to pattern A–D
5. Attach action to weekly plan notes + priority
```

### Pattern A — Ads high / Cover low

1. Raise restock priority to **A**  
2. Shorten inbound path (air / express if margin allows)  
3. Destination: **FBA first** (not upstream)  
4. Flag ads owner: throttle or shift spend to in-stock ASINs until cover recovers  
5. Recheck daily until cover ≥ minimum policy  

### Pattern B — Cover high / Ads low

1. **No restock** (recommended_qty = 0)  
2. Request ads/promo support **or** start clearance path  
3. If near aged threshold → run `hold_vs_remove.py`  
4. Priority: aged risk first, then cash recovery  

### Pattern C — Both high

1. Confirm whether peak demand justifies it  
2. If off-peak: freeze inbound; consider upstream only for already-committed supply  
3. Align ads with sell-through plan so stock clears before aged threshold  

### Pattern D — Both low

1. Strategic choice: relaunch (test ads + small FBA stock) or exit  
2. New ASIN TEST phase is allowed only with explicit test budget  
3. Do not “quietly” rebuild FBA stock without a demand plan  

## Fields for Weekly Plan

Add when data available:

| Column | Values / meaning |
|--------|------------------|
| ads_status | OFF / LOW / ON / HIGH |
| cover_class | LOW / OK / HIGH |
| ads_inventory_pattern | A / B / C / D / n/a |
| ads_action_note | e.g. “throttle SP until W18 ETA” |

## Handoff Rules (Planner ↔ Ads)

- Planner owns: cover policy, inbound priority, aged decisions  
- Ads owns: bid/budget/creative  
- Shared: **do not scale spend into projected stockout window**; **do not leave high-cover SKUs dark without a clearance plan**

Minimum joint SLA idea:
- If cover < 14 days and ads ON-HIGH → joint review same day  
- If cover > 60 days and ads OFF → clearance or ads plan within a week  

## Link to Other Modules

| Module | Interaction |
|--------|-------------|
| demand-forecasting | Ad uplift belongs in causal layer; do not double-count |
| calculate_restock | Pattern A increases urgency / target cover temporarily |
| multi-warehouse | Pattern A → FBA only; Pattern B → no FBA inbound |
| hold_vs_remove | Pattern B + near threshold → economic remove test |
| new-asin-ramp | TEST needs controlled ads + small FBA stock together |

## Principle

> Inventory without demand push ages.  
> Demand push without inventory burns cash and rank.  
> Plan the **pair**, not each metric alone.
