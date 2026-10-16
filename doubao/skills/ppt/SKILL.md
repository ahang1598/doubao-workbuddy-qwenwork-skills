---
name: ppt
version: 1.0.32
description: 飞书幻灯片：创建和编辑幻灯片。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli slides --help"
---

# 飞书幻灯片

本文是总入口和流程主线。按场景路由进入对应分支（新建 / 编辑），逐步执行并在每一步读取该步指向的 `references/` 文档。文档按职责分四类：`style/`（怎么设计）、`cli/`（怎么操作命令）、`xml/`（具体定义）、`workflow/`（流程：排障 / 校验 / 模板改写 / 编辑）。


## 权威经验
1. 你有充足的时间完成一个高质量的幻灯片，**每个新增或修改页都必须开启服务端 lint 提交；修复问题后仍须开启 lint 重验**。不得以批量处理、提高效率或其他页报过错为由跳过校验；`--no-lint` 只能按单页例外规则使用，见 [`validation-xml.md`](references/workflow/validation-xml.md)。
2. **开工通知和成稿交付都必须调用 present_files 工具**。
3. **按当前场景、需求和步骤选中的必读文档必须完整读完，尾部有重要信息，不要中途截断**。Read 工具单次返回有 token 上限，`limit` 单位为行数；大文件需用 `offset` + `limit` 分段续读，直到返回 `[End of file.]` 为止。
4. 牢记幻灯片 URL 和关键 ID（`xml_presentation_id`、`slide_id`、`revision_id`、`file_token`、`block_id`、`obj_token`）。
5. 牢记每一页幻灯片的真实完成状态，不要混淆「已落本地 XML 文件」、「已写入飞书幻灯片」、「已通过写入 lint」、「已完成例外核验」、「已回读并完成 lint 与内容核对」；使用 `--no-lint` 后写入成功不等于通过 lint。编辑/模板任务在修改前保存原稿 XML 与回读 lint 基线，修改后另存回读结果用于比较，见 [`validation-xml.md`](references/workflow/validation-xml.md)。素材同理，区分「已取到本地」、「已去底色（或确认无需抠 / 已回退原图）」、「已上传拿到 `file_token`」。
6. 牢记选定的设计系统，选定后视觉与版式应全程遵守，不能违背。
7. **本地电脑模式背景补充**：SystemPrompt 里若出现 `Computer OS: Mac` 或 `Computer OS: Windows` （电脑端不一定就是本地电脑，也可能是云电脑），**在阅读完本 SKILL后，必须完整 Read [`workflow/local-compat.md`](references/workflow/local-compat.md)，查看在本地电脑模式下执行命令所需要知道的背景，否则会出现大面积报错**，并且如果产物是在线幻灯片（非有本地路径和token的本地文件），在最后请使用 `lark-cli drive +export` 和 `present_files` 将文件重新导出来给到用户本地文件的路径。
8. **Windows 平台差异**：SystemPrompt 里若出现 `Computer OS: Windows`（电脑端不一定是 windows），**在阅读完 local-compat.md 后，必须完整 Read [`workflow/windows-compat.md`](references/workflow/windows-compat.md)，查看在 windows 平台上执行命令所必须要注意的问题，否则会出现大面积报错**。
9. 跨轮编辑后的交付（强制）：只要本轮对用户可见的幻灯片发生了实际写入或更新，验收完成后必须在本轮再次调用 present_files 交付最新版本。即使该幻灯片链接已在前序轮次交付、URL 没有变化，也不得复用前轮产物卡片或只提示用户刷新。
10. **除了本 skill 下的其他文档的说明，默认不调用 organizer**：对于 PPT 的任务而言，除非本 skill 中的文档有说明需要调用 organizer，否则默认不使用 organizer 做多 agent 任务
11. **【非常重要】用户提供了模版的情况下，绝对不允许批量生成/编辑xml文件**：一定要一个文件一个文件去写好、上传、通过lint；做批量生成/编辑的xml文件上传到页面中完全不可用的
12. **除了 chart 库生成的 svg 以外的 svg 图必须走 atomize**：手画的概念图/示意图/流程图/装饰图必须读 svg-writing-guide.md，用 drawing 库（`scripts/svg_lib/svg_drawing.py`，常用接口已列在指南第四节）画图，`to_slide` 输出可编辑原生元素。chart 库（`gen_svg_charts.py`）的数据图用 `chart_slide(...)` 放入页面，得到半可编辑结果（文字原生、同色色块可整体换色）。这两类结果直接按页开启服务端 lint 写入；不要先跑本地 `xml_lint.py` 校准（它会对图内文字与色块误报），数据图不渲染 PNG 预览；手画示意图先 `d.check()` 自检，`d.review()` 有细节提示时再 `d.preview()` 看一次、精修一轮后写入（见 svg-writing-guide.md 第四节「审查有提示才预览精修」），不要为避开告警改用 PNG 图片或手画图替代；按数值画长短的条形/点（如 ORR、比例对比）也属于数据图，必须走 `chart_slide`，不能用 rect 拼
13. **【非常重要】MUST RELOAD SKILL：对于 PPT 的任务而言，无论之前是否读过 SKILL.md 文档，当用户提出了新的指令时，你的第一个工具调用必须是重新 Read ppt skill 下的 SKILL.md 文档，在此之前禁止使用任何其他工具或执行 xml 相关指令；若用户新上传了附件需要下载或解析，解析完附件后也必须立即重新 Read ppt 下的 SKILL.md 再继续，不得跳过。**


## 一、场景路由

先判断任务类型，再进入对应分支。无论改动是大是小、命令是否熟悉，无论此前是否用过类似命令、做过类似任务，无论之前是否读过对应分支的 MD 文档，**必须重新 Read 对应分支的 MD 文档之后才能动手**。**特别是多轮对话中用户对前轮已有 PPT 的任何修改/扩写/压缩精简/组合合并/重新排版/调整风格等，都属于"编辑已有幻灯片"场景，本次动手前必须先完整 Read references/workflow/slides-editing.md，不得凭上一轮记忆直接改 XML。**


| 任务                                                 | 对应分支（必读）                                                                                    |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **新建幻灯片**（从零、参考风格，或把图片/PDF 1:1 复刻）    | [`SKILL.md`](SKILL.md) 中「二、新建幻灯片」Step 1 → Step 8                                           |
| **编辑已有幻灯片**（修改已有的 PPTX 或 Slides，或多轮对话里改前轮产物）    | [`workflow/slides-editing.md`](references/workflow/slides-editing.md)            |
| **只要用户给了模板**（给了 PPTX 或 Slides，照它的版式做）  | [`workflow/template-editing-main.md`](references/workflow/template-editing-main.md) |
| **读取分析已有幻灯片**                                 | [`cli/lark-slides-xml-presentations-get.md`](references/cli/lark-slides-xml-presentations-get.md) |


## 二、新建幻灯片

**核心顺序：理解需求 → 选定设计系统 → 收集素材 → 理大纲 → 准备工作 → 图片处理 → 逐页完成 → 验收交付。**

### Step 1 · 理解需求

先确定：**目的、受众、页数、风格倾向、输入类型**（仅主题 / 完整文档 / 逐页大纲讲稿）。

- **页数**：用户指定则以用户为准；给了逐页大纲/讲稿则对齐其页数；只给主题或给了结构化长文档时，自行按主题和内容量推测一个合理页数直接开始，并在回复里说明你定的页数与理由。
- **默认不打断，能推测就直接做**：需求不完全明确时，优先按合理默认推进，不要为小问题反复发问。只有确实无法推进的硬阻塞才停下来，直接回复向用户说明并提问即可，例如：附件/URL 打不开导致缺关键素材、意图自相矛盾（选了某设计系统又要一个完全冲突的风格 / 既要"做 10 页"又要"输出 30 页以上"）。


### Step 2 · 选定设计系统

设计系统决定整份 deck 的视觉，也决定了下一步要收集哪些素材。

- 先排除两类不走本步的任务：用户给的是**模板**（PPTX 或飞书 Slides） → 不走本步，走「用户给了模板」场景，见 [`workflow/template-editing-main.md`](references/workflow/template-editing-main.md)；**复刻任务（把图片/PDF 1:1 还原成幻灯片）** → 不做场景选择，改为分析原图：估算每个元素的位置、字号、配色、间距，尽量 1:1 复刻原稿的版式与视觉。
- 读 [`style/slide-taxonomy.md`](references/style/slide-taxonomy.md) 判定场景，七类里选一个主场景 → 读对应场景文档作为本 deck 的设计系统。
- 不匹配任何场景 → 回退到兜底 [`style/fallback.md`](references/style/fallback.md)。
- 用户已给品牌/配色/字体/参考风格 → 以用户为准。
- 选定后，配色、字体、留白、版式、装饰、图片密度等所有视觉与版式决策一律以选定的设计系统为准，不要从别处引入与之冲突的约束。


### Step 3 · 收集素材

按选定的设计系统决定素材需求，本步负责**确定要哪些素材、并把它们找齐**（联网搜索、搜图、生图都在这里做完）。

- **阅读用户附件（重要性与权威性都最高）**：用户上传/提供的一切材料都是本次任务的第一手事实来源，优先级高于联网搜索和你的先验知识。用户附件里有很多关键信息藏在图/表/公式里，只跑 `paragraphs` / `pdftotext` 会丢掉它们；如果之前读取附件时只获得了文本信息或没有读取附件，那你必须再一次解析附件内容获得更多相关信息，docx 必须再跑 `doc.tables` + `doc.inline_shapes` + `unzip word/media/`，pdf 必须再跑 `fitz.get_images` + `fitz.find_tables` 来获得一些附件中的图片/表格信息或使用 `page.get_pixmap` 来获得 pdf 中的截图，附件中的图片/表格插入 PPT 时，必须保留原图表的所有信息，**绝对不允许做裁剪，但是可以缩放大小来适配 PPT 的排版布局**；与其它来源冲突时以用户附件为准。**在创建 PPT 前，你必须完整阅读附件中嵌入的文字/图片/表格等信息才能创建**。（本条仅适用于作为内容或素材来源的 DOCX、PDF、XLSX、图片等辅助附件。作为主原稿或模板的 PPTX/Slides 必须先导入或读取在线 Slides，再通过服务端 XML 和截图分析，不做本地 PPTX 解析。）
- **联网搜索**：补齐主题相关的真实数据、事实、案例；不得编造，缺失就标注占位/假设/待补，并标注来源。用户给的是完整文档或逐页大纲、且没说能否扩写时，默认联网搜索扩充素材与案例，除非用户明确要求不扩写，学术场景可以加载并使用学术搜索工具，而不是通用搜索。
- **网页精读**：对于搜索到的重要的网页，可以使用 web fetch 工具阅读网页中的完整内容，来补充更多真实数据，对于 academic 场景的 ppt 而言，精读论文可以拿到真实的完整数据，不要跳过这一步，同时也不要过度滥用这个工具，一次 academic 相关的任务只使用1-3次
- **搜图工具**：真实实体（人物、产品、logo、地标等）对应的图片必须用搜图工具获取。搜图时每次少搜一些（工具默认返回 6 张，可把数量设为 4 张），避免一次拉取过多。
- **生图工具**：插画、封面主视觉、示意图、以及缺真实图时的兜底图用生图工具生成。用于背景或封面的图不应带文字，生成后检查，出现文字必须重做。**在生成 ppt 的过程中，禁止去阅读 “doubao creative design” 这个 skill**， 可以直接调用生图工具，阅读这个 skill 会造成大量不必要的 token 消耗

**记下每张图的原始宽高**，Step 7 写 `<img>` 时要用它做裁剪或缩放大小的参考。


### Step 4 · 理一份轻量大纲

想清楚即可，不必写成文件；可在思考里给出。每页先想清读者任务；尽量用多种版式；翻页要有节奏（有的一眼看完，有的值得细读）。**注意整理大纲目录规划需要与后续内容页正确对应。** 格式参考：

```text
幻灯片标题：
目标受众：
设计系统：[选定场景 或 兜底风格]
配色方案：[主色 / 辅色 / 强调色]
页面规划（共 N 页）：
第 N 页 - 角色/读者任务；关键信息（标题、副标题、核心概念、内容、结论、目标等按需取用）
```

### Step 5 · 准备工作

动手落 XML 之前，先把语法读到位、把承接页面的空幻灯片建好。

1. **读语法**：生成任何 XML 前必读 [`xml/xml-schema-quick-ref.md`](references/xml/xml-schema-quick-ref.md)，篇幅较长，务必完整读完；图表按选定设计系统调用 SVG 图表库，用户明确要求原生图表或需编辑已有原生 `<chart>` 时，必须先用 `python3 scripts/slides_chart_tool.py get <id-or-keyword>` 获取对应 XML 片段，再照抄工具输出；用 svg 专业图表前跑 `python3 -c "from scripts.gen_svg_charts import chart_help; print(chart_help())"` 一次拿到完整的调用范式总览，**不要接 `| head` / `| tail` 截断，末尾的全部入口索引也要看到**（也可 `chart_help('sankey')` 拿单张详情）；需要使用到树状图时先跑 `python3 -c "from scripts.gen_svg_relations import relation_help; print(relation_help())"`（也可 `relation_help('<slug>')` 拿单张详情），支持范围以当前 manifest 为准；正式 Slides 必须用 `make_relation_atomized(..., strict_no_embed=True)` 或 CLI `--atomized` 输出多个独立元素，不得用 `<embed>` 作树状图主体；**手写 SVG 前必读 [`xml/svg-writing-guide.md`](references/xml/svg-writing-guide.md)** 了解规则；用图标先用 `python3 scripts/iconpark_tool.py search --query "<关键词>"` 检索（见 [`xml/iconpark.md`](references/xml/iconpark.md)）；选择、修改字体必读 [`xml/fonts.md`](references/xml/fonts.md)，不要凭记忆填写 `fontFamily`。
2. **建空白幻灯片（两步创建·第一步）**：先 `slides +create --title <幻灯片标题>`（不带 `--slides`）建一份空白幻灯片（见 [`cli/lark-slides-create.md`](references/cli/lark-slides-create.md)），**必须从工具返回结果中拿到并记下 `xml_presentation_id` 和 `url`**。Step 6 上传图片、Step 7 写入、Step 8 回读要用 `xml_presentation_id`，Step 5 通知、Step 8 交付要用幻灯片链接 `url`，缺失时先检查完整响应，并用已有 ID／链接只读确认创建状态，按 [`error-handling.md`](references/workflow/error-handling.md) 恢复；仅确认未创建成功后才重试创建，状态不明不得直接重建。
3. **开工通知**：用 present_files 工具把上一步拿到的 `url` 发给用户，并在回复里附上简短说明。这个链接和 Step 8 交付用的是同一个地址，但两次都必须发，不能省掉任何一次：这里是开工通知，Step 8 才是成稿交付。

present_files 提交的链接会变成一张可点击的产物卡片，你需要直接回复向用户说明**PPT 已经开始制作，可以点击卡片，关注进度**，为了确保用户看到，**开工通知务必放在思考过程之外，以用户可见的回复正文输出**（思考过程内容在展示时会被折叠）。这个能边做边看进度的体验非常棒，所以通知环节非常关键，一定要让用户感受到。

### Step 6 · 图片处理

本次要用的图片统一在这一步落地成 `file_token`：**取到本地 → 图片去底色 → 上传**。图片裁剪在 Step 7 中用 `<img>` 的 `<crop>` 实现，不需要在本步处理。

1. **取到本地**：禁止 http(s) 外链，飞书 slides 渲染端不会代理外链图，外链 `src` 在幻灯片里通常不显示；网图必须先 `curl -L` 下载到 CWD 内，生图/搜图工具的产物同样先落成 CWD 内的文件。从已有 Slides 复用图片时，从实时回读 XML 的 `<img src>` 获取 `file_token`，再用 `lark-cli api GET "/open-apis/drive/v1/medias/<file_token>/download" --output "<file>"` 下载到本地。
2. **图片去底色**：带底色的图片盖在有色背景上会让整页设计垮掉。对 Step 3 收集到的图片素材，调用去底色工具前完运行 `mediakit-cli image remove-image-background --help` 与 `mediakit-cli image remove-image-background --schema` 获取命令的输入输出说明，注意该命令里的boolean 参数--need-crop-background 必须写成 --need-crop-background=true / --need-crop-background=false，--image-url 参数可以接受搜索到的图片URL，直接使用即可；未完成上述读取和检查前禁止直接调用，logo徽标、动漫卡通图片使用 `--scene=general`，人像、真人、实物使用 `--scene=product`。**黑白灰底色的图片必须抠**，渐变底和复杂背景直接跳过不要硬抠；命令成功后立即下载返回的 `image_url`，另存为新的 PNG（不覆盖原图、不可存 JPG）；无需去底色、跳过处理或抠图效果差时，使用原图作为最终素材；**抠完逐张检查，确认背景透明、主体边缘无残留色块、主体内部无误抠，如果抠后效果差回退使用原图**。
3. **上传拿 `file_token`**：把本次要用的图片逐个 `+media-upload --file <图片路径> --presentation <id>` 上传，**拿到各自的 `file_token`**（见 [`cli/lark-slides-media-upload.md`](references/cli/lark-slides-media-upload.md)）。


### Step 7 · 逐页完成

**按页闭环：落 XML → 开启 lint 提交 → 完整读取响应 → 有问题则修复并开启 lint 重提**。通过或完成单页例外核验后再做下一页，不要攒完整份再统一写入，禁止批量创建。

默认追加时，页序由成功写入的先后决定，与文件名编号无关。当前页既未通过 lint 也未完成例外核验，或写入未确认时，不得跳过它继续追加后续页，否则稍后补写会落到末尾。

1. **落 XML**：核心结论定标题，选定的设计系统定版式与配色。带图页把 Step 6 拿到的 `file_token` 写进 `<img src>`。不用写 `<?xml ...?>` 声明，也不用包 `<presentation>`，只提交单个 `<slide>` 元素。元素上不要自己编 `id`，留空即可（ID 由服务端分配，自造 ID 容易撞车）。文本和属性值里的 `&`、`<`、`>` 必须转义为 `&amp;` / `&lt;` / `&gt;`。**全篇禁止使用 emoji（任何位置都不能出现）**，语义图标一律用检索到的 IconPark `<icon>`。
2. **图片使用**：**图片可以裁剪或缩放大小来适配 PPT 的排版布局，不要溢出画布**；**附件中提取的图片/表格不允许做裁剪**，但可以缩放大小来适配你选择的 PPT 的排版布局；`<img>` 的 `width:height` 对齐原图比例就不会裁剪，只会缩放大小；对不上会自动裁剪，且默认从中心裁掉多余部分，可用 `<crop>` 的 `anchor` 指定保留哪一侧。**同一张图片不要在多页重复使用**，补充素材或重新排版，Logo、统一装饰除外。
3. **素材兜底**：主视觉优先用真实素材，绝不留空白图框。缺图先用搜图工具或生图工具补这一页要用的图；补不到或不可用时，用生图工具生成替代的近似图或抽象图。仍不可用时，按内容类型兜底：数据图从 SVG 图表库选择，结构示意用手写 SVG 或 `<shape>`+`<line>` 等可编辑元素。数据类可视化缺真实数据时不要编造数字，确需图表占位时仍按数据含义选 SVG 入口，并标注「模拟数据，仅占位，待替换真实数据」。
4. **演讲者备注**：需要在每页 `<slide>` 的 `<note>` 中提供 3–5 句可直接照读的讲稿。
5. **写入幻灯片（两步创建·第二步）**：每页用 `slides +add-slide` 写入（见 [`cli/lark-slides-add-slide.md`](references/cli/lark-slides-add-slide.md) 与本步末尾的示例）。**页面里有 SVG 数据图或示意图（`chart_slide` / `d.to_slide` 的片段）时改用 `publish_slide`**，写法见 svg-writing-guide.md「合页与写入：publish_slide」一节：它负责合页、豁免图形转换误报并返回带坐标的改法；这类页不要自己拼 `<embed>` 塞 SVG，也不要把片段手动拼进 XML 再调 `+add-slide`。**某页被拦需要修改时，用同一页的修正版重新提交（不要先写后面的页）**；已写错位置时插到正确位置再删旧页。**默认追加到整份幻灯片的末尾；要插入到某页之前，必须传 `--before-slide-id <目标页的slide_id>`。** **记下返回的 `slide_id`**：它是这一页的唯一关联键，Step 8 截图和修复都按它定位。写入命令见本步末尾的示例。
6. **处理校验结果**：返回 JSON 的外层 `ok` 表示调用是否成功；成功时 ID、版本及问题发现位于 `data`，失败时错误码与报告位于 `error`。成功且无问题发现时记录 ID/版本并继续；有问题时按下表处理。报告结构、长报告读取和例外条件见 [`validation-xml.md`](references/workflow/validation-xml.md)。

   | 响应 | 含义 | 处理 |
   |---|---|---|
   | 开启 lint，成功且无 `data.issues` | 这一页通过校验并已落库 | 继续下一页，最终仍须回读与视觉验收 |
   | 成功，带 `data.issues` | 已落库，但仍有问题发现或内容被服务端丢弃 | 对象/数组直接读，JSON 字符串解码后读，普通文本完整读；多页创建还要读 `data.slide_issues`。立即回读并截图；真实问题修复后开启 lint 重提，逐项核对无碍才继续 |
   | `ok: false`，`error.code: 4000153` | 校验拒绝，这一页**没有**写入 | 将 `error.message` 这个 JSON 字符串二次解析，**读完 `document` 和 `slides[]` 中各级问题正文**，`issues` 可能是镜像；不能只看 summary 或前几百字符，缺少 `data.issues` 不等于零问题；按 `message` / `hint` 修复后开启 lint 重提，新暴露的问题也必须继续处理 |
   | 当前页首次写入直接使用 `--no-lint`，仍被服务端 lint 阻断 | 首次提交保护生效，不能据此判断参数不支持 | 完整读取检测报告，按问题修复并恢复默认开启 lint 的提交方式；被拦一次不代表下一次可自动跳过，例外仍按 [`validation-xml.md`](references/workflow/validation-xml.md) 判断 |
   | 使用 `--no-lint` 后成功 | 仅说明已写入，**不代表通过校验** | 立即回读并实际查看本页截图，逐项完成例外核验后才继续；截图失败不能按完成处理 |

   **修复时保留正文、数值、单位、标签和图例，不能为消除 lint 批量删除内容。本次新增或加重的真实问题必须修复，不能以“原稿布局”或“稍后截图”为由绕过。** 有意设计被误判、且必须原样保留时，也须先读完当前页当前 XML 的报告并核实依据，才能单独豁免这一次提交。禁止把 `--no-lint` 写入多页循环、公共参数或失败后自动重试；下一页以及同页再次修改后都恢复 lint。
7. **写入确认与失败排障**：写入后检查完整 CLI 响应，只有 `.ok == true` 且 `.data.slide_id` 非空，才能标记该页已写入，并记下页码与 ID 的对应关系。Shell 退出码为 0 不代表业务成功。遇到解析失败、ID 缺失、`invalid param`、创建失败、空白页或 3350001 等异常时，按 [`workflow/error-handling.md`](references/workflow/error-handling.md) 查看原始响应并回读确认实际状态，再决定修复或补写，不得假定成功或直接重试。补到非末尾位置前，先核实非空的插入锚点 ID，定位失败不得退化为末尾追加。

**写入命令（关键）**：把每页 XML 存成文件，用 `--slide @<文件>` 传入（必须是当前工作目录内的相对路径，不接受绝对路径或 `../`），不要把 XML 内联进命令行（中文/引号/特殊字符易被 shell 转义或截断）。例：

```bash
cd "<本页XML所在目录>" &&
lark-cli slides +add-slide \
  --presentation "<xml_presentation_id>" \
  --slide @slide-01.xml
```
如需插入到某页之前，在上述命令中增加 --before-slide-id "<已核实的目标页ID>"；追加和插入二选一，不要重复执行。

### Step 8 · 验收与交付

核对实际页数、页面顺序、关键元素，完整校验清单见 [`workflow/validation-xml.md`](references/workflow/validation-xml.md)。

1. **回读全文及默认 lint 报告**：`slides +xml-get --presentation <xml_presentation_id> --output <CWD 内相对路径> --json`，必须使用 `--output` 保存纯 XML，并另存 stdout 完整响应与 stderr；版本和 `data.issues` 报告在响应 JSON 中，不在 XML 文件内。报告读取规则见 [`validation-xml.md`](references/workflow/validation-xml.md)。
2. **解析回读结果**：先用 `lint_inspect.py --input <完整响应 JSON>` 获取 lint 检测报告摘要，再按页和文档级范围用 `--details --limit 3 --max-chars 6000` 读问题正文（`issues[].issue`），按 `pagination.next_offset` 继续到 `has_more: false`，处理全部发现；不要把大报告整段打印或只读 lint 检测报告摘要；报告缺失不能视为通过。编辑/模板须读取目标页原稿详情并与同一实际页面比较：整稿第 4 页在单页报告中可能编号为 1，以请求/响应 slide ID 和同次 XML 页序关联，不能只比总数或同名 code。再用 `xml_inspect.py --input <纯 XML 文件> --mode summary` 输出 XML 内容与结构摘要，按实际顺序核对 `index、slide_id、text_preview` 与大纲及创建记录是否对应；该 XML 内容与结构摘要不包含服务端 lint。补页后重新核对，页数相同、写入成功或 lint 通过不能代替页序验收。自行解析时必须使用 XML 解析器，命名空间从根元素实际读取，不要硬编码或猜测。服务端会规整你提交的 XML（丢弃不认识的属性、补默认值），落地结果和你写的可能不是一回事，一律以回读到的为准。
3. **逐页截图复核**：`slides +screenshot --presentation <xml_presentation_id> --slide-id <slide_id> --output-dir <CWD 内相对路径>` 看真实渲染（见 [`workflow/validation-visual.md`](references/workflow/validation-visual.md)）；`slide_id` 取自第 1 步的回读结果或 Step 7 的创建响应，多页重复传 `--slide-id`、一次最多 8 页。只有确实拿不到 `slide_id` 时才用 `--slide-number <页号>` 回退定位，定位后立刻换回 `slide_id`。
4. **问题修复**：局部问题用 `+replace-slide`（见 [`cli/lark-slides-replace-slide.md`](references/cli/lark-slides-replace-slide.md)）做块级替换；整页要重做用 `+update-slide` 原地覆盖（见 [`cli/lark-slides-update-slide.md`](references/cli/lark-slides-update-slide.md)，多页就每页各跑一次），或 `+delete-slide` 删旧页（见 [`cli/lark-slides-delete-slide.md`](references/cli/lark-slides-delete-slide.md)）+ `+add-slide` 建新页。改完重新回读、重新校验。
5. **成稿交付**：用 present_files 工具把最终幻灯片链接明确交付给用户，并在回复里附上制作介绍；编辑已有幻灯片同样必须交付链接。交付链接**用 `+create` 返回的 `url` 字段**（Step 5 已记下）。SystemPrompt 里若出现 `Computer OS: Windows` 或 `Computer OS: Mac`，并且如果产物是在线幻灯片（非有本地路径和token的本地文件），使用 `lark-cli drive +export --token "lark slides的file_token" --doc-type slides --file-extension pptx --output-dir "导出路径(使用CWD内相对路径)" ` 先把 ppt 导出来，然后将导出的文件用本地路径调用 `present_files` 给到用户；在线的幻灯片也需要调用 `present_files` 给到用户
6. 不要使用 `artifact-preview` 或 `verifier-hub` 验证最终 PPT 产物，统一按上述步骤执行。

## 三、参考文档地图


### `style/`


| 文档  | 何时读|
| --- | ---|
| [`slide-taxonomy.md`](references/style/slide-taxonomy.md)  | **选定设计系统的入口**：先读本文件，根据场景路由再读取具体设计系统或 fallback。不要跳过本文件直接选择场景文档。|



### `xml/`


| 文档                                                                                    | 何时读                  |
| ------------------------------------------------------------------------------------- | -------------------- |
| [`xml-schema-quick-ref.md`](references/xml/xml-schema-quick-ref.md)                   | 生成任何 XML 前必读，元素与属性速查 |
| [`slides_chart_tool.py`](scripts/slides_chart_tool.py)                               | 画原生 `<chart>` 前按类型获取 XML 片段并照抄工具输出；禁止直接通读 demo |
| [`slides_xml_schema_definition.xml`](references/xml/slides_xml_schema_definition.xml) | 唯一权威 XML 协议，需要精确定义时查 |
| [`iconpark.md`](references/xml/iconpark.md)                                           | IconPark 图标检索与用法     |
| [`iconpark-index.json`](references/xml/iconpark-index.json)                             | 图标离线索引，供脚本检索，不用手读    |
| [`svg-writing-guide.md`](references/xml/svg-writing-guide.md)                         | 图表库调用 + 手写 SVG 示意图（drawing 库、转换边界、atomize 与合页） |




### `cli/`


| 文档                                                                                            | 何时读                                |
| --------------------------------------------------------------------------------------------- | ---------------------------------- |
| [`lark-slides-create.md`](references/cli/lark-slides-create.md)                               | `+create` 创建幻灯片（两步创建第一步：建空白幻灯片）    |
| [`lark-slides-add-slide.md`](references/cli/lark-slides-add-slide.md)                         | `+add-slide` 逐页追加/插入单页（两步创建第二步）    |
| [`lark-slides-xml-presentations-get.md`](references/cli/lark-slides-xml-presentations-get.md) | `+xml-get` 回读全文 XML                |
| [`lark-slides-replace-slide.md`](references/cli/lark-slides-replace-slide.md)                 | `+replace-slide` 块级替换/插入           |
| [`lark-slides-update-slide.md`](references/cli/lark-slides-update-slide.md)                   | `+update-slide` 整页原地覆盖（多页每页一次）      |
| [`lark-slides-delete-slide.md`](references/cli/lark-slides-delete-slide.md)                   | `+delete-slide` 按 `slide_id` 删除单页  |
| [`lark-slides-media-upload.md`](references/cli/lark-slides-media-upload.md)                   | `+media-upload` 上传图片拿 `file_token` |
| [`lark-slides-screenshot.md`](references/cli/lark-slides-screenshot.md)                       | `+screenshot` 截图                   |
| [`lark-slides-history.md`](references/cli/lark-slides-history.md)                             | `+history-list` / `+history-revert` / `+history-revert-status` 查看与回滚历史版本 |
| `lark-slides-xml-presentation-slide-get.md` / `-replace.md`                                   | 单页原生 API（无 shortcut 覆盖时用）          |




### `workflow/`


| 文档                                                                 | 何时读                                                               |
| ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| [`slides-editing.md`](references/workflow/slides-editing.md)       | 在原稿上改的完整流程：理解现状（归一到在线 Slides / 读附件 / 回读 deck）→ 定位改哪里 → 按需备素材 → 改 → 回读校验 |
| [`template-editing-main.md`](references/workflow/template-editing-main.md) | 拿模板做一份新 deck（PPTX/飞书 Slides）· **MainAgent 视角** 7 Steps：离线解析模板 → 制定 page-plan → 建空白 deck + 派 Organizer 并行 → MainAgent 流式生成 → 收尾通知 + 初稿交付 → 兜底修复 + 二次交付；含派 Organizer 的 subtask 模板 |
| [`template-editing-organizer.md`](references/workflow/template-editing-organizer.md) | **Organizer 视角** 5 Steps：冷启动 Read → poll 感知新页 → 抽单页 XML → 审查+修复（fixed_template 只修 bug · active_rebuild 既修 bug 也 refine 拔高） → 出口。**MainAgent 不需要 Read**，只在派 Organizer 时把它作为 Organizer 的 workflow 文档 |
| [`error-handling.md`](references/workflow/error-handling.md)       | XML 语法/接口/错误码排障与失败处理（视觉与版面问题见 validation-visual）                  |
| [`validation-xml.md`](references/workflow/validation-xml.md)       | 写入/回读报告解析、原稿 lint 基线与前后对比、修复与单页例外规则；回读核对清单（Step 7/8 必做） |
| [`validation-visual.md`](references/workflow/validation-visual.md) | 截图视觉校验                                                 |
| [`windows-compat.md`](references/workflow/windows-compat.md) | windows 本地电脑操作报错兼容说明                                                 |
| [`local-compat.md`](references/workflow/local-compat.md) | windows/mac 本地电脑模式操作背景说明                                                 |



### `scripts/`

| 脚本                                             | 用途                                                                            |
| ---------------------------------------------- | ----------------------------------------------------------------------------- |
| [`xml_inspect.py`](scripts/xml_inspect.py)     | `--mode summary`（默认）输出摘要及其它模式用法提示；`--mode content` 输出不截断的页面文字/数据，不含演讲者备注；`--mode raw` 返回含完整 XML 的 JSON。summary 固定读全稿，不接受 `--slide-id`；content/raw 可加 `--slide-id ID...` 选页，不传则读全稿。精确编辑、模板继承必须读 raw XML |
| [`lint_inspect.py`](scripts/lint_inspect.py) | 读取回读或写入响应中的 lint 报告：默认输出 lint 检测报告摘要，`--details` 分页读取，支持页码、级别、错误码及文档级筛选；自动解析 4000153 的 JSON 字符串，规则见 validation-xml.md |
| [`iconpark_tool.py`](scripts/iconpark_tool.py) | IconPark 图标检索，最小用法 `python3 scripts/iconpark_tool.py search --query "<关键词>"`（再按需 `resolve`）             |
| [`gen_svg_charts.py`](scripts/gen_svg_charts.py) | SVG 图表生成：先写下每页数据图要回答的研究问题，按 `chart_help()` 的学科表选专业入口（文献已报告的汇总值即可作图）；类别柱状只用于没有更贴切问题的单值概览。`chart_slide(slug, x=, y=, width=, height=, **kwargs)` 返回半可编辑页面片段（`make_<slug>` 只返回 SVG）。**主入口**：`python3 -c "from scripts.gen_svg_charts import chart_help; print(chart_help())"` 获取数据条件与名称短索引；`chart_help('<slug>')` 按需获取签名、示例、变体和组合条件 |
| [`svg_lib/svg_drawing.py`](scripts/svg_lib/svg_drawing.py) | 手写示意图的几何与排布助手：轮廓端口、连线避障、行/列/网格/环形排布、两列配对、端口分配、按文字定尺寸的节点框与自动标签。**主入口**：`python3 -c "from scripts.svg_lib.svg_drawing import drawing_help; print(drawing_help())"`，用法见 svg-writing-guide.md 第四节 |
| [`gen_svg_relations.py`](scripts/gen_svg_relations.py) | SVG 树状图生成：支持范围以当前 manifest 为准，运行 `relation_help()` / `relation_help('<slug>')` 或 CLI `--list` 查看。正式 Slides 必须用 `make_relation_atomized(..., strict_no_embed=True)` 或 CLI `--atomized` 输出拆分的独立元素；**主入口**：`python3 -c "from scripts.gen_svg_relations import relation_help; print(relation_help())"` |
| [`color_contrast_check.py`](scripts/color_contrast_check.py) | 独立的 XML 靠色回归入口；图片背景跳过。用法：`python3 scripts/color_contrast_check.py --xml <回读 XML>`。 |
| [`safe_update_slide.py`](scripts/safe_update_slide.py) | 目标页级 CAS 保护的 `+update-slide` 包装：语义级 diff（元素签名：元素数/id 集合/几何/文本前 60 字），一致才允许写入，不一致 abort 并把服务端最新版覆盖本地。**仅 Organizer 流式检查+refine 模式使用**（见 template-editing-organizer.md）；MainAgent 主流程走裸 `+update-slide` 即可 |
| [`parse_template.py`](scripts/parse_template.py) | template-editing 分支 Step 1 用：离线解析 PPTX 产出 `template-manifest.json`（每页 role / 壳层 shape / 可用区 bbox / 占位文本清单 / 缩略图路径）+ `theme.json`（配色 + 字体）+ 抽全部图片到 `assets/` + 渲染每页缩略图到 `thumbs/`。用法：`python3 scripts/parse_template.py --pptx <path> --work-dir <WORK_DIR>` |



### `svg`

数据图（`chart_slide`）、树状图（`make_relation_atomized`）、手画示意图（drawing 库）以及任何手写 SVG，动手前读 [`xml/svg-writing-guide.md`](references/xml/svg-writing-guide.md)；图表目录以 `chart_help()` 为准，树状图以 `relation_help()` 为准。维护图表生成代码时，不得修改 `scripts/embed_svg_validator.py` 和 `scripts/embed_svg_validator_test.py`。



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
| [`+update-slide`](references/cli/lark-slides-update-slide.md)     | 整页原地覆盖，`slide_id` 和页序不变；没写进 `--content` 的元素会被删除          |
| [`+screenshot`](references/cli/lark-slides-screenshot.md)         | 页面截图                                                             |


没有 shortcut 覆盖时用原生 API；调用前必须先看参数结构：

```bash
lark-cli schema slides.<resource>.<method>   # 调 API 前必先看参数结构
lark-cli slides <resource> <method> [flags]  # 调 API
```
