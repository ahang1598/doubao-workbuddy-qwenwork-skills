# Factor Audit And Robustness

Use this reference to keep factor validation honest.

## Leakage Checks

- Confirm the factor never uses future labels, future returns, future prices, or later revisions.
- Record when each input becomes available.
- Apply a clear signal lag before constructing forward returns.
- For price-derived signals, separate signal price, execution price, and evaluation price.
- If a leak is found and fixed, document the incident, fix, and rerun results.

## Robustness Checks

- IS/OOS split.
- Walk-forward windows when sample size allows.
- Parameter stability around the selected parameter values.
- Cost sensitivity for fees and slippage.
- Reverse-factor baseline.
- Fixed-seed random-factor baseline on real returns.
- Equal-weight buy-and-hold baseline.
- Zero-return / always-flat baseline.
- Leave-one-asset-out or leave-one-sector-out tests when data allows.

## Subagent Governance

If a background agent is used:

- It must work in `/home/coder/project/replication/report-replication/{report_id}/.agent_work/` or another isolated scratch directory.
- Its outputs are drafts only.
- The main agent must verify formulas, data provenance, timestamps, CSVs, charts, BACKTEST outputs, and conclusions before promotion.
- Untraceable data, unverifiable metrics, synthetic market data, or unsupported conclusions must be discarded or recorded as rejected attempts.

## Report Requirements

- HTML report must include reading guide, metric dictionary, RAG scorecard, benchmark comparison, and BACKTEST alignment audit.
- Every chart must include chart-specific beginner-facing explanation.
- The conclusion label must be one of: effective, weakly effective, ineffective, regime-dependent, or inconclusive.
