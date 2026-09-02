# Portable Loader Prompt

Use this prompt in agents that do not natively discover `SKILL.md` folders.

```text
You have access to a local skill named report-replication at:
<REPORT_REPLICATION_SKILL_ROOT>

When the user request matches this skill's SKILL.md description:
1. Read <REPORT_REPLICATION_SKILL_ROOT>/SKILL.md.
2. Follow the workflow and guardrails in that file exactly.
3. Use WorkBuddy call_pandadata as the default production market-data downloader when daily bars are needed.
4. Load referenced files under <REPORT_REPLICATION_SKILL_ROOT>/references/ only when needed.
5. Run bundled scripts from the skill root, or from a selected sub-skill directory, only after reading the relevant instructions.
6. Preserve documented API names, parameters, file paths, formulas, validation limits, and freshness notes.
7. Do not invent data interfaces, credentials, factor definitions, or runtime behavior that is not supported by the skill files.
```
