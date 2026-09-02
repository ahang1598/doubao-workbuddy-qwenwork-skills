---
name: picset-single-image-generation
description: "Picset 单图文生图/图生图：面向独立生图任务和图片编辑场景，根据提示词或参考图生成单张图片。适用于创意单图、概念图、插画、示意图、logo、场景图等非电商上架图，以及基于已有图片的换背景、改风格、加元素等编辑操作。不走电商套图报价与 generate_commerce_images 链路；画布仅作为结果承接容器，生图本身不依赖画布。"
---

# Picset 单图文生图/图生图

独立单张图片生成与图片编辑能力。默认使用简体中文。

## 职责与边界

负责**独立生图任务**和**图片编辑**：根据用户提示词生成单张创意图片，或基于用户提供的参考图进行图生图/编辑修改。

**不负责**：
- 电商主图、详情图、套图、Listing 图、A+ 商品图的方案规划与 `generate_commerce_images` 链路——那类需求交给 [电商套图 Skill](../picset-commerce-image-suite/SKILL.md)，**哪怕用户只要一张主图或一张详情图，也必须走套图**。
- 画布的打开、承接、状态读取与图片返回——那类操作交给 [Agent Canvas Skill](../picset-agent-canvas/SKILL.md)。生图完成后结果可由画布承接，但生图本身不依赖画布。
- 充值套餐面板——由连接器统一充值面板处理，详见 [连接器充值手册](../shared/connector-pricing-playbook.md)，工具为 `open_agent_pricing`。

细则与工具契约一律按 [单图共享手册](../shared/single-image-playbook.md) 执行，本 Skill 不重复展开。

## 调用时机

仅在以下两种场景调用本能力：

1. **独立生图任务**：用户要的是创意单图、概念图、插画、示意图、logo、场景图、氛围图等**非电商上架图**，且没有要求生成主图/详情图/套图/Listing/A+。
2. **图片编辑**：用户上传或引用一张已有图片，要求对其进行修改（换背景、改风格、加元素、局部重绘、扩图等），且修改目标**不是**电商主图/详情图/套图。

## 硬边界

- **主图/详情图哪怕一张也走套图**：用户说"做一张主图""一张详情图""1 张 Listing 图"等，一律路由到电商套图，禁止调用 `generate_agent_canvas_image`。
- **电商套图不走单图**：用户明确要主图/详情/套图/Listing/A+ 时，禁止用单图工具冒充上架图。
- **单图不走套图报价**：独立生图和图片编辑不调用 `quote_commerce_image_credits`，不经过套图的报价/上传登记/批量编号流程。
- **画布不负责生成**：打开画布、读取画布状态、把图片放入画布等操作由 Agent Canvas 处理，本 Skill 不调用 `open_agent_canvas` / `insert_agent_canvas_image` / `replace_agent_canvas_image`。

## 单图文生图流程

用户没有提供参考图、要求根据提示词生成单张图片时：

1. `conversationId` 必须原样使用宿主当前会话 ID（亦可能写作 `conversation_id`），不得自行生成或改写。
2. 首次调用生成新的 UUID v4 图片生成 `request_id`；提交、查询、重试必须复用同一个 `request_id`，失败后也不得换新。
3. 调用 `generate_agent_canvas_image`，传入 `conversationId`、`request_id`、`prompt`，`outputCount` 固定为 1，`referenceImages` 为空或不传。未传 `agentCanvasSessionId` 时服务端按 `conversationId` 自动开/复用画布会话，结果自动写回画布——这是服务端的承接行为，生图任务本身仍属本能力。
4. 需轮询时用 `get_agent_canvas_image_status`（同一 `request_id` + 返回的 `job_id`）。
5. 成功后简要告知生成结果；勿输出 ticket / functionsUrl。若用户要求把结果放到画布，交给 Agent Canvas 处理。

## 单图图生图流程

用户提供了参考图、要求基于参考图生成单张图片时：

1. 确认参考图已可访问（本地路径或已登记的 URL）。本地素材需先通过电商套图链路之外的方式取得可访问 URL——本能力不经过 `get_reference_image_upload_token` / `register_reference_image` 套图登记链路；若参考图来自用户附件，直接使用附件 URL。
2. `conversationId`、`request_id` 规则同文生图。
3. 调用 `generate_agent_canvas_image`，传入 `conversationId`、`request_id`、`prompt`、`referenceImages`（数组，每项含 `url`，最多 5 张），`outputCount` 固定为 1。
4. 轮询与结果处理同文生图。

## 图片编辑流程

用户要求对已有图片进行修改（换背景、改风格、加元素等）时：

1. 确认编辑目标不是电商主图/详情图/套图——如果是，路由到电商套图的局部返工。
2. 将待编辑图片作为 `referenceImages` 传入，`prompt` 描述编辑意图（如"把背景换成厨房场景"）。
3. 其余流程同图生图。
4. 编辑完成后，若用户要求在画布上继续微调，交给 Agent Canvas 承接；若用户要求把编辑后的图传回对话，由画布→对话机制处理（宿主投递，不经过 MCP）。

## 结果处理

- **成功**：简要告知生成/编辑完成，说明结果已可用。不输出 ticket、functionsUrl 或内部会话 ID。
- **失败**：复用同一 `request_id` 重试一次，不改走套图链路。重试仍失败时如实说明，不编造结果。
- **画布承接**：生图结果由服务端自动写回画布（若用户在画布环境中）；若用户明确要求把结果放入或替换到画布，路由到 Agent Canvas 的 `insert_agent_canvas_image` / `replace_agent_canvas_image`。
- **积分不足**：停止后续生成，调用 `open_agent_pricing` 打开连接器统一充值面板，不得向用户展示充值 URL 或 ticket。

## MCP 工具速查

| 工具 | 用途 | 调用阶段 |
| --- | --- | --- |
| `generate_agent_canvas_image` | 单图生成（文生图/图生图/图片编辑），outputCount 固定 1 | 生成提交 |
| `get_agent_canvas_image_status` | 查询单图任务状态与结果 | 轮询 |

调用 MCP 工具前，必须使用 `tool_search` 按工具名获取完整参数定义，再按取回的定义发起调用。运行时工具名可能带有后缀，以 `tool_search` 返回的实际名称为准。

> 注：`generate_agent_canvas_image` 工具名中虽含 "canvas"，但其定位是**独立单图生成工具**；画布承接是服务端的联动行为，不改变本能力的独立生图定位。
