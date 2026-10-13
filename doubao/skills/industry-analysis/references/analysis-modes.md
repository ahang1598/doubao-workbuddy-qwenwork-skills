# Analysis Depth And Delivery Rules

Use these rules to answer the user's task. Select analysis depth independently
of output form and domain-specific business dimensions. Apply safety and scope,
then explicit user choices, then reasoning dependencies; choose the smallest
sufficient depth. Do not choose depth from prompt length or keyword counts.

## Select Depth

- `direct`: Answer one local question with the minimum sufficient evidence and relevant limitations.
- `brief`: Resolve a focused chain of related questions, its drivers, constraints and verification signals.
- `full`: Resolve coupled judgments, cross-object comparisons or scenarios with comparable evidence, alternatives and falsification.

`deep` means `full`, not a fourth tier. Use `brief` for a focused evidence chain;
use `full` when answering requires coupled comparisons, competing explanations
or dependent scenarios. Short questions can need deep reasoning; long background
can still lead to a local answer. Do not add irrelevant analysis to fill a tier.

## Select Delivery Separately

Default to `answer`. Use `report` or `files` only when the user's intent calls for
that form; `full` does not imply either. A requested format does not by itself
increase reasoning depth. Respect requested brevity and scope, explaining any
material limit instead of silently expanding the task. All depths share evidence
quality, not mandatory chapters, a fixed length or an obligatory template.

## Use Relevant Resources

The machine-readable contract is [analysis-mode-contract.json](analysis-mode-contract.json).
For task-specific applicability and resource conditions consult
[analysis-mode-implementation.json](analysis-mode-implementation.json) only when
needed. Load only resources relevant to the selected task, not all tiers' files.
Domain-specific business dimensions may combine. If a required dimension is
missing and changes the answer, ask for the minimum clarification or explicitly
bound the answer; do not invent defaults.

## Stop And Degrade

Stop when the requested judgment, necessary support and relevant limitations
are supplied. Stop unsafe or out-of-scope work while preserving independent
supported parts. Missing evidence weakens only conclusions that depend on it;
keep unknown facts unknown. Do not fabricate sources, calculations, tool success
or delivered files to compensate for a limitation.

Use the inline routing in SKILL.md when additional resources cannot be loaded.
Explicit zero-tool requests prohibit loading references and executing scripts.
Closed-material requests prohibit external information and search, while any
offline reading, calculation or file creation remains subject to actual user
authorization. Tool limitations constrain delivery, not the duty to be accurate.
