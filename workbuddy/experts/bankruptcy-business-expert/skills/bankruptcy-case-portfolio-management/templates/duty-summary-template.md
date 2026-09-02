# 破产管理人履职汇总报告

> 报告期间：{{period_start}} 至 {{period_end}}
> 生成时间：{{generated_at}}
> 案件总数：{{total_count}}（进行中 {{active_count}} / 已结案 {{closed_count}}）

---

## 履职完成度总览

| 案件ID | 债务人 | 程序类型 | 完成度 | 关键风险 |
|--------|--------|----------|--------|----------|
{{#each cases}}
| {{case_id}} | {{debtor_short_name}} | {{procedure_type_cn}} | {{completion_rate}}% | {{key_risks}} |
{{/each}}

---

## 团队成员任务分配矩阵

| 成员 | {{#each case_ids}}{{this}} | {{/each}}合计任务数 |
|------|{{#each case_ids}}------|{{/each}}------------|
{{#each team_matrix}}
| {{member_name}}（{{role}}） | {{#each tasks}}{{this}} | {{/each}}{{total_tasks}} |
{{/each}}

---

## 履职风险提示

| 风险等级 | 案件ID | 风险描述 | 建议措施 |
|----------|--------|----------|----------|
{{#each risks}}
| {{level_icon}} {{level_cn}} | {{case_id}} | {{description}} | {{suggestion}} |
{{/each}}

---

## 履职统计

| 统计项 | 数值 |
|--------|------|
| 本期间新收债权申报 | {{new_claims}}份 |
| 本期间完成债权审查 | {{reviewed_claims}}份 |
| 本期间召开会议 | {{meetings_held}}次 |
| 本期间提交法院文件 | {{court_filings}}份 |
| 本期间完成履职节点 | {{completed_nodes}}个 |
| 本期间新增案件 | {{new_cases}}件 |
| 本期间结案 | {{closed_cases}}件 |

---

## 程序合规检查

| 检查项 | 合规情况 | 备注 |
|--------|----------|------|
| 债权申报期限合规 | {{claim_deadline_compliance}} | {{claim_notes}} |
| 债权人会议期限合规 | {{meeting_deadline_compliance}} | {{meeting_notes}} |
| 重整计划提交期限合规 | {{reorg_deadline_compliance}} | {{reorg_notes}} |
| 分配方案公告期限合规 | {{distribution_deadline_compliance}} | {{distribution_notes}} |
| 履职报告提交期限合规 | {{report_deadline_compliance}} | {{report_notes}} |

---

## 下一步工作计划

| 优先级 | 案件ID | 计划事项 | 预计完成日期 | 负责人 |
|--------|--------|----------|--------------|--------|
{{#each next_plans}}
| {{priority_icon}} {{priority_cn}} | {{case_id}} | {{plan}} | {{target_date}} | {{assignee}} |
{{/each}}

---

## 说明

1. 本报告基于案件工作空间数据自动生成，可能存在遗漏或偏差
2. 履职完成度按法定履职节点计算，等权重处理
3. 风险提示仅供参考，具体风险判断由管理人作出
4. 本报告不构成对管理人履职情况的正式评价

---

*本报告由 bankruptcy-case-portfolio-management 技能自动生成*
