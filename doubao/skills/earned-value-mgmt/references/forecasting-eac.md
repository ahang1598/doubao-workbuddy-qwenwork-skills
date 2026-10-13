# Estimate at Completion (EAC) Forecasting

## The EAC Family — pick by diagnosis
| Formula | Assumption | Use When |
|---|---|---|
| `EAC = AC + (BAC − EV)` | Past variance was one-off; remaining work at plan | Isolated, corrected problem |
| `EAC = BAC / CPI` | Cost efficiency to date persists | Most common default; systemic cost issue |
| `EAC = AC + (BAC − EV)/(CPI × SPI)` | Cost AND schedule pressure both persist | Behind schedule with acceleration costs |
| `EAC = AC + bottom-up ETC` | Re-estimate remaining work | Major scope/approach change; mandated at thresholds |

`ETC = EAC − AC`; `VAC = BAC − EAC` (negative = overrun).

## TCPI — the reality check
`TCPI(BAC) = (BAC − EV) / (BAC − AC)` = efficiency required on ALL remaining work to land on budget.
- TCPI > 1.10 while CPI < 0.95: recovery is fantasy — re-baseline or fund the variance.
- Compare TCPI against the project's best 3-month historical CPI: if required > best ever achieved, escalate.

## Research-Backed Rules of Thumb (DoD studies)
- CPI stabilizes by ~20% completion; it rarely improves more than 10% thereafter.
- The overrun at completion is usually WORSE than the overrun to date predicts.
- Therefore: CPI-based EAC at 20%+ complete is a floor, not a ceiling.

## Schedule Forecasting
SPI($) degenerates to 1.0 at completion — use **earned schedule**: `ES = time at which planned value equaled current EV`; `SPI(t) = ES / actual time`; forecast duration = planned duration / SPI(t).

## Reporting Discipline
Show EAC range (best/likely/worst from the formula family), VAC, TCPI, and the driver narrative (rate vs. usage vs. scope — tie to variance-analysis decomposition).
