---
name: fenbeitong-workbuddy
description: "分贝通 WorkBuddy Connector。用于当前账号与企业、差旅查询与行程、申请单、订单、消费规则、发票与报销、客服问答及问题处置。"
description_zh: "通过分贝通 Connector 处理企业差旅、申请单、订单、消费规则、发票报销和客服需求。"
description_en: "Use the Fenbeitong Connector for business travel, applications, orders, policies, invoices, reimbursement, and support."
version: "1.0.0"
author: "分贝通 Fenbeitong"
---

# 分贝通 WorkBuddy Connector

这份 Skill 指导 WorkBuddy 使用分贝通 MCP Connector。默认通过已启用的 Connector 调用工具，不要求用户提供或粘贴任何 Token。

## 适用场景

当用户需要处理以下分贝通业务时使用本 Skill：

- 查看当前账号、所在企业或切换企业；
- 查询酒店、机票、火车票，或创建和调整综合行程；
- 查询消费规则、申请单和商旅订单；
- 归集发票、生成费用草稿、创建或查询报销单；
- 查询产品规则、操作方法，或处理需要实际动作的问题。

只做普通旅行攻略、与分贝通无关的知识问答或不需要企业账号数据的请求时，不使用本 Skill。

## 使用边界

- 所有分贝通业务数据访问和业务操作都通过 MCP 工具完成；不要用本地脚本直接访问分贝通服务。
- 工具名称、参数、返回值和当前可用范围以 Connector 实时提供的工具描述为准，不凭记忆补充参数。
- 本 Skill 负责工具间的选择和多步流程，不替代 MCP Server 的鉴权、权限检查和副作用控制。
- 当前 WorkBuddy Connector 已验证模型可以读取工具结果的 `content`，但不能稳定读取 `structuredContent`。需要继续驱动流程的数据必须出现在模型可见文本中。
- `present_files` 是 WorkBuddy 平台内置的文件展示工具，不属于分贝通 MCP Server；需要展示本地 HTML 产物时按平台提供的接口调用。
- 只有工具真实返回成功时，才能声称已经查询、创建、修改、删除、提交或完成处置。

## 当前工具面

| 业务域 | MCP 工具 |
| --- | --- |
| 账号与企业 | `fbt_account` |
| 差旅 | `fbt_hotel_search`、`fbt_travel_search`、`fbt_trip_planner`、`fbt_apply_order`、`fbt_consumption_rules`、`fbt_order_search` |
| 发票与报销 | `fbt_invoice_management`、`fbt_expense_management`、`fbt_reimb_management` |
| 客服 | `fbt_service_ask`、`fbt_self_solve` |

工具可能按账号状态、权限和渠道策略动态显示。上表只用于路由，不代表用户必然有权调用全部工具。

## 推荐调用顺序

1. 用户询问当前账号、企业或要求切换企业时，先调用 `fbt_account`。其他业务只有在当前企业不明确且会影响结果时才先确认企业。
2. 根据用户目标选择唯一匹配的业务工具；不要为了探索能力并行调用多个相近工具。
3. 调用前读取该工具当前的参数定义。缺少工具明确要求的关键信息时再向用户追问，不让用户填写一份与当前工具无关的完整表单。
4. 多步流程始终沿用前一步工具返回的真实业务 ID、状态和下一步参数，不猜测 ID，不重新创建同一业务对象。
5. 创建、修改、删除、提交或实际处置等有副作用的操作，遵守工具返回的确认门；查询类操作不额外制造确认步骤。

## 路由规则

- 单独查询酒店使用 `fbt_hotel_search`；单独查询机票或火车票使用 `fbt_travel_search`；完整行程的新建、修改或取消使用 `fbt_trip_planner`。
- `fbt_trip_planner` 规划成功后，最终回复必须逐项保留每个机票、火车票和酒店后的 `预订链接: <booking_url>`，不得省略、改写或把多个链接合并。必须把工具返回的 `trip_html` 原样写入当前 WorkBuddy 工作区根目录的 `{trip_html_filename}`；其中 `trip_html_filename` 是工具返回结果中的字段名，值为本次产物应使用的文件名。然后调用 WorkBuddy 内置的 `present_files` 在侧边栏打开；HTML 中必须保留所有完整预订 URL。每次规划或修改都必须使用工具返回的新文件名生成新产物，不得覆盖此前的 HTML。正文不输出 HTML Markdown 链接，只通过产物和 `present_files` 展示页面。
- 查询当前员工适用的差旅标准和消费政策使用 `fbt_consumption_rules`；查询本人商旅订单使用 `fbt_order_search`。
- 发票归集或票夹查询使用 `fbt_invoice_management`；把发票生成费用草稿使用 `fbt_expense_management`；创建或查询报销单使用 `fbt_reimb_management`。
- 产品规则和操作方法等知识问题使用 `fbt_service_ask`；需要重新推送、修正、诊断、建单或跟进等实际动作时使用 `fbt_self_solve`。
- `fbt_apply_order` 创建、修改或预览待提交草稿时，按下文“申请单草稿预览”流程生成本地 HTML；查询列表和正式提交成功时不生成。

## 本地脚本

普通工具调用不得搜索、创建或执行替代脚本。只在下列明确流程中使用随 Skill 提供的脚本；脚本只做本地数据加工和文件交付，不访问分贝通业务接口。

### 申请单草稿预览

`fbt_apply_order` 需要呈现草稿时，其模型可见 `content` 包含一组完整标记：

```text
[DRAFT_PREVIEW_PAYLOAD_V1]
<URL-safe Base64>
[/DRAFT_PREVIEW_PAYLOAD_V1]
```

1. 仅提取两个标记之间的 Base64 字符串，不改写、不向用户展示该载荷。载荷包含完整性校验；脚本会在模型复制字符发生变化时从当前 WorkBuddy 会话记录恢复原始 MCP 结果，无法恢复则拒绝生成错误链接。
2. 解析本 `SKILL.md` 所在目录的绝对路径，以参数列表调用唯一指定脚本 `scripts/render_apply_draft.py`，不将载荷拼接成未转义的 shell 命令：

   ```bash
   python3 "<resolved-skill-directory>/scripts/render_apply_draft.py" --payload-base64 "<Base64>" --output-dir outputs
   ```

3. 读取脚本 stdout 中的 JSON，取 `draft_html_path`，立即调用 `present_files([draft_html_path])` 在侧边栏打开。
4. 同一申请单更新后重复执行；脚本会覆盖 `outputs/apply-draft-<id>.html`，不堆积历史文件。
5. 脚本失败时不重试创建或修改申请单，也不影响已成功的业务结果；降级为展示工具返回的草稿摘要和编辑链接。
6. `present_files` 成功后，文本只说明草稿预览已在侧边栏打开；不要再单独输出 `edit_url` 或引导用户点击外部草稿链接，编辑地址只保留在 HTML 的“编辑草稿”按钮中。

未列出的工具需要本地加工时，由该工具开发者把脚本随 Skill 一起提交，并写明唯一脚本路径、输入输出、失败处理和展示步骤。

## 结果与错误处理

- 优先使用工具返回的模型可见文本回答，不从不可见字段猜测结果。
- 工具要求补充信息时，只追问当前步骤缺失的信息，并在下一次调用中保留已经确认的参数。
- 登录态失效或鉴权失败时，提示用户在 WorkBuddy 中重新连接分贝通 Connector；不要要求用户在对话中发送 Token。
- 权限不足时说明当前账号或企业没有对应权限，不改用其他工具绕过。
- 超时或临时服务异常最多按工具提示重试；没有明确重试建议时，如实说明失败，不重复创建有副作用的业务对象。
- 若后续工具专属流程生成了完成文件，按 WorkBuddy 的结果展示规则将文件放入当前工作区 `outputs/`，再调用 `present_files`。没有生成文件时只返回文本结果。

## 安全边界

- 不单独展示 access token、user token、临时凭证、签名或会话标识；申请单草稿编辑 URL 中由工具生成的 token 仅保留在本地 HTML 按钮内，不在对话文本中重复输出。
- 不把健康检查、工具列表或探针结果当成真实业务已经完成的证据。
- 不根据工具名称猜测未公开能力，不把查询成功描述成创建、提交或审批成功。
