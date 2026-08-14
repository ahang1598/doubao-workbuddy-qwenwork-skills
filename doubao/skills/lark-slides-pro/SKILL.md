---
name: lark-slides-pro
version: 1.0.0
description: 飞书幻灯片：创建和编辑幻灯片。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli slides --help"
---

# 飞书幻灯片

本文是总入口和流程主线。按场景路由进入对应分支（新建 / 编辑），逐步执行并在每一步读取该步指向的 `references/` 文档。文档按职责分四类：`style/`（怎么设计）、`cli/`（怎么操作命令）、`xml/`（具体定义）、`workflow/`（流程：排障 / 校验 / 模板改写 / 编辑）。


## 权威经验
1. 你有充足的时间完成一个高质量的幻灯片，**必须对所有页面执行静态校验**，不要以加快进度、提高效率为由减少工作或打乱流程，质量永远比速度重要。
2. **开工通知和成稿交付都必须 NotifyHuman**。
3. **技能中的所有文档都必须完整读完，尾部有重要信息，不要中途截断**。可以分多次读，或把 Read 工具的 `limit` 参数设为 16K 确保一次读全。
4. 牢记幻灯片 URL 和关键 ID（`xml_presentation_id`、`slide_id`、`revision_id`、`file_token`、`block_id`、`obj_token`）。
5. 牢记每一页幻灯片的真实完成状态，不要混淆「已落本地 XML 文件」、「已通过静态校验」、「已写入飞书幻灯片」、「已回读且全文校验通过」。素材同理，区分「已取到本地」、「已去底色（或确认无需抠 / 已回退原图）」、「已上传拿到 `file_token`」。
6. 牢记选定的设计系统，选定后视觉与版式应全程遵守，不能违背。
7. 当用户要求无损复述历史上下文时，必须明确列出上面要求牢记的内容，并在复述末尾原样附上这句提醒（写给接手这段上下文的下一个执行者）：**【非常重要】MUST RELOAD SKILL：对于 PPT 的任务而言，无论之前是否读过 SKILL.md 文档，当用户提出了新的指令时，你的第一个动作或 TodoWrite 中的第一个 Todo 必须是重新 Read lark-slides-pro skill 下的 SKILL.md 文档，在此之前禁止使用任何其他工具或下载任何附件，也不要直接阅读其他的 MD 文档**。


## 一、场景路由

先判断任务类型，再进入对应分支。无论改动是大是小、命令是否熟悉，无论此前是否用过类似命令、做过类似任务，无论之前是否读过对应分支的 MD 文档，**必须重新 Read 对应分支的 MD 文档之后才能动手**。


| 任务                                                 | 对应分支（必读）                                                                                    |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **新建幻灯片**（从零、参考风格，或把图片/PDF 1:1 复刻）    | [`SKILL.md`](SKILL.md) 中「二、新建幻灯片」Step 1 → Step 8                                           |
| **编辑已有幻灯片**（修改已有的 PPTX 或 Slides，或多轮对话里改前轮产物）    | [`workflow/slides-editing.md`](references/workflow/slides-editing.md)            |
| **只要用户给了模板**（给了 PPTX 或 Slides，照它的版式做）  | [`workflow/template-editing.md`](references/workflow/template-editing.md)                         |
| **读取分析已有幻灯片**                                 | [`cli/lark-slides-xml-presentations-get.md`](references/cli/lark-slides-xml-presentations-get.md) |


## 二、新建幻灯片

**核心顺序：理解需求 → 选定设计系统 → 收集素材 → 理大纲 → 准备工作 → 图片处理 → 逐页完成 → 验收交付。**

### Step 1 · 理解需求

先确定：**目的、受众、页数、风格倾向、输入类型**（仅主题 / 完整文档 / 逐页大纲讲稿）。

- **页数**：用户指定则以用户为准；给了逐页大纲/讲稿则对齐其页数；只给主题或给了结构化长文档时，自行按主题和内容量推测一个合理页数直接开始，并在回复里说明你定的页数与理由。
- **默认不打断，能推测就直接做**：需求不完全明确时，优先按合理默认推进，不要为小问题反复发问。只有确实无法推进的硬阻塞才停下来，直接回复向用户说明并提问即可，例如：附件/URL 打不开导致缺关键素材、意图自相矛盾（选了某设计系统又要一个完全冲突的风格 / 既要"做 10 页"又要"输出 30 页以上"）。


### Step 2 · 选定设计系统

设计系统决定整份 deck 的视觉，也决定了下一步要收集哪些素材。

- 先排除两类不走本步的任务：用户给的是**模板**（PPTX 或飞书 Slides） → 不走本步，走「用户给了模板」场景，见 [`workflow/template-editing.md`](references/workflow/template-editing.md)；**复刻任务（把图片/PDF 1:1 还原成幻灯片）** → 不做场景选择，改为分析原图：估算每个元素的位置、字号、配色、间距，尽量 1:1 复刻原稿的版式与视觉。
- 读 [`style/slide-taxonomy.md`](references/style/slide-taxonomy.md) 判定场景，七类里选一个主场景 → 读对应场景文档作为本 deck 的设计系统。
- 不匹配任何场景 → 回退到兜底 [`style/fallback.md`](references/style/fallback.md)。
- 用户已给品牌/配色/字体/参考风格 → 以用户为准。
- 选定后，配色、字体、留白、版式、装饰、图片密度等所有视觉与版式决策一律以选定的设计系统为准，不要从别处引入与之冲突的约束。


### Step 3 · 收集素材

按选定的设计系统决定素材需求，本步负责**确定要哪些素材、并把它们找齐**（联网搜索、搜图、生图都在这里做完）。

- **阅读用户附件（重要性与权威性都最高）**：用户上传/提供的一切材料都是本次任务的第一手事实来源，优先级高于联网搜索和你的先验知识。用户附件里有很多关键信息藏在图/表/公式里，只跑 `paragraphs` / `pdftotext` 会丢掉它们；如果之前读取附件时只获得了文本信息或没有读取附件，那你必须再一次解析附件内容获得更多相关信息，docx 必须再跑 `doc.tables` + `doc.inline_shapes` + `unzip word/media/`，pdf 必须再跑 `fitz.get_images` + `fitz.find_tables` 来获得一些附件中的图片/表格信息或使用 `page.get_pixmap` 来获得 pdf 中的截图，附件中的图片/表格插入 PPT 时，必须保留原图表的所有信息，**绝对不允许做裁剪，但是可以缩放大小来适配 PPT 的排版布局**；与其它来源冲突时以用户附件为准。**在创建 PPT 前，你必须完整阅读附件中嵌入的文字/图片/表格等信息才能创建**。
- **联网搜索**：补齐主题相关的真实数据、事实、案例；不得编造，缺失就标注占位/假设/待补，并标注来源。用户给的是完整文档或逐页大纲、且没说能否扩写时，默认联网搜索扩充素材与案例，除非用户明确要求不扩写。
- **搜图工具**：真实实体（人物、产品、logo、地标等）对应的图片必须用搜图工具获取。搜图时每次少搜一些（工具默认返回 6 张，可把数量设为 4 张），避免一次拉取过多。
- **生图工具**：插画、封面主视觉、示意图、以及缺真实图时的兜底图用生图工具生成。用于背景或封面的图不应带文字，生成后检查，出现文字必须重做。

**记下每张图的原始宽高**，Step 7 写 `<img>` 时要用它做裁剪或缩放大小的参考。


### Step 4 · 理一份轻量大纲

想清楚即可，不必写成文件；可在思考里给出。每页先想清读者任务；尽量用多种版式；翻页要有节奏（有的一眼看完，有的值得细读）。格式参考：

```text
幻灯片标题：
目标受众：
设计系统：[选定场景 或 兜底风格]
配色方案：[主色 / 辅色 / 强调色]
页面规划（共 N 页）：
第 N 页 - 角色/读者任务；关键信息（标题、副标题、核心概念、内容、结论、目标等按需取用）；主视觉
```


### Step 5 · 准备工作

动手落 XML 之前，先把语法读到位、把承接页面的空幻灯片建好。

1. **读语法**：生成任何 XML 前必读 [`xml/xml-schema-quick-ref.md`](references/xml/xml-schema-quick-ref.md)，篇幅较长，务必完整读完；画图表另照抄 [`xml/slides_chart_demo.xml`](references/xml/slides_chart_demo.xml)；用图标先用 `python3 scripts/iconpark_tool.py search --query "<关键词>"` 检索（见 [`xml/iconpark.md`](references/xml/iconpark.md)）。
2. **建空白幻灯片（两步创建·第一步）**：先 `slides +create --title <幻灯片标题>`（不带 `--slides`）建一份空白幻灯片（见 [`cli/lark-slides-create.md`](references/cli/lark-slides-create.md)），**必须从工具返回结果中拿到并记下 `xml_presentation_id` 和 `url`**。Step 6 上传图片、Step 7 写入、Step 8 回读要用 `xml_presentation_id`，Step 5 通知、Step 8 交付要用幻灯片链接 `url`，缺失任何一个都需要重建空白幻灯片。
3. **开工通知**：用 NotifyHuman 工具把上一步拿到的 `url` 发给用户，并在回复里附上简短说明。这个链接和 Step 8 交付用的是同一个地址，但两次都必须发，不能省掉任何一次：这里是开工通知，Step 8 才是成稿交付。

NotifyHuman 提交的链接会变成一张可点击的产物卡片，你需要直接回复向用户说明**PPT 已经开始制作，可以点击卡片，关注进度**，为了确保用户看到，**开工通知务必放到 `<think>` 外输出**（`<think>` 中的内容在展示的时候会被折叠）。这个能边做边看进度的体验非常棒，所以通知环节非常关键，一定要让用户感受到。

### Step 6 · 图片处理

本次要用的图片统一在这一步落地成 `file_token`：**取到本地 → 图片去底色 → 上传**。图片裁剪在 Step 7 中用 `<img>` 的 `<crop>` 实现，不需要在本步处理。

1. **取到本地**：禁止 http(s) 外链，飞书 slides 渲染端不会代理外链图，外链 `src` 在幻灯片里通常不显示；网图必须先 `wget` 下载到 CWD 内，生图/搜图工具的产物同样先落成 CWD 内的文件。
2. **图片去底色**：带底色的图片盖在有色背景上会让整页设计垮掉。对 Step 3 收集到的图片素材，用 Python PIL 的 `ImageDraw.floodfill()` 抠掉纯色底（图片编辑工具做不了抠图，只能走 PIL），**黑白灰底色的图片必须抠**，渐变底和复杂背景直接跳过不要硬抠；结果另存为新的 PNG（不覆盖原图、不可存 JPG）；**抠完逐张检查，确认背景透明、主体边缘无残留色块、主体内部无误抠，如果抠后效果差回退使用原图**。
3. **上传拿 `file_token`**：把本次要用的图片逐个 `+media-upload --file <图片路径> --presentation <id>` 上传，**拿到各自的 `file_token`**（见 [`cli/lark-slides-media-upload.md`](references/cli/lark-slides-media-upload.md)）。


### Step 7 · 逐页完成

**按页闭环：落 XML → 静态校验 → 写入幻灯片**。不需要加快速度，**一页一页来，校验和写入后再做下一页，这样每一页的更新用户都能及时看到，会更满意**，不要攒完整份再统一校验和写入，禁止批量创建。

1. **落 XML**：核心结论定标题，选定的设计系统定版式与配色。带图页把 Step 6 拿到的 `file_token` 写进 `<img src>`。不用写 `<?xml ...?>` 声明，也不用包 `<presentation>`，只提交单个 `<slide>` 元素。元素上不要自己编 `id`，留空即可（ID 由服务端分配，自造 ID 容易撞车）。文本和属性值里的 `&`、`<`、`>` 必须转义为 `&amp;` / `&lt;` / `&gt;`。**全篇禁止使用 emoji（任何位置都不能出现）**，语义图标一律用检索到的 IconPark `<icon>`。
2. **图片使用**：**图片可以裁剪或缩放大小来适配 PPT 的排版布局，不要溢出画布**；**附件中提取的图片/表格不允许做裁剪**，但可以缩放大小来适配你选择的 PPT 的排版布局；`<img>` 的 `width:height` 对齐原图比例就不会裁剪，只会缩放大小；对不上会自动裁剪，且默认从中心裁掉多余部分，可用 `<crop>` 的 `anchor` 指定保留哪一侧。**同一张图片不要在多页重复使用**，补充素材或重新排版，Logo、统一装饰除外。
3. **素材兜底**：主视觉优先用真实素材，绝不留空白图框。缺图先用搜图工具或生图工具补这一页要用的图，补不到或不可用就用生图工具生成替代的近似图或抽象图，生图也不可用才用 `<shape>`+`<line>` 画结构图。数据类可视化缺真实数据时不要编造数字，优先换成不依赖数据的表达（结构图、要点卡片、定性对比），确需图表占位才用原生 `<chart>` 并标注「模拟数据，仅占位，待替换真实数据」。
4. **演讲者备注**：需要在每页 `<slide>` 的 `<note>` 中提供 3–5 句可直接照读的讲稿。
5. **静态校验（必做·至关重要）**：这一页 XML 存成本地文件，跑 `python3 scripts/xml_lint.py --input <文件>`（`--input` 必填，不带参数会报错，见 [`workflow/validation-xml.md`](references/workflow/validation-xml.md)），`error_count` 必须为 0 才能写入。这里只校验这一页的本地文件，写入后针对全文的回读校验在 Step 8。每条 issue 自带 `message`（含实测数值）和 `hint`（具体修法），照着改即可，元素位置看 `elements`。lint 报出的问题绝大多数是真实缺陷、应直接修复；个别你确信是有意设计（如刻意层叠营造设计感）、疑似误报的，留到写入后用 `+screenshot` 核对（见 Step 8），确认无碍可保留并在验证记录说明。
6. **写入幻灯片（两步创建·第二步）**：完成静态校验后，用 `xml_presentation.slide create` 把这一页 `<slide>` 提交（见 [`cli/lark-slides-xml-presentation-slide-create.md`](references/cli/lark-slides-xml-presentation-slide-create.md)）至已创建的幻灯片中（Step 5 记录的 `xml_presentation_id`）。**记下返回的 `slide_id`**：它是这一页的唯一关联键，Step 8 截图和修复都按它定位。写入命令与 `--data` 的组装写法见本步末尾的示例。
7. **失败排障**：`invalid param`、创建失败、空白页、3350001 等报错按 [`workflow/error-handling.md`](references/workflow/error-handling.md) 处理，不假设原操作原子成功，中途某页失败先回读确认状态再修复或追加。**追加/插入页面** 同样用 `slide create`，插到某页前用 `before_slide_id`，它**只能放进 `--data`**——写进 `--params` 会被当成未知 query 参数静默忽略，接口照样返回成功，新页却跑到了末尾。

**写入命令与 `--data` 组装（关键）**：把每页 XML 存成文件，用 `jq --rawfile`/`--arg` 组装，不要把 XML 内联进命令行（中文/引号/特殊字符易被 shell 转义或截断）。例：

```bash
lark-cli slides xml_presentation.slide create \
  --params '{"xml_presentation_id":"<id>"}' \
  --data "$(jq -n --rawfile c slide-01.xml '{slide:{content:$c}}')"
```


### Step 8 · 验收与交付

核对实际页数、页面顺序、关键元素，完整校验清单见 [`workflow/validation-xml.md`](references/workflow/validation-xml.md)。

1. **回读全文**：`slides +xml-get --presentation <xml_presentation_id> --output <CWD 内相对路径>`，`--output` 必填。
2. **解析回读结果**：必须先用 XML 解析器解析，不要用正则或字符串切分；命名空间从根元素实际读取，不要硬编码或猜测，否则匹配不到元素。
3. **对全文重跑静态校验**：`python3 scripts/xml_lint.py --input <回读文件>`，`error_count` 必须为 0。Step 7 逐页都干净不等于全文干净——服务端会规整提交的 XML，且 `id` 跨页撞车这类问题只有全文才查得出。疑似 lint 误报的页用 `slides +screenshot --presentation <xml_presentation_id> --slide-id <slide_id> --output-dir <CWD 内相对路径>` 核对真实渲染（见 [`workflow/validation-visual.md`](references/workflow/validation-visual.md)）；`slide_id` 取自第 1 步的回读结果或 Step 7 的创建响应，多页重复传 `--slide-id`、一次最多 10 页。只有确实拿不到 `slide_id` 时才用 `--slide-number <页号>` 回退定位，定位后立刻换回 `slide_id`。
4. **问题修复**：局部问题用 `+replace-slide`（见 [`cli/lark-slides-replace-slide.md`](references/cli/lark-slides-replace-slide.md)）做块级替换；整页要重做用 `+replace-pages`（见 [`cli/lark-slides-replace-pages.md`](references/cli/lark-slides-replace-pages.md)），或 `slide.delete` 旧页 + `slide.create` 新页。改完重新回读、重新校验。
5. **成稿交付**：用 NotifyHuman 工具把最终幻灯片链接明确交付给用户，并在回复里附上简短说明和验证记录；编辑已有幻灯片同样必须交付链接。交付链接**用 `+create` 返回的 `url` 字段**（Step 5 已记下）。


## 三、参考文档地图


### `style/`


| 文档                                                                                                                                                                    | 何时读                       |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| [`slide-taxonomy.md`](references/style/slide-taxonomy.md)                                                                                                                       | **选定设计系统的入口**：通用规则 + 场景路由 |
| `strategy-and-analysis.md` / `business-pitch.md` / `business-review.md` / `academic-research.md` / `learning-and-training.md` / `technical-presentation.md` / `brand-storytelling.md` | 七个场景各自的设计系统（匹配到哪个读哪个）     |
| [`fallback.md`](references/style/fallback.md)                                                                                                                                   | 兜底设计系统（不匹配任何场景时读）         |




### `xml/`


| 文档                                                                                    | 何时读                  |
| ------------------------------------------------------------------------------------- | -------------------- |
| [`xml-schema-quick-ref.md`](references/xml/xml-schema-quick-ref.md)                   | 生成任何 XML 前必读，元素与属性速查 |
| [`slides_chart_demo.xml`](references/xml/slides_chart_demo.xml)                       | 画图表前照抄范例             |
| [`slides_xml_schema_definition.xml`](references/xml/slides_xml_schema_definition.xml) | 唯一权威 XML 协议，需要精确定义时查 |
| [`iconpark.md`](references/xml/iconpark.md)                                           | IconPark 图标检索与用法     |
| `iconpark-index.json`                                                                 | 图标离线索引，供脚本检索，不用手读    |




### `cli/`


| 文档                                                                                            | 何时读                                |
| --------------------------------------------------------------------------------------------- | ---------------------------------- |
| [`lark-slides-create.md`](references/cli/lark-slides-create.md)                               | `+create` 创建幻灯片（两步创建第一步：建空白幻灯片）    |
| [`lark-slides-xml-presentations-get.md`](references/cli/lark-slides-xml-presentations-get.md) | `+xml-get` 回读全文 XML                |
| [`lark-slides-replace-slide.md`](references/cli/lark-slides-replace-slide.md)                 | `+replace-slide` 块级替换/插入           |
| [`lark-slides-replace-pages.md`](references/cli/lark-slides-replace-pages.md)                 | `+replace-pages` 多页整页重建            |
| [`lark-slides-media-upload.md`](references/cli/lark-slides-media-upload.md)                   | `+media-upload` 上传图片拿 `file_token` |
| [`lark-slides-screenshot.md`](references/cli/lark-slides-screenshot.md)                       | `+screenshot` 截图                   |
| `lark-slides-xml-presentation-slide-create.md` / `-get.md` / `-delete.md` / `-replace.md`     | 单页原生 API（无 shortcut 覆盖时用）          |




### `workflow/`


| 文档                                                                 | 何时读                                                               |
| ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| [`slides-editing.md`](references/workflow/slides-editing.md)       | 在原稿上改的完整流程：理解现状（归一到在线 Slides / 读附件 / 回读 deck）→ 定位改哪里 → 按需备素材 → 改 → 回读校验 |
| [`template-editing.md`](references/workflow/template-editing.md)   | 拿模板做一份新 deck（PPTX/飞书 Slides）：导入或复制成目标文档 → 看全貌选来源页 → 建页面规划 → 逐页复用原始页面与元素来承载新内容（不是机械换字） |
| [`error-handling.md`](references/workflow/error-handling.md)       | XML 语法/接口/错误码排障与失败处理（视觉与版面问题见 validation-visual）                  |
| [`validation-xml.md`](references/workflow/validation-xml.md)       | XML 校验（Step 7/8 必做）                                               |
| [`validation-visual.md`](references/workflow/validation-visual.md) | 截图视觉校验                                                 |




### `scripts/`


| 脚本                                             | 用途                                                                            |
| ---------------------------------------------- | ----------------------------------------------------------------------------- |
| [`xml_lint.py`](scripts/xml_lint.py)           | XML 静态检查（well-formed / schema 合法性与约束 / 元素 ID 重复 / 文本重叠 / 形状·图片·表格·图表遮挡文字 / 越界 / 文本溢出（高度与宽度）/ 文字溢出容器 / 表格尺寸 / icon 填充 / 布局密度；Step 7 每页提交前必跑，Step 8 对回读全文再跑一次） |
| [`xml_inspect.py`](scripts/xml_inspect.py)     | 回读 XML 的导航器：不带 `--slide-id` 输出摘要（页数、页序、每页 `slide_id`、元素统计、正文预览），带 `--slide-id` 返回指定页的完整 raw XML。编辑/模板改写里用它定位页面，避免把整份 XML 读进上下文 |
| [`iconpark_tool.py`](scripts/iconpark_tool.py) | IconPark 图标检索，最小用法 `python3 scripts/iconpark_tool.py search --query "<关键词>"`（再按需 `resolve`）             |




## 四、核心概念



### URL 格式与 Token


| URL 格式     | 示例                                          | Token 类型              | 处理方式                                  |
| ---------- | ------------------------------------------- | --------------------- | ------------------------------------- |
| `/slides/` | `https://xxx.larkoffice.com/slides/xxxx`    | `xml_presentation_id` | 路径中的 token 直接作为 `xml_presentation_id` |
| `/wiki/`   | `https://xxx.larkoffice.com/wiki/wikcnxxxx` | `wiki_token`          | ⚠️ **不能直接用**，需先查询拿真实 `obj_token`      |


**Wiki 链接特殊处理**：直接调用原生 API 前，先查 wiki 节点，确认 `node.obj_type == "slides"`，再用 `node.obj_token` 作为真实 presentation ID：

```bash
lark-cli wiki spaces get_node --params '{"token":"wiki_token"}'
```

> `+replace-slide`、`+media-upload`、`+screenshot`、`+xml-get` 等 shortcut 会自动解析 `/slides/` 和 `/wiki/` URL；只有手动调 `xml_presentations.*` / `xml_presentation.slide.*` 原生 API 时才需要自己解析 wiki。



### 资源关系

```text
Wiki Space (知识空间)
└── Wiki Node (obj_type: slides)
    └── obj_token → xml_presentation_id

Slides (演示文稿)
├── xml_presentation_id (演示文稿唯一标识)
├── revision_id (版本号)
└── Slide (页面)
    └── slide_id (页面唯一标识)
```



### Shortcut 与原生 API

Shortcut 是常用操作的高级封装（`lark-cli slides +<verb> [flags]`），有 shortcut 优先用：


| Shortcut                                                          | 说明                                                         |
| ----------------------------------------------------------------- | ---------------------------------------------------------- |
| [`+create`](references/cli/lark-slides-create.md)                 | 创建幻灯片（统一两步：先建空白幻灯片，再逐页 `slide create`；`--slides` 一步法不再作默认） |
| [`+xml-get`](references/cli/lark-slides-xml-presentations-get.md) | 读全文 XML 并存本地文件，避免终端截断                                      |
| [`+media-upload`](references/cli/lark-slides-media-upload.md)     | 上传本地图片，返回 `file_token`（最大 20 MB）                           |
| [`+replace-slide`](references/cli/lark-slides-replace-slide.md)   | 块级替换/插入，不改页序                                               |
| [`+replace-pages`](references/cli/lark-slides-replace-pages.md)   | 原 presentation 内批量重建多页，不新建链接                               |
| [`+screenshot`](references/cli/lark-slides-screenshot.md)         | 页面截图                                                             |


没有 shortcut 覆盖时用原生 API；调用前必须先看参数结构：

```bash
lark-cli schema slides.<resource>.<method>   # 调 API 前必先看参数结构
lark-cli slides <resource> <method> [flags]  # 调 API
```
