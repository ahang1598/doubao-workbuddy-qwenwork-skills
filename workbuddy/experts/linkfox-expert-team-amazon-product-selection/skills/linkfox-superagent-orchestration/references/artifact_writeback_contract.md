# Artifact / Result / Write-back Contract

## Concept Boundary

- Handoff: 交接下一段任务，让前端打开子 Agent 卡片或链接。
- Artifact: 子 Agent 或 Skill 产生的报告、brief、图片、视频、listing draft、数据文件等。
- Completion/result: 子 Agent 完成后的状态、摘要、artifactRefs 和后续建议。
- Write-back proposal: 准备写入业务实体前的提案。

## Write-back Rules

- 写回必须 confirmation。
- Agent 不直接改 Product Library、Keyword Library、Listing 或共享实体。
- proposal 应说明要写入什么、写到哪里、依据是什么、风险是什么。
- 用户确认后，由业务模块或正式 runtime API 执行写入。

## Result Card Rules

SuperAgent 主会话读取 child completion 后，应展示 result card，而不是把 handoff 当作结果。

Result card 至少表达：

- 子 Agent 名称
- 状态：completed / blocked / needs_input
- 简短摘要
- artifactRefs
- write-back proposal 状态
- blocker 信息（如有）
