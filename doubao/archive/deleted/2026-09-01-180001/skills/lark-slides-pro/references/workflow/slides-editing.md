# 编辑已有幻灯片

用户已有一份原稿、要在其基础上修改时走这里。原稿可能是当前轮上传的 PPTX、上一轮生成结果或飞书 Slides 链接；是否属于编辑任务看有没有需要保留和修改的原稿。

用户若只沿用原稿版式制作全新内容，转 [`template-editing.md`](template-editing.md)；未提供新模板的扩写、压缩和合并仍走编辑链路。用户提供新模板并要求按其调整或统一风格时，也转 `template-editing`：新模板作为目标文档和视觉来源，原稿作为内容来源，当前轮或前轮用户要求作为制作目标。只有用户明确要求保留原稿链接、仅借用新模板的配色、字体或局部元素时，才继续走编辑链路。

## 总体流程

```text
理解原稿和附件 → 拆解目标/约束/验收 → 锁定变更范围 → 准备素材
→ 结构 → 内容 → 图表/图片 → 排版 → 全局样式 → 回读验收 → 交付
```

用户已指定页面或对象时，只修改指定范围；未指定位置且要求全局优化时，扫描整稿并自主选择最需要改进的页面和内容。“更精美”“更多图表”“图片少一点”等全局要求不能只改一页示例，但也不能改写用户未要求变化的内容，避免指令外的变更。

## 1. 理解原稿和材料

后续只认一个作为交付对象的 `xml_presentation_id`。先识别主原稿，并在主原稿上修改。

| 输入 | 处理 |
|---|---|
| 当前轮 PPTX + 编辑要求 | PPTX 是主原稿，导入后原地编辑 |
| 上一轮结果或 Slides 链接 | 重新实时读取该在线 Slides |
| 上一轮原稿 + 当前轮新模板 + 按模板调整/统一风格 | 转 template-editing；新模板承载结果，原稿提供内容 |
| 两份 PPT 合并 | 确定主原稿与内容来源，再做页面映射 |
| PPT + DOCX/PDF/XLSX/图片 | PPT 是主原稿，其余是事实、数据、素材或品牌规范（如 Logo、标准色和指定字体） |


### 1.1 归一到在线 Slides

**主原稿 PPTX**：导入成在线 Slides，导入结果就是之后编辑和交付的对象，不再回头动本地文件。

> 主原稿或参考模板是 PPTX 时，拿到文件后第一步必须通过 lark-cli drive +import 导入在线 Slides。禁止先使用 python-pptx、解压 PPTX、LibreOffice、本地渲染或其他方式解析内容。导入完成后，只通过服务端 XML、xml_inspect.py 和页面截图理解原稿。导入失败时先排查导入问题，不得静默切换为本地解析后继续编辑。

```bash
lark-cli drive +import --file "<deck.pptx>" --type slides --json
# 未就绪时执行响应里的 next_command，或：
lark-cli drive +task_result --scenario import --ticket <TICKET>
```
导入时可加 `--name` 指定名称，或加 `--folder-token` 指定目标文件夹。

**参考风格/模板 PPTX**：也必须单独导入成在线 Slides，并转 [`template-editing.md`](template-editing.md)；不使用 python 解包本地文件、看缩略图或凭印象学习风格。导入就绪后实时保存全文 XML、生成摘要并截图查看；再按页面角色读取候选页 raw XML，定位可复用页面和 block。

在线参考 Slides 同样实时 `+xml-get`，`/wiki/` 链接先解析真实 `obj_token`。参考稿保持只读；后续写入和交付仍只使用主原稿的 `xml_presentation_id`。

**飞书 Slides 链接/token**：路径里的 token 直接就是 `xml_presentation_id`，不用转换。

**`/wiki/` 链接**：不能直接当 presentation ID 用，先解析真实 `obj_token`，见 SKILL.md「四、核心概念」。

### 1.2 判断附件角色

不要把所有附件笼统当“素材”：

- 参考风格/模板 PPT：必须先导入成在线Slides，结合截图、摘要和候选页 raw XML，提取页面类型、栅格、配色、字体、背景、装饰语言、层级和可复用组件；记录来源 `slide_id`、`block_id`、坐标及结构限制。复用必须从来源页或组件的原始 XML 出发，不能只看截图近似重画；写入主稿前替换内容、按目标 presentation 重新上传媒体并 lint，不替换主稿内容和事实来源。

- 待合并 PPT：建立来源页到目标结构的映射，检查内容覆盖。
- DOCX/PDF/XLSX：作为优先级最高的事实来源；XLSX 要确认工作表、字段、单位、时间范围和真实末行。
- 图片：区分页面图片、背景图和 Logo，记录身份与原始比例。

附件读取见 SKILL.md `Step 3 · 收集素材`。DOCX 不能只读段落，还要读 `doc.tables`、`doc.inline_shapes` 和 `unzip word/media/`；PDF 不能只跑 `pdftotext`，还要跑 `fitz.get_images`、`fitz.find_tables` 和 `page.get_pixmap`。附件提取的图片/表格禁止裁剪，只按原比例缩放。没读完会影响范围判断的附件，不进入第 2 步。

### 1.3 实时回读原稿

必须从服务端重新读取，禁止复用上一轮本地 XML、`slide_id`、`block_id` 或 `revision_id`；用户可能已手改，旧状态会覆盖新改动或报 3350001/3350002。

明确只改某页时直接单页读，响应会带该页的 `block_id` 和 `revision_id`：

```bash
PID="xml_presentation_id"; SID="slide_id"
lark-cli slides +xml-get --presentation "$PID" --slide-id "$SID" --json
```

目标未指定、牵涉多页或属于全局要求时，先读全文摘要再取页：

```bash
# 1. 回读全文到本地（--output 必填）
mkdir -p .lark-slides
lark-cli slides +xml-get --presentation "$PID" \
  --output .lark-slides/current.xml --json

# 2. 看页数、页序、slide_id、元素统计、正文预览；summary.warnings 必读
#    摘要模式可加 --output 落盘，避免占用上下文
python3 scripts/xml_inspect.py --input .lark-slides/current.xml

# 3. 按需取一个或多个目标页的完整 raw XML
python3 scripts/xml_inspect.py --input .lark-slides/current.xml \
  --slide-id "<sid-1>" "<sid-2>"

# 4. raw 模式返回 JSON，XML 在 .slides[].raw_xml；raw 模式不接受 --output
SID="<摘要中选定的 slide_id>"
python3 scripts/xml_inspect.py --input .lark-slides/current.xml --slide-id "$SID" \
  | jq -r '.slides[0].raw_xml' > ".lark-slides/page-$SID.xml"
```

从根 `<presentation>` 记录真实 `width`、`height` 和方向。XML 文件里没有 `revision_id`；它只在 `+xml-get --json` 响应或单页读取的 `data.revision_id` 中，所以 `xml_inspect` 摘要里的 `presentation.revision_id` 恒为 `null`。

必须处理 `summary.warnings`：

- `<undefined>` 多为导入的音视频等不支持块，不能写回；含它的页优先块级替换。整页重建会报 3350001，删除该块又会丢音视频，必须先告知用户。
- 目标 `block_id` 重复时不能唯一替换，改走整页重建；`slide_id` 重复时整页替换和按 ID 取页也不可用，只能先告知用户。

解析 XML 必须使用解析器，并从根元素读取真实命名空间，禁止硬编码。

### 1.4 建立基线并复核路由

XML 摘要负责结构和文字，截图负责真实视觉。局部任务只截图目标页及必须联动的同页对象；全局任务覆盖封面、目录、章节页、内容页、数据页、结束页及异常页。

```bash
# 单页传一个 --slide-id；多页重复该参数，单次最多 10 页
lark-cli slides +screenshot \
  --presentation "$PID" \
  --slide-id "$SID_1" \
  --slide-id "$SID_2" \
  --output-dir .lark-slides/screenshots
```

记录页数/页序、章节、主要文本和数据、图片/图表分布、字体/配色/对齐。内容保护任务保存文本与数据快照；“更多/更少”任务记录修改前数量或覆盖页面。

按产出物复核路由：保留原稿主题和主要内容就继续编辑；内容基本全新、只留版式才转 template-editing。页数变化不是路由依据。

## 2. 拆解要求、修改边界和验收条件

| 维度 | 需要明确 |
|---|---|
| 目标与范围 | 结构/内容/视觉/图片/图表/模板；全局/章节/页面/对象/待诊断 |
| 必须修改 | 用户逐项要求的可观察结果 |
| 必须保留 | 页面、文字、数字、结论、图片、结构、页数或链接 |
| 允许的连带调整 | 为完成目标所必需的同页移动、缩放、换色或重排 |
| 禁止修改 | 指定范围外页面/对象，以及用户未授权变化的内容 |
| 事实来源 | 附件 > 原稿 > 用户事实 > 可信搜索 > 通用知识 |
| 验收条件 | 每个要求完成后可观察、可比较的结果 |

含“和、并且、同时、以及”等连接词的复合请求，必须拆成独立、可验收的子要求，不允许用一个完成项代替另一个。例如“丰富一下，加点例子和图片”至少拆为内容深化、补充案例、增加图片；显式要求的图片、图表、目录、翻译等都必须分别进入修改清单和验收条件。

保护性表达按硬约束执行：“内容不改”禁止改文字、数字和结论；“变化不要太大”保留主题、观点和关键事实；“以表格为准”用 Excel 修正冲突数据；“页数不变”不能靠增删页解决拥挤。

用户明确要求“背景风格更换”时，按**整体背景替换**理解，不得降级为在旧背景上添加几个图标、线条或装饰。“更多、更丰富、少一点”必须与基线比较并覆盖多个页面，不能只处理一个页面。

## 3. 确定修改范围

形成页面级清单，不要求另建计划文件：

```text
slide_id/当前页序｜当前问题｜修改动作｜必须保留｜素材/来源｜验收方式
```

- 用户指定页码时仍从实时回读核对页序，实际按 `slide_id` 操作；指定对象后取 raw XML 确认对象类型、`block_id`、坐标和邻居。`block_id` 是回读 XML 中块的 3 位 short id，如 `<shape id="bUn" ...>`。
- 用户只描述内容目标时，先用摘要 `text_preview` 找候选页，再读 raw XML 确认是 `<chart>`、`<table>` 还是其它块，以及系列数、指标口径和单位；这些信息决定素材缺口和修改方式。
- 视觉目标检查配色、层级、字体、对齐、留白、密度、重复版式、裁剪和跨页一致性。
- 内容深化检查缺少依据/案例/解释的页面、重复内容、附件可补充信息和新增后的承载空间。
- 图表目标扫描对比、占比、趋势、阶段、流程和关系型内容；无真实数据不得制造假图表。
- 图片目标统计分布和视觉占比，区分信息图片与装饰图片；显式要求增加图片时，修改清单不能没有图片项，每项写明目标页、图片角色、附件/搜图/生图来源策略、布局变化和验收方式。新增后必须重排，删减后必须修复留白。
- 背景目标先识别旧背景块及其覆盖页面，再按封面、章节、内容、结束等页面角色规划同一风格的背景或变体；清单写明旧背景如何移除/替换、新背景来源、文字安全区和可读性处理。
- 全局格式先识别页面类型和“正文/标题/页眉”等语义对象，禁止无差别修改所有文本。
- 重新制作某页时必须明确文字动作：“重新撰写/重新写某主题”必须产出新文案；“重新排版/美化”才默认保留文字。不能只换排版冒充内容重写。

压缩、扩展、合并、拆页、删章节或加目录时，先建立：

```text
原页面/章节 → 核心内容 → 新页面/章节 → 保留/合并/精简/扩写/删除
```

页数达标不代表完成；每个核心观点、事实和必要案例都要有去向，目录和章节编号同步更新。

## 4. 准备素材

只准备修改清单确认的缺口；但用户显式提出图片、图表、案例、数据等要求时，对应缺口不得为空。若内容确实不适合承载或来源不可用，必须说明原因，不能静默跳过。

缺数据先查附件再联网，沿用原指标口径、单位和时间范围，禁止编造。真实人物、产品、Logo、地标等必须调用搜图工具获取真实图片；插画、示意图、主视觉或缺少合适真实图片时调用生图工具。搜到素材不算完成：必须下载或生成到本地、完成必要处理和上传、写入目标页并重排布局；只搜索案例或图片，不算完成“增加图片”。

具象风格背景必须准备图片素材：涉及真实场景或实体时优先搜图；漫画、手绘、插画等非真实风格优先生图。生成背景按画布比例制作，不带文字，为标题和正文预留低细节区域，需考虑已有内容，不与已有元素发生重叠遮挡；按页面角色准备少量一致的变体，避免整稿机械重复。背景图保留完整背景，不去底色。

普通配图流程固定为获取本地文件 → 去底色 → `+media-upload`，一步都不能省；禁止 http(s) 外链，`<img src>` 只能填 `file_token`。带底色的图使用去底色工具（运行 `mediakit-cli image remove-image-background --help` 与 `mediakit-cli image remove-image-background --schema` 获取命令的输入输出说明，注意该命令里的boolean 参数--need-crop-background 必须写成 --need-crop-background=true / --need-crop-background=false，--image-url 参数可以接受搜索到的图片URL；未完成上述读取和检查前禁止直接调用）抠纯色底，黑白灰底必抠；抠完效果差则回退原图。**明确作为全画布背景使用的图片保留背景，不执行去底色。** 
下载原稿图片：
```bash
lark-cli api GET "/open-apis/drive/v1/medias/<file_token>/download" --output "<file>"
```

## 5. 按场景执行

复合任务默认按“结构 → 内容 → 图表/图片 → 排版 → 全局样式”执行。结构变更（加页、删页）后立即重新回读页序和 `slide_id`，禁止继续使用旧 ID。

| 场景 | 执行规则 |
|---|---|
| 精确局部修改 | 只修改指定页/对象，优先块级；如果文字变长或新增图片会挤压周围内容，只同时调整该页中受影响的元素。范围外不改动 |
| 全局格式 | 按页面类型和语义对象覆盖全部适用页，处理特殊页例外；不改用户未授权变化的内容 |
| 只排版不改内容 | 用基线锁定文字、数字和数据；只移动、缩放和改样式，完成后前后比较 |
| 清空内容留模板 | 删除所有用户内容文字，不擅自补占位文案；保留背景、装饰和可复用版式，回读确认无残留正文 |
| 压缩/扩展/拆合页 | 先内容覆盖表，再改结构；扩写不靠空泛段落凑页；同步目录和引用 |
| 内容改写/翻译 | 区分润色、重写、丰富、精简、翻译；专名、事实和数据不丢；无来源不造数据 |
| 重新制作指定页 | 根据需求确定执行文字重写或视觉重构；用户要求重新撰写时必须生成新文案，只要求重新排版时才锁定原文字 |
| 调整布局/增加图片/美化 | 先盘点内容与阅读顺序，再分配区域并重排；不得把图片直接叠在现有内容上，也不得靠盲目缩小字号硬塞。空间不足时换布局或减少非必要装饰，只有用户允许时才能拆页 |
| 图片 | 选择图片 → 确定角色 → 重构布局 → 检查渲染；背景处理可读性，替换核对对象身份；水印图改用有权的干净来源，不直接抹除权属标记 |
| 背景换风格 | 识别并移除/替换旧背景 → 搜图或生图 → 放到底层 → 调整前景对比度和安全区；不得保留旧背景再叠少量装饰冒充换背景 |
| 图表/图示 | 对比用柱/条，趋势用线，占比用饼/环，阶段用时间轴，流程用流程图；保留单位、标签和来源 |
| 竖版转横版/更换画布方向 | 当前 lark-cli 不支持修改已有演示文稿的画布宽高。用户要求竖版转横版或更换画布方向时，需要新建目标横版 Slides，以原稿作为内容和视觉来源，将页面内容逐页迁移到新文档。每页写入前按目标画布进行 lint 校验， 确保不引入尺寸适配问题，完成后截图检查。 |
| 明确只参考模板 | 转 template-editing.md |


## 6. 选择 XML 操作并写入

### 6.1 选操作

| 需求 | 用什么 | 理由 |
|------|--------|------|
| 换某个块的整体内容（改标题、换图、挪坐标、改字号） | [`+replace-slide`](../cli/lark-slides-replace-slide.md) 的 `block_replace` | 精准替换单块，`slide_id` 和页序不变 |
| 只加 1~N 个元素、不动现有布局 | `+replace-slide` 的 `block_insert` | 新增不覆盖，可选 `insert_before_block_id` 定位 |
| 一次动多个块（如换标题 + 加图） | 单次 `--parts` 里拼多条，`block_replace` / `block_insert` 混用 | 整批原子事务，任一失败整批不生效 |
| **删除某个元素** | [`+update-slide`](../cli/lark-slides-update-slide.md) 整页覆盖 | 块级只有 `block_replace` / `block_insert`，**没有删除块的动作**；整页覆盖时没写进 `--content` 的元素即被删除 |
| **跨页统一改某个属性**（整份换字体、换配色等全局改写） | [`+update-slide`](../cli/lark-slides-update-slide.md)（每页一次） | 没有字段级 patch，逐块 `block_replace` 代价高；把受影响的页逐页整页覆盖更省事 |
| 多页版式重建、整页坐标重排 | [`+update-slide`](../cli/lark-slides-update-slide.md)（每页一次） | 原地整页覆盖，`slide_id` 和页序不变，不生成新链接 |
| 追加新页 | [`+add-slide`](../cli/lark-slides-add-slide.md)，插到某页前加 `--before-slide-id` | 省略 `--before-slide-id` 就是追加到末尾 |
| **删除整页** | [`+delete-slide`](../cli/lark-slides-delete-slide.md) | **不可逆**（可走 `+history-revert` 回滚），删前先确认这页确实不要了；一份 deck 至少得留一页 |

所有操作原地更新主 presentation，不要用 `+create` 另建链接。没有字段级 patch、删除块或 `str_replace`：即使只改坐标也要替换整个块；`+update-slide` 原地覆盖整页，`slide_id` 和页序都不变，但没写进 `--content` 的元素会被删除。

### 6.2 XML 与 lint

动手前必读 [`xml-schema-quick-ref.md`](../xml/xml-schema-quick-ref.md)。不要编 ID；转义 `& < >`；禁用 emoji，语义图标使用 IconPark；新增页补 `<note>`，整页重建保留原 `<note>`。除非用户要求换风格，新元素复用原稿字体、层级、配色、留白和对齐轴。

块片段不能直接 lint。把修改块拼回完整 `<slide>` 后运行：

```bash
python3 scripts/xml_lint.py --input <整页文件>
```

原则上非豁免 error 必须为 0 才写入。若导入原稿的真实画布宽或高超过 960×540，先记录根 `<presentation>` 的实际宽高；优先用真实宽高包装单页后 lint。若单页 lint 因回退到 960×540 而产生 `shape_out_of_canvas`、`img_out_of_canvas`、`table_out_of_canvas` 或 `chart_out_of_canvas`，且元素仍位于真实画布内，可标记 `canvas_size_mismatch` 后放行，不得为清除假越界生硬缩小元素。重叠、遮挡、文本溢出以及真正超出实际画布的问题仍必须修复。用户明确要求转换画布时按目标画布校验，不适用此豁免。

修改底色、文字颜色、字号、边框、线条粗细或布局后，必须对该页完整 XML 重新 lint；写入后立即回读并截图。截图检查文字/图标/线条与底色的对比度、相邻色块是否粘连、边框是否过粗抢占视觉、异常换行、文本溢出、重叠和裁切。只通过 lint 不能证明视觉合格。


### 6.3 块级替换与加图

```bash
lark-cli slides +replace-slide --presentation "$PID" --slide-id "$SID" \
  --parts '[{"action":"block_replace","block_id":"bUn","replacement":"<shape type=\"text\" topLeftX=\"80\" topLeftY=\"80\" width=\"800\" height=\"120\"><content textType=\"title\"><p>新标题</p></content></shape>"}]'
```

CLI 会补 replacement 根 `id` 和缺失的 `<content/>`，不要手写。并发/多步编辑可从读取响应取 `revision_id` 传 `--revision-id`；XML 文件里没有它，默认 `-1` 基于最新版，传入超过当前版本的值会报 3350002。写入结果不明确时先回读再重试，见 [`error-handling.md`](error-handling.md)。

给已有页加图时先读坐标；空间不足就在同一 `--parts` 中移动/缩小邻居后插入。需要把背景或底纹放到前景块之后时，用 `insert_before_block_id` 插到页面第一个前景块之前；无法可靠控制层级时改走整页重建。附件提取图片/表格只按原比例缩放，`<img>` 的 `width:height` 对齐原图比例时只缩放、不裁剪；普通图框比例不同时默认中心裁剪，可用 `<crop>` 的 `anchor` 指定保留侧，但不能切主体。同一普通配图不跨页重复，Logo/统一装饰除外。

```bash
TOKEN=$(lark-cli slides +media-upload --file ./pic.png \
  --presentation "$PID" --jq '.data.file_token')
lark-cli slides +replace-slide --presentation "$PID" --slide-id "$SID" \
  --parts "$(jq -n --arg t "$TOKEN" \
    '[{action:"block_insert",insertion:("<img src=\""+$t+"\" topLeftX=\"500\" topLeftY=\"100\" width=\"200\" height=\"150\"/>")}]')"
```

### 6.4 整页覆盖与增删页

`+update-slide` 要完整 `<slide>`，不接受 `--parts`；一次一页，多页就每页各跑一次。content 本身就是整页，直接对它 lint，不用像块级替换那样先拼回原页。先确认页面没有 `<undefined>`，参数见 [`+update-slide`](../cli/lark-slides-update-slide.md)：

```bash
# page-01.xml 是这一页改好的完整 <slide>，已 lint 通过
lark-cli slides +update-slide --presentation "$PID" --slide-id "$SID" --content @page-01.xml --dry-run
lark-cli slides +update-slide --presentation "$PID" --slide-id "$SID" --content @page-01.xml
```

**加页与删页**：`--before-slide-id` 指定插入位置，省掉就是追加到末尾。

```bash
lark-cli slides +add-slide  \
  --presentation "$PID" \
  --slide @new-page.xml \
  --before-slide-id "$SID"
lark-cli slides +delete-slide --presentation "$PID" --slide-id "$SID"
```

## 7. 回读验收并交付

必须使用最新回读结果，逐项完成五层验收：

1. **范围**：目标范围内要求全部完成；范围外页面和对象无计划外变化；允许的连带调整没有越界。
2. **任务要求**：页数/时长、目录、字号/颜色/Logo覆盖、翻译范围、指定文字/图片/图表、更多/更少相对基线全部满足；复合请求逐项验收，不支持项明确说明。显式要求增加图片时，核对目标页已实际新增图片并完成布局调整；只有搜索记录、没有页面落图，判定为未完成。
3. **内容结构**：内容保护任务前后文字、数字、数据和结论一致；要求重写时确实生成符合主题的新文案，不能只换排版；附件驱动任务核对字段、数字、单位和时间范围；检查页序、章节、目录和引用。
4. **XML**：重新 `+xml-get`，对最新全文跑 `xml_lint.py`，不得引入新错误；逐页确认目标元素和服务端规整后的结构。见 [`validation-xml.md`](validation-xml.md)。
5. **视觉**：所有视觉变化页都截图；全局风格、画布方向转换任务检查全部页面；检查溢出、异常换行、遮挡、裁切、清晰度、对齐、留白、层级、字号、边框粗细、对比度和一致性。背景换风格还要确认旧背景无残留、新背景实际覆盖目标页；只增加装饰元素判定为未完成。无法完成必要截图时不得声称视觉验收完成。见 [`validation-visual.md`](validation-visual.md)。

全部通过后用 present_files 交付最终链接，并简述主要修改、实际范围、页数/关键约束、和明确未支持项。

## 相关文档

- [lark-slides-replace-slide.md](../cli/lark-slides-replace-slide.md) — `+replace-slide` 命令、parts 字段、合法根元素、报错（编辑主命令，细节都在这）
- [lark-slides-update-slide.md](../cli/lark-slides-update-slide.md) — 整页原地覆盖（多页就每页各跑一次）
- [lark-slides-xml-presentation-slide-get.md](../cli/lark-slides-xml-presentation-slide-get.md) — 单页读取
- [lark-slides-add-slide.md](../cli/lark-slides-add-slide.md) — 追加/插入新页（`--before-slide-id` 定位）
- [lark-slides-delete-slide.md](../cli/lark-slides-delete-slide.md) — 删除整页（不可逆）
- [lark-slides-xml-presentations-get.md](../cli/lark-slides-xml-presentations-get.md) — `+xml-get` 回读全文到本地文件
- [lark-slides-media-upload.md](../cli/lark-slides-media-upload.md) — 上传图片拿 `file_token`
- [lark-slides-screenshot.md](../cli/lark-slides-screenshot.md) — `+screenshot` 页面截图
- [xml-schema-quick-ref.md](../xml/xml-schema-quick-ref.md) — XML 元素与属性速查
- [validation-xml.md](validation-xml.md) — 写入前/写入后两道校验关卡
- [template-editing.md](template-editing.md) — 拿模板做一份新 deck（不是在原稿上改）
