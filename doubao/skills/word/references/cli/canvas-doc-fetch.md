# docs +local-fetch：读取本地 Word

本命令只读取宿主已识别并派发的本地 Word。`--doc` 必须使用 Canvas 上下文提供的 `<token>`，不接受在线文档 URL 或普通文件路径。

## 按需读取

首次调用前读取公共契约：[参数](#参数)、[选择 detail](#选择-detail)、[选择 scope](#选择-scope) 的正文、[返回值](#返回值) 的正文及[失败与重试](#失败与重试)。编辑前后再读[目标读取方式](#编辑前后如何读取目标)；返回 `<fragment>` 时读其[元数据属性](#fragment-的元数据属性)；需要预览、下载或替换图片资源时读[图片资源读取](#图片资源读取)。[命令示例](#命令示例)按本次 scope 查阅。

每节读至下一同级或更高级标题；“正文”读至首个子标题，子节按导航补齐。同轮已完整读取且仍可见的内容直接复用；搜索片段、截断内容或示例不能代替完整规则。

## 命令示例

```bash
# 只读全文浏览或总结
lark-cli docs +local-fetch --doc "<token>" \
  --scope full --detail simple

# 确需整篇正文作为基线时（篇幅可控）
lark-cli docs +local-fetch --doc "<token>" \
  --scope full --detail full

# 大文档局部编辑：先定位全部标题，再读取目标章节底稿
lark-cli docs +local-fetch --doc "<token>" \
  --scope outline --detail with-ids

lark-cli docs +local-fetch --doc "<token>" \
  --scope section --start-block-id "<heading_block_id>" \
  --detail full

# 精确区间；保留编辑所需样式
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
```

## 参数

| 参数 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `--doc` | 是 | — | Canvas 上下文提供的 `<token>`；拒绝 URL 和文件路径 |
| `--detail` | 否 | `simple` | `simple`、`with-ids`、`full` |
| `--scope` | 否 | `full` | `full`、`outline`、`section`、`range`、`layout`、`page`、`chart_data`、`pdf`、`style_catalog`、`style_usage`、`block_styles` |
| `--start-block-id` | 视 scope | — | `section` 的正文顶层锚点，或 `range` 起点 |
| `--end-block-id` | 视 scope | — | 仅用于 `range`；`-1` 表示直到文末 |
| `--max-depth` | 否 | `-1` | 用于 `outline`、`section`、`range`；限制标题层级，`-1` 表示不限 |
| `--revision-id` | 否 | — | 兼容读取参数；`-1` 或非负安全整数。读取始终取得当前 checkpoint，不按传入值锁定旧版本 |
| `--start-page-index` | `page` 必填 | — | 用于 `page` 或 `pdf`；正整数页码，第 1 页是文档首页；PDF 指定页范围时也必须提供 start，不能只传 end |
| `--end-page-index` | 否 | 与起始页相同 | 用于 `page` 或 `pdf`；正整数页码，且不小于起始页；PDF 起止页均省略时导出全文 |
| `--data-id` | `chart_data` 必填 | — | 普通 Fetch 返回的图表 `data-id`；不得自行构造 |
| `--quality` | 否 | `standard` | 仅用于 `pdf`；`standard` 或 `high` |
| `--output-file-name` | 否 | 宿主生成 | 仅用于 `pdf`；只传文件名，不传路径 |
| `--timeout-ms` | 否 | CLI 默认值 | 仅用于 `pdf`；正整数毫秒 |
| `--export-style-context` | 否 | 关闭 | 仅 `full/outline/section/range/page` 可使用 `refs` 返回样式引用上下文；须配合 `with-ids` 或 `full` |
| 样式查询参数 | 视 scope | — | 仅使用当前 `--help` 明确列出的 `--style-*`、`--cursor`、`--limit` 等参数；完整用法见 [`canvas-doc-style.md`](canvas-doc-style.md) |

## 选择 detail

| 意图 | detail | 请求映射 |
|---|---|---|
| 浏览、总结 | `simple` | 不请求 block ID 和样式 |
| 定位章节或 block | `with-ids` | 请求 block ID，不请求样式 |
| 保真编辑、分页或布局分析 | `full` | 请求 block ID 和样式 |

`--detail full` 请求样式和 block ID，`--scope full` 请求整篇正文。两者独立；`--scope page --detail full` 用于读取指定页的完整块。

`layout` 是例外：始终导出布局和样式属性，`detail` 只影响 ID；`with-ids` 与 `full` 都包含可写 ID 和完整布局样式。`chart_data`、`pdf` 和三个样式 scope 不使用 detail，CLI 会忽略它，建议省略。

正文 simple/with-ids 会省略样式，不代表原文没有格式，也不能作为 `block_replace` 底稿或格式验收证据。保留 block ID 不会自动恢复省略的字体、字号等行内格式，也不保证产生 warning。正文编辑直接读取 `full`，同时取得定位和样式信息。

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
| `chart_data` | 已知图表 `data-id`，读取完整数据与版本 | 必传 `--data-id`；不传 block、页码或深度参数；detail 不参与，建议省略 |
| `pdf` | 导出宿主当前版本的 PDF | 可传页范围、质量、文件名和超时；detail 不参与，建议省略 |
| `style_catalog` | 查询样式 identity、关系、行为和定义 | 使用 XML envelope，结果在结构化 `command_result`；可按 type/ID 过滤和分页 |
| `style_usage` | 查询指定样式的使用点 | 必传真实 style ID，可包含 `based_on` 后代 |
| `block_styles` | 查询 block 绑定、直接格式、effective 属性及 provenance | 必传真实 block ID；仅 `subtree` 可分页 |

- **大文档不要强行整篇读取。** 已知文档篇幅很大时优先使用分段 scope；同一文档的 `full` 已经超时一次后，不再原样重试。要结构用 `outline`，要某章用 `section`，要连续区间用 `range`，要指定页面用 `page`。写后验证局部结果时同样不为“确认全篇没坏”而整篇回读。
> **过程反馈**：整篇读取未完成但仍可分段读取时，不报告具体失败原因；需要反馈进度时说明“文档内容较多，我正在分段读取”。不展示超时、命令名、错误码或重试信息。分段后仍有缺失时，只说明未读取的范围及其对任务的影响。
- **`page` 返回与请求页相交的完整 block，不是该页可见内容的裁剪。** 首末 block 均可能跨页，不能据其在返回中的位置认定实际页首或页尾；须读取相邻页比较边缘 block ID，重复表示跨页，块内页面边界仅能由 PDF 唯一确定。
- **XML 正文 scope 会附带所选 roots 引用可达的普通 Note。** `full`、`section`、`range`、`page` 只附带各自范围内 `<note-ref>` 可达的 `<note>`，按首次引用顺序放在正文 roots 后的 `<notes>` detached collection 中；不会带入范围外 Note。`full` 不含 `<layout>`，也会剔除 `<layout-break/>`。判断文档有几节、纸张多大、页眉写了什么，必须另外读 `--scope layout`。
- **`section` 和 `range` 的请求锚点必须是正文顶层块。** 传单元格 ID、列表项 ID、TextBox/Note/Header/Footer 内 block ID 或分节符 ID 都不会自动上溯；分离 story 的 block 只有在 Fetch 结果已包含其 owner graph 时才可定位，不能拿正文 scope 猜父级。
- **`section` 的锚点不必是标题。** 锚点是标题时读到下一个同级或更高级标题之前；锚点是普通段落、表格或图片时只返回该块本身，可以用它精确读单个块，不必先跑一次 `outline`。
- **`--max-depth` 限制标题层级，不是树深度。** `outline` 只筛选标题；`section/range` 还筛选标题所属正文。例如 `3` 会排除 h4 及更深标题和其下正文；任何标题之前的内容不受影响。
- **样式 identity 不写进 DocxXML。** 普通正文需要后续样式查询或 dry-run 时，使用 `--export-style-context refs` 并选择可导出 block ID 的 detail；三个样式 scope 使用 XML envelope，结果位于结构化 `command_result`。完整路由和参数见 [`canvas-doc-style.md`](canvas-doc-style.md)。
- **PDF 是 Fetch，不是 Update。** 它不会把 PDF 字节塞进 JSON；成功后只使用 CLI 响应给出的宿主本地路径，不自行猜路径。请求页码是 1 基闭区间。
- **底层格式统一为 XML。** 正文、Chart Data、PDF 和样式读取均使用 `format=xml` envelope；Chart Data、PDF 和三个样式 scope 的业务结果是 `data.command_result` object，不是 DocxXML string。
- **只调用 CLI，不构造内部请求。** `document_id`、`format`、`read_option`、`export_option`、`command_params` 等是宿主内部协议字段，不是模型可传给 `lark-cli` 的参数。当前 `--help` 未列出的 flag 不得猜测，也不得绕过 CLI 直调私有接口。

### 编辑前后如何读取目标

写前保存完整目标 XML，写后按同一路径回读并验证；读取范围的锚点不一定等于更新命令的目标 ID。同轮最新完整响应可以同时用于定位、规划和写前检查；写后回读覆盖下一目标且中间无写入或协同变化时，可直接作为下一步基线，不重复抓取相同范围。

content-control 自动目录的身份位于 `data.command_result.table_of_contents`（`target_id,parent_id`，仅覆盖本次范围），不以主 XML 是否含目录条目判断目录是否存在。目录页的 `page` 空片段也不能证明没有目录；已有身份后，条目与页码按 [目录验收](../xml/canvas-doc-toc.md#回读验收) 用宿主页面/PDF 补证，不反复换 scope 查找目录 XML。

| 更新目标 | 使用 `--detail full` 的读取方式 |
|---|---|
| 正文顶层段落、标题、表格、standalone 图片或图表 | `range` 的 start/end 均传该顶层块 ID；非标题块也可用 `section` |
| 单元格、列表项、inline 图片、Field、题注、Drawing 等正文子节点 | `range` 的 start/end 均传所属正文顶层块 ID，再从返回 XML 提取目标；不要把子节点 ID 当作 range 锚点 |
| Note 正文或 TextBox 内 block | 读取包含对应 `<note-ref>/<notes>` 或 `<drawing>/<textbox>` owner graph 的最小正文范围，从 detached/嵌套 story 提取目标；不要把内部 block ID 当成正文 range/section 锚点 |
| `<layout>`、`<layout-break>` 及其页眉页脚 | `layout`，从返回 XML 提取所属布局和 story；页眉页脚 story 内 block 可通过其真实 block ID 精确更新，但不能把 header/footer ID 当 block ID |
| 图表数据 | `--scope chart_data --data-id <data_id>`；结果不包含 DocxXML content，不替代图表占位所在正文范围的读取 |

所属顶层块尚未确定时，先按上述 scope 规则读取并确认包含关系，不要猜测父 ID。写后使用最新 ID；分页或布局变更还需读取受影响的 `page`。

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

- 除 `chart_data` 外，成功 Fetch 的 `data.document.revision_id` 是本次当前 checkpoint，可供后续更新使用；`chart_data` 虽建立内部读取基线，但不在响应中返回该 revision；图表数据替换使用返回的 `data_version`，其他更新仍需对应正文、布局或样式证据。
- 当 detail 为 `with-ids` 或 `full`，且本次范围内存在可由目录领域命令更新的 content-control 自动目录时，`data.command_result.table_of_contents` 只返回 `[{"target_id":"...","parent_id":"..."}]` 领域身份，不在 `data.document.content` 返回目录的具体 XML；field-only 目录从同次主 DocxXML 的 PAGEREF `<field id>` 寻址。字段缺席表示本次可见范围内未发现兼容 content-control 目标，不得从可见目录文字猜 ID。
- 普通正文和布局 scope 的 `data.document.content` 是 XML；结构化 scope 与 PDF 的结果位于 `data.command_result`。
- `full` 的 `content` 是无统一根标签的正文 XML 片段，引用可达的普通 Note 可在正文 roots 后追加一个 `<notes>` detached collection；其他 XML scope 返回 `<fragment>`，`outline` 还包含 `<outline>`。Update 不接受 `<fragment>`、`<outline>`；`<notes>` 可随正文片段写入，规则见 [Field/Note 专项](../xml/canvas-doc-field-note.md#脚注与尾注)。
- `layout` 返回 `<fragment mode="layout">`，其中 `<layout>` 表示第一节，后续 `<layout-break>` 依次表示正文中的后续节；返回顺序就是正文节顺序。没有 `<layouts>` 包裹层。
- `page` 结果只覆盖与选定页范围相交的块，可能包含这些块在其他页上的内容，不能当作逐页可见内容或完整文档。
- `chart_data` 和三个样式 scope 不返回 DocxXML content，但仍使用 `format=xml` envelope；结构化结果位于 `data.command_result`。图表契约见 [`canvas-doc-chart.md`](canvas-doc-chart.md)，样式契约见 [`canvas-doc-style.md`](canvas-doc-style.md)。
- `pdf` 的 `data.command_result` 返回文件路径和导出元信息，不返回 Blob/base64。常用字段包括 `file_path`、`relative_path`、`file_name`、`mime_type`、`size`、`document_page_count`、`exported_page_count`、`page_indexes`、`quality`；以当前 CLI 实际输出为准。`page_indexes` 是实际导出的 0 基页索引；请求页码仍是 1 基闭区间。路径只用于本次任务，须先验证存在再消费。
- 读取用于编辑时保存目标 block ID、表格坐标和页面范围；写入完成后重新读取验证。

### 失败与重试

- 先检查 CLI 进程退出码，再解析信封并确认 `ok == true`，之后才能按 scope 访问 `data.document.content` 或 `data.command_result`；失败时不读取成功字段。不要把 `... | head` 或末尾 `echo` 的退出码当作 CLI 退出码。
- 自动处理响应时使用结构化进程调用分别保留 stdout、stderr 和 returncode。完整 JSON 先落盘或完整解析，再截取需要展示的 XML；不要截断 JSON 后再解析，也不要把 JSON 信封直接当 XML。
- **失败信封走 stderr，stdout 可能为空。** 非零退出时必须保留并解析 stderr；丢弃 stderr 会把参数错误、页码越界、限流和文档未就绪都压成“无输出”。
- **不要把“无输出”当成页码越界。** 读取错误码和详情，参数错误应修正命令；只有响应明确给出总页数时才能据此判断文末，不能从 timeout、5xx 或加载态推断页数。
- `ok == false` 时读取返回的错误码与错误信息再决定下一步：文档处于加载态（错误明确指向"仍在加载 / 尚未就绪"）时按 [`canvas-doc-recovery.md`](../workflows/canvas-doc-recovery.md#失败处理) 的退避重试规则处理，其余错误按普通失败处理，不要盲目重发同一请求。
- 宿主报告文件已关闭时本命令不可用，按 [`canvas-doc.md`](../workflows/canvas-doc.md#关闭文件分支) 处理，禁止把 `<path>` 传给本命令。`open` 状态下只有恢复模块能判定全部 Canvas CLI 不可用；编辑任务停止并要求用户先保存、关闭文件，只读任务仅可读取磁盘已保存版本并披露未保存改动不可见。

### `<fragment>` 的元数据属性

除 `full`、`chart_data`、`pdf` 和三个样式 scope 外的 XML scope 都在 `document.content` 返回 `<fragment>`，它带一组描述**本次请求**的属性：

| 属性 | 含义 |
|---|---|
| `mode` | 本次使用的 scope，如 `section`、`range`、`layout`、`page` |
| `requested-start` / `requested-end` | 请求时传入的起止 block ID |
| `requested-start-page-index` / `requested-end-page-index` | 请求时传入的起止页码 |

这些属性只回显请求范围，不证明实际内容完整。须核对目标、起止边界、必要子对象和 tips；仅见请求值相等不能认定无截断。编辑时不随意限制 `--max-depth`，它会过滤深层标题所属内容。这些读取元数据不可写入 Update。

## 图片资源读取

预览或下载前，完整读取本节至「全文完」；未见该标记时，调整 offset 继续读取。本节只处理本地 Word `<img>`，不处理在线文档附件、`<source>`、画板或封面；不要传 `--type whiteboard`，也不要套用这些对象的下载规则。

### 获取图片 token

本地 Word 图片使用 `<img src="...">` 表达资源引用：

```xml
<img id="blk_image" src="file_xxx" width="800" height="600"/>
```

- `src` 是图片资源 token，不是本地路径或网络 URL。
- 先按本页读取规则获取包含目标图片的最小范围；图片定位或后续还要编辑时使用 `--detail full`。
- 替换图片前使用 `--detail full`，同时保存图片 block ID 和所有未要求修改的属性。
- token 必须来自 `<img src>`，不能用文档 ID、图片 block ID、`document_id`、`obj_token` 或本地文件路径代替。

### 预览图片

用户要求“看一下、预览、确认图片内容”时使用 `docs +media-preview`。提取 `src` 后执行：

```bash
lark-cli docs +media-preview \
  --token "file_xxx" \
  --output "./preview-image"
```

预览完成后向用户展示或说明实际输出路径。

### 下载原图

用户明确要求“下载、保存、导出原图”时使用 `docs +media-download`；只是查看内容时优先预览。下载前明确输出目录或文件名，避免覆盖已有文件。提取 `src` 后执行：

```bash
lark-cli docs +media-download \
  --token "file_xxx" \
  --output "./downloaded-image"
```

成功后返回实际保存路径。

### 输出路径与失败处理

- 两个命令的 `--output` 不带扩展名时，均会根据响应类型自动补全。
- token 为空：重新 fetch 目标图片，不能猜测 token。
- 预览返回 `HTTP 403` 或资源不可见：检查当前上下文对该素材的访问权限；不要改用文档 ID 下载。
- 下载返回 `HTTP 403`：仅需查看内容时可改用预览；明确要求下载时，报告权限错误，不得把预览结果冒充下载结果。
- 输出路径已存在：遵循当前命令的覆盖规则，不得未经用户允许覆盖已有文件。

===== 全文完 =====
