# Data Contract & Missing-Data Degradation

Defines **what fields the planning pipeline expects**, where they usually come from, and **what to do when data is missing, late, or conflicting** — so automation does not invent numbers or silently over-order.

## 1. Field contract (canonical planning inputs)

| Field | Required? | Typical source | Used by |
|-------|-----------|----------------|---------|
| marketplace | Yes | User / report scope | Fees, aged threshold |
| sku / fnsku / asin | Yes | Inventory report | All |
| sellable_qty | Yes | FBA Inventory / Manage Inventory | Cover, Q |
| inbound_qty | Soft | Inventory / Restock / Shipments | Pipeline |
| sales_7d / 30d (or daily series) | Yes for forecast | Business Report / Sales & Traffic | \(\hat{D}\), σ |
| inventory_age_band or oldest_age | Soft | Inventory Age / Aged Inventory | Age risk, hold_vs_remove |
| unit_cube or size_tier | Soft | Inventory / catalog | Storage $ |
| lead_time_days | Soft (default allowed) | Planner config / supplier | ROP, SS |
| std_lead | Optional | History | SS |
| unit_cost | Optional | Cost sheet / ERP | H(Q), cash, hold_vs_remove |
| net_price | Optional | Fee estimate / settlement | L(Q), profit |
| capacity_headroom | Optional | Capacity monitor | FBA qty cap |
| asin_restock_headroom | Optional | Restock limits | FBA qty cap |
| ads_status / spend | Optional | Ads console | Pattern A–D |
| moq / multiple | Optional | Supplier | Qty adjust |

**Yes** = do not compute a firm PO without it (or explicit override).  
**Soft** = may default with a stated assumption.  
**Optional** = feature degrades (no economics / no capacity cap / no ads pattern).

## 2. Report → field mapping (LinkFox / Seller Central style)

Use as a checklist when wiring report skills; column names vary by locale.

| Planning field | Prefer report | Fallback |
|----------------|---------------|----------|
| sellable_qty | FBA Inventory (sellable) | Manage Inventory “Available” |
| inbound_qty | Inbound working+shipped | Restock Inventory inbound |
| velocity | Business Report units ordered (Amazon fulfilled) by day/week | 30-day units / 30 |
| age | Inventory Age snapshot | Aged Inventory surcharge report |
| stranded | Stranded Inventory | Listing health |
| capacity | Capacity monitor | Manual planner input |
| restock limit | Restock recommendations / limits UI | Manual |

If multiple sources disagree: **prefer WMS/ERP for hub stock; prefer Amazon reports for FBA sellable/age; prefer explicit planner override last-write-wins with log.**

## 3. Degradation matrix (missing data)

| Missing | Allowed action | Forbidden | Message pattern |
|---------|----------------|-----------|-----------------|
| sellable_qty | Ask user / stop SKU | Invent stock | “No sellable qty — blocked” |
| all velocity | Use analog only for TEST phase; else stop | Fake 30-day sales | “No demand signal — blocked” |
| short history | MA/EWMA with wide σ; lower service optional | Full seasonal index claim | “Thin history — high uncertainty” |
| inbound_qty | Assume 0 + flag | Assume “enough inbound” | “Inbound unknown — treated as 0” |
| age | Skip hold_vs_remove auto; still allow restock with warning | Ignore aged fees | “Age unknown — no remove decision” |
| lead_time | Default from marketplace profile (e.g. 35–45) + flag | Silent 0 LT | “LT defaulted to X” |
| unit_cost / net_price | Qty only; skip H/L/profit | Fake margins | “Economics skipped” |
| capacity / restock headroom | Qty without Amazon cap + warn | Assume infinite capacity | “No capacity input — uncapped” |
| ads_status | Pattern n/a | Assume ads OFF or ON | “Ads pattern skipped” |
| moq | No raise/defer logic | — | “MOQ not applied” |

## 4. Conflict rules

| Conflict | Resolution |
|----------|------------|
| Report sellable ≠ WMS for same pool | For **FBA cover** use Amazon sellable; for **hub ATP** use WMS |
| Restock recommendation ≫ internal Q* | Prefer internal Q*; log Amazon suggestion as reference only |
| Parent ASIN velocity vs FNSKU | Plan at FNSKU when variation velocity differs |
| Stale report (older than policy, e.g. >48h for daily plan) | Refresh or mark S4/E9 data quality; no S1 ship decision on stale stockout alone without confirm |

## 5. Pipeline behavior

```text
1. Bind fields per contract
2. For each SKU classify: COMPLETE | DEGRADED | BLOCKED
3. COMPLETE → full forecast → restock → capacity → destination → ads → score
4. DEGRADED → run allowed subset; list assumptions in notes
5. BLOCKED → no recommended_qty; exception E9; ask for data
```

Never fill BLOCKED gaps with silent zeros unless the matrix explicitly says “treat as 0” (e.g. inbound).

## 6. Defaults (only when Soft and stated)

| Field | Example default | Must print |
|-------|-----------------|------------|
| lead_time_days | 40 (US sea+FC, planner-specific) | Yes |
| service level | 0.95 | Yes |
| inbound_qty | 0 | Yes |
| holding_rate | 0.28 | If economics run |
| target_cover | Policy by tier/phase | Yes |

Document defaults in weekly plan `notes`.

## 7. Automation integration notes

When a report skill returns data:

1. Map to canonical fields (this contract)  
2. Validate types and non-negative qty  
3. Apply degradation matrix  
4. Only then call forecast / calculate_restock / hold_vs_remove  

If report skill fails auth: entire run is Manual mode — **do not invent inventory.**

## 8. Principle

> **No silent fiction.**  
> Missing data either blocks the SKU, or continues under **named** assumptions with degraded features — never a confident PO from empty velocity or empty sellable.
