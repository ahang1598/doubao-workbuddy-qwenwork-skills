---
name: skill-a1-lhb-tracking
description: "Track A-share LHB seat behavior, persistence, and post-event observations from Pandadata MCP evidence. Use when a user asks about 龙虎榜席位、游资/机构行为、席位历史胜率、资金持续性、or post-event return labels."
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


# A1 龙虎榜资金追踪（WorkBuddy 连接器版）

使用 WorkBuddy 已连接的 Pandadata MCP 获取龙虎榜明细与交易日数据。不得调用
`panda_data` Python SDK，不得要求用户名、密码、Token 或 MCP 地址。

## 工作流

1. 先解析最近完成交易日和观察窗口。
2. 使用 `references/pandadata-interface-contracts.md` 中已登记的 `get_lhb_list`、
   `get_lhb_detail` 和 `get_stock_daily` 契约，直接通过 `call_pandadata` 取数。
3. 仅当已登记接口不覆盖任务时使用 `search_methods`；仅在明确契约错误后使用
   `get_method_doc`。接口返回 0 行时核对参数并报告无数据，不重新检索接口。
4. 通过连接器取得事件、营业部/机构席位、买卖方向、净额和事后行情。
5. 需要确定性聚合时，可把已取得的结构化数据交给 `scripts/a1_core.py`；该脚本只做本地计算，不负责登录或取数。
6. 将席位身份写成规则匹配或研究推断，不得表述为官方身份认定。
7. 未来收益只能作为事件发生后的观察标签，不能作为当时可得特征。

## 输出

记录股票、事件日、席位、方向、金额、样本数、观察窗口、数据日期和缺失状态。
样本不足时输出“不足以形成稳定统计”，不要生成买卖指令。
