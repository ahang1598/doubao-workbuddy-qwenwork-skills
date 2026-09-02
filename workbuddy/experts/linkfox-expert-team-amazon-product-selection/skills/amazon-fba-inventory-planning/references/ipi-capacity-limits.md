# IPI, Storage Capacity & Restock Limits (FBA)

Amazon does not only price storage — it **caps** how much you can hold and send.  
IPI and capacity limits are hard constraints on `recommended_qty` to FBA.

Confirm live thresholds in Seller Central; bands below are planning defaults used widely in 2025–2026 operator practice.

## 1. IPI (Inventory Performance Index)

- Score range roughly **0–1000**
- Built from efficiency signals such as: excess inventory, sell-through, stranded inventory, in-stock rate (weights evolve)
- Evaluated on Amazon’s schedule (historically quarterly; enforcement can feel faster)

| IPI band (approx.) | Planning stance |
|--------------------|-----------------|
| **&lt; 400** | At risk / restricted capacity — protect sell-through, clear excess & stranded first |
| **400–500** | Survive zone — avoid new aged build; tight FBA cover |
| **500–550+** | Healthier capacity eligibility — still don’t waste cube |
| **Higher** | More flexibility, not a license to overstock |

**Target for serious operators:** stay comfortably **above 400**, prefer **500+**.

## 2. Storage capacity vs restock limits

| Control | What it limits | Failure mode |
|---------|----------------|--------------|
| **Storage capacity** | How much volume you may **hold** in FBA (often by size tier: standard, oversize, apparel, etc.) | Cannot create/ship inbound when full |
| **Restock / ASIN limits** | How much you may **send** for an ASIN or group (e.g. days-of-supply style caps) | Shipment blocked even if account capacity remains |
| **Utilization / aged policy** | Economic pressure | Fees, not always a hard create-shipment block |

Approximate capacity math operators use:

```text
Available to send ≈ Restock_or_capacity_limit − (On-hand + Inbound working + Inbound shipped)
```

Always use Amazon’s current capacity monitor numbers when available.

## 3. How this changes restock quantity

After unconstrained `Q*` (forecast + cover + MOQ rules):

```text
Q_fba_final = min(Q_fba_desired, capacity_headroom, asin_restock_headroom)
```

If truncated:

1. **Do not** push the remainder into FBA “anyway”  
2. Park upstream (AWD / hub) per multi-warehouse rules **if** network allows  
3. Or delay PO / reduce buy  
4. Flag exception (capacity) on weekly plan — high severity in peak season  

## 4. Improving IPI (planner levers)

| Lever | Action |
|-------|--------|
| Excess | Lower target cover; split inbound; remove chronic overstock |
| Sell-through | Prefer A-items in limited cube; ads-inventory alignment |
| Stranded | Fix listing/eligibility ASAP (zero sell-through, still occupies capacity) |
| In-stock | Protect hero SKUs from stockout (stockouts also hurt) |

Clearing **stranded + dead** often helps more than micro-tuning a healthy ASIN.

## 5. Peak season warning

Q4 (and major events): capacity is scarcest when you need it most.  
If IPI is weak entering peak, you may be unable to inbound enough — plan upstream stock and earlier FBA fills in allowed windows.

## 6. Weekly plan fields

| Field | Meaning |
|-------|---------|
| ipi_band | e.g. AT_RISK / OK / STRONG |
| capacity_headroom_units_or_cuft | Remaining send capacity if known |
| qty_capped_by_limit | true/false |
| qty_deferred_upstream | Units kept out of FBA due to limits |

## 7. Script enforcement

`scripts/calculate_restock.py` accepts:

- `--capacity-headroom` — account/size-tier units still sendable
- `--asin-restock-headroom` — ASIN restock units still sendable
- `--defer-overflow-upstream` — surface cut qty as AWD/hub suggestion
- `--require-capacity` — if no headroom inputs, force FBA qty to 0 (strict/peak policy)

Final FBA qty is capped by `min(capacity_headroom, asin_restock_headroom)` when provided.
Without headroom inputs, default is **uncapped with warning**; `--require-capacity` blocks send.

## 8. Link to other modules

| Module | Interaction |
|--------|-------------|
| storage-optimization.md | Aged + utilization economics |
| multi-warehouse.md | Overflow to AWD/hub when FBA capped |
| multi-channel-inventory.md | Don’t starve other channels by over-filling FBA |
| exception-priority.md | Capacity block = pipeline/constraint exception |
| hold_vs_remove.py | Free cube by removing dead stock |

## Principle

> FBA qty is `min(demand need, policy cover, MOQ reality, **Amazon capacity**)`.  
> IPI protects future capacity; excess inventory spends it.
