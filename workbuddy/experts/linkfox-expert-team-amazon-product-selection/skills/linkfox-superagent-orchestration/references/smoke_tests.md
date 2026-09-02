# Manual Smoke Tests

这些用例只用于人工上线后验证，不是生产 Skill 行为示例。

## 1. Main Agent Direct Answer

输入普通解释类问题。

期望：主 Agent 直接回答，不强制 handoff。

## 2. Product Validation Handoff

输入一个商品验证类任务，包含站点和商品标识。

期望：SuperAgent 先补必要字段，再输出 targetAgent=product-validation 的 handoff intent；前端显示卡片或链接。

## 3. Market Analysis Handoff With Long Context

输入较长竞品/市场背景，并要求交给市场分析 Agent 深做。

期望：handoff 中出现 contextSummary、keyFacts、constraints、sourceRefs、artifactRefs；不复制完整聊天全文。

## 4. Child Task Open

点击 handoff 卡片或链接。

期望：进入对应子 Agent 任务，携带 userGoal、intakeContext、sourceRefs/artifactRefs。

## 5. Write-back Boundary

要求把结果写回业务库。

期望：只输出 write-back proposal，等待用户确认；不能静默写入。

## 6. Runtime Blocker

在 ACP/session/积分不可用时触发深度任务。

期望：明确 blocker，不显示 demo success。
