---
name: invoice-info-fetcher
description: 票据专家的查询计数能力。经脚本调用 get_user_and_org_info + get_pending_invoice，返回待开票任务总数与机构上下文。
---

# 票据专家 · 查询计数

## 职责边界

- **只查计数，不拉明细**：本 skill 唯一用途是查询待开票任务总数（`total`）。
- **Agent 不直调 MCP 工具**：`get_user_and_org_info` / `get_pending_invoice` 仅由 `scripts/query_invoice_count.py` 经 `mcp_client` 内部调用。

## 使用方式

```bash
python skills/invoice-info-fetcher/scripts/query_invoice_count.py
```

## 输出契约

标准输出为扁平 JSON：

```json
{ "org": { "org_no": "...", "org_name": "..." }, "total": 10, "title": "待开票任务", "subtitle": "还有 10 张票据待处理, 我来协助你批量识别并提交" }
```

- `org`：机构上下文（`org_no` / `org_name`），供 agent 做机构提示
- `total`：待开票任务总数（机构维度全量，跨页一致）
- `title` / `subtitle`：由脚本组装的展示文案（`total === 0` 时两者留空）

## 错误契约

- 接口不可用（网络/鉴权/服务端错误）时，脚本打印 `{"success": false, "error_code": "auth_failed|mcp_error", "message": "...", "need_refresh": true/false}` 并以退出码 1 结束。
- `need_refresh=true` 表示 MCP 鉴权失败（token 过期/缺失）：agent 应调用 `get_mcp_token` 重新获取并落盘后重试。
- **绝不降级展示假数据**：接口不可用时 agent 如实告知用户，不拼装空计数/占位文案。
