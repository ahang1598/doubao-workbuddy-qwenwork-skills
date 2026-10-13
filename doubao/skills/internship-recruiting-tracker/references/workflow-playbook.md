# Workflow Playbook

## Scenario Diagnosis
1. Identify the artifact type requested by the user.
2. Extract facts: who, what, when, where, why, constraints, audience, tone, source materials.
3. Mark missing facts as `待确认` instead of inventing them.
4. Choose the output template and execute the corresponding path.

## Deadline and Limit Rules
- For every deadline, preserve `岗位编号`, `公司`, `原始时区`, `当地截止`, `北京时间`, `剩余小时`, `来源/更新时间`, and `风险提醒`.
- For expired roles, keep the ID and reason in an exclusion table instead of deleting them.
- For platform limits, compute dates explicitly: `被拒日期`, `同岗冷却结束日`, `90天禁投截止日`, `剩余机会`, and `是否与正式岗分开计数`.
- Separate web application deadline, written test, info session, AI interview, and interview-start reminders; do not merge them into one generic date.

## Resume and Interview Depth
- Resume review should cover PII minimization, ATS parsing, truthful quantification, subjective praise vs evidence, AI-polish distortion, and scam/fee warning.
- When mentioning authority, name the dimension or source type such as university career center guidance; do not imply legal advice.
- Interview package default depth: 8 role-specific questions, 2 STAR stories, AI interview high-frequency prompts, group-discussion strategy when relevant, and a复盘/跟进 table.

## Templates

### One-Page Plan
- 背景：一句话说明任务和目标。
- 关键信息：对象、时间、地点、负责人、来源。
- 行动方案：3-6 个步骤，每步有产物或验收方式。
- 风险与待确认：只列真实影响执行的内容。

### Script or Copy
- 开头：明确身份、场景和目的。
- 主体：2-3 个证据点或利益点。
- 结尾：行动号召、确认方式或后续安排。

### Checklist/Table
Columns should usually include: item, owner, deadline, source/evidence, status, note.

## Domain-Specific Outputs
- 岗位周报
- 投递计划
- 简历修改建议
- 面试题库
- 跟进提醒清单

## Quality Standard
A strong output is specific enough to use today, but honest about missing facts. It should reduce the user's next action to editing, confirming, or sending.
