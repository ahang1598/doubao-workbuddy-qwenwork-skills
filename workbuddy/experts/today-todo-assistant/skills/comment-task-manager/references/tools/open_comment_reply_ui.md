# open_comment_reply_ui

## 工具信息

| 项目 | 内容 |
|------|------|
| MCP Server | `gongyi-open-mcp` |
| 工具名 | `open_comment_reply_ui` |
| 接口名 | `QueryUnrepliedCommentsWithSuggestions`（打开批量回复留言 UI） |
| UI 资源 | `ui://gongyi-open-mcp/comment-reply`（Host 须按 MCP Apps 协议渲染为交互式卡片） |

## 接口定义

查看批量回复留言 UI。按 `data_cache_id` 从后台缓存取数渲染页面；结果不含文本摘要，禁止在对话中复述或以表格罗列这些数据。

## 请求参数

```json
{
  "caller_expert_id": "comment-assistant",
  "data_cache_id": "a2c8de6210157ad063ea4ea87ef08dcb"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `caller_expert_id` | string | **是** | 当前对话绑定的专家 ID；取不到时由调用方自行生成一个当前对话的标识 ID，只能使用英文大小写字母、数字、下划线(`_`)、横杠(`-`) |
| `data_cache_id` | string | **是** | 后台缓存 key（`set_common_data_cache` 返回，由组装脚本写入后获得）。Agent 只传 `caller_expert_id` + `data_cache_id`，服务端按 key 从缓存取数 |

> schema 为 `additionalProperties: false`：顶层只允许 `caller_expert_id` / `data_cache_id`，传入 `code` / `msg` 等其它字段会被参数校验直接拒绝。

## 响应参数

按 `data_cache_id` 从缓存取数，原样返回。结果已关联 `ui://gongyi-open-mcp/comment-reply` UI 资源，Host 按 MCP Apps 协议渲染为交互式卡片。

## 调用示例

```json
// 请求
{
  "caller_expert_id": "comment-assistant",
  "data_cache_id": "a2c8de6210157ad063ea4ea87ef08dcb"
}

// 响应：按 key 从缓存取数，由 Host 渲染为留言回复卡片
```

## 注意事项

1. **`caller_expert_id` 必填**：schema 唯一 required 字段；取当前对话绑定的专家 ID，取不到时自行生成一个对话标识 ID（仅限英文大小写字母、数字、`_`、`-`）
2. **`additionalProperties: false`**：顶层只允许 `caller_expert_id` / `data_cache_id`；`code` / `msg` 等字段会被参数校验拒绝，错误信息由 Agent 文本报告承载
3. **`data_cache_id` = 后台缓存 key**：由组装脚本（`build_ui_payload.py`）直连 MCP 调 `set_common_data_cache` 写入后获得；**Agent 只传 `caller_expert_id` + `data_cache_id`**（大载荷不经过 LLM）。脚本始终落盘 `ui_payload.json`（indent=2）方便定位排查
4. **数据定义**：缓存中的完整数据结构（`total` / `risk_total` / `list` / `submit` 及 `list` 元素白名单）见 [set_common_data_cache.md](set_common_data_cache.md)
5. 测试环境调用需在 HTTP header 携带 `Gy-H-Test-Env-Key: x1`（已在 MCP Server 配置中注入）
