---
name: todo-list-fetcher
description: 查询机构今日待办聚合。由 today-todo-assistant（Lead 主理人）在「查询总体待办」或「直达指定类型」阶段调用，经本 skill 的 Python 脚本调用 get_org_todo_list 聚合接口，输出可点击列表。本 skill 只做聚合查询，不召唤任何子专家。
---

# 今日待办聚合查询

## 职责边界

- **只查不调**：`fetch_todo_list.py` 聚合四类待办数据，输出展示文案。
- **不召唤子专家**：子专家只在用户点击对应选项后，由 Lead 通过 Agent 工具召唤。
- **Lead 不能直接调用 `get_org_todo_list`**：该接口仅由本脚本经 MCP 客户端调用。Lead 获取四类待办数据的唯一方式是运行本脚本，严禁裸调该 MCP 工具。

## 使用方式

```bash
# 主路径聚合查询（不含备案号明细）
python skills/todo-list-fetcher/scripts/fetch_todo_list.py

# 备案号直达（含备案号明细列表 filing_options）
python skills/todo-list-fetcher/scripts/fetch_todo_list.py --include-filing-list
```

## 输出契约

标准输出为扁平 JSON：

```json
{
  "org": { "org_no": "123456", "org_name": "XX 市慈善基金会" },
  "has_message": true,
  "has_invoice": true,
  "has_filing": false,
  "has_cert": true,
  "items": [
    {"key": "message", "type": "message", "option_data": "[留言处理]有36条留言待处理, 其中2条高风险留言, 我来协助你处理"},
    {"key": "alert",   "type": "alert",   "kind": "cert", "option_data": "[证件更新]法人身份证在 8 天后到期, 请尽快更新证件, 我来协助你更新"},
    {"key": "invoice", "type": "invoice", "option_data": "[待开票任务]还有 122 张票据待处理, 我来协助你批量识别并提交"}
  ]
}
```

- `org`：机构信息（`org_no` / `org_name` 等），供 Lead 做机构提示。
- `has_message` / `has_invoice` / `has_filing` / `has_cert`：四类待办的布尔标记，供「直达指定类型」路由与「指定类型为空时推荐其他待办」判断。
- `items`：仅包含 `option_data` 非空项（即该类别存在待办）。`option_data` 为脚本拼好的完整展示文案，Lead 只透传、不拼装。
- `type` 为点击路由键：`message`→comment-assistant、`alert`→alert-expert、`invoice`→invoice-expert。
- `alert` 额外返回 `kind`（`cert`/`record`/`both`），供 Lead 转发时携带，子专家内部按 `kind` 分流。
- `filing_options`：仅当命令行传 `--include-filing-list` 时返回（备案号明细列表，供 Lead 弹备案号选项），防 Lead 在未指定备案号时误用。每个元素字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| key | string | `project_no`（项目编号），供 Lead 兜底匹配 |
| option_data | string | 拼好的备案号展示文案，含 `project_no` + 项目名 + 剩余天数；审批中（`fund_raising_program_audit_status=2`）时追加"【审批中】"标注 |

`filing_options` 示例（`--include-filing-list` 且 `has_filing=true`）：

```json
"filing_options": [
  { "key": "224328", "option_data": "[备案号更新]224328 项目A 的备案号在 5 天后到期" },
  { "key": "224329", "option_data": "[备案号更新]224329 项目B 的备案号在 12 天后到期, 【审批中】备案号更新中, 请等待审批通过后再修改" }
]
```

## 错误契约

- 接口不可用（网络/鉴权/服务端错误）时，脚本打印 `{"success": false, "error_code": "auth_failed|mcp_error", "message": "...", "need_refresh": true/false}` 并以退出码 1 结束。
- `need_refresh=true` 表示 MCP 鉴权失败（token 过期/缺失），agent 侧处理见 `skills/_common/README.md`。
- **绝不降级展示假数据**：接口不可用时 Lead 如实告知用户，不拼装空列表/占位文案。
