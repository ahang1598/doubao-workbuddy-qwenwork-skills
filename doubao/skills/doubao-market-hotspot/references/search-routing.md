# Search 路由与预算

## 决策

- `off`：Closed-fixture、错误路由、用户禁止Search。
- `required`：当前公开事实、规则、市场数据或公开候选池是完成任务的必要输入。
- `optional`：用户材料已足够，仅需补证。
- `blocked`：对象未冻结，或缺口只能由用户提供的私有材料补齐。

先运行 `scripts/search_router.py`。`blocked` 时先澄清，不得用同名对象或行业平均替代。

用户无需主动说明是否联网。根据任务对象、材料充分性、时效性和规则依赖自主判断：

| 模式 | 当前领域判断标准 |
|---|---|
| `required` | 未提供事件原文，或需要确认事件是否发生、最新规则、实施状态、谈判进展和市场基线。 |
| `optional` | 已提供官方原文，仅需补充少量执行细则、主体暴露或市场价格证据。 |
| `off` | 封闭Fixture或用户要求只分析所附事件材料中的条件传导。 |
| `blocked` | 事件对象、版本、时间或辖区不明确，无法确定应核验的原文。 |

执行前写入内部 `search-decision.json`，至少记录模式、理由、证据缺口、预算和来源顺序；该文件不向用户展示。

## 当前领域预算

- 最多调用：4 次。
- 双通道顺序：`general_search` 先核验事件原文、状态、辖区与生效日；通过事件门禁后，`seed_finance_search` 补市场价格、曲线、成交、一致预期、公司财务暴露、机构观点和 priced-in 基线。
- `seed_finance_search` 不可用时回退仅用 `general_search`；工具名仅限 `seed_finance_search` 与 `general_search`；参数以宿主 schema 为准，不发明。
- 来源顺序：`law_or_regulation` → `issuing_authority` → `implementing_authority` → `industry_primary` → `reputable_secondary`。
- 查询阶段：
1. `original_event_and_status`
2. `consolidated_rules`
3. `implementation_details`
4. `affected_entities_and_conflicts`

预算是上限，不是目标。证据契约满足后立即停止。

## 查询原则

1. 一次查询只解决一个证据缺口。
2. 查询词包含对象、期间、文档类型和官方域名意图。
3. 先原始文件，再解释材料；不得反向用媒体数字覆盖原始文件。
4. 搜索失败时记录缺口，不扩大到相邻对象。
5. 每次结果记录 tool、query、asof、source、period、unit、currency、reported-vs-estimate；库内结果不自动等于一手来源。
6. 缺受支持的事件前市场基线时保持 `can_assess_priced_in=false`，只降级 priced-in 槽位。

完整双通道、证据台账和回退要求见 `references/seed-finance-search-routing.md`。
