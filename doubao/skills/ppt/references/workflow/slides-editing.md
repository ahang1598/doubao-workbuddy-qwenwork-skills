# 编辑已有幻灯片

用户已有一份原稿、要在其基础上修改时走这里。原稿可能是当前轮上传的 PPTX、上一轮生成结果或飞书 Slides 链接；是否属于编辑任务看有没有需要保留和修改的原稿。

用户若提供 PPT（PPTX 或在线 Slides）先根据用户要求判断新增 PPT 的用途。用于组合、合并或整合两稿内容时，继续本编辑流程，同时要求统一风格也不改变这一判断。用户将附件指定为模板，或要求采用附件的版式制作时，转 [`template-editing-main.md`](template-editing-main.md)；基于已有原稿套模板时，先阅读其中“已有原稿套用模板”一节。

**本地电脑模式背景补充**：SystemPrompt 里若出现 `Computer OS: Mac` 或 `Computer OS: Windows`，**阅读完本文档后必须完整 Read [`workflow/local-compat.md`](references/workflow/local-compat.md)，查看在本地电脑模式下执行命令所需要知道的背景，否则会出现大面积报错**

**写入 XML 前必须完成的检查**：

- 实时读取目标页最新的 raw XML，确认哪些内容需要修改、哪些内容必须保持不变；不能只看摘要、凭记忆或重新制作页面。
- 列出原稿中本轮没有要求修改的内容，并记录其原值、单位、表达的含义以及与其它内容的对应关系；编辑时不得删除、改写、重新计算或用新内容替换这些内容。
- 用户要求扩展内容时，只能在用户指定的范围内新增；新增内容要与原稿内容区分清楚，不能冒充或覆盖原稿内容，也不能与原稿事实冲突。转到 `template-editing-main.md` 流程时，也必须保留这份原稿内容清单，模板只能改变视觉和版式。


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
| 已有原稿 + 用户指定的模板 / 要求采用附件版式 | 转 template-editing-main.md，先读“已有原稿套用模板”一节 |
| 两份 PPT 组合合并，包括同时要求统一风格 | 继续本编辑流程。围绕主稿目标，按主题重新组织两稿内容，将相关观点、案例和数据安排到对应章节；统一视觉风格，保留原有内容、数据和结论 |
| PPT + DOCX/PDF/XLSX/图片 | PPT 是主原稿，其余是事实、数据、素材或品牌规范（如 Logo、标准色和指定字体） |


### 1.1 归一到在线 Slides

**主原稿 PPTX**：导入成在线 Slides，导入结果就是之后编辑和交付的对象，不再回头动本地文件。

> 主原稿或参考模板是 PPTX 时，拿到文件后第一步必须通过 lark-cli drive +import 导入在线 Slides。禁止先使用 python-pptx、解压 PPTX、LibreOffice、本地渲染或其他方式解析内容。导入完成后，只通过服务端 XML、xml_inspect.py 和页面截图理解原稿。导入失败时先排查导入问题，不得静默切换为本地解析后继续编辑。

```bash
lark-cli drive +import --file "./<deck>.pptx" --type slides --json
# `--file` 只接受 CWD 内的相对路径。PPTX 不在 CWD 时，先将文件复制到 CWD 并保留原文件名，再传入相对路径；不得直接传绝对路径。
# 未就绪时执行响应里的 next_command，或：
lark-cli drive +task_result --scenario import --ticket <TICKET>
```
导入时可加 `--name` 指定名称，或加 `--folder-token` 指定目标文件夹。

**飞书 Slides 链接/token**：路径里的 token 直接就是 `xml_presentation_id`，不用转换。

**`/wiki/` 链接**：不能直接当 presentation ID 用，先解析真实 `obj_token`，见 SKILL.md「四、核心概念」。

### 1.2 判断附件角色

不要把所有附件笼统当“素材”：

- 待合并 PPT：用户要求将其中内容与原稿组合，作为内容来源；建立来源内容到目标章节、页面的映射，检查内容覆盖。
- 模板 PPT：用户指定其作为模板，或要求采用其版式，作为版式和视觉来源。
- DOCX/PDF/XLSX：作为优先级最高的事实来源；XLSX 要确认工作表、字段、单位、时间范围和真实末行。
- 图片：区分页面图片、背景图和 Logo，记录身份与原始比例。

附件读取见 SKILL.md `Step 3 · 收集素材`。DOCX 不能只读段落，还要读 `doc.tables`、`doc.inline_shapes` 和 `unzip word/media/`；PDF 不能只跑 `pdftotext`，还要跑 `fitz.get_images`、`fitz.find_tables` 和 `page.get_pixmap`。附件提取的图片/表格禁止裁剪，只按原比例缩放。没读完会影响范围判断的附件，不进入第 2 步。

### 1.3 实时回读原稿、保存内容与 lint 基线

必须从服务端 xml-get 重新读取，禁止复用上一轮本地 XML、`slide_id`、`block_id` 或 `revision_id`；用户可能已手改，旧状态会覆盖新改动或报 3350001/3350002。首次写入前，必须连续完成“保存最新全文 XML 及同次完整响应 → 提取全稿内容 content → 确认 content 非空”，并读取 lint 检测状态和诊断，才算建立基线，验收完成前不得覆盖或修改。

文件保存在当前工作目录 `<CWD>` 下，命令用相对路径；每轮按任务区分文件名，后续回读另存，不能覆盖已有文件或基线。以下是 Bash 示例；Windows 按 [`windows-compat.md`](windows-compat.md) 使用 Python 保存响应和编排命令，保持 UTF-8 编码。

```bash
PRES="xml_presentation_id"
if lark-cli slides +xml-get --presentation "$PRES" \
  --output "./source.xml" --json > "./source-response.json" \
  2> "./source-error.json"; then
  python3 scripts/xml_inspect.py --input "./source.xml" --mode content --output "./source-content.txt" || exit 1
  python3 scripts/lint_inspect.py --input "./source-response.json"
else
  cat "./source-response.json" "./source-error.json"
  exit 1
fi
```

`source.xml` 保存写入前的完整结构，`source-content.txt` 保存全稿可见文字、数字、单位、表格/图表数据和结论，不包含演讲者备注；`source-response.json` 保存版本、读取范围和展开的 `data.issues` 报告。即使只改一页，也必须先建立整稿基线；不得用摘要、截图、旧文件或记忆代替，也不得先截图、准备素材或写入后再补基线。后续在线回读另存为 `current.xml`、`current-response.json` 等，需比较的不同批次分别命名。

上例在同次调用中保存内容并显示 lint 检测状态、数量和诊断；确认 content 非空、`response_ok` 及报告有效性后，按 `--details --limit 3 --max-chars 6000` 分页读完文档级和相关页面问题；不能只读 lint 检测报告摘要。脚本路径以当前 Skill 目录为准，参数见 [`validation-xml.md`](validation-xml.md)。

明确只改某页时，从本轮保存的全文 XML 读取该页完整 raw XML：

```bash
SID="slide_id"
python3 scripts/xml_inspect.py --input "./source.xml" --slide-id "$SID" --mode raw
```

完成整稿基线建立后，若目标页未指定、任务涉及多页或属于全局要求，先从 `source.xml` 读取 XML 内容与结构摘要以定位目标页，再读取相关页面的完整 raw XML：

```bash
# 1. 看页数、页序、slide_id、元素统计、正文预览；summary.warnings 是本地结构提示，也要读取，不能替代服务端 lint
python3 scripts/xml_inspect.py --input "./source.xml" --mode summary

# 2. 修改对象前，取目标页的完整 raw XML
python3 scripts/xml_inspect.py --input "./source.xml" --mode raw --slide-id "<sid-1>" "<sid-2>"

# 3. raw 模式返回 JSON，XML 在 .slides[].raw_xml
SID="<XML 内容与结构摘要中选定的 slide_id>"
python3 scripts/xml_inspect.py --input "./source.xml" --slide-id "$SID" --mode raw \
  | jq -r '.slides[0].raw_xml' > "./page-$SID.xml"
```

用 `--mode summary|content|raw` 选模式（默认 summary）。summary 固定读全稿；content/raw 不选页读全稿，可加 `--slide-id ID...` 选页。三种模式均可用 `--output` 保存。XML 内容与结构摘要只用于导航，可能截断，不包含服务端 lint。`--mode content` 用纯文本保留页/块 ID、完整页面文字、表格行列/合并/显式颜色、图表字段名和值，并提示未展开的对象，可加 `--output content.txt` 落盘；它不输出演讲者备注，也不是可回写 XML。raw 太大时按目标块读取完整片段，不能只读前几千字符就重写整页。`tag_counts` 和 `embeds` 用于补查对象类型；图片或图标计数为 0 不代表没有 SVG 等图形。

选定目标后，必须读取对应原稿页的 lint 详情（`--details --slide-number <同次报告页码>`）及文档级问题，按 `pagination.next_offset` 读到 `has_more: false`，不能只保存报告或只读 XML 索引。整稿第 4 页可能在单页写入报告中编号为 1，按实际 slide ID 与同次 XML 页序对应后再比较；不能按总数或同名 code 认定继承。命令示例与字段路径见 [`validation-xml.md`](validation-xml.md)「按目标页读取基线的例子」。

从根 `<presentation>` 记录真实 `width`、`height` 和方向。XML 文件里没有 `revision_id`；它只在 `+xml-get --json` 响应或单页读取的 `data.revision_id` 中，所以 `xml_inspect` 的 XML 内容与结构摘要里的 `presentation.revision_id` 恒为 `null`。

保存同次读取的页序与 `slide_id` 对应关系；单页 lint 按请求/响应的 slide ID 定位，不把内部页码直接当整稿页码。后续补充单页回读时，XML 根 `<slide>` 可能不带命名空间，不能直接交给当前 `xml_inspect.py`；可用 XML 解析器按实际结构读取，或从最新整稿 XML 提取。`+xml-get` 不支持重复 `--slide-id` 读取多页，需要逐页请求或整份读取后本地取页；补充回读不能覆盖原稿基线，也不等于完成修改后的问题复核。

必须处理 `summary.warnings`：
- `<undefined>` 可能是图表、音视频或其它当前不可写回的对象；权限提示也不表示它可删除。原页含此块且用户未要求删除时，必须对支持的块做 `block_replace` / `block_insert`，让未知对象留在服务端。不能为通过 lint/写入而删块后整页覆盖；任务确实需要改该对象时，先说明限制并取得可用来源或明确取舍。
- 目标 `block_id` 重复时不能唯一替换；只有原页全部对象都可保留并写回时才可整页覆盖，否则说明无法安全定位。`slide_id` 重复时，按 ID 取页和整页替换也不可用。

解析 XML 必须使用解析器，并从根元素读取真实命名空间，禁止硬编码。修改原 XML 时保留 SVG、嵌入对象及其命名空间；重新序列化导致命名空间丢失或写入失败时，应保留原片段或修复序列化，不能用删图解决报错。

### 1.4 建立基线并复核路由

XML 内容与结构摘要用于定位页面，content 模式读取页面文字和数据，raw XML 确认对象结构，截图确认真实视觉。局部任务只截图目标页及必须联动的同页对象；全局任务覆盖封面、目录、章节页、内容页、数据页、结束页及异常页。

```bash
# 单页传一个 --slide-id；多页重复该参数，单次最多 8 页
lark-cli slides +screenshot \
  --presentation "$PRES" \
  --slide-id "$SID_1" \
  --slide-id "$SID_2" \
  --output-dir ./screenshots/
```

记录页数/页序、章节、主要文本和数据、图片/图表分布、字体/配色/对齐。内容保护任务保存文本与数据快照；视觉任务保留 `<p>`、`<note>`、表格单元格和图表数据的完整字符串，内容任务另列保护项及允许新增/改写的字段。保护项必须带语义锚点并保留完整表达、来源和结论，不能只存摘要或无上下文的数字。“更多/更少”任务记录修改前数量或覆盖页面。


## 2. 拆解要求、修改边界和验收条件

| 维度 | 需要明确 |
|---|---|
| 目标与范围 | 结构/内容/视觉/图片/图表/模板；全局/章节/页面/对象/待诊断 |
| 必须修改 | 用户逐项要求的可观察结果 |
| 必须保留 | 页面、文字、数字、结论、图片、结构、页数或链接 |
| 允许的连带调整 | 为完成目标所必需的同页移动、缩放、换色或重排 |
| 禁止修改 | 指定范围外页面/对象，以及用户未授权变化的内容 |
| 事实来源 | 本轮用户指定/更正 > 指定数据源或附件 > 原稿；搜索只补授权新增内容，冲突先核实  |
| 验收条件 | 每个要求完成后可观察、可比较的结果 |

含“和、并且、同时、以及”等连接词的复合请求，必须拆成独立、可验收的子要求，不允许用一个完成项代替另一个。例如“丰富一下，加点例子和图片”至少拆为内容深化、补充案例、增加图片；显式要求的图片、图表、目录、翻译等都必须分别进入修改清单和验收条件。

保护性表达按硬约束执行：“内容不改”禁止改文字、数字和结论；“变化不要太大”保留主题、观点和关键事实；“以表格为准”用 Excel 修正冲突数据；“页数不变”不能靠增删页解决拥挤。

“美化/更精美、换风格、统一底色、调布局、加图片”等视觉指令只授权视觉变化，均按内容保护任务处理：默认锁定原稿文字、数字、比例、单位、表格/图表数据和业务结论，未经明确要求不得增删、改写或用近似值替换。压缩页数只授权重组、合并和必要的文字精简，不授权改变上述事实；无法在目标页数内完整保留时先说明取舍，不得自行改数或改结论。

“丰富内容、增加案例、更多图表”授权在目标范围内新增，不授权改写原稿已有内容。新增案例可带新数字，示意数据必须明确标注“示意”；保护基线中的内容仍须保持原有身份、取值、关系和含义。

用户明确要求“背景风格更换”时，按**整体背景替换**理解，不得降级为在旧背景上添加几个图标、线条或装饰。要求重新排版时，必须改变内容分区、大小关系或阅读顺序；只换色、加装饰不算完成。“更多、更丰富、少一点”必须与基线比较并覆盖多个页面，不能只处理一个页面。

## 3. 确定修改范围

形成页面级清单，不要求另建计划文件：

```text
slide_id/当前页序｜当前问题｜修改动作｜必须保留｜素材/来源｜验收方式
```

- 用户指定页码时仍从实时回读核对页序，实际按 `slide_id` 操作；指定对象后取 raw XML 确认对象类型、`block_id`、坐标和邻居。`block_id` 是回读 XML 中块的 3 位 short id，如 `<shape id="bUn" ...>`。
- 用户只描述内容目标时，先用 XML 内容与结构摘要中的 `text_preview` 找候选页，再用 content 模式读全内容、用 raw XML 确认是 `<chart>`、`<table>` 还是其它块，以及系列数、指标口径和单位；这些信息决定素材缺口和修改方式。
- 视觉目标检查配色、层级、字体、对齐、留白、密度、重复版式、裁剪和跨页一致性。
- 内容深化检查缺少依据/案例/解释的页面、重复内容、附件可补充信息和新增后的承载空间。
- 图表目标扫描对比、占比、趋势、阶段、流程和树状结构需求；无真实数据不得制造假图表。需要使用到树状图时先查 `relation_help()`，正式 Slides 用 atomized 可编辑输出，不得把树状图主体做成 `<embed>`。
- 图片目标统计分布和视觉占比，区分信息图片与装饰图片；显式要求增加图片时，修改清单不能没有图片项，每项写明目标页、图片角色、附件/搜图/生图来源策略、布局变化和验收方式。新增后必须重排，删减后必须修复留白。
- 背景目标先识别旧背景块及其覆盖页面，再按封面、章节、内容、结束等页面角色规划同一风格的背景或变体；清单写明旧背景如何移除/替换、新背景来源、文字安全区和可读性处理。
- 全局格式先识别页面类型和“正文/标题/页眉”等对象，禁止无差别修改所有文本；明确要求统一底色时覆盖全部页面角色，一般统一风格可保留合理深浅变体。
- 重新制作某页时必须明确文字动作：“重新撰写/重新写某主题”必须产出新文案；“重新排版/美化”才默认保留文字。

压缩、扩展、合并、拆页、删章节或加目录时，先建立：

```text
原页面/章节 → 核心内容 → 新页面/章节 → 保留/合并/精简/扩写/删除
```

页数达标不代表完成；每个核心观点、事实和必要案例都要有去向，目录和章节编号同步更新。

## 4. 准备素材

只准备修改清单确认的缺口；但用户显式提出图片、图表、案例、数据等要求时，对应缺口不得为空。若内容确实不适合承载或来源不可用，必须说明原因，不能静默跳过。

缺数据先查附件再联网，沿用原指标口径、单位和时间范围，禁止编造。真实人物、产品、Logo、地标等必须调用搜图工具获取真实图片；插画、示意图、主视觉或缺少合适真实图片时调用生图工具。搜到素材不算完成：必须下载或生成到本地、完成必要处理和上传、写入目标页并重排布局；只搜索案例或图片，不算完成“增加图片”。

具象风格背景必须准备图片素材：涉及真实场景或实体时优先搜图；漫画、手绘、插画等非真实风格优先生图。生成背景按画布比例制作，不带文字，为标题和正文预留低细节区域，需考虑已有内容，不与已有元素发生重叠遮挡；按页面角色准备少量一致的变体，避免整稿机械重复。背景图保留完整背景，不去底色。

普通配图流程固定为获取本地文件 → 去底色 → `+media-upload`，一步都不能省；禁止 http(s) 外链，`<img src>` 只能填 `file_token`。带底色的图使用去底色工具（运行 `mediakit-cli image remove-image-background --help` 与 `mediakit-cli image remove-image-background --schema` 获取命令的输入输出说明，注意该命令里的boolean 参数--need-crop-background 必须写成 --need-crop-background=true / --need-crop-background=false，--image-url 参数可以接受搜索到的图片URL；动漫卡通相关无论图片主体是什么，参数--scene均设置为product；未完成上述读取和检查前禁止直接调用）抠纯色底，黑白灰底必抠；抠完效果差则回退原图。**明确作为全画布背景使用的图片保留背景，不执行去底色。** 

下载原稿图片：
```bash
lark-cli api GET "/open-apis/drive/v1/medias/<file_token>/download" --output "<file>"
```

## 5. 按场景执行

复合任务默认按“结构 → 内容 → 图表/图片 → 排版 → 全局样式”执行。结构变更（加页、删页）后立即重新回读页序和 `slide_id`，禁止继续使用旧 ID。
**美化、排版和全局格式本身**不包含内容改写授权；用户未同时明确要求内容变化，或明确要求保持内容和章节架构不变时，按内容保护任务执行：页面可见文字、数字、单位、表格/图表数据和结论必须与基线一致。可以在保持字词、标点和阅读顺序的前提下拆分或合并文本框，但不得借机润色、精简、扩写或补充内容。

| 场景 | 执行规则 |
|---|---|
| 精确局部修改 | 只修改指定页/对象，优先块级；如果文字变长或新增图片会挤压周围内容，只同时调整该页中受影响的元素。范围外不改动 |
| 全局格式 | 按页面类型和语义对象覆盖全部适用页，处理特殊页例外；不改用户未授权变化的内容 |
| 只排版不改内容 | 用基线锁定文字、数字和数据；只移动、缩放和改样式，完成后前后比较 |
| 清空内容留模板 | 删除所有用户内容文字，不擅自补占位文案；保留背景、装饰和可复用版式，回读确认无残留正文 |
| 压缩/扩展/拆合页 | 先内容覆盖表，再改结构；结构变化不等于授权修改事实，数字、比例、单位、表格/图表数据和业务结论保持不变；扩写不靠空泛段落凑页；同步目录和引用 |
| 两份或多份 PPT 组合 | 围绕主稿主题安排两稿内容，将相关内容放在一起，不建议直接前后机械拼接；统一视觉风格，保留原有内容、数据和结论 |
| 内容改写/翻译 | 区分润色、重写、丰富、精简、翻译；专名和原有事实不丢；新增案例数据注明来源或“示意”，不得伪装成原稿事实 |
| 丰富内容/增加案例/更多图表 | 新增项与原内容分开呈现；可增加解释、案例、结论和配套数字，但不得替换、删除或重算原有数字、数据系列、规则和结论 |
| 调整布局/增加图片/美化 | 只改视觉，不增删或改写原文字与数据；先盘点内容与阅读顺序，再分配区域并重排。不得把图片直接叠在现有内容上，也不得靠盲目缩小字号硬塞；空间不足时换布局或减少非必要装饰，只有用户允许时才能拆页 |
| 图片 | 选择图片 → 确定角色 → 重构布局 → 检查渲染；背景处理可读性，替换核对对象身份；水印图改用有权的干净来源，不直接抹除权属标记 |
| 背景换风格 | 识别并移除/替换旧背景 → 搜图或生图 → 放到底层 → 调整前景对比度和安全区；不得保留旧背景再叠少量装饰冒充换背景 |
| 图表/图示 | 对比用柱/条，趋势用线，占比用饼/环，阶段用时间轴，流程用流程图；只改图表类型时原类别、数值、单位、标签、来源及周边正文/演讲者备注保持不变，不得为适配图表重解释数据 |
| 竖版转横版/更换画布方向 | 当前 lark-cli 不支持修改已有演示文稿的画布宽高。用户要求竖版转横版或更换画布方向时，需要新建目标横版 Slides，以原稿作为内容和视觉来源，将页面内容逐页迁移到新文档。每页写入后按目标画布截图检查，确保没有引入尺寸适配问题。 |

## 6. 选择 XML 操作并写入

### 6.1 选操作

内容保护任务的候选 XML 必须复制自本轮实时读取的 raw XML，再只改白名单内的样式、坐标、图片或结构；整页重建也不得从 XML 内容与结构摘要或记忆重新写文案。不授权改写 `<p>`、`<note>`、表格单元格、图表数据或业务规则。用户允许删除的装饰可以删除；未知对象不能当装饰处理。

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

### 6.2 XML 与校验

动手前必读 [`xml-schema-quick-ref.md`](../xml/xml-schema-quick-ref.md)、涉及选择、修改字体时还必读 [`fonts.md`](../xml/fonts.md)。不要编 ID；转义 `& < >`；禁用 emoji，语义图标使用 IconPark；新增页补演讲者备注 `<note>`，整页重建保留原演讲者备注。除非用户要求换风格，新元素复用原稿字体、层级、配色、留白和对齐轴。

写入前先对“基线 XML → 候选 XML”做内容差异检查：逐项核对带语义锚点的保护项，不能只比较无上下文的文字或数字集合；其原值、单位、关联关系、完整性和含义必须保持。视觉任务的保护字符串必须一致；内容任务只允许改清单列出的字段，授权新增项单独验收且不得覆盖基线。发现保护项缺失、换值、关联变化、信息不完整或含义改变时停止写入并修复。服务端版式校验只看结构和布局，不能替代内容差异检查。

**每个修改页先开启 lint 提交，修复后仍开启 lint 重验。** 动手前完整读取 [`validation-xml.md`](validation-xml.md) 的报告解析和单页例外规则；`4000153` 的 `error.message` 是 JSON 字符串，直接解码当次返回的完整字符串，读完 `document` 和 `slides[]` 各级问题的正文；报告过大或工具输出截断时，先检查是否已有该次完整响应文件；有文件时可用 `lint_inspect.py` 分页读取，只有截断文本时无法恢复遗漏内容，不能据此认定问题已全部处理。块级替换校验 parts 拼装后的整页：旧元素没改，也可能被本次新增图片遮挡或受重排影响，必须核对相关元素及位置关系。新增或加重的问题必须修复，不能归为原稿问题。逐页直接检查当次响应，成功无问题时记录 ID/版本并继续；成功的 `data.issues` 按对象/数组、JSON 字符串或普通文本完整读取，创建还要检查 `data.slide_issues`，不要只读 summary 或消息前缀。遇到失败或 `data.issues` 时停下处理，禁止公共参数或循环默认带 `--no-lint`。

按 [`validation-xml.md`](validation-xml.md)「原稿基线与前后对比」判断继承、新增和加重的问题；基线中没有某条问题，不足以证明写入时才引入，需核对规则覆盖范围和原稿 XML。当前回读或失败报告不能覆盖原始基线；原稿既有问题也不能直接作为跳过写入 lint 的依据。修复布局时保留正文、数值、单位、标签和图例；不能通过批量删除这些信息消除 lint。

**非标准画布例外**：原稿真实画布宽或高超过 960×540 时，服务端可能按 960×540 报 `shape_out_of_canvas`、`img_out_of_canvas`、`table_out_of_canvas` 或 `chart_out_of_canvas`。先记录根 `<presentation>` 的实际宽高，核对被指出的元素确实仍在真实画布内；当前页报告中的越界全部确认是假越界、其他问题已处理后，才按单页例外规则单独重提并立即回读、截图；不能套用到其他页，也不得为清除假越界生硬缩小元素。重叠、遮挡、文本溢出以及真正超出实际画布的问题仍必须修复。用户明确要求转换画布时按目标画布判定，不适用此例外。

修改底色、文字颜色、字号、边框、线条粗细或布局后，写入后立即回读并截图。截图检查文字/图标/线条与底色的对比度、相邻色块是否粘连、边框是否过粗抢占视觉、异常换行、文本溢出、重叠和裁切。通过服务端校验不能证明视觉合格。增大字号时，须同步检查文本框容量；出现溢出、异常换行或遮挡时，应在保留内容、满足目标字号及用户布局约束的前提下，扩大文本框并按需调整相邻元素，修复后复验，不得仅完成字号修改就交付。




### 6.3 块级替换与加图

```bash
lark-cli slides +replace-slide --presentation "$PRES" --slide-id "$SID" \
  --parts '[{"action":"block_replace","block_id":"bUn","replacement":"<shape type=\"text\" topLeftX=\"80\" topLeftY=\"80\" width=\"800\" height=\"120\"><content textType=\"title\"><p>新标题</p></content></shape>"}]'
```

CLI 会补 replacement 根 `id` 和缺失的 `<content/>`，不要手写。并发/多步编辑可从读取响应取 `revision_id` 传 `--revision-id`；XML 文件里没有它，默认 `-1` 基于最新版，传入超过当前版本的值会报 3350002。写入结果不明确时先回读再重试，见 [`error-handling.md`](error-handling.md)。

给已有页加图时先读坐标；空间不足就在同一 `--parts` 中移动/缩小/重排邻居后插入。需要把背景或底纹放到前景块之后时，用 `insert_before_block_id` 插到页面第一个前景块之前；无法可靠控制层级时改走整页重建。附件提取图片/表格只按原比例缩放，`<img>` 的 `width:height` 对齐原图比例时只缩放、不裁剪；普通图框比例不同时默认中心裁剪，可用 `<crop>` 的 `anchor` 指定保留侧，但不能切主体。同一普通配图不跨页重复，Logo/统一装饰除外。

```bash
TOKEN=$(lark-cli slides +media-upload --file ./pic.png \
  --presentation "$PRES" --jq '.data.file_token')
lark-cli slides +replace-slide --presentation "$PRES" --slide-id "$SID" \
  --parts "$(jq -n --arg t "$TOKEN" \
    '[{action:"block_insert",insertion:("<img src=\""+$t+"\" topLeftX=\"500\" topLeftY=\"100\" width=\"200\" height=\"150\"/>")}]')"
```

### 6.4 整页覆盖与增删页

`+update-slide` 要完整 `<slide>`，不接受 `--parts`；一次一页，多页就每页各跑一次。先确认页面没有 `<undefined>`，参数见 [`+update-slide`](../cli/lark-slides-update-slide.md)：

```bash
# page-01.xml 是这一页改好的完整 <slide>
lark-cli slides +update-slide --presentation "$PRES" --slide-id "$SID" --content @page-01.xml --dry-run
lark-cli slides +update-slide --presentation "$PRES" --slide-id "$SID" --content @page-01.xml
```

**加页与删页**：`--before-slide-id` 指定插入位置，省掉就是追加到末尾。

```bash
lark-cli slides +add-slide  \
  --presentation "$PRES" \
  --slide @new-page.xml \
  --before-slide-id "$SID"
lark-cli slides +delete-slide --presentation "$PRES" --slide-id "$SID"
```

## 7. 回读验收并交付

必须使用最新回读结果，逐项完成五层验收：

1. **范围**：目标范围内要求全部完成；范围外页面和对象无计划外变化；允许的连带调整没有越界。
2. **任务要求**：页数/时长、目录、字号/颜色/Logo覆盖、翻译范围、指定文字/图片/图表、更多/更少相对基线全部满足；复合请求逐项验收，不支持项明确说明。显式要求增加图片时，核对目标页已实际新增图片并完成布局调整；只有搜索记录、没有页面落图，判定为未完成。
3. **内容结构**：所有未明确授权改内容的任务，前后文字、数字、比例、单位、表格/图表数据和结论必须一致；要求重写时确实生成符合主题的新文案，不能只换排版；附件驱动任务核对字段、数字、单位和时间范围；检查页序、章节、目录和引用。
4. **XML 与回读 lint**：逐页核对本次写入报告均已处理，写入 lint 通过或单页例外已核验；对修改范围重新 `+xml-get --output`，另存实际结果 XML 与完整响应，处理回读报告并与原稿基线比较，新增或加重的真实问题须修复后重验。不能以 `ok: true`、缺失报告或错误总数下降代替通过；范围外的原稿既有问题单独说明，不擅自修改。逐页确认目标元素和服务端规整后的结构，并核对页数、内容完整性、跨页 `id` 撞车、素材落地；涉及页集合变化时回读全文。见 [`validation-xml.md`](validation-xml.md)。
5. **视觉**：所有视觉变化页都截图；全局风格、画布方向转换任务检查全部页面；检查溢出、异常换行、遮挡、裁切、清晰度、对齐、留白、层级、字号、边框粗细、对比度和一致性。背景换风格还要确认旧背景无残留、新背景实际覆盖目标页；只增加装饰元素判定为未完成。无法完成必要截图时，该页仍未完成视觉验收，不得仅凭写入成功交付为已完成。见 [`validation-visual.md`](validation-visual.md)。

全部通过后用 present_files 交付最终链接，并简述主要修改、实际范围、页数/关键约束、和明确未支持项。前轮已经交付过、链接未变化也不能省略本轮交付。

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
- [validation-xml.md](validation-xml.md) — 写入报告解析、修复与单页例外规则、回读核对
- [template-editing-main.md](template-editing-main.md) — 模板制作新内容，或保留原稿内容套用新模板
