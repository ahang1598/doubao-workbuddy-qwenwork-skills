## PDF 转飞书文档

PDF 转飞书文档工作流必须使用 `create_agent` 启动。各个agent只需阅读本文档中自己负责的部分，无需关注其他agent的工作。

### 命中信号

用户提供 PDF，且交付目标是**飞书云文档**（Docx 或 Wiki）时，使用本流程。命中关键词包括 `飞书文档`、`飞书云文档`、`lark doc`，以及包含 `feishu.cn/docx/...` 或 `larkoffice.com/docx/...` 的 URL。若目标是 `.docx` 格式的 Word 文件，则使用 `pdf-to-word.md`，不使用本流程。

### 三个层级的Agent
#### MainAgent
`MainAgent`的主要工作:
1. 如果用户未提供目标文档，先使用`docs +create`创建一个空的飞书云文档
2. 启动`OrganizerAgent`并传递相关上下文
3. `OrganizerAgent`工作完成后，`MainAgent`承担交付任务

用户提供目标文档时，读取其正文状态；若非空，只有在用户明确要求覆盖时才能先按更新规则移除或替换原正文，否则应另建空文档。

#### OrganizerAgent
`OrganizerAgent`的主要工作:
1. 统计PDF的页数，每 4 页启动一个`SubAgent`重建PDF，实现并行处理
2. 每个`SubAgent`会输出其负责的4页PDF对应的 DocxXML 片段，`OrganizerAgent`按 PDF 页码顺序将各批次片段写入待交付的飞书云文档。

#### SubAgent
`SubAgent`的主要工作是按照下文中`SubAgent的转换核心要求`要求重建每4页的内容，完成后交付给`OrganizerAgent`

### 转换必读文件
1. `lark-doc/SKILL.md`
2. `lark-doc/references/lark-doc-xml.md`（飞书 XML 语法）
3. `lark-doc/references/lark-doc-update.md`（分批 append、str_replace、block_replace 等）

### SubAgent的转换核心要求
#### 过程记录文件
在SubAgent重建PDF时，必须在工作目录创建独立的 `pdf-to-doc-process-{subagent_id}.md`，并在整个转换过程中持续更新。创建前可以读取 PDF 元数据以取得总页数，并按上文确定目标文档；暂时无法取得的字段先标记为 `pending`，取得后立即补齐。该文件只记录本次任务的处理过程，不得插入待上传 XML，也不得写入目标飞书文档。图片处理记录统一按“页码 → 裁剪 run → 裁剪文件”组织，所有目录和文件均记录实际路径，不得只写“已完成”。

至少记录以下内容：

- 当前批次ID、PDF路径、需要处理的页号、目标文档链接或 token
- 裁剪输出根目录、`run-id` 及其目录
- 当前有效 run 中裁剪图的路径及 XML 插入位置
- `unclear_source`、`source_anomaly`、源色到落地色映射、版式调整、失败与恢复操作

#### 公式转换要求（`<latex>`）

凡可以可靠转录的公式必须使用飞书原生 `<latex>...</latex>`；禁止以纯文本近似（如 `x^2 + 1`）、Unicode 上下标（如 `x²`）或截图代替，也不得创建空 `<latex>`。

**识别**：依据源页面中的数学字体名（`CM*`、`MSAM`、`STIX`、`Cambria Math`、`Symbol`）、密集数学符号（`∑ ∫ ∏ √ ± ≤ ≥ ≠ → ∈ ∀ ∃`、希腊字母、上下标嵌套、根号）、分数线特征（水平细线夹在两行小字之间），以及整行居中且右侧带 `(数字)` 或 `(章节.序号)`的文本行。

**转录规则**：

- 同时参考源页面高清渲染图、文本层和字体信息；三者冲突时以可见渲染结果为最终依据，不直接采信可能错误解码的公式字符。
- 上下标、共轭 `\bar`、转置 `^{\top}`、极限 `\lim_{n\to\infty}`、大定界符 `\left(\right)`、分段函数 `\begin{cases}...\end{cases}`、对齐推导 `\begin{aligned}...\end{aligned}`，以及矩阵 `\begin{bmatrix}` 或 `\begin{pmatrix}` 均按源文转录。
- **无法辨认的内容**：局部无法辨认时，在对应位置使用 `\text{[unclear]}`，并在交付说明中记录 `unclear_source` 的页码、位置和上下文；整条公式无法可靠辨认时，不创建空 `<latex>` 或猜测内容，改用相邻普通段落明确标注“源公式无法可靠转录”，并将其列入未完成项。
- **函数名直立**：`\sin \cos \log \exp \lim \min \max` 使用内置命令（自动直立）；单字母变量默认使用斜体。
- **多字符变量名**使用 `\mathrm{Var}` 或 `\text{if}`，不要写成 `Var`（否则会被当作 `V·a·r`）。
- **疑似原文笔误**（量纲不匹配、明显手误）应**忠实保留**，并在交付说明中单独列为 `source_anomaly`；不要擅自改成正确形式。

**写入 XML**：

- **行内公式**： 与正文写在同一段中：`<p>由 <latex>a=2</latex> 可得...</p>`。
- **独立公式**： 单独成段并居中：`<p align="center"><latex>a^2 = 4</latex></p>`。
- **带编号的独立公式**：单独成段并居中，使用 `\tag{编号}` 添加编号，并写在 `<latex>` 内部。例如：`<p align="center"><latex>a^2 = 4 \tag{公式1.4}</latex></p>`。

**LaTeX 中的 XML 转义**：LaTeX 源码中的 `<`、`>`、`&` **必须写成 XML 实体** `&lt;`、`&gt;`、`&amp;`；花括号 `{}` 无需转义。


```xml
<!-- 错 -->
<latex>a<b</latex>
<latex>P(A&B)</latex>

<!-- 对 -->
<latex>a&lt;b</latex>
<latex>P(text\_A \land text\_B) \tag{2-5}</latex>
<latex>\begin{aligned}a&amp;=b+c\\&amp;=d\end{aligned}</latex>
```

逻辑“与”优先使用 `\land`；`aligned`、矩阵等 LaTeX 语法中的对齐符 `&` 仍须保留，但在 XML 中写成 `&amp;`。

**LaTeX 元素内禁止嵌套任何 XML 标签**——强调或颜色样式应写在 `<latex>` 外部，或使用 LaTeX 内置命令（如 `\boldsymbol`、`\color{red}`）。

#### 表格转换要求（`<table>`）

表格必须使用飞书原生 `<table>`；禁止转为段落文本、用制表符拼接的 `<pre>` 或代码块、项目符号列表或整表截图。

**结构要求**：

- 源表存在语义表头时，在 `<thead>` 中使用 `<th>`；没有表头时不要凭空创建。数据行放在 `<tbody>` 中并使用 `<td>`。
- 合并单元格使用 `colspan` 或 `rowspan`，且**只在起始单元格中出现**；被合并的单元格不要重复写入。
- 使用 `<colgroup><col width="..."/></colgroup>` 显式指定列宽，`width` 数值按照源表格的列宽比例反推，不附加未在 `lark-doc-xml.md` 中声明的单位。禁止**无依据**均分；源表本身等宽时可以等分。
- 单元格内如果包含公式，必须仍用 `<latex>`。
- 底纹使用 `background-color` 命名色：基础 7 色、`light-{色相}` 或 `medium-gray`；表格单元格不得使用其他 `medium-*` 值。源文使用飞书不支持的十六进制颜色时，降级为最接近的命名色，并在交付说明中列出“源色 → 落地色”。无法通过飞书 XML 表达的边框颜色也应列入保真妥协。

**跨页表格**：语义连续且服务端可接受时使用一张 `<table>`，并删除续页中重复出现的表头。若单表写入失败、体量过大或超出批次限制，则按连续行拆表，每张表重复语义表头并注明“续表”；不得删除数据行。

**超宽表**：不要为了缩窄版面合并不同语义的列。确实无法在文档宽度内清晰呈现时，按列组拆成多张 `<table>`，每张重复主键或标识列，并在正文中明确说明“该表按列分段呈现”。服务端返回容量或结构错误时停止当前批次，根据错误缩小表格或拆分行；当前 `lark-doc-xml.md` 未声明固定列数或单元格数上限，不得编造具体上限。**禁止**降级为 `<pre>` 或代码块。

**目视可见但未被识别的表格**：PDF 中的表格有时没有边框，仅依靠空白对齐。先使用 PyMuPDF `page.find_tables()`；未识别时，再结合文本 x 起点、行基线、列间空白和语义一致性补建 `<table>`。仅凭 x 坐标聚类不足以判定表格。

#### 图片转换要求（`<img>`，必须真实上传）

本地图片必须在对应批次 XML 的原位置使用 `<img path="@./relative/path"/>` 上传；公开 HTTPS 图片可使用 `href`，仅复制文档中已有图片时使用 `src` token。禁止用占位文字代替图片、以 `src` 引用本地文件，以及使用 `file://` 或 `data-src`。

**硬性要求**：正文与图片必须同步处理，裁剪得到的图片按对应页面写入 XML。

**目录口径**：裁剪图写入 `<figure-output-dir>/<run-id>/`。执行命令后，立即把实际目录、文件名和 `run-id` 写入过程记录文件，并保证 XML 引用的图片路径可由批次 XML 相对访问。

##### 1. 使用脚本批量定位并裁剪

使用 `python scripts/locate_pdf_figures.py <source.pdf> --pages "5-8" --output <figure-output-dir> --run-id <run-id>`，将 PDF 中的图片裁剪下来。
每轮结果位于独立的 `<figure-output-dir>/<run-id>/` 目录，目录内只包含本轮裁剪图。裁剪图命名为 `page-<四位页码>-image-<两位序号>.png`，例如 `page-0030-image-01.png`。

##### 2. 图注转换要求

图注优先使用对应 `<img>` 的 `caption` 属性写入，如 `<img path="@./figure.png" caption="图 1 示例"/>`，并忠实保留图号、标题和子图标识，不得将图注裁入图片；仅当原生图注无法表达复杂内容时，才降级为紧随图片的独立文本段落。

#### 目录转换要求

对于整个文档的目录，使用两列表格进行转换，按照8：2的比例分配宽度，左列是文章内容中的标题，右列是标题的页码。

目录中标题的缩进、格式也按照原文中的格式进行转换。

如果整个批次以文档目录开始或结尾，要注意可能与相邻批次的目录有粘连。

#### 飞书 XML 的几个陷阱

**不要在待上传 XML 中使用注释**：XML 注释不是 `lark-doc-xml.md` 声明的文档结构，页码、批次和处理备注应保存在本次任务的过程记录文件中。若草稿已含注释，使用支持 XML fragment 的解析方式（先包裹临时根节点）删除注释，再序列化根节点的全部子节点；不要直接对包含多个顶层 block 的 DocxXML 调用 `etree.fromstring(xml_bytes)`，也不要用正则表达式处理 XML。

**多栏页面按语义选择 `<grid>`**：双语并排、逐项对照或阅读关系依赖横向位置时使用 `<grid>`，各栏 `width-ratio` 之和为 `1`，并按源页面比例设置。普通学术或报纸双栏若只是连续阅读流，可以按“左栏从上到下，再右栏从上到下”转成单栏；同页存在跨栏标题、表格或图片时，应拆成“满宽 block + grid + 满宽 block”，不要把整页机械包进一个 grid。

#### SubAgent 的交付

`SubAgent`必须向 `OrganizerAgent` 交付以下产物：

1. **DocxXML 文件**：包含本批次最多 4 页、按源 PDF 阅读顺序排列且可直接用于 `append` 的 XML 片段。文件不得包含临时根节点、XML 注释、页码标记或处理备注。所有 `<img path>` 必须使用相对于该 XML 文件的有效路径。
2. **交接 README**：即本批次的 `pdf-to-doc-process-{subagent_id}.md` 过程记录文件，不另建内容重复的说明文件。除上文要求的过程记录外，交付时还必须集中列出：
   - 批次 ID、页码范围、DocxXML 文件路径、目标文档链接或 token，以及裁剪图所在目录。
   - 所有 `unclear_source`、`source_anomaly`、保真妥协、失败与恢复操作和未完成项。
3. **图片资产目录（如有）**：随 DocxXML 一并保留所有被 `<img path>` 引用的最终裁剪图片。不得交付未被 XML 引用的临时候选图作为有效资产，也不得在交付后移动、重命名或删除图片，直至 `OrganizerAgent` 完成写入。

### OrganizerAgent的写入

`OrganizerAgent` 负责汇总各 `SubAgent` 交付的 DocxXML 片段，并按 PDF 页码顺序分批写入目标文档。具体流程如下：

1. **排序批次**：无论各 `SubAgent` 以何种顺序完成，都必须按 PDF 页码范围对批次排序。
2. **按序写入**：按批次页码范围升序执行 `docs +update --command append`，将内容写入目标文档。一次最多只上传5000个block，XML大小不超过200 kB，超过上传上限时需要将本批次进一步拆开，按顺序上传，直至全部批次写入完成。

### MainAgent的交付说明

根据PDF的页数计算耗时，小于20页的PDF约20分钟，20页以上，每10页多7分钟，将计算后的耗时通知用户，并告知用户可以先处理其他任务，任务完成后交付。

交付内容必须包含：

1. **文档链接与当前 `revision_id`**（便于用户回滚）。
2. **保真妥协**：源色 → 落地色映射、栏宽近似值、跨页或超宽表拆分说明、转为单栏的页面、无法完全排除的裁剪残留文本，以及无法映射的 PDF 内部锚点。

**飞书不保留 PDF 的文档物理分页**——这是产品特性，应在交付说明中明确指出，避免用户误认为这是保真失败。

===== 全文完 =====
