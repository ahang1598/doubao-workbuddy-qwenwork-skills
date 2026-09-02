# Multi-Channel Shared Inventory (海外仓 / 本地仓 / 多平台)

Extends FBA-centric planning to a **shared inventory network**: local warehouse, overseas 3PL, and non-Amazon channels (Shopify, TikTok Shop, eBay, Walmart, wholesale, etc.).

Industry consensus (2025–2026 ops practice): one physical truth, channel-specific **visibility**, hard rules against oversell — especially when Amazon is in the mix.

## 1. Core Architecture

```
Physical stock (WMS / 3PL / local / overseas)
        ↓
  Free-to-sell (ATP) pool
        ↓
  ┌─────┴──────────────────────┐
  │                            │
Static ring-fence            Shared pool
(FBA send-in)            (MFN + DTC + other marketplaces)
  │                            │
FBA only              Channel caps + buffers + reserves
```

**Critical fact:** Units already in **FBA are not poolable** with other channels (unless using MCF at extra cost).  
Treat FBA as a **static allocation**. Everything else can share one pool if sync is fast enough.

## 2. Available-to-Promise (ATP) Formula

Do not publish “on-hand” to channels. Publish ATP:

```
ATP = On-hand
    − Committed orders (unshipped)
    − Quality / returns hold
    − Wholesale / promo / pre-order reserves
    − FBA-dedicated & FBA in-transit
    − Central safety buffer (optional)
```

Only **ATP** feeds channel availability rules.

## 3. Pooling Models (choose by sync speed)

| Sync latency | Safe model | Oversell risk |
|--------------|------------|---------------|
| Manual / hours–days | **Static split only** (fixed units per channel) | High if forced unified |
| 15–60 min | Dynamic allocation + larger buffers | Moderate |
| 2–15 min | Unified pool + small buffers | Low |
| < 2 min (event-driven) | Full unified pool | Minimal |

**Hybrid (most Amazon+DTC sellers):**  
- Static quantity for FBA  
- Unified pool for Shopify / TikTok / eBay / MFN / wholesale remainder  

## 4. Channel Buffers (anti-oversell)

Never list 100% of ATP on every channel. Hold back a buffer for sync lag and spikes.

| Channel | Typical buffer | Why |
|---------|----------------|-----|
| Amazon (MFN) | 10–15% | Oversell → ODR / suspension risk |
| Walmart | 10–15% | Similar marketplace penalties |
| TikTok Shop | 15–20% | Faster spikes, API maturity varies |
| Shopify DTC | 5–10% | Lower platform penalty; higher margin |
| eBay | ~10% | Mid |

**Velocity-based buffer (optional):**

```
Buffer ≈ daily_velocity × (sync_interval_hours / 24) × 1.5~2.0
```

## 5. Channel Priority When Stock Is Scarce

When ATP is low, do not first-come-first-served blindly. Prefer:

1. **Hard reserves** (confirmed wholesale PO, pre-orders, promo holds)  
2. **Highest contribution margin** after fees  
3. **Strategic / rank-critical** Amazon ASINs (if MFN)  
4. Lower-margin marketplaces last  

Example priority stack (illustrative): DTC → Wholesale committed → Amazon MFN → other marketplaces.

## 6. FBA vs Shared Pool Planning

| Decision | Rule |
|----------|------|
| How much to send to FBA | Use **Amazon-only forecast** + FBA LT + FBA safety stock (existing skill modules) |
| What remains for other channels | Total purchasable − FBA allocation − FBA pipeline |
| Over-ship to FBA | Double penalty: FBA storage/aged fees **and** starvation of other channels |
| Amazon restock report | Often ignores other channels — **do not** follow blindly for shared SKUs |

## 7. Overseas / Local Warehouse Roles

| Node | Shared-pool role |
|------|------------------|
| **Overseas 3PL (美/欧仓等)** | Primary shared pool for MFN + multi-platform fulfillment |
| **Local / origin warehouse** | Bulk hold, prep, first-leg to overseas or FBA |
| **FBA** | Ring-fenced sellable for Amazon Prime path |
| **AWD** | Amazon-side upstream (not multi-platform pool) |

Allocation idea for overseas hub stock:

```
Hub_ATP → apply channel buffers → publish per channel
Hub → FBA transfer = separate decision (multi-warehouse rules)
```

## 8. Replenishment of the Shared Pool

Forecast **total multi-channel demand** for hub replenishment:

```
D_shared = Σ channel daily demand (exclude pure FBA-fulfilled volume)
ROP_shared = D_shared × LT_to_hub + SS_shared
```

Then split arrivals:

- Portion to FBA (Amazon plan)  
- Remainder to hub ATP pool  

Do **not** sum independent channel safety stocks if they share one warehouse — that double-counts buffer and ties up cash. Prefer **one pool SS** + channel publish buffers.

## 9. Reserves (must subtract from ATP)

- Wholesale standing orders  
- Pre-orders  
- Campaign / flash-sale holds  
- Quality inspection / quarantine  
- Bundle component locks  

Review reserves weekly; stale reserves recreate silos.

## 10. Planner Workflow (add-on to weekly plan)

1. Start from WMS on-hand by location  
2. Compute ATP (formula above)  
3. Decide FBA send-in with existing FBA modules  
4. Remaining ATP → shared pool  
5. Apply channel buffers + priority / caps  
6. Set publish qty per channel  
7. Flag sync health (if lag high → raise buffers or freeze risky channels)  

## 11. Weekly Plan Fields (optional columns)

| Column | Meaning |
|--------|---------|
| location | FBA / AWD / OVERSEAS_HUB / LOCAL |
| atp_units | Free-to-sell after holds |
| pool_type | STATIC_FBA / SHARED |
| channel_publish_amazon_mfn | Qty visible on Amazon MFN |
| channel_publish_dtc | Qty visible on DTC |
| channel_buffer_pct | Buffer used |
| shared_priority | Channel rank when scarce |

## 12. Principles

1. **One physical truth** — WMS/ERP is source of truth, not Seller Central alone.  
2. **FBA is ring-fenced** — plan it separately; never assume it can back DTC.  
3. **Publish ATP, not on-hand.**  
4. **Buffers scale with lag and penalty severity.**  
5. **Replenish the pool from combined demand; allocate FBA from Amazon demand.**  
6. **Oversell prevention > maximizing every channel’s displayed stock.**

## Link to Existing Modules

| Module | Interaction |
|--------|-------------|
| multi-warehouse.md | FBA/AWD/hub node choice for Amazon path |
| demand-forecasting.md | Channel-level inputs; sum for shared ROP |
| safety-stock.md | Pool-level SS for hub; FBA SS stays Amazon-specific |
| supplier-constraints.md | MOQ applies to factory→hub or factory→FBA legs |
| exception-priority.md | Add oversell/sync failures as data-quality or pipeline exceptions |
| ads-inventory-linkage.md | Do not spike ads on a channel whose publish qty is buffer-throttled |
