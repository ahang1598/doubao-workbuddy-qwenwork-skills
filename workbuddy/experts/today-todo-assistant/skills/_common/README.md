# MCP 客户端公共约定

本目录的 `mcp_client.py` 是本专家包所有 Python 脚本调用 MCP 接口的**通用请求层**。任何经它发起请求的脚本都遵循以下约定。各 skill 的 SKILL.md、agent 文档均引用本文件，不在各自正文重复。

## Token 约定

- Token 固定从全局路径 `~/.workbuddy/.gongyi_token` 读取。
- Token 缺失 / 鉴权失败（401）时，脚本打印 `{"need_refresh": true, ...}` 并以退出码 1 结束。

## 重新获取 token（两种触发场景共用同一操作）

1. 调用 `gongyi-open-mcp` 的 `get_mcp_token`（`caller_expert_id` 固定为当前专家包 ID，本包为 `"today-todo-assistant"`）获取最新 token；
2. 将 token 写入 `~/.workbuddy/.gongyi_token`；
3. 重新运行脚本 / 重新查询。

**若 `get_mcp_token` 调用本身失败，直接提醒用户连接 mcp，不再重试、不降级**：
- 「工具不存在 / 连接器未挂载」→ 提醒用户去连接 `gongyi-open-mcp` 连接器。
- 「鉴权失败 / 授权失效」→ 提醒用户在连接器上重新连接授权。

### 场景一：脚本鉴权失败（`need_refresh`，自动恢复）

脚本返回 `need_refresh=true` 时，按上述步骤恢复后重跑脚本。对 agent 编排主逻辑无感。

### 场景二：用户切换机构（刷新机构缓存）

用户表达"机构不对 / 切换机构 / 刷新机构缓存"时，按上述步骤重新绑定新机构后重新查询。由 agent 在编排层主动触发。