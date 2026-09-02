# Picset Agent Canvas 共享手册

本手册定义 MCP Agent Canvas（万能画布）的标准操作。主 Skill、电商套图 Skill、单图文生图/图生图 Skill 与 Agent Canvas Skill 共用，不在各处重复实现。充值面板的操作详见 [连接器充值手册](./connector-pricing-playbook.md)。

跨宿主原生画布。调用前用 `tool_search` 取参；只用 live MCP 工具。不得向用户展示 ticket / functionsUrl；`get_agent_canvas_state` 等返回的图片 URL 可展示。

**画布定位**：画布只负责**承接 Agent 生成的图片**和**用户修改后将图片返回给 Agent**。画布不负责图片生成——生成由电商套图（`generate_commerce_images`）或单图文生图/图生图（`generate_agent_canvas_image`）完成。画布也不负责充值——充值由连接器统一充值面板（`open_agent_pricing`）处理，详见 [连接器充值手册](./connector-pricing-playbook.md)。单图文生图/图生图的生成流程详见 [单图共享手册](./single-image-playbook.md)。

命中画布能力时：不要求商品图、不展示套图配置表、不走报价/生成套图链路；直接按下列流程或工具执行。

---

## 一、何时用画布 / 何时用套图 / 何时用单图 / 何时用充值

| 用户意图 | 正确路径 | 禁止 |
| --- | --- | --- |
| 已有商品图的主图/详情/套图/Listing/A+（**含一张主图或一张详情图**） | 电商套图 Skill / [共享执行手册](./execution-playbook.md) | 不得用单图工具或 Canvas 冒充上架套图；**哪怕只有一张也必须走套图** |
| 独立创意单图/概念图/插画/示意图/logo/场景图等非电商上架图 | 单图文生图/图生图 Skill / [单图共享手册](./single-image-playbook.md) | 不得调用 `generate_commerce_images`；不得先走套图报价 |
| 基于已有图做编辑（换背景/改风格/加元素等，非电商上架图） | 单图文生图/图生图 Skill（图生图） | 不得走套图链路；不得用 Canvas 代替编辑 |
| 打开画布 / 把生成结果放入画布 / 查看画布状态 | Agent Canvas Skill / 本手册 | 不得编造 session / conversation id |
| 积分不足 / 用户要充值 | [连接器充值手册](./connector-pricing-playbook.md) → `open_agent_pricing` | 不得向用户展示充值 URL / ticket；不得编造套餐价目 |
| 把已有 URL 图放入画布 | `insert_agent_canvas_image` / `replace_agent_canvas_image` | 不得把 ticket 当图片 URL |
| 用户在画布改完后把图传回对话 | 画布→对话（宿主投递，不经过 MCP） | 不得调用 `send_canvas_image_to_agent`（已废弃） |

---

## 二、画布承接流程

生成任务（电商套图或单图文生图/图生图）完成后，若需把结果同步到画布：

### 2.1 插入新图

调用 `insert_agent_canvas_image`，传入：
- `agentCanvasSessionId`：当前画布会话 ID
- `request_id`：与生成时相同的 UUID v4
- `image`：对象，含 `url`（必填），`id` 和 `prompt` 可选

### 2.2 替换已有图

调用 `replace_agent_canvas_image`，传入：
- `agentCanvasSessionId`、`request_id`
- `targetImageId`：画布中待替换的目标图片 ID
- `image`：新图片对象，含 `url`

### 2.3 打开画布

若用户要求打开画布查看或继续编辑，调用 `open_agent_canvas`，传入 `conversation_id`（当前对话 ID）。未传 `agentCanvasSessionId` 时服务端按 `conversation_id` 自动开/复用会话。

### 2.4 panelActive 判断

- `panelActive: true` 时写回流程结束，**不得**再调用 `open_agent_canvas`。
- `panelActive: false` 且宿主没有打开工具结果返回的 UI 时，才可使用同一个 `conversation_id` 调用 `open_agent_canvas` 兜底。

---

## 三、套图与单图结果写回画布

- 电商套图经 `present_files` 交付后，若需同步到画布，按本手册第二节执行 `insert_agent_canvas_image`（新图）或 `replace_agent_canvas_image`（替换）。
- 单图文生图/图生图的结果由服务端自动写回画布（若未传 `agentCanvasSessionId`，按 `conversationId` 自动开/复用）；若用户明确要求手动放入或替换，同样按本手册第二节执行。
- 生成或修改后的图片必须写回当前 Agent Canvas。

---

## 四、画布 → 对话

用户在画布上点击「加入当前对话」时，面板把选中图投到宿主输入框（下一条消息附件），**不经过任何 MCP 工具**。

- Agent 不必触发；收到带图消息即作修改上下文，勿再调工具或索要地址。
- `send_canvas_image_to_agent` 已废弃，不得调用。该工具只回显入参，不会向对话推送任何内容，仅为兼容旧客户端保留。

---

## 五、画布工具速查

| 工具 | 用途 |
| --- | --- |
| `open_agent_canvas` | 打开/复用画布 Panel |
| `get_agent_canvas_state` | 读取画布状态摘要 |
| `insert_agent_canvas_image` | 插入图片到画布 |
| `replace_agent_canvas_image` | 替换画布中目标图片 |

> 注 1：`generate_agent_canvas_image` 和 `get_agent_canvas_image_status` 属于单图文生图/图生图能力，详见 [单图共享手册](./single-image-playbook.md)，不在本画布手册范围内。
> 注 2：`open_agent_pricing` 属于连接器统一充值面板，详见 [连接器充值手册](./connector-pricing-playbook.md)，不在本画布手册范围内。
