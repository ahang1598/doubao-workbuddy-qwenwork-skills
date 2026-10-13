# Case 019: template preview 流程护栏验证

## 测试目标
验证 Agent 创建模板时严格遵循 preview → create 两步流程，不跳过 preview 直接 create。

## 预期行为
- Agent 先执行 `template preview`（含 --scene 参数）获取完整预览
- Agent 将预览中的派发消息模板完整展示给用户
- 用户确认后 Agent 才执行 `template create`（传入 --message-title 和 --dispatch-message）
- 严禁跳过 preview 直接 create
