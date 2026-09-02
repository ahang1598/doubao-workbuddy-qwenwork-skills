---
name: picset-agent-canvas
description: "Picset Agent Canvas（万能画布）：跨宿主原生画布，负责承接 Agent 生成的图片、用户在画布上修改后将图片返回给 Agent。画布不负责图片生成（生成由电商套图或单图文生图/图生图完成），也不负责充值（充值由连接器统一充值面板 open_agent_pricing 处理）。"
---

# Picset Agent Canvas

跨宿主原生画布能力入口。默认使用简体中文。

## 职责与边界

负责：
- **承接 Agent 生成的图片**：把电商套图或单图文生图/图生图的生成结果放入画布，供用户查看和编辑。
- **用户修改后返回图片到 Agent**：用户在画布上点击「加入当前对话」时，画布把选中图投递到宿主输入框，成为下一条消息的图片附件，Agent 收到后可继续编辑。

**不负责**：
- 图片生成——电商主图/详情/套图/Listing/A+ 由 [电商套图 Skill](../picset-commerce-image-suite/SKILL.md) 完成；独立创意单图/图片编辑由 [单图文生图/图生图 Skill](../picset-single-image-generation/SKILL.md) 完成。
- 单图文生图/图生图的生成流程——详见 [单图共享手册](../shared/single-image-playbook.md)。
- 充值套餐面板——积分不足或用户要充值时，由连接器统一充值面板处理，详见 [连接器充值手册](../shared/connector-pricing-playbook.md)，工具为 `open_agent_pricing`。

细则与工具契约一律按 [Agent Canvas 共享手册](../shared/agent-canvas-playbook.md) 执行，本 Skill 不重复展开。

## 画布承接流程

生成任务（电商套图或单图文生图/图生图）完成后，若需把结果同步到画布：

1. **新图插入**：调用 `insert_agent_canvas_image`，传入 `agentCanvasSessionId`、`request_id` 和 `image`（含 `url`）。
2. **替换已有图**：调用 `replace_agent_canvas_image`，传入 `agentCanvasSessionId`、`request_id`、`targetImageId` 和新 `image`。
3. **打开画布**：若用户要求打开画布查看或继续编辑，调用 `open_agent_canvas`，传入 `conversation_id`。
4. **panelActive 判断**：
   - `panelActive: true` 时写回流程结束，**不得**再调用 `open_agent_canvas`。
   - `panelActive: false` 且宿主没有打开工具结果返回的 UI 时，才可使用同一个 `conversation_id` 调用 `open_agent_canvas` 兜底。

## 画布 → 对话

用户在画布上点击「加入当前对话」时，面板把选中图投到宿主输入框（下一条消息附件），**不经过任何 MCP 工具**。

- Agent 不必触发任何工具；收到带图消息即作为修改上下文。
- 勿再调用工具或索要图片地址。
- `send_canvas_image_to_agent` 已废弃，不得调用。

## 套图与单图结果写回画布

电商套图经 `present_files` 交付后，若需同步到画布，按 [Agent Canvas 共享手册](../shared/agent-canvas-playbook.md) 的写回章节执行。单图文生图/图生图的结果写回同理。

## MCP 工具速查

| 工具 | 用途 | 调用阶段 |
| --- | --- | --- |
| `open_agent_canvas` | 打开/复用画布 Panel | 打开画布 |
| `get_agent_canvas_state` | 读取画布状态摘要 | 画布状态 |
| `insert_agent_canvas_image` | 插入图片到画布 | 结果承接 |
| `replace_agent_canvas_image` | 替换画布中目标图片 | 结果承接 |

调用 MCP 工具前，必须使用 `tool_search` 按工具名获取完整参数定义，再按取回的定义发起调用。运行时工具名可能带有后缀，以 `tool_search` 返回的实际名称为准。

> 注 1：`generate_agent_canvas_image` 和 `get_agent_canvas_image_status` 属于单图文生图/图生图能力，由 [单图文生图/图生图 Skill](../picset-single-image-generation/SKILL.md) 调用，不在本画布能力的工具范围内。
> 注 2：`open_agent_pricing` 属于连接器统一充值面板，详见 [连接器充值手册](../shared/connector-pricing-playbook.md)，不在本画布能力的工具范围内。
