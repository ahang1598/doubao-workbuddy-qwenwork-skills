# 输入规格

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| deal_context | object | 是 | 交易背景（轮次/估值/投资额/持股比例/公司信息） |
| right_types | list | 是 | 需设计的权利类型（R1-R20子集或全部） |
| investor_preferences | text | 否 | 投资方特殊诉求 |
| founder_constraints | text | 否 | 创始方已知约束 |

## 输入模式

- Mode A：全面设计（20类全部）
- Mode B：专项设计（指定权利类型子集）
- Mode C：模板获取（仅获取标准模板+可调参数）
