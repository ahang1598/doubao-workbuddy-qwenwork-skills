# Output Contracts

## Required Artifact Fields
- 岗位周报
- 投递计划
- 简历修改建议
- 面试题库
- 跟进提醒清单
- 时区/倒计时表
- 限投冷却与排除岗位表

## Minimum Quality Bar
- The result must match the user's context and audience.
- The result must include concrete wording, table rows, schedule, or checklist items when applicable.
- The result must not be only a framework unless the user explicitly asks for a framework.
- The result must label unknown facts and assumptions.
- Deadline rows must include original timezone, local deadline, Beijing time, remaining hours, and source/update time when the source provides a deadline.
- Excluded or expired roles must keep job ID, company, deadline, and exclusion reason; do not collapse them into a count.
- Limit rules must calculate cooldown end date, no-apply-until date, remaining attempts, and whether formal/full-time applications count separately from internships.
- Resume diagnostics must cite or label multiple authority dimensions: PII minimization, ATS compatibility, achievement quantification, truthful claims, and AI-polish distortion.
- Interview packs should include at least 8 questions, 2 STAR stories, AI interview prompts, and a review/follow-up table per candidate or target role.

## Final Review Checklist
- Trigger matched: yes/no.
- Required inputs complete or visibly marked.
- Deliverables present.
- Tone fits the audience.
- No fabricated fact.
- No unsafe or non-compliant instruction.
- User can take a next action immediately.
- Timezone, excluded-role IDs, cooldown dates, and interview depth are complete when relevant.
