# Kits, Bundles & BOM Inventory

A kit/bundle sells as one parent SKU but **consumes multiple components**.  
Planning errors here cause phantom ATP, component stockouts, and oversell.

## 1. BOM basics

```text
Parent KIT-A
  ├─ Component C1 × 2
  ├─ Component C2 × 1
  └─ Packaging P1 × 1
```

Available kits are limited by the **tightest component**:

```text
Max_buildable_kits = min over i of floor( ATP_component_i / qty_per_kit_i )
```

Never publish parent availability above `Max_buildable_kits` (minus buffers).

## 2. Two operational models

| Model | How stock is held | When to use |
|-------|-------------------|-------------|
| **Virtual kit** | Components only; assemble to order / at pick | Flexible; needs WMS BOM |
| **Pre-built kit** | Parent already assembled in warehouse | Faster pick; ties capital in built form |

Hybrid: pre-build a small floor; keep remainder virtual.

## 3. ATP for parents vs components

**Shared component pool (multi-channel):**

```text
ATP_Ci = component free-to-sell (same ATP formula as single SKU)
Publish_KIT = min_i floor(ATP_Ci / bom_i) × (1 - buffer)
```

If the same component is also sold **standalone**:

- One physical ATP pool for C_i  
- Allocate priority: kit vs standalone (margin/strategy)  
- Or hard-reserve components for kits during promo  

## 4. FBA-specific notes

- FBA often receives **pre-built** kits as a single FNSKU — plan inbound as parent units  
- If you ship components separately and assemble later, Amazon path usually still needs compliant parent listing stock  
- Returns: parent return may yield incomplete components → QC before ATP  
- Don’t assume FBA parent stock can break into components for DTC without removal/rework  

## 5. Restock planning

1. Forecast **parent demand** (and standalone component demand if any)  
2. Explode BOM → component gross requirements  
3. Net against component ATP + inbound  
4. Apply MOQ per component supplier  
5. Decide pre-build qty vs virtual  
6. For FBA: convert to parent inbound qty within capacity limits  

```text
Component_need_i = parent_forecast × bom_i + standalone_forecast_i
Component_Q_i = Component_need_i − ATP_i − inbound_i (+ SS_i)
```

## 6. Oversell failure modes

| Mistake | Result |
|---------|--------|
| Publish parent from parent “record qty” without BOM check | Oversell kits |
| Double-count component in kit + standalone publish | Oversell component |
| No reservation on component when kit order books | Race between channels |
| Return incomplete kit to full ATP | Bad customer shipments |

## 7. Concurrency & reservation

- Reserve **components** (or pre-built parents) atomically when kit order is accepted  
- Idempotent keys on parent order line still apply  
- Bundle promotions: raise buffer or hard-reserve BOM before campaign  

## 8. Weekly plan fields

| Field | Meaning |
|-------|---------|
| is_kit | true/false |
| bom_json_or_ref | Component list |
| max_buildable | From current component ATP |
| limiting_component | SKU that binds max_buildable |
| prebuild_qty | Assembled on hand |

## 9. Link to other modules

| Module | Interaction |
|--------|-------------|
| multi-channel-inventory.md | Component ATP + channel publish |
| inventory-reservation.md | Reserve components on kit sell |
| calculate_restock.py | Run at component level, then parent FBA |
| new-asin-ramp.md | Test kits with minimal BOM exposure |
| exception-priority.md | Limiting component stockout = E1 on all parents that use it |

## Principle

> Kits don’t have independent physics — **components do**.  
> Plan, reserve, and publish through the BOM; treat parent qty as a derived view.
