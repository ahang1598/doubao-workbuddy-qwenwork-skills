# Worked Example - fixed-asset-accounting

## Ask

> We bought a generator: invoice 12,000,000 NGN, delivery 400,000, installation 600,000, staff training 250,000, 10-year life, 1,000,000 residual, straight-line. What do we capitalize and what's annual depreciation?

## What a correct response contains

Capitalize 13,000,000 (invoice + delivery + installation); expense training 250,000. Annual depreciation = (13,000,000 - 1,000,000)/10 = 1,200,000.

## File-driven variant

With fixture(s) `evals/files/asset_register.xlsx`:

> Compute year-1 depreciation for each asset in the attached register (evals/files/asset_register.xlsx) using the stated method, and total the charge. The mould has a 200,000-unit life and produced 35,000 units this year.

Expected: Press $20,000 (SL); trucks $40,000 (DDB y1); mould $17,500 (UoP); total $77,500.

## Compute, don't estimate

All figures above come from [`scripts/calculate.py`](./scripts/calculate.py) - import its functions rather than doing arithmetic in prose.
