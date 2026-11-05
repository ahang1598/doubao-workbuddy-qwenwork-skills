# 模板遵循工作流

用户提供 PPTX / 在线 Slides 作为模板并要求据此制作演示文稿时走本流程。

**核心原则**:**模板适配内容,不是内容适配模板**。模板只提供视觉资产(组件 + 色系 + 字体),核心目的是把用户信息表达清楚、表达漂亮。不要为"保留模板"强行让内容适配组件 · 更不能跳过模板适配报错。

**本地电脑模式**：按 `SKILL.md`「权威经验」中的运行环境规则判为本地电脑时，读完本文档后必须完整 Read [`local-compat.md`](local-compat.md) 与（若 Windows）[`windows-compat.md`](windows-compat.md)。


## 一、执行方式

MainAgent 负责解析模板、制定 plan、开工通知、图片上传、逐页生成和成稿交付。使用 Step 1 导入后保留的同一个 `lark.deck.xml_presentation_id` 作为交付目标。

默认流程在写入成功后直接交付。仅当用户明确要求额外审查、复验或生成后优化时，才启用第四、五节的 Organizer 可选流程。页数、原稿附件或保留数字/事实的要求不触发 Organizer。

## 二、CWD 与产物目录
始终停留在任务开始时的 CWD；所有产物写入 CWD 内的独立目录：
```bash
LARK_SLIDES_SKILL_DIR="<包含当前 SKILL.md 的绝对目录>"
WORK_DIR=".lark-slides/template/<deck-or-task-id>"
mkdir -p "$WORK_DIR/manifest/slides" "$WORK_DIR/assets" "$WORK_DIR/thumbs" "$WORK_DIR/source-slides" "$WORK_DIR/authoring"
```
Skill 脚本始终通过 `$LARK_SLIDES_SKILL_DIR/scripts/...` 调用。

## 三、MainAgent 流程（6 Steps）
### Step 1 · 解析模板 + 复用为交付 deck
一条命令跑完解析 + 导入 + 清空到 1 页:
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/parse_template.py" \
  --pptx "$WORK_DIR/<template>.pptx" \
  --work-dir "$WORK_DIR" \
  --deck-title "<用用户主题命名,例:L 医药流通企业数字化转型的经济效果研究>"
```
**拿 pptx**:用户传的是在线 Slides(`/slides/` / `/wiki/`)先 `lark-cli drive +export --token <token> --doc-type slides --file-extension pptx --output-dir "$WORK_DIR"` 导出成 pptx;wiki 链接先 `lark-cli wiki spaces get_node --params '{"token":"<wiki_token>"}'` 取 `obj_token`。

**从 stdout JSON envelope 解析并记住的字段**:

| 字段 | 用途 |
|---|---|
| `lark.deck.xml_presentation_id` | 后续所有 `+add-slide` / `+update-slide` / `+media-upload` / `+screenshot` / `safe_update_slide.py` 都用它 |
| `lark.deck.url` | Step 3 开工通知 + Step 6 交付 |
| `lark.deck.first_page_slide_id` | 清空后保留的第 1 页 id;Step 5 第 1 页必须用 `+update-slide --slide-id <这个>` 覆盖 |
| `lark.deck.first_page_state` | `"blank"` = 已清空成空白;`"template_remnant"` = 清空失败留了模板首页(非致命) |
| `lark.deck.purge_failed_slide_ids` | **若存在(非空数组)必须补删** —— parse_template 主删除阶段用"一趟扫无重试"策略,撞 rate_limit 的页会跳过并列在这里 |
| `capability_level` | `full`/`degraded`/`minimal` 三档 |

**⚠️ Step 1 立即善后:补删残留页**

如果 stdout 里 `lark.deck.purge_failed_slide_ids` 非空(常见于 100+ 页模板),**Step 2 之前必须补删**,否则用户看到的 deck 会残留大量模板页:

```bash
# 从 stdout JSON 拿 purge_failed_slide_ids 列表 · 后台跑 purge_deck.py 慢速清扫
FAILED_IDS="<用逗号分隔的失败 slide_id 列表>"
python3 "$LARK_SLIDES_SKILL_DIR/scripts/purge_deck.py" \
  --deck "<lark.deck.xml_presentation_id>" \
  --work-dir "$WORK_DIR" \
  --slide-ids "$FAILED_IDS" \
  > "$WORK_DIR/.purge_deck.log" 2>&1 &
echo $! > "$WORK_DIR/.purge_deck.pid"  # pid 落盘 · 后续 tool call 里读回
```

- `purge_deck.py` 用 **pace=1s(1 QPS)**,不撞 rate_limit,单页 ~1.6s,60 页约 1:40 稳定清完。
- **后台跑,不阻塞 Step 2**。MainAgent 直接推进 Step 2 制定 plan,purge 后台清残留。
- Step 3 只是发工作卡片链接(deck 还是空的),不需要等 purge。**Step 6 交付前**从 `.purge_deck.pid` 读 pid 并 wait,避免用户点开看到模板残留。
- purge_deck.py 失败也不阻塞主流程:残留页 MainAgent 后续 `+add-slide` 时不受影响,仅视觉上多几页。

**MainAgent 全流程只需要 Read 3 类产物**：

| 产物 | 何时 Read | 用途 |
|---|---|---|
| `manifest/template-index.json` | Step 2 一次 | **唯一轻量索引**:含 stdout envelope 关键字段 + 每页 200 字文字预览(`slides[N].preview_text`)+ `overview.paths`(数组,大 deck 会分片成多张 jpg)+ `visual_language`(主色 palette + 字体族,规则 5.2.1 硬性保留)+ `assets_with_tokens`(模板自带图 file_token 清单,Step 5 引用图片从这里取,不需要重传)+ 每页 `content_skeleton_path`(active_rebuild 页的干净起点) |
| `thumbs/overview*.jpg` 或 `.pdf` | Step 2 一次 | 全稿联图;从 `template-index.json.overview.paths`(数组)按顺序 Read 所有分片;大 deck 会分成 `overview-1.jpg`/`overview-2.jpg`/...(每张 ≤ 3800px 保证 Read 工具能读);Read 工具对 JPG 和 PDF 都支持,不需要强行转格式 |
| `source-slides/slide-NN.xml` | Step 5 每页写入前（**仅 fixed_template 页**） | 该页导入飞书后的完整 SXSD，是 cover/toc/chapter/transition/ending 每页 authoring/*.xml 的起点。**active_rebuild 内容页不 Read source**，直接 cp `template-index.json.slides[N].content_skeleton_path`（brand_assets only 干净骨架，见 Step 5 「写页起点」）|

`capability_level=minimal` 或 `overview.ok=false` 时，跳过看 overview，直接 Read `source-slides/slide-NN.xml` 反推每页结构。

**当解析模板时间较长时,可以先进入 Step2**:解析模板可能超过 5 分钟,可异步进入 Step 2 读文档 + 收集资料,制定 plan 时再等解析结果

### Step 2 · 读 style + 制定 plan

**选定 style · 一次 Read 拿到目标文件**：根据用户诉求从下表匹配唯一主场景，然后完整 Read 对应 `style/*.md`（Step 5 每页决策的依据）：

| 场景 | 典型诉求 | style 文件 |
|---|---|---|
| 分析决策 | 咨询、金融、行业研究、战略、市场机会、商业分析、投资分析 | [`../style/strategy-and-analysis.md`](../style/strategy-and-analysis.md) |
| 商业提案 | 营销方案、销售提案、融资路演、招商/招投资、产品提案、商业计划书 | [`../style/business-pitch.md`](../style/business-pitch.md) |
| 管理汇报 | 工作汇报、项目复盘、季度总结、OKR、管理简报、职业培训 | [`../style/business-review.md`](../style/business-review.md) |
| 学术研究 | 研究生课题、论文答辩、科研项目、开题/中期/结题报告 | [`../style/academic-research.md`](../style/academic-research.md) |
| 教育培训 / 科普 | K12 课件、教学演示、患者教育、专业科普 | [`../style/learning-and-training.md`](../style/learning-and-training.md) |
| 技术工程 | 工程方案、架构评审、研发报告、AI / 数据 / 运维 / 安全 | [`../style/technical-presentation.md`](../style/technical-presentation.md) |
| 品牌 / 创意 | 品牌故事、设计提案、作品集、文化活动、人物介绍、影片艺术品介绍 | [`../style/brand-storytelling.md`](../style/brand-storytelling.md) |

优先级例外：
- **模板中的 配色 / 字体** → 以模版为准，忽略 style 文档里冲突的视觉细节
- **不匹配任何场景** → 回退 [`../style/fallback.md`](../style/fallback.md)（信息密度极高的图文卡片布局）

**收集材料**：
- 用户附件（docx / pdf / xlsx / doc）：docx 必须 `doc.tables` + `doc.inline_shapes` + `unzip word/media/`，pdf 必须 `fitz.get_images` + `fitz.find_tables` + `page.get_pixmap`，doc 必须转成 docx 之后进行图片等信息提取；只跑 `paragraphs` / `pdftotext` 会丢关键信息。**图/表/数字/事实必须完整提取**。
- **文本/图片来源默认规则**：
  - 用户提供了附件或资料 → **只用用户的**，禁止用搜索/生图工具扩写
  - 用户未提供附件或资料或指定来要扩展 → 走搜图 / 生图 / 联网搜索获得真实素材
  - **模板里的文本和图片默认不使用**（除非用户明确要求保留模板的某句话或某张图）—— 模板示例文字、图片都是占位符，与用户主题无关

**扫模板**:Read overview(按 `template-index.json.overview.paths` 数组顺序 Read 所有分片)+ Read `manifest/template-index.json`(含每页 200 字 `preview_text`)。目标是**心里有数**:
- 主色 palette（照搬 `template-index.json.visual_language.primary_colors`）
- 字体族（照搬 `template-index.json.visual_language.fonts_used[0].name` 或 `fonts_declared`；见规则 5.2.1）
- 跨页复用的品牌资产（Logo / 页脚 / 页眉 / 导航条 / 水印 / 背景图 —— 通过看 overview + source-slides 找出 shape id 和 file_token）

内容页只保留以上这些，其余的无关图片、占位文字全部删掉

**落 page-plan.md**：一份完整的施工清单，**顶部先记录 style**，再落每页表格：

```
Style: academic-research
```

每一页一行：

| 目标页 | 页形 | 页型策略 | 来源模板页 | 来源 XML | skeleton_ref | 使用的 style 内容 | 要填的新内容（含要保留的数字/事实）|
|---|---|---|---|---|---|---|---|
| P1 | cover | fixed_template | slide-01 | source-slides/slide-01.xml | - | - | 标题=xxx；副标=yyy；院系/专业/答辩人/导师元信息 4 项 |
| P2 | toc | fixed_template | slide-02 | source-slides/slide-02.xml | - | - | 4 章名（模板 6 章，删 2 个 + 调间距） |
| P4 | content | active_rebuild | slide-07 | source-slides/slide-07.xml | - | style academic KPI 数字带（46/13/11 字号）+ 来源脚注行 | 3 大 KPI（10% / 26,000㎡ / 6,000+）+ 4 步驱动力（政策/效率/挤压/升级） |
| P5 | content | active_rebuild | slide-07 | source-slides/slide-07.xml | **P4** | 同 P4 | 另一组 3 大 KPI |
| P6 | content | active_rebuild | slide-11 | source-slides/slide-11.xml | - | style academic 三线表（4 行 × 2 列：CORE INSIGHT / REPRESENTATIVE AUTHORS）+ 底部 GAP 3 编号条 | 4 大研究维度 × 每维 3 位代表学者引用；3 大 GAP |
| P7 | content | active_rebuild | slide-11 | source-slides/slide-11.xml | **P6** | 同 P6 | 另一维度的 4 项研究 |
| ... | ... | ... | ... | ... | ... | ... | ... |

**列填法**：

- **页形**：`cover` / `toc` / `chapter` / `transition` / `ending` / `content`
- **页型策略**（决定 Step 5 走 5.1 还是 5.2，二选一）：
  - `fixed_template` → cover / toc / chapter / transition / ending 一律走这个 → 规则 5.1（只改文字 + 数量 + 少量位置适配，其余版式全保留）
  - `active_rebuild` → content 页走这个 → 规则 5.2（只保 brand_assets，禁止使用原slide的其余任何元素，其余所有元素走 style）；**注意两个章节过渡页之间必须有内容页**
- **skeleton_ref**（只对 `active_rebuild` 页有意义，`fixed_template` 一律填 `-`）：
  - **默认填 `Pn`（复用前一同版式页的骨架）** —— 除首个建立此版式的页外，每个 active_rebuild 都应指向前一个同版式基线 Pn（Step 5 会走"直接 Write from memory"路径，不重复读 source，省 context 也快）
  - 填 `-` 是**例外** —— 仅当**首次建立此版式**时才填（后续遇到"从 KPI 卡切到三线表"这种版式跳变，新版式的第一页也是新基线填 `-`）
  - **判"同版式"**：来源模板页相同 + 使用的 style 内容相同 + 主视觉容器（KPI 数字带 / 三线表 / 卡片阵列 / 时间线 / 等）结构一致
  - **每种版式一个基线，其他全指过来**：如 P4 KPI 卡=基线填 `-`、P5-P7 都是 KPI 卡都填 `P4`；P8 换三线表 → P8 新基线填 `-`、P9-P10 填 `P8`
  - **不填 `Pn` 而填 `-` 需要显式理由**（page-plan 的「使用的 style 内容」列写清楚"新版式：xxx"），否则默认应该复用
- **使用的 style 内容**：`active_rebuild` 页必填，具体到 style/*.md 里的哪种表达（"academic KPI 数字带"、"academic 三线表"、"SVG waterfall 图"）；`fixed_template` 页填 `-`；skeleton_ref 指向其他页时可以填 "同 Pn"
- **要填的新内容**：写明所有关键数字/事实（防止后续丢失原稿数据的唯一保障）

### Step 3 · 开工通知

`present_files` 交付 Step 1 拿到的 `lark.deck.url`。**必须放在思考过程之外的正文回复里**，让用户看到"PPT 已经开始制作，可以点击卡片关注进度"。这个链接和 Step 6 交付用的是同一个地址，两次都必须发。

### Step 4 · 上传图片

**图片上传**：

- **模板自带图**：Step 1 已抽 file_token 到 `template-index.json` 的 `assets_with_tokens` 字段，直接引用不用 `+media-upload`
- **新素材**（用户附件里的图/表、联网搜图产物、生图产物）：必须 `+media-upload --file <path> --presentation <lark.deck.xml_presentation_id>` 拿新 file_token；自己记着新 token 别丢，Step 5 写 XML 时引用

### Step 5 · 流式生成

每页闭环：**落 XML → 带 `--no-lint` 写入 → 确认成功 → 下一页**。

**🚫 严禁批量生成 XML —— 每页必须独立走一次 Edit 或 Write 工具调用**。批量生成会跳过 harness 的 read-before-edit 追踪，直接导致后期页面质量崩塌（文本没替换干净、id 没删对、note 位置错、样式属性丢失）。以下 4 种 pattern **一律禁止**，就算跑一次也算违规：

1. **for 循环处理多页 slide XML**：`for i in 04 05 06; do cp source-slides/slide-$i.xml authoring/...; done` / `for sid in pQx pQy pQz; do sed -i ... done` —— 不管循环体里写什么，只要在一条 Bash 里对多个 slide 文件做修改，都禁止
2. **单条 Bash 里 cp + sed 链**：`cp source X && sed -i 's/A/B/' X && sed -i 's/C/D/' X && sed -i 's/E/F/' X ...` —— 5 条以上 sed 串起来实际上就是脱离 Edit 追踪的批量改，必须拆成正规的 cp + Read + Edit
3. **python -c 内嵌多文件循环**：`python3 -c "for f in ['s04.xml','s05.xml','s06.xml']: ..." ` / `python3 -c "notes = {'04':..., '05':..., '06':...}; for i in ...: ..."` —— 一段 python 内联脚本改多个 slide 文件都禁止
4. **heredoc / cat + note 拼接批量灌页**：`for i in ...; do cat > slide-$i.xml <<EOF ... EOF; done` —— 直接落盘绕过 Write 工具，禁止

**合法路径只有两条**（跟 Step 5 「写页起点」的三条路径对齐）：
- **fixed_template 页 / active_rebuild 首基线页**：cp source → **Read authoring**（一次工具调用）→ **Edit authoring**（一次工具调用改一处，需要多处改就多次 Edit，允许连续多个 Edit）→ 单页 `+add-slide`
- **active_rebuild 复用基线页（skeleton_ref=Pn）**：**Write authoring**（一次工具调用从零落文件）→ 单页 `+add-slide`

**判断"是否越界"最简判据**：本条 Bash 里出现 `for` / `python3 -c` 且里面涉及多个 slide 文件路径 = 违规；本条 Bash 里 `sed -i` 出现 ≥ 5 次或替换多个 slide 文件 = 违规。发现自己写出这种命令立刻停手，拆成一页一次 Edit/Write。

**写页起点**（按 page-plan 该行的 `页型策略` + `skeleton_ref` 分三条路径）：

**骨架复用规则**：如果这是 active_rebuild 页且**前一 active_rebuild 页版式相同**（来源模板页相同 + style 内容相同），那么本页 skeleton_ref 就应该指向前一页（复用骨架）。**默认走复用**，只有版式真跳变才回退基线路径。**不复用 = 重复读一份几乎相同的 XML,浪费 20-80 KB context**。

三条路径:

- **active_rebuild 页且 skeleton_ref = `Pn`（默认 · 复用 Pn 骨架）**：**不 cp、不 Read source**。**骨架来源**：context 里还能看到 authoring/slide-<Pn>.xml 的完整正文？能看到就直接 Write from memory 只替换内容字段；看不到（compact 掉了）就先 Read authoring/slide-<Pn>.xml 一次再 Write。Write 前不需要再 Read —— "Edit 前必须 Read" 的约束只对 Edit 生效。写完直接用 `+add-slide --no-lint` 写入。
- **active_rebuild 页且 skeleton_ref = `-`（例外 · 首个建立此版式的基线）**：**cp `content_skeleton_path` → authoring/slide-NN.xml**（从 `template-index.json.slides[N].content_skeleton_path` 取，通常是 `manifest/content-skeletons/slide-NN.content-skeleton.xml`）→ Read authoring 副本 → 按 style 文档的表达规则 Edit 填内容 shape → 写入。写完这页 authoring/slide-NN.xml 就是**版式基线**供后续同版式页复用。**注意**：MainAgent 按 style 文档直接完成内容表达、信息层次和视觉设计。
  - 🚫 **禁止 cp source-slides 作为 active_rebuild 起点** —— source 里的内容占位符会诱导模型"生搬硬套"。content-skeleton 只含跨页复用 brand_assets（背景/页眉/页脚/装饰线），是干净起点。
  - `content_skeleton_path` 为 null（模板未识别到跨页 brand_assets）时才回退 cp source，但**写入前必须删掉 60%+ 的 source shape**（保留背景 + 页眉 + 页脚，其余全清）。
- **fixed_template 页**（cover / toc / chapter / transition / ending）：`cp source-slides/slide-NN.xml authoring/slide-NN.xml` → **只 Read authoring 副本** → Edit。**禁止先 Read source 再 cp** —— source 与副本内容完全相同，重复读会把同一份 XML 塞进 context 两遍。

**slide 根元素 `id` 属性**：第 1 页(走 `+update-slide` 覆盖)保留 id 无影响;第 2 页起(走 `+add-slide` 追加)**必须删掉根元素 id**,否则 `+add-slide` 会撞 id。子元素 id 一律不动。

#### 规则 5.1 · fixed_template 页（cover / toc / chapter / transition / ending）

这类页承担整份 deck 的品牌辨识度，**必须整套继承版式，只做必要替换和数量适配**。

**5.1.1 · 内容替换 + 文本框自适应**
保留几乎所有原本元素（形状、装饰、位置、色彩），只删除或替换占位文本与占位图片。替换后文本长度和原占位差异明显时，同步调整文本框宽高与字号，保证不换行畸形、不压边、不虚挂；同时同一行同一列的元素需要完全对齐 —— 让替换后的内容在原骨架里"填得刚刚好"。

**5.1.2 · 数量适配**
当页面结构和数量绑定（目录 6 章、章节页 5 卡、进度条 4 段）而用户实际内容数量不同：主动增删对应元素。删多余 / 补不足时**新增元素复用同页现有元素的形状/尺寸/间距/配色，不引入新造型**。增删后同步调整剩余元素的位置和字号，让整页疏密节奏合理，不出现大片空洞或挤压。

#### 规则 5.2 · active_rebuild 内容页

**核心：模板只提供"外壳"（品牌资产 + 视觉基调），内容表达完全走 style。** —— 只做两件事：**照单保留 brand_assets，其余照 style 做**。

**骨架复用（默认行为）**：同一份 deck 里同版式的 active_rebuild 页通常有多张（比如连续 4 页 KPI 卡、连续 3 页三线表）。**默认每页都复用前一同版式页的骨架**：首基线页（skeleton_ref=`-`）走 cp content_skeleton → Read → Edit → 写入；**后续同版式页（skeleton_ref=`Pn`）不重复 cp/Read source,直接 Write from memory**（骨架来源见 Step 5 「写页起点」路径 1）。**不复用的成本**：每页多读 20-80 KB source XML,10 页 deck 可能多读 500 KB / 100K token,直接触发 harness compact。

**5.2.1 · 硬性保留清单**

保留的元素只能是下面这些跨页复用的品牌资产：

- **跨页复用 shape**：页眉条 / 页脚条 / 顶部导航条 / 左侧编号角标 / 页码框 / 装饰细线（在 3 张及以上 content 页出现的同 signature shape）
- **跨页复用 img**：Logo / 校徽 / 水印 / 全页背景图
- **主色 palette**：主色和强调色 100% 照搬模板 —— 从 `template-index.json.visual_language.primary_colors` 直接拿（top 6 是模板实际用的色系）；不引入新色族
- **字体族**：写 XML 的 `fontFamily` 属性时**必须**从 `template-index.json.visual_language` 里拿：
  - 首选 `fonts_used`（从 SXSD 实际统计的 top 4 字体，出现次数最多的那款就是模板正文字体）
  - fallback `fonts_declared`（从 theme.xml 拿的 majorFont/minorFont，headline 用 major、body 用 minor；latin 是英文/数字字体、ea 是中文字体）
  - **不要凭记忆写 "Arial" / "微软雅黑" / "思源黑体" 这类默认字体** —— 模板的字体族即使是标准字体，也必须从这里取值确认一致

保留时**位置全部不动**，大小允许随文本适配。装饰性用色允许在主色同色系深浅内变化（`#224581` 可派生 `#3A5A8B` / `#6C7EA1` 等变体）。

**除以上清单外的一切原页元素（示例文字 / 占位图 / 内容框 / 特色组件如金字塔/蜂窝/齿轮/半圆拱 …）默认删掉**

**例外**：只有用户在 query 里**明确点名**要求保留某个模板页的特定组件（"我喜欢那个金字塔"、"必须用上模板里的蜂窝阵"）时，才可以在对应 content 页复用该组件。默认场景下模型不主动这么做。

**5.2.2 · 内容表达走 style**

删掉 brand_assets 以外的一切模板元素后，页面剩下的可用区域**完全按 Step 2 已 Read 的 style/*.md** 组织内容：

- 按 style 的**页面语法**（每类内容页应该长什么样）决定版式
- 按 style 的**字号层级 / 行距 / 装饰节制**决定排版
- 按 style 的**图表选择**决定用哪种 SVG / 原生 chart / 文字要点承载数据
- 按 style 的**主标必陈述句 + 来源脚注 + 图注**规则完成文字修辞

**默认视觉化 · 纯段落是例外**:能用结构化视觉承载的信息就不要用纯段落 —— 数字用 KPI 数字带、并列要点用编号卡片 / 分栏列表 / IconPark bullet、有先后顺序用时间线 / 步骤流、有对比用三线表 / 二列对照、有数据用 SVG 图表或原生 chart、有分类结构用矩阵 / 树 / 蜂窝。**用户内容超过 3 行先判断能否结构化拆分**;只有真正的叙述型长文(如"研究背景综述""案例故事叙述""结论陈词")才用纯段落 —— 且纯段落每段不超过 4 行、必须配主视觉(图 / 图表 / 大数字 / 引用块)平衡视觉重量,不允许"整页只有标题 + 几段纯文字 + 页眉页脚"。

`fixed_template` 页承担 deck 的"模板辨识度"，`active_rebuild` 页承担 deck 的"内容品质"。两者分工清晰，不互相干扰。

#### Step 5 每页写入闭环

1. **落本页 XML**：按 5.1 或 5.2 规则改 authoring 副本。图片用 `template-index.json` 的 `assets_with_tokens` 里的 file_token（模板图直接引用不用重传；新图先 `+media-upload` 拿新 token）。**全篇禁止 emoji，语义图标一律 IconPark。**
2. **写入 deck**:
   - **第 1 页**用 `+update-slide` 覆盖占位页:
     ```bash
     cd "$WORK_DIR" && lark-cli slides +update-slide --no-lint \
       --presentation "<lark.deck.xml_presentation_id>" \
       --slide-id "<lark.deck.first_page_slide_id>" \
       --content @authoring/slide-01.xml
     ```
   - **第 2 页起**用 `+add-slide` 追加:
     ```bash
     cd "$WORK_DIR" && lark-cli slides +add-slide --no-lint \
       --presentation "<lark.deck.xml_presentation_id>" \
       --slide @authoring/slide-NN.xml
     ```
   `--slide @<文件>` 必须是 CWD 内相对路径。检查 `.ok == true` 且 `.data.slide_id` 非空。失败按 [`error-handling.md`](error-handling.md) 排障。写入成功后进入下一页
   - 默认带 `--no-lint`；成功后继续。服务端仍拒绝时按 [error-handling.md](error-handling.md) 保留失败状态，不自动进入 lint 修复循环。

### Step 6 · 交付

按 page-plan 完成逐页写入，并根据每次响应记录成功结果。先等 Step 1 已启动的 purge_deck.py 完成清理，再交付当前 deck。

```bash
# 从 pid 文件读回后台清理任务的进程 ID
if [ -f "$WORK_DIR/.purge_deck.pid" ]; then
  PURGE_TASK_PID=$(cat "$WORK_DIR/.purge_deck.pid")
  while kill -0 "$PURGE_TASK_PID" 2>/dev/null; do sleep 2; done
fi
```

用 `present_files` 交付 `lark.deck.url`，并简述制作结果。必要 ID 缺失或写入状态不明时，按 [error-handling.md](error-handling.md) 只读确认实际状态。

## 四、按用户要求启用 Organizer

本节仅在用户明确要求额外审查、复验或生成后优化时适用。Organizer 的完整流程见下方文档。

**[`template-editing-organizer.md`](template-editing-organizer.md)**

启用此可选流程后，MainAgent 派 Organizer 时，把 `<skill_root>/references/workflow/template-editing-organizer.md` 作为 Organizer 的 workflow 参考文档(Organizer 冷启动 Read 顺序里替代原来的 template-editing.md)。

**MainAgent 本身不需要 Read template-editing-organizer.md** —— Organizer 会自己读。MainAgent 只需要知道 Organizer 的 6 Steps 概要即可:
1. 冷启动 Read(含 refine/<style>.md 手册)
2. Fan-out enrich subagent(poll 前一次性发完 · 不 wait) —— 联网搜真实数据 / 挖原稿 / 图片素材,并行给 refine 用
3. Poll 感知新页(每次做完实际工作立即再 poll · 空轮 sleep 15-20s)
4. 抽单页 XML
5. 审查 + 修复(按页型分支:fixed_template 只修 bug · active_rebuild 既修 bug 也 refine 拔高)
6. 出口(收 MainAgent 通知后跑收尾窗口再 return)

仅在此可选流程已启用时，MainAgent 在页面写入完毕后通知 Organizer 收尾，并等待其返回。按用户要求处理返回结果后，用 `present_files` 交付本轮结果。Organizer 修改既有页使用 `safe_update_slide.py` 的版本保护，MainAgent 负责新建和删除页面，双方避免同时修改同一页。

## 五、附录 · 可选 Organizer 的 subtask 模板

### Organizer subtask 消息模板

确认用户已明确要求额外审查、复验或生成后优化后，才使用以下 `create_agent` 消息（路径和参数替换成实际值）：

```
用户已明确要求本次额外审查或生成后优化。你是 template-editing 流程的 Organizer 影子审查 agent。冷启动请按下面清单顺序 Read 文档，读完直接进入 poll 循环，不需要回消息确认。

任务参数：
- WORK_DIR: <绝对路径>
- skill_root: <绝对路径>
- deck_xml_presentation_id: <id>
- deck_url: <url>
- first_page_slide_id: <sid>
- is_manuscript_apply: <true|false>
- style_doc: <MainAgent Step 2 选定的 style 文件名,如 academic-research>

冷启动 Read 清单（严格按顺序）：
1. <skill_root>/SKILL.md
2. <skill_root>/references/workflow/template-editing-organizer.md
3. <skill_root>/references/refine/<style_doc>.md   ← Track 2 refine 手册（气质定位 + enrich/reframe/decorate 三段决策树）
4. <skill_root>/references/xml/xml-schema-quick-ref.md

按需 Read（不进冷启动清单）：
- <skill_root>/references/style/<style_doc>.md：MainAgent 已把 style 决策落定，只在个别页决策不清时按需 Read
- <skill_root>/references/cli/lark-slides-replace-slide.md：99% 走 safe_update_slide.py，需要块级 replace-slide 时按需 Read

核心纪律：
- 只有一个 deck；所有 +xml-get / safe_update_slide.py 都用 deck_xml_presentation_id
- deck 初始状态:第 1 页是 parse_template 清空的空白占位页 · 后续被 MainAgent `+update-slide` 覆盖;判"第 1 页是否已被 MainAgent 处理" = 检查该页 shape 数 > 0(初始为 0);第 2 页起是新 poll 出的 `+add-slide` 追加页 · 每张都纳入审查
- 修复走 safe_update_slide.py，禁止裸调 +update-slide
- 中途不 send_message 给 MainAgent
- **按页型分支修复**：`fixed_template` 只修 bug；`active_rebuild` 既修 bug 也主动 refine 拔高（每页 ≤ 2 次 refine · 保 brand_assets + 保内容意图 · 可加可减）
- 收到 MainAgent 的收尾通知（不是 shutdown_request，而是 "所有页面已写入完毕"这类文本消息）后进入**收尾窗口**：只补齐 P0 bug → 产 return-summary.md → return（不通知用户，MainAgent 会做二次 present_files）
- **Poll 节奏**：上一轮审到 ≥ 1 张新页 → 立即再 poll，不 sleep；上一轮空轮 → sleep 15-20s；429/5xx/timeout 指数退避重试
```
