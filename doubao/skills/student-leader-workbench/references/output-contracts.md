# Output Contracts

## Required Artifact Fields
- 通知/群公告
- 活动策划案
- 排班表/分工表
- 会议纪要
- 执行清单与催办话术

## Minimum Quality Bar
- The result must match the user's context and audience.
- The result must include concrete wording, table rows, schedule, or checklist items when applicable.
- The result must not be only a framework unless the user explicitly asks for a framework.
- The result must label unknown facts and assumptions.

## Complex Execution Contract
If the user asks for a compound student-organization task, the final answer is incomplete unless it contains:

- A `事实/冲突台账` with at least one row for every conflicting or missing execution-critical fact.
- A `约束校验表` covering time, venue/capacity, budget, roster, approval/safety, accessibility/privacy when relevant.
- A task table whose first four execution columns are exactly `负责人`, `截止时间`, `交付物`, `确认方式`.
- A volunteer roster or scheduling note that states availability constraints, forbidden roles, continuous-duty limit, and unresolved gaps.
- At least one send-ready artifact when the requested outcome includes notice, announcement, follow-up, or minutes.

Do not remove these sections because the user says "快一点"; compress them instead.

## Detail Preservation Contract
The real comparison report showed that the Skill can over-compress evaluative or roster-heavy work into a summary. When the input contains scoring, rankings, candidate lists, second-class-credit applications, award reviews, dormitory ledgers, or any person-by-person decision table, include both:

- `结论汇总表`: grouped conclusions, counts, limits, and recommended actions.
- `原始明细追溯表`: one row per person/item with source fields, calculated or checked fields, risk tags, and the basis for the conclusion.

Never replace the detailed trace table with only a level summary. If privacy is sensitive, desensitize identifiers but keep enough row-level evidence for a class adviser or officer to audit the decision.

## Final Review Checklist
- Trigger matched: yes/no.
- Required inputs complete or visibly marked.
- Deliverables present.
- Tone fits the audience.
- No fabricated fact.
- No unsafe or non-compliant instruction.
- User can take a next action immediately.
- Complex execution tasks include conflict ledger, constraint checks, mandatory four-column assignment table, roster fairness, and closure artifact.
- Roster/evaluation tasks preserve row-level traceability in addition to summary conclusions.
