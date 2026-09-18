# docs +local-update：公共更新契约

先按下方导航完整读取公共契约，再读取本次命令及所涉对象的规则，不连带加载其他命令示例。

所有更新先按 [`canvas-doc-fetch.md` 的读取导航](canvas-doc-fetch.md#按需读取)读取公共契约和本次所需章节；正常执行与回读遵循 [`canvas-doc-editing.md`](../workflows/canvas-doc-editing.md)，失败恢复由 [`canvas-doc-recovery.md`](../workflows/canvas-doc-recovery.md) 产出标准结果，分支切换只由 [`canvas-doc.md`](../workflows/canvas-doc.md#路由总表唯一判定入口) 决定。

## 按需读取

**公共必读**：[前置条件](#前置条件)、[内容格式与输入](#内容格式与输入)、[参数](#参数)（含 revision 规则）、[通用指令速查](#通用指令速查)、[返回值与验证](#返回值与验证)的正文、[安全与能力边界](#安全与能力边界)。出现 warning / `partial_success` 时，继续操作前完整读取 [warnings 的格式](#warnings-的格式)并按恢复流程核验。

**命令按需**：`str_replace` 读取其[完整小节](#str_replace唯一文本替换)；block 与表格操作加读[寻址表](#可寻址标签与可用命令)和 [ID 生命周期](#block-id-生命周期)，通用 block 操作再读[指令示例](#通用指令示例)中对应命令的完整小节。`append` 同时读取 `block_insert_after` 小节中的新增格式规则。领域命令直接进入下表专项，不读取无关 block 示例。

每节读至下一同级或更高级标题；“正文”读至首个子标题，子节按导航补齐。同轮已完整读取且仍可见的内容直接复用；搜索片段、截断内容或示例不能代替完整规则。

| 本次操作 | 加读 |
|---|---|
| `str_replace` 纯文本替换 | 不要求 XML 规范 |
| block 删除 | 本页[可寻址标签与可用命令](#可寻址标签与可用命令)；含书签的 carrier 还须读取 [`canvas-doc-text.md`](../xml/canvas-doc-text.md#书签) 的只读边界 |
| XML 内容写入 | [`canvas-doc-xml.md`](../xml/canvas-doc-xml.md) + 其中命中的能力文件 |
| 表格命令或单元格替换 | [`canvas-doc-update-table.md`](canvas-doc-update-table.md) |
| 仅设置已有段落/标题的段前分页 | XML 公共规则 + [`canvas-doc-text.md` 的段落规则](../xml/canvas-doc-text.md#按需读取)；所涉内嵌结构按并集补读 |
| 独立分页符、块内分页、分节和页面布局更新 | [`canvas-doc-update-layout.md`](canvas-doc-update-layout.md) |
| Field、独立题注、脚注或尾注 | [`canvas-doc-field-note.md`](../xml/canvas-doc-field-note.md) |
| Drawing、Shape、TextBox 或文字效果 | [`canvas-doc-drawing.md`](../xml/canvas-doc-drawing.md) |
| 插入或替换图片资源 | [`canvas-doc-media-insert.md`](canvas-doc-media-insert.md) |
| 只改图片属性/浮动布局 | [`canvas-doc-media-insert.md`](canvas-doc-media-insert.md#4-更新现有图片属性) + [`canvas-doc-media.md`](../xml/canvas-doc-media.md)；保留原 `src`，无需上传 |
| 图表读取、新建、数据替换、尺寸或删除 | [`canvas-doc-chart.md`](canvas-doc-chart.md)；纯数据更新不写 XML |
| 样式目录、usage、block effective 样式或样式修改 | [`canvas-doc-style.md`](canvas-doc-style.md) |
| 水印或自动目录 | [`canvas-doc-update-domain.md`](canvas-doc-update-domain.md)；它们是领域命令，不写 XML |

命中文件明确提供按需读取导航时，完整读取其公共与命中章节；其他文件仍完整读取。不沿索引展开全部能力；组合 XML 或必须保真的内嵌结构取对应能力的并集。禁止用在线文档 reference 补充本地 Word 语法。

## 前置条件

执行任何写操作前：

1. 确认已完整读取本次路由要求的公共契约、命令章节及对象规则；没有按需读取导航的文件须完整读取。
2. 遵循已安装 `lark-shared` Skill 的权限、JSON 信封、文件输入和高风险确认规则。
3. 确认 `--doc` 使用 Canvas 上下文提供的 `<token>`，不是普通 `.docx` 文件路径或根据 token 外形猜出的资源类型；图片上传也复用该 token 作为 `--parent-node`，具体门禁见媒体插入专项。
4. 按 [`写前门禁`](../workflows/canvas-doc-editing.md#第-1-步--理解任务并读取定位) 区分既有 block、新增、纯文本及领域命令。正文编辑用 `full`，包括确认 `str_replace` 匹配区间的共同格式；layout 的 `with-ids` 也包含完整样式。既有 ID 必须来自最新响应且在 owner/story 内唯一；新增对象不要求预存 ID，领域身份按专项。替换时保留全部非目标内容和属性，同轮完整且未过期的响应可复用。
5. block 操作核对下方寻址表的 command/content 形状。`block_replace` 必须持有该类型完整可写快照，包含必需属性、block-specific defaults、非目标子节点和适用 owner/reference graph。仅有摘要、裁剪结果、`BLOCK_REF_INCOMPLETE`、`BLOCK_ID_FABRICATED` 或缺少 defaults 时先用正确 scope/detail 补齐，不试写；领域命令不套用本条根标签条件。
6. 根据本次操作确认目标 block ID、表格 A1 坐标或页面范围仍然有效，且插入锚点仍位于预期容器、具有预期相邻关系；任何会改变结构、坐标或分页关系的前序写操作，以及协同变化、revision 冲突、目标移动/删除之后，都要重新 fetch 并重做第 4–6 项检查。读取警告按 [CLI 编辑流程的读取警告处理](../workflows/canvas-doc-editing.md#第-1-步--理解任务并读取定位)分类，不因警告本身原样重读。
7. 确认当前 `docs +local-update --help` 明确暴露目标 command 及参数；未暴露时不要改用在线 `docs +update`、改写 argv、跳过校验或直调私有 API。
8. 对覆盖整块、删除、大范围表格变更、分页或布局修改，确认目标范围已由用户指令或已有确认明确授权；只有范围仍有实质歧义时才询问。当前构建支持 `--dry-run` 时优先预览请求。

## 内容格式与输入

`str_replace` 的 `--pattern` 和 `--content` 仅支持纯文本，不能创建、修改或删除公式；其中形似 `<equation>` 的标签会作为普通文字写入。block 写入与插入行列的 `--content` 固定使用 XML，并按 XML 公共规则及能力规范生成；不要传内容格式参数，也不要切换为其他格式。`block_delete` 和不插入内容的表格指令不接受 `--content`。

256 KiB 上限同时作用在**整个请求**和单个字段上，两者口径不同：整包按 JSON 转义后的 UTF-8 字节计，单个字段按原始值计。XML 里的每个 `"` 转义后都会变成 `\"`，属性密集的内容转义后接近翻倍，所以整包能装的 XML 实际远少于 256 KiB。大段内容应拆成多次小范围更新。`--chart-option` 中的 `data` 另有 192 KiB 上限，见图表专项文件。

`--content` 支持直接字符串、`@relative-file` 或 `-` 从 stdin 读取。`@` 后只接受当前工作目录内的相对路径，不接受绝对路径或 `../`；不要假定上一条 shell 的 `cd` 会延续。文件内容较长时，Mac/Linux 优先使用 stdin 重定向，避免 XML 引号和工作目录解析问题：

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace --block-id "<最新目标 ID>" \
  --content - < "/absolute/path/to/content.xml"
```

重定向路径由 shell 打开，`--content` 实际接收的是 `-`。使用 `@content.xml` 时，须在同一条调用中先进入文件所在目录。同一次调用只有一个参数可以从 stdin 读取；Windows 写法见 [`windows-compat.md`](../workflows/windows-compat.md)。

## 参数

| 参数 | 必填 | 适用指令 | 说明 |
|---|---|---|---|
| `--doc` | 是 | 全部 | Canvas 上下文提供的 `<token>`；不接受普通 `.docx` 路径 |
| `--command` | 是 | 全部 | 指令名，见下方速查表及专项文档 |
| `--revision-id` | 视指令 | 图表数据指令禁止；其余见下表 | 顶层 CLI flag；选择读取 checkpoint，不能写进业务 option JSON |
| `--content` | 视指令 | 文本/块写入、插入行列 | 新内容；`str_replace` 传空字符串表示删除匹配文本；表格插入行列可省略 |
| `--pattern` | 视指令 | `str_replace` | 要匹配的旧文本 |
| `--block-id` | 视指令 | block 与表格指令 | 目标 block ID；表格指令必须传表格 block ID |
| `--table-option` | 视指令 | 7 个 `table_*` 指令 | 单层 JSON object；支持内联、`@relative-file` 或 stdin，不要双重 JSON 编码 |
| `--chart-option` | 视指令 | 2 个 `chart_data_*` 指令 | 单层 JSON object；支持内联、`@relative-file` 或 stdin |
| `--watermark-option` | 视指令 | `watermark_update` | 单层 JSON object；完整字段见水印与目录专项文件 |
| `--table-of-contents-option` | 视指令 | `table_of_contents_update` | 单层 JSON object；`config`、`source` 可包含嵌套业务字段 |
| `--style-option` | 视指令 | `style_*` | 单层 JSON object；JSON 中只放业务字段 |

### revision 规则

| 指令 | 顶层 `--revision-id` |
|---|---|
| `style_update`、`style_apply`、`watermark_update`、`table_of_contents_update` | 必填，接受 `-1` 或非负安全整数；优先使用同一轮 Fetch 返回的具体 revision |
| `chart_data_create`、`chart_data_replace` | 禁止传入；replace 使用 `expected_data_version` |
| 其余文本、block、表格指令 | 可选；省略或 `-1` 使用最新读取 checkpoint，没有 checkpoint 时才基于当前状态；显式非负值选择对应基线 |

安全整数上限为 `9007199254740991`。`-1` 选择最新读取 checkpoint，无 checkpoint 时基于当前状态；专项命令接受 `-1` 不代表可省略该 flag，也不能省略 fingerprints、dry-run 或 plan token 等专项约束。为了明确绑定写前基线，优先传入本轮 Fetch 的具体 revision。revision 是冲突检测的读取基线，不是保证任意旧 ID 仍可写的整篇版本锁；过期基线或冲突应重新 Fetch。

`+local-update` 不接受在线文档专属参数。不要改用 `docs +update` 补齐本地协议，也不要手工构造下游请求字段。

`document_id`、`format`、`command_params`、`reference_map` 等宿主内部字段不是模型可直接传入的 CLI 参数；`revision_id` 也不得写进 option JSON。样式、水印与自动目录命令要求使用当前 `--help` 暴露的顶层 `--revision-id`。模型只根据当前 `--help` 组装命令行；帮助中没有的 flag、command 或 option 不得从后端协议字段推导。

## 通用指令速查

| 指令 | 说明 | 必需参数 |
|---|---|---|
| `str_replace` | 查找唯一文本并进行纯文本替换；`--content ''` 可删除匹配文本 | `--pattern` `--content` |
| `block_delete` | 删除指定 block | `--block-id` |
| `block_insert_after` | 在指定 block 后插入一个或多个 XML block | `--block-id` `--content` |
| `block_replace` | 用 XML 整体替换目标 block | `--block-id` `--content` |
| `append` | 在文档末尾追加 XML 内容 | `--content` |

另有 7 个表格指令、2 个图表数据指令、2 个样式指令，以及水印和自动目录领域指令，按需读取专项文件。样式 `style_update/style_apply` 必须先 dry-run 再携带 plan token 提交；提交成功以 `applied=true,new_revision_id` 为准，保存由宿主正常保存链路处理。

**指令选择速查**：同一文本块（段落、标题或列表项）内的一处唯一纯文本修改，新文字只需继承共同格式时用 `str_replace`。需要分别保留各 span 格式、合并同块多处修改，或调整格式/结构时，用最新完整 XML 执行一次 `block_replace`。完整 XML 无法表达必须保留的结构时，不得为减少调用而整块重写。

## 可寻址标签与可用命令

带 `id` 不等于支持全部命令。下表的 ID 来自最新 Fetch；获取方式见 [`canvas-doc-fetch.md`](canvas-doc-fetch.md#选择-detail)，XML 节点身份与合法结构见 [`canvas-doc-xml.md`](../xml/canvas-doc-xml.md#节点身份与结构约束)。

| 标签 | `block_replace` | `block_delete` | `block_insert_after` |
|---|---|---|---|
| `<p>`、`<h1>`～`<h9>`、`<li>`、`<img>`、`<chart>`、`<drawing>`、`<table>` | 支持 | 支持 | 支持 |
| `<td>` / `<th>` | 支持 | 不支持 | 不支持 |
| TextBox、Note、Header/Footer story 内已由 Fetch 返回且专项允许编辑的 block | 支持 | 支持 | 支持 |
| `<layout-break/>` | 支持 | 支持 | 支持 |
| `<layout>` | 支持 | 不支持 | 不支持 |

- 单元格是表格结构的一部分，只能整格替换内容；增删单元格用 [`table_*`](canvas-doc-update-table.md) 命令。
- `<layout>` 是文档级单例，只能用作 `block_replace` 目标；删除它或在它之后插入内容都没有语义。
- `<tr>` 和 `<col>` 没有独立 Record，不可直接操作。
- `<bookmark-start>` / `<bookmark-end>`、`<tabs>` / `<tab>` 是宿主段落的一部分，不是独立 command target。删除含书签的 carrier 前，必须核对 [`canvas-doc-text.md`](../xml/canvas-doc-text.md#书签) 的跨 carrier 只读边界。
- `<page-break/>` 是行内对象，即使回读时带 `id` 也不能作为 `--block-id` 直接删除、替换或后插入；要改它必须替换所属的 `<p>`、标题或 `<li>`。
- `<equation>` 没有 `id` 属性且不是 block；新增、修改、删除或复制公式时，使用宿主 carrier 的 block ID 和完整 XML。
- `<field>` 和 `<note-ref/>` 是宿主文本流的一部分，不是独立 command target；修改或删除时替换完整 carrier，并按 Field/Note 专项携带所需的 detached graph。新建题注也必须一次写入完整 `<p role="caption">`，不能先建普通段落再补角色。
- `<notes>` 是 detached collection，`<note>` / `<textbox>` 是 story owner，不是 command target；只操作其内部 Fetch 返回的 block ID。跨 body、note、textbox、header-footer story 使用 ID 会失败。
- `<drawing>` 虽位于宿主文本流，但拥有专用 inline-object target：更新、删除或在其后插入 Drawing 时，`--block-id` 使用最新 Fetch 返回的 drawing ID；替换 content 必须是同 ID 的单根 `<drawing>`，后插 content 必须是省略 ID 的单根 `<drawing>`。shape/textbox ID 不能作为 Drawing 命令目标；TextBox story 内部 block 的精确更新是另一条 story target 路径。
- standalone 图片按普通 block 处理；inline 图片使用图片 record ID 作为 `block_delete`、`block_insert_after`、`block_replace` 的专用目标，插入或替换内容必须是单个 `<img>`。具体约束见 [`canvas-doc-media.md`](../xml/canvas-doc-media.md)。
- `<layout-break/>` 支持 `block_delete`、`block_insert_after` 和 `block_replace`；`block_replace` 的 content 必须是同 ID 的单根 `<layout-break>`，其 root page 直接子节点约束见 XML 规范。
- `<li>` 可作命令目标，但 content 不能是裸 `<li>`，否则整次失败（`BLOCK_INVALID_PARENT`）。替换和插入须携带列表容器；替换原项还须保留原 `id`，省略会新建。合法形状见 [`canvas-doc-text.md`](../xml/canvas-doc-text.md#列表)。
- 列表容器会定义本次写入后的完整同级集合。只写一个子节点时，原容器中未写入的同级项可能分裂成独立容器。改单项前保存完整容器**用于比较，不代表可将兄弟项 ID 放入该单项的替换载荷**；目标范围外的 ID 会被拒绝。写后按[列表重组与保留项](../workflows/canvas-doc-editing.md#列表重组与保留项)核对目标及原同级项的容器归属和编号，不能只回读目标文字。发生非目标分裂时，按工作流将恢复与目标修正合并在一次共享预算内处理，不能另开“清理后再重写”循环。

## Block ID 生命周期

**普通 block 的 `block_replace` 写回原 `id` 时保留身份；省略时可能新建 record，使原 ID 失效。** 不把此规则套到 inline 图片（原 record 原地更新）或 layout/layout-break（必须同 ID）等专项目标。 以 fetch 返回的完整 XML 为底稿改写时 `id` 天然带着。inline 图片及 layout 等特殊目标还须满足专项约束。

无论 ID 是否保留，每次写后都必须重新 fetch 最小目标范围，确认结果并取得后续操作所需的最新定位信息；写前保存未受影响的相邻或容器锚点，不能依赖旧目标 ID。表格坐标与分页关系的生命周期见对应专项文件。

## 通用指令示例

### str_replace：唯一文本替换

`str_replace` 只支持纯文本唯一匹配和替换：`pattern` 必须在搜索范围内恰好出现一次；`content` 中的标签形似文本会按字面写入，不能用于格式化或创建公式。找不到或出现多次时都会失败；可增加同一文本块内的前后文使其唯一。它不接受 `--block-id`，也不支持 `replace_all`；需要按 Block ID 精确修改、调整格式、结构或公式时用 `block_replace`。

搜索从正文顶层块沿实际引用遍历文本块，包括表格、引用到的 Note/TextBox，以及分节符引用的页眉页脚；仅挂在 root page 上且未被上述链路引用的页眉页脚不在范围内。它不按最近一次 Fetch 的选区缩小范围。编辑分离 story 时，优先用所属 story 内的 block ID 精确更新；页眉页脚仍通过 layout 读取。

匹配可跨同一文本块内的多个 span/run，不能跨文本块。新文字只继承匹配区间共有且可继承的格式，不继承批注、修订、提及、Field 或行内对象身份；非空替换存在不能共同继承的 mark 时返回 `COMPAT_STYLE_LOST`，具体判读见下方 warnings 说明。空字符串删除匹配文本，保留范围外内容，不因被删除范围的格式差异产生此告警。命中行内对象，或只覆盖 Field run 的一部分会报参数错误；编辑 Field 时使用专项 XML 流程，避免把域退化为普通文本。

```bash
# 普通文本替换
lark-cli docs +local-update --doc "<token>" \
  --command str_replace \
  --pattern '旧版本预计周五发布' \
  --content '新版本预计下周一发布'

# 删除匹配文本
lark-cli docs +local-update --doc "<token>" \
  --command str_replace \
  --pattern '废弃内容' --content ''
```

### block_delete：删除 block

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_delete \
  --block-id "<obsolete_block_id>"
```

`block_delete` 只接受单个 Block ID，不支持数组或逗号分隔的批量删除。

### block_insert_after：插入 block

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_insert_after \
  --block-id "<section_heading_block_id>" \
  --content @insert.xml
```

`insert.xml` 按用户要求生成完整 XML；需要延续现有格式时，以写前 `full` 中的同类元素为基准，移除新对象不应复用的 ID。一次可写入连续的多个 XML block。Update 回执不返回新增 record ID；所有新对象都要用写前保存的稳定锚点重新 Fetch 后取得 identity。若锚点是 inline 图片，content 必须是单个 `<img>`，结果是在同一段文本流中新增一个 inline 图片，而不是新建段落。

新增段落默认延续相邻同类元素的字体、字号、缩进和行距；用户指定新格式时按要求设置。没有同类元素时按目标样式生成，不以缺少模板为由禁止新增。

### block_replace：替换整个 block

`<p>`、标题和 `<li>` 是 `block_replace` 的原子目标，内部 `<span>` 是行内边界。选择整块替换时，在最新完整 XML 上一次形成终态，并保留原 ID、非目标 span 边界和属性。

**这是内容替换，不是只补指定格式的 patch。** 对被替换文本，字体、字号、颜色等协议拥有的行内格式由传入 XML 表达，缺席时不自动继承，且可能没有 warning；原 ID 只保留身份。段落属性中明确规定“缺席保持”的规则不能推广到行内格式。修改文字并加粗时，复制原格式节点后做局部修改，见[局部文字与格式修改](../xml/canvas-doc-text.md#局部文字与格式修改)。

**强制前置条件（缺一不可）：**
1. 已取得目标的最新完整 XML；正文用 `full`，layout 的 `with-ids` 也可用。
2. 替换 XML 保留原 `<p>` 的全部非目标属性（对齐、缩进、行距、段间距等）。
3. 每个 `<span>` 保留全部非目标属性（字体、字号、颜色等）。
4. 提交前已将候选 XML 与写前完整基线比较，差异仅限计划内的文字、格式或结构变化；不是仅检查候选 XML 自身合法。

先用 `--detail full` 取得完整目标，将未修改的字体、段落、图片或表格属性一并回放：

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace \
  --block-id "<paragraph_block_id>" \
  --content '<p id="<paragraph_block_id>" align="justify" first-line-indent="24px" line-height="1.5"><span font-family="Arial" font-size="16px">更新后的正文。</span></p>'
```

实际编辑以最新完整 XML 为底稿保留原 ID。单元格、列表项、图片和布局目标各有 content 形状约束，必须读取对应能力文件。

### append：文末追加

```bash
lark-cli docs +local-update --doc "<token>" \
  --command append \
  --content @append.xml
```

`append.xml` 按用户要求或写前 `full` 中的文末同类基准生成。`append` 只用于文末追加；需要插入到指定章节时用 `block_insert_after`。

追加内容沿用上方新增段落的格式选择规则。

**多节文档须确认落点，不能用 `append` 推断节归属。** `<layout-break>` 的页面设置属于其后新节；插在该分节符之前的内容不属于它开启的新节。用户要求追加到指定节，或文末存在分节边界时，先读取 layout 和末尾正文，优先用目标节内的真实末块执行 `block_insert_after`，再回读顺序、节归属及适用布局。一般文末追加可用 `append`，仍按实际回读验收。新增标题的已有样式要求见 text 规范。

新增标题因目标层级样式不存在而失败时，先确认请求未写入并核对目标层级。用户只要求视觉外观时，可按共享修正预算改用带显式格式的 `<p>`；要求真实标题层级、目录收录或导航语义时，不得用普通段落冒充标题，由 recovery 输出 `local_unsupported_runtime` 交回入口。

## 返回值与验证

成功返回沿用 docs JSON 信封：

```json
{
  "ok": true,
  "data": {
    "document": {
      "document_id": "doccn_xxx",
      "new_blocks": []
    },
    "result": "success",
    "updated_blocks_count": 1,
    "warnings": []
  }
}
```

| 字段 | 说明 |
|---|---|
| `ok` | CLI 调用是否成功；必须同时确认进程退出码为 0 且 `ok == true`，不要按顶层 `code == 0` 判断 |
| `document.document_id` | 被修改的本地 Word 标识 |
| `document.new_blocks` | 当前前端 Update 实现始终返回空数组，不提供新增 record ID；新增对象必须通过写前保存的稳定锚点重新 Fetch 定位 |
| `result` | 成功信封里只会是 `success` 或 `partial_success`。**有 warning 不等于 `partial_success`**：降级的只有 `ATTR_*`、`COMPAT_*` 以及 `REPAIR_NODE_DEMOTED`、`REPAIR_ATTR_IGNORED`；其余 `REPAIR_*` 给出 warning 但仍是 `success`。`success` 和空 warnings 不证明原格式保留；还须对照写前基线回读验收。调用失败是 `ok == false` 加错误码 |
| `updated_blocks_count` | 命令级状态值，不是实际受影响的 block/cell 数。普通文本、XML、表格及 `chart_data_replace` 成功时固定为 `1`；纯预创建、dry-run 或无实际 mutation 的专项命令可为 `0`。不能用它推断新增、删除或跳过了多少对象，必须回读确认 |
| `command_result` | 图表、样式、水印和目录命令的结构化结果；包含 Chart Data 版本、样式 dry-run/commit 的 `applied/new_revision_id` 及领域命令回执 |
| `warnings` | 归一化、兼容性或能力限制诊断；是否造成实际损失须结合类型和回读判断，格式见下 |

按以下顺序解析响应：

1. 保存 CLI 进程退出码和原始 stdout/stderr；退出码非 0 时不按成功信封解析。
2. 退出码为 0 时解析完整 JSON，先判断顶层 `ok`。只有 `ok == true` 才访问 `data.document`、`data.result`、`data.command_result` 或 `data.warnings`；`ok == false` 时只读取实际存在的 error/code/message。
3. 非法 JSON、缺失 `ok` 或成功响应缺少命令必需字段时，按原始失败处理；不继续索引 `data['data']`，不让后续 `KeyError`/`TypeError` 覆盖首个错误。

### warnings 的格式

每条 warning 形如 `CODE: <标签 属性>`，标签名和属性名就是本协议的标签与属性。诊断定位不到具体标签时（例如整块内容被丢弃），退化成 `CODE: 一句英文说明`：

```text
ATTR_ENUM_INVALID_DROPPED: <img border-style>
REPAIR_CHILD_WRAPPED: <td>
```

同一个 `(code, 标签, 属性)` 组合只报一次。同一个 code 超过 10 条时截断，并追加一行 `CODE: ... (N total, M more omitted)`；看到这行说明同类问题还有更多，应缩小写入范围排查。是否可修正及剩余预算仍遵循工作流。

| 前缀 | 含义与验证关注点 |
|---|---|
| `REPAIR_CHILD_WRAPPED`、`REPAIR_CHILD_UNWRAPPED`、`REPAIR_PARENT_WRAPPED`、`REPAIR_ATTR_SUPPLIED`、`REPAIR_TEXT_NORMALIZED`、`BLOCK_PARENT_REPAIRED` | 内容被自动归一：补容器、解包、补必填属性、清正文裸换行。回读确认归一结果符合预期即可，不算失败，`result` 仍是 `success` |
| `REPAIR_NODE_DEMOTED`、`REPAIR_ATTR_IGNORED` | 多余表头行降进表体、`<col>` 的 `id` 因 `span>1` 被忽略等降级，`result` 为 `partial_success`。回读确认可接受；不可接受时按工作流共享预算修正 |
| `ATTR_*`（下列例外除外）、`COMPAT_DUPLICATE_ATTR_LAST_WINS` | 属性未生效：名称、枚举、颜色 alpha、互斥属性等。目标属性没生效等于本次修改失败，核对对应能力文档后按工作流处理 |
| `ATTR_CAPABILITY_LIMITED` | 协议有但编辑器未实现，如图片 `href`、`action-type`。目标或基线保真依赖时向 recovery 输出 `local_unsupported_runtime`，再由入口决定路由；仅误加的非目标属性才在修正预算内移除，不反复换写法。图片替代文本已由 `alt-description` / `alt-title` 支持 |
| `ATTR_UNKNOWN_IGNORED` | 未知属性被忽略，或未知行内标签被剥成纯文本。区分拼写错误与能力缺口，按工作流修正或切换 |
| `COMPAT_*`（`BLOCK_DROPPED` / `REF_INCOMPLETE` / `RESOURCE_DROPPED`） | 内容、引用或资源未完整保留。保留写前基线，按工作流合并恢复非目标内容与目标修改；不要在已降级块上只修目标属性 |
| `COMPAT_STYLE_LOST` | 样式继承或协议表达存在限制，也可能是纯文本中的标签形似文本提醒；不单凭 code 判定实际样式丢失。按下文和恢复流程核验后决定是否修正 |

**`COMPAT_STYLE_LOST` 的判读边界**：文本替换路径会比较旧范围内可继承的 mark；存在不能共同继承的 mark 且替换内容非空时即可告警，并不先检查新 XML 是否已显式补齐相关格式。`str_replace` 继承共有且可继承的格式；`block_replace` 的协议行内格式仍须在新 XML 中显式携带，不能靠原 ID 或无 warning 推断继承。

该 code 也可来自读取投影或其他对象的兼容性处理。泛化英文消息不暴露具体 mark 键，不能仅凭它猜测加粗、引号、字体或作者信息是原因，也不能断言无害。告警不证明最终显示已损坏，无告警也不证明保真；必须对照写前完整基线、计划变化与写后完整回读，必要视觉检查沿用编辑流程的触发条件。

`str_replace` 的 content 里出现形似标签的 ASCII 文本（如 `<b>`、`<TODO>`）会额外产生一条 `COMPAT_STYLE_LOST`，说明它被当作字面文本写进了文档，并把 `result` 降成 `partial_success`。**这是提醒不是丢失**——`见 <Attachment1> 说明` 这类内容就是合法的纯文本，确认写进去的确实是你要的字面量即可，不要据此回滚。真要加格式请改用 `block_replace`。中文尖括号内容（如 `<附件1>`）不会触发这条。

必须逐条检查并在内部保留 warnings 和原始 `result`，包括 `partial_success`；面向用户按 workflow 说明已核验结果、实际影响或验证缺口，不直接展示原始 warning code。回读比较目标修改、非目标内容、结构、节点边界及格式，不能只凭 `ok` 或 `result` 宣称成功。回读顺序与共享修正预算遵循 [`canvas-doc-recovery.md`](../workflows/canvas-doc-recovery.md#失败处理)，分支切换交回 [`canvas-doc.md`](../workflows/canvas-doc.md#第四层cli-调用与失败判定)；表格、布局额外验收见对应专项文件。

## 安全与能力边界

- 最小更新优先：不要为改一句话覆盖整篇；完整 XML 回放及冲突处理按工作流执行。
- CLI 返回 `confirmation_required` 时按 `lark-shared` 展示 action、risk 和关键参数；用户确认后才能追加 `--yes`（仅当该命令实际支持）。
- 未知 command、非法 `--table-option` 已知字段、派发失败或客户端不可达时，不直调 `LocalDocxUpdate` 私有 API。先由 [恢复流程](../workflows/canvas-doc-recovery.md#标准化运行结果) 产出标准结果，再交回 [统一路由](../workflows/canvas-doc.md#路由总表唯一判定入口)；可编辑路径只能来自 `+ooxml-fetch`，不能使用 Canvas `path`。
- 不支持在线文档的 `overwrite`、`block_copy_insert_after`、`block_move_after`。其他能力限制统一见 [`canvas-doc-editing.md`](../workflows/canvas-doc-editing.md) 与 [`canvas-doc-xml.md` 明确不支持的标签与能力](../xml/canvas-doc-xml.md#明确不支持的标签与能力)。

===== 全文完 =====
