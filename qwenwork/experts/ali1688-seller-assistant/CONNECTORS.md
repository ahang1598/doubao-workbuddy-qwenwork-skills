# 连接器说明

本套件通过 `.mcp.json` 预配置了 MCP 连接器，安装后自动注册到 QoderWork。

## 连接器：ali1688-seller

- **协议**: MCP (Streamable HTTP)
- **端点**: `https://mcp.1688.com/mcp/qoderwork-seller`
- **认证**: OAuth 2.1（安装后首次使用时触发授权流程，授权一次即可）
- **工具总数**: 16 个

该 server 暴露 16 个独立工具，各 skill 在自己的 SKILL.md 中声明所需工具及调用规则，运行时 agent 直接按工具名调用。