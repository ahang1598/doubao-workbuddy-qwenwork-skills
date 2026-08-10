# 官方 MCP 接入与回查

用户在巨量开放平台的 MCP 页面完成账户授权，并复制由官方生成的 Remote MCP 配置。凭证由官方 MCP 配置承载，不写入 Skill、对话或请求模板。

在目标 AI 平台：

1. 添加官方生成的 Remote MCP 配置，选择 Streamable HTTP。
2. 将服务绑定到使用本 Skill 的应用；登记的服务 ID 约定为 `oceanengine-official-remote`。
3. 新开会话，先列出 MCP Tools，再查询授权账户和一个小时间窗的基础报表。
4. 三项均成功后才标记“默认版已接入”。未成功时只返回 `setup_required`，说明需由用户在官方页完成授权或绑定。

官方 MCP 的实际工具范围以工具列表为准。若没有某个报表层级或指标，保留 `null` 或 `unsupported`，不可用其他来源补造。
