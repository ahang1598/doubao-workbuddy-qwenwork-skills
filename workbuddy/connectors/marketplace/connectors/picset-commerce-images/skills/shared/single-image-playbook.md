# Picset 单图文生图/图生图共享手册

本手册定义单图文生图、图生图和图片编辑的工具契约与操作细节。所有业务 Skill（[单图文生图/图生图 Skill](../picset-single-image-generation/SKILL.md)）统一遵循本手册，不重复实现工具调用逻辑。

调用 MCP 工具前，必须使用 `tool_search` 按工具名获取完整参数定义，再按取回的定义发起调用。禁止凭工具名猜测参数结构。

---

## 一、工具总览

| 工具 | 用途 | 调用阶段 |
| --- | --- | --- |
| `generate_agent_canvas_image` | 单图生成（文生图/图生图/图片编辑），outputCount 固定 1 | 生成提交 |
| `get_agent_canvas_image_status` | 查询单图任务状态与结果 | 轮询 |

> 注：`generate_agent_canvas_image` 工具名中虽含 "canvas"，但其定位是独立单图生成工具。服务端在生成后会自动把结果写回画布（若未传 `agentCanvasSessionId`，按 `conversationId` 自动开/复用画布会话），这是结果承接行为，不改变本能力的独立生图定位。画布的打开、承接管理与图片返回由 [Agent Canvas 共享手册](./agent-canvas-playbook.md) 处理。

---

## 二、generate_agent_canvas_image

### 用途

根据提示词和可选参考图生成单张图片。文生图时不传参考图；图生图/图片编辑时传入参考图。

### 前置条件

- 用户意图已确认为独立生图任务或图片编辑（非电商主图/详情/套图/Listing/A+）
- `conversationId` 已从宿主当前会话取得
- `request_id` 已生成为 UUID v4

### 入参

```json
{
  "conversationId": "<宿主当前会话 ID>",
  "request_id": "<UUID v4，本次生图的稳定幂等键>",
  "prompt": "<本次图片生成提示词，1-4000 字符>",
  "referenceImages": [
    { "url": "<参考图 URL>", "id": "<可选，图片标识>", "mimeType": "<可选，MIME 类型>" }
  ],
  "outputCount": 1,
  "agentCanvasSessionId": "<可选，画布会话 ID；不传时按 conversationId 自动开/复用>"
}
```

- `conversationId`：必填，宿主提供的真实当前对话 ID。必须原样使用，不得自行生成、改写，不得使用 `request_id` 代替。亦可能写作 `conversation_id`。
- `request_id`：必填，UUID v4。本次生图请求的稳定幂等键；提交、查询、重试必须复用同一个值，失败后也不得换新。
- `prompt`：必填，1-4000 字符。本次图片生成提示词。
- `referenceImages`：可选，数组，最多 5 项。每项必须含 `url`；`id` 和 `mimeType` 可选。文生图时为空或不传；图生图/图片编辑时传入待参考/待编辑的图片。
- `outputCount`：固定为 1，不得传其他值。
- `agentCanvasSessionId`：可选。当前 Agent Canvas 会话 ID；未提供时服务端按 `conversationId` 自动打开或复用画布会话，生成结果自动写回该画布。

### 返回

提交成功后返回 `job_id`（用于后续轮询）。保存 `job_id` 和 `request_id`，把该任务标记为 `submitted`。

### 约束

- 不得先调用 `generate_agent_canvas_image` 试探或校验 `request_id`
- 提交失败时，保留 `request_id`，只重试未提交或失败的请求
- 提交返回积分不足时，停止后续生成和轮询，调用 `open_agent_pricing` 打开连接器统一充值面板，不得向用户展示 URL
- 不得将本工具用于电商主图/详情/套图/Listing/A+ 生成——那类需求必须走 `generate_commerce_images`

---

## 三、get_agent_canvas_image_status

### 用途

查询单张 Agent Canvas 图片生成结果，并在成功后由服务端写回当前画布。

### 前置条件

- 已调用 `generate_agent_canvas_image` 并取得 `job_id`
- 保存了同一 `request_id`

### 入参

```json
{
  "conversationId": "<宿主当前会话 ID>",
  "request_id": "<与生成时相同的 UUID v4>",
  "job_id": "<generate_agent_canvas_image 返回的任务 ID>",
  "agentCanvasSessionId": "<可选，画布会话 ID>"
}
```

- `conversationId`：必填，与生成时一致。
- `request_id`：必填，与生成时相同的 UUID v4，不得换新。
- `job_id`：必填，`generate_agent_canvas_image` 返回的任务 ID。
- `agentCanvasSessionId`：可选。

### 返回与状态处理

- `processing`：继续轮询
- `success`：任务完成，记录结果（图片 URL 由服务端写回画布）
- `failed`：任务失败，记录失败原因

### 节奏

- 固定 30 秒间隔调用一次
- 不向用户输出逐次进度消息
- 轮询期间不读写本地文件

### 超时处理

- 累计等待达到合理上限时停止轮询
- 保留原 `request_id` 和 `job_id`，告知用户任务仍可能在后台处理
- 不得自动新建任务或重新提交
- 用户后续可凭 `request_id` + `job_id` 恢复查询

---

## 四、request_id 规则

- 每次独立生图任务生成一个新的 UUID v4 `request_id`
- 提交、查询、重试必须复用同一个 `request_id`
- 失败后重试不得换新 `request_id`
- 不同生图任务使用不同的 `request_id`
- `request_id` 只保留在本地上下文，不发送给报价工具

---

## 五、conversationId 规则

- 必须原样使用宿主当前会话 ID（亦可能写作 `conversation_id`）
- 不得自行生成、改写或拼接
- 不得使用图片生成 `request_id` 代替 `conversationId`
- 同一会话内的多次生图调用使用同一个 `conversationId`

---

## 六、参考图规则

- `referenceImages` 最多 5 张
- 每项必须含 `url` 字段
- 文生图时 `referenceImages` 为空或不传
- 图生图/图片编辑时传入待参考或待编辑的图片 URL
- 本能力不经过 `get_reference_image_upload_token` / `register_reference_image` 套图登记链路；参考图直接使用用户附件 URL 或已可访问的图片 URL

---

## 七、结果与失败处理

- **成功**：简要告知生成/编辑完成。不输出 ticket、functionsUrl 或内部会话 ID。图片由服务端写回画布（若在画布环境中）。
- **失败**：复用同一 `request_id` 重试一次，不改走套图链路。重试仍失败时如实说明失败原因，不编造结果。
- **积分不足**：停止后续生成和轮询，调用 `open_agent_pricing` 打开连接器统一充值面板，不得向用户展示充值 URL 或 ticket。说明需充值后再重试。
- **画布承接**：若用户明确要求把生成结果放入或替换到画布，路由到 Agent Canvas 的 `insert_agent_canvas_image` / `replace_agent_canvas_image`，详见 [Agent Canvas 共享手册](./agent-canvas-playbook.md)。

---

## 八、通用重试原则

最多重试一次，且仅在安全修正后（如缩小范围、提供已知标识、修正提示词）。不将空响应、部分响应或错误响应转为成功结论。
