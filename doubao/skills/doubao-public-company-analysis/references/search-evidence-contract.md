# Search 证据契约

`full_runtime` 在 Search 后生成 `search-evidence.json` 并运行 `scripts/search_evidence_validator.py`。`agent_only` 使用同一 Claim 字段和状态语义，在交付前执行 `online-agent-execution-contract.md` 的十项内联自检；不得声称运行过不可执行的脚本。

Search 前必须先完成：

- `freeze_point`：公司 IR 与交易所/监管页已检查，记录最近完整财年、截止点前最新披露期、检查时间，以及是否存在更晚披露；
- `evidence_slots`：依据用户问题和公司类型生成 8–15 个必需槽位。每项含 id、所需事实、允许来源类型、期间、影响 claim、状态。

冻结点未通过不得进入正式分析；不得把较旧期间称为“最新”。槽位搜索在覆盖或明确 blocked 后结束，不按调用预算凑数。

P2 核心槽使用 `slot_kind` 标记 `latest_annual_report`、`latest_interim_report`、`cashflow_statement`；正文使用公司自定义现金指标时另加 `company_cash_metric_definition`。每槽记录 `availability`。可访问的一手核心槽必须先 `covered`；确实不可访问才用 `unavailable` 并记录 `access_attempt`。同行、价格或预期缺口不得触发 `global_degraded`。

每条 Claim 至少包含：

- `id`、`claim`、`critical`；
- 文档证据：`source_url`、`source_type`、`published_at`；
- 结构化数据库证据：`provider`、`dataset`、`record_id`、`field`、
  `as_of`，并提供底层公告 lineage 或标记为权威数据库；
- `supported`、`conflict`、`conflict_note`；
- 关键数字的 `period`、`currency`、`unit`；
- 比较数字的 `geography`、`category_scope`、`denominator`、`metric_type`；
- 规则类事实的适用辖区和年度。

关键 Claim 由与Claim类型匹配的来源承担：

- 标准化财务、行情、股本、汇率、明确标记的预期/估值字段：可由满足字段完整性契约的 `authoritative_financial_database` 承担；
- 公司自定义KPI、分部边界和正式指引：公司/监管/交易所一手材料；
- 合同、权属、客户、交易状态、法规、审批、项目条件：对应公司、交易对手、监管或发布机关一手材料；
- 行业份额与竞争：必须有方法、期间、地域、分母和适格第三方/一手依据。

普通二手来源只能发现线索、解释机制、提供行业背景或明确标注的外部预期；不得承担正式经营指标、交易状态、精确估值或决定性公司特异事实。

Claim 状态使用：

- `supported`：来源等级、内容和口径足以承担；
- `provisional`：只有二手转述、摘要或来源等级不足，可能正确但不能承担决定性结论；
- `conflict|empty|unsupported|blocked`：分别表示冲突、目标字段为空、证据不支持、当前能力无法补齐。

多家普通二手来源重复同一说法不会自动升级为 `supported`。关键 Claim 只有二手转述时必须标 `provisional`；最终回答按待核验事实降级，或删除其精确值。满足权威金融数据库字段契约的Seed结构化数据不属于普通媒体转述。

只有 `supported` 可以进入“已验证事实”。若所有决定性 Claim 都是 `provisional|unsupported|conflict`，最终只能给条件式方向判断和待验证假设，不得给确定性结论、精确评级或精确情景结果。

Validator 未通过时：

1. 预算仍有剩余：只搜索失败 Claim；
2. 预算耗尽：删除无证据精确值，改为unknown或条件式结论；
3. 不得把Validator错误隐藏在最终回复中。

## 冲突契约

多个结果只有在对象、期间、地域、产品/行业定义、分母、指标类型、币种、单位和 reported/estimate 均可比时，才可合并或形成区间。

口径不一致时：

1. 标记 `conflict` 并记录差异维度；
2. 不得取均值或拼成上下限；
3. 不得跨口径排名、计算倍数或声称领先幅度；
4. 分别展示定义，或选择与用户问题最匹配且来源最强的口径；
5. 仍无法消解时降低结论强度。

工具调用成功但没有返回有效文档或字段时，状态必须是 `empty`，不是 `supported`。

工具调用状态与证据槽状态必须分开：工具可以 `transport_status=success`，但目标槽仍为 `evidence_status=empty|provisional|conflict`。

## 推断契约

来源只承担其明确表达的最小事实。模型从覆盖、复购、增长、份额、授权、毛利、规模或爆款等代理指标推出竞争优势时，必须：

1. 标为 `inference`；
2. 列出支持事实；
3. 给至少一个替代解释；
4. 给可观察证伪条件；
5. 避免来源未支持的“最高、唯一、全部、几乎、必然、完全”等绝对措辞。

精确证伪阈值必须有历史分布、同行基准、管理层目标或透明计算依据；否则只写方向和观察窗口。不得从集团净利润、分部经营利润和集团现金流的简单差额推导营运资金贡献。

## 输出与计算闭环

- 最终回答中的每个外部数字、日期、比例、公司事实必须存在于 Claim 台账；台账外内容删除。
- 每个派生精确值必须有 calculation id、输入 Claim、公式、单位、币种、期间、合并范围、舍入和重算状态。
- 模型设定的增长率、汇率、利用率、折旧期或其他情景输入必须进入 assumption 台账并标明来源角色。
- 计算器只有在本任务上接收实际输入、成功退出并产生结果时，才可标记 executed；运行 `--help` 不算。
- ROE 不得替代 ROIC；现金流覆盖 CapEx 不证明新增投资维持资本回报；多年度投资承诺不得当作单年现金 CapEx。

## 领域硬规则

- 收入、净利润、CFO、CapEx、FCF、客户集中和最新季度必须由监管披露或公司IR承担。
- 先锁定财年和最新已发布季度，再取数；不得从EPS或媒体摘要倒推正式报表数字。
- 现金流桥接任一关键输入缺一手来源时，停止精确桥接并列数据缺口。
- 公司 adjusted FCF 的定义和每项调整必须来自公司正式材料，并与法定 CFO/总现金流及客户融资前后范围对账。
