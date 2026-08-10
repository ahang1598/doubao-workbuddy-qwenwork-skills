# P1 执行契约

## 先探测，再取数

冻结公司、代码、交易所、截止时间与时区。先查公司 IR 和交易所/监管披露页，记录最近完整财年、截止点前最新季度，以及盘后、临时、更正披露。未完成探测时不得把任何期间称为“最新”。

## 必需证据槽位

按用户问题与公司类型生成 8–15 个槽位。每个槽位必须写明：所需事实、允许来源层级、期间、影响的 claim、状态。搜索在槽位覆盖或明确 blocked 后停止，不按轮次凑满。

财务报表数字、正式经营指标、交易状态、精确估值和决定性公司事实必须由一手披露或有底层 lineage 的权威数据库承担。二手来源只用于发现线索、行业背景和外部预期，并明确标成外部估计。

## 公司类型路由

先运行 `scripts/company_type_router.py`。支持：

- `financial_insurance`
- `retail_membership`
- `project_credit_sales`
- `manufacturing`
- `internet_platform_capital_intensive`
- `brand_ip_licensing`
- `general`

必须覆盖指标包中的指标，或逐项记录 blocked 及其局部影响；禁止套用该类型不适用的财务或估值方法。

## 局部能力门

分别判断 `can_assess_business`、`can_assess_competition`、`can_assess_financial_quality`、`can_compare_peers`、`can_value`、`can_state_investment_view`。一个能力为 false 只降级对应 claim，不得阻断无关章节。

unknown 必须包含缺什么、影响哪些 claim、下一份去哪里找。不得用 unknown 代替可完成的机制判断或条件结论。

## 三级估值

- `full`：价格、时点、股本、净债务、预测和方法输入齐全，输出可复算估值及隐含假设。
- `degraded`：缺部分输入，不给目标价；仍给方法、变量关系、当前价格隐含的方向性经营要求与 blocked inputs。
- `blocked`：对象、证券或价格口径不明；只阻断估值，并明确最小恢复输入。

单一券商目标价不能替代估值。

## 精确计算

所有派生增速、利润率、覆盖率和倍数记录原始输入、变量名、公式、结果、单位、期间、来源和容差。正文中的精确派生值必须绑定 calculation id，并通过 `validate_deliverable.py --report-json` 重算。

## 最小可用交付

不论 direct、brief 或 full，至少包含：对象与期间、直接结论、一个类型驱动、具名同行或明确阻断、一条财务桥、三级估值之一、最强反方、至少三个带方向/期间/来源入口的可观察证伪信号、来源与局部 unknown。

禁止交付纯研究提纲、纯缺口清单或因估值/同行缺口产生的全局拒答。
