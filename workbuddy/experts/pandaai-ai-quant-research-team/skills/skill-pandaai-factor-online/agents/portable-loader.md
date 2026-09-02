# Portable Runtime Loader

For Hermes, OpenClaw, and other runtimes without a native skill manifest:

1. Resolve this repository directory and read `SKILL.md` before any PandaAI factor action.
2. Use `SKILL.zh-CN.md` when the user works in Chinese.
3. Follow the Core Workflow exactly: preflight, resolve login, report balance, agree parameters and
   budget, show a probe batch, then wait for approval before `factor_run`.
4. Treat `references/competition_rules.md` and `scripts/competition_proxy.py` as opt-in advanced
   material only when the user requests competition-preparation analysis.

Never copy private CLI credentials into repository files, prompts, or chat. This is research
guidance, not an investment recommendation or an official PandaAI integration.
