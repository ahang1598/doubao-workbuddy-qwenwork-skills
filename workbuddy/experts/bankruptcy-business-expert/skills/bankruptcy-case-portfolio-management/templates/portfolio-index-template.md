# 破产案件索引台账

> 生成时间：{{generated_at}}
> 案件总数：{{total_count}} | 进行中：{{active_count}} | 已结案：{{closed_count}}

---

## 案件清单

| 案件ID | 案号 | 债务人 | 程序类型 | 当前阶段 | 承办团队 | 立案日期 | 状态 |
|--------|------|--------|----------|----------|----------|----------|------|
{{#each cases}}
| {{case_id}} | {{case_number}} | {{debtor_short_name}} | {{procedure_type_cn}} | {{stage_cn}} | {{team_display}} | {{filing_date}} | {{status_cn}} |
{{/each}}

---

## 状态看板

### 按程序类型分布

| 程序类型 | 数量 | 占比 |
|----------|------|------|
{{#each procedure_stats}}
| {{type_cn}} | {{count}} | {{percentage}}% |
{{/each}}

### 按阶段分布

| 阶段 | 数量 | 案件 |
|------|------|------|
{{#each stage_stats}}
| {{stage_cn}} | {{count}} | {{case_ids}} |
{{/each}}

### 按团队分布

| 负责人 | 案件数 | 案件列表 |
|--------|--------|----------|
{{#each team_stats}}
| {{leader}} | {{count}} | {{case_ids}} |
{{/each}}

---

## 筛选视图

### 进行中案件（{{active_count}}件）

{{#each active_cases}}
- **{{case_id}}** {{debtor_short_name}}（{{procedure_type_cn}}）- {{stage_cn}} - {{team_display}}
{{/each}}

### 已结案案件（{{closed_count}}件）

{{#each closed_cases}}
- **{{case_id}}** {{debtor_short_name}}（{{procedure_type_cn}}）- 结案日期：{{closed_date}}
{{/each}}

---

## 统计摘要

| 统计项 | 数值 |
|--------|------|
| 案件总数 | {{total_count}} |
| 进行中 | {{active_count}} |
| 已结案 | {{closed_count}} |
| 暂停 | {{suspended_count}} |
| 平均处理时长 | {{avg_duration}}天 |
| 最长处理时长 | {{max_duration}}天（{{max_duration_case}}） |

---

*本台账由 bankruptcy-case-portfolio-management 技能自动生成*
