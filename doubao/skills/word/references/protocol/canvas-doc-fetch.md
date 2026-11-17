# 用 +local-fetch 读取 Canvas

`--doc` 使用客户端给出的 Canvas `token`。用 `--scope` 选读取范围，用 `--detail` 选返回的详细程度。

## 命令示例

```bash
# 只读全文浏览或总结
lark-cli docs +local-fetch --doc "<token>" \
  --scope full --detail simple

# 读取整篇正文和样式
lark-cli docs +local-fetch --doc "<token>" \
  --scope full --detail full

# 用标题定位章节
lark-cli docs +local-fetch --doc "<token>" \
  --scope outline --detail with-ids

lark-cli docs +local-fetch --doc "<token>" \
  --scope section --start-block-id "<heading_block_id>" \
  --detail full

# 读取指定区间和样式
lark-cli docs +local-fetch --doc "<token>" \
  --scope range --start-block-id "<start_block_id>" \
  --end-block-id "<end_block_id>" --detail full

# 页面布局、分节、页眉页脚与页面关系
lark-cli docs +local-fetch --doc "<token>" \
  --scope layout --detail full

# 指定页范围
lark-cli docs +local-fetch --doc "<token>" \
  --scope page --detail full \
  --start-page-index 1 --end-page-index 2

# 导出当前 Word 的 PDF
lark-cli docs +local-fetch --doc "<token>" \
  --scope pdf --start-page-index 1 --end-page-index 3 \
  --quality high --output-file-name "preview.pdf" --timeout-ms 15000

# 读取正文并附带样式引用上下文
lark-cli docs +local-fetch --doc "<token>" \
  --scope full --detail full --export-style-context refs

# 读取批注、域、修订、水印或表格几何
lark-cli docs +local-fetch --doc "<token>" --scope comments
lark-cli docs +local-fetch --doc "<token>" --scope fields
lark-cli docs +local-fetch --doc "<token>" --scope revisions
lark-cli docs +local-fetch --doc "<token>" --scope watermarks
lark-cli docs +local-fetch --doc "<token>" --scope table_geometry --block-id "<table_id>"
```

## 参数

| 参数 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `--doc` | 是 | — | Canvas 上下文提供的 `<token>`；拒绝 URL 和文件路径 |
| `--detail` | 否 | `simple` | `simple`、`with-ids`、`full` |
| `--scope` | 否 | `full` | 见下方 scope 表 |
| `--start-block-id` | 视 scope | — | `section` 的正文顶层锚点，或 `range` 起点 |
| `--end-block-id` | 视 scope | — | 仅用于 `range`；`-1` 表示直到文末 |
| `--max-depth` | 否 | `-1` | 用于 `outline`、`section`、`range`；限制标题层级，`-1` 表示不限 |
| `--revision-id` | 否 | — | 可填 `-1` 或非负安全整数。读取返回当前文档版本，不能用它打开旧版本或指定待审修订 |
| `--start-page-index` | `page` 必填 | — | 用于 `page` 或 `pdf`；正整数页码，第 1 页是文档首页；PDF 指定页范围时也必须提供 start，不能只传 end |
| `--end-page-index` | 否 | 与起始页相同 | 用于 `page` 或 `pdf`；正整数页码，且不小于起始页；PDF 起止页均省略时导出全文 |
| `--data-id` | `chart_data` 必填 | — | 普通 Fetch 返回的图表 `data-id`；不得自行构造 |
| `--quality` | 否 | `standard` | 仅用于 `pdf`；`standard` 或 `high` |
| `--output-file-name` | 否 | 宿主生成 | 仅用于 `pdf`；只传文件名，不传路径 |
| `--timeout-ms` | 否 | CLI 默认值 | 仅用于 `pdf`；正整数毫秒 |
| `--export-style-context` | 否 | 关闭 | 仅 `full/outline/section/range/page` 可使用 `refs` 返回样式引用上下文；须配合 `with-ids` 或 `full` |
| 结构化查询参数 | 视 scope | — | 按命中专项使用目标 ID、operation、分页和过滤参数；字段语义按目标查询 `comment`、`field_update`、`revisions`、`table_geometry` 或 `object` |
| 样式查询参数 | 视 scope | — | 完整用法按目标查询 `style_catalog`、`style_usage` 或 `block_styles` |

## 选择 detail

| 意图 | detail | 请求映射 |
|---|---|---|
| 浏览、总结 | `simple` | 不请求 block ID 和样式 |
| 定位章节或 block | `with-ids` | 请求 block ID，不请求样式 |
| 保真编辑、分页或布局分析 | `full` | 请求 block ID 和样式 |

`--detail full` 请求样式和 block ID，`--scope full` 请求整篇正文。两者独立；`--scope page --detail full` 用于读取指定页的完整块。

`layout` 是例外：始终导出布局和样式属性，`detail` 只影响 ID；`with-ids` 与 `full` 都包含可写 ID 和完整布局样式。

结构化 scope 不使用 detail，CLI 会忽略它，建议省略。

正文的 `simple` 和 `with-ids` 会省略样式；为 `block_replace` 取底稿时用 `full`。

- **定位阶段**：仅需定位时可用 `--detail with-ids` 获取真实 `id`；已知要编辑的范围直接用 `full`，不要自行编造 ID。
- **写前阶段**：替换使用目标的最新完整 XML；新增需要沿用格式时读取相邻同类元素。正文使用 `--detail full`，layout 的 `with-ids` 也满足此条件。同轮已有完整且未过期的响应可直接复用。

## 选择 scope

| scope | 使用场景 | 约束 |
|---|---|---|
| `full` | 确实需要整篇正文 | 不传 block、页码或深度参数；内容量大时可能超时；引用可达的普通 Note 会在正文 roots 后以 `<notes>` detached collection 返回 |
| `outline` | 结构未知 | 可用 `--max-depth` 控制标题层级 |
| `section` | 已知正文顶层 block ID（标题或单块） | 必传 `--start-block-id`；不传 `--end-block-id` |
| `range` | 已知连续区间 | start/end 均可省略；可传 `--max-depth` |
| `layout` | 页面尺寸、方向、页边距、分节、页眉页脚 | detail 可选；需要可写 ID 时使用 `with-ids` 或 `full` |
| `page` | 指定页范围 | 必传 `--start-page-index`；end 可省略并默认等于 start，detail 可选 |
| `search` | 在正文底层文本记录中查找 UTF-16 范围；可能包含当前界面隐藏的修订内容 | 必传 `--keyword`。`--limit` 默认 20、最多 100 条，`--context-chars` 最多 100 个字符 |
| `comments` | 读取批注树、锚点和并发指纹 | 可按 target ID 过滤并分页；创建或修改前先读本 scope |
| `fields` | 读取域 ID、缓存值和可更新状态 | 可按 field ID、type、可更新性过滤并分页 |
| `revisions` | 读取待审修订、模式/追踪/展示状态与 `state_fingerprint` | 可按最多 1000 个唯一修订 ID 过滤；分页默认 100、上限 500；查询 `revisions` |
| `watermarks` | 读取文字或图片水印、页眉范围和状态指纹 | 不接受业务参数；写入前回填 `state_fingerprint` |
| `table_geometry` | 读取表格各处显示位置、几何和写入所需的指纹 | 必传表格 ID。页眉页脚里的表格要选实际显示位置 |
| `object_context` | 读取移动、缩放、旋转、换锚点、复制或调整层叠所需的位置和指纹 | 传操作名和对象 ID，写入用所选对象的 `update_context_base` |
| `chart_data` | 已知图表 `data-id`，读取完整数据与版本 | 必传 `--data-id`；不传 block、页码或深度参数；detail 不参与，建议省略 |
| `pdf` | 导出当前 Canvas 的 PDF | 可传页范围、质量、文件名和超时；detail 不参与，建议省略 |
| `style_catalog` | 读取样式 ID、关系和定义 | 结果在 `data.command_result`；可按 type/ID 过滤和分页 |
| `style_usage` | 查询指定样式的使用点 | 必传真实 style ID，可包含 `based_on` 后代 |
| `block_styles` | 读取块或指定字符范围的样式绑定、直接格式和最终生效的属性及来源 | 必传真实 block ID；仅 `subtree` 可分页；self 可成对查询 start/end 的非空 UTF-16 半开范围，范围 CLI 参数名以当前帮助为准 |

### 搜索与待审修订

- 知道文字但不知道块 ID 时，可以用 `search --keyword`。

  每条结果有 `block_id`、UTF-16 `range`、`matched_text`、可选 `context` 和 `read_only`。

  用上下文区分候选，需要完整块 XML 时按 ID 读取目标范围。标为 `read_only=true` 的范围不能直接写入。
- 搜索没有分页游标。`truncated=true` 时，只能用当前结果找候选。需要全部命中时，缩小关键词或分段读取，避免按截断的结果计数或替换。
- 有待审修订时，搜索和普通正文读取都可能包含待删除和待插入的文字。

  一次搜索命中可能跨过相邻的待删除文字和待插入文字，需要区分修订前后时，用 `--scope revisions` 读取对应修订。

  无法确定命中属于哪一侧时，不能据此回答当前正文内容或修改该处。
- 需要查询本次新增或更新的修订时，可用回执中的 `revision_changes.created_revision_ids` 和 `updated_revision_ids` 作为过滤条件，见 `revisions`。

### 页面、脚注与布局

- `page` 返回与所选页相交的完整块，首尾块可能跨页。相邻页出现同一块 ID 时，它们共享该块；精确到块内的分页位置见页面 PDF。
- `full`、`section`、`range` 和 `page` 返回各自范围内 `<note-ref>` 引用到的普通脚注和尾注。`<notes>` 在正文块之后，按首次引用的顺序排列。

  `full` 不含 `<layout>` 或 `<layout-break/>`。要看分节、纸张或页眉页脚，用 `--scope layout`。

### 正文锚点与标题层级

- **`section` 和 `range` 的请求锚点必须是正文顶层块。** 传单元格 ID、列表项 ID、TextBox/Note/Header/Footer 内 block ID 或分节符 ID 都不会自动上溯；分离 story 的 block 只有在 Fetch 结果已包含其 owner graph 时才可定位，不能拿正文 scope 猜父级。
- **`section` 的锚点不必是标题。** 锚点是标题时读到下一个同级或更高级标题之前；锚点是普通段落、表格或图片时只返回该块本身，可以用它精确读单个块，不必先跑一次 `outline`。
- **`--max-depth` 限制标题层级，不是树深度。** `outline` 只筛选标题；`section/range` 还筛选标题所属正文。例如 `3` 会排除 h4 及更深标题和其下正文；任何标题之前的内容不受影响。

### 样式与专用读取

- **样式 identity 不写进 DocxXML。**

  普通正文需要后续样式查询或 dry-run 时，使用 `--export-style-context refs` 并选择可导出 block ID 的 detail；三个样式 scope 使用 XML envelope，结果位于结构化 `command_result`。完整路由和参数按目标查询 `style_catalog`、`style_usage` 或 `block_styles`。
- 修改字符样式需要同一字符范围的指纹。用 `block_styles` 查询所需的 `expected_text_range_fingerprint`，清除绑定时还需要 `fallback_effective_fingerprint`。参数和返回值见 `block_styles`。
- 批注、域、修订、表格几何、浮动对象和水印各有专用读取范围。写入需要的 ID 或指纹从对应读取结果中取，参数见下表。

### 读取编辑所需的锚点和参数

命令要块 ID、对象 ID 或文档版本时，从对应的读取结果取。用来划定读取范围的锚点与要修改的对象 ID 可能不同。

内容控件式目录的 `target_id` 和 `parent_id` 在 `data.command_result.table_of_contents`。正文 XML 或指定页没返回目录条目时，这个字段仍可能给出目录 ID。

| 更新目标 | 使用 `--detail full` 的读取方式 |
|---|---|
| 正文顶层段落、标题、表格、standalone 图片或图表 | `range` 的 start/end 均传该顶层块 ID；非标题块也可用 `section` |
| 单元格、列表项、inline 图片、Field、题注、Drawing 等正文子节点 | `range` 的 start/end 均传所属正文顶层块 ID，再从返回 XML 提取目标；不要把子节点 ID 当作 range 锚点 |
| Note 正文或 TextBox 内 block | 读取包含对应 `<note-ref>/<notes>` 或 `<drawing>/<textbox>` owner graph 的最小正文范围，从 detached/嵌套 story 提取目标；不要把内部 block ID 当成正文 range/section 锚点 |
| `<layout>`、`<layout-break>` 及其页眉页脚 | `layout`，从返回 XML 提取所属布局和 story；页眉页脚 story 内 block 可通过其真实 block ID 精确更新，但不能把 header/footer ID 当 block ID |
| 图表数据 | `--scope chart_data --data-id <data_id>`；结果不包含 DocxXML content，不替代图表占位所在正文范围的读取 |
| 批注、Field、修订、水印 | 使用对应结构化 scope；从 `command_result` 保存 identity、fingerprint 和状态，普通更新 revision 仍取文档字段 |
| 表格几何、浮动对象 | 使用 `table_geometry` / `object_context`；从候选中选择 exact occurrence，并复用 `update_context_base` |

从返回 XML 提取目标时，使用 XML 解析按 `id` 属性定位，不用依赖属性顺序或固定标签形状的正则；本地提取失败先检查解析方法，不据此认定 Fetch 失败或目标不存在。

所属顶层块尚未确定时，先按上述 scope 规则读取并确认包含关系，不要猜测父 ID。后续操作使用当前 ID。

## 返回值

```json
{
  "ok": true,
  "data": {
    "document": {
      "document_id": "doccn_xxx",
      "content": "<p id=\"blk_xxx\">...</p><h1 id=\"blk_heading\">...</h1>"
    }
  }
}
```

### 版本与指纹

除 `chart_data` 外，成功 Fetch 的 `data.document.revision_id` 可供后续普通更新使用；修订接受/拒绝另用 `state_fingerprint`。

`chart_data` 不返回文档 revision，图表数据替换使用 `data_version`；其他更新仍需对应正文、布局或样式证据。

### 自动目录身份

当 detail 为 `with-ids` 或 `full`，且本次范围内存在可由目录领域命令更新的 content-control 自动目录时，`data.command_result.table_of_contents` 只返回 `[{"target_id":"...","parent_id":"..."}]` 领域身份，不在 `data.document.content` 返回目录的具体 XML；field-only 目录从同次主 DocxXML 的 PAGEREF `<field id>` 寻址。

字段缺席表示本次可见范围内未发现兼容 content-control 目标，不得从可见目录文字猜 ID。

### 内容所在字段

普通正文和布局 scope 的 `data.document.content` 是 XML；`search/comments/fields/revisions/watermarks/table_geometry/object_context/chart_data/pdf/style_catalog/style_usage/block_styles` 的结构化结果位于 `data.command_result`。

### XML 返回结构

`full` 的 `content` 是无统一根标签的正文 XML 片段，引用可达的普通 Note 可在正文 roots 后追加一个 `<notes>` detached collection；其他 XML scope 返回 `<fragment>`，`outline` 还包含 `<outline>`。

Update 不接受 `<fragment>`、`<outline>`；`<notes>` 可随正文片段写入，规则见 Field/Note 专项。

`layout` 返回 `<fragment mode="layout">`，其中 `<layout>` 表示第一节，后续 `<layout-break>` 依次表示正文中的后续节；返回顺序就是正文节顺序。没有 `<layouts>` 包裹层。

`page` 结果只覆盖与选定页范围相交的块，可能包含这些块在其他页上的内容，不能当作逐页可见内容或完整文档。

### 结构化 scope

结构化 scope 不返回可写 DocxXML content，但仍使用 `format=xml` envelope；每个 `command_result.read_mode` 必须等于请求 scope。

图表契约查询 `chart_data`；样式契约按目标查询 `style_catalog`、`style_usage` 或 `block_styles`；其他领域契约查询 `comment`、`field_update`、`revisions`、`table_geometry`、`object` 或 `watermark`。

### PDF 导出结果

`pdf` 的 `data.command_result` 返回文件路径和导出元信息，不返回 Blob/base64。

常用字段包括 `file_path`、`relative_path`、`file_name`、`mime_type`、`size`、`document_page_count`、`exported_page_count`、`page_indexes`、`quality`；以当前 CLI 实际输出为准。

`page_indexes` 是实际导出的 0 基页索引；请求页码仍是 1 基闭区间。路径只用于本次任务。

### 读取失败

用 CLI 本身的退出码和完整 JSON 判断结果。

- 退出码为 0 且 `ok=true` 时，从 `data.document.content` 或 `data.command_result` 取内容。
- 普通读取把结果写到 stdout，`--output-file-name` 只用于 PDF。
- 失败详情可能在 stderr，尤其是 stdout 为空时。

空输出、超时或文档还在加载都不能说明页码越界。下一步见[Canvas 遇到问题怎么办](../workflows/canvas-doc-recovery.md)。

### `<fragment>` 的元数据属性

除 `full`、文档/领域结构化 scope 和协议元数据 scope 外的 XML scope 都在 `document.content` 返回 `<fragment>`，它带一组描述**本次请求**的属性：

| 属性 | 含义 |
|---|---|
| `mode` | 本次使用的 scope，如 `section`、`range`、`layout`、`page` |
| `requested-start` / `requested-end` | 请求时传入的起止 block ID |
| `requested-start-page-index` / `requested-end-page-index` | 请求时传入的起止页码 |

这些属性回显请求范围，实际返回内容可能不全。`--max-depth` 也可能过滤深层标题和内容。

编辑底稿缺少目标或要保留的子对象时，用能返回完整结构的范围和详细程度补读。提交时省略这些读取元数据。
