---
keyword: block_delete
---

**功能**：原子删除一个或多个块或行内对象

### block_delete：删除 block

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_delete \
  --block-id "<obsolete_block_id>"
```

`--block-id` 可传一个 ID。当前 CLI 帮助明确支持逗号分隔时，一次可传最多 1000 个非空且不重复的 ID。目标不能相互包含，例如同一请求不能同时删除段落和段落里的图片。任一目标失败时，整批不写入。回执里的 `updated_blocks_count=1` 表示命令成功，实际删除数量可能更多。

## 图表删除

删除图表时，`--block-id` 使用 Fetch 返回的 chart record ID。`CHART_CAPABILITY_UNAVAILABLE` 表示当前客户端不支持图表操作，按[异常处理](../../workflows/canvas-doc-recovery.md)处理，不转用私有接口。