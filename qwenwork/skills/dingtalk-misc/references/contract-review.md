# 合同审核（新链）命令参考

命令前缀主入口为 `dws contract-review`。千问办公同时提供空格路径别名 `dws contract review <同名叶子>`，与主入口执行同一套 MCP。所有调用追加 `--format json`。本产品对应 law-ai 新审核 MCP：`contract_review_*`，与旧版 `createContractReviewTask` / `contractAnalysis` 无关。

## 能力范围与边界

Use when：用户要对合同文件发起 AI 审核（准备上传、按 URL 上传、确认开审、查状态/结果）。

Avoid when：

- 合同台账、批量导入、听记起草、归档、项目、相对方、账款：若本发行版提供 `dws contract`，走台账产品，不要混用本命令族。
- OA 审批实例走 `dws oa`；钉盘文件元数据走 `dws drive`。

## 标准流程

1. `prepare-upload` 取得 `upload_url` / `file_url`；调用方 HTTP PUT 文件到 `upload_url`。
2. 生成 `session_id`（建议 `sess_` 前缀），用 `upload` 传入 `file_url` + `filename`，保存返回的 `review_id`。
3. 根据 `upload` 返回的 `recommended`，用 `confirm` 开审；用户指定了立场/尺度/类型时须显式传入对应 flag，否则服务端沿用 recommended（常为中立）。
4. `get-status` 轮询；未完成只报告处理中。
5. 完成后 `get-result` 取结果；未完成不得宣称审核已完成。

若调用方已有可用 HTTPS `file_url`，可跳过步骤 1。

## 命令

| 命令 | 必填参数 | 用途 |
|---|---|---|
| `dws contract-review prepare-upload` | `--filename` | 申请 OSS 预签名 PUT/GET |
| `dws contract-review upload` | `--session-id`, `--file-url`, `--filename` | 按 URL 创建审查 |
| `dws contract-review confirm` | `--session-id`, `--review-id` | 确认参数并开审（`--action` 默认 `start`；可选 `--contract-type` / `--standpoint` / `--scale` / `--checklist-id` / `--custom-rules`；后两者互斥） |
| `dws contract-review get-status` | `--session-id` | 查询状态（`--review-id` 可选） |
| `dws contract-review get-result` | `--session-id` | 查询结果（`--review-id` 可选） |

```bash
dws contract-review prepare-upload --filename 采购合同.docx --format json
dws contract-review upload --session-id sess_demo1 --file-url "<FILE_URL>" --filename 采购合同.docx --format json
dws contract-review confirm --session-id sess_demo1 --review-id <REVIEW_ID> --action start --standpoint 甲方立场 --scale 均势 --format json
dws contract-review confirm --session-id sess_demo1 --review-id <REVIEW_ID> --custom-rules '[{"name":"账期","description":"须写明付款期限"}]' --format json
dws contract-review get-status --session-id sess_demo1 --review-id <REVIEW_ID> --format json
dws contract-review get-result --session-id sess_demo1 --review-id <REVIEW_ID> --format json
```

## 命令与 MCP 能力映射

仅用于诊断；不要绕过 CLI 直接调 MCP：

| CLI | MCP tool |
|---|---|
| `prepare-upload` | `contract_review_prepare_upload` |
| `upload` | `contract_review_upload` |
| `confirm` | `contract_review_confirm` |
| `get-status` | `contract_review_get_status` |
| `get-result` | `contract_review_get_result` |
