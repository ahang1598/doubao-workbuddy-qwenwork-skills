---
name: ppt
version: 1.0.89
description: 飞书幻灯片：创建和编辑幻灯片。创建演示文稿、读取幻灯片内容、管理幻灯片页面（创建、删除、读取、局部替换）。当用户需要创建或编辑幻灯片、读取或修改单个页面时使用。
metadata:
  requires:
    bins: ["lark-cli"]
  cliHelp: "lark-cli slides --help"
---

# 飞书幻灯片

本文是总入口和流程主线。按场景路由进入对应分支（新建 / 编辑），逐步执行并在每一步读取该步指向的 `references/` 文档。文档按职责分四类：`style/`（怎么设计）、`cli/`（怎么操作命令）、`xml/`（具体定义）、`workflow/`（流程：排障 / 模板改写 / 编辑）。

## 权威经验

1. **页面写入默认请求跳过 lint**：`+add-slide`、`+update-slide`、`+replace-slide` 均传 `--no-lint`；含图页的 `publish_slide()` 也采用此默认。成功后记录页面 ID 并继续。默认制作与交付不主动执行 lint、布局或视觉自检、成稿预览、截图复检和写后内容验收，也不分页阅读报告、建立 lint 基线或进入清零修复循环。独立检查与审查工具仅在用户明确要求检查时调用。服务端仍可能拒绝写入，失败处理见 [`error-handling.md`](references/workflow/error-handling.md)。
2. **开工通知和成稿交付都必须调用 present_files 工具**。
3. **按当前场景、需求和步骤选中的必读文档必须完整读完，尾部有重要信息，不要中途截断**。Read 工具单次返回有 token 上限，`limit` 单位为行数；大文件需用 `offset` + `limit` 分段续读，直到返回 `[End of file.]` 为止。
4. 牢记幻灯片 URL 和关键 ID（`xml_presentation_id`、`slide_id`、`revision_id`、`file_token`、`block_id`、`obj_token`）。
5. 牢记每一页幻灯片的真实完成状态，区分「已落本地 XML 文件」「已写入幻灯片」；以写入响应的 `ok` 和页面 ID 确认落库，不把请求跳过 lint 描述成通过校验。编辑任务保留原稿 XML 和内容快照，后续读取另存。素材同理，区分「已取到本地」「已去底色（或确认无需抠 / 已回退原图）」「已上传拿到 `file_token`」。
6. 牢记选定的设计系统，全程落实下文[通用设计要求](#通用设计要求)；场景 style 对字号等有更高要求时，按更高要求执行。
7. **本地电脑模式背景补充**：运行环境只看最后一个含 `Main project directory` 的 `<system-reminder>`（忽略更早 SR）：`Computer OS` 为 `Windows` / `macOS` 判为本地电脑；无 `Computer OS` 时，`Main project directory` 为 `/home/user/Doubao/...` 判为云电脑，`/Users/...`、`C:\...` 等判为本地电脑。判为本地电脑时，**在阅读完本 SKILL后，必须完整 Read [`workflow/local-compat.md`](references/workflow/local-compat.md)，查看在本地电脑模式下执行命令所需要知道的背景，否则会出现大面积报错**。
8. **Windows 平台差异**：按「本地电脑模式背景补充」中的规则判定当前环境为 Windows 时，**在阅读完 local-compat.md 后，必须完整 Read [`workflow/windows-compat.md`](references/workflow/windows-compat.md)，查看在 windows 平台上执行命令所必须要注意的问题，否则会出现大面积报错**。
9. 跨轮编辑后的交付（强制）：只要本轮对用户可见的幻灯片发生了实际写入或更新，写入成功后必须在本轮再次调用 present_files 交付最新版本。即使该幻灯片链接已在前序轮次交付、URL 没有变化，也不得复用前轮产物卡片或只提示用户刷新。
10. **Organizer 仅用于用户明确要求的审查或优化任务**：默认新建、编辑和模板制作在写入成功后直接交付。
11. **模板专属规则**：模板任务的解析、读取频次、逐页制作、发布和复核，按 [workflow.md](references/template/workflow.md) 执行。
12. **除了 chart 库生成的 svg 以外的 svg 图必须走 atomize**：手画的概念图/示意图/流程图/装饰图必须读 svg-writing-guide.md，用 drawing 库（`scripts/svg_lib/svg_drawing.py`，常用接口已列在指南第四节）画图，`to_slide` 输出可编辑原生元素。chart 库（`gen_svg_charts.py`）的数据图用 `chart_slide(...)` 放入页面，得到半可编辑结果（文字原生、同色色块可整体换色）。这两类结果直接按页用 `publish_slide()` 写入（默认请求跳过 lint）；图形按设计要求生成后直接转换并写入，默认不调用 `d.check()`、`d.review()` 或 `d.preview()`；按数值画长短的条形/点（如 ORR、比例对比）也属于数据图，必须走 `chart_slide`，不能用 rect 拼
13. **【非常重要】MUST RELOAD SKILL：对于 PPT 的任务而言，无论之前是否读过 SKILL.md 文档，当用户提出了新的指令时，你的第一个工具调用必须是重新 Read ppt skill 下的 SKILL.md 文档，在此之前禁止使用任何其他工具或执行 xml 相关指令；若用户新上传了附件需要下载或解析，解析完附件后也必须立即重新 Read ppt 下的 SKILL.md 再继续，不得跳过。**
14. 不要使用 `artifact-preview` 或 `verifier-hub` 验证最终 PPT 产物，做完交付即可，速度优先。

### 事实依据与内部引用

新建、模板制作和编辑时，对本轮新增或改写的事实，先选依据、定说法，再写正文和讲稿并记录引用；不要先写结论再凑出处。**事实也包括经历、能力、成熟度、效率和因果判断，宣传或内部复盘同样需要依据。**

1. **保留材料性质与限定**：用户明确提供的事实优先；写作要求不能证明实际经历、能力或成果。示例、计划、备选和待确认项保留原属性；“可选”仅指是否展示时，不降低已确认事实。缺信息可待补，继续完成有依据的部分。不能从同主题资料或图片推定本次实际到场、采访、采集或实施，也不能用系统日期、文件时间代填业务日期。
2. **依据能支持多强，就写多强**：`direct` 直接转述已读材料；`calculated` 给出原数、单位、口径和公式；`inferred` 必须有已知事实前提和可复核的推导，不能借“推断／内部判断”补出材料没有的具体经历、业绩或能力。前提不足就改为待核实的问题、建议或明确的假设，不把假设写成既成事实。缺少足以支撑的事实依据和推导时，只能作为待核实的条件或假设，未确认的选项不能全部写成已发生，对象、时间、状态、单位与口径在每处复述中保持一致。
3. **详细依据集中保存**：每份演示在作者稿工作目录只维护一份 `references.json`。`references` 数组每条对应一个具体事实，字段为：`id`（从1开始的整数）、`fact`（事实及限定）、`sources`（数组，每项含真实文件名/URL/用户消息 `source`、页码/单元格/段落 `locator`、已读原文/原数 `evidence`）、`kind`（`direct` / `calculated` / `inferred` / `example`）、`status`（材料中的确认、计划、预测等状态）。计算和推断另写 `derivation`，内容见上条。摘录保留标题、前句、脚注中的必要限定。自拟示例用 `kind: "example"`、`sources: []`，明确标为示例；缺依据放入同文件的 `gaps`，不作为事实引用。纯结构、装饰和无具体断言的待补占位免记。
4. **使用处只标编号**：作者 XML 在对应文字元素前紧邻写 `<!-- citation: [1] -->`，多项事实写 `<!-- citation: [1][2] -->`。标题、正文、图注和讲稿逐项绑定，讲稿放在对应 `<p>` 前，不能只列整页编号。不同事实分开记录，同一事实跨页、正文与讲稿复用同一编号；多个来源放在该事实的 `sources`。新增事实追加编号，已有编号不重排、不转给其他事实。
5. **同步修改并保留作者稿**：每处实际句子仍须由原文支持，`fact` 摘要不能代替证据。改删内容同步改编号，更正依据时核对所有使用处。编辑旧稿保留原稿，将本轮涉及的旧完整引用转存到集中记录并换成编号，不补造来源；仅改样式保留原引用。含注释的作者 XML 与 `references.json` 一起保留，服务端回读另存；解析、发布或导出可能丢注释，不据此重复写入或声称最终 PPT 携带引用。编号只在 XML 注释中，不新增元素、属性或可见角标；默认不增加页脚、来源备注，用户要求或原稿已有出处除外，此条优先于风格指南的来源位置建议。

完整字段与正文、讲稿编号复用见 [XML 完整示例](references/xml/xml-schema-quick-ref.md#完整示例)，实际任务替换为真实已读材料。

## 通用设计要求

- **字号不得小于 14 pt**：所有页面文字，包括正文、表格、图表标签、脚注和来源，完成排版与缩放后的实际字号必须 **≥ 14 pt**。教育与科普场景按对应 [style](references/style/learning-and-training.md) 使用更大字号，**最低 18 pt**；14 pt 仅是通用底线，不是推荐正文大小。先定字号再排版，放不下就精简重复内容、调整布局或拆页，不靠缩字塞内容，也不沿用低于底线的模板或组件默认值。
- **正文聚焦，标题与脚注简洁**：正文只放需要读者关注、理解或据此作判断的必要信息，以正常正文层级呈现，不夹带无意义小字注释、旁白式补充或制作说明。避免在标题下添加灰色小字注释或解释性副标题。补充背景、详细口径与延伸说明放入备注或参考资料页；理解结论不可缺少的条件应直接写进主要表述。脚注仅保留必要的来源或简短口径，干净清晰、不超过一行，不靠缩字或降低对比度塞进页脚。
- **装饰必须服务表达**：气泡、圆不得作为页面装饰；只有确需呈现对话内容时才使用。删除无助于理解内容、组织信息或引导视线的图形、线条和色块，不为填空或凑视觉效果添加装饰。
- **一页一个核心观点，信息之间有逻辑**：每页围绕一个明确的观点、问题或任务组织材料，标题、证据、图表与说明共同支持这一重点。通过分组、对照、顺序和必要形状连线呈现比较、因果、递进或流程等真实关系，避免把互不相连的要点平铺成清单或卡片。
- **图文并茂与页型变化**：高质量幻灯片应兼顾信息表达与阅读体验。根据内容选用高质量图片、截图、图表、流程图或结构示意图，让视觉素材帮助解释观点、展示证据，避免通篇堆文字或仅用图标装饰。**生活类、面向消费者或公众的演示通常需要图片参与表达**：用贴合主题的人物、实物、场景照片或插画辅助理解、烘托气氛、吸引注意，并围绕图片组织图文，而非写完文字后随意配一张小图。仅有图标、色块或文字卡片不能替代这些场景所需的图片。不必为凑图片数量或满足“每页有图”而强行塞入无关图片；整套演示应有适当的页型变化，如大图页、图文分栏页、数据页、对比页、流程页和案例页；变化应体现在构图与信息层级，不能只改变卡片颜色、数量或位置，也不为凑页型强行变换布局。卡片按需使用，**不要全稿只用卡片布局**，不把每段文字、每组信息都装进框里，不要依靠卡片堆叠或嵌套来组织层级；应根据内容关系选择合适的排版方式，通过排版展示信息逻辑而不是罗列。保持字体、配色与视觉风格统一，避免连续多页机械套用同一布局。
- **充分铺展，合理利用版面**：在统一边距内展开主图、文字和图表，按信息主次分配空间，避免内容缩在一角、挤成窄条或留下大块无意义空白。用对齐与疏密建立秩序，留白服务阅读和分组；不为铺满页面增加冗余内容或装饰。
- **默认禁用的设计**：除非用户明确要求，禁止使用 AI pattern 的渐变背景、彩虹配色、背景跳色、竖条卡片和阴影效果，不为制造层次、节奏或“设计感”自行添加；style 中的可选风格与组件默认效果也不能覆盖此要求。
- **整稿色系统一，工作场景优先纯白底**：从封面、正文到结尾沿用统一的底色体系、主色和强调色。工作汇报、经营分析等场景默认使用纯白底；不要惯性地将封面或结尾做成深色页，也不要在中间插入无意义的跳色或深色页。页面节奏主要通过构图、信息层级和素材变化形成；只有用户明确要求时才调整背景色，并保持与整稿色系协调。

## 一、场景路由

先判断任务类型，再进入对应分支。无论改动是大是小、命令是否熟悉，无论此前是否用过类似命令、做过类似任务，无论之前是否读过对应分支的 MD 文档，**必须重新 Read 对应分支的 MD 文档之后才能动手**。**特别是多轮对话中用户对前轮已有 PPT 的任何修改/扩写/压缩精简/组合合并/重新排版/调整风格等，都属于"编辑已有幻灯片"场景，本次动手前必须先完整 Read references/workflow/slides-editing.md，不得凭上一轮记忆直接改 XML。**

| 任务                                                            | 对应分支（必读）                                                                                          |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **新建幻灯片**（从零、附件作事实材料，或把图片/PDF 同内容 1:1 复刻）                     | [`SKILL.md`](SKILL.md) 中「二、新建幻灯片」Step 1 → Step 8                                                  |
| **编辑已有幻灯片**（修改已有的 PPTX 或 Slides，或多轮对话里改前轮产物）                  | [`workflow/slides-editing.md`](references/workflow/slides-editing.md)                             |
| **提供视觉规范制作新内容**（PPTX/Slides 模板、空母版、VI、PDF/图片风格参考；含已有 PPT 换模板） | [`template/workflow.md`](references/template/workflow.md)                                         |
| **读取分析已有幻灯片**                                                 | [`cli/lark-slides-xml-presentations-get.md`](references/cli/lark-slides-xml-presentations-get.md) |

## 二、新建幻灯片

**核心顺序：理解需求 → 选定设计系统 → 收集素材 → 理大纲 → 准备工作 → 图片处理 → 逐页完成 → 交付。**

### Step 1 · 理解需求

先确定：**目的、受众、页数、风格倾向、输入类型**（仅主题 / 完整文档 / 逐页大纲讲稿）。

- **页数**：用户指定则以用户为准；给了逐页大纲/讲稿则对齐其页数；只给主题或给了结构化长文档时，自行按主题和内容量推测一个合理页数直接开始，并在回复里说明你定的页数与理由。
- **默认不打断，能推测就直接做**：需求不完全明确时，优先按合理默认推进，不要为小问题反复发问。只有确实无法推进的硬阻塞才停下来，直接回复向用户说明并提问即可，例如：附件/URL 打不开导致缺关键素材、意图自相矛盾（选了某设计系统又要一个完全冲突的风格 / 既要"做 10 页"又要"输出 30 页以上"）。

### Step 2 · 选定设计系统

设计系统决定整份 deck 的视觉，也决定了下一步要收集哪些素材。

- 先排除两类不走本步的任务：用户给的是**模板、空版式、VI 或新内容的视觉参考** → 走 [`template/workflow.md`](references/template/workflow.md)；**复刻任务（把图片/PDF 1:1 还原成幻灯片）** → 不做场景选择，改为分析原图：估算每个元素的位置、字号、配色、间距，尽量 1:1 复刻原稿的版式与视觉。

**优先遵循用户指定的教材、教案、模板、品牌规范与参考风格。按整份演示的主要沟通目的选择场景与设计指南**，以用户需求和附件内容为依据，不仅凭行业、单位身份、是否带 Logo 或是否包含数据判断。指南中的可选视觉风格按主题和受众选择。 各 style 中的字号、注释与脚注、背景和阴影规定若与[通用设计要求](#通用设计要求)冲突，以通用设计要求为准；不得以研究稿密度或组件默认值为由降低标准。

| 类别        | 主要目的与适用场景                                                                                                                     | 指南                                                  |
| --------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 商业分析与汇报 | 商务类默认档。包括工作与述职汇报、经营复盘、项目评审、董事会汇报、内部方案与商业提案，以及一般行业资讯、市场与竞品分析。以进展、业绩或执行安排为主体时使用；不因出现“研究”“分析”或所属金融行业而转入金融研究。 | [商业分析与汇报](references/style/business-deck.md) |
| 金融研究 | 仅用于金融研究和咨询报告：服务投资判断的宏观、行业、公司、信用、盈利预测与估值研究，以及围绕明确问题开展系统诊断、方案比较和证据论证的咨询报告。一般工作汇报不走本档。 | [金融研究](references/style/financial-research.md) |
| 品牌叙事与通用展示 | 以介绍、展示、分享、吸引兴趣或传达体验为主的通用档。包括品牌与企业形象、产品与服务介绍、发布推广、个人介绍与作品集、人物故事、生活方式、旅行美食、兴趣文化、活动与面向消费者或公众的主题分享。 | [品牌叙事与通用展示](references/style/brand-storytelling.md) |
| 教育与科普 | 以系统教会知识、方法或技能为主要任务，有明确学习目标，需要按学习者基础组织讲解与学习过程。包括课程、培训、实训、复习、自学及具有教学目标的科普。 | [教育与科普](references/style/learning-and-training.md) |
| 党建与党政     | 党政、党建及党史相关演示，包括党建工作汇报与述职、党课宣讲、党员教育、专题学习、主题党日、活动展示、经验交流、党史教学与展陈，以及党政工作部署、政策解读与研讨。适用于机关、各类企业、学校、社区、农村及社会组织等，不以讲述人的公务员身份或单位性质限制。 | [党建与党政](references/style/government-and-party.md)   |

**金融阅读型路由例外**：选择 `financial-research.md` 时完整读取并持续执行其“通用表达补充”；用户明确指定阅读型的经营、市场或竞品研究也可进入本路由。仅此路由的字体、字号按该文档的最终有效 px 执行（正文 14、主要结论 16、脚注／来源／页码 12，偶数整数），优先于通用 14pt 下限及“通用字号优先”。数据图保留原 Exhibit，其入口优先于通用 `chart_slide`／`chart_help`；有明确业务或数值含义的节点与图形允许使用，装饰禁令仍适用。其他场景与本 SKILL 的创建、编辑、模板、发布和交付流程不变。

**品牌与教育的边界看主要任务**：让观众了解对象、感受特点、产生兴趣或作出选择，优先用品牌叙事与通用展示；让学习者系统学会并能理解、判断或操作，才用教育与科普。例如产品介绍、生活经验分享走品牌，产品操作培训、系统教学课程走教育。没有明确教学任务时，不套用课程、练习和问答分离结构。

未明确属于商务汇报、金融研究、教育或党政等专门场景的任务，优先以品牌叙事与通用展示兜底，按主题与受众调整，不强行包装成商业品牌故事。所有 PPT 仍遵守通用设计要求。

### Step 3 · 收集素材

按选定的设计系统决定素材需求，本步负责**确定要哪些素材、并把它们找齐**（联网搜索、搜图、生图都在这里做完）。

-**读取材料时记依据，定大纲前保存 `references.json`**：按[事实依据与内部引用](#事实依据与内部引用)区分材料性质，记录拟采用事实、来源、定位、原文及限定，缺口列入 `gaps`。集中记录只是索引，不能把自己的摘要当证据；不另建重复的 `facts.md`。
- **阅读用户附件（重要性与权威性都最高）**：用户上传/提供的一切材料都是本次任务的第一手事实来源，优先级高于联网搜索和你的先验知识。用户附件里有很多关键信息藏在图/表/公式里，只跑 `paragraphs` / `pdftotext` 会丢掉它们；如果之前读取附件时只获得了文本信息或没有读取附件，那你必须再一次解析附件内容获得更多相关信息，docx 必须再跑 `doc.tables` + `doc.inline_shapes` + `unzip word/media/`，pdf 必须再跑 `fitz.get_images` + `fitz.find_tables` 来获得一些附件中的图片/表格信息或使用 `page.get_pixmap` 来获得 pdf 中的截图，附件中的图片/表格插入 PPT 时，必须保留原图表的所有信息，**绝对不允许做裁剪，但是可以缩放大小来适配 PPT 的排版布局**；与其它来源冲突时以用户附件为准。**在创建 PPT 前，你必须完整阅读附件中嵌入的文字/图片/表格等信息才能创建**。（本条仅适用于作为内容或素材来源的 DOCX、PDF、XLSX、图片等辅助附件。作为主原稿或模板的 PPTX/Slides 必须先导入或读取在线 Slides，再通过服务端 XML 分析，不做本地 PPTX 解析。）
- **联网搜索**：补齐主题相关的真实数据、事实、案例；不得编造，缺失就标注占位/假设/待补，并标注来源。用户给的是完整文档或逐页大纲、且没说能否扩写时，默认联网搜索扩充素材与案例，除非用户明确要求不扩写，学术场景可以加载并使用学术搜索工具，而不是通用搜索。
- **网页精读**：对于搜索到的重要的网页，可以使用 web fetch 工具阅读网页中的完整内容，来补充更多真实数据，对于 academic 场景的 ppt 而言，精读论文可以拿到真实的完整数据，不要跳过这一步，同时也不要过度滥用这个工具，一次 academic 相关的任务只使用1-3次
- **搜图工具**：真实实体（人物、产品、logo、地标等）对应的图片必须用搜图工具获取。搜图时每次少搜一些（工具默认返回 6 张，可把数量设为 4 张），避免一次拉取过多。
- **生图工具**：插画、封面主视觉、示意图、以及缺真实图时的兜底图用生图工具生成。用于背景或封面的图不应带文字，生成后检查，出现文字必须重做。**在生成 ppt 的过程中，禁止去阅读 “doubao creative design” 这个 skill**， 可以直接调用生图工具，阅读这个 skill 会造成大量不必要的 token 消耗

**记录图片的宽高比**，供 Step 7 写 `<img>` 时安排缩放与裁剪参考。

#### 封面与内容页配图

- **重视封面，围绕主图设计**：封面决定整份 PPT 的第一印象，应投入足够的设计精力。根据主题、受众和整稿色系，生成贴合内容、具有审美与质感的高质量主图，再结合图片的构图、主体位置与视觉重心安排标题、文字和留白，形成图文一体、精致协调的封面。
- **内容页配图服务信息表达**：根据当前页的观点与材料选择合适的图片，用于解释概念、展示对象或提供证据，图文相互支持；强调视觉和设计的策划、画册等需要注意配图的质感。

### Step 4 · 理一份轻量大纲

想清楚即可，不必写成文件；可在思考里给出。

大纲设计必读：

- 明确整稿要让受众理解什么、形成什么判断或完成什么任务，再安排逐页内容。每页承担清楚的表达任务，相邻页面有承接，目录与后续内容正确对应。版式与翻页节奏随内容安排。内容组织和语言风格应贴合场景、受众与所选指南，保持整稿主线清楚、前后衔接自然。充分、合理地使用用户附件，补充与引申紧扣主题；事实、数据、案例和引用真实可追溯，不编造内容或来源，并区分事实、推断与示例。
- **页面设计**：先落实[通用设计要求](#通用设计要求)，再安排各页细节。
  - 目录按需设置，同级项结构与层级一致，单列自上而下、多列逐行从左到右；重复展示时保留顺序与位置，只突出当前章节。
  - 内容页按真实主次强调，同级且同等重要的信息保持相同的强调程度，不因排列先后或装饰需要随意放大、加粗。
  - 同级字体与颜色含义保持一致，保证文字和背景的对比；避免彩虹式装饰和大面积高饱和渐变，不以章节切换为由随意改换底色。

格式参考：

```text
幻灯片标题：
目标受众与沟通目的：
整稿主线：[核心问题/命题，以及内容如何推进和收束]
本稿设计方向：[用一句话说明]
配色方案：[主色 / 辅色 / 强调色]
页面规划（共 N 页）：
第 N 页 - 角色/读者任务；关键信息；支撑材料与来源；与前后页的联系
```

### Step 5 · 准备工作

动手落 XML 之前，先把语法读到位、把承接页面的空幻灯片建好。

1. **读语法**：生成任何 XML 前必读 [`xml/xml-schema-quick-ref.md`](references/xml/xml-schema-quick-ref.md)，篇幅较长，务必完整读完；图表按选定设计系统调用 SVG 图表库，用户明确要求原生图表或需编辑已有原生 `<chart>` 时，必须先用 `python3 scripts/slides_chart_tool.py get <id-or-keyword>` 获取对应 XML 片段，再照抄工具输出；用 svg 专业图表前跑 `python3 -c "from scripts.gen_svg_charts import chart_help; print(chart_help())"` 一次拿到完整的调用范式总览，**不要接 `| head` / `| tail` 截断，末尾的全部入口索引也要看到**（也可 `chart_help('sankey')` 拿单张详情）；需要使用到树状图时先跑 `python3 -c "from scripts.gen_svg_relations import relation_help; print(relation_help())"`（也可 `relation_help('<slug>')` 拿单张详情），支持范围以当前 manifest 为准；正式 Slides 必须用 `make_relation_atomized(..., strict_no_embed=True)` 或 CLI `--atomized` 输出多个独立元素，不得用 `<embed>` 作树状图主体；**手写 SVG 前必读 [`xml/svg-writing-guide.md`](references/xml/svg-writing-guide.md)** 了解规则；用图标先用 `python3 scripts/iconpark_tool.py search --query "<关键词>"` 检索（见 [`xml/iconpark.md`](references/xml/iconpark.md)）；选择、修改字体必读 [`xml/fonts.md`](references/xml/fonts.md)，不要凭记忆填写 `fontFamily`。
2. **建空白幻灯片（两步创建·第一步）**：先 `slides +create --title <幻灯片标题>`（不带 `--slides`）建一份空白幻灯片（见 [`cli/lark-slides-create.md`](references/cli/lark-slides-create.md)），**必须从工具返回结果中拿到并记下 `xml_presentation_id` 和 `url`**。Step 6 上传图片、Step 7 写入要用 `xml_presentation_id`，Step 5 通知、Step 8 交付要用幻灯片链接 `url`，缺失时先检查完整响应，并用已有 ID／链接只读确认创建状态，按 [`error-handling.md`](references/workflow/error-handling.md) 恢复；仅确认未创建成功后才重试创建，状态不明不得直接重建。
3. **开工通知**：用 present_files 工具把上一步拿到的 `url` 发给用户，并在回复里附上简短说明。这个链接和 Step 8 交付用的是同一个地址，但两次都必须发，不能省掉任何一次：这里是开工通知，Step 8 才是成稿交付。

present_files 提交的链接会变成一张可点击的产物卡片，你需要直接回复向用户说明**PPT 已经开始制作，可以点击卡片，关注进度**，为了确保用户看到，**开工通知务必放在思考过程之外，以用户可见的回复正文输出**（思考过程内容在展示时会被折叠）。这个能边做边看进度的体验非常棒，所以通知环节非常关键，一定要让用户感受到。

### Step 6 · 图片处理

已选用的图片按本步落地成 `file_token`：**取到本地 → 图片去底色 → 上传**。逐页制作时补充的图片素材同样执行本步。图片裁剪在 Step 7 中用 `<img>` 的 `<crop>` 实现，不需要在本步处理。

1. **取到本地**：禁止 http(s) 外链，飞书 slides 渲染端不会代理外链图，外链 `src` 在幻灯片里通常不显示；网图必须先 `curl -L` 下载到 CWD 内，生图/搜图工具的产物同样先落成 CWD 内的文件。从已有 Slides 复用图片时，从实时回读 XML 的 `<img src>` 获取 `file_token`，再用 `lark-cli api GET "/open-apis/drive/v1/medias/<file_token>/download" --output "<file>"` 下载到本地。
2. **图片去底色**：带底色的图片盖在有色背景上会让整页设计垮掉。对 Step 3 收集到的图片素材，调用去底色工具前完运行 `mediakit-cli image remove-image-background --help` 与 `mediakit-cli image remove-image-background --schema` 获取命令的输入输出说明，注意该命令里的boolean 参数--need-crop-background 必须写成 --need-crop-background=true / --need-crop-background=false，--image-url 参数可以接受搜索到的图片URL，直接使用即可；未完成上述读取和检查前禁止直接调用，logo徽标、动漫卡通图片使用 `--scene=general`，人像、真人、实物使用 `--scene=product`。**黑白灰底色的图片必须抠**，渐变底和复杂背景直接跳过不要硬抠；命令成功后立即下载返回的 `image_url`，另存为新的 PNG（不覆盖原图、不可存 JPG）；无需去底色、跳过处理或抠图效果差时，使用原图作为最终素材；**抠完逐张检查，确认背景透明、主体边缘无残留色块、主体内部无误抠，如果抠后效果差回退使用原图**。
3. **上传拿 `file_token`**：上传最终选用的图片；若处理改变了图片比例，更新用于排版的宽高比记录。逐个 `+media-upload --file <图片路径> --presentation <id>` 上传，**拿到各自的 `file_token`**（见 [`cli/lark-slides-media-upload.md`](references/cli/lark-slides-media-upload.md)）。

### Step 7 · 逐页完成

**按页完成：落 XML → 带 `--no-lint` 提交 → 确认写入结果**。写入成功后再做下一页，不要攒完整份再统一写入，禁止批量创建。

默认追加时，页序由成功写入的先后决定，与文件名编号无关。当前页写入失败或尚未确认时，不得跳过它继续追加后续页，否则稍后补写会落到末尾。

1. **落 XML**：核心结论定标题，选定的设计系统定版式与配色。带图页把 Step 6 拿到的 `file_token` 写进 `<img src>`。不用写 `<?xml ...?>` 声明，也不用包 `<presentation>`，只提交单个 `<slide>` 元素。元素上不要自己编 `id`，留空即可（ID 由服务端分配，自造 ID 容易撞车）。文本和属性值里的 `&`、`<`、`>` 必须转义为 `&amp;` / `&lt;` / `&gt;`。**全篇禁止使用 emoji（任何位置都不能出现）**，语义图标一律用检索到的 IconPark `<icon>`。

2. **图片使用**：**图片可以裁剪或缩放大小来适配 PPT 的排版布局，不要溢出画布**；**附件中提取的图片/表格不允许做裁剪**，但可以缩放大小来适配你选择的 PPT 的排版布局；`<img>` 的 `width:height` 对齐原图比例就不会裁剪，只会缩放大小；对不上会自动裁剪，且默认从中心裁掉多余部分，可用 `<crop>` 的 `anchor` 指定保留哪一侧。**同一张图片不要在多页重复使用**，补充素材或重新排版，Logo、统一装饰除外。

3. **素材补充与兜底**：制作过程中发现素材缺口，或已有素材无法满足当前页的内容表达、质量或版面需求时，允许继续联网搜索、搜图或生图补充素材；新增图片服务当前页的信息表达，并按 Step 6 完成处理与上传。主视觉优先用真实素材，绝不留空白图框。缺图先用搜图工具或生图工具补这一页要用的图；补不到或不可用时，用生图工具生成替代的近似图或抽象图。仍不可用时，按内容类型兜底：数据图从 SVG 图表库选择，结构示意用手写 SVG 或 `<shape>`+`<line>` 等可编辑元素。数据类可视化缺真实数据时不要编造数字，确需图表占位时仍按数据含义选 SVG 入口，并标注「模拟数据，仅占位，待替换真实数据」。

4. **演讲者备注**：需要在每页 `<slide>` 的 `<note>` 中提供 3–5 句可直接照读的讲稿。

5. **提交前核对引用**：读取本页已保存的作者 XML 和 `references.json`，从标题、正文、图注与讲稿的实际句子，反查编号对应的原文、定位及对象、时间、状态、确定程度和口径。**核对整句支撑，不只数编号；混合句拆开核，数字有依据不代表附带的能力或因果判断成立，预测不能改成已发生的实绩。**检查编号唯一对应记录、紧邻使用处，计算和推断有 `derivation`。支撑不足时补真实依据，或修改实际句子及引用；不能仅改注释、`kind` 或末页说明。修改后重读最新作者稿再提交。使用 `publish_slide` 时一并核对待传图形片段与数据，保留合页前的含注释作者稿，不手工拼页。这是提交前内容核对，不启动视觉 lint 或截图

6.  **写入幻灯片（两步创建·第二步）**：每页用 `slides +add-slide` 写入（见 [`cli/lark-slides-add-slide.md`](references/cli/lark-slides-add-slide.md) 与本步末尾的示例）。**页面里有 SVG 数据图或示意图（`chart_slide` / `d.to_slide` 的片段）时改用 `publish_slide`**，写法见 svg-writing-guide.md「合页与写入：publish_slide」一节：它负责合页、文本框适配及带 `--no-lint` 写入；这类页不要自己拼 `<embed>` 塞 SVG，也不要把片段手动拼进 XML 再调 `+add-slide`。**某页写入失败时，先按失败原因处理当前页（不要先写后面的页）**；已写错位置时插到正确位置再删旧页。**默认追加到整份幻灯片的末尾；要插入到某页之前，必须传 `--before-slide-id <目标页的slide_id>`。** **记下返回的 `slide_id`**：它是这一页的唯一关联键，后续编辑与异常状态确认都按它定位。写入命令见本步末尾的示例。

7. **处理写入结果**：成功时从 `data` 记录页面 ID 和版本并继续；成功响应附带的 `issues` / `slide_issues` 不触发 lint 报告阅读、修复或复检。`ok: false` 时该次写入未确认成功，按 [`error-handling.md`](references/workflow/error-handling.md) 处理。`4000153` 表示服务端仍拒绝了页面，即使传了 `--no-lint` 也不能标记已写入；保留失败状态，不自动重试或进入 lint 清零循环。

8. **写入确认与失败排障**：写入后检查完整 CLI 响应，只有 `.ok == true` 且 `.data.slide_id` 非空，才能标记该页已写入，并记下页码与 ID 的对应关系。Shell 退出码为 0 不代表业务成功。遇到解析失败、ID 缺失、`invalid param`、创建失败、空白页或 3350001 等异常时，按 [`workflow/error-handling.md`](references/workflow/error-handling.md) 查看原始响应并回读确认实际状态，再决定修复或补写，不得假定成功或直接重试。补到非末尾位置前，先核实非空的插入锚点 ID，定位失败不得退化为末尾追加。

**写入命令（关键）**：把每页 XML 存成文件，用 `--slide @<文件>` 传入（必须是当前工作目录内的相对路径，不接受绝对路径或 `../`），不要把 XML 内联进命令行（中文/引号/特殊字符易被 shell 转义或截断）。例：

```bash
cd "<本页XML所在目录>" &&
lark-cli slides +add-slide --no-lint \
  --presentation "<xml_presentation_id>" \
  --slide @slide-01.xml
```

如需插入到某页之前，在上述命令中增加 --before-slide-id "<已核实的目标页ID>"；追加和插入二选一，不要重复执行。

### Step 8 · 交付

**成稿交付**：用 present_files 工具明确交付最终产物，并在回复里附上制作介绍，但是禁止在最终回复中直接给出产物的链接；编辑已有幻灯片同样必须再次交付。本地已打开文件按 [`workflow/local-compat.md`](references/workflow/local-compat.md) 交付原始路径，不要求磁盘同步更新，也不得声称已代用户保存。在线幻灯片交付最终链接；新建稿的链接**用 `+create` 返回的 `url` 字段**（Step 5 已记下）。

## 三、参考文档地图

### `style/`

五类指南及适用场景见[新建流程 Step 2](#step-2--选定设计系统)。按主要沟通任务选择；普通介绍、生活分享、个人和产品展示优先走品牌叙事与通用展示，教育场景须有明确教学任务。未命中专门场景时，以品牌叙事与通用展示兜底。

### `xml/`

| 文档                                                                        | 何时读                                                                |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [`xml-schema-quick-ref.md`](references/xml/xml-schema-quick-ref.md)       | 生成任何 XML 前必读，元素与属性速查                                               |
| [`slides_chart_tool.py`](scripts/slides_chart_tool.py)                    | 画原生 `<chart>` 前按类型获取 XML 片段并照抄工具输出；禁止直接通读 demo                     |
| [`slides_xml_schema_index.md`](references/xml/slides_xml_schema_index.md) | 语法下钻权威来源：按元素摊平、已展开继承的可 grep 索引，含属性、枚举、约束、内容模型与最小 XML；精确定义 grep 本文件 |
| [`iconpark.md`](references/xml/iconpark.md)                               | IconPark 图标检索与用法                                                   |
| [`iconpark-index.json`](references/xml/iconpark-index.json)               | 图标离线索引，供脚本检索，不用手读                                                  |
| [`svg-writing-guide.md`](references/xml/svg-writing-guide.md)             | 图表库调用 + 手写 SVG 示意图（drawing 库、转换边界、atomize 与合页）                     |



### `cli/`

| 文档                                                                                            | 何时读                                                                      |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| [`lark-slides-create.md`](references/cli/lark-slides-create.md)                               | `+create` 创建幻灯片（两步创建第一步：建空白幻灯片）                                          |
| [`lark-slides-add-slide.md`](references/cli/lark-slides-add-slide.md)                         | `+add-slide` 逐页追加/插入单页（两步创建第二步）                                          |
| [`lark-slides-xml-presentations-get.md`](references/cli/lark-slides-xml-presentations-get.md) | `+xml-get` 回读全文 XML                                                      |
| [`lark-slides-replace-slide.md`](references/cli/lark-slides-replace-slide.md)                 | `+replace-slide` 块级替换/插入                                                 |
| [`lark-slides-update-slide.md`](references/cli/lark-slides-update-slide.md)                   | `+update-slide` 整页原地覆盖（多页每页一次）                                           |
| [`lark-slides-delete-slide.md`](references/cli/lark-slides-delete-slide.md)                   | `+delete-slide` 按 `slide_id` 删除单页                                        |
| [`lark-slides-media-upload.md`](references/cli/lark-slides-media-upload.md)                   | `+media-upload` 上传图片拿 `file_token`                                       |
| [`lark-slides-history.md`](references/cli/lark-slides-history.md)                             | `+history-list` / `+history-revert` / `+history-revert-status` 查看与回滚历史版本 |
| `lark-slides-xml-presentation-slide-get.md` / `-replace.md`                                   | 单页原生 API（无 shortcut 覆盖时用）                                                |



### `workflow/`

| 文档                                                           | 何时读                                            |
| ------------------------------------------------------------ | ---------------------------------------------- |
| [`slides-editing.md`](references/workflow/slides-editing.md) | 在原稿上改的完整流程：理解原稿 → 定位改哪里 → 按需备素材 → 修改并确认写入 → 交付 |
| [模板制作流程](references/template/workflow.md)                    | L1–L9 唯一制作入口：解析资产 → 内容与版式配方 → 逐页发布 → 完整稿复核与交付  |
| [`error-handling.md`](references/workflow/error-handling.md) | XML 语法/接口/错误码排障与失败处理                           |
| [`validation-xml.md`](references/workflow/validation-xml.md) | 写入响应确认、失败状态处理及按需读取原稿                           |
| [`windows-compat.md`](references/workflow/windows-compat.md) | windows 本地电脑操作报错兼容说明                           |
| [`local-compat.md`](references/workflow/local-compat.md)     | windows/mac 本地电脑模式操作背景说明                       |



### `scripts/`

| 脚本                                                         | 用途                                                                                                                                                                                                                                                                                                                               |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`xml_inspect.py`](scripts/xml_inspect.py)                 | `--mode summary`（默认）输出摘要及其它模式用法提示；`--mode content` 输出不截断的页面文字/数据，不含演讲者备注；`--mode raw` 返回含完整 XML 的 JSON。summary 固定读全稿，不接受 `--slide-id`；content/raw 可加 `--slide-id ID...` 选页，不传则读全稿。精确编辑、模板继承必须读 raw XML                                                                                                                           |
| [`iconpark_tool.py`](scripts/iconpark_tool.py)             | IconPark 图标检索，最小用法 `python3 scripts/iconpark_tool.py search --query "<关键词>"`（再按需 `resolve`）                                                                                                                                                                                                                                      |
| [`gen_svg_charts.py`](scripts/gen_svg_charts.py)           | SVG 图表生成：先写下每页数据图要回答的研究问题，按 `chart_help()` 的学科表选专业入口（文献已报告的汇总值即可作图）；类别柱状只用于没有更贴切问题的单值概览。`chart_slide(slug, x=, y=, width=, height=, **kwargs)` 返回半可编辑页面片段（`make_<slug>` 只返回 SVG）。**主入口**：`python3 -c "from scripts.gen_svg_charts import chart_help; print(chart_help())"` 获取数据条件与名称短索引；`chart_help('<slug>')` 按需获取签名、示例、变体和组合条件 |
| [`svg_lib/svg_drawing.py`](scripts/svg_lib/svg_drawing.py) | 手写示意图的几何与排布助手：轮廓端口、连线避障、行/列/网格/环形排布、两列配对、端口分配、按文字定尺寸的节点框与自动标签。**主入口**：`python3 -c "from scripts.svg_lib.svg_drawing import drawing_help; print(drawing_help())"`，用法见 svg-writing-guide.md 第四节                                                                                                                                    |
| [`gen_svg_relations.py`](scripts/gen_svg_relations.py)     | SVG 树状图生成：支持范围以当前 manifest 为准，运行 `relation_help()` / `relation_help('<slug>')` 或 CLI `--list` 查看。正式 Slides 必须用 `make_relation_atomized(..., strict_no_embed=True)` 或 CLI `--atomized` 输出拆分的独立元素；**主入口**：`python3 -c "from scripts.gen_svg_relations import relation_help; print(relation_help())"`                               |
| [`safe_update_slide.py`](scripts/safe_update_slide.py)     | 目标页级 CAS 保护的 `+update-slide` 包装：语义级 diff（元素签名：元素数/id 集合/几何/文本前 60 字），一致才允许写入，不一致 abort 并把服务端最新版覆盖本地。**仅 Organizer 流式检查+refine 模式使用**；MainAgent 主流程走裸 `+update-slide` 即可                                                                                                                                                          |
| [`parse_template.py`](scripts/template/parse_template.py)  | template-editing 分支 Step 1 用：离线解析 PPTX 产出 `template-manifest.json`（每页 role / 壳层 shape / 可用区 bbox / 占位文本清单 / 缩略图路径）+ `theme.json`（配色 + 字体）+ 抽全部图片到 `assets/` + 渲染每页缩略图到 `thumbs/`。用法：`python3 scripts/template/parse_template.py --pptx <path> --work-dir <WORK_DIR>`                                                             |



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
| [`+update-slide`](references/cli/lark-slides-update-slide.md)     | 整页原地覆盖，`slide_id` 和页序不变；没写进 `--content` 的元素会被删除            |

没有 shortcut 覆盖时用原生 API；调用前必须先看参数结构：

```bash
lark-cli schema slides.<resource>.<method>   # 调 API 前必先看参数结构
lark-cli slides <resource> <method> [flags]  # 调 API
```
