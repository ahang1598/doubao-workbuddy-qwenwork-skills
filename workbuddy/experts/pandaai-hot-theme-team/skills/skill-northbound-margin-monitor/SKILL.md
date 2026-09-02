---
name: skill-northbound-margin-monitor
description: "Monitor A-share capital conditions across stock-connect disclosures, margin financing, index futures, market breadth, and major-fund indicators with PandaData evidence. Use when a user asks for a capital-flow dashboard, leverage-risk check, or multi-signal market review."
---

## WorkBuddy PandaData 数据源覆盖

本技能在 WorkBuddy 专家包中运行时，所有实时和历史金融数据必须来自已连接的
`pandadata` Connector。若下文、参考资料或脚本提到 Python `panda_data` SDK、
AkShare、Tushare、网页抓取、直连 HTTP 或本地凭证，以本节为准：不得使用这些
方式获取正式数据。

1. 数据型任务必须先完成 `auth_status` 和至少一次真实的 `call_pandadata` 业务调用；在收到
   Connector 返回前，禁止输出分析、排名、数字结论或“无数据”。本 Skill 的流程不得绕过
   主 Agent 的最低接口调用清单。
2. 先按本 Skill 的 `references/pandadata-interface-contracts.md` 选择已登记方法和参数。只要任务能映射到已登记接口，
   就直接通过 `call_pandadata` 传入该业务方法和 `params`；常规调用前不得执行接口检索。
3. 仅当已登记方法被 Connector 明确报告为参数契约不兼容、字段契约变化或调用失败时，
   才对该方法调用一次 `get_method_doc`，修正参数后最多重试一次。
4. 仅当本地接口表没有匹配项，或 Connector 明确报告方法不存在/不受支持时，才调用
   `search_methods` 动态发现接口；不得靠猜测连续试用名称相近的 `get_*` 方法。
5. 只有 `call_pandadata` 实际返回 0 行时才允许写“无数据”。必须先完成一次复查调用：校验
   最新交易日与代码格式，放宽日期窗口，移除非必填过滤条件，或使用登记的备用参数；仍为
   0 行才可如实报告，并保留两次调用回执。0 行不得触发 `search_methods`。
6. 不向 `call_pandadata` 添加未登记参数或顶层行数限制；记录实际方法、参数、数据日期、
   频率、复权口径、行数、空值和错误状态。
7. 包内脚本只可处理 Connector 已返回的数据或执行纯本地计算与校验，不得自行联网取数。

最终答案必须包含“数据调用回执”表：接口、实际参数、状态、行数、数据日期范围和关键字段。
缺少回执表示任务未完成，必须继续调用工具而不是结束回答。

权限不足、配额限制、空结果、延迟发布和字段缺失都必须明确披露，不得切换到其他数据源
或用模型推断补数。


# A股资金与杠杆监测

## 工作流

1. 明确截止交易日、观察窗口和用户关注的市场或指数。
2. 每个会话首次取数前调用一次 `auth_status`；未认证时停止取数并引导完成 WorkBuddy 连接。
3. 优先从 `references/pandadata-interface-contracts.md` 选择已登记的 `get_hsgt_hold`、
   `get_margin`、指数行情、市场宽度和龙虎榜方法，并直接通过 `call_pandadata` 获取数据。
4. 仅当所需维度没有已登记接口时使用 `search_methods`；仅在明确契约错误后使用一次
   `get_method_doc`。接口返回 0 行时核对披露制度、日期和权限，不重新检索接口。
5. 按同一交易日或最近可比发布日期对齐数据。北向资金披露制度变化、延迟发布和缺失字段必须单独标注，不得用旧口径冒充实时净流入。
6. 分析融资余额变化、融资买入强度、期现相对表现、涨跌家数或涨跌停宽度、资金流集中度及信号共振。
7. 每个信号给出原始数值、历史比较窗口、方向、置信度和数据质量；缺少关键维度时不得生成综合强结论。

## 输出

- 资金环境摘要
- 各维度数据表和截至日期
- 同向共振、背离和风险提示
- 数据缺口、披露延迟和口径变化
- Connector 方法、参数、返回行数和异常状态

不得把资金流、杠杆或期货持仓的历史相关性表述为确定性预测。
