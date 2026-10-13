# Worked Example - cvp-breakeven

## Ask

> Price 1,200, variable cost 780, fixed costs 8,400,000/year. How many units to break even, and how many for 2,100,000 after-tax profit at 30% tax?

## What a correct response contains

Contribution 420/unit. Breakeven 20,000 units (24,000,000 revenue). After-tax target needs pre-tax 3,000,000 -> (8,400,000+3,000,000)/420 = 27,143 units.

## File-driven variant

With fixture(s) `evals/files/product_economics.csv`:

> From the attached unit economics (evals/files/product_economics.csv): compute breakeven units and sales, units needed for the target profit, margin of safety at current volume, and degree of operating leverage.

Expected: Breakeven 6,000 units ($300,000); target requires 8,000 units; MOS 25%; DOL 4.0.

## Compute, don't estimate

All figures above come from [`scripts/calculate.py`](./scripts/calculate.py) - import its functions rather than doing arithmetic in prose.
