---
name: factor-mining-pandaai
description: "Mine A-share quantitative factors with PandaAI in two modes: AI-led blind discovery using PandaAI data and iterative factor-analysis feedback, or evidence-grounded extraction from papers, reports, PDFs, DOCX files, and text. Use when asked to discover new factors autonomously, translate research formulas into pandaai-cli syntax, run controlled factor experiments, or interpret PandaAI factor-analysis results."
---

## WorkBuddy 登录职责边界

本成员只设计和检查候选因子，不执行 PandaAI 登录。需要登录时必须把任务交给
`pandaai-experimenter`，由其运行 WorkBuddy 安全交互入口。禁止在聊天、命令参数、任务包
或证据文件中接收任何登录信息。

## WorkBuddy 登录职责边界

本成员只设计和检查候选因子，不执行 PandaAI 登录。需要登录时必须把任务交给
`pandaai-experimenter`，由其运行 WorkBuddy 安全交互入口。禁止在聊天、命令参数、任务包
或证据文件中接收任何登录信息。

# Factor Mining PandaAI

Discover factor hypotheses autonomously from PandaAI data or extract them from
research documents, translate them into `pandaai-cli` formula syntax, and
optionally run PandaAI analysis. Treat every output as a research hypothesis.

## Maintainer And Scope

- Upstream author: `TerribleCookie`.
- QuantSkills maintainer: `abgyjaguo`.
- Repository: `https://github.com/quantskills/skill-factor-mining-pandaai`.
- License: GNU General Public License v3.0 only (`GPL-3.0-only`).
- Scope: research and education only. Do not present generated factors,
  backtests, or rankings as investment advice or guaranteed performance.

## Prerequisites

- Python 3.10 or later.
- `pandaai-cli` 0.1.2 or a compatible release.
- `pdfplumber` when the source is a PDF.
- A PandaAI account for platform operations.

Install dependencies only when needed:

```bash
python -m pip install pandaai-cli pdfplumber
```

For authentication, ask the user to run `PandaAI experimenter WorkBuddy interactive login entry` interactively.
Never request, print, store, or pass the user's phone number, password, token,
or config file contents through the conversation or repository.

## Select A Mode

- **Blind mining**: use when no source document is supplied or the user asks AI
  to lead discovery from PandaAI data. Read
  `references/blind_mining_workflow.md` before generating candidates.
- **Document extraction**: use when a paper, report, PDF, DOCX, or source text
  grounds the factor ideas. Follow the document workflow below.

If the request is ambiguous, infer document extraction only when a source is
present; otherwise select blind mining and state that choice.

## Shared Platform Rules

1. Read `references/pandaai_cli_reference.md` before translating formulas or
   running platform commands.
2. Prefer `--formula` over Python `--code`. Start with confirmed fields:
   `open`, `high`, `low`, `close`, `volume`, and `amount`.
   For standard quantitative transformations in Python mode, read
   `references/quant_operator_mapping.md` and generate snippets with
   `scripts/pandaai_quant_operators.py`.
3. Present formulas, direction, date range, adjustment cycle, candidate count,
   and expected compute use before platform execution.
4. Use `scripts/pandaai_cli_wrapper.py` for platform operations. Creating or
   running factors requires an explicit user request or approval.
5. Report exact configuration, billing returned by the platform, errors, and
   research limitations.

## Document Extraction Workflow

1. Read the supplied PDF, DOCX, or text and identify every candidate factor's
   source passage, formula, intended direction, economic rationale, lookback,
   rebalance interval, and universe assumptions.
2. Reject any factor that cannot be reproduced from the available document or
   supported PandaAI fields. Clearly label any inferred formula or parameter.
3. Simplify long nested expressions
   and avoid unsupported neutralization or cross-sectional transforms.
4. Present the proposed formula, direction, date range, and rebalance interval
   to the user before spending platform compute. Do not silently use defaults
   when they materially affect interpretation.
5. Use `scripts/pandaai_cli_wrapper.py` to create or inspect factors. Run a
   backtest only when the user asked for platform execution.
6. Report the exact data source, universe, dates, rebalance interval, factor
   direction, fees/slippage assumptions if available, and all platform errors.
7. Interpret IC, grouped returns, Sharpe ratio, annualized return, and maximum
   drawdown as historical diagnostics, not forecasts.

## Blind Mining Workflow

1. Define the search contract: sample and holdout dates, adjustment cycle,
   maximum candidates or compute budget, field source, target families, and exclusions.
2. Read `references/field_sources.md`. Normalize Excel/TXT/JSON/direct fields
   with `scripts/pandaai_field_catalog.py`; use documented market fields when
   the user requests pure blind discovery or supplies no field source.
3. Inspect existing factors with `list` to avoid duplicates. Check `balance`
   before proposing platform execution.
4. Run the three-stage genetic engine in `scripts/blind_mining_engine.py`:
   stage 1 combines fields with base mechanisms; stage 2 evolves time-series transforms;
   stage 3 evolves cross-sectional transforms. Use platform-native formulas
   and let the ledger drive selection, crossover, mutation, and deduplication.
5. Record every candidate in a JSONL ledger with a stable ID, formula,
   direction, hypothesis, family, parameters, run IDs, metrics, and decision.
6. After user approval, execute a batch with `blind_mining_runner.py --execute`.
   Rank with IC,
   Rank IC, IC IR, statistical evidence, grouped-return monotonicity, Sharpe,
   return, and drawdown; never optimize one metric alone.
7. Evolve winners by changing one mechanism at a time and preserve diversity
   across at least two families. Record failures rather than silently replacing
   them.
8. Validate promoted candidates on a holdout window and a neighboring parameter
   or adjustment cycle. Stop at the approved budget or the reference stop rules.

## Wrapper Examples

```bash
python scripts/pandaai_cli_wrapper.py create \
  --formula "close/ref(close,5)-1" \
  --name "five-day-momentum" \
  --start-date 20240101 \
  --end-date 20241231 \
  --adjustment-cycle 5 \
  --factor-direction 1

python scripts/pandaai_cli_wrapper.py run <factor-id>
python scripts/pandaai_cli_wrapper.py result <run-id>

python scripts/blind_mining_candidates.py --count 8 --seed 1

python scripts/blind_mining_engine.py --stage 1 --population 8 --output stage1.json
python scripts/pandaai_field_catalog.py --input fields.xlsx --output fields.json
python scripts/blind_mining_engine.py --stage 1 --field-catalog fields.json \
  --population 8 --output stage1.json
python scripts/blind_mining_runner.py --batch stage1.json --ledger runs.jsonl \
  --start-date 20240101 --end-date 20251231 --adjustment-cycle 5 --execute
python scripts/blind_mining_engine.py --stage 2 --parent-stage 1 \
  --ledger runs.jsonl --population 8 --output stage2.json
```

On Windows, keep `--json` enabled; the wrapper adds it automatically.

## Research Contract

- Data source: PandaAI platform A-share daily market data. Confirm current
  available fields and coverage in the platform before use.
- Default universe: PandaAI's default Shanghai/Shenzhen A-share universe.
- Grouping: 10 cross-sectional groups according to the current CLI contract.
- Default date range: approximately the latest 60 days; never use this implicit
  default for blind mining or meaningful research.
- Rebalance interval: 1-10 trading days, defaulting to 1.
- Costs and tradability: do not assume fees, slippage, limit-up/limit-down,
  suspensions, survivorship treatment, or point-in-time fundamentals are
  handled unless the returned configuration proves it.

## Known Limitations

- Formula mode may not support industry neutralization or cross-sectional
  standardization.
- Python code factors may fail with platform error `10075`.
- Long nested formulas may also trigger platform validation errors.
- Paper assumptions, publication timing, and A-share market behavior may not
  match the selected test period.
- Short samples, repeated trials, data snooping, and omitted transaction costs
  can materially overstate performance.
- The platform is an external service; commands, fields, pricing, compute
  charges, and availability may change.

## Cross-Runtime Use

Keep the core workflow runtime- and model-independent. It requires only an AI
that can read Markdown, inspect local files, and execute `python`/`pandaai-cli`.
Do not assume a particular model, tool-call schema, subagent system, memory API,
or vendor-specific feature.

- If a runtime supports `SKILL.md`, install this folder unchanged and invoke it
  using that runtime's skill mechanism.
- If native skill discovery is unavailable, give the AI
  `agents/portable-loader.md` with the real skill-root path.
- Treat files such as `agents/openai.yaml` and `agents/cursor-rule.mdc` as thin
  optional adapters only. They must not contain unique research logic.
- Keep all portable behavior in `SKILL.md`, `references/`, and `scripts/`.

## References

- `references/pandaai_cli_reference.md`: CLI commands, parameters, and result
  shape based on PandaAI CLI 0.1.2.
- `references/blind_mining_workflow.md`: autonomous search loop, evaluation,
  ledger, and stop conditions.
- `references/quant_operator_mapping.md`: verified, approximate, conditional,
  and unsupported quantitative-operator mappings for PandaAI.
- `references/field_sources.md`: Excel/TXT/JSON/direct/pure-blind field input
  contract, normalization, provenance, and safety rules.
- `scripts/pandaai_cli_wrapper.py`: JSON-oriented command wrapper.
- `scripts/blind_mining_candidates.py`: deterministic diversified seed-batch
  generator with ledger-aware deduplication.
- `scripts/blind_mining_engine.py`: three-stage native-formula genetic search,
  multi-objective fitness, elitism, crossover, mutation, validation, and dedup.
- `scripts/blind_mining_runner.py`: approved batch executor and compact metric
  ledger writer; requires the explicit `--execute` safety switch.
- `scripts/pandaai_quant_operators.py`: machine-readable native operator
  catalog, expression wrapper, and validator used by the genetic engine.
- `scripts/pandaai_field_catalog.py`: dependency-light field importer and
  normalizer for spreadsheets, text, JSON, direct names, and pure-blind mode.
