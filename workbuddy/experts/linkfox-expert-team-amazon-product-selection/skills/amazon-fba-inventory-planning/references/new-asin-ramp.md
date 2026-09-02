# New ASIN Cold-Start & Ramp Rules (FBA)

New products lack stable demand history. Treat them as a **test → learn → scale** loop, not as mature SKUs with full safety-stock math.

## Phases

| Phase | Typical window | Goal | Inventory stance |
|-------|----------------|------|------------------|
| 0. Prep | Before first inbound | Listing, main image, basic backend ready | Do not over-order |
| 1. Test | First 14–30 days after sellable | Validate conversion & velocity signal | **Small first shipment only** |
| 2. Learn | Days 30–60/90 | Stabilize forecast, ad efficiency, return rate | Moderate top-up if signal is healthy |
| 3. Scale | After reliable 60–90 days history | Apply normal forecast + safety stock | Full restock logic |
| 4. Kill / pause | Any time signal fails | Stop cash burn | No further inbound; clear remainder |

## Phase 1 — Test Quantity

**First inbound quantity (units):**

```
Q_test = max( MOQ_constraint,  D_analog × cover_test × uncertainty_factor )
```

Practical defaults when no better analog exists:

| Product type | Suggested first cover | Notes |
|--------------|----------------------|-------|
| Low-price consumable / accessory | 20–30 days of *expected* daily sales | Cap absolute units if uncertain |
| Mid-ticket standard | 25–40 days | Watch returns |
| Bulky / high-cost | 15–25 days | Cash & storage sensitive |
| Strong seasonal (off-season launch) | Minimal test only | Avoid building peak inventory early |

**Uncertainty factor:** 0.5–0.8 for weak analogs; 1.0 only when analog is very close (same category, price, audience).

**Hard caps (recommended):**
- Do not ship more than **1.0–1.5×** the cash you are willing to lose on a failed test
- Prefer one small shipment over “test quantity that is already a full scale buy”

## Phase 2 — Learn (top-up rules)

After 14–30 days of real sales, re-estimate daily demand from **Amazon-channel only** data.

**Healthy signal (examples — tune to your category):**
- Stable or rising sessions → conversion
- Returns within category norms
- Ad ACOS acceptable relative to margin
- No critical listing / compliance issues

If healthy:

```
Q_topup = D_hat_recent × target_cover_learn − current − inbound
```

Suggested `target_cover_learn`: **30–45 days** (still tighter than mature A-items).

If mixed / weak signal:
- Top-up only to avoid stockout on proven residual demand
- Or hold and improve listing/ads before more inventory

## Phase 3 — Scale (graduate to normal planning)

Graduate when **most** of these are true:

- ≥ 60 days of sellable history (90 better for seasonal)
- Forecast method can be chosen with residual error measured
- Velocity not driven only by one short promo spike
- Returns and quality stable

Then:
- Use full demand-forecast module (including Bayesian / seasonal as appropriate)
- Apply normal safety stock, H(Q), L(Q), aged-risk checks
- Raise service level toward tier policy (A/B/C)

## Kill / Pause Triggers (stop inbound)

- Conversion far below analog / category after adequate traffic
- Returns or defects elevated
- ACOS persistently destroys contribution margin
- Inventory age trending toward threshold with no velocity recovery
- Strategic kill (portfolio, compliance, supply)

Action: **no further restock**; run hold_vs_remove / clearance playbook.

## Analog Selection (for Phase 1)

Prefer analogs that match:
1. Category / subcategory  
2. Price band  
3. Variation structure (size/color complexity)  
4. Seasonality pattern  
5. Fulfillment size tier (storage cost profile)

Document the analog ASIN and why it was chosen in the plan notes.

## Interaction with Other Skill Modules

| Module | How new ASINs use it |
|--------|----------------------|
| demand-forecasting | Phase 1–2: analog or short MA/EWMA; Phase 3: full methods |
| safety-stock | Phase 1: light or none; Phase 3: full Z-based SS |
| storage-optimization | Always enforce aged threshold; bulky tests stay small |
| hold_vs_remove | Use early if test stock stalls near threshold |
| weekly plan template | Tag phase in `notes` (TEST / LEARN / SCALE / KILL) |

## Planner Checklist (new ASIN)

1. Confirm listing readiness before first inbound  
2. Set test budget (max cash at risk)  
3. Choose analog → compute Q_test (respect MOQ)  
4. Review at day 14 and day 30 with real velocity  
5. Top-up only on healthy signal  
6. Graduate to normal restock only after history threshold  
7. Kill fast when signals fail — do not “wait one more shipment”

## Principle

> New ASIN inventory is an **experiment cost**, not a service-level commitment.  
> Earn the right to scale with data; do not grant full safety stock on day one.
