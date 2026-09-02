# Multi-Warehouse & AWD Allocation (FBA Planning)

After you know **how many** units to buy, decide **where** they should sit: FBA, AWD, local/overseas hub, or a split.

This module is a practical allocation layer on top of restock math — not a full WMS.

## Node Roles

| Node | Role | Strengths | Watch-outs |
|------|------|-----------|------------|
| **FBA** | Customer-facing Amazon fulfillment | Fast Prime delivery, conversion | Higher storage & aged fees; utilization risk |
| **AWD** | Amazon Warehousing & Distribution (US-focused) | Lower storage than FBA; replenishes FBA on signal | Extra hop; not all marketplaces/SKUs; still Amazon ecosystem rules |
| **Local / overseas hub** | Seller or 3PL warehouse | Cheap bulk hold; flexible cross-channel | Longer ship-to-FBA lead time; not Prime until in FBA |
| **Split** | Combine nodes | Cash & age control | More ops complexity |

## Decision Inputs

Reuse existing plan fields, then add:

- `recommended_qty` (after MOQ / multiple constraints)
- Days of cover if all went to FBA
- Unit cube / size tier (storage sensitivity)
- Season phase (pre-peak, peak, post-peak, off)
- Age risk of current FBA stock
- Lead time **to FBA** from each node (hub→FBA, AWD→FBA, factory→FBA)
- Cash peak tolerance

## Default Allocation Rules

### Rule A — Ship direct to FBA when

- SKU is **Priority A** with low cover (stockout risk)
- Recommended cover target is already lean (e.g. ≤ 45 days)
- Unit is small-cube / high-turn
- Not in a bulk pre-build for a far peak

→ **Destination = FBA (100%)**

### Rule B — Prefer AWD (or hub) for bulk / early build when

- Pre-peak or scale buy would push FBA weeks-of-supply high
- Product is bulky or storage-expensive in FBA
- You can replenish FBA from AWD/hub inside an acceptable LT
- Goal is to keep **FBA cover in a healthy band** (often ~30–45 days) while parking excess upstream

→ **Split example:**
- FBA tranche = units to reach FBA target cover (e.g. 35–45 days)
- Remainder → AWD or hub

### Rule C — Keep excess out of FBA post-peak / slow movers

- Post-season or LEARN-phase weak signal
- Near aged threshold on existing FBA stock
- recommended_qty would mainly increase aged exposure

→ Prefer **no FBA inbound** or **hub only**; run hold_vs_remove on FBA remainder

### Rule D — New ASIN TEST phase

- First test quantity: **FBA only** (need real Amazon velocity signal)
- Do not park test stock in AWD/hub “to save storage” if it delays learning

## Simple Split Formula

When Rule B applies:

```
FBA_target_units = forecast_daily × FBA_cover_days   # e.g. 40
FBA_ship = max(0, FBA_target_units − FBA_on_hand − FBA_inbound)
Upstream_ship = max(0, total_recommended_qty − FBA_ship)
```

Clamp each leg to carton multiples / MOQ rules separately if suppliers require.

## Lead-Time Stacking

| Path | Effective LT to sellable on Amazon |
|------|-------------------------------------|
| Factory → FBA | Production + ocean/air + FBA receiving |
| Factory → AWD → FBA | Factory→AWD LT + AWD→FBA replenish LT |
| Hub → FBA | Hub pick/pack + transit + FBA receiving |

Safety stock for the **customer-facing node** should use the LT that actually replenishes FBA sellable stock.

## Cash & Storage Interaction

- Upstream storage is usually cheaper per cube, but **adds time**
- Splitting often lowers FBA peak storage and aged risk, while smoothing cash if tranches ship on different dates
- Still run H(Q)/L(Q) on the FBA-facing portion; upstream stock has its own hold cost (model simply if needed)

## Weekly Plan Columns (add)

| Column | Values |
|--------|--------|
| destination | FBA / AWD / HUB / SPLIT |
| qty_fba | Units inbound to FBA this cycle |
| qty_upstream | Units to AWD or hub |
| fba_cover_target_days | Policy cover for FBA node |
| upstream_note | Why split / why not |

## Planner Checklist

1. Compute unconstrained then constraint-adjusted total Q  
2. Choose destination using rules A–D  
3. If SPLIT, compute FBA leg to target cover; remainder upstream  
4. Apply MOQ/multiple **per leg** if needed  
5. Re-check FBA age risk and utilization  
6. Record destination + quantities on the weekly plan  

## Principle

> FBA is for **sellable readiness**.  
> AWD/hub is for **bulk and timing**.  
> Do not fill FBA just because total Q is large — fill FBA to the cover policy, park the rest upstream when the network allows.
