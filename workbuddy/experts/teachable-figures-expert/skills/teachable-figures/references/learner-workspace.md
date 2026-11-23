# Learner workspace: a local lookup the agent reads first

Lessons are more useful when they build on what the learner already knows and on the figures already made. The workspace is three plain Markdown files the user owns. Any coding agent (Claude Code, Codex, others) reads them at the start of a session and updates them after each lesson. It is a local lookup, not a database or a learner model, and it never leaves the user's machine unless they move it.

## Files

| File | Holds | Template |
| --- | --- | --- |
| `LESSONS.md` | Registry of every 2D/3D lesson created | [assets/templates/LESSONS.md](../assets/templates/LESSONS.md) |
| `LEARNER.md` | Learner profile, or a **class profile** for teachers | [assets/templates/LEARNER.md](../assets/templates/LEARNER.md) |
| `LEARNING-PLAN.md` | Knowledge-point graph: prerequisites, objectives, misconceptions, status, linked lessons | [assets/templates/LEARNING-PLAN.md](../assets/templates/LEARNING-PLAN.md) |

A filled example for one self-learner is in [assets/templates/sample/](../assets/templates/sample/).

## Where it lives

Default: a `teachable-figures/` folder at the root of the user's project, holding `LESSONS.md`, `LEARNER.md` and `LEARNING-PLAN.md`. The user may choose another path. If they do, record it in their `AGENTS.md` / `CLAUDE.md` with the [snippet](../assets/templates/agents-snippet.md). A teacher with several classes uses one folder per class, or one `LEARNER.md` per class inside a shared folder. Each `LEARNER.md` names the group it describes.

## Protocol

1. **Session start:** look for the workspace before asking anything.
   - **If present:** read all three files. Use them to skip questions already answered (audience, language, prior knowledge), to link the new lesson to earlier ones, and to suggest the next knowledge point.
   - **If absent:** offer to create it from the templates. Create it only with the user's consent. Declining is fine; then work as usual and do not ask again in the same session.
2. **Interview (guided mode):** ask only what the files leave open. For a self-learner whose prior knowledge for this topic is unknown or stale, run the 2–4 question probe (SKILL.md §0). Record the answers as evidence, not as verdicts.
3. **Plan:** if `LEARNING-PLAN.md` has no node for the requested concept, propose a small subgraph (3–7 points): the target point, its prerequisites, and one or two next points. Ask the user to accept, edit or skip it. Never build a whole course; one figure per mechanism, chosen with the user.
4. **After delivery,** update the files and tell the user what changed:
   - `LESSONS.md`: add or update the lesson row.
   - `LEARNING-PLAN.md`: link the lesson to its point(s); set the point's status to `introduced` (not `mastered`).
   - `LEARNER.md`: add observations that came from this session, such as probe answers, the learner's stated prediction, or misconceptions they expressed, each with a date and source.
5. **Evidence from an evolving artifact** (see [evolving-artifacts.md](evolving-artifacts.md)): summarise exported evidence into `LEARNER.md` as observations with uncertainty. Do not paste raw logs.

## Stable schemas

Generation and questions depend on these files, so their structure must stay stable:
- Keep the headings and table columns exactly as in the templates. Add columns only at the end, never rename them.
- Ids are lowercase kebab-case and never reused: lesson ids (`cone-sections`), knowledge-point ids (`area-scales-with-square`), misconception ids (`linear-scaling`). Renaming an id means adding the new one and marking the old one `superseded-by: new-id`.
- Dates are ISO `YYYY-MM-DD`.
- Status vocabularies:
  - Lesson status: `draft`, `delivered`, `used`, `retired`.
  - Knowledge-point status: `not-started`, `introduced`, `practising`, `secure`, `needs-review`.
- `secure` requires evidence the learner produced: a correct independent-practice or transfer answer, or the teacher's judgement for a class. Operating a figure is not evidence of understanding.
- Confidence is `low`, `medium` or `high`, always paired with a source: `probed`, `stated` (by the learner or teacher), `observed` (from exported evidence), or `assumed`.

## Privacy

- **No personal identifiers:** no full names, emails, school names, photos, or ages more precise than a band (e.g. "13–14"). Use a pseudonym or "class 8B" if a label is needed.
- **Children:** record the minimum needed to choose the next figure. Prefer a class profile over individual profiles. Do not record sensitive categories (health, disability details beyond the accessibility needs the user chooses to state, family circumstances).
- **No raw audio and no transcripts of minors.** If voice input is used, keep at most a short, user-checked paraphrase of the answer.
- **The user owns the files.** They can edit or delete any line. When they correct an entry, the correction wins. Do not rebuild deleted content from memory.
- The agent never uploads, publishes or syncs the workspace on its own.

## What not to infer

Write observations, not diagnoses. Write "predicted ×2 for doubling the radius (2026-11-02, probe)", not "doesn't understand area". A hypothesis in `LEARNER.md` names its evidence and stays revisable. One answer is weak evidence, a pattern across lessons is stronger, and neither is a measurement of the learner's mind.
