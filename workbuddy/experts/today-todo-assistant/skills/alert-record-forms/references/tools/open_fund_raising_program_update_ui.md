# open_fund_raising_program_update_ui — 字段契约

> 本文件是调用 `open_fund_raising_program_update_ui` MCP 工具时的唯一字段契约。
> 仅当 `run_record_ui.py` stdout 返回 `state=PAYLOAD_BUILT` 时，直接使用同一 JSON 中的 `caller_expert_id` 与 `data_cache_id` 调用工具；不写入或读取 UI 参数文件，不查询 schema，不重组或改写值。

## 顶层结构（精简调用模式）

| 字段 | 类型 | 必填 | 值 / 来源 |
|------|------|------|-----------|
| `caller_expert_id` | string | 是 | 由 `run_record_ui.py` stdout 返回 |
| `data_cache_id` | string | 是 | `run_record_ui.py` 写入公共缓存后在 stdout 返回的 ID |
