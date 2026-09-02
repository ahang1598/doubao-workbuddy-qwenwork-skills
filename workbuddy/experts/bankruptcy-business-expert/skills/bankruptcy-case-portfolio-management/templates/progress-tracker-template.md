# 破产案件进度跟踪

> 生成时间：{{generated_at}}

---

## 履职事项完成度

{{#each cases}}
### {{case_id}} {{debtor_short_name}}（{{procedure_type_cn}}）

| 法定履职节点 | 状态 | 完成日期 | 备注 |
|--------------|------|----------|------|
{{#each duty_nodes}}
| {{node_name}} | {{status_icon}} {{status_cn}} | {{completed_date}} | {{notes}} |
{{/each}}

**完成度：{{completed_count}}/{{total_count}}（{{completion_rate}}%）**

{{/each}}

---

## 待办事项清单

| 优先级 | 案件ID | 事项 | 截止日期 | 负责人 |
|--------|--------|------|----------|--------|
{{#each todos}}
| {{priority_icon}} {{priority_cn}} | {{case_id}} | {{task}} | {{deadline}} | {{assignee}} |
{{/each}}

---

## 阶段切换记录

| 时间 | 案件ID | 从阶段 | 到阶段 | 触发事项 |
|------|--------|--------|--------|----------|
{{#each stage_history}}
| {{timestamp}} | {{case_id}} | {{from_stage_cn}} | {{to_stage_cn}} | {{trigger}} |
{{/each}}

---

## 进度统计

| 统计项 | 数值 |
|--------|------|
| 总履职节点数 | {{total_nodes}} |
| 已完成 | {{completed_nodes}} |
| 进行中 | {{in_progress_nodes}} |
| 未开始 | {{pending_nodes}} |
| 整体完成度 | {{overall_completion}}% |

---

## 状态说明

| 图标 | 含义 |
|------|------|
| ✅ | 已完成 |
| 🔄 | 进行中 |
| ⬜ | 未开始 |
| ⏸️ | 暂停 |
| ❌ | 取消 |

---

*本跟踪表由 bankruptcy-case-portfolio-management 技能自动生成*
