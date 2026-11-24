# 模板制作流程 · L1–L9

本文件是模板任务的唯一制作入口。使用具体工具时，按 [工具说明](tools.md#阅读导航) 的导航读取所需章节；不要求通读工具文件。工具说明覆盖 Python 函数与脚本入口；原生 `lark-cli` 命令仍查 `references/cli/`。

用户提供模板、空版式、VI 或 PDF/图片风格参考制作新内容，以及已有 PPT 换模板时走本流程；按输入用途判 L1–L9，不按扩展名判定。PDF 仅作事实材料走普通新建，要求同内容同版式 1:1 复刻走总入口的复刻分支。**MainAgent 独立完成解析、资料整理、全部页面、视觉修订和交付**。模板制作不启动多 agent，也无需角色判断、派单或交接。已发现的具体问题按下文「困难页优化」处理。

**核心原则：先用模板的整页与组件表达内容。** 模板包括内容组件、图表、装饰图、形状、排版关系，以及各文字角色的字体、字号、字色，不只是页眉页脚和配色。逐页按 **整页适配 → 借用组件 → 同族新建** 的顺序选择。替换旧事实与示例内容，保留适用的视觉设计。

内容尚未定稿时，按自然匹配的模板结构组织叙述；用户给定完整材料或逐页内容时，先保证内容完整，组件随内容适配。不要为了复用删事实、改口径，也不要因一个槽位不合适而抛弃整页可用资产。

## 模板专属执行约定

以下约定仅适用于本模板分支。模板附件解析、读取频次、逐页配方、发布和复核按本文执行；本地环境、工具身份与 `present_files` 交付沿用总入口的通用规则。

- **技能包**：使用用户提供的模板 skill ZIP 时，以完整解压目录中的版本为准。用 `unzip -q` 完整解压，不将输出 pipe 到 `head`；脚本或参考缺失时先从原 ZIP 完整重解压。
- **读取频次**：首次进入模板流程，完整读取 SKILL.md 和本文。`tools.md` 以章节为阅读单位，只完整读取当前实际使用的部分；首次发布读普通发布与结果处理，用整稿配方再读配方，有指标填值再读指标，严格诊断仅在需要时读对应部分。后续继续同稿、同工具时沿用已读说明，先核对目标 ID 与原有内容；新模板、新接口或参数问题再查相关节或 help，不为每页重复加载全文。本条仅规定模板分支的读取方式。
- **轻量发布**：`template_publish.py` 以业务 ACK 和真实页面 ID 登记写入。视觉、密度、源几何和风格检查默认提供诊断；`--no-lint` 可直接跳过误报，理由用可选 `--reason` 简记；`--strict` 才启用严格检查。已 ACK 的差异作为可选诊断，状态未知时只读恢复，避免重复新增。全部页面写入完成后直接导出并交付，默认不主动执行成稿回读、全页截图验收或循环修复；用户明确要求检查或排障时再按需处理。逐页配方、具体参数及交付步骤见 Step 5–6。

**本地电脑模式**：按 `SKILL.md`「权威经验」中的运行环境规则判为本地电脑时，读完本文档后必须完整 Read [`local-compat.md`](../workflow/local-compat.md) 与（若 Windows）[`windows-compat.md`](../workflow/windows-compat.md)。


## CWD 与产物目录
始终停留在任务开始时的 CWD；所有产物写入 CWD 内的独立目录：
```bash
LARK_SLIDES_SKILL_DIR="<包含当前 SKILL.md 的绝对目录>"
WORK_DIR=".lark-slides/template/<deck-or-task-id>"
mkdir -p "$WORK_DIR/manifest/slides" "$WORK_DIR/assets" "$WORK_DIR/thumbs" "$WORK_DIR/source-slides" "$WORK_DIR/authoring" "$WORK_DIR/lint"
```
Skill 脚本始终通过 `$LARK_SLIDES_SKILL_DIR/scripts/...` 调用。

## 流程（6 Steps）
### Step 1 · 判定链路，再解析模板

先记录 `LINK`。已有 PPT 换模板优先判 L8；其余按输入与模板形态判断：

| LINK | 输入与模板 | 执行重点 |
|---|---|---|
| L1 | 只有 VI，无模板页 | 从 VI 建风格卡与新 deck；按品牌规范做各页，不调用 PPTX 模板解析 |
| L2 | 只有封面、目录、章节、结尾等结构页 | 结构页整页继承，内容页从其框架、字阶、装饰语言延伸 |
| L3 | 空版式 / 母版占位区 | 读取 PPTX 的 slideLayouts、母版、theme，记录版式名和各槽 bbox；按内容匹配版式，保留占位区位置与角色；0 页模板不是空文件错误 |
| L4 | 组件样例 + 一句话主题 / 零散大纲 | 按本题内容展开，优先使用真实整页或完整内容组件；页眉与背景不能替代内容组件复用 |
| L5 | 组件样例 + 完整材料 / 已定逐页内容 | 先逐条映射 facts，再借合适组件；不设比例，不借时写具体不适配原因 |
| L6 | 数据对象 / 图表模板 + 本次数据 | 复用原生图表类型与视觉配置，更新数据；可原生的图表不降为图片或数字卡 |
| L7 | 完整成稿作为模板 | 按用户 > 材料 > 模板对齐章节与每页用途；模板没有材料支持的示例槽删掉，不编经历、金额和时间 |
| L8 | 已有 PPT 换模板 | 原稿逐页一一迁移；正文、标题、图表、表格、符号和备注不增删、不改写；仅换视觉样式 |
| L9 | 只能看的 PDF / 图片参考 | 看完整参考，提炼风格卡，自建可编辑页面；不复制参考品牌、人名与内容 |

L4 与 L5 看内容是否已定，不看附件扩展名；只有几条事实的材料仍属 L4。L1/L9 用 `slides +create` 建新 deck；L3 先解析原版式；0 页母版实例化完整工作页后导入，以原背景、装饰、占位区与文字样式为起点，并记录 `layout` 名。L8 的原稿与模板分别读取、保存、编号，不能把原稿当作模板清空。

模板 PPTX/POTX 作为视觉来源时，先离线盘点原页、组件、图表与版式，再导入工作副本。L3 零页模板先读取 slideLayouts、母版、主题和占位区；L8 原稿与目标模板分别按本流程准备。总入口对普通原稿内容编辑的读取顺序不替代这些模板解析步骤。

L1/L9 先查看真实参考。**独立图片直接看原图并记录尺寸、构图和文字角色**，无需改扩展名或转成 PDF；参考为 PDF 时，用以下命令生成全页浏览图：
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_reference_assets.py" overview \
  --pdf "$WORK_DIR/<reference>.pdf" --output-dir "$WORK_DIR/thumbs/reference" \
  --manifest "$WORK_DIR/manifest/reference-overview.json"
```
返回全部页的 `overview.paths` 联图与 `pages[].path` 放大图。先用联图选择封面、内容、数据与结束页，再放大核对字形、网格、色板和特色资产；原PDF和独立图片提取各自保留。

L1/L9 在制作前记录有具体值的视觉约定，可保存成 `style-card`：画布底色；标题/正文/数字/标签的字体、字号、颜色、字重；页眉页脚几何；图形母题和线型；图表色板；留白与信息密度。PDF用页面截图核对，同时可从文本 span 读取字体、字号和颜色；不能只读纯文本后取一个通用风格名。缺少原字体时读取支持字体，明确最接近的替代并保持衬线/无衬线角色，不能静默用默认黑色无衬线标题或白底覆盖参考。L1的品牌母题只建一个完整组件并等比复用，不逐页重画。

L1/L9 的新建仅表示没有可复制的原页，视觉仍由这份卡控制。先完成一个典型内容页，与VI/参考同屏核对底色、标题、数字、图表和密度后再继续，避免整份做完才发现体系不同。L8首个迁移页也先核对无模板残留或新增文字。

风格卡按用户指定的**文字角色**落值：例如“金色衬线标题”指主要页标题，不能只给小眉标/栏目标签金色而把主标题换成另一颜色。用户明确要求优先于参考稿或 style 的默认角色值。

**L9 先记录本题内容范围和用户的文字角色要求，再采集参考视觉。** 以下 extract 使用 PDF 文字层；独立图片直接查看原图，按角色记录视觉值，必要时清字，不要求先转 PDF 或强行提取字体。card 根据已准备的视觉 reference 生成角色约定。 完整看参考截图，分别建立风格卡和视觉资产目录：字体、配色、构图、密度，以及可复用的背景、纹理、插画和特色图片。事实、表格数值与讲稿从本题独立内容资料组织。
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_style_reference.py" extract \
  --pdf "$WORK_DIR/<reference>.pdf" --out "$WORK_DIR/manifest/visual-reference.json"
```
提取需要当前 Python 已有 PyMuPDF；校验只需标准库。输出不含参考正文、栏目、名称或备注，角色候选须与截图核对。**先把用户明确指定的角色值保存到 `manifest/style-overrides.json`，再生成卡**：例如金色主标题的要求可写 `{"main_title":{"basis":"explicit_user","values":{"color":"#C49A3C"}}}`，实际色值按本题要求与可读性选择；参考中的绿色主标题不能代替该要求。只有“serif”而未点名字体时，选适合本题语言的衬线字体，并记录原字体不可用或缺字的替代理由。没有显式覆盖项才省略 overrides 文件及下面的 `--overrides`。

**L9 从原视觉资产开始制作。** 先检查 PDF 的独立图片层，用 `template_reference_assets.py` 提取原图片及其页内位置；查看资产联图，选择与本题视觉体系自然匹配的背景和装饰。独立底图往往已经无字，直接提取可保留光影、纹理和曲面细节。文字确实烘焙在特色图中时，用当前环境的 `image_edit` 清除文字：保留原构图、图形、色彩和纹理，清图后与源图对照，再作为背景/图片上传。前景标题、正文、容器、表格和本题数据图用原生元素重建；数据图形承载新值，视觉素材承担背景或装饰。整页参考图只用于分析和清图，不作为完整成稿页交付。
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_reference_assets.py" extract \
  --pdf "$WORK_DIR/<reference>.pdf" --pages <选定典型页，例如1,4,10> \
  --output-dir "$WORK_DIR/assets/reference" \
  --manifest "$WORK_DIR/manifest/reference-assets.json"
```
资产目录给原图片宽高、SHA和使用页/bbox，联图只作选型预览；选用图片按原比例布局，透明mask和模糊关联结合原页确认。
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_style_reference.py" card \
  --reference "$WORK_DIR/manifest/visual-reference.json" \
  --overrides "$WORK_DIR/manifest/style-overrides.json" \
  --out "$WORK_DIR/manifest/style-card.json"
```
未被用户覆盖的角色值保持参考依据。不同页型可用 `--source-page` 选择典型页，所有卡使用同一份用户要求；发布时默认核对独立的 `style-overrides.json`、卡与实际文字，不能删卡内标记或重选参考值跳过要求。不要把参考的整句观点、翻译或换行业名词的改写放进正文/备注；视觉指标和角色校验不判断语义搬用，最终仍人工比较。

L3 先运行以下只读命令生成真实版式目录，再按名称/placeholder角色选页。目录记录母版继承的 bbox 和文字样式来源；画布尺寸以返回值为准，不把占位区拉满默认画布：
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_layouts.py" --pptx "$WORK_DIR/<template>.pptx" --output "$WORK_DIR/manifest/layouts.json"
```
目录中的 `slide_count=0` 时，从原母版生成完整可导入工作稿：
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_layout_materialize.py" \
  --source-pptx "$WORK_DIR/<original-zero-slide-template>.pptx" \
  --output-pptx "$WORK_DIR/layout-source.pptx" \
  --report "$WORK_DIR/manifest/layout-materialization.json"
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/parse_template.py" \
  --pptx "$WORK_DIR/layout-source.pptx" --work-dir "$WORK_DIR" --deck-title "<本题标题>"
```
工作页带原版式完整背景、装饰、系统字段和可识别的内容槽标记；原模板的master/layout/theme/media保持原样。receipt的版式与逐槽marker/idx/geometry映射用于对应真正导入的源页和元素。已有空页的模板直接解析原页。

L3 的 page-plan 每页写 `layout`、标题/正文/图表各用哪个 placeholder、对应 bbox。没有原页的0页模板不标 `fixed_template`；它是按真实空版式落位。若平台画布必须缩放，所有坐标使用同一明确比例，保留版式内留白。

**L3 从真实空槽开始写，而非看完目录后自行估坐标。** 每页选定 layout 后，生成该页原生 XML 与外部槽位绑定（版式名以目录实际值为准）：
```bash
mkdir -p "$WORK_DIR/manifest/layout-contracts"
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_layout_contract.py" \
  --manifest "$WORK_DIR/manifest/layouts.json" --layout "<真实版式名>" --instance-id P1 \
  --output "$WORK_DIR/manifest/layout-contracts/page-01.json" \
  --skeleton "$WORK_DIR/manifest/layout-contracts/page-01.slots.xml"
```
以选定版式的 `source-slides/slide-NN.xml` 完整框架为作者底稿。slots文件提供原空槽的几何与样式；按工作稿marker及receipt将实际原生元素ID绑定到对应slot。只在内容槽填标题、正文；图表/表格/图片替换对应内容槽时保留其 slot ID，元素完整落在槽 bbox 内。一个槽内组合多个元素时，用 `<page-NN>.bindings.json` 的 `elements` 将各元素 ID 映射到同一 slot ID。标题以原槽风格为起点；长标题先精简或调宽/行高，必要时适度调整字号，保持字阶和可读性。原字体不可用时在 bindings 的 `font_substitutions` 写替代字体与具体理由，保持原字形职责。保留底稿已有背景和无文字装饰，图片背景/logo 在 bindings 的 `decorative_ids` 明确登记，文字/图表/表格不能标装饰。Title Only/Blank 没有内容占位区时用 `--free-regions` 提供选定留白区的 name/bbox，再生成绑定；不修改源标题槽来扩大内容区。用法见 [发布与恢复](tools.md#发布与恢复)。

**L2/L4–L8：解析模板 + 复用导入副本为交付 deck**。只操作导入副本，不修改用户提供的源模板：
一条命令跑完解析 + 导入 + 清空到 1 页:
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/parse_template.py" \
  --pptx "$WORK_DIR/<template>.pptx" \
  --work-dir "$WORK_DIR" \
  --deck-title "<用用户主题命名,例:L 医药流通企业数字化转型的经济效果研究>"
```
`--pptx` 可直接传原 `.pptx` 或 `.potx` 文件名。POTX 自动在工作目录生成可导入的演示副本，完整保留主题、母版、页面、素材与备注；索引中的 `source_input` 记录原文件与副本。
模板SVG图片可在此解析入口用 `--prepare-import-source` 选择原有PNG/JPEG fallback；需要改列表显示时另给 `--import-bullet-char`。格式选择记录保存在索引的 `source_input/source_import_preparation`。L8原稿的完整源树由 `prepare-source` 取得，目标模板副本在此解析。

**在线来源转 PPTX**：Slides 链接取实际 presentation token，再用 `lark-cli drive +export --as user --token <token> --doc-type slides --file-extension pptx --output-dir "$WORK_DIR"` 导出；Wiki 链接先用 `lark-cli wiki +node-get --as user --node-token <wiki URL/token>` 读取实际 `obj_token`，确认类型为 slides。

**统一实际画布（导入后、制作典型页前）**：模板尺寸不一定是 960×540。先回读当前交付 deck 的整稿 XML，从 `<presentation width="..." height="...">` 取得实际 SML 坐标宽高，保存为本题 `DECK_W/DECK_H`；导入后的源页坐标也按这组数解释。PPTX 的 EMU/英寸、截图像素、默认尺寸都不能替代实际 SML 尺寸。L1/L9 新建的 deck 同样读返回的实际尺寸。

```bash
# 在任务 CWD 运行，DECK 为当前交付 deck 的真实 ID
lark-cli slides +xml-get --as user --presentation "$DECK" --output ./canvas-baseline.xml --json > ./canvas-baseline-response.json
# 先确认回读响应 ok:true，再从 XML 根读取并记录尺寸
read DECK_W DECK_H < <(python3 -c 'import xml.etree.ElementTree as E; r=E.parse("canvas-baseline.xml").getroot(); print(r.attrib["width"], r.attrib["height"])')
```

DECK_W/DECK_H 由上述回读赋值；后续独立 Bash 调用从同一实际 XML 再读取，不假定 shell 变量跨工具调用保留。优先在实际画布上保留原模板的完整几何和字号；同族新增页也用相同坐标系。每次调用 `template_publish.py`、整稿执行器或单页本地 lint 时，在该命令前传 `LARK_SLIDE_CANVAS_W="$DECK_W" LARK_SLIDE_CANVAS_H="$DECK_H"`。单页 `<slide>` 没有整稿尺寸上下文，本地 `xml_lint.py` 缺省才按 960×540；完整 `<presentation>` 则直接使用根尺寸。环境变量只控制本地检查；写入侧仍可能错误地按 960×540 校验，应读取其实际报告的 `slide_size/canvas`，不能假定它已使用目标 deck 的尺寸。

遇到大量 `*_out_of_canvas`，先核对报告里的 `canvas` 是否等于实际 deck，再判断原元素是否真越界。不要把正常的 1440/1920 宽模板压到 960 来通过默认检查，也不要把画布错配标为源装饰出血。若目标实际为 1440×810、本地按实际尺寸通过，但写入侧 `4000153` 报告仍用 960×540，不要先缩坏正确稿；可以直接 `--no-lint` 写入，诊断记录留到整稿核对，不要求每页豁免声明。真实文字溢出、遮挡或其它错误仍须修复。只有确实需要把不同尺寸的来源迁入目标时，才统一变换整个内容组的坐标、尺寸、字号、线宽、图片和图表/表格；保持宽高比与原布局关系，再用目标尺寸校验并看典型页截图。仅改 `<slide>` 的宽高、只缩背景或只缩文字，不能完成画布适配。

**从 stdout JSON envelope 解析并记住的字段**:

| 字段 | 用途 |
|---|---|
| `first_page_write` | **首页写入提示与可执行命令**：解析后保留的第一页仍然存在，第一张成稿用 `+update-slide` 覆盖它，第2页起再 `+add-slide`；回执带真实 `slide_id`，用发布器时显式传 `--slide-id` |
| `empty_text_cleanup` | 导入副本中自动移除无文字、无可见样式的闲置文本框，返回数量及记录路径；原始 PPTX、有效文字、图片、版式占位槽和被引用的对象保留。这类空对象在截图中不可见，不靠“点击添加正文”关键词判断 |
| `lark.deck.xml_presentation_id` | 后续所有 `+add-slide` / `+update-slide` / `+media-upload` / `+screenshot` 都用它 |
| `lark.deck.url` | Step 3 开工通知 + Step 6 交付 |
| `lark.deck.first_page_slide_id` | 首次发布传这个真实 `slide_id` 来更新保留的首页；发布器的自动空页识别仅作兜底，后续按登记 ID 更新 |
| `lark.deck.first_page_state` | `"blank"` = 已清空成空白;`"template_remnant"` = 清空失败留了模板首页(非致命) |
| `lark.deck.purge_failed_slide_ids` | **若存在(非空数组)必须补删** —— parse_template 主删除阶段用"一趟扫无重试"策略,撞 rate_limit 的页会跳过并列在这里 |
| `capability_level` | `full`/`degraded`/`minimal` 三档 |

**⚠️ Step 1 立即善后:补删残留页**

如果返回的 `lark.deck.purge_failed_slide_ids` 非空，安排补删这些残留页；内容准备可继续，交付前确认删净和页序：

```bash
# 从 stdout JSON 拿 purge_failed_slide_ids 列表 · 后台跑 purge_deck.py 慢速清扫
FAILED_IDS="<用逗号分隔的失败 slide_id 列表>"
python3 "$LARK_SLIDES_SKILL_DIR/scripts/purge_deck.py" \
  --deck "<lark.deck.xml_presentation_id>" \
  --work-dir "$WORK_DIR" \
  --slide-ids "$FAILED_IDS" --no-clear-first \
  > "$WORK_DIR/.purge_deck.log" 2>&1 &
echo $! > "$WORK_DIR/.purge_deck.pid"  # pid 落盘 · 后续 tool call 里读回
```

- `purge_deck.py` 按设置的 pace 节流和有限轮次重试；按实际回执判断成功，不保证固定耗时或绝不会限流。补删只删除已确认的残留 ID，不再清空首页。
- **后台跑,不阻塞 Step 2**。直接推进 Step 2 制定 plan,purge 后台清残留。
- Step 3 只是发工作卡片链接(deck 还是空的),不需要等 purge。**Step 6 交付前**确认清扫结果并回读页数,避免用户点开看到模板残留。
- purge_deck.py 失败不阻塞内容准备，但交付前必须删净残留页并核对页序，不能把进程结束当作清扫成功。

**解析后先读索引与全稿联图，再按计划读选中的源页和组件；完整源页始终保留**：

| 产物 | 何时 Read | 用途 |
|---|---|---|
| `manifest/template-index.json` | Step 2 一次 | **唯一轻量索引**:含 stdout envelope 关键字段 + 每页 200 字文字预览(`slides[N].preview_text`)+ `overview.paths`(数组,大 deck 会分片成多张 jpg)+ `visual_language`(主色 palette + 字体族,按角色继承)+ `assets_with_tokens`(模板自带图 file_token 清单,Step 5 引用图片从这里取,不需要重传)+ 每页 `content_skeleton_path`(active_rebuild 页的干净起点) |
| `thumbs/overview*.jpg` 或 `.pdf` | Step 2 一次 | 全稿联图;从 `template-index.json.overview.paths`(数组)按顺序 Read 所有分片;大 deck 会分成 `overview-1.jpg`/`overview-2.jpg`/...(每张 ≤ 3800px 保证 Read 工具能读);Read 工具对 JPG 和 PDF 都支持,不需要强行转格式 |
| `source-slides/slide-NN.xml` | 首次选择该源页/组件时完整读取；后续复用已读原件，来源改变再读 | 该页导入飞书后的完整 SXSD，是 cover/toc/chapter/transition/ending 每页 authoring/*.xml 的起点。内容页选组件时也读取候选源页完整 XML；品牌骨架只作为确需同族新建的起点，不是内容页默认起点|

`capability_level=minimal` 或 `overview.ok=false` 时，跳过看 overview，直接 Read `source-slides/slide-NN.xml` 反推每页结构。

**解析尚未完成时**：可先读用户资料、准备内容；选择模板组件与正式落页要等真实索引完成，不用固定耗时猜测成功或重启解析。

### Step 2 · 盘点可复用资产 + 制定 plan

**选定 style**：统一按主 [SKILL 的场景路由](../../SKILL.md#step-2--选定设计系统) 选择并记录主场景，只有需新建或补足表达时才读取对应指南。普通生活分享、个人或产品介绍、公众主题展示优先走品牌叙事与通用展示；教育须有明确教学任务，不因内容带知识性而误选。模板已有的组件造型与排版优先，style 用于信息组织与质量判断。

优先级例外：
- **模板的组件、装饰、图表类型与系列色板、文字角色的字体/字号/字色/字重、留白、线型和形状** → 以模板为准。style 的禁卡片、指定图表库、封面大图与字号默认值不覆盖模板；容量不足优先删冗词、增槽或拆页，L8 保持页数与原文。
- **未命中专门场景** → 以[品牌叙事与通用展示](../style/brand-storytelling.md)兜底，按主题与受众调整，不强行套入品牌故事或课程结构。

**收集事实材料**（L9 只读风格参考按 Step 1 处理，不提取其中事实或示例文字）：
- 用户附件（docx / pdf / xlsx / doc）：docx 必须 `doc.tables` + `doc.inline_shapes` + `unzip word/media/`，pdf 必须 `fitz.get_images` + `fitz.find_tables` + `page.get_pixmap`，doc 必须转成 docx 之后进行图片等信息提取；只跑 `paragraphs` / `pdftotext` 会丢关键信息。**图/表/数字/事实必须完整提取**。
- **内容先于样板**：模板中的诗词、案例和广告是设计示例。先用用户资料或主题事实组织完整讲解，再选版式；资料里的表格、实施阶段、选型与部署内容读全，引用名称、范围和单位按原文，章节顺序按新稿阅读逻辑。
- **文本/图片来源默认规则**：
  - 用户提供了内容资料 → 事实以资料为准，不擅自扩写；只有模板附件不等于已有内容资料。用户要求作品图、案例或联网补充时按其要求搜集并记来源。
  - 用户未提供附件或资料或指定来要扩展 → 走搜图 / 生图 / 联网搜索获得真实素材
  - **联网补充**：用户给了完整文档、数据或逐页大纲时，默认按其内容制作；缺少必要解释或素材再补查，记录新增来源和时间。缺失事实写“未披露”，假设或虚构示例按用户要求明确标注，不把它们作为原资料事实。
  - **模板示例文字与数值按本题事实替换**；通用标签可保留，L8 保留原稿内容。模板图片按下表判断。封面沿用模板构图，纯色、文字或原生图形也可以构成主视觉，按实际参考选择配图。
  - **不留占位、不编事实**：未知的公司、人数、年限、经历、联系方式、汇报人删槽或改为有依据的页面用途。仅用户明确要求虚构示例时才使用并标注。L8 不额外补说明、年份、脚注或备注。
  - **文字层级**：从对应模板槽继承标题、正文、数据标签、脚注的字号档位、字体、字重和字色；记录每个角色的源页/元素。不得把全稿统一成出现最多的字体或 style 默认字阶。小字确实不可读时按角色适度调整并保持层级，按实际容量适度调整标题/正文，并保持清楚字阶。

**模板资产按用途处理**：

| 资产 | 复用与适配 |
|---|---|
| 品牌框架 | 保留对应页型的页眉页脚、背景、导航、标题区、品牌资产及几何。L8 按换模板约定迁移视觉，排除模板样例机构的 logo/国旗/人物；L9 不搬参考品牌 |
| 内容组件 | 时间线、流程、金字塔、蜂窝、对比组、指标组、引文框等是可复用整体。保留节点、连线、底形、编号、标签与相对位置，替换文字；数量变化复制/删减完整节点后重排 |
| 装饰图与装饰形状 | 水墨、纹理、抽象图画、边饰、曲线等默认保留，包含仅出现一页的装饰；不能用跨页出现次数判断是否值得保留。保留宽高比与叠放关系，不把装饰位替换为主题照片 |
| 数据图表 | 优先原地更新原生图表的数据与标签；保留适用的图种、系列顺序、配色职责、图例、标注及小多图布局。轴范围按新数据调整。截图图表可按同样规格重建原生图表 |
| 真实照片 / 作品图 / 截图 | 检查是否与本题事实相关；相关则保留并记来源，不相关只替换这个内容槽。该图不适合不代表其余版式和装饰都不能用。用户作品图保持全貌，不裁断字画 |
| 示例文字 / 示例数值 | 按 facts 替换，未知删槽。图片内部的示例字样也检查，不能当装饰原样保留 |

**从全稿找组件，而非先挑一个空壳。** 看完所有 overview 分片，选候选页，读取对应 `source-slides/slide-NN.xml`。需要细看时看单页缩略图。记录 `template-assets.json`：

- `text_roles`：每种文字角色的源页/元素 ID、字体（含中西文）、字号、字色、字重、行距。
- `components`：给真实的相关元素组一个本地引用，如 `slide-07:c1`；记录 source、完整 member_ids、用途（对比/流程/层级等）、节点数、bbox、可变内容槽和保留的造型/装饰。引用必须能回到源 XML，不能只写“复用模板风格”。
- `charts`：原图类型、系列色板、单位/轴/图例/标注、系列排列和小多图关系；不要把 logo 或装饰颜色当数据系列色。
- `decorations`：源页、完整 member_ids / file_token、位置尺寸、作用、是否含示例字。圆环与红点、曲线与端点等共同构成的装饰按整体登记；默认连同有意出血保留原几何，不独立缩圈或移动端点。组件组与装饰均保留原始片段，不能仅保留文字预览。
- 不适配来源：按需要记录选型理由；不要求逐张登记未使用的模板页。

上述资产记录可复用解析器/组件工具已经生成的索引，只登记本题实际选用的来源，不要求再手写全模板台账。需要查看原元素的完整结构和实际文字样式时，运行：
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_reuse.py" inventory --source-dir "$WORK_DIR/source-slides" --output "$WORK_DIR/manifest/element-candidates.json"
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_reuse.py" extract --source "$WORK_DIR/source-slides/slide-07.xml" --ids <组件完整成员ID列表> --output "$WORK_DIR/authoring/component-v01.xml"
```
inventory 列出候选元素，不自动把单元素认定成有语义的组件；用原图选择完整 member_ids。extract 保留源顺序、样式、文字、图表数据和图片 token，拒绝缺失成员和已知孤立连线引用。提取片段按前述适配动作处理后合入本页，源文件不改。

**选中的内容组件直接在源槽内换字。** 用 inventory 的 `text_slots` 读取真实 shape ID、p/span 路径和继承样式，把本题内容写到 text-map，再运行 `replace`：
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_reuse.py" replace \
  --source "$WORK_DIR/source-slides/slide-07.xml" --ids <组件完整成员ID列表> \
  --text-map "$WORK_DIR/authoring/text-map-07.json" \
  --output "$WORK_DIR/authoring/component-filled-07.xml"
```
单一文本槽可用 `{"<真实shape ID>":"新内容"}`；多段或中西文不同 run 用真实槽路径逐项映射，例如 `{"<真实shape ID>":{"content[1]/p[1]/span[1]#text":"中文","content[1]/p[1]/span[2]#text":"Latin"}}`。它只改指定文字，保留组件成员、字框、段落、run、几何和样式，另存 `.replace.json` 来源。不自动加换行或拆合段落；字段/公式/列表用相应数据操作。文字放不下时按容量适配完整节点或换自然匹配的源组件，不将整组替换成新卡片。

**L4/L5/L7的新内容适配用完整填充计划。** 选定完整源组后先 `prepare-fill`，得到该组有序的标题、正文、节点标签、时期、表格文字和p/span槽位。逐项填写 `action`（`replace`、`keep_label`、`remove`）与 `new_text`：本题内容引用facts，确属通用标签的项明确保留，缺材料的项清除并重排完整组。然后 `fill` 生成填好的组件和来源摘要；这比只替换几个大标题更容易完成复杂组的全部内容。普通局部编辑仍用上面的 selective `replace`。
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_reuse.py" prepare-fill \
  --source "$WORK_DIR/source-slides/slide-07.xml" --ids <完整源组ID列表> \
  --output "$WORK_DIR/authoring/component-07.plan.json"
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_reuse.py" fill \
  --source "$WORK_DIR/source-slides/slide-07.xml" --ids <同一完整组ID列表> \
  --plan "$WORK_DIR/authoring/component-07.plan.json" \
  --output "$WORK_DIR/authoring/component-filled-07.xml"
```
在合页时给本页写与已填内容对应的讲稿，保留需要的来源署名。图表的系列、类别和新数值另用原生图表操作更新，按同一facts/派生表核对。


需要整体移入另一页或等比适配完整组件时，使用同一个仿射变换处理所有成员，避免只缩底形而保留旧端点坐标：
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_reuse.py" transform \
  --source "$WORK_DIR/source-slides/slide-07.xml" --ids <完整成员ID列表> \
  --x <组件目标左上X> --y <组件目标左上Y> --scale <统一比例> \
  --output "$WORK_DIR/authoring/component-v02.xml"
```
它完整变换节点、局部 SVG path、已支持的连线、字号与间距，保留字体、颜色、数据值、图片 token 和引用；旁边的 `.transform.json` 记录来源与比例。host 等仍未支持的对象会说明边界；可原位继承或改用合适的同族组件。

脚本的 brand_assets 和 content-skeleton 是候选外框，不覆盖上述人工视觉判断。脚本未归类的单页装饰、带文字的组件、图表仍从完整源页选取。

原生图表在导入后可能只显示占位图标。`overview.origin=original_pptx_local_render` 是原输入的本地渲染；`source_chart_render_required=true` 表示当前联图来自导入兜底或未得到原图，须取得原 PPTX 的真实渲染再判图型/布局。不能把导入占位当成模板没有数据图或只剩空框。本地已安装的 macOS LibreOffice 应被脚本识别，无需因 PATH 缺失再安装；无法本地渲染时仍结合原 OOXML 索引处理并说明视觉缺口。

L6 或其它含图表模板，先读 `template-index.json` 的原生图表索引及详情路径；导入丢失图表时仍可从原 PPTX 得到配置。解析失败可单独运行 `template_chart_inventory.py --pptx <源模板> --output <manifest/native-chart-inventory.json>`。它提供源图种、系列色来源、轴/图例与同页图表位置，省略示例数值/类别。结合源截图选一组适用图表并保留排列，不把每个小图拆成整页大图；如需改图种，记录本题缺少的维度或数据条件。新事实只取本题数据。

**L6 从源配置生成原生图，而不是只抄品牌色再重画。** 用 `template_chart_contract.py` 的 `build_chart` / `build_group`（或 CLI）选择真实 chart/group ID，显式传新数据与源系列/点色映射；保存到 `manifest/chart-contracts/page-NN.json` 和 `page-NN.bindings.json`，图表片段合入单页。保留原图所需的底形/容器，不能白底承载只适用于深底的源白字。原生表格与非数据封面/结尾有独立角色；group 可按数据调整节点数但保留原布局规律。用法见 [发布与恢复](tools.md#发布与恢复)。不支持的范围/复杂配置先看具体实现边界，再按完整源配置与 schema 处理或选真正自然适配的同源图；不能把实现限制变成丢分面、造范围数据或画数值色块的理由。

连续时间指标先检查模板的折线/面积或语义适配的组合图，横截面类别比较再选条形/柱形，小多图用于同指标分组对比。以实际数据条件选源图，保留系列/轴/图例职责；不为了类型数量增加没有意义的图种。

完整材料与逐页大纲的首要判断：是否已经给定每页的标题、数字、结论或指定目录。已给定则按 L5；“页数不限”只允许合理拆分，不能把已给内容降级为 L4 自由展开。将指定标题/目录和精确数字列为不可改字段；建议放到单独标明“建议”的内容中，不把推演出的名额、时长、年份或权益写成既定事实。

**制定逐页内容配方**：可使用 `page-plan.md` 或作者配方中的逐页记录，写清内容、用途、源组件和资料来源。复杂材料用事实表统一口径，已有用户大纲、CSV/JSON 计算结果可直接复用，不重复抄多份台账。L8 原稿索引保存全文、数据与备注，目标页保持一一对应。

制作前把本题的时期、指标和假设放到同一份轻量事实表。每个指标带 `label / unit / denominator / period / value_scale`；虚构数据和场景假设也有独立身份。标题、图表标签和讲稿引用同一记录，跨页复用时保持该含义。比较、极值和增长先计算成结果，再写结论：可用 `template_metrics.py compare` 得到差值/倍数，用 `matrix` 得到各行/各列极值与例外，用 `format` 按声明的单位与尺度生成显示文字。结果负责“发生了什么”；原因、作用机制和收益解释由本题证据支持。

流程或机制先用一个小关系表整理实体、状态/条件、分支、并行与反馈，再从模板选择表达同种关系的完整组件。箭头、节点和讲稿都对应这份表；分支图围绕判断点布置命中/未命中路径，反馈图明确返回目标，重叠时段的行动用并行关系组织。

数据题先将已计算的汇总与派生值保存到同一份派生表（CSV/JSON），注明源列、筛选范围、公式与权重。各页的图表数据、标签和结论从同一结果读取，不在每页重新手填一份数值；季度/城市/类别明细与总量在该表内核对。同比和差值保留未舍入值，最后才格式化。

派生数字记录同一套范围、时间、公式、权数和显示口径；以实际计算输出生成数值及标签，不把季度简单均值标成门店数加权年均。观察值、情景测算、建议目标分别标明，混合页面不用“均为情景估计”覆盖真实现状；没有绝对年份的动作沿用材料相对表述。实体、时期、方法名与类别按资料逐项核对，不把模板示例的分类或时期套到新题对象。用户要求实体图或作品素材时提供对应真实资料，装饰图片不替代内容证据。

比率差和同比使用未舍入的原始计算结果，最后才按展示精度舍入；排序结论核对实际城市/店型组合。讲解顺序按用户大纲或本题逻辑组织，不把演示顺序表述为实际的历史/因果先后。

每一页一行，顶部写 LINK、场景、目标页数、模板/原稿身份：

| 目标页 | role | mode | source / style_source | reuse | 适配动作或不适配原因 | facts / from_source |
|---|---|---|---|---|---|---|
| P1 | cover | fixed_template | slide-01 | 整页 | 换标题，保留水墨主视觉与标题字阶 | F1 |
| P2 | content | component_reuse | slide-07 | slide-07:c1 | 三阶段流程改为四阶段，复制完整节点、等距重排 | F2–F5 |
| P3 | content | component_reuse | slide-11 / slide-07 | slide-11:c2 | 借对比组与装饰曲线，整体移入 slide-07 内容区；标题样式取该区源槽 | F6–F9 |
| P4 | content | component_reuse | slide-12 | slide-12:c1 | 原生分组柱更新数据，保留系列顺序和图例 | data.csv 行2–9 |
| P5 | content | active_rebuild | slide-07 | - | 材料是交叉关系，模板只有串行流程；沿用框架与字阶自建关系图 | F10–F14 |

`mode` 三选一：
- `fixed_template`：整页能自然承载，包含结构页和内容页。整体继承，替换内容、适配节点数。
- `component_reuse`：整页不匹配但一个或多个组件可用。引用真实完整组件，保留其视觉规则；允许跨模板页借用，并整体移动/等比缩放后重新排版。
- `active_rebuild`：全稿没有自然匹配的整页或组件，或 L1/L9 无可编辑模板。保留选定 `style_source` 框架、文字层级和装饰语言后新建；写出具体的语义/容量/数据条件差异，不能只写“内容不同”。

内容组件按信息关系选择，复用整页或真实内容组，不以固定比例、模板页覆盖率或重复次数作为完成条件。L5 以内容完整性优先；纯文字页按阅读任务安排。只有信息数量不同先增删节点，信息关系不同才换组件。L6 保持数据表达，不能用数字卡替代图表。L8 不为了模板多加封面/目录、合并或拆页。

为首个内容页选择语义自然匹配、能检查主要组件的源页型；完成后与源图同屏核对内容结构、装饰和文字角色，再展开后续页。错落四组内容可承载四组并列论点，保留步进位置、底形和装饰，只换各组内容；大图配竖文可承载图文专题。L5 仍以已定材料为准，不凑条目。后续来源改变时同步更新 page-plan 的组件、member_ids 和具体不适配理由；记录实际选用的组件，不用原计划代替实际复用。

#### MainAgent 困难页优化

复杂组件/分面图的适配、文字容量、作品素材或已发现的视觉问题，由 MainAgent 在同一 deck 内诊断和修复。先确认来源与数据足够，再比较真实源页完整 XML/截图、本题 facts、当前页回读/截图及发布报告，定位具体差异。资料缺必要维度时合理换同源组件，不编数据；登录、目标 ID 或接口失败按原任务恢复，不重发或创建第二份 deck。

1. 从完整源组件和原文字槽开始修容量、对齐、遮挡、竖文或图表配置，保留已正确的装饰、字体角色和事实。作品图等比保留全貌；同指标小多图核对共同轴、单位、数值和新数据。
2. 在本页版本文件中准备修订，经 `template_publish.py` 原地更新真实登记 ID。source/layout/chart/style 记录可沿用诊断，不要求每次先补严格声明；需要核对外部编辑基线时先回读 `cache.xml`，再用 `--local-cache`，用法见 `tools.md` 的“发布与恢复”节。
3. 查看实际差异与受影响页截图，修真实遮挡、截断、缺图或错误数据。仅有服务默认字段/启发式误报时保留正确内容，留到全稿核对；平台限制反复出现时改用同源可读表达，记录仍未解决的具体问题。
4. 同步更新 page-plan 的最终来源与适配理由，继续完成其余页；全部页制作完成后由 MainAgent 导出并向用户交付，不以局部优化记录代替成稿。

内容页多样性仍是文档选型提示，过渡页统一，不新增页型数量/重复次数硬拦。

### Step 3 · 开工通知

`present_files` 交付 Step 1 拿到的 `lark.deck.url`。**必须放在思考过程之外的正文回复里**，让用户看到"PPT 已经开始制作，可以点击卡片关注进度"。这个链接和 Step 6 交付用的是同一个地址，两次都必须发。

### Step 4 · 上传图片

- **模板自带图**：Step 1 已抽 file_token 到 `template-index.json` 的 `assets_with_tokens` 字段，直接引用不用 `+media-upload`
- **新素材**（用户附件里的图/表、联网搜图产物、生图产物）：必须 `+media-upload --file <path> --presentation <lark.deck.xml_presentation_id>` 拿新 file_token；自己记着新 token 别丢，Step 5 写 XML 时引用

**整页图片背景**：预期作为整页底图的图片可用原生页面背景填充，避免只靠图片图层的存储渲染路径。保持素材原字节/来源标记，使用已上传的真实 token：
```xml
<style><fill><fillImg src="<file_token>" alpha="1"/></fill></style>
```
如果存储页截图黑底，但完整原 XML 的 content 预览和实际 PPTX 都显示正常，先区分渲染路径差异，不反复重生正确图片。可改为原生背景填充后核对实际图。图本身、数据图层和文字仍按原位置制作。

### Step 5 · 逐页适配与写入

先把整稿的内容、模板来源、版式和讲稿组成明确的逐页配方，再让脚本完成机械填充、迁移和发布。每页仍独立落 XML、检查、登记；执行器停在真实失败页，修复该页后从返回的页号继续。用 [内容配方](tools.md#内容配方) 的 `prepare/run` 执行已定配方，避免为长稿反复手写同一套操作。

配方中的新内容先完成讲稿，与图表和标签共用同一份已计算、已按单位格式化的 `values`。`fill` 的新文字和 notes 可用 `{{key}}` 引用它，减少数字、时期和单位被再次手打或改写。L8 配方保留原 notes，包括原稿的空备注。

**写页起点**：
- `fixed_template`：复制选定完整源页到 authoring，读取副本，替换文字/数据/内容图片。
- `component_reuse`：读取所选源页完整 XML，从主来源页或其外框开始，拷入 `reuse` 声明的完整元素组，保留 ID 对应和组内几何；同页 ID 冲突时确定性重命名并记录映射，不能只改 ID 伪装新建。所有必要连线、标签、底形、装饰一同保留。
- `active_rebuild`：可用 content-skeleton 起步，但先从完整源页补齐标题槽字阶、单页装饰和品牌框架，再按已记录的理由组织新内容。没有“至少删除多少元素”的要求。

结构页只换标题/章节名时从完整源页按 `fixed_template` 填槽。源标题由上下两个独立字框组成时，各字框分别换字；例如两源槽分别填“甲”“骨”，说明文字另写。保持源 `shape/p/span/vert` 结构，不合并成 `ea-vert` 的多个段落——竖排中的段落可能变成从右到左的多列。确需改变构图才记 `component_reuse` 并保留完整组件；仅换文字不需要重建字框。

**先核对组件隐含的断言**：矩阵的象限标签、时间线的先后、金字塔的层级、箭头的因果也属于内容，必须有材料依据。例如只有“已完成巡检”不能推成“紧急但不重要”，只有单期复购率不能写“持续提升”；材料未提某类事项不能写“暂无”。时间范围重叠的事项不强行排成先后。缺少这些依据时，选择同模板内的中性并列组件，或保留框架与装饰做同族新建，在去向表说明不用原因。

`template_disposition` 要求每页有判断，**不要求每个组件都用上**。L4 的复用比例只统计适配后的实际内容页，不能重复同一组事实增加复用分子。用户未限定页数时，五条事实不必拆成五页；页数由不同读者任务决定。保留组件造型与文字层级，按内容容量调整整体高度和间距，避免一行文字悬在巨大空卡里。

**组件适配顺序**：
1. 判定信息关系：并列、顺序、层级、对比、比例或趋势。组件必须表达同一种关系；项目数相同不代表语义适合。
2. 只更换可变槽内容；多/少一个节点就复制/移除完整节点并重排连线与间距。图文模块中照片换掉时，保留边框、题签和说明布局。
3. 空间不够时先压缩冗词，保持事实与模板字阶；再调整组件整体尺寸或拆页（L8 不拆）。多余图表没有数据就移除，按已有事实补相关组件或重排余下图表，不虚构数据填空。
4. 仍不能承载时换模板内其它组件；确实没有才同族新建，并保留原因。不要把复杂组件拆散后重新拼成通用卡片。

**完整资料与自然表达**：模板的原诗/故事只用作视觉样板，新题用真实内容重新写，不保原格律/句法。文献先弄清实际测量项目、回归方式、B/β与预测/因果范围，再写简明讲解；不要把一般教科书列表当成该文测过的项目。方案/报告读取全部段落与表格后形成内容提纲，尤其后半的建设任务、交付物和部署选型；只讲推广阶段不能代替建设路线。已有资料能回答的内容不默认扩新事实，引用机构不替换。

图表数据先从原材料用代码汇总，标题与图例用同一结果。长类别名用语义换行或独立完整标签，不让绘图器自动省略；近邻数值标签扩大绘图区/错开放置，不缩小到不可读。统计存量、期间流量、季度与年度使用正确口径；绝对增量和增长率分开，不能把“增长最快”写成“新增最多”。加权/简单均值按实际计算说明，不用模板词或先验替换。

填入目标语言后，按文字角色适配容量。横排标题或标签末尾仅剩一个字、一个括号或缩写落到下一行时，先精简标题或把缩写/补充说明移到正文；需保留原文的 L8 用合适宽度与语义断行保留全文。确实需要两行时，给完整“标题＋说明”组件留足高度，并相应移动下方说明，不能只增大标题框。`shape-auto-fit` 只扩展自身，不会移动兄弟元素；警告已指出 growing would reach 下方文本时，原位加高不能解决遮挡。多行中文正文保持合适行距与模板字阶，容量不足时调整完整节点或换同族组件。数字、年份和短标签先确定一行可读的字框，再安排说明。首个典型内容页同时核对原构图、完整本题文字和讲稿，完成这一个真实适配页后再展开其它页。

文字框的可用区按真实形状计算。圆/椭圆的内框比外接矩形小，默认内边距还会吃掉容量；先用 `template_text_fit.py prepare --source <作者副本> --ids <文字容器ID> --output <新副本>` 调整选中容器内边距并得到容量建议。它保留文字、字号、几何和讲稿，给的是启发式估算；用典型页截图确认。仍放不下时按返回的 `needed_bbox` 调整完整节点或改选同族组件，不将标签逐字挤成竖列。

**固定页与容量**：`fixed_template` 固定的是原页构图，不能仅因“更居中”“更好看”移动标题、署名或装饰。条目增删时只在原条目区重排，保持标题和品牌框架在原位。长文本先按原可用区换行/精简冗词；检查图片区压住的部分不属于文字安全区，背景容器或前景装饰遮挡的区域不属于文字可用区，换行不能挤出有效文本区域。真正需要改变构图时改记 `component_reuse` 并记录移动的组件与原因，不伪称整页固定。

**内容页多样、过渡页按需要使用**：过渡页统一风格，但不为沿用模板页数或凑目标页数机械插章页。需要章节切换时，让主体区域有醒目的章节标题/导览；只有小页眉、正文空着的骨架不能当成完成的章页。可以把章标题并入该章第一张内容页，页数预算用于真实资料。内容组件按关系复用，不要求每种源页都用一遍；同指标比较保持一致形式。

**装饰和文字**：装饰不因“不是跨页品牌资产”而删除；固定页保持装饰位置尺寸。组件迁移时允许整体移动/等比缩放，不拉伸水墨、作品或人物。按标题/正文/标签分别继承字体、字号、字重、文字色，不能统一用频次最高的字体。跨页可复用章节装饰、logo、背景与小装饰，内容照片按内容使用。

先从完整源页更换内容槽，保留承载内容的装饰组合。例如圆环与节点、错落题签与底形、山水图与图片区共同构成版式时，复用整组，不只留下外框。源装饰有意越界可直接选择 `--no-lint`；需要精确排障时再用工具说明中的可选出血诊断，不先挪动或清空正确装饰来清零告警。作品图放不下时先调整内容槽或迁移完整组件；确实语义不适配才改选同源页型，并写明原因。

**图表遇到导入限制**：源页的图表若读成 `undefined`、host引用或只读对象，回看源页截图及 PPTX 图表结构，记录原图种、系列顺序、标注、轴、图例和分面布局后重建。限制改变的是对象实现，不是只提取配色后另选通用图。比如模板按地区分面且本题也有城市/店型维度，应优先保持小多图结构；若数据缺少原图必需维度，说明差异并选同族的合适图种。没有范围/预测/构成数据时不造范围图、预测或堆叠。

**图表**：优先改原生 `<chart>` 的数值、类别及标签，保持图种和样式；转换不支持时才按模板重建可编辑图表。`chartField` 数值使用英文逗号分隔，值数与类别数匹配，核对单位、正负号、系列名和零值；模板类型与数据语义冲突时选同模板内正确图种并说明，不能为了模仿曲线编造趋势。原生图表的变更先获取对应 schema/示例，新增组件遵循 XML 语法。

图表最终要能读到单位、数值或清晰刻度，堆叠图要能识别各系列。源示例隐藏值或刻度时，用显式 `data_labels`、`value_format`、`legend` 覆盖隐藏配置；同一指标的小多图用 `build_group(..., value_axis={"shared": True, "include_zero": True, "format": '0.0"%"'})` 共用由本次数据算出的轴界（百分数已为 11.8 时用此字面百分号格式；0.118 用 `0.0%`），详见 `tools.md` 的“发布与恢复”节。不同单位/口径不合并轴；不改数据迎合源图数值范围。完成后截图核对同值同长、较大值确实更长及系列名称可辨。

把每个指标的名称、单位、分母/口径和前后时段连同已计算端点保存到 `computed-metrics.json`，用 [`template_metrics.py values`](tools.md#共享指标显示值) 生成共享显示字符串与算术收据。正文、表格、图旁结论和讲稿从同一份 `values_file` 填值；数量、次数和资金状态也保留来源完整单位或原句。图组按单位、口径与时段选共同轴或分面，数值图从当前数组用原生图表或chart库生成。流程先列触发、判定、执行、完成节点和分支，再按节点ID连线；时间目标放在实际被测量的阶段。

#### L8 原稿迁移

L8 交付前逐页比较原稿与成稿的可见文本、表格单元格、图表标签/数值、符号和备注；短标签、重复KPI、模板英文眉标也计入新增文字。`from_source` 必须一一对应，不用只核对长段正文的方法漏掉这些变化。

**L8 从原稿内容树组成迁移稿。** 一条命令准备完整原生源树：
```bash
SOURCE_DIR="$WORK_DIR/original-source"
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_migration.py" prepare-source \
  --source-pptx "$WORK_DIR/<original>.pptx" --work-dir "$SOURCE_DIR" \
  --authoring-work-dir "$WORK_DIR" --deck-title "<本题原稿工作副本>" --as user
```
有已验证的原备注sidecar时加 `--notes-json`。 source产物位于 `SOURCE_DIR`；返回配方的源SML用绝对路径，图片绑定相对声明的作者 `WORK_DIR`。在此作者目录运行配方和发布，目标模板frame与源选择仍来自各自完整索引。它只导入独立完整source工作副本，保存原包字节、全部原生单页/全局样式、真实媒体、原备注与按原页序的migration配方；原source deck保持全页。目标模板仍独立跑 `parse_template.py`。由返回配方填目标 `frame/frame_ids/target_region/role_styles` 与 `publish_source`，原文、公式和图片来自已经准备的源树。先与原PPTX/源渲染核对图示、媒体和备注，导入收据中有具体差异时针对原对象处理。选定目标模板的视觉壳（背景、空容器、装饰）后，用 `template_migration.py inventory` 盘点原稿事实成员；`compose` 直接复制原p/span、表格单元格、图表数据、信息图片和原note，移动到目标内容区。标题/正文/图表可分组放入各目标槽，`role_styles`只调整其字体/色彩/字阶，内容不再人工重录。原稿note为空时，组合结果也保留为空。

原稿有 SVG 图片且导入后不便迁移时，先用 `template_import_source.py --source-pptx <原稿> --output-pptx <工作副本> --report <JSON>` 选择原图片自带的 PNG/JPEG fallback，再导入这份工作副本。它保留完整图片对象、位置、裁剪、原媒体与关系，记录原 SVG/fallback SHA；与原图核对分辨率和外观。列表标记依赖旧符号字体时，可显式提供 `--bullet-char '•'` 采用目标列表样式，正文、代码和公式内的符号保持原值。原稿与格式选择收据一同保留，不删除信息对象来重建基线。
L8 重排采用 `component_reuse`，目标视觉壳与原稿事实分别指定；`fixed_template` 适合保持原页构图的换字。`role_styles` 自动保留局部高亮、符号字体和代码字体，并按比例保留大小字阶。原生有序列表在导出前显式化每个段落起点：L8 的 compose/配方用 `explicit_numbering: true`（CLI `--explicit-numbering`）；它按原、新列表实际编号比较等价，原文、顺序与层级保持。其他新稿可用 `template_list_layout.explicit_numbering` 处理作者副本，使 A/B/C 等选项稳定导出，而不是依赖列表默认起点。
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_migration.py" inventory \
  --source "$SOURCE_DIR/original-slides/slide-01.xml" \
  --output "$WORK_DIR/manifest/original-content-01.json"
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_migration.py" compose \
  --source "$SOURCE_DIR/original-slides/slide-01.xml" \
  --frame "$WORK_DIR/authoring/target-frame-01.xml" --frame-ids <无示例内容的视觉壳ID> \
  --placements "$WORK_DIR/authoring/migration-regions-01.json" \
  --explicit-numbering \
  --output "$WORK_DIR/authoring/slide-01.xml" \
  --contract-out "$WORK_DIR/manifest/migration-contracts/page-01.json"
```
`placements`是组列表，每组含 `ids` 与 `target_region:[x,y,width,height]`，完整覆盖原事实成员；将标题和各内容组件分别放入目标区域，比整页统一缩小更易读。同源图片换为本稿上传token时在bindings登记实际 `media` 映射，元素ID变动用 `ids` 映射。`compose`生成源绑定合同，发布时检查实际内容和原notes；导入已经丢失的原信息先从原PPTX/渲染补回，再生成迁移起点。

原稿图表的标题、单位和图例按**可见基线**检查；`c:title` 缺失不等于没有标题，单系列可能由 `autoTitleDeleted` 与系列名生成自动标题。导入丢失可见标题/单位时恢复原稿原有文字，不能只核对缓存系列名与数字而认为视觉也守恒。

**文字与备注**：替换全部旧示例事实，检查图内文字；联系方式等未知就删槽，不造“示例”。通常给本页写 3–5 句讲稿；L8 只保留原备注，原稿无备注则留空。

追加新页必须去掉 slide 根 id；源元素 id 可保留，单页内唯一。源 XML/图表数据是复用证据，不用“改掉 ID”来躲检查。首个典型适配内容页核对源图与目标截图后再扩展；其余首稿正常页不逐页截图；诊断留到全稿检查；怀疑未写入、缺图或实际内容错误时及时核对当前页。

#### Step 5 · 连续发布完整稿

单页用 `template_publish.py`，多页已准备好时用 `template_authoring_plan.py` 的 ready 配方列真实文件路径统一 run，省掉逐页手拼命令与文件名。默认检查是诊断：源几何/样式、槽位/图表/迁移合同、密度和文字估算不作为发布许可；用户要求或确需精确排障时才加 `--strict`。

```bash
LARK_SLIDE_CANVAS_W="$DECK_W" LARK_SLIDE_CANVAS_H="$DECK_H" \
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_publish.py" \
  --presentation "$DECK" --work-dir "$WORK_DIR" \
  --xml "$WORK_DIR/authoring/slide-01.xml" --page 1 --mode component_reuse --link "$LINK" \
  --slide-id "<导入副本保留的真实首页ID>"
```

逻辑第1页没有显式目标或登记时，发布器会尝试复用当前 deck 唯一的空白保留页；只有确认无内容才更新其真实 ID，其他情况照正常路径，不覆盖已有内容。原始作者 XML 的 slide 根 id 与目标冲突时应去掉来源 id 后再发布。

source/layout/chart/style 参数有现成材料可提供，以便复用和诊断，不要求每页先填一套校验 JSON。已登记页按真实 ID 更新；补页按逻辑页号插入后页之前。`published` 表示业务 ACK 已写入并登记，继续后页；`needs_final_review`、`first_difference` 和视觉 warning 是可选诊断，不要求额外成稿检查，不对每个服务默认字段反复恢复。

**直接跳过误报**：正常写入若被视觉/模板兼容 lint 拒绝，判断后原命令直接加 `--no-lint`，可选 `--reason "原模板装饰出血/已核对视觉"`。它跳过本地视觉预检及服务 lint，无需先造声明文件。写入还须拿到真实业务 ACK；实际 API 拒绝、无效单页 XML、写错目标仍不能算成功。旧 `--exception-file` 与 `--source-decorations` 只作可选严格/诊断用法，见 [发布与恢复](tools.md#发布与恢复)。

只有真正未拿到写入 ACK 的 unknown 才保留 pending、按原目标只读确认，避免重复追加；不要对后续所有页循环套同一个恢复参数。已 ACK 的内容差异在整稿实际回读/视觉中核验，不锁住整个制作流程。

**内容先于规则**：以模板视觉语言为起点，容量需要时可以调整完整内容组件的位置、尺寸和字阶，不为形式上的 fixed_template 声明来回回滚。数据、正文、图例和原素材信息保留；真实遮挡/截断最终要修。画布不同时用 `template_reuse.py transform` 完整等比变换坐标、局部 path、字号、线宽等，不手写只缩外框的正则。

### Step 6 · 交付

1. **确认残留页清扫结果**：仅 Step 1 启动了补删任务时检查它的回执/日志，并回读实际页序确认残留 ID 已消失。使用该任务的进程/会话句柄等待完成；不要按裸 PID 循环无期限等待，也不把进程消失等同于删净。仍有失败 ID 时只补删这些残留对象。
2. **核对登记再导出 PPTX**：运行
   ```bash
   python3 "$LARK_SLIDES_SKILL_DIR/scripts/multiagent_sync.py" export \
     --deck "<lark.deck.xml_presentation_id>" --cwd "<任务 CWD 绝对路径>" --who solo
   ```
   这里仅调用 `multiagent_sync.py export --who solo` 的单任务导出入口，文件名保留兼容；不调用角色判断或派单。登记/页序差异默认给出审阅提示，`--strict` 才阻断。`look` 中的图片页或 warning 不等于实际失败，也不触发额外校验；全部页面写入完成后导出并交付。真实页有修改时重新导出最新文件，不循环导出只为让提示列表为空。
3. **交付**：MainAgent 用 `present_files` 同时交付在线链接与最新 PPTX，说明完成情况及已确认的限制。本轮交付后停止额外自发修改；用户后续要求修改时，按新一轮编辑回读原稿、原地修订，再导出并交付最新版本。

## 不要做

- 不派子代理审查或做页；不用 python-pptx 改本地 PPTX 代替飞书 deck。
- 不用一个空壳和同一段文字机械套全稿；整稿执行器消费明确的逐页内容、来源与版式配方。
- 视觉/模板兼容误报按 [发布与恢复](tools.md#发布与恢复) 选择 `--no-lint`；实际 XML、目标 ID 与未知写入按真实结果处理，不伪造登记或完成状态。
- **保留模板装饰语言与叠放关系**，内容图不占用装饰槽；L9 参考中有烘焙文字时可清字取得同构图背景，保持其特色图形与纹理。
