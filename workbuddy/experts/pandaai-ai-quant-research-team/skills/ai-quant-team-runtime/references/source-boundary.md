# Source boundary

This agent orchestrates five independent QuantSkills repositories and does not vendor their source code.

## Upstream projects

- `skill-report-replication`: report provenance, formula reconstruction, real-data validation, and backtest groundwork.
- `skill-factor-mining-pandaai`: candidate-factor translation and auditable experiment ledger.
- `skill-pandaai-factor-online`: PandaAI CLI preflight, factor execution, result collection, and cost-aware interpretation.
- `skill-backtest-overfit`: DSR, PBO, Haircut Sharpe, and minimum track-record diagnostics.
- `skill-strategy-tearsheet-report`: JSON and self-contained HTML performance reporting.

Follow each upstream repository's license and current `SKILL.md`. The upstream repositories remain the authority for tool-specific commands and field definitions.

## Local original work

The orchestration policy, evidence contract, deterministic workflow guard, validation tests, and portable runtime adapters in this repository are original coordination work for this agent.

## Data and credentials

- Do not commit research data, PandaAI responses, reports supplied by users, API tokens, passwords, cookies, or local account configuration.
- Login must remain an interactive action in the official client.
- A run directory is user-owned working data and must stay outside the published agent repository.

## Claims

The evidence gate proves that required local artifacts and command receipts existed and matched their hashes at finalization. It does not prove economic validity, guarantee future returns, or force a third-party host to invoke tools. Host-side required-tool and workflow enforcement remain platform responsibilities.

