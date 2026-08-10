# Search 路由与预算

## 决策

- `off`：Closed-fixture、错误路由、用户禁止Search。
- `required`：当前公开事实、规则、市场数据或公开候选池是完成任务的必要输入。
- `optional`：用户材料已足够，仅需补证。
- `blocked`：对象未冻结，或缺口只能由用户提供的私有材料补齐。

`full_runtime` 运行 `scripts/search_router.py`；`agent_only` 按 `online-agent-execution-contract.md` 完成等价内联路由。`blocked` 时先澄清，不得用同名对象或行业平均替代。

用户无需主动说明是否联网。根据任务对象、材料充分性、时效性和规则依赖自主判断：

| 模式 | 当前领域判断标准 |
|---|---|
| `required` | 用户点名真实公司且需要当前财报、最新季度、价格、估值、行业或监管事实，且未提供足够的一手材料。 |
| `optional` | 用户已提供完整近期财报，但需要核对少量公司公告、交易所披露或外部竞争证据。 |
| `off` | 只做方法、模板、纯计算，或用户提供封闭材料并要求仅据此分析。 |
| `blocked` | 公司或证券身份不明确，或关键结论依赖用户未提供的内部模型、预测和交易数据。 |

真实上市公司对象已冻结、用户未提供足够近期一手材料且任务不是方法模板/封闭材料时，默认 `required`。不得依赖“财务、年报、最新”等关键词是否出现。

执行前写入内部 `search-decision.json`，至少记录模式、理由、证据缺口、预算和来源顺序；该文件不向用户展示。

## 当前领域预算

- `required` 最多调用 5 次，`optional` 最多 2 次；这是硬上限，不得发起第 6 次或第 3 次调用。
- 工具按 Claim 路由，不为满足形式而各调用一次。工具名仅限 `seed_finance_search` 与 `general_search`；参数以宿主 schema 为准，不得发明。
- 首次调用由首要证据槽决定：标准化金融字段可先用 `seed_finance_search`；公司自定义指标、正式指引、合同/权属、监管/交易状态和项目条件先用 `general_search`。至少保留 1 次调用用于失败 Claim 修复。
- 需要一手材料且首次只得到媒体/聚合结果或官方入口时，下一次相关调用优先使用官方域名、报告标题、期间和单一指标定向修复。
- 当前财务、行情、一致预期、估值和同口径金融字段使用 `seed_finance_search`；监管/交易所/公司 IR 原文、一般经营与竞争事实使用 `general_search`。
- Seed标准化字段满足提供方、对象/代码、期间/as_of、字段、币种、单位、reported/estimate和无冲突契约时，可作为 `authoritative_financial_database` 直接支持该字段，不强制重复搜索官方PDF。
- `seed_finance_search` 不可用或失败时回退仅用 `general_search`。
- 来源顺序：`regulator_filing` → `company_ir` → `official_transcript` → `reputable_secondary`。
- 查询阶段：
1. `identity_period_and_first_party_anchor`
2. `professional_financial_fields`
3. `company_type_and_competition`
4. `claim_specific_repair`

预算是上限，不是目标。证据契约满足后立即停止。

## 查询原则

1. 一次查询只解决一个主要证据缺口；允许收入与毛利等紧密关联字段，不允许混入多个独立经营、用户、渠道或竞争问题。
2. 查询词通常包含公司/代码、市场、单一报告期或 as-of、单一 metric/doc type/Claim 和所需来源角色。
3. 先原始文件，再解释材料；不得反向用媒体数字覆盖原始文件。
4. 搜索失败时记录缺口，不扩大到相邻对象。
5. 数据库数字、库内估算和公司披露分开标注；不得把数据库数字伪装成原始公告或把估算写成公司披露。
6. 每轮写 `query_log`、`evidence_atoms`、`coverage_gaps` 并同步 claim ledger。
7. 比较或合并前核对对象、期间、地域、品类边界、分母、指标类型、币种、单位和 reported/estimate；任一关键维度不一致时不得拼区间、排名或倍数。
8. 二手来源发现关键数字后继续追溯底层一手材料；无法追溯时只作待核验线索。
9. 工具 transport status 与证据槽 evidence status 分开；调用成功不代表目标字段已覆盖。
10. 多家二手来源重复同一说法不会升级来源等级，关键 Claim 仍标 `provisional`；但满足权威金融数据库契约的标准化Seed字段不是普通二手转述。
11. 每次调用前记录 calls_used/calls_remaining；预算耗尽后不得继续搜索。

## 调用与停止

- `closed_fixture`、`off`、纯计算和用户禁搜时调用次数为 0。
- 关键槽位已覆盖、连续查询重复、缺口只能由私有材料补齐或达到预算时停止。
- `seed_finance_search` 不可用只触发 P2 回退和局部缺口，不触发全局拒答。
- 工具返回无文档或无有效字段时状态为 `empty`，不得只因调用本身成功而标记为 covered。
