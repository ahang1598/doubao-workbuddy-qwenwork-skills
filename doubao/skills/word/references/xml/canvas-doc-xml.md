# 本地 Word XML：公共规则与语法索引

本页定义公共结构、节点身份、颜色、单位和转义规则；标签属性、取值及嵌套约束见下方索引。CLI 参数见 `references/cli/`，操作流程见 [`canvas-doc-editing.md`](../workflows/canvas-doc-editing.md)。不得用 `online-doc` XML 参考补充本地语法，也不得从只读返回结构推导写入能力。

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

生成 XML 前完整读取本页；片段涉及的语法文件若明确提供按需读取导航，完整读取其公共与命中章节，否则完整读取至「全文完」。
编辑已有 Word 时以最新完整 XML 为准，获取方式见 [`canvas-doc-fetch.md`](../cli/canvas-doc-fetch.md#选择-detail)：保留目标范围内不认识的读取属性，只修改用户要求的内容。不要因为本规范未列出某个只读属性就主动删除它。

## 语法索引

按 XML 片段中的标签和属性查阅对应文件：

| 语法类别 | 标签与属性范围 | 语法文件 |
|---|---|---|
| 段落与标题 | `<p>`、`<h1>`～`<h9>`；对齐、缩进、间距、行距和段落分页属性 | [`canvas-doc-text.md`](canvas-doc-text.md) |
| 富文本与基础行内对象 | `<span>`、粗体/斜体/下划线/删除线标签及别名、`<sup>` / `<sub>`、`<br/>`、`<symbol/>`、`<equation/>`；字体、字号、颜色、底纹、字符边框 | [`canvas-doc-text.md`](canvas-doc-text.md) |
| 域、题注、脚注与尾注 | `<field>`、`<p role="caption">`、`<note-ref/>`、`<notes>` / `<note>`、`<note-settings/>`；Field identity、只读结果、detached collection 与设置 | [`canvas-doc-field-note.md`](canvas-doc-field-note.md) |
| Drawing、Shape 与 TextBox | `<drawing>`、`<shape>`、`<textbox>`；布局、几何、填充、轮廓、WordArt 与文字效果 | [`canvas-doc-drawing.md`](canvas-doc-drawing.md) |
| 列表、制表位与书签 | `<ul>` / `<ol>` / `<li>`、`<tabs>` / `<tab/>`、`<bookmark-start/>` / `<bookmark-end/>`；`list-style-type`、`list-preset`、`marker-*`、编号层级、制表位属性与边界配对 | [`canvas-doc-text.md`](canvas-doc-text.md) |
| 表格 | `<table>`、`<colgroup>` / `<col>`、`<thead>` / `<tbody>`、`<tr>`、`<td>` / `<th>`；宽度、行高、合并、边框、底色、内边距及结构归一化 | [`canvas-doc-table.md`](canvas-doc-table.md) |
| 图片 | `<img/>`；资源引用、尺寸、裁剪、旋转、翻转、边框、浮动定位与环绕属性 | [`canvas-doc-media.md`](canvas-doc-media.md) |
| 图表 | `<chart/>` 占位；`id`、`data-id`、尺寸和空元素约束；图表类型、系列及展示属性 JSON | [`canvas-doc-chart.md`](canvas-doc-chart.md) |
| 分页、分节与页面布局 | `<page-break/>`、`<layout-break/>`、`<layout>`、`<columns>` / `<column>`、`<header>` / `<footer>`、`<page-number/>` / `<page-count/>`；行网格、分栏、纸张、方向、页边距、页眉页脚与页码域 | [`canvas-doc-layout.md`](canvas-doc-layout.md) |

**组合结构**：以上语法按嵌套关系组合，不能只看最外层标签。例如表格单元格内含富文本和图片时，需要 table、text、media 三份规范。范围仅限当前 XML 片段，包括其中必须保留的原有结构，不扩展到文档其他部分。

表格和布局规范已说明的最小 `<p>文本</p>`、`<p><page-break/></p>` 等形状无需额外读取 text；包含段落格式、富文本、列表、制表位、书签或 SYMBOL 时仍须读取 text，不得为减少读取而删掉原有格式。

**目录专项**：自动目录操作读取 [`canvas-doc-toc.md`](canvas-doc-toc.md)，统一走 CLI 领域命令，不属于上表的 XML 标签语法。`<page-number/>` / `<page-count/>` 的语法仍见 layout。

## 片段与只读容器

正文 XML 采用片段形式，无统一根标签，不支持 `<docx>` 包裹层。`<fragment>`、`<outline>` 是读取结果中描述范围的容器，不属于可写入标签。各 scope 的返回范围见 [`canvas-doc-fetch.md`](../cli/canvas-doc-fetch.md#选择-scope)。

## 节点身份与结构约束

- `<table>`、`<td>` / `<th>` 有独立 Record；`<tr>`、`<col>` 没有独立 Record。单元格仍属于表格结构。
- `<layout>` 是文档级单例；`<layout-break/>` 只能作为 root page 的直接子节点。
- `<bookmark-start>` / `<bookmark-end>`、`<tabs>` / `<tab>` 属于宿主段落；书签的配对和跨 carrier 只读边界见 [`canvas-doc-text.md`](canvas-doc-text.md#书签)。
- `<page-break/>` 是宿主 `<p>`、标题或 `<li>` 内的行内对象，即使带 `id` 也不是独立 block。
- `<equation>` 是宿主文本流中的行内特殊对象，没有 `id` 属性，也不是 block 或独立 Record；只能通过宿主 carrier 操作。
- `<field>`、`<note-ref/>` 和 `<drawing>` 是宿主文本流内对象；Field identity、note owner identity 和 drawing record identity 的命令目标规则见各自专项文件。
- `<notes>` 是 detached collection，可在 Fetch 和 Update 片段中跟在正文 roots 后；它不进入正文 roots，也不是独立命令目标。写入时按 Field/Note 专项携带匹配的引用和 owner。
- `<textbox>`、`<note>`、`<header>` / `<footer>` 的正文属于分离 story；其中 block ID 只能在所属 story 内使用。
- standalone 图片位于正文 `children` 链路中；inline 图片位于文本流中，其图片 record 与宿主段落的身份不同。
- `<li>` 必须位于列表容器中，不能作为写入片段的根节点。已有列表项的合法形状为 `<ol list-style-type="decimal"><li id="<原 li id>">新内容</li></ol>`；列表类型和 ID 沿用原结构。

节点带 `id` 不代表支持所有命令。命令支持矩阵、特殊目标的 content 形状和 ID 保留规则统一见 [`canvas-doc-update.md`](../cli/canvas-doc-update.md#可寻址标签与可用命令)。

## 必填属性

- 插入图片时必须提供 `<img src="..."/>`。
- 插入图表时必须提供 `chart_data_create` 返回的 `<chart data-id="..."/>`，以及合法的 `width` / `height`。
- 写入页面布局时必须提供 `<layout id="...">`。
- 插入分节符时必须提供 `<layout-break type="..."/>`。
- 新建独立题注必须包含且只包含一个无 `id`、无 result 的 `SEQ` Field。
- 新建 Drawing 必须提供正 `width` / `height`，并包含恰好一个 Shape；Shape 最多包含一个 TextBox。
- 其他专项必填条件（例如 SYMBOL 的 `code` / `unicode`）见对应能力文件。

## 颜色与单位

- 颜色优先沿用 fetch 返回值。统一颜色文法支持 3、6、8 位 Hex（`#` 可省略）、`rgb(...)`、`rgba(...)` 和 `auto`，例如 `#F00`、`ff0000`、`#FF0000FF`、`rgb(255,255,0)`、`rgba(255,255,0,1)`。
- 禁止写入命名色和 `light-*` 等颜色枚举，例如 `red`、`yellow`、`gray`、`light-yellow`。
- 颜色值不接受空白，通道越界不会自动截断。普通属性会被丢弃并告警；严格标签的非法颜色会让整次请求失败。
- **alpha 小于 1 不会自动降成不透明色。** `<img border-color>`、文字效果的 `text-shadow-color` / `text-glow-color` 支持真实 alpha；其余普通颜色属性会整体丢弃并返回 `ATTR_COLOR_ALPHA_DROPPED`，严格校验的属性（如 Shape 的 `fill-color` / `outline-color`、文字效果的 `text-fill-color` / `text-outline-color`）则返回 `ATTR_VALUE_INVALID`，整次失败。alpha=1 可以无损归一化为不透明颜色。
- 字号使用 `pt` 或 `px`，必须带单位；段落缩进使用 `ch`、`pt` 或 `px`；字符和表格边框宽度、表格 padding 使用 `pt`。
- 图片 `width` / `height`：裸数字按 `pt` 解释（fetch 返回的就是这一种），也接受 `512pt`、`6in` 等带单位写法；图片 `border-width` 也接受裸数值或 `pt`。
- 表格 `<col width>`：不带单位，数值按 `px` 解释，精度与值域见 [`canvas-doc-table.md`](canvas-doc-table.md#属性与结构规则)。
- 图表 `width` / `height`：只接受 `pt`，范围 `16pt..1584pt`。
- 正文侧的其余尺寸属性（段落缩进、字号、字符间距、表格 padding 与边框宽度）写裸数字只丢该属性。
- **`<layout>` / `<layout-break>` 的页面尺寸、页边距和装订线写裸数字是整次失败**（`ATTR_VALUE_INVALID`）；只接受 `pt`、`px`、`in`、`cm`、`mm`。
- 宽高、页边距、缩进等尺寸优先沿用 fetch 返回值；没有明确换算契约时，不自行在不同单位之间换算。

## 严格属性校验

`<equation>`、`<field>`、`<drawing>`、`<shape>`、`<textbox>`、`<note-ref>`、`<notes>`、`<note>`、`<note-settings>` 使用严格属性校验：未知属性、非法格式或非法枚举会返回 `ATTR_VALUE_INVALID`，整次失败，不按普通属性的 warning/drop 规则处理。其他标签也可能对特定属性强制报错，应以专项规则为准。

## XML 转义

标签本身禁止转义，只有文本内容和属性值中的特殊字符需要转义。

```xml
<!-- 错误：标签被转义 -->
&lt;p&gt;内容&lt;/p&gt;

<!-- 正确：仅转义文本中的特殊字符 -->
<p>A &amp; B 的对比：1 &lt; 2</p>
```

| 字符 | 转义 |
|---|---|
| `&` | `&amp;` |
| `<` | `&lt;` |
| `>` | `&gt;` |
| `"`（属性值内） | `&quot;` |

段内换行不走转义，用 `<br/>` 标签，见 [`canvas-doc-text.md`](canvas-doc-text.md#段内换行)。XML 源码里的裸换行和缩进是不显著空白，可以用来格式化，但英文句子中间折行会粘连文字。

## 明确不支持的标签与能力

当前本地 Word 只支持本页及能力文件列出的标签；未定义的标签均不支持，不要写入。常见的不支持标签包括：

- `<checkbox>`、`<callout>`、`<grid>`、`<figure>`；`<column>` 仅允许作为 `<columns>` 的子节点，不可用于正文分栏；
- `<whiteboard>`、`<sheet>`、`<task>`、`<chat_card>`、`<sub-page-list>`、`<html5-block>`、`<okr>`；
- `<cite>`、`<bookmark>`（在线文档标签；本地书签使用 `<bookmark-start/>` / `<bookmark-end/>`）、`<button>`、`<time>`、`<source>`、URL preview；
- `<a>`、`<wordart>`（WordArt 使用 `<shape word-art="true">`）、`<caption>`（题注使用 `<p role="caption">`）、`<title>`、`<layouts>`、`<docx>`；
- `<latex>` 或其他未定义公式节点；公式只使用 `<equation/>`。

当前不开放文档 theme 定义与 Shape theme ref 写入（文本的 `font-family-*-theme` 可引用已有主题字体，见[文本规范](canvas-doc-text.md#富文本)）、超链接创建或修改、任意原始 Field instruction、custom geometry、geometry/warp adjustment、group/canvas、VML TextPath 写入、inline/隐藏 label 题注、对象上方题注和 Caption 全局设置。各属性级只读边界见 Field/Note 与 Drawing 专项文件。

整套封面模板的创建、插入或替换未开放，不要从“能识别封面”推导为可写；已导入封面中以普通 block 返回的内容仍可按其实际类型编辑。

`<tfoot>` 和 `<layout-break type="next-column">` 在协议里已定义但尚未实现，写入返回 `BLOCK_NOT_IMPLEMENTED_TAG`；上面列出的标签是协议根本没有，块级写入返回 `BLOCK_UNSUPPORTED_TAG`。两类都不要写。

**未支持标签的失败分级取决于它出现在哪里。** 出现在块级位置（正文顶层、单元格、列表容器）返回 `BLOCK_UNSUPPORTED_TAG`，整次失败；出现在**行内位置**（`<p>`、`<h1>`～`<h9>`、`<li>` 的文本流里）不会失败，标签被剥掉、子节点当纯文本写入，只返回一条 `ATTR_UNKNOWN_IGNORED`。所以在段落里写 `<a href="...">链接</a>` 的结果是接口返回成功、链接文字进了文档、超链接没有；自闭合的未知行内标签则整个消失。必须逐条读 `warnings`，不能只看 `ok`。

艺术字、通用域等能力边界统一见 [`canvas-doc-editing.md`](../workflows/canvas-doc-editing.md) 与 [`canvas-doc.md` 的 CLI 能力门禁](../workflows/canvas-doc.md#第三层最少必要读取cli-能力与调用预算)。本规范未定义的 OOXML 节点创建不属于 XML 更新能力。

`+local-fetch` 返回但本规范不支持编辑的结构，应保持原 block 不变并向 [`canvas-doc.md` 的 CLI 能力门禁](../workflows/canvas-doc.md#第三层最少必要读取cli-能力与调用预算) 输出 `local_unsupported`；只有入口最终选择 `open_ooxml` 后才执行 OOXML 流程。可编辑的 `.docx` 路径必须由 `+ooxml-fetch` 返回（不要使用 Canvas 上下文里的 `path`），不得从“本 XML 不支持”直接推导具体实现方式。

所有 XML 写入均受 262144 UTF-8 bytes 请求上限以及 CLI 返回的对象深度、单 story block 和资源数量限制。只提交从最新完整 Fetch 基线生成的最小修改；失败时不得假定已有部分内容落盘，成功后按工作流回读，涉及兼容性验收时再验证保存重开结果。不要在日志中主动打印正文、Field result、完整 XML 或资源 payload。

===== 全文完 =====
