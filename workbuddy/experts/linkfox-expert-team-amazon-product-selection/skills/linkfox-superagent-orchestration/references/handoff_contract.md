# Handoff Contract

handoff 是任务交接结果，不是 Skill 调用，也不是最终 artifact。

## Required Fields

- type: 固定为 handoff。
- targetAgent: product-validation / market-analysis / image-generation / video-generation / listing-generation。
- parentTaskId: 主 Agent 任务 id；运行时可用时填写。
- childTaskId: 子 Agent 任务 id；运行时可用时填写。
- sourceConversationId: 来源会话 id；运行时可用时填写。
- userGoal: 用户目标的精简表达。
- contextSummary: 对当前任务上下文的压缩总结。
- keyFacts: 子 Agent 必须知道的事实列表。
- constraints: 用户要求、业务限制、合规限制、预算、站点、风格等约束。
- intakeContext: 主 Agent 已收集并归一化的字段。
- sourceRefs: 长文本、文件、表格、URL、消息、记录等来源引用。
- artifactRefs: 已生成或已存在的 artifact 引用。
- writeBackRequiresConfirmation: 只要可能涉及业务实体写回，就必须为 true。

## Context Compression Rules

- 不复制完整聊天全文。
- 不把大段竞品资料、CSV、HTML、图片列表直接放入 handoff。
- 长内容放 sourceRefs 或 artifactRefs，由子 Agent 按需读取。
- keyFacts 只保留会改变子 Agent 判断的事实。
- constraints 要保留用户显式边界，不能被摘要吞掉。

## Failure Rules

- 缺少关键 intake 时，先在主会话补字段。
- targetAgent 不明确时，先澄清，不猜。
- 运行时无法创建子任务时，返回 blocker，不伪造 child task。
