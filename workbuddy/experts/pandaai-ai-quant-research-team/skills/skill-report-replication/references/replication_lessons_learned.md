# Replication Lessons Learned

Keep these lessons in mind during report replication.

## Data Mismatch

If the original report uses a data vendor, market, contract universe, or sample period that is not available locally:

- State the mismatch in the validation report.
- Do not invent replacement data.
- If using a proxy universe, label the conclusion as limited or inconclusive unless the proxy is clearly justified.

## Theory Versus Engine Backtest

Factor validation curves and BACKTEST account/equity curves can differ because of:

- Close-to-close theoretical returns versus executable order timing.
- Equal-weight validation versus actual position sizing.
- Fees, slippage, margin, contract multiplier, and capital allocation.
- Missing trade-level data.
- Different universe filters or roll rules.

Always explain the difference before drawing a conclusion.

## Output Discipline

- Keep outputs under `/home/coder/project/replication/report-replication/{report_id}`.
- Keep subagent scratch work isolated.
- Preserve raw engine outputs when useful for audit.
- Never call a project complete if the final quality gate fails.
