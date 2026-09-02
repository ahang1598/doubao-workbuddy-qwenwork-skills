# 输入规格

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | enum | 是 | `compare_dispute_resolution` / `assess_execution` / `select_exit_path` |
| dispute_nature | text | 条件必填 | 争议性质描述（compare时必填） |
| jurisdiction | text | 条件必填 | 管辖地/仲裁地（compare时必填） |
| enforcement_target | text | 条件必填 | 执行标的描述（assess时必填） |
| exit_context | text | 条件必填 | 退出背景描述（select时必填） |
| cross_border | boolean | 否 | 是否跨境争议 |
| arbitration_clause | text | 否 | 现有仲裁条款 |
| company_status | text | 否 | 公司经营状况（影响退出路径选择） |

## 追问策略

- 追问≤1次：信息不足时一次性列全部缺口
