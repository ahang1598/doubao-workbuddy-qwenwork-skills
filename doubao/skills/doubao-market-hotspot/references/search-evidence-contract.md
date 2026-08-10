# Search 证据契约

Search 后先生成 `search-evidence.json`，再运行 `scripts/search_evidence_validator.py`。

工具调用状态与证据状态分开：`transport_status=success|error`；`evidence_status=supported|provisional|conflict|empty|unsupported|blocked`。多家普通二手重复不升级supported；工具成功但目标字段为空仍为empty。

Seed合格市场/曲线/成交/consensus/标准财务暴露字段可由`authoritative_financial_database`承担，但不能支持事件身份、法规状态、辖区、生效日或适用范围。事件关键Claim未supported时禁止量化。

最终外部数字必须进入Claim ledger，情景、敏感度和影响区间需calculation与assumption记录。比较前统一对象、时区、事件窗口、基线、币种、单位和reported/estimate；事件后价格不得倒作事件前基线。原始轨迹优先宿主捕获，模型摘要不是raw。

每条 Claim 至少包含：

- `id`、`claim`、`critical`；
- 文档证据：`source_url`、`source_type`、`published_at`；
- 结构化数据库证据：`provider`、`dataset`、`record_id`、`field`、
  `as_of`，并提供底层公告 lineage 或标记为权威数据库；
- `supported`、`conflict`、`conflict_note`；
- 关键数字的 `period`、`currency`、`unit`；
- 规则类事实的适用辖区和年度。

关键 Claim 必须由监管披露、公司/交易对手一手材料、政府规则或发布机关材料承担。二手来源只能解释机制。

Validator 未通过时：

1. 预算仍有剩余：只搜索失败 Claim；
2. 预算耗尽：删除无证据精确值，改为unknown或条件式结论；
3. 不得把Validator错误隐藏在最终回复中。

## 领域硬规则

- 法规正文、合并版本、实施细则和提案必须分层，提案不得写成已生效规则。
- 关键日期、产品范围、计算公式和主管机关义务必须由法规或发布机关承担。
- 情景参数没有官方或用户依据时保留变量，不得为了情景表填入数值。
