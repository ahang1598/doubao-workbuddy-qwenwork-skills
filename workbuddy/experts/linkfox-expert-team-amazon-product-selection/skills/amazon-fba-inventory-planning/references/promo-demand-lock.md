# Promo / Peak Demand Uplift & Inventory Lock Windows

Big events (Prime Day, Black Friday, 88/99/11.11, store-wide deals) change **demand, ads, and what inventory is allowed to move**.  
This module connects forecasting uplifts, inbound freezes, channel reserves, and ads–inventory alignment.

## 1. Definitions

| Term | Meaning |
|------|---------|
| **Demand uplift** | Multiplier on baseline forecast during the event window |
| **Lock window** | Period when inventory is reserved for the event and not freely sold down by other channels/promos |
| **Freeze inbound** | Stop or delay non-critical FBA/hub receipts that would arrive mid-chaos without sell-through plan |
| **Pre-position** | Inbound timed to be **sellable before** the event starts (include FC receiving lag) |

## 2. Demand uplift model (planning)

Start from baseline daily demand \(\hat{D}_{base}\), then:

```text
D̂_event(t) = D̂_base(t) × U_event × U_ads × U_price × U_halo
```

| Factor | Typical range | Notes |
|--------|---------------|-------|
| \(U_{event}\) | 1.5×–5× (category dependent) | Use last 1–3 years same event if possible |
| \(U_{ads}\) | 1.0×–2.0× | Only if incremental spend is funded and in stock |
| \(U_{price}\) | 1.0×–1.8× | Deep discount elasticity; watch margin floor |
| \(U_{halo}\) | ~1.0–1.2 | Variant halo / store traffic spillover |

**Practical shortcuts**

- No history: use category benchmarks + conservative 1.5–2×, then revise  
- Strong history: day-by-day profile (build-up, peak day, tail) not a flat multiplier  
- Always produce **low / base / high** scenarios for cash and capacity  

Feed \(\hat{D}_{event}\) into safety stock and target cover **only for the event horizon**, then revert.

## 3. Inventory lock window

Purpose: stop other channels or non-event promos from eating stock needed for the main event.

```text
Lock start: typically T−7 to T−3 before event (earlier for slow inbound)
Lock end:   event end + short tail (1–3 days) unless aged risk forces clearance
```

### What “lock” means operationally

| Action | During lock |
|--------|-------------|
| Shared pool publish | Raise buffer or **hard-reserve** qty for event channel/listing |
| Other channels | Lower caps or pause low-priority marketplaces |
| Wholesale | No discretionary draws against reserved pool |
| DTC sitewide deals | Exclude locked SKUs unless event is DTC-led |
| FBA | Ensure sellable **before** T0; avoid inbound that lands after peak without plan |

Reserves must appear in ATP as `reserves` (see multi-channel-inventory / atp_calculate).

## 4. Timeline (planner checklist)

| Phase | Timing (relative to event start T0) | Actions |
|-------|--------------------------------------|---------|
| Plan | T−60 to T−30 | Pick SKUs, uplift scenarios, capacity/IPI check |
| Buy / inbound | T−45 to T−21 | Factory + ship so FBA **sellable by T−7 to T−3** |
| Ads creative / budget | T−21 to T−7 | Align spend to cover; no scale if cover thin |
| Lock | T−7 to T−3 | Apply reserves; reduce non-event publish |
| Event | T0 to T_end | Monitor cover hourly/daily; throttle ads if cover collapses |
| Unlock / tail | T_end to +3d | Release reserves; clearance if aged risk |
| Post-mortem | +7 to +14d | Actual uplift vs forecast; update playbook |

Receiving lag: treat “in FC” ≠ “sellable”; include check-in days in LT.

## 5. Link to ads–inventory patterns

| Situation | Pattern | Action |
|-----------|---------|--------|
| Ads ramped, cover below event policy | **A** | Prioritize FBA inbound / air; throttle ads until ETA |
| Cover high, ads not funded | **B** | Don’t lock idle stock; either fund ads or don’t pre-position |
| Both high through peak | **C** | OK if sell-through plan clears before aged threshold |
| Event on new ASIN | **D / TEST** | Small controlled buy; don’t full-lock network stock |

## 6. Capacity & aged constraints

- Event builds often conflict with **IPI / restock limits** — check headroom before PO  
- Q4 storage rates: model holding cost if tail inventory remains  
- Post-event leftover: run hold_vs_remove earlier if age band is tight  

```text
Q_event_fba = min(demand_need, cover_policy, MOQ, capacity_headroom)
Remainder → hub/AWD only if it can replenish in time OR is intentionally post-event buffer
```

## 7. Forecast handoff fields

| Field | Example |
|-------|---------|
| event_id | PRIME_2026_H1 |
| uplift_base | 2.2 |
| uplift_high | 3.0 |
| lock_start / lock_end | dates |
| reserve_units | 5000 |
| sellable_deadline | date stock must be live |

## 8. Anti-patterns

- Flat 3× uplift with no day curve and no low scenario  
- Ads live while stock arrives **after** peak  
- Locking stock on all channels with no release rules  
- Ignoring capacity so event PO is rejected at shipment create  
- Treating post-event leftover as “normal SS” without age check  

## Principle

> Event planning = **time-phased demand** + **reserved inventory** + **ads only when cover is real** + **capacity-aware inbound**.  
> Unlock fast after the event so locks don’t become aged inventory.

## Links

- demand-forecasting.md — causal uplift layer  
- ads-inventory-linkage.md — patterns A–D during events  
- multi-channel-inventory.md — reserves in ATP  
- ipi-capacity-limits.md — FBA headroom  
- seasonal-calendar.md — peak calendar context  
- safety-stock.md — phase-specific cover  
