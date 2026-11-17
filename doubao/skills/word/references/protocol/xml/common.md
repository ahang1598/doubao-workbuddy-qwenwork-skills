---
keyword: xml:common
---

**功能**：XML 公共身份、片段与只读容器、必填属性、颜色与单位、严格校验、转义及明确不支持能力

# 本地 Word XML：公共规则与语法索引

本页定义公共结构、节点身份、颜色、单位和转义规则；标签属性、取值及嵌套约束按下方索引查询具体关键词。CLI 参数按下方索引查询具体命令关键词，操作流程由上层 workflow 负责。不得用 `online-doc` XML 参考补充本地语法，也不得从只读返回结构推导写入能力。

编辑已有 Word 时以 `+local-fetch` 获取的最新完整 XML 为准：保留目标范围内不认识的读取属性，只修改用户要求的内容。不要因为本规范未列出某个只读属性就主动删除它。

## 语法索引

按 XML 片段中的标签和属性查阅对应文件：

| 语法类别 | 标签与属性范围 | 查询关键词 |
|---|---|---|
| 段落与标题 | `<p>`、`<h1>`～`<h9>`；对齐、缩进、间距、行距和段落分页属性 | 属性查 `xml:p`；所有标题层级的通用规则查 `xml:h1` |
| 富文本与基础行内对象 | `<span>`、`<a>`、粗体/斜体/下划线/删除线标签及别名、`<sup>` / `<sub>`、`<br/>`、`<column-break/>`、`<symbol/>`、`<equation/>`；字体、字号、颜色、底纹、字符边框与普通超链接 | `xml:span` |
| 普通块级内容控件 | `<content-control>`；只更新现有控件 children | `xml:content-control` |
| 域、题注、脚注与尾注 | `<field>`、`<p role="caption">`、`<note-ref/>`、`<notes>` / `<note>`、`<note-settings/>`；Field identity、只读结果、detached collection 与设置 | `xml:field`、`xml:note` |
| Drawing、Shape 与 TextBox | `<drawing>`、`<shape>`、`<textbox>`；布局、几何、填充、轮廓、WordArt 与文字效果 | `xml:drawing` |
| 列表、制表位与书签 | `<ul>` / `<ol>` / `<li>`、`<tabs>` / `<tab/>`、`<bookmark-start/>` / `<bookmark-end/>`；`list-style-type`、`list-preset`、`marker-*`、编号层级、制表位属性与边界配对 | `xml:ol`、`xml:p` |
| 表格 | `<table>`、`<colgroup>` / `<col>`、`<thead>` / `<tbody>`、`<tr>`、`<td>` / `<th>`；宽度、行高、合并、边框、底色、内边距及结构归一化 | `xml:table` |
| 图片 | `<img/>`；资源引用、尺寸、裁剪、旋转、翻转、边框、浮动定位与环绕属性 | `xml:img` |
| 图表 | `<chart/>` 占位；`id`、`data-id`、尺寸和空元素约束；图表类型、系列及展示属性 JSON | `xml:chart` |
| 分页、分节与页面布局 | `<page-break/>`、`<layout-break/>`、`<layout>`、`<columns>` / `<column>`、`<header>` / `<footer>`、`<page-number/>` / `<page-count/>`；行网格、分栏、纸张、方向、页边距、页眉页脚与页码域 | `xml:layout-break`、`xml:layout` |

**组合结构**：以上语法按嵌套关系组合，不能只看最外层标签。例如表格单元格内含富文本和图片时，查询 `xml:table`、`xml:span`、`xml:img`。范围仅限当前 XML 片段，包括其中必须保留的原有结构，不扩展到文档其他部分。

表格和布局协议已说明的最小 `<p>文本</p>`、`<p><page-break/></p>` 等形状无需额外读取文本协议；包含段落格式、富文本、列表、制表位、书签或 SYMBOL 时，分别查询命中的 `xml:p`、`xml:span`、`xml:ol`，不得为减少读取而删掉原有格式。

**目录专项**：自动目录操作查询 `table_of_contents`，统一走 CLI 领域命令，不属于上表的 XML 标签语法。`<page-number/>` / `<page-count/>` 的语法查询 `xml:layout`。

## 片段与只读容器

正文 XML 采用片段形式，无统一根标签，不支持 `<docx>` 包裹层。`<fragment>`、`<outline>` 是读取结果中描述范围的容器，不属于可写入标签。各 scope 的返回范围遵循已读取的 [canvas-doc-fetch.md](../canvas-doc-fetch.md)。

## 块、对象和 ID

段落、表格等内容是块。行内对象所在的段落或列表项也叫所属块（carrier）。正文、页眉、页脚、脚注等各自的内容区域在协议中称为 story。

- `<table>`、`<td>` / `<th>` 有独立 Record；`<tr>`、`<col>` 没有独立 Record。单元格仍属于表格结构。
- `<layout>` 是文档级单例；`<layout-break/>` 只能作为 root page 的直接子节点。
- `<bookmark-start>` / `<bookmark-end>`、`<tabs>` / `<tab>` 属于宿主段落；书签的配对和跨 carrier 只读边界查询 `xml:p`。
- `<page-break/>` 是宿主 `<p>`、标题或 `<li>` 内的行内对象，即使带 `id` 也不是独立 block。
- `<column-break/>` 与分页符一样是宿主文本流内对象，不是独立 block；只在已有分栏布局中使用。
- `<equation>` 是宿主文本流中的行内特殊对象，没有 `id` 属性，也不是 block 或独立 Record；只能通过宿主 carrier 操作。
- `<field>`、`<note-ref/>` 和 `<drawing>` 是宿主文本流内对象；Field identity、note owner identity 和 drawing record identity 的命令目标规则见各自专项文件。
- `<notes>` 是 detached collection，可在 Fetch 和 Update 片段中跟在正文 roots 后；它不进入正文 roots，也不是独立命令目标。写入时按 Field/Note 专项携带匹配的引用和 owner。
- `<textbox>`、`<note>`、`<header>` / `<footer>` 的正文属于分离 story；其中 block ID 只能在所属 story 内使用。
- standalone 图片位于正文 `children` 链路中；inline 图片位于文本流中，其图片 record 与宿主段落的身份不同。
- `<li>` 必须位于列表容器中，不能作为写入片段的根节点。已有列表项的合法形状为 `<ol list-style-type="decimal"><li id="<原 li id>">新内容</li></ol>`；列表类型和 ID 沿用原结构。

节点带 `id` 不代表支持所有命令。命令支持矩阵、特殊目标的 content 形状和 ID 保留规则查询 `local-update`，并按操作查询 `block_replace`、`block_insert_after`、`block_delete` 或其他明确命中的命令关键词。

## 必填属性

- 插入图片时必须提供 `<img src="..."/>`。
- 插入图表时必须提供 `chart_data/action=create` 返回的 `<chart data-id="..."/>`，以及合法的 `width` / `height`。
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
- 表格 `<col width>`：不带单位，数值按 `px` 解释，精度与值域查询 `xml:table`。
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

段内换行不走转义，用 `<br/>` 标签，查询 `xml:span`。XML 源码里的裸换行和缩进是不显著空白，可以用来格式化，但英文句子中间折行会粘连文字。

## 明确不支持的标签与能力

当前 Local XML 只支持关键词协议明确列出的标签；未定义标签均不支持写入。常见不支持标签包括：

- `<checkbox>`、`<callout>`、`<grid>`、`<figure>`；`<column>` 仅允许作为 `<columns>` 的子节点，不可用于正文分栏；
- `<whiteboard>`、`<sheet>`、`<task>`、`<chat_card>`、`<sub-page-list>`、`<html5-block>`、`<okr>`；
- `<cite>`、`<bookmark>`（在线文档标签；Local 书签使用 `<bookmark-start/>` / `<bookmark-end/>`）、`<button>`、`<time>`、`<source>`、URL preview；
- `<wordart>`（WordArt 使用 `<shape word-art="true">`）、`<caption>`（题注使用 `<p role="caption">`）、`<title>`、`<layouts>`、`<docx>`；
- `<latex>` 或其他未定义公式节点；公式只使用 `<equation/>`。

当前也不开放以下能力：文档 theme 定义与 Shape theme ref 写入（文本可引用已有主题字体）、Shape hyperlink sidecar、HYPERLINK Field 定义编辑、任意原始 Field instruction、custom geometry、geometry/warp adjustment、group/canvas、VML TextPath 写入、inline/隐藏 label 题注、对象上方题注及 Caption 全局设置。属性级和对象级只读边界仍以命中的 Field、Note、Drawing 等专项关键词为准。

整套封面模板的创建、插入或替换未开放；不能从“能识别封面”推导为可写。已导入封面中以普通 block 返回的内容，仍可按其实际类型编辑。`<tfoot>` 和 `<layout-break type="next-column">` 在协议中已有定义但尚未实现，同样不要写入。

未支持标签出现在块级位置时整次写入失败；出现在 `<p>`、标题或 `<li>` 的行内位置时，标签可能被剥离、子节点作为纯文本写入并只返回 warning，自闭合未知标签可能直接消失。因此不得用试写判断能力，也不能只看 `ok`；第一层已明确不支持时直接按路由处理。

用 Canvas 命令改不了的结构可保留原样，或按任务[取回 DOCX 改好再提交](../../workflows/canvas-doc-ooxml.md)。整份 DOCX 的编辑路径来自 `+ooxml-fetch`。

所有 XML 写入均受 262144 UTF-8 bytes 请求上限以及 CLI 返回的对象深度、单 story block 和资源数量限制。只提交从最新完整 Fetch 基线生成的最小修改。不要在日志中主动打印正文、Field result、完整 XML 或资源 payload。