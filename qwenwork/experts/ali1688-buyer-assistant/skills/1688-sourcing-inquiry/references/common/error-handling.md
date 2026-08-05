# 错误处理

## MCP 调用失败

- 原样展示 MCP 返回的错误信息。
- 鉴权、401、Forbidden、token 过期等错误：提示用户检查 `ali1688-buyer` 连接器 OAuth 授权，必要时在连接器设置中重新授权。
- 限流、超时、服务异常：提示稍后重试。

## Python 后处理失败

- 检查传入内容是否为 `1688_procurement_digital_human_tool` 返回 JSON。
- 使用 `--mcp-result-file` 时确认文件路径存在且为 UTF-8 JSON。
- 使用 stdin 时确认已将完整 MCP JSON pipe 给命令。
- 参数缺失时追问用户补齐商品名称、采购数量、采购需求。

## 禁止

- 禁止提示用户配置 AK。
- 禁止调用浏览器、网页搜索或旧 HTTP 脚本降级。
- 禁止由 Agent 自行改写 MCP 原始返回为最终结果。
