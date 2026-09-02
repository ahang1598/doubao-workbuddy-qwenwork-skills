# Card Context Rule

当 loop 推荐或确认进入专业 Agent 卡片时，读取本 reference。

`<linkfox-suggestion-agent>` 可以渲染一个或多个可点击专业 Agent 卡片。点击卡片时，只携带该卡片上显式写明的 `context` 业务摘要。

## Context Content

卡片可以提供业务上下文：

```xml
<linkfox-suggestion-agent modeId="linkfox-listing-agent" context="用户想基于竞品 ASIN 优化 Listing；已完成初步分析，下一步适合深挖标题、五点和埋词；需保留用户给定站点、ASIN 和合规约束。">Listing 生成｜继续优化标题、五点和埋词</linkfox-suggestion-agent>
```

`context` 文本可以包含：

- 用户目标
- 已确认参数
- 当前主会话结论
- 推荐下一步
- 约束条件和输出格式

`context` 文本不要包含：

- 系统内部字段
- 工具调用参数
- 协议 JSON
- 完整报告正文
- 未在当前回复中明确展示的上下文

## Required User-Visible Meaning

如果用户通过卡片进入专业 Agent，用户可见含义应该是：

`点击卡片可进入对应专业 Agent，并携带本卡片中显式写明的业务摘要。`

用户可见文案要准确表达：这是一个可点击的后续专业方向，不是当前回复正文的一部分。不要暗示目标 Agent 已经拥有完整对话、文件或工具输出。

如果 workspace 无法打开，标记 blocker，不要假装成功。
