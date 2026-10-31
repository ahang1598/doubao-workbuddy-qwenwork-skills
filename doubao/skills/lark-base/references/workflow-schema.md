# 工作流步骤图结构契约

## 使用范围与依赖

用于读懂 `+workflow-get` 的 `steps`，或构造 `+workflow-create`／`+workflow-update` 的 `--json` body。只列 Workflow 或读状态时不加载本页。

- 解释或构造步骤时，按实际节点读 [触发器](workflow-triggers.md)、[动作](workflow-actions.md)、[控制流](workflow-control-flow.md)。
- 构造或核验条件、字段赋值、`ref` 时，完整读 [值类型与条件](workflow-values.md)，再按 [输出引用](workflow-outputs.md#使用范围与依赖) 读公共路径和实际节点章节；不得只凭骨架构造。
- 创建或修改步骤结构时，按 [示例索引](workflow-examples.md#示例索引) 读对应完整示例和结构说明；只改名称或文案时保留原结构，不读示例。

外层只承载 workflow 元信息，核心校验对象是 `steps`；列表只用于拿 workflow ID 和启停状态。

## 步骤结构（WorkflowStep）

Trigger/Action/Branch/System 共享结构：

```json
{"id":"step_xxx","type":"AddRecordTrigger","title":"监控新订单","next":"step_yyy","data":{}}
```

|字段|类型/必填|契约|
|-|-|-|
|id|string/是|用户自定义的唯一 ID；供 next、children.links[].to 引用|
|type|string/是|下列步骤类型|
|title|string/是|非空；省略/空字符串会被服务端拒绝，dry-run 不能代替此校验|
|children|StepChildren/否|全部分支/循环的子关系边|
|next|string\|null/否|线性后继 ID；null 表示结束；IfElseBranch 不支持公共后继，省略或设 null|
|data|object/是|步骤配置；按 type 读触发器/动作/控制流文档，值与条件见 workflow-values.md|
|meta|object/APIHubAction、AIAgentMCPAction 必填|component_id 指定二方组件/MCP 工具包；见 workflow-apihub.md、workflow-ai-agent.md|

连线写 children，扩展标识写 meta，输入参数写 data。普通 Action/APIHubAction 作为 Agent 工具时，可在业务参数同级的 data.tool_info.description 写调用说明；更新前 get 并保留原值；完整语义见 workflow-ai-agent.md#工具调用说明。

## 子关系与连线

StepChildren 是独立 JSON 值，含 ChildLink：

```json
{"links":[{"kind":"if_true","to":"step_4","label":"branch_1","desc":"金额大于1000"}]}
```

links 为 ChildLink[]，无子关系时为 []。每条边从当前节点指向 to。

|字段|类型/必填|契约|
|-|-|-|
|kind|string/是|if_true/if_false/case/loop_start/slot|
|to|string/是|目标 ID|
|label|string/否|标签，如 branch_1/tool/llm/memory|
|desc|string/否|语义说明，如“状态正常”|

|kind|使用节点与规则|
|-|-|
|if_true/if_false|IfElseBranch 条件真/假跳转|
|case|SwitchBranch/AIClassificationBranch 多路分支；label 选用 branch_1 等中性标签，desc 写语义|
|loop_start|Loop 循环体入口|
|slot|AIAgentAction 工具以 label: tool 挂载；LLM/记忆由根节点配置；回读的空 llm/memory 链接可保留|

## 节点类型索引

### Trigger 类型

| type | 触发时机 |
|-|-|
| `AddRecordTrigger` | 新增记录且关注字段非空 |
| `SetRecordTrigger` | 指定字段发生修改 |
| `ChangeRecordTrigger` | 新增记录，或条件字段修改后满足条件 |
| `TimerTrigger` / `ReminderTrigger` / `ButtonTrigger` | 定时 / 日期提醒 / 按钮点击 |
| `LarkMessageTrigger` | 接收飞书消息 |

Trigger 不得设置 `children`，用 `next` 串联后继。构造或核验记录触发器时，完整读 [记录触发器对比](workflow-triggers.md#记录触发器对比)，确认事件范围、监听字段及修改前后的条件。

### Action 类型

| type | 说明 |
|-|-|
| `AddRecordAction` / `SetRecordAction` / `FindRecordAction` | 新增 / 更新 / 查找记录 |
| `HTTPClientAction` / `Delay` | HTTP 请求 / 延迟 |
| `LarkMessageAction` / `LarkEmailAction` | 发送飞书消息 / 邮件；邮件见[节点参数](workflow-actions.md#发送邮件larkemailaction) |
| `GenerateAiTextAction` / `AIAnalysisAction` | AI 生成文本 / AI 分析 |
| `APIHubAction` | 当前仅支持飞书任务、日程、群组的 9 个动作，只用 [APIHub 清单](workflow-apihub.md) 所列组件、参数和输出 |
| `AIAgentAction` | AI Agent 根节点，见 [AI Agent](workflow-ai-agent.md) |
| `AIAgentMCPAction` | AI Agent 的 MCP 工具包步骤，必须通过 `slot`／`tool` 挂载 |

普通 Action 用 `next` 串联；`AIAgentAction` 用 `children.links` 挂工具、用 `next` 接执行后的动作；作为 Agent 工具的步骤不设置 `next`。

### Branch 与 System 类型

Branch 类型有 `IfElseBranch`、`SwitchBranch`、`AIClassificationBranch`；System 类型有 `Loop`。连线见 kind 表。
