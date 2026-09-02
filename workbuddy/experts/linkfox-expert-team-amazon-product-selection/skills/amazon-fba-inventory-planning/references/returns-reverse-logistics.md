# Returns & Reverse Logistics Inventory Impact

Returns change **sellable supply, ATP, age profile, and cash** — not just “lost sales.”

## 1. What happens to a returned unit

| Path | Inventory effect | Planner note |
|------|------------------|--------------|
| **Sellable restock** | Back to FBA sellable (or hub after QC) | May reset or mix age bands; monitor stranded |
| **Unfulfillable** | Not sellable; still may incur storage | Decide remove / liquidate / Grade & Resell |
| **Amazon-owned damage** (e.g. DAMAGED / CARRIER_DAMAGED) | Often reimbursed; unit leaves your inventory | Track reimbursement lag in cash, not ATP |
| **Customer-damaged / opened** | Often unfulfillable under your account | High volume → policy + packaging review |
| **Expired** | Unfulfillable → disposal path | Date-sensitive categories need tighter cover |

Condition codes and programs change; always verify current Seller Central definitions.

## 2. FBA-oriented decision tree

```text
Return received
  → Sellable? → treat as inbound to sellable pool (adjust forecast noise)
  → Unfulfillable?
        → Grade & Resell eligible & margin OK? → used listing path
        → High residual value? → Removal to hub for re-prep / other channel
        → Low value / hygiene / safety? → Liquidation or disposal
```

**Rule of thumb:** if re-prep + fees > expected recovery, do not “wait and see” in unfulfillable.

## 3. Impact on planning math

| Input | How returns affect it |
|-------|------------------------|
| Forecast demand | Net demand ≈ gross orders − refund/return rates; use net when possible |
| Sellable on-hand | Include only fulfillable; never count unfulfillable as cover |
| Days of cover | Use sellable only |
| ATP (hub) | Returns in QC = quality_hold until graded |
| Aged risk | Restocked returns can worsen age mix if slow |
| H(Q) / L(Q) | Unfulfillable has holding cost with little revenue optionality |

## 4. Hub / multi-channel returns

- Physical return to overseas/local hub → **QC hold** before ATP  
- Only **graded sellable** re-enters shared pool  
- Component returns for bundles: restock components carefully (see kits BOM)  
- Cross-channel returns should not double-count into Amazon sellable

## 5. Operating cadence

**Weekly**
- Unfulfillable units & estimated storage burn  
- Return rate by ASIN (spike = listing/quality issue)  

**Monthly**
- Recovery mix: restock % / Grade & Resell % / remove % / dispose %  
- Top return-reason ASINs → fix or kill restock  

## 6. Planner actions

| Signal | Action |
|--------|--------|
| High return rate + still restocking | Pause scale; fix product/listing |
| Unfulfillable aging | Removal / liquidation batch |
| Sellable returns volatile | Slightly higher SS or lower service on that ASIN |
| Reimbursement backlog | Cash forecast only; not cover |

## Principle

> Returns are a **supply stream with friction**.  
> Count only graded sellable toward cover and ATP; clear unfulfillable on economics, not hope.
