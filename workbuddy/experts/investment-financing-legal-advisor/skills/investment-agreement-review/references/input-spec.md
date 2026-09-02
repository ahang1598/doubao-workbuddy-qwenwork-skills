# 输入规格

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | enum | 是 | review/search/rewrite/design_remediation |
| agreement_text | text/file | 条件必填 | 协议全文（PDF/Word/文本） |
| agreement_type | enum | 条件必填 | SPA/SHA/capital_increase/equity_transfer |
| rule_groups | list | 否 | 启用规则组（默认全部：VA/GOV/EX/FP/IR/MR） |
| search_query | text | 条件必填 | 检索问题（search时必填） |
| rewrite_instructions | text | 条件必填 | 改写指令（rewrite时必填） |
| remediation_context | text | 条件必填 | 处置背景（design_remediation时必填） |

## 协议解析

审查/检索/改写前须先解析协议→结构化JSON。详见 `合同解析引擎.md`。

- 支持格式：PDF（可复制）/ Word / 纯文本
- 解析失败→提示用户提供可复制文本或Word版
- 中英文双语协议均支持
