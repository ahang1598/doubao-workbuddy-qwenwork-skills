# 破产案件期限看板

> 生成时间：{{generated_at}}
> 预警统计：🔴 已逾期 {{overdue_count}} | 🟠 临期(7日内) {{urgent_count}} | 🟡 即将到期(30日内) {{warning_count}} | 🟢 正常 {{normal_count}}

---

## 期限节点汇总

| 案件ID | 债务人 | 节点类型 | 截止日期 | 剩余天数 | 预警级别 |
|--------|--------|----------|----------|----------|----------|
{{#each deadlines}}
| {{case_id}} | {{debtor_short_name}} | {{node_type_cn}} | {{deadline_date}} | {{days_remaining}} | {{alert_level}} |
{{/each}}

---

## 按预警级别分组

### 🔴 已逾期（{{overdue_count}}项）

{{#if overdue_count}}
| 案件ID | 债务人 | 节点 | 截止日期 | 逾期天数 |
|--------|--------|------|----------|----------|
{{#each overdue_items}}
| {{case_id}} | {{debtor_short_name}} | {{node_type_cn}} | {{deadline_date}} | {{overdue_days}} |
{{/each}}
{{else}}
无
{{/if}}

### 🟠 临期（7日内，{{urgent_count}}项）

{{#if urgent_count}}
| 案件ID | 债务人 | 节点 | 截止日期 | 剩余天数 |
|--------|--------|------|----------|----------|
{{#each urgent_items}}
| {{case_id}} | {{debtor_short_name}} | {{node_type_cn}} | {{deadline_date}} | {{days_remaining}} |
{{/each}}
{{else}}
无
{{/if}}

### 🟡 即将到期（30日内，{{warning_count}}项）

{{#if warning_count}}
| 案件ID | 债务人 | 节点 | 截止日期 | 剩余天数 |
|--------|--------|------|----------|----------|
{{#each warning_items}}
| {{case_id}} | {{debtor_short_name}} | {{node_type_cn}} | {{deadline_date}} | {{days_remaining}} |
{{/each}}
{{else}}
无
{{/if}}

### 🟢 正常（{{normal_count}}项）

{{#if normal_count}}
| 案件ID | 债务人 | 节点 | 截止日期 | 剩余天数 |
|--------|--------|------|----------|----------|
{{#each normal_items}}
| {{case_id}} | {{debtor_short_name}} | {{node_type_cn}} | {{deadline_date}} | {{days_remaining}} |
{{/each}}
{{else}}
无
{{/if}}

### ⚪ 未设定（{{unset_count}}项）

{{#if unset_count}}
| 案件ID | 债务人 | 节点类型 |
|--------|--------|----------|
{{#each unset_items}}
| {{case_id}} | {{debtor_short_name}} | {{node_type_cn}} |
{{/each}}
{{else}}
无
{{/if}}

---

## 期限更新记录

| 时间 | 案件ID | 更新内容 |
|------|--------|----------|
{{#each update_history}}
| {{timestamp}} | {{case_id}} | {{update_content}} |
{{/each}}

---

## 预警说明

| 级别 | 含义 | 建议措施 |
|------|------|----------|
| 🔴 已逾期 | 已超过法定期限 | 立即补救，向法院说明情况 |
| 🟠 临期 | 7日内到期 | 优先处理，确保按期完成 |
| 🟡 即将到期 | 30日内到期 | 提前准备，预留缓冲时间 |
| 🟢 正常 | 30日以上 | 按计划推进 |
| ⚪ 未设定 | 尚未设定期限 | 尽快确认并设定 |

---

*本看板由 bankruptcy-case-portfolio-management 技能自动生成*
