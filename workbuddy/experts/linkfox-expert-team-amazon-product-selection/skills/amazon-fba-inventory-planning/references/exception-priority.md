# Exception Alerts & Priority Scoring (FBA Planner)

Turn multi-signal inventory health into a **daily/weekly action queue**.  
Goal: the planner opens one ranked list, not ten raw reports.

## Exception Types

| Code | Exception | Typical trigger |
|------|-----------|-----------------|
| E1 | Stockout risk | Days of cover < policy minimum (e.g. < 21–28) |
| E2 | Aged risk | Age within 30 days of marketplace threshold, or already in surcharge band |
| E3 | Ads–inventory mismatch A | Ads high + cover low |
| E4 | Ads–inventory mismatch B | Cover high + ads low / off |
| E5 | Overstock / utilization | Cover ≫ policy or account weeks-of-supply pressure |
| E6 | Inbound late / pipeline gap | Needed ETA misses lead-time stack |
| E7 | New ASIN test fail | TEST/LEARN kill signals |
| E8 | Constraint block | Q* > 0 but deferred by MOQ economics |
| E9 | Data quality | Missing velocity, age, or cost inputs for a key SKU |

A SKU may carry multiple exception codes; the **highest severity** drives rank.

## Severity Levels

| Level | Meaning | Response expectation |
|-------|---------|----------------------|
| **S1 Critical** | Imminent stockout on A-item, or aged fees already severe | Same-day action |
| **S2 High** | Cover low with ads on, or threshold < 30 days | Within 1–2 business days |
| **S3 Medium** | Overstock, mismatch B, MOQ deferral | This week |
| **S4 Low** | Watch-list, data gaps on C-items | Batch in weekly review |

## Priority Score (simple, transparent)

Use a 0–100 score; higher = act first.

```
score = 0
score += stockout_component      # 0–40
score += aged_component          # 0–25
score += ads_mismatch_component  # 0–15
score += revenue_tier_component  # 0–15  (A=15, B=8, C=3)
score += overstock_component     # 0–5   (only if not already stockout)
```

### Suggested component rubrics

**Stockout (0–40)**  
- Cover < 7d → 40  
- Cover < 14d → 30  
- Cover < 21d → 20  
- Cover < 28d → 10  
- Else → 0  

**Aged (0–25)**  
- Already in surcharge / CRITICAL → 25  
- Within 14 days of threshold → 20  
- Within 30 days → 12  
- WATCH only → 5  

**Ads mismatch (0–15)**  
- Pattern A (ads high, cover low) → 15  
- Pattern B (cover high, ads low) → 8  
- Pattern C problematic off-peak → 5  
- Else → 0  

**Revenue tier (0–15)**  
- A / Hero → 15  
- B → 8  
- C → 3  

**Overstock (0–5)**  
- Cover > 2× policy → 5  
- Cover > 1.5× policy → 3  

Clamp total to 100.  
Sort queue by score DESC, then by forecast_daily DESC as tie-breaker.

## Action Mapping (default)

| Top exception | Default next action |
|---------------|---------------------|
| E1 + S1/S2 | Expedite FBA inbound; destination FBA; notify ads if Pattern A |
| E2 | Run hold_vs_remove; promo or removal |
| E3 | Restock FBA + ads throttle note |
| E4 | No restock; ads/promo or clearance |
| E5 | Freeze inbound; consider upstream only / clearance |
| E6 | Re-plan ETA; split or air option |
| E7 | Kill ramp; no further PO |
| E8 | Negotiate MOQ / combine / defer explicitly |
| E9 | Fix data before ordering |

## Daily / Weekly Cadence

**Daily (30 min)**  
1. Refresh inventory + age + sales  
2. Recompute cover + exception codes + scores  
3. Work S1 then S2 only  

**Weekly (plan meeting)**  
1. Full queue S1–S4  
2. Confirm POs, destinations, removals  
3. Publish weekly plan CSV + executive summary  

## Weekly Plan Fields

| Column | Meaning |
|--------|---------|
| exception_codes | e.g. E1\|E3 |
| severity | S1–S4 |
| priority_score | 0–100 |
| next_action | One-line action |

## Worked Example (illustrative)

| SKU | Cover | Age risk | Ads pattern | Tier | Score (approx) | Queue |
|-----|-------|----------|-------------|------|----------------|-------|
| Cable | 12d | OK | A | A | ~30+15+15 ≈ 60 | Restock FBA first |
| Fan-02 | 52d | WATCH | B | B | ~12+8+8 ≈ 28 | Promo / hold_vs_remove |
| Dead | 2500d | CRITICAL | B | C | ~25+8+3 ≈ 36 | Remove |
| New test | n/a | OK | D | B | low | Keep test discipline |

## Principle

> Exceptions without ranking create noise.  
> Ranking without actions creates reports.  
> Score → queue → **one clear next action** per SKU.
