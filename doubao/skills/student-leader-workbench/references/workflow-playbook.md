# Workflow Playbook

## Scenario Diagnosis
1. Identify the artifact type requested by the user.
2. Extract facts: who, what, when, where, why, constraints, audience, tone, source materials.
3. Mark missing facts as `待确认` instead of inventing them.
4. Choose the output template and execute the corresponding path.

## Combination Event Operating Table
Use this path when the request mixes activity planning with roster, notice, guest, venue, budget, safety, or minutes.

### 1. Facts and Conflicts Ledger
Always start by separating:
- `已确认`: facts directly supported by user input.
- `冲突`: two facts cannot both be true. Examples: "10 天后" conflicts with a named date; venue capacity below expected attendance; budget below must-have costs.
- `待确认`: missing but execution-critical facts.
- `确认人/方式`: who should confirm and how.

### 2. Constraint Checks
Run a compact check table:

| 约束 | 当前值 | 判断 | 处理 |
| --- | --- | --- | --- |
| 容量 | expected attendance vs venue capacity | pass/risk/fail | reserve backup / cap registration |
| 时间 | start/end/curfew/deadline | pass/risk/fail | revise schedule |
| 预算 | must-have total vs budget | pass/risk/fail | cut optional items |
| 排班 | availability / max continuous duty / role limits | pass/risk/fail | assign backup |
| 审批安全 | guest, food, venue, emergency | pass/risk/fail | owner + deadline |
| 无障碍隐私 | access needs, captions, data collection | pass/risk/fail | accommodation / minimization |

### 3. Assignment Table Is Mandatory
For execution tasks, use exactly these four columns at minimum: `负责人`, `截止时间`, `交付物`, `确认方式`. Add `状态/备注` only after those four.

### 4. Volunteer Scheduling
When availability or role restrictions are provided:
- State scheduling rules before the table.
- Avoid assigning people to unavailable slots or forbidden roles.
- Flag any gap instead of silently overbooking.
- Include a fairness note: continuous duty, repeated roles, and backup coverage.

### 5. Closure
Finish with send-ready notice/copy when needed, then meeting-minutes or follow-up templates. The user should be able to send, assign, or confirm immediately.

## Evaluation and Ledger Path
Use this path when the task involves award or grant review, cadre assessment, second-class-credit补录, dormitory violation follow-up, reimbursement, attendance, voting, or any table where each row can affect a person.

1. Preserve source granularity. Build a row-level `原始明细追溯表` before writing the summary.
2. For each person/item, keep the source value, checked value, rule applied, issue tag, conclusion, and next action. Use desensitized labels when needed, but do not collapse evidence into only "优秀/良好/需补材料" counts.
3. Then add a `结论汇总表` with category counts, proportion limits, threshold checks, and owner/action.
4. If the user asks for public copy, separate public announcement from internal audit details. The public copy should minimize personal information; the internal trace table should remain available for adviser review.
5. If any source row has contradiction, missing signature, abnormal score, duplicate claim, policy uncertainty, or privacy risk, mark it as `待复核` instead of silently deciding.

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

For student organization execution, prefer Chinese operational columns: `负责人`, `截止时间`, `交付物`, `确认方式`, `状态`, `备注`.

## Domain-Specific Outputs
- 通知/群公告
- 活动策划案
- 排班表/分工表
- 会议纪要
- 执行清单与催办话术

## Quality Standard
A strong output is specific enough to use today, but honest about missing facts. It should reduce the user's next action to editing, confirming, or sending.
