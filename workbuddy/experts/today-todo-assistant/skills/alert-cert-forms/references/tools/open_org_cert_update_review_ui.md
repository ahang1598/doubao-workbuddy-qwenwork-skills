# open_org_cert_update_review_ui — 字段契约

> 本文件是调用 `open_org_cert_update_review_ui` MCP 工具时的唯一字段契约。
> 直接读取 `build_cert_ui_params.py --output` 写出的 JSON 文件作为完整工具参数，不得手抄、重组、增删字段、查询 schema 后另行拼参或改写任何值。

## 顶层结构（精简调用模式）

>
> | 字段 | 类型 | 必填 | 值 / 来源 |
> |------|------|------|-----------|
> | `caller_expert_id` | string | 是 | 由 `build_cert_ui_params.py` 固定为 `alert-expert` |
> | `data_cache_id` | string | 是 | 调用方存入公共缓存时返回的ID |