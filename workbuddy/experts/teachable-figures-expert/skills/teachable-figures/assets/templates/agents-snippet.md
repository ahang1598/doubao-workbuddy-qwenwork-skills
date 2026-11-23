# Snippet for AGENTS.md / CLAUDE.md

Paste the block below into the project's `AGENTS.md` (Codex and others) or `CLAUDE.md` (Claude Code), so every session consults the learner workspace before building a figure. Change the path if the workspace lives elsewhere.

```markdown
## Teachable figures workspace

Before creating or changing any teachable figure, read these files in `teachable-figures/`:

- `LEARNER.md` — who the learner or class is, prior knowledge, misconceptions, preferences, accessibility needs
- `LEARNING-PLAN.md` — knowledge points, prerequisites, status, and linked lessons
- `LESSONS.md` — every lesson already created

Use them to skip questions they already answer, to link the new figure to earlier lessons, and to choose the audience build (presenter or self-learner). After delivering a lesson, update all three files following the skill's `references/learner-workspace.md`. Keep their headings and columns unchanged. Never record names, contact details, schools or raw audio. The user may edit or delete any entry.
```
