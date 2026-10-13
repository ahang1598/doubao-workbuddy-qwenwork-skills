# 运行时（runtime）文档索引

> 仅在「派发 / 查询 / 催办 / 报表 / 统计」等**高频或周期性**操作时加载本目录。
> 一次性的绑定 / 维护门店 / 维护模板 / 分享配置请改读 `../setup/`。

---

## 场景 → 文档 速查表

| 场景 | 跳转 |
| :--- | :--- |
| 立即派发某模板的当日任务 | [01-dispatch.md#手动派发init--notify-两步](./01-dispatch.md#手动派发init--notify-两步) |
| 用户已提供表单分享链接想直接派发 | [01-dispatch.md#携带-form_url-的两步式](./01-dispatch.md#携带-form_url-的两步式) |
| `dispatch init` 中断 / 用户后回复链接 | [01-dispatch.md#form_url-缺失时的处理agent-必读](./01-dispatch.md#form_url-缺失时的处理agent-必读) |
| 想搞清楚派发内部到底走了哪几步 | [dispatch-internals.md](./dispatch-internals.md) |
| 查询任务实例（按自定义字段筛选） | [01-dispatch.md#查询任务实例记录](./01-dispatch.md#查询任务实例记录) |
| 查"哪些店还没填表" | [02-monitor.md#查询未填写名单催办场景](./02-monitor.md#查询未填写名单催办场景) |
| 查"某店通知发出去了吗" | [02-monitor.md#查询通知发送状态](./02-monitor.md#查询通知发送状态) |
| 再催一遍未完成门店 | [01-dispatch.md#二次催办--only-pending](./01-dispatch.md#二次催办--only-pending) |
| 立即推一份某模板的汇总报表 | [03-summary.md#生成报表](./03-summary.md#生成报表) |
| 看模板使用率 / 完成率 / 门店表现 / 时间趋势 | [04-stats.md#查看统计](./04-stats.md#查看统计) |
| 获取某条记录附件字段的下载链接 | 见下方 [附件下载链接](#附件下载链接) |

> 完整子命令清单以 `uv run python scripts/cli.py <dispatch|monitor|summary|stats> --help` 为准，本目录文档只承担「业务决策」。

---

## 共同前置约束

- 任何业务操作前先 `init validate`（步骤 1，见 SKILL.md 工作流）
- **禁止绕过 CLI 直接调 dws / aitable**，详见 `../shared/hard-constraints.md#H1`
- 多模板时未指定 ID 必须先列模板让用户确认，详见 `../shared/hard-constraints.md#H5`
- 字段定义、占位符、统计口径见 `../shared/data-model.md` 与 `../shared/placeholders.md`

---

## 附件下载链接

当用户需要获取 AI 表格中附件字段（照片、视频、文档等）的下载地址时，使用 `attachment get-urls` 命令：

```bash
cd <SKILL_DIR> && uv run python scripts/cli.py attachment get-urls \
  --base-id "<BASE_ID>" --table-id "<TABLE_ID>" --field-id "<FIELD_ID>" \
  [--record-id "<RECORD_ID>"] [--limit N] [--url-only]
```

- **`--field-id`**：目标附件字段的 fieldId（可通过 `dws aitable field get` 查询，`type` 为 `"attachment"` 的字段）
- **`--record-id`**：可选，指定单条记录；不传则返回所有记录的附件链接
- **`--url-only`**：仅输出 URL，每行一个，适合管道处理

> 附件 URL 为 OSS 临时签名链接，有时效性；过期后重新调用即可获取新链接。详见 [`docs/aitable-attachment-download-guide.md`](../../docs/aitable-attachment-download-guide.md)。
