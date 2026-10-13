# Worked Example - earned-value-mgmt

## Ask

> Our project was supposed to be 50% done ($500k PV). We've spent $600k (AC) but we are only 40% done (EV = $400k). How are we doing?

## What a correct response contains

Should calculate CPI (400/600 = 0.67). Should calculate SPI (400/500 = 0.80). Should conclude the project is over budget and behind schedule. Should provide a Project Performance Dashboard.

## File-driven variant

With fixture(s) `evals/files/project_status.csv`:

> Assess the project in the attached status file (evals/files/project_status.csv): compute CV, SV, CPI, SPI, EAC (CPI method), and TCPI, and state whether the original budget is still credible.

Expected: CV -70,000, SV -50,000, CPI 0.865, SPI 0.90, EAC $2,311,111, TCPI 1.047.

## Compute, don't estimate

All figures above come from [`scripts/calculate.py`](./scripts/calculate.py) - import its functions rather than doing arithmetic in prose.
