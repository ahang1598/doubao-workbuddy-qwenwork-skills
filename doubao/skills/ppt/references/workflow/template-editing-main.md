# 模板遵循工作流

用户提供 PPTX / 在线 Slides 作为模板并要求据此制作演示文稿时走本流程。

**核心原则**:**模板适配内容,不是内容适配模板**。模板只提供视觉资产(组件 + 色系 + 字体),核心目的是把用户信息表达清楚、表达漂亮。不要为"保留模板"强行让内容适配组件 · 更不能跳过模板适配报错。

**本地电脑模式**：SystemPrompt 里若出现 `Computer OS: Mac` 或 `Computer OS: Windows`，读完本文档后必须完整 Read [`local-compat.md`](local-compat.md) 与（若 Windows）[`windows-compat.md`](windows-compat.md)。


## 一、Agent 协作与通信
本流程涉及两个 agent：
- **MainAgent**：主流程执行者。负责解析模板、制定 plan、开工通知、图片上传、流式生成、成稿交付
- **Organizer**：影子审查 agent。异步 poll deck 服务端全稿，diff 出新页做**两条线的工作**：
  - **Track 1 · Bug 修复**（所有页型都做）：修视觉错误，走 A/B/C/D/E 五项审查
  - **Track 2 · Refine 优化**（**仅 active_rebuild content 内容页**）：即使没错也主动 refine，核心是尽可能提高 ppt 的视觉效果和信息密度，按 [`../refine/<style>.md`](../refine/) 手册的三段决策树 enrich(补内容) / reframe(换表达) / decorate(增加视觉) 优化页面。**fixed_template 页（cover/toc/chapter/transition/ending）禁止 refine**——它们承担模板辨识度，只做 Track 1

**通信规则**：

- 只有一个 deck(Step 1 导入模板 + 单线程串行 delete 除第 1 页外所有页 + `+update-slide` 把第 1 页覆盖成空白后就是交付目标),双方共用同一个 `lark.deck.xml_presentation_id`。
- MainAgent 独占 `+add-slide` 和第 1 页 `+update-slide` 占位覆盖;Organizer 独占 `safe_update_slide.py` 做修改(修 bug + refine · fixed_template / active_rebuild 都走它),禁止裸调 `+update-slide` / `+add-slide` / `+delete-slide`。
- Organizer 冷启动后中途不 `send_message`，只在收到 MainAgent 收尾通知后跑完收尾窗口再 return 一次。
- MainAgent 全部写完后:`send_message` 通知 Organizer 收尾 → 立即 `present_files` 交付初稿给用户 → 并行做全稿 lint / 抽查 → `wait_agent` 接住 Organizer return → Step 7 兜底(修 return 里未处理 P0 + 补 6c 发现的 lint 错 + 处理 missing_pages 告警) → 二次 `present_files`。全流程仅一次 `wait_agent`。
- 启用条件：page-plan 目标页数 > 2，或用户提供了需要保留的原稿附件，或用户强制要求保留数字/事实。单页/双页且无原稿的任务跳过 Organizer。


## 二、CWD 与产物目录
始终停留在任务开始时的 CWD；所有产物写入 CWD 内的独立目录：
```bash
LARK_SLIDES_SKILL_DIR="<包含当前 SKILL.md 的绝对目录>"
WORK_DIR=".lark-slides/template/<deck-or-task-id>"
mkdir -p "$WORK_DIR/manifest/slides" "$WORK_DIR/assets" "$WORK_DIR/thumbs" "$WORK_DIR/source-slides" "$WORK_DIR/authoring" "$WORK_DIR/lint"
```
Skill 脚本始终通过 `$LARK_SLIDES_SKILL_DIR/scripts/...` 调用。

## 三、MainAgent 流程（7 Steps）
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
| `lark.deck.url` | Step 3 开工通知 + Step 7 交付 |
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
- Step 3 只是发工作卡片链接(deck 还是空的),不需要等 purge。**Step 6b 交付初稿前**从 `.purge_deck.pid` 读 pid 并 wait,避免用户点开看到模板残留。
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

**选定 style · 一次 Read 拿到目标文件**：根据用户诉求从下表匹配唯一主场景，然后完整 Read 对应 `style/*.md`（Step 5 每页决策的核心依据，Organizer 冷启动会读同一份）：

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

**落 page-plan.md**：一份完整的施工清单，**顶部先记录 style**（Organizer 会读），再落每页表格：

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

`present_files` 交付 Step 1 拿到的 `lark.deck.url`。**必须放在思考过程之外的正文回复里**，让用户看到"PPT 已经开始制作，可以点击卡片关注进度"。这个链接和 Step 7 交付用的是同一个地址，两次都必须发。

### Step 4 · 派 Organizer + 上传图片
**派 Organizer**(Step 4 起,见第五章 subtask 模板):`create_agent` 派完立刻推进图片上传,**不 wait_agent、不 peek_agent**。Organizer 会异步冷启动读文档、跑 Step 5 期间的流式检查。

**注意**：除非页数只有1-2页，否则**必派 organizer 做优化**，防止出现任何错误

**图片上传**：

- **模板自带图**：Step 1 已抽 file_token 到 `template-index.json` 的 `assets_with_tokens` 字段，直接引用不用 `+media-upload`
- **新素材**（用户附件里的图/表、联网搜图产物、生图产物）：必须 `+media-upload --file <path> --presentation <lark.deck.xml_presentation_id>` 拿新 file_token；自己记着新 token 别丢，Step 5 写 XML 时引用

### Step 5 · 流式生成

每页闭环：**落 XML → 聚合 lint → 写入 → 下一页**。默认不截图，视觉验收由 Organizer 异步做（除下面规则 5.1.3 的截图判断路径）。Organizer 通过 diff deck 服务端全稿自己感知进度，MainAgent 每页写完不需要 Edit page-plan 打标记。

**🚫 严禁批量生成 XML —— 每页必须独立走一次 Edit 或 Write 工具调用**。批量生成会跳过 harness 的 read-before-edit 追踪、跳过 lint、跳过 per-page 校验，直接导致后期页面质量崩塌（文本没替换干净、id 没删对、note 位置错、样式属性丢失）。以下 4 种 pattern **一律禁止**，就算跑一次也算违规：

1. **for 循环处理多页 slide XML**：`for i in 04 05 06; do cp source-slides/slide-$i.xml authoring/...; done` / `for sid in pQx pQy pQz; do sed -i ... done` —— 不管循环体里写什么，只要在一条 Bash 里对多个 slide 文件做修改，都禁止
2. **单条 Bash 里 cp + sed 链**：`cp source X && sed -i 's/A/B/' X && sed -i 's/C/D/' X && sed -i 's/E/F/' X ...` —— 5 条以上 sed 串起来实际上就是脱离 Edit 追踪的批量改，必须拆成正规的 cp + Read + Edit
3. **python -c 内嵌多文件循环**：`python3 -c "for f in ['s04.xml','s05.xml','s06.xml']: ..." ` / `python3 -c "notes = {'04':..., '05':..., '06':...}; for i in ...: ..."` —— 一段 python 内联脚本改多个 slide 文件都禁止
4. **heredoc / cat + note 拼接批量灌页**：`for i in ...; do cat > slide-$i.xml <<EOF ... EOF; done` —— 直接落盘绕过 Write 工具，禁止

**合法路径只有两条**（跟 Step 5 「写页起点」的三条路径对齐）：
- **fixed_template 页 / active_rebuild 首基线页**：cp source → **Read authoring**（一次工具调用）→ **Edit authoring**（一次工具调用改一处，需要多处改就多次 Edit，允许连续多个 Edit）→ 单页 `+add-slide`
- **active_rebuild 复用基线页（skeleton_ref=Pn）**：**Write authoring**（一次工具调用从零落文件）→ 单页 `+add-slide`

**判断"是否越界"最简判据**：本条 Bash 里出现 `for` / `python3 -c` 且里面涉及多个 slide 文件路径 = 违规；本条 Bash 里 `sed -i` 出现 ≥ 5 次或替换多个 slide 文件 = 违规。发现自己写出这种命令立刻停手，拆成一页一次 Edit/Write。

**写页起点**（按 page-plan 该行的 `页型策略` + `skeleton_ref` 分三条路径）：

**⚠️ 写下一页前先自检**：如果这是 active_rebuild 页且**前一 active_rebuild 页版式相同**（来源模板页相同 + style 内容相同），那么本页 skeleton_ref 就应该指向前一页（复用骨架）。**默认走复用**，只有版式真跳变才回退基线路径。**不复用 = 重复读一份几乎相同的 XML,浪费 20-80 KB context**。

三条路径:

- **active_rebuild 页且 skeleton_ref = `Pn`（默认 · 复用 Pn 骨架）**：**不 cp、不 Read source**。**骨架自检**：context 里还能看到 authoring/slide-<Pn>.xml 的完整正文？能看到就直接 Write from memory 只替换内容字段；看不到（compact 掉了）就先 Read authoring/slide-<Pn>.xml 一次再 Write。Write 前不需要再 Read —— "Edit 前必须 Read" 的约束只对 Edit 生效。写完直接进 lint + `+add-slide`。
- **active_rebuild 页且 skeleton_ref = `-`（例外 · 首个建立此版式的基线）**：**cp `content_skeleton_path` → authoring/slide-NN.xml**（从 `template-index.json.slides[N].content_skeleton_path` 取，通常是 `manifest/content-skeletons/slide-NN.content-skeleton.xml`）→ Read authoring 副本 → 按 style 文档的表达规则 Edit 填内容 shape → 写入。写完这页 authoring/slide-NN.xml 就是**版式基线**供后续同版式页复用。**注意**：本步是 MainAgent 建首稿，只需按 style 文档表达出内容;Organizer 收尾会按 refine 手册做 refine 提升视觉密度和信息层次。
  - 🚫 **禁止 cp source-slides 作为 active_rebuild 起点** —— source 里的内容占位符会诱导模型"生搬硬套"，触发 `template_copy_overfit` lint P0 阻断。content-skeleton 只含跨页复用 brand_assets（背景/页眉/页脚/装饰线），是干净起点。
  - `content_skeleton_path` 为 null（模板未识别到跨页 brand_assets）时才回退 cp source，但**写入前必须删掉 60%+ 的 source shape**（保留背景 + 页眉 + 页脚，其余全清）。
- **fixed_template 页**（cover / toc / chapter / transition / ending）：`cp source-slides/slide-NN.xml authoring/slide-NN.xml` → **只 Read authoring 副本** → Edit。**禁止先 Read source 再 cp** —— source 与副本内容完全相同，重复读会把同一份 XML 塞进 context 两遍。

**slide 根元素 `id` 属性**：第 1 页(走 `+update-slide` 覆盖)保留 id 无影响;第 2 页起(走 `+add-slide` 追加)**必须删掉根元素 id**,否则 `+add-slide` 会撞 id。子元素 id 一律不动。

**注意**:
1. lint 报错必须查截图确认(不能因"source 有同样问题"就跳过 · source 也可能有视觉 bug)
2. lint 通过不需要截图,直接下一页 · 省时间

#### 规则 5.1 · fixed_template 页（cover / toc / chapter / transition / ending）

这类页承担整份 deck 的品牌辨识度，**必须整套继承版式，只做必要替换和数量适配**。

**5.1.1 · 内容替换 + 文本框自适应**
保留几乎所有原本元素（形状、装饰、位置、色彩），只删除或替换占位文本与占位图片。替换后文本长度和原占位差异明显时，同步调整文本框宽高与字号，保证不换行畸形、不压边、不虚挂；同时同一行同一列的元素需要完全对齐 —— 让替换后的内容在原骨架里"填得刚刚好"。

**5.1.2 · 数量适配**
当页面结构和数量绑定（目录 6 章、章节页 5 卡、进度条 4 段）而用户实际内容数量不同：主动增删对应元素。删多余 / 补不足时**新增元素复用同页现有元素的形状/尺寸/间距/配色，不引入新造型**。增删后同步调整剩余元素的位置和字号，让整页疏密节奏合理，不出现大片空洞或挤压。

**5.1.3 · 页形本身设计导致的 lint 报错**
默认所有 lint 报错都必须修，但对疑似"模板本身设计意图导致"的报错走这个判断流程：

1. 先写入 + `+screenshot --slide-id <sid> --output-dir "$WORK_DIR/lint/screenshots"` + Read 截图
2. **判断依据只有一条：用户视觉上是否完全察觉不到这是问题** —— 例如章节角标 by design 半出画布这种刻意设计，或字号严格对齐但被 lint 判为"略溢出"的边界情况
3. 只要肉眼能看出"这里怪怪的"（字压边、文字挤成一团、颜色对比不足、元素明显遮挡），无论 source 里是不是这样都必须修
4. 判定放过的报错记入 `$WORK_DIR/lint/slide-NN.skips.jsonl`
5. 不要直接强行修掉或跳过这一类错误，视觉效果才是验证 lint 到底是真报错还是误报的唯一标准

#### 规则 5.2 · active_rebuild 内容页

**核心：模板只提供"外壳"（品牌资产 + 视觉基调），内容表达完全走 style。** —— 只做两件事：**照单保留 brand_assets，其余照 style 做**。

**骨架复用（默认行为）**：同一份 deck 里同版式的 active_rebuild 页通常有多张（比如连续 4 页 KPI 卡、连续 3 页三线表）。**默认每页都复用前一同版式页的骨架**：首基线页（skeleton_ref=`-`）走 cp content_skeleton → Read → Edit → 写入；**后续同版式页（skeleton_ref=`Pn`）不重复 cp/Read source,直接 Write from memory**（骨架自检 + 回读兜底见 Step 5 「写页起点」路径 1）。**不复用的成本**：每页多读 20-80 KB source XML,10 页 deck 可能多读 500 KB / 100K token,直接触发 harness compact。

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
2. **聚合 lint**：每写完一个 xml 文件，都需要跑一次 lint 检查，直到把所有 lint 检查的报错全部消除之前，都绝对不可以上传至 deck 中
   ```bash
   python3 "$LARK_SLIDES_SKILL_DIR/scripts/template_lint_all.py" \
     --authored "$WORK_DIR/authoring/slide-NN.xml" \
     --source   "$WORK_DIR/source-slides/slide-NN.xml" \
     --skill-root "$LARK_SLIDES_SKILL_DIR" \
     --page-role <fixed_template|active_rebuild> \
     > "$WORK_DIR/lint/slide-NN.json" || true
   ```
   **`--source` 是 lint 脚本自己读的**(用来做 template_copy_overfit 检查) · **不算 MainAgent Read source** · 不违反 "active_rebuild 不 Read source" 约束。**`--page-role` 必传**:从 page-plan 该行「页型策略」列取 `fixed_template` 或 `active_rebuild`。`fixed_template` 页(cover/toc/chapter/transition/ending)天然元素少或纯文字,sparsity 相关 issue 会降级为 info 不阻断;`active_rebuild` 页会严格审 sparsity(防"页眉页脚 + 几段纯文字"的空稿)。

   看结果：
   - `status=ready_to_write` 才能写入；`status=blocked` 禁止写入，看 `block_reasons` 逐项修完重跑
   - `placeholder_warnings > 0` 不阻断但必须逐条判断（黑名单命中一定是漏改，其他相同文本自行判断是骨架 label 还是漏改）
   - `overflow_covers_below_fail_count > 0` 阻断写入，改小字号或缩短文本让 `estimated_h <= declared_h`
   - **`sparsity_fail_count > 0` 阻断写入**，常见原因（看 `checks.sparsity.issues`）：
     - `too_few_elements`（active_rebuild 页元素 < 3）→ 加视觉元素（KPI 数字带 / 编号卡 / 图 / SVG）
     - `text_ratio_too_high`（文字元素占比 > 90%）→ 拆结构化视觉
     - `dominated_by_paragraphs`（1 个 ≥ 80 字长段落 + 长段占比 > 60%）→ 把大段拆成 bullet / 卡片 / 图表
     - `density_below_source`（新页元素数 < 源模板页 × 60%）→ 补结构性视觉，不用照搬示例文字
3. **写入 deck**:
   - **第 1 页**用 `+update-slide` 覆盖占位页:
     ```bash
     cd "$WORK_DIR" && lark-cli slides +update-slide \
       --presentation "<lark.deck.xml_presentation_id>" \
       --slide-id "<lark.deck.first_page_slide_id>" \
       --content @authoring/slide-01.xml
     ```
   - **第 2 页起**用 `+add-slide` 追加:
     ```bash
     cd "$WORK_DIR" && lark-cli slides +add-slide \
       --presentation "<lark.deck.xml_presentation_id>" \
       --slide @authoring/slide-NN.xml
     ```
   `--slide @<文件>` 必须是 CWD 内相对路径。检查 `.ok == true` 且 `.data.slide_id` 非空。失败按 [`error-handling.md`](error-handling.md) 排障。写入成功后进入下一页
   - 使用 update 或 add 命令更新飞书 deck 时，可能会因为 lint 报错而碰到 4000153 错误码，如果这个报错确实是模版有意为之，那么可以在命令中增加 no-lint 参数来成功写入

### Step 6 · 通知 Organizer 收尾 + 交付初稿(**不阻塞**)

MainAgent 按 page-plan 把每页都成功 `+add-slide` / `+update-slide` 后进本步。

**6a · 通知 Organizer 收尾**（`send_message`，**不是 shutdown**）：

```
所有页面已成功写入 deck。请你进入收尾窗口:
1. 继续 poll 循环 5-10 轮(下限 5 保证把最后写的几页全审一遍;上限 10 防止无限修复)
2. 每轮把当前批次新页跑完 A/B/C/D/E 五项审查
3. 尝试修复所有 P0:能修的直接走 safe_update_slide.py 落地;修不动的(safe_update 2 次 abort / 判定不安全自动改)记入 report 第 3/4 段
4. **`active_rebuild` 页必须至少 refine 1 次**(即使无 bug 也主动按 refine 手册 enrich/reframe/decorate 拔高视觉密度)
5. 上限触发(任一):达到 10 轮 / 上一轮 diff 新增页 = 0 且当前 P0 全部处理 且每个 active_rebuild 页 refine ≥ 1 次 —— 产出 return-summary.md 并 return
6. 不要通知用户;MainAgent 会做二次 present_files 交付最终稿
```

**6b · 交付初稿给用户**(`present_files`,**必须放在正文回复里**):

**先等 purge 完成**(Step 1 后台跑的 purge_deck.py 到此必须已清完,否则用户看到模板残留页):
```bash
# 从 pid 文件读回 pid(跨 tool call 不能用 $PURGE_PID 变量)
if [ -f "$WORK_DIR/.purge_deck.pid" ]; then
  PID=$(cat "$WORK_DIR/.purge_deck.pid")
  # kill -0 探测进程是否还在 · 在的话 wait 到它结束
  while kill -0 "$PID" 2>/dev/null; do sleep 2; done
fi
```

`present_files` 交付 `lark.deck.url`,并在**正文回复**明确说明:

> 这是**初稿**,可以先点开看。Organizer 还在做最后几轮视觉审查和修复,几分钟内会更新到同一个链接,然后我会再给你发一次卡片表示打磨完成。

**6c · MainAgent 并行做 Step 7 准备工作 + wait return**：

Organizer 的收尾窗口需要几分钟，MainAgent 这段时间不能干等 —— 并行做以下工作，跑完再 `wait_agent` 接住 Organizer 的 return 报告：

1. **全稿回读**:
   ```bash
   lark-cli slides +xml-get --presentation "<lark.deck.xml_presentation_id>" --output "$WORK_DIR/final.xml"
   ```
2. **逐页 lint**(`template_lint_all.py` 只接受单页 authoring/slide-NN.xml · 不能传全稿 final.xml):
   ```bash
   # 用 xml_inspect.py 从 final.xml slice 每页,对每页跑 lint
   for sid in $(python3 "$LARK_SLIDES_SKILL_DIR/scripts/xml_inspect.py" --mode summary --input "$WORK_DIR/final.xml" | jq -r '.slides[].slide_id'); do
     python3 "$LARK_SLIDES_SKILL_DIR/scripts/xml_inspect.py" --mode raw --slide-id "$sid" --input "$WORK_DIR/final.xml" > "$WORK_DIR/lint/final-$sid.xml"
     # --page-role 从 page-plan 该行「页型策略」列取
     python3 "$LARK_SLIDES_SKILL_DIR/scripts/template_lint_all.py" \
       --authored "$WORK_DIR/lint/final-$sid.xml" \
       --skill-root "$LARK_SLIDES_SKILL_DIR" \
       --page-role <fixed_template|active_rebuild> \
       > "$WORK_DIR/lint/final-$sid.json"
   done
   ```
   任意页 `error_count > 0` 记下问题页,Step 7 一并修
3. **可疑页视觉抽查**:对逐页 lint 报警的页 `+screenshot` + Read
4. **`wait_agent`** 接住 Organizer return(回读 + lint 期间 Organizer 可能已经完成,wait 立即返回;未完成则继续等)
5. Read `return-summary.md`

### Step 7 · 兜底修复 + 二次交付

Organizer 已通过 return 交出报告并自然退出，MainAgent 现在可以裸调 `+update-slide` / `+replace-slide` 做兜底修复。

1. **看 return 报告第 0 段告警**（若有）：`missing_pages`（Organizer 对比 page-plan 目标页数 vs deck 实际页数发现有页没写入 → 逐页照单补写）/ `no_new_pages_seen`（Organizer 全程没 poll 到新页 → 必须自己走完全稿 lint + 逐页截图 review）
2. **修 return 报告第 3、4 段未修复 P0**：Organizer 已 return，MainAgent 可裸调 `+update-slide` / `+replace-slide` 修复。每个 P0 修完后 `+screenshot` + Read 确认修好了
3. **合并 Step 6c 自己发现的 lint 问题**：如果 Step 6c 的全文 lint 有 error 但 return 里没提到（例如 Organizer 收尾窗口用光前没审到），一并修
4. **二次交付**：`present_files` 再交付一次 `lark.deck.url`（**同一个 URL，但这是第二次卡片交付**），正文回复说明"打磨完成，最终稿如下"。若 SystemPrompt 里出现 `Computer OS: Mac`/`Windows`，先 `lark-cli drive +export --token <file_token> --doc-type slides --file-extension pptx --output-dir "$WORK_DIR"` 导出 pptx，再对本地路径调 `present_files` 一次


## 四、Organizer 流程

Organizer 的完整流程(冷启动 Read 清单、6 Steps、subtask 消息模板、工具约束)在**另一份文档**:

**[`template-editing-organizer.md`](template-editing-organizer.md)**

MainAgent Step 4 派 Organizer 时,把 `<skill_root>/references/workflow/template-editing-organizer.md` 作为 Organizer 的 workflow 参考文档(Organizer 冷启动 Read 顺序里替代原来的 template-editing.md)。

**MainAgent 本身不需要 Read template-editing-organizer.md** —— Organizer 会自己读。MainAgent 只需要知道 Organizer 的 6 Steps 概要即可:
1. 冷启动 Read(含 refine/<style>.md 手册)
2. Fan-out enrich subagent(poll 前一次性发完 · 不 wait) —— 联网搜真实数据 / 挖原稿 / 图片素材,并行给 refine 用
3. Poll 感知新页(每次做完实际工作立即再 poll · 空轮 sleep 15-20s)
4. 抽单页 XML
5. 审查 + 修复(按页型分支:fixed_template 只修 bug · active_rebuild 既修 bug 也 refine 拔高)
6. 出口(收 MainAgent 通知后跑收尾窗口再 return)

## 五、附录 · MainAgent 派 Organizer 的 subtask 模板

### Organizer subtask 消息模板

`create_agent` 时把这段作为初始消息发给 Organizer（路径和参数替换成实际值）：

```
你是 template-editing 流程的 Organizer 影子审查 agent。冷启动请按下面清单顺序 Read 文档，读完直接进入 poll 循环，不需要回消息确认。

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
4. <skill_root>/references/workflow/validation-visual.md
5. <skill_root>/references/xml/xml-schema-quick-ref.md

按需 Read（不进冷启动清单）：
- <skill_root>/references/style/<style_doc>.md：MainAgent 已把 style 决策落定，只在个别页决策不清时按需 Read
- <skill_root>/references/cli/lark-slides-replace-slide.md：99% 走 safe_update_slide.py，需要块级 replace-slide 时按需 Read

核心纪律：
- 只有一个 deck；所有 +xml-get / +screenshot / safe_update_slide.py 都用 deck_xml_presentation_id
- deck 初始状态:第 1 页是 parse_template 清空的空白占位页 · 后续被 MainAgent `+update-slide` 覆盖;判"第 1 页是否已被 MainAgent 处理" = 检查该页 shape 数 > 0(初始为 0);第 2 页起是新 poll 出的 `+add-slide` 追加页 · 每张都纳入审查
- 修复走 safe_update_slide.py，禁止裸调 +update-slide
- 中途不 send_message 给 MainAgent
- **按页型分支修复**：`fixed_template` 只修 bug；`active_rebuild` 既修 bug 也主动 refine 拔高（每页 ≤ 2 次 refine · 保 brand_assets + 保内容意图 · 可加可减）
- 收到 MainAgent 的收尾通知（不是 shutdown_request，而是 "所有页面已写入完毕"这类文本消息）后进入**收尾窗口**：只补齐 P0 bug → 产 return-summary.md → return（不通知用户，MainAgent 会做二次 present_files）
- **Poll 节奏**：上一轮审到 ≥ 1 张新页 → 立即再 poll，不 sleep；上一轮空轮 → sleep 15-20s；429/5xx/timeout 指数退避重试
```
