# Worked Example - tax-planning

## Ask

> I'm a freelancer making $150k/year. I'm currently a sole proprietor. Am I paying too much in tax?

## What a correct response contains

Should identify the potential benefit of an S-Corp election (to save on self-employment tax). Should discuss common deductions for freelancers. Should emphasize that AI cannot file taxes and a CPA review is required. Should provide a Tax Strategy Report structure with an action plan.

## File-driven variant

With fixture(s) `evals/files/income_and_brackets.csv`:

> Using the attached bracket schedule and income (evals/files/income_and_brackets.csv): compute total tax, effective rate, and marginal rate. Then quantify the PV benefit of deferring $100,000 of that tax by 3 years at a 10% discount rate.

Expected: Tax $308,000; effective 15.4%; marginal 21%; deferral PV benefit $24,869.

## Compute, don't estimate

All figures above come from [`scripts/calculate.py`](./scripts/calculate.py) - import its functions rather than doing arithmetic in prose.
