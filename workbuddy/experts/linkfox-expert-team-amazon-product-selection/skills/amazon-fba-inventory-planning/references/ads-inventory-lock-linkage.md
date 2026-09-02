# Ads ↔ Inventory Lock Linkage (双向门闩)

Advertising can scale in hours; inventory moves in weeks.  
**Lock** creates committed supply for an event; **ads gates** prevent buying demand the network cannot fulfill.

This extends `promo-demand-lock.md` and `ads-inventory-linkage.md`.

## 1. Objective

\[
\text{Sellable cover during event} \geq \text{Demand implied by ads + price + event uplift}
\]

Non-event channels must not freely consume reserved units during the lock window.

## 2. Core objects

| Object | Symbol | Role |
|--------|--------|------|
| Baseline demand | \(\hat{D}_{base}\) | Normal forecast |
| Combined uplift | \(U\) | Event × ads × price × halo |
| Event demand | \(\hat{D}_{evt}=\hat{D}_{base}\times U\) | Planning demand in window |
| Reserve qty | \(R\) | Hard lock subtracted from ATP |
| Ad spend plan | \(C_{ads}\) | Only fully released if cover gates pass |

Suggested reserve:

```text
R ≈ D̂_evt × lock_days + SS_evt
```

Cap \(R\) by capacity, aged risk, and cash. Always keep low/base/high scenarios.

## 3. Dual gate rules

### Gate A — Inventory gates ads

```text
if projected_sellable_cover < policy_min_for_event:
    throttle or pause scale-up of C_ads
if inbound_eta > sellable_deadline:
    block main budget release
if reserve_shortfall and no expedite path:
    reduce U_ads / U_price targets (don’t “hope” stock in)
```

### Gate B — Ads plan gates lock size

```text
if event ads cancelled or budget cut sharply:
    reduce R or unlock early (avoid false shortage)
if ads only funds a smaller SKU set:
    lock only that set; don’t freeze the whole catalog
```

Both directions are mandatory. One-way linkage fails in practice.

## 4. Business state machine

| Phase | Inventory | Ads | Linkage rule |
|-------|-----------|-----|--------------|
| T−60~T−30 Plan | Scenario R, capacity check | Draft budget | Budget ≤ supply scenarios |
| T−30~T−14 Inbound | Hit sellable_deadline | Creative ready, test only | ETA slip → cut pre-commit spend |
| T−14~T−7 Confirm | Write reserves into ATP | Soft launch optional | No reserve ⇒ no main push |
| Lock | Hard R; lower other-channel publish | Ramp within cover | Cover breach ⇒ throttle |
| Event | Real-time cover monitor | Spend vs remaining cover | Pattern A ⇒ prioritize stock / cut ads |
| Unlock | Release unused R | Event campaigns off | Leftover → normal or clearance path |

## 5. How lock serves ads

1. **Hard reserve \(R\)** in shared-pool ATP (`reserves` in ATP formula)  
2. **Priority** event channel consumes R first  
3. **Buffers** still apply on published qty; lock is not a reason to show 100% of physical  
4. **FBA events** require *sellable* FBA units by deadline — hub on-hand alone is not enough  

## 6. How ads constrain lock

| Ads change | Inventory response |
|------------|--------------------|
| Budget ↑ | Recompute \(U_{ads}\); raise R only if capacity/age allow |
| Budget ↓ / cancel | Shrink R; unlock surplus |
| Mid-event ACOS spike + low cover | Stop scale; do not “spend out of stockout” |
| Post-event ads still high | Conflicts with unlock/clearance — explicit decision |

## 7. Numeric pattern

Example: base 100 u/day, 5-day event, \(U=2.5\), \(SS_{evt}=400\):

```text
R ≈ 250×5 + 400 = 1,650
```

- If sellable by T−3 ≥ ~80% of R → release main ads budget  
- If sellable only 900 → cut demand target (budget/discount/duration) **or** expedite stock — not ads-only  

## 8. Org SLA (minimum)

| Signal | Owner response |
|--------|----------------|
| Cover &lt; policy and ads status HIGH | Same-day joint action (plan + ads) |
| R change &gt; 20% | Notify ads within 24h |
| ETA miss past sellable_deadline | Ads gate closes until new ETA accepted |

Plan owns R, windows, capacity; Ads owns bids/budget **inside** gates; Ops executes publish/reserves.

## 9. Failure modes

- Locking in-transit as if sellable  
- Ads uses high scenario; stock uses low scenario with no reconcile  
- Reserve not reflected in ATP — other channels sell through  
- No unlock → artificial stockout and aged risk  
- Locking Amazon path while shared components stay fully published elsewhere  

## 10. Weekly plan fields

| Field | Example |
|-------|---------|
| event_id | BFCM_2026 |
| reserve_units | 1650 |
| ads_gate_status | OPEN / THROTTLED / BLOCKED |
| sellable_deadline | 2026-11-20 |
| cover_at_lock | 18.5 days |

## 11. Principle

> **Lock = promised supply for paid demand.  
> Ads gate = no supply, no scale.  
> Unlock = don’t let locks become aged inventory.**

## Links

- promo-demand-lock.md — uplift & timeline  
- ads-inventory-linkage.md — patterns A–D  
- multi-channel-inventory.md / atp_calculate.py — reserves in ATP  
- inventory-reservation.md — technical hold lifecycle  
- ipi-capacity-limits.md — FBA headroom for event builds  
