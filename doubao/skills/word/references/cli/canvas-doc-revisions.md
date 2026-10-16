# 本地 Word 修订与待审内容

本页用于本地 Word 的修订模式和待审内容。先读 [`canvas-doc-fetch.md`](canvas-doc-fetch.md) 与 [`canvas-doc-update.md`](canvas-doc-update.md)；使用这些契约列出的参数，CLI 返回未知参数或有版本漂移证据时再查看当前 `--help`。未开放的查询或控制操作须报告不可用。

## 写入边界

- `--revision-id` 是编辑基线，不是待审修订 ID。修订开启时，每次写入成功后重新读取，后续写入使用新的基线。
- 主文档中受支持的文本、段落、行内图片与 Drawing/Chart 子集、表格、样式、Field 结果及浮动对象层级/变换可产生待审修订。行内 Drawing 可插入/删除，行内 Chart 可删除或修改尺寸；表格单元格的内边距、不换行和首选宽度也有受支持的写入路径。具体操作仍以相应专项和写后回读为准；不能据此推断页眉页脚、锚定 Drawing/Chart 或任意属性都可修订。
- 水印、自动目录、图表数据替换、整文件 OOXML 更新及浮动对象迁锚/复制不能作为修订写入路径。图表数据创建不修改正文，也不会产生修订；修订开启时不用其他写法绕过限制。
- 即使关闭修订，也须避开已有待审内容；冲突时先处理相关修订，或重读后选择不相交目标，不原样重试。

## 查询与审阅

接受/拒绝前用 `revisions` 读取 `data.command_result.revisions` 和 `state_fingerprint`；需要判断修订前后文本时，也以修订项区分的待删除、待插入内容为准，不从普通正文投影推断。默认每页 100 项、上限 500；结果 `truncated=true` 时，在查询条件不变的情况下将 `next_cursor` 原样传给下一次 `--cursor` 查询，直至读完；游标失效则从第一页重查。可用 `revision_ids` 过滤最多 1000 个唯一 ID，空列表等同不筛选；未知 ID 会失败。只用当前查询返回的 ID，决议时把 `state_fingerprint` 填入 `expected_state_fingerprint`。`revision` 命令不传顶层 `--revision-id`：

| action | 额外参数 | 作用 |
|---|---|---|
| `accept/reject` | `revision_ids`：1..1000 个唯一待审修订 ID；`expected_state_fingerprint` | 选择性接受/拒绝 |
| `accept_all/reject_all` | `confirm_all=true`；`expected_state_fingerprint` | 全量接受/拒绝，须显式确认 |
| `set_mode` | `document_mode=editing\|revising\|reading`；可选 `show_revisions:boolean` | 切换工作模式，并可同时控制修订展示 |
| `set_tracking` | `track_revisions:boolean` | 只更改持久化的修订追踪设置 |

`document_mode` 决定后续 AI 编辑按修订或普通编辑执行。省略 `show_revisions` 时，`revising` 默认展示修订，`editing/reading` 默认隐藏；显式传入可覆盖展示值。展示开关只控制正文修订标记和右侧卡片，不处理待审修订，也不改变 `track_revisions`。回执始终包含生效的 `show_revisions`，`changed` 计入展示变化。

模式和追踪控制不需要先查询修订，也不传 `expected_state_fingerprint`。同轮已取得的 `document_mode`、`show_revisions` 和 `track_revisions` 直接复用；仅在回执明确改变状态、更新返回 revision 冲突或状态未知时重新读取。当前仅因工作模式为 reading 时，可切回 editing/revising；宿主只读或文档保护仍会拒绝。`document_mode=revising` 时，所有内容修改必须以修订形式记录，禁止普通编辑直接落盘；Local 提示重读时只重读一次，确认不支持后立即返回 `local_unsupported_runtime`，不反复重试。决议成功后重新查询，再处理剩余修订；状态指纹失效、目标不可审阅或权限不足时停止。回执用 `changed` 判断是否修改，决议的处理 ID 位于 `reviewed_revision_ids`；`updated_blocks_count=0` 不代表未处理修订。

不能凭可见文字或 OOXML 标记猜待审修订 ID。修订模式下不能直接整文件回写；Local 明确不支持结构化修订时，先切到 `editing` 并确认，再通过 OOXML 仅以 `w:ins` / `w:del` 记录本轮内容变化，提交完成后恢复 `revising`。

## 验收

写后回读待审修订和目标内容，确认修订已产生、非目标内容未变；修订态正文投影可能同时包含插入与删除文字，不用普通纯文本全文 diff 推断接受态，以修订列表和目标块回读验收。接受或拒绝后核对最终内容和剩余修订。能力不支持、权限不足或版本冲突时不能报告成功；保存重开及桌面显示须另行验证。

===== 全文完 =====
