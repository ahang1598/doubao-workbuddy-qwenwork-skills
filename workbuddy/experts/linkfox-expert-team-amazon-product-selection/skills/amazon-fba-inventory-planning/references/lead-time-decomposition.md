# Lead Time Decomposition & Monitoring

Do not treat lead time as a single unexplained constant.  
Decompose **PO → sellable**, measure each leg, and derive \(LT_{avg}\) and \(\sigma_{LT}\) from data.

## 1. Why

Safety stock already accepts \(\sigma_{LT}\):

\[
SS = Z \sqrt{LT \cdot \sigma_d^2 + D^2 \cdot \sigma_{LT}^2}
\]

If \(LT\) and \(\sigma_{LT}\) are guesses, SS is a guess.  
Most overruns sit in a few legs (space, customs, FC receiving)—not uniformly in “the lead time.”

## 2. Standard legs (PO → FBA sellable)

| Code | Leg | Typical content |
|------|-----|-----------------|
| \(L_{prod}\) | Production | Confirm → cargo ready |
| \(L_{exw}\) | Origin handoff | Ready → gate-in / loaded |
| \(L_{port}\) | Origin port | Gate-in → ATD |
| \(L_{ocean}\) | Linehaul | ATD → ATA |
| \(L_{dest}\) | Import clearance | ATA → cleared |
| \(L_{dray}\) | Drayage | Cleared → warehouse/FC appointment |
| \(L_{fc}\) | FC receive | Appointment/receive → **sellable** |

\[
LT = \sum_i L_i
\]

Simplify for sparse data (4 legs): Production | International move | Clearance+dray | FC sellable.  
**Keep the same definition per lane** (mode × origin × destination network).

Air/domestic lanes drop ocean-specific legs but must still end at **sellable**, not “arrived at port.”

## 3. Variance

If legs approximately independent:

\[
\sigma_{LT} \approx \sqrt{\sum_i \sigma_i^2}
\]

Contribution share:

\[
\text{Share}_i \approx \frac{\sigma_i^2}{\sum_j \sigma_j^2}
\]

Manage the legs with the highest share first.  
If legs are strongly correlated in peak season, also track empirical \(\mathrm{std}(LT_{total})\).

## 4. What to store per shipment

Timestamps (minimum useful set):

```text
po_confirm → cargo_ready → etd → atd → ata
→ cleared → wh_or_appt → fc_received → sellable
```

Derived: each \(L_i\), \(LT_{total} = sellable - po_confirm\).

**Lane key:** mode + origin region + dest region + FC vs hub.

## 5. Statistics to publish per lane

| Metric | Use |
|--------|-----|
| Median / P50 of \(LT\) and each \(L_i\) | Default planning LT |
| P90 of \(LT\) | Event sellable deadlines, commitments |
| Std of \(LT\) or synthesized \(\sigma_{LT}\) | `--std-lead` into restock/SS |
| Share of variance by leg | Ops priority |
| Sample size + as-of date | Trust / staleness |

Rolling window example: last 20 shipments or 90 days (reset on structural change).

## 6. Feeding restock math

```text
--lead-time   ← lane P50 (or mean) total LT to sellable
--std-lead    ← lane std(LT) or sqrt(sum σ_i²)
```

| Decision | Prefer |
|----------|--------|
| Routine ROP / cover | \(LT_{P50}\) + SS using \(\sigma_{LT}\) |
| Promo sellable_deadline | Work backward from event using \(LT_{P90}\) |
| One-off path change | Temporary buffer days on the weak leg; don’t permanently inflate all SKUs |

## 7. When to update parameters

| Trigger | Action |
|---------|--------|
| Biweekly / monthly | Recompute lane P50/P90/σ |
| Leg P90 up for 2 periods | Raise that leg’s plan time or σ; document |
| Carrier / port / season regime change | **Reset** sample window |
| Systematic late bias | Add days to the slow legs first |
| Single disruption | Exception for in-transit POs; don’t rewrite lane forever |

## 8. Monitoring cadence

- **Weekly:** in-transit ETAs vs plan by leg (early warning)  
- **Monthly:** refresh lane file used by planning  
- **Post-event:** actual vs planned sellable date for promo SKUs  

Tie slips to ads gates and expedite decisions (`ads-inventory-lock-linkage.md`).

## 9. Data contract fields (lane profile)

| Field | Example |
|-------|---------|
| lane_id | US_WEST_SEA_FBA |
| lt_p50_days | 38 |
| lt_p90_days | 52 |
| std_lt_days | 7.5 |
| leg_stats_json | medians/σ per leg |
| sample_n / as_of | 24 / 2026-07-01 |

Soft default LT in planning is allowed only if labeled; prefer lane profile over silent constants (`data-contract.md`).

## 10. Principle

> **Decompose to see where time goes; measure to see where risk sits; aggregate to feed SS.**  
> \(\sigma_{LT}\) is an output of monitoring—not a fixed folklore number.

## Links

- safety-stock.md — uses LT and \(\sigma_{LT}\)  
- calculate_restock.py — `--lead-time`, `--std-lead`  
- promo-demand-lock.md — sellable_deadline from P90  
- data-contract.md — no silent LT = 0  
- supplier-constraints.md — supplier reliability affects \(L_{prod}\)  
