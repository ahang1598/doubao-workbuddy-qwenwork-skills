---
keyword: revisions
---

**功能**：读取和处理待审修订，管理文档模式、修订追踪与展示状态

**依赖关键词**：`local-update`

# 本地 Word 修订与待审内容

本页用于本地 Word 的修订模式和待审内容。`revisions` 是 `+local-fetch` scope，`revision` 是 `+local-update` command；读取见 [Canvas 读取](../canvas-doc-fetch.md)，公共写入参数见 `local-update`。CLI 返回未知参数或有版本漂移证据时再查看当前 `--help`。

## 写入边界

- `--revision-id` 是编辑基线，不是待审修订 ID。**修订模式的 Local 内容写入必须显式传入 `--revision-id`**；首笔使用写前 Fetch 的 `revision_id`，成功回执返回有效 `new_revision_id` 时，下一笔使用该值。未返回时先重新 Fetch，不复用旧值。
- 主文档中受支持的文本、段落、行内图片与 Drawing/Chart 子集、表格、样式、Field 结果及浮动对象层级/变换可产生待审修订。行内 Drawing 可插入/删除，行内 Chart 可删除或修改尺寸；表格单元格的内边距、不换行和首选宽度也有受支持的写入路径。支持范围见对应专项；不能据此推断页眉页脚、锚定 Drawing/Chart 或任意属性都可修订。
- 水印、自动目录、图表数据替换及浮动对象 reanchor/copy 不支持产生可审阅修订；图表数据 `create` 不修改正文，也不产生修订。修订开启时不得改为普通编辑绕过限制。
- 未经用户明确要求，禁止接受或拒绝任何修订，也不得以此规避编辑报错；即使关闭修订也须避开已有待审内容，Local 无法完成时按 Canvas 路由转 OOXML，并保留既有待审修订。

## 查询与审阅

接受/拒绝前用 `revisions` 读取 `data.command_result.revisions` 和 `state_fingerprint`；需要判断修订前后文本时，也以修订项区分的待删除、待插入内容为准，不从普通正文投影推断。默认每页 100 项、上限 500；结果 `truncated=true` 时，在查询条件不变的情况下将 `next_cursor` 原样传给下一次 `--cursor` 查询，直至读完；游标失效则从第一页重查。可用 `revision_ids` 过滤最多 1000 个唯一 ID，空列表等同不筛选；未知 ID 会失败。只用当前查询返回的 ID，决议时把 `state_fingerprint` 填入 `expected_state_fingerprint`。`revision` 命令不传顶层 `--revision-id`：

| action | 额外参数 | 作用 |
|---|---|---|
| `accept/reject` | `revision_ids`：1..1000 个唯一待审修订 ID；`expected_state_fingerprint` | 选择性接受/拒绝 |
| `accept_all/reject_all` | `confirm_all=true`；`expected_state_fingerprint` | 全量接受/拒绝，须显式确认 |
| `set_mode` | `document_mode=editing\|revising\|reading`；可选 `show_revisions:boolean` | 切换工作模式，并可同时控制修订展示 |
| `set_tracking` | `track_revisions:boolean` | 只更改持久化的修订追踪设置 |

`document_mode` 决定后续 AI 编辑按修订或普通编辑执行。省略 `show_revisions` 时，`revising` 默认展示修订，`editing/reading` 默认隐藏；显式传入可覆盖展示值。展示开关只控制正文修订标记和右侧卡片，不处理待审修订，也不改变 `track_revisions`。回执始终包含生效的 `show_revisions`，`changed` 计入展示变化。

模式和追踪控制不要求先查询修订，也不传 `expected_state_fingerprint`。同轮已取得的 `document_mode`、`show_revisions` 和 `track_revisions` 直接复用；仅在回执明确改变状态、更新返回 revision 冲突或状态未知时重新读取。当前仅因工作模式为 reading 时，可切回 editing/revising；宿主只读或文档保护仍会拒绝。`document_mode=revising` 时，所有内容修改必须以修订形式记录，禁止普通编辑直接落盘。后续决议使用当前修订列表和指纹。回执用 `changed` 判断是否修改，决议的处理 ID 位于 `reviewed_revision_ids`；`updated_blocks_count=0` 不表示未处理修订。

待审修订 ID 来自 `revisions` 查询。取回 DOCX 编辑前，有当前的 `document_mode` 就复用，未知时才查询。`revising` 模式下，所有修改都按修订写入。文本变化用 `w:ins` 或 `w:del`，作者身份按 [DOCX 修订说明](../../workflows/canvas-doc-ooxml.md#新增批注与修订) 写入。无法合法表达为修订时停止。

## 查询修订结果

读取待审状态或修订前后内容时，可用 `revisions` scope；写入回执的 `revision_changes.created_revision_ids` 和 `updated_revision_ids` 可用作过滤条件。
