# 工作流 AI Agent 节点契约

## 使用范围与依赖

Agent 在运行时理解输入、生成文本或结构化结果，按需调用工具；用 `base +workflow-create/+workflow-update` 创建或更新。

## 节点关系

- 根节点 `AIAgentAction` 的 `data.model` 配模型、`data.memory` 配记忆；不要创建 `AIAgentLLMAction` / `AIAgentMemoryAction` 独立步骤。
- 工具是 `steps` 中的独立步骤，通过根节点 `children.links` 的 `{"kind":"slot","label":"tool","to":"工具步骤ID"}` 挂载。同一工具只挂一个 Agent。
- 主链末节点必须位于 `steps` 数组末尾；工具步骤放在它前面，不能追加到末节点之后。
- 工具步骤没有 `next`；Agent 之后的动作挂在根节点 `next`。工具按需调用，不保证顺序，也不保证都被调用。
- `get` 返回的 `llm/memory` 空链接（`to:""`）可保留；不要填不存在的内部节点 ID。

## 输入与模型

本节及“输出配置”“记忆”的字段都位于根节点 `AIAgentAction.data` 下。公开 CLI 字段用 snake_case；引用字符串中的 ID 和输出路径保持原样。

| 字段 | 说明 |
|---|---|
| `prompt` / `system_message` | 输入指令 / 系统设定，text/ref 片段数组；prompt 执行前要有明确内容 |
| `model.name` | 模型 pack ID，如 `doubao_chat_model`；从现有工作流或服务端配置确认，不能凭显示名编造 |
| `model.temperature` / `model.max_token` | 数字 / 正整数；范围和上限随服务端当前模型配置 |
| `model.timeout` | 正整数，单位毫秒，不要填秒数 |
| `max_iterations` | 正整数；上限由服务端决定 |
| `enable_streaming_reply` | 布尔，是否流式回复；不替代下游记录或消息动作 |

- 不支持 `thinking_mode`：不要填，并告诉用户暂不支持。
- 新建可运行的 Agent 时显式填写已确认的 `model.name`，不要假定服务端自动选模型。

## 输出配置

| 字段 | 说明 |
|---|---|
| `output_format_type` | `text` / `json` / `form` |
| `json_output` | 结果形状的 JSON 示例字符串，不接受 JSON Schema。字段名、数组结构和标量类型决定下游引用路径 |
| `form_output` | 字段数组，每项 `{name,type,description?}`；type 为 `string/number/boolean/timestamp/fileInfo` |

json 模式必填 `json_output`，form 模式必填非空 `form_output`；不要同时填多种。

## 记忆

`memory.history_rounds`：记忆轮数，正整数。仅 `LarkMessageTrigger` 生效；其他触发器不要填。

## MCP 工具包

只支持下表 5 个 MCP 包。工具步骤类型统一为 `AIAgentMCPAction`，用 `meta.component_id` 选包。

| 能力 | component_id | 常用 tool_list |
|---|---|---|
| 联网搜索 | `search_mcp` | `["web_search"]` |
| 读取 URL | `link_reader_mcp` | `["link_reader"]` |
| 多维表格 | `feishu_base_mcp` | `["add_base_record","update_base_record"]` |
| 飞书用户和云文档 | `openplatform_mcp` | 按需选 `search-user/get-user/search-doc/fetch-doc/create-doc/update-doc/list-docs/fetch-file/get-comments/add-comments` |
| 豆包联网搜索 | `doubao_general_search_mcp` | `["GeneralSearch"]`；可能消耗相应额度 |

- 这 5 个包的工具描述由服务提供，`data.tool_info.description` 不参与编译；调用时机和业务约束写进 Agent 的 `prompt`。
- 上表不是工具全集；服务端用 `GetMCPInfo` 校验真实工具，新增工具只用已确认的真实 key。CLI 没有工具目录查询命令，不要虚构 `+workflow-meta` 等接口。

| MCP data 字段 | 说明 |
|---|---|
| `tool_list` | 工具 key 数组，大小写敏感。省略=服务端默认选择，`[]`=显式空选择；优先显式列出所需工具 |
| `identity_type` | `maker` / `triggerPersonal`。只有按钮、飞书消息触发支持触发人身份；其他触发器用 `maker` |
| `env` | 字符串键值；只设工具需要的项 |

- `openplatform_mcp` 需要运行身份对当前 Base 完成飞书 MCP 授权；报 `UAT is empty` 时提示该身份授权后再运行。CLI 已登录不代表已授权；不要把凭证填进 `env`、prompt、工作流或报告。
- 不支持自定义 MCP、`feishu_doc_mcp`、`doubao_fetch_mcp` 等未列出的包；不要自动换成相近工具，先向用户说明差异。

## 普通 Action 工具

普通 Action 工具复用对应节点的 `data` 协议，用 slot/tool 挂载；`Delay` 只放主链。

可挂载的类型：
- `FindRecordAction` 查找记录；`AddRecordAction` / `SetRecordAction` 新增 / 修改记录
- `LarkMessageAction` 发飞书消息；`LarkEmailAction` 发飞书邮件（见[节点参数](workflow-actions.md#发送邮件larkemailaction)）
- `HTTPClientAction` HTTP 请求；`GenerateAiTextAction` AI 生成文本（注意 `Ai` 大小写）；`AIAnalysisAction` AI 分析
- `APIHubAction` 仅限[已支持的 9 个二方动作](workflow-apihub.md)

- 参数必须符合节点协议；不能留空或伪造“AI 自动填写”标记让 Agent 补齐。
- 不要把 Agent 最终输出引用回它自己的工具；要用邮件发送最终结果时，把邮件作为 Agent 之后的普通节点。

## 工具调用说明

普通 Action 和已支持的 APIHub 工具可在 `data.tool_info.description` 中写调用时机，与业务参数并列：

```json
{"tool_info":{"description":"需要查询当前库存时调用。"}}
```

- 描述只帮助 Agent 选工具，不替代业务参数、授权，也不强制执行工具。
- `+workflow-update` 提交完整 steps：先 get，保留各工具原有 `tool_info`；传 `{"description":"新说明"}` 替换，传 `null` 清除。省略字段不会保留原描述。空字符串会原样保存，能否启用由服务端校验。
- 只配置 `description`；不要传内部 `AIData/ai_data`、`description_is_user_change` 或 `AIInferList`。`title`、链接 `desc` 和 `meta.op_desc` 不能代替工具描述。

## 输出与引用

| 输出配置 | 下游引用 |
|---|---|
| text | 整体字符串：`$.agent_id` |
| json object | 按示例字段：`$.agent_id.摘要` |
| json 对象内的数组字段 | 输出 `{"items":[{"名称":"文本"}]}` 时，Loop 引用 `$.agent_id.items`，循环内用 `$.loop_id.item.名称` |
| form | 按配置字段名：`$.agent_id.字段名` |

- 顶层 JSON 数组的根引用被识别为 object，不能直接作 Loop 数据源；改用上面的对象包装。
- 不要引用内部 LLM/记忆节点。下游动作优先用 Agent 最终输出，不要假定某个工具一定被调用并引用它的输出。

## 示例：联网整理输入，写入结果表

先查询真实表名和字段 ID，替换示例中的值再提交。每次新建使用新的 `client_token`。

```json
{"client_token":"new-unique-request-id","title":"联网整理后写入结果","steps":[
{"id":"input","type":"AddRecordTrigger","title":"输入","next":"agent","data":{"table_name":"输入表","watched_field_name":"主题"}},
{"id":"agent","type":"AIAgentAction","title":"整理","next":"save","children":{"links":[{"kind":"slot","label":"tool","to":"search"}]},
"data":{"prompt":[{"value_type":"text","value":"联网核实以下主题，输出摘要和来源："},{"value_type":"ref","value":"$.input.fld真实字段ID"}],
"system_message":[{"value_type":"text","value":"只基于查到的结果回答，查询失败明确说明。"}],"model":{"name":"doubao_chat_model"},"max_iterations":5,
"enable_streaming_reply":false,"output_format_type":"json","json_output":"{\"摘要\":\"文本\",\"来源\":\"URL\"}"}},
{"id":"search","type":"AIAgentMCPAction","title":"搜索","meta":{"component_id":"search_mcp"},"data":{"tool_list":["web_search"],"identity_type":"maker"}},
{"id":"save","type":"AddRecordAction","title":"保存","data":{"table_name":"结果表","field_values":[{"field_name":"摘要","value":[{"value_type":"ref","value":"$.agent.摘要"}]},{"field_name":"来源","value":[{"value_type":"ref","value":"$.agent.来源"}]}]}}
]}
```
