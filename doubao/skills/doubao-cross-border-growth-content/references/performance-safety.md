# Performance Safety

Use this whenever metrics, paid amplification, budget, scaling, pause, channel comparison, or account actions appear. Detailed account optimization is outside this skill; do not route to a named ads skill unless a current ads/growth skill is available.

## Gate 1: Normalize

Fill the table before calculating.

| field | value |
|---|---|
| currency |  |
| reporting window |  |
| attribution window |  |
| aggregation level | channel / campaign / ad group / ad / creative / query / SKU |
| maturity | mature / partial / immature / unknown |
| clicks definition |  |
| orders definition |  |
| revenue basis | gross / net / unknown |
| cancellation/refund treatment |  |

If a required definition is unknown, label the result directional or block the decision.

## Gate 2: Reconcile Metrics

Use these formulas only with matching definitions:

- `CTR = clicks / impressions`
- `CPC = spend / clicks`
- `CVR = orders / clicks`
- `CPA = spend / attributed orders`
- `ROAS = attributed revenue / spend`
- `ACOS = spend / attributed revenue`
- `CPM = CPC × CTR × 1000`, with CTR as a decimal

Reverse-check where possible:

- `revenue ≈ orders × confirmed net AOV`
- `CPA × orders ≈ spend`
- `ROAS × spend ≈ revenue`
- `CPC / CPA ≈ CVR`

| check | result | status |
|---|---:|---|
| spend reconciliation |  | pass / conflict / unavailable |
| revenue reconciliation |  | pass / conflict / unavailable |
| CVR denominator |  | confirmed / ambiguous |
| attribution and maturity |  | usable / blocked |

If a conflict exceeds rounding or a documented attribution difference, stop the recommendation and name the field to reconcile. Do not choose the convenient number.

## Gate 3: Protect Profitability

Gross margin is not contribution margin.

Material variable costs can include:

- product cost;
- platform or marketplace commission;
- payment fees;
- fulfillment, pick-pack, warehousing and seller-paid shipping;
- discounts and subsidies borne by the seller;
- returns, refunds, cancellations and chargebacks;
- creator or affiliate commission;
- taxes or other per-order costs borne by the seller.

Formulas:

- `contribution_before_ads = net_revenue_per_order - material_variable_costs`
- `break_even_CPA = contribution_before_ads`
- `break_even_ACOS = contribution_before_ads / net_revenue_per_order`
- `break_even_ROAS = 1 / break_even_ACOS`
- `contribution_after_ads = orders × contribution_before_ads - spend`

Choose one status:

| status | meaning | permitted use |
|---|---|---|
| `verified` | net revenue and material costs are confirmed | may support a decision threshold |
| `scenario_only` | some costs are explicitly excluded | show as a scenario, not a hard business rule |
| `unknown` | material costs or revenue basis are missing | formula and missing fields only |

## Gate 4: Control Actions

Any increase in total budget is scaling. Renaming it “validation”, “small test”, “learning budget”, or “pre-scaling” does not change the action.

| current state | permitted action |
|---|---|
| metrics conflict | reconcile data only |
| maturity partial/immature/unknown | continue bounded sampling, maintain, reduce or pause; no scaling |
| profitability `unknown` | no profitability or scaling claim |
| below verified break-even | maintain only if a justified minimum learning budget exists; otherwise reduce or pause |
| above break-even but below verified safety target | maintain; no total-budget increase |
| verified mature unit above safety target | scaling may be considered by ads skill |

Additional blockers:

- Do not invent universal bid-change percentages, test budgets, fixed days, click counts, conversion counts, page-speed targets or scaling increments.
- If the user supplies a decision rule, use it exactly and test whether it is internally consistent.
- Keep reserve budget uncommitted.
- Without creative-level data, do not name a winning or losing creative.
- Do not use future LTV or repeat purchase to subsidize current losses when it is missing.

## Gate 5: Decision Ledger

Every budget, pause, maintain, or scale recommendation needs one row.

| unit | conclusion | required evidence or threshold | current state | permitted action | pass |
|---|---|---|---|---|---|
|  |  |  |  |  | yes / no |

Revise every `pass=no` row before answering.

## Common Failure Examples

- `ROAS 2.41 < safety ROAS 2.65`, then increasing budget: blocked.
- `ROAS 1.39 < break-even ROAS 2.38`, then retaining a large default test budget: blocked unless the user supplied and justified that learning budget.
- `CPC fixed`, then claiming CTR alone lowers CPA: mathematically invalid.
- Gross margin provided without fees/refunds, then declaring definitive break-even ACOS: scenario only.
- Five-day mature data mixed with two immature days, then naming a final winner: blocked.

## Optional Deterministic Check

If code execution is available, run:

```bash
python3 scripts/validate_performance.py --input <json-file>
```

Use this exact JSON shape. Keep `maturity` as one string; put thresholds and
budget actions in their named objects.

```json
{
  "spend": 270,
  "revenue": 649.86,
  "orders": 13,
  "clicks": 260,
  "impressions": 12000,
  "reported": {"roas": 2.41, "cpa": 20.77},
  "maturity": "mature",
  "profitability": {
    "status": "verified",
    "safety_roas": 2.65,
    "safety_cpa": 18.89
  },
  "decision": {
    "action": "scale",
    "current_budget": 100,
    "proposed_budget": 120
  }
}
```

Exit code `0` means the input passed; `1` means errors or blockers were found;
`2` means the JSON could not be read.

If execution is unavailable, fill Gates 1–5 manually. The absence of the script is not permission to skip the gates.
