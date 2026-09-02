# PandaAI Blind Mining Workflow

## Contents

1. Research contract
2. Candidate generation
3. Platform loop
4. Evaluation and promotion
5. Ledger schema
6. Stop conditions

## Research contract

Blind mining means AI-led hypothesis search using PandaAI's A-share data and
factor-analysis results. It does not mean unconstrained random formula search.
Use only fields confirmed by the current platform. Start with the documented
daily fields `open`, `high`, `low`, `close`, `volume`, and `amount`; treat any
additional field as unavailable until a platform create/run proves otherwise.

Before spending compute, obtain or state:

- start/end dates and at least one holdout period;
- adjustment cycle and factor direction;
- maximum candidates or compute budget;
- target families and exclusions;
- experiment ledger path.

Never turn one short-sample winner into a submission recommendation.

## Three-stage genetic search

Use `scripts/blind_mining_engine.py` as the primary loop so candidate creation,
deduplication, fitness, elitism, crossover, mutation, and promotion happen in
Python rather than conversational tokens.

1. **Stage 1 — field/base discovery:** sample user-supplied or default fields
   across categories and evolve raw, signed-power, ratio, spread, and product
   mechanisms. Preserve field provenance in every candidate.
2. **Stage 2 — time series:** promote stage-1 elites and evolve delay,
   delta, rolling mean/std/min/max/rank/z-score, and linear-decay transforms.
3. **Stage 3 — cross section:** promote stage-2 elites and evolve rank, z-score,
   scale, and winsorization transforms. Read `quant_operator_mapping.md` first.

Smoke-test each approximate operator by itself before allowing it into a paid
population. Do not enable group operators without confirmed point-in-time group
data from PandaAI.

Run multiple generations inside a stage when the approved budget permits. Do
not promote by in-sample Sharpe alone. The engine uses a conservative composite
fitness and keeps the raw metrics in the ledger.

Use the bundled deterministic generator as a seed bank:

```bash
python scripts/blind_mining_candidates.py --count 8 --seed 1
```

The older candidate generator remains a lightweight seed bank. Prefer the
genetic engine for full blind mining. Let the AI modify the gene/operator space
only when several generations stall or platform compatibility requires it.

## Platform loop

1. Check `balance` and show the batch plus dates/cycle to the user.
2. Create and run candidates only after explicit platform-execution approval.
   Use `scripts/blind_mining_runner.py`; it refuses to run without `--execute`.
3. Record create failures and platform errors; do not silently mutate failed
   formulas until they pass.
4. Retrieve full results for successful runs.
5. Compare candidates within families and across families.
6. Generate the next batch from the scored ledger. The Python engine handles
   elitism, crossover, mutation, stable IDs, and previously-seen deduplication.
7. Re-test promoted candidates on a holdout window and at one neighboring
   adjustment cycle.

Run each candidate through `scripts/pandaai_cli_wrapper.py`; do not put account
credentials in commands or the ledger.

## Evaluation and promotion

Treat these as diagnostics rather than universal hard thresholds:

- prefer non-trivial absolute IC/Rank IC with consistent sign;
- prefer higher IC IR and meaningful t-statistics/lower p-values;
- require broadly monotonic grouped returns rather than one extreme group;
- compare Sharpe and annualized return with maximum drawdown;
- reject results dominated by a few dates, tiny samples, or implausible zero
  drawdown;
- penalize complexity and repeated parameter trials;
- do not compare directions without normalizing the expected sign.

Promote only candidates that survive holdout and neighboring-parameter checks.
Preserve at least two different factor families to prevent search collapse.

## Ledger schema

Store one JSON object per line. Recommended fields:

```json
{
  "candidate_id": "stable hash",
  "generation": 1,
  "family": "momentum",
  "formula": "close/ref(close,10)-1",
  "factor_direction": 1,
  "hypothesis": "medium-term continuation",
  "parameters": {"lookback": 10},
  "sample": {"start": "20240101", "end": "20251231", "cycle": 5},
  "factor_id": null,
  "run_id": null,
  "status": "proposed",
  "metrics": {},
  "error": null,
  "decision": "pending"
}
```

Do not store tokens, passwords, phone numbers, or config contents.

## Stop conditions

Stop when the approved candidate/compute budget is exhausted, balance is low,
platform failures repeat, all families stall for two generations, or a promoted
candidate passes the requested validation. Report both winners and failures.
