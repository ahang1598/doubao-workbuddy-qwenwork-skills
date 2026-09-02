---
name: image-creator
display_name: 图片模型指南
display_name_en: Image Model Guide
description: "本技能应在用户需要生成或编辑图片、尚未指定模型、需要图片模型选型，或需要统一执行图片生成时使用。用户明确指定 GPT-Image、Nano-Banana、Seedream 等模型时，可同时加载对应模型专属技能补充提示词知识，但工具调用仍由本技能负责。"
description_zh: "通过 AI-HIVE 的 100+ 模型能力完成图片选型、提示词整理、参考图上传与图片生成。"
description_en: "Routes image tasks across AI-HIVE's 100+ model capabilities and executes the selected image workflow."
category: design
version: 1.1.1
author: 极睿科技（Infimind）/ AI-HIVE 团队
permissions:
  provisional: true
  read:
    - 仅限当前对话中用户主动选择的本地图片
  network:
    - 仅通过已启用的 AI-HIVE Connector 调用 get_user_info、list_models、upload_media_from_path、generate_image 与 get_generation_task
triggers:
  - "生成图片"
  - "编辑图片"
  - "图片模型选型"
  - "营销海报"
  - "商品主图"
  - "PPT 配图"
---

# 图片模型指南

## 职责边界

本技能负责图片任务的路由与执行。模型专属技能只补充该模型的提示词和参数建议，不得另起一套工具字段。

以下情况不要创建图片任务：用户只要咨询或 Prompt、未授权读取本地素材、Connector 未连接、实时目录没有合适模型，或用户尚未确认费用。

## 工作流

1. 明确用途、主体、风格、画幅、数量、文字要求和参考素材。
2. 需要执行时调用 `get_user_info`，再调用 `list_models` 并设置 `modelType=IMAGE`。
3. 只从实时结果中选择模型和路由；价格、模型数量与能力不凭记忆判断。
4. 有参考图时，经用户授权后调用 `upload_media_from_path`，把返回值放入 `imageMediaIds`。
5. 根据所选模型的 `imageConfig` 组装 `params`；批量使用 `batchSize`。
6. 展示模型、路由、批量、主要参数和价格摘要，取得用户确认。
7. 调用 `generate_image`，随后用真实 `taskId` 调用 `get_generation_task`。
8. 按 [工具契约](../references/tool-catalog.md) 和 [错误处理](../references/error-catalog.md) 完成交付。

## Prompt 合同

Prompt 优先描述主体、场景、构图、视觉风格、光线、材质和需要准确呈现的文字。接口参数独立放入 `params`，不混入 Prompt。

用户指定模型时读取相应模型专属技能；未指定时可参考 [模型场景](../references/model-scenarios.md) 和 [提示词优化](../references/prompt-optimization.md)。

## 付费安全

- 每次图片生成都必须有明确的用户执行意图和当次费用确认。
- 任务处于 `PENDING`、`SUBMITTED` 或 `PROCESSING` 时只查询原任务。
- `FAILED` 时展示 `failure.code`、`failure.summary`、`failure.suggestion`，不自动创建新任务。
- 调整 Prompt、参数、模型、路由或批量后的调用属于新付费任务，必须重新确认。

## 输出

- 执行前：模型、路由、Prompt 摘要、参数、批量、参考素材职责和价格摘要。
- 完成后：`taskId`、结果 URL、实际返回元数据和复用建议。
- 未完成：当前真实状态和 `taskId`。
- 失败：用户可见失败字段和下一步选择。
