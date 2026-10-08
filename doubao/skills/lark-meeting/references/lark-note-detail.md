# note +detail

通过 `note_id` 查询会议纪要详情，获取下挂文档 Token（AI 智能纪要、逐字稿、会中共享文档）。只读操作。

## 命令

```bash
lark-cli note +detail --note-id <note_id>
```

## 输出

返回下挂文档 token（`note_doc_token`、`verbatim_doc_token`、`shared_doc_tokens`）、`note_display_type` 和 `meeting_id`（仅在该纪要由会议生成时返回）。各字段的详细用法见 [查询纪要及关联产物](../scenes/query-note-and-artifacts.md)。

## 反查关联会议

`meeting_id` 提供从纪要反向定位会议的入口，传给 `vc +detail --meeting-ids` 可继续查会议详情、参会人或反查日程（会议详情可含 `calendar_event_id`，用于再反查日程）。

查询成功后仍缺少 `meeting_id` 时，只说明未取得关联会议 ID，不据此断言纪要为手动创建，也不猜测 ID 反查；查询失败按实际错误处理。

## 相关场景
- [基于 note_id 查询纪要、逐字稿、共享文档等](../scenes/query-note-and-artifacts.md)
