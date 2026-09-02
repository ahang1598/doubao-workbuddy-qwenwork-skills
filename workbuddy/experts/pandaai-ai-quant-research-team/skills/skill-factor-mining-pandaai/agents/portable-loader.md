# Portable Loader

Use this model-neutral loader with any AI runtime that does not natively
discover `SKILL.md` folders. The runtime only needs to read files and execute
local commands. If native skill discovery is available, install the full folder
unchanged and load `SKILL.md` directly.

```text
You have access to a local skill named factor-mining-pandaai at:
<FACTOR_MINING_PANDAAI_SKILL_ROOT>

When the user asks to blind-mine factors with PandaAI or extract quantitative
factors from a paper, report, PDF, DOCX file, or text:
1. Read <FACTOR_MINING_PANDAAI_SKILL_ROOT>/SKILL.md.
2. Read <FACTOR_MINING_PANDAAI_SKILL_ROOT>/references/pandaai_cli_reference.md
   before translating formulas or using PandaAI.
3. For blind mining, also read `references/blind_mining_workflow.md`; define a
   search budget, generate diversified candidates, keep a ledger, and validate
   winners on holdout data.
4. For document extraction, extract source passages, formulas, directions,
   parameters, and assumptions. Clearly label inferences.
5. Show the proposed setup before spending platform compute.
6. Never request or expose credentials; ask the user to log in interactively.
7. Report results with data, sample, cost, limitation, and risk boundaries.
```

Example runtime placement (not an exhaustive compatibility list):

- Codex: install under a Codex skill path and invoke `$factor-mining-pandaai`.
- Claude Code: install under a Claude skill path and invoke `$factor-mining-pandaai`.
- Cursor: copy to `.cursor/skills/factor-mining-pandaai` and enable
  `agents/cursor-rule.mdc`.
- Hermes/OpenClaw: mount the folder as a local skill root or paste the loader
  above with the real path.
- Any other AI: expose the folder read-only or locally, replace the placeholder
  root in the loader, and let the AI follow the same Markdown contract.
