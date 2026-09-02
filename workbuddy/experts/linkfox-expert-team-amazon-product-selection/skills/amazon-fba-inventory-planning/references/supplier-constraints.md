# Supplier MOQ & Lead-Time Constraints in Restock Qty

Statistical restock quantity is only a **demand-side recommendation**.  
Final ship quantity must respect supplier and logistics constraints.

## Constraint Types

| Constraint | Symbol | Meaning |
|------------|--------|---------|
| Minimum order quantity | MOQ | Smallest units (or cartons) supplier will accept |
| Order multiple / batch size | Mult | Must order in packs of Mult (carton, case, container layer) |
| Maximum order quantity | MaxQ | Supplier capacity or cash/risk cap this cycle |
| Fixed lead time | LT | Agreed production + transit + FBA receiving estimate |
| Lead-time variability | σ_LT | Historical spread; feeds safety stock |
| Cutoff / ship window | — | Latest factory exit date to hit a needed arrival week |
| Payment terms | — | Affects cash peak, not unit math directly (see storage-optimization.md) |

## Adjustment Pipeline

Start from unconstrained recommendation \( Q^* \) (from target cover or ROP logic), then:

```
1. Q = max(Q*, 0)
2. If Q > 0 and Q < MOQ:
     - either raise to MOQ (if economics still OK)
     - or defer order / combine with next cycle / switch supplier
3. Round up to next multiple of Mult (carton/case)
4. Cap at MaxQ if set
5. Re-check aged risk, cash, and H(Q)/L(Q) after adjustment
```

### Pseudocode

```
Q_star = recommended unconstrained units
if Q_star <= 0:
    return 0

Q = Q_star
if Q < MOQ:
    if accept_moq_raise(Q, MOQ):   # margin, age risk, cash OK
        Q = MOQ
    else:
        return 0                  # defer

if Mult > 1:
    Q = ceil(Q / Mult) * Mult

if MaxQ is set:
    Q = min(Q, MaxQ)

return Q
```

## When Raising to MOQ Is Acceptable

Raise only if **all** roughly hold:

- Extra units still sell within aged threshold at expected velocity  
- Extra holding cost H(ΔQ) is acceptable vs margin  
- Cash peak still tolerable  
- SKU is not a failing TEST-phase new ASIN  

Otherwise **defer** rather than buy dead stock to satisfy MOQ.

## Lead Time in Planning

- Use **expected LT** (PO placed → sellable in FC), including Amazon receiving  
- Feed **σ_LT** into safety stock when variability is material  
- If supplier quotes improve/worsen, update LT before recalculating ROP  
- For split inbound: each tranche can have its own LT and arrival week  

### Late supplier risk

If factory is likely late:

- Increase effective LT or σ_LT  
- Or pull arrival target earlier (order sooner)  
- Or split: smaller early tranche + later balance  

## Interaction with New ASIN Ramp

- TEST phase: MOQ may force a larger first buy than ideal — treat excess as explicit test risk budget  
- If MOQ >> test budget, renegotiate sample MOQ, shared container, or do not launch  
- LEARN/SCALE: normal MOQ rounding applies once velocity is proven  

## Interaction with Weekly Plan Output

Record in plan notes / columns when possible:

- `moq`, `order_multiple`, `max_qty`  
- `qty_unconstrained` vs `qty_final`  
- Reason if deferred due to MOQ economics  

## Planner Checks Before Confirming PO

1. Unconstrained Q* from forecast + cover policy  
2. Apply MOQ / multiple / max  
3. Recompute days of cover and age exposure with final Q  
4. Run H(Q)/L(Q) if cost data exists  
5. Confirm cash timing under payment terms  
6. Only then lock supplier PO  

## Principle

> Constraints change **quantity and timing**, not the demand truth.  
> Never let MOQ silently create aged inventory without an explicit accept/defer decision.
