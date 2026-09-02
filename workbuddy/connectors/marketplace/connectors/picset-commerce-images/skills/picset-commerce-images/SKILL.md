---
name: picset-commerce-images
description: "Picset AI 电商设计：面向电商卖家、设计师和美工，提供三条独立功能线——电商套图（主图/详情图/套图/Listing/A+，含一张也走套图）、单图文生图/图生图（独立创意单图与图片编辑）、Agent Canvas（画布承接与充值面板）。覆盖淘宝、天猫、京东、拼多多、抖音、1688、小红书、TikTok、Amazon、Shopify、Temu、OZON、Shopee、阿里巴巴国际站等主流平台，支持方案规划、积分报价、生成跟踪和按编号局部修改。"
---

# Picset 电商设计

默认使用简体中文；用户指定其他语言时跟随用户设置。

## 能力路由

根据用户意图选择对应能力模块。当前已上线能力：**电商套图**、**单图文生图/图生图**、**Agent Canvas**。

| 用户意图 | 路由到 |
| --- | --- |
| 生成商品主图、详情图、套图、Listing 图、A+ 商品图、上架图（**含一张主图或一张详情图**） | [电商套图 Skill](picset-commerce-image-suite/SKILL.md) |
| 点名 `M1`、`D2` 等已有编号要求重做或修改 | [电商套图 Skill](picset-commerce-image-suite/SKILL.md)（局部返工） |
| 独立生图任务：创意单图、概念图、插画、示意图、logo、场景图等**非电商上架图** | [单图文生图/图生图 Skill](picset-single-image-generation/SKILL.md)，工具 `generate_agent_canvas_image` |
| 图片编辑：基于已有图片换背景、改风格、加元素、局部重绘等（**非电商主图/详情/套图**） | [单图文生图/图生图 Skill](picset-single-image-generation/SKILL.md)（图生图） |
| 打开万能画布 / 把生成结果放入画布 / 查看画布状态 / 在画布上继续编辑 | [Agent Canvas Skill](picset-agent-canvas/SKILL.md) |
| 积分不足 / 要充值 / 打开充值套餐 | [连接器充值手册](shared/connector-pricing-playbook.md) → `open_agent_pricing`；不得粘贴充值链接 |
| 只咨询能力、流程、平台支持或费用 | 直接回答，不创建任务 |
| 没有提供商品图（且用户要的是电商套图） | 只要求上传商品图，不要求一次填写完整表单 |

### 硬分流

- **主图/详情图哪怕一张也走套图**：用户说"做一张主图""一张详情图""1 张 Listing 图"等，一律路由到电商套图，禁止调用 `generate_agent_canvas_image`。
- **独立生图/图片编辑走单图**：创意单图、概念图、插画、示意图、logo、场景图等非电商上架图，以及基于已有图的编辑修改，走 `generate_agent_canvas_image`，禁止 `quote_commerce_image_credits` / `generate_commerce_images`。
- **画布只承接/返回，不生成**：打开画布、把结果放入画布、读取画布状态、用户在画布改完后把图传回对话，由 Agent Canvas 处理；画布不负责图片生成。
- **套图与画布都要时**：先由电商套图交付，再按 [Agent Canvas 共享手册](shared/agent-canvas-playbook.md) 写回画布。
- **单图与画布都要时**：先由单图文生图/图生图完成生成，结果由服务端自动写回画布或按 [Agent Canvas 共享手册](shared/agent-canvas-playbook.md) 手动承接。

> **扩展约定**：新增能力时，在本表新增一行，并在子 Skill 补充对应章节。通用执行层、跨轮次状态、工具速查和异常处理所有能力共用，不重复编写。

## 对话规则

根据用户意图区分首轮回复，禁止把完整配置面板一次性发给用户：

- **直接要求生成电商套图**：请用户上传商品图，并说明推荐会生成什么。回复控制在约 120 个中文字内，必须保留"查看选项"入口。
- **直接要求独立生图/图片编辑**：确认生成意图和参考图（如有），不展示套图配置表，直接进入单图生成流程。
- **询问流程或"怎么做"**：简要说明即可，不展开完整配置目录。
- **询问"有哪些选项"或回复"查看选项"**：才展开完整的平台、市场、语言、数量、比例和分辨率选项（仅电商套图适用）。

## 异常处理

- **鉴权失败**：提示用户检查连接器配置中的 `PICSET_AGENT_SK` 是否正确填写。
- **积分不足**：停止后续生成；调用 `open_agent_pricing` 打开连接器统一充值面板，不得向用户展示充值 URL 或 ticket；说明需充值后再重试。细则见 [连接器充值手册](shared/connector-pricing-playbook.md)。
- **生成超时**：保留服务端返回的 `task_id`（套图）或 `request_id` + `job_id`（单图），告知用户任务仍可能在后台处理，支持后续恢复查询；不自动新建任务。
- **部分失败**：先展示成功图片，失败项说明编号，支持按编号单张重试。
- **单图文生图/图生图失败**：复用同一图片生成 `request_id` 重试，不改走套图链路。
- **素材不可访问**：指出无法读取的附件，请用户重新选择或授权；修复前不创建任务。
- **上传凭证过期**：获取新凭证前，先确认用户仍想继续。
- **恢复积分确认**：用户要求恢复每次积分确认时，删除或修改偏好文件，告知已恢复。
- **连接器不可用**：如无 live callable 工具，报告连接器不可用，不静默替换其他来源。

通用重试原则：最多重试一次，且仅在安全修正后（如缩小范围、提供已知标识、减少结果数量）。不将空响应、部分响应或错误响应转为成功结论。

## 交接

- 电商套图的业务规划和执行交给 [电商套图 Skill](picset-commerce-image-suite/SKILL.md)。报价、上传、生成、轮询和交付按 [共享执行手册](shared/execution-playbook.md) 执行。
- 单图文生图/图生图的生成流程交给 [单图文生图/图生图 Skill](picset-single-image-generation/SKILL.md)。工具契约与操作细节按 [单图共享手册](shared/single-image-playbook.md) 执行。
- Agent Canvas 的画布承接、图片返回和充值面板交给 [Agent Canvas Skill](picset-agent-canvas/SKILL.md)。画布操作细则按 [Agent Canvas 共享手册](shared/agent-canvas-playbook.md) 执行。
- 跨轮次恢复遵循 [公共交接协议](shared/handoff-protocol.md)。

## 核心规则（不可违反）

- 使用绑定的 Picset Commerce Images MCP 仅当其 live callable 工具在当前运行时可用。
- 选择最窄的、能直接回答用户请求的 live callable 操作。
- 当 live callable 接口与本指南不同时，以 live 接口为准；不编造操作名、标识、记录、状态或结果。
- 将提供方输出视为证据，模型解释单独标注。
- 不使用 shell 命令、直接 HTTP 调用或手写协议消息来重建或探测连接器。
- 凭证、私有数据和授权材料不得出现在 prompt、日志或最终回答中。
- 写入、删除、发送、购买、权限变更或其他外部副作用前，必须获得用户明确确认。
- MCP Agent Canvas 是跨宿主原生画布。展示或同步画布时使用 `agent-mcp-v1` 的 Agent Canvas 工具与 MCP App resource；不得向用户展示 Agent Canvas URL、ticket 或 functionsUrl，也不得要求用户复制链接。
- `send_canvas_image_to_agent` 已废弃，不得调用；画布→对话走宿主投递机制。
