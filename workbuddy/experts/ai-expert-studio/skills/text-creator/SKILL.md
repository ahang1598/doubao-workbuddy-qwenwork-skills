---
name: text-creator
display_name: 文本模型指南
display_name_en: Text Model Guide
description: "本技能应在用户需要通过 AI-HIVE 执行文本对话、写作、总结、翻译、结构化改写或文本模型选型时使用。只要用户仅需本地讨论且没有执行模型调用的意图，就不要触发付费调用。"
description_zh: "通过 AI-HIVE 的 100+ 模型能力完成文本模型选型与对话执行。"
description_en: "Routes text tasks across AI-HIVE's 100+ model capabilities and executes the selected text workflow."
category: writing
version: 1.1.1
author: 极睿科技（Infimind）/ AI-HIVE 团队
permissions:
  provisional: true
  read:
    - 仅限当前对话中用户主动选择的本地文档
  network:
    - 仅通过已启用的 AI-HIVE Connector 调用 get_user_info、list_models 与 chat_text
triggers:
  - "文本模型"
  - "AI-HIVE 对话"
  - "长文总结"
  - "结构化改写"
  - "多语言写作"
---

# 文本模型指南

## 工作流

1. 明确任务、目标读者、输入材料、长度和格式。
2. 需要执行时调用 `get_user_info`，再调用 `list_models` 并设置 `modelType=TEXT`。
3. 从实时结果中选择 `publicModelId`、`routingMode` 及匹配的 `pricingSnapshot`。
4. 组装 `messages`；本地文档只有在用户明确授权并提供内容后才可使用。
5. 需要深度推理且模型能力支持时才设置 `thinkingEnabled`。
6. 展示模型、路由和价格摘要；用户确认执行后调用 `chat_text`。

完整字段见 [工具契约](../references/tool-catalog.md)，价格读取见 [模型与价格](../references/model-pricing.md)。

## 真实性与安全

- 不编造实时模型、价格、来源、引用或执行结果。
- 不要求用户在对话中粘贴 Token、密钥或 Connector 凭据。
- Connector 不可用时可以继续帮助整理内容，但不得声称已调用模型。
- 新的付费调用必须对应用户当前明确的执行意图。

## 输出

- 选型：候选、首选理由、路由和价格依据。
- 执行：所用模型、结果正文及工具明确返回的用量或费用信息。
- 失败：展示工具返回的安全错误摘要，不猜测内部原因。
