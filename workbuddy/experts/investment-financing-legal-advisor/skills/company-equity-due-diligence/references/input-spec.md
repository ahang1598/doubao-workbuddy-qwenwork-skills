# 输入规格

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| target_company | text | 是 | 目标公司全称 |
| scenario | enum | 是 | M&A/IPO/financing/partnership/post_invest/pre_startup/single_query |
| depth | enum | 否 | full/standard/quick（默认按场景自动确定） |
| mcp_available | boolean | 否 | 天眼查MCP是否可用 |
| internal_docs | text | 否 | 已提供的内部资料 |
| subsidiaries | list | 否 | 子公司清单（需逐一搜索） |

## 追问策略

- 追问≤1次：信息不足时一次性列全部缺口
- 达到上限后→列入待补充信息清单并继续执行
