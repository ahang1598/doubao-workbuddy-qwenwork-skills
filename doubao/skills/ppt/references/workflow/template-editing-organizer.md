# 模板遵循工作流 · Organizer 部分

本文档是 [template-editing-main.md](template-editing-main.md) 的 Organizer 子文档 · 只讲 Organizer 侧的流程。MainAgent 侧流程见 main 文档。


## 一、你在系统里的位置

- 你（Organizer）是**影子审查 agent** · 由 MainAgent 通过 `create_agent` 派单启动
- MainAgent 独占 `+add-slide` 和第 1 页 `+update-slide` 占位覆盖;**你独占 `safe_update_slide.py`** · 禁止裸调 `+update-slide` / `+add-slide` / `+delete-slide`
- 你冷启动后**中途不 send_message**，只在收到 MainAgent 收尾通知后跑完收尾窗口再 return 一次
- MainAgent 通过 subtask 消息给你 7 个字段:`WORK_DIR` / `skill_root` / `deck_xml_presentation_id` / `deck_url` / `first_page_slide_id` / `is_manuscript_apply` / `style_doc`

## 二、CWD

- CWD 由 MainAgent 决定 · 你在 subtask 里拿到 `WORK_DIR` 后所有产物写到 `$WORK_DIR/.lark-slides/organizer/`
- 你**只允许写**这个目录 · 不要写别处

## 三、双轨工作

对每张审到的新页做审查 + 修复闭环：
- **Track 1 · Bug 修复**（所有页型都做）：修视觉错误，走 A/B/C/D/E 五项审查
- **Track 2 · Refine 优化**（仅 `active_rebuild` content 页）：按 [`../refine/<style>.md`](../refine/) 里的 refine 手册对页面走 enrich(补内容) / reframe(换表达) / decorate(增加视觉) 三段决策。`fixed_template` 页禁止 refine


## 四、Organizer 流程（6 Steps）

### Step 1 · 冷启动 Read（严格按顺序）

subtask 从 MainAgent 拿到 7 字段(`WORK_DIR` / `skill_root` / `deck_xml_presentation_id` / `deck_url` / `first_page_slide_id` / `is_manuscript_apply` / `style_doc`)。冷启动读文档顺序:

1. `<skill_root>/SKILL.md`
2. `<skill_root>/references/workflow/template-editing-organizer.md`（即本文档）
3. **`<skill_root>/references/refine/<style_doc>.md`**（Track 2 refine 手册 —— 该 style 的气质定位 + Refine 三段决策树 enrich/reframe/decorate）
4. `<skill_root>/references/workflow/validation-visual.md`
5. `<skill_root>/references/xml/xml-schema-quick-ref.md`

**按需 Read（不进冷启动清单）**：
- `<skill_root>/references/style/<style_doc>.md`：MainAgent 已经在 page-plan 里把 style 决策落定；Organizer 不需要预读 style 文档，只在个别页碰到"不知道 style 应该怎么呈现"时按需 Read
- `<skill_root>/references/cli/lark-slides-replace-slide.md`：Organizer 99% 走 `safe_update_slide.py`，只在极少数需要块级 replace-slide 时按需 Read

读完直接进入 Step 2（fan-out enrich subagent），不需要回消息确认。

### Step 2 · fan-out Enrich Subagent（poll 前 · 一次性发完 · 不 wait）

**为什么**：refine 手册 3.1 段的 Enrich 工作(联网搜索真实数据 / 挖原稿 / 搜图 / 生图 / image_edit / +media-upload)**耗时长(单页 30-60s+)**，如果放到 Step 5 refine 时才做，会拖垮 poll 节奏。在 poll 前一次性 fan-out enrich subagent，让它们**并行**跑，Organizer 自己继续 poll。

**何时发**：Step 1 冷启动读完手册后**立刻**发 · 不等 MainAgent 写页 · subagent 与 MainAgent 并行工作。

**发几个 · 按 enrich 类型分**（每 deck 通常 1-2 个 subagent · 不要更多）：

1. **用户给了附件/原稿**（`is_manuscript_apply=true`）→ 派 **1 个「原稿深挖 subagent」**：
   - 系统 Read 用户附件全部章节 · 按 page-plan 每页主题挖次要信息层
   - 产出:每页的「次要指标 / 引文 / 边界条件 / 方法学细节 / 关键 quote」清单

2. **用户没给附件或明确要求扩写**（`is_manuscript_apply=false` 或用户说要扩充）→ 分两种情况:
   - **文字侧** → 派 **1 个「联网搜索 subagent」**：按 refine 手册 3.1 段的搜索方向 + 关键词模式,搜真实数据/引文/案例/统计
   - **图片侧** → 派 **1 个「图片素材 subagent」**：按 refine 手册的图片策略(学术少图 / 商务重 logo / 品牌重生图 / 教育重 IconPark / 技术重架构图),用 image_search / image_generate / image_edit 收集图片 · **subagent 自己 +media-upload 拿 file_token**

**发派判据速查**:
- `is_manuscript_apply=true` → 只派原稿深挖 subagent(**1 个**)
- `is_manuscript_apply=false` + 用户不用图 → 只派联网搜索 subagent(**1 个**)
- `is_manuscript_apply=false` + 用户要用图 → 联网搜索 + 图片素材(**2 个**)

**subagent 参数与产物**（不需要长 prompt · 说清 3 件事即可）：
1. **参数**:`WORK_DIR` / `deck_xml_presentation_id`(图片 upload 用) / `style_doc` / `page_plan_path`(subagent 自己 Read 拿每页主题)
2. **冷启动 Read**:refine 手册对应段(`refine/<style_doc>.md` 3.1 段 · 学本 style 搜索方向 / 图片策略) + page-plan
3. **产物**:追加写 `<WORK_DIR>/.lark-slides/organizer/enrich-materials/manifest.json`,按 page_num 索引 · 图片必须带 file_token(subagent 自己 +media-upload) · 数据必须真实来源(Source 归属)

**manifest 简要结构**（subagent 边搜边写 · 完成一页就标 status=ready）：
```json
{
  "pages": {
    "<page_num>": {
      "status": "ready | in_progress",
      "text_findings": [{"topic": "...", "value": "...", "source": "..."}],
      "images": [{"file_token": "boxcnXXX", "topic": "...", "usage_hint": "hero / 支撑 / 背景"}]
    }
  }
}
```

**Organizer 不 wait**：`create_agent` 完就直接进 Step 3(poll) · **不 wait_agent**。refine 时怎么用素材见 Step 5.2 Enrich 段(**有用没跳过** · 不阻塞主流程)。

### Step 3 · Poll 感知新页

**Poll 节奏（关键）**：

- **上一轮做了实际工作**（审到并处理了 ≥ 1 张新页）→ **立即进入下一轮 poll，不 sleep**。因为 MainAgent 通常已经写到下一页，让 Organizer 空转 20s 是浪费——审完这页立刻拉下一版 full.xml。
- **上一轮空轮**(`+xml-get` 后 diff 出 0 张新页 · 也没有第 1 页 shape 数变化)→ sleep **15-20s** 再 poll。此时 MainAgent 在忙别的事(写 XML / 跑 lint / 图片上传),空转反而应该给它时间。
- **429 / 5xx / timeout** → 指数退避重试(1s → 2s → 4s → 8s,最多 4 次),不算空轮

`+xml-get --presentation <deck_xml_presentation_id> --output $WORK_DIR/.lark-slides/organizer/current-round-N/full.xml` 拉 deck 当前全稿 → 用 `xml_inspect.py --mode summary` 解析出每页 `(slide_id, shape_count)` 对,跟上轮做 diff:

- 上轮不存在的 slide_id → 加入本轮审查
- `first_page_slide_id` shape 数从 0 变 > 0 → MainAgent 刚覆盖了第 1 页,加入本轮审查
- 空判定(既无新增 id 也无第 1 页变化)→ 记 skip · sleep 15-20s 再 poll

### Step 4 · 抽单页 XML

对每个新增 slide_id，从 full.xml 里 slice 出该页 XML 存到 `current-round-N/slide-<sid>.xml`（用 `xml_inspect.py --mode raw --slide-id <sid>`）。视觉审查另外 `+screenshot` 拉截图。

### Step 5 · 审查 + 修复（按页型分支）

对每张新增页做完整的**审查 + 修复**闭环：先跑五项审查找 bug，再按页型走对应修复动作。

**页型分工**:`fixed_template` 页只审查 + 修 bug 保护模板;`active_rebuild` 页按 refine 手册三段决策树(enrich/reframe/decorate)拔高视觉和信息密度 · refine 是核心工作 · 不是审查后的可选补充。审查发现的 bug 顺手在 refine 里一起修。看下面 5.2 的动作顺序。

#### 5.1 · 审查（所有页型都做）

- **A · XML 完整性**：`template_lint_all.py` 单页跑，任一子项 error / FAIL 都是 P0。**你自己跑 lint 时必须传 `--page-role`**，命令如下：

  ```bash
  python3 "$SKILL_ROOT/scripts/template_lint_all.py" \
    --authored "$ROUND/slide-<sid>.xml" \
    --source   "$WORK_DIR/source-slides/slide-NN.xml" \
    --skill-root "$SKILL_ROOT" \
    --page-role <fixed_template|active_rebuild>       # ⚠️ 必传！从 page-plan 该行「页型策略」列取
  ```

  **漏传 `--page-role` 是常见坑**：脚本会在 summary 里输出 `refine_triggers.signal_error = "missing_page_role_argument"`，看到这个立刻补参数重跑，不要误以为"这页不适用 refine"。传对了才能在 summary 里拿到 `refine_triggers.should_refine`（详见 5.2）。

  **A 里的 `template_copy_overfit` 检测**（仅 `active_rebuild` 页）：`checks.template_copy_overfit.shared_ratio > 0.70` = MainAgent 那页几乎照抄了 source-slides shape（生搬硬套模板），属于 P0 阻断。你 refine 那一页时**必须整页重写**，不要基于 authored 版做微调 —— 起点应该是 `manifest/content-skeletons/slide-NN.content-skeleton.xml`（干净 brand_assets 骨架）+ 按 refine 手册的决策树(enrich / reframe / decorate)重新组织内容和视觉，从零建。
- **B · 视觉完整与正确**（必截图 + Read）：分子项审查，后续新增视觉相关检查都放在 B 项下继续加 Bx。判断这些问题**只靠截图**（不能通过读 XML 数据判断），Organizer 每张新增页都要拉一次 `+screenshot` 亲自 Read。
  - **B1 · 页面正确性**：占位符残留 / 元素遮挡 / 章节角标编号错乱 / 图文不匹配 / 单字换行 / 文字和背景色过于相近。**重点看"字数变化引发的版式不适配"**（模板示例字数 vs 新内容字数差异导致的溢出/换行/间距失衡）—— 这是线上高频 P0 主要拦截线；你可以通过左右上下移动、缩放、改变文字内容来对齐；如果这种 pattern 在多页都出现，那你每一页都需要改对才行
  - **B2 · 疏密与留白**（`active_rebuild` 页尤其重要）：不同于 A 项 template_lint_all 检查的是"精确越界"，B2 检查的是**肉眼可见的美感问题** —— lint 不报错但页面观感不好。逐条对照：
    - **字太多 · 挤成一团**：文本框内正文密度过高，行距被压得看不出层级；单行文字过长没换气；正文字号 < 12pt 却塞满整页 → **P0**；如果实际已经溢出容器（截图上文字被切）→ **P0**。修法：删冗余修饰词 / 拆到两页 / 提炼要点 bullet
    - **留白太多 · 视觉空洞**：整页元素总面积占比 < 40% + 无明确视觉锚点；大块 > 200×200 px 的空白区域没有元素也没有装饰 → **P0**。修法：扩大主视觉 / 加子标题解释 / 拆出来源脚注 + 补充说明性图表 / 加入横向分割线做区隔
    - **信息密度不匹配**：模板卡位 4 个但只填了 2 个（剩下 2 个空卡）→ **P0**（要么补内容要么删多余卡）；模板卡位 4 个但塞了 8 条内容（内容被硬压到卡里）→ **P0**。改变布局，增加/删除更多内容或卡位
    - **视觉重量塌陷**：整页视觉重心偏向一角、另一半空荡荡 → **P0**。修法：把主视觉挪到画布中心区域 / 加装饰或次视觉平衡
    - **B2 的客观信号**：lint summary 里的 `refine_triggers` 字段（详见 5.2）决定"是否 refine"，B2 这里只做补充：即使 refine_triggers 全通过，若视觉观感有以上问题也要 refine
  - **B3 · 图表检查**（原生 `<chart>` / SVG embed / 手绘 shape 图表 都在此审）：
    - **坐标轴与数据对齐**：柱形 / 折线 / 散点等有坐标轴的图，柱底 / 折线端点 / 散点必须精确落在 x 轴对应刻度位置，y 值必须精确落在 y 轴对应刻度高度；出现"柱形飘在 x 刻度之间""柱高与标注数字不匹配（如标注 320 但视觉上只到 200 高度）""SVG embed 里坐标轴刻度和柱位错开"→ **P0**。修法：重新按数据算 x/y 坐标，柱宽和间距按 (画布宽 - 左右 padding) / 类别数 均分
    - **坐标轴范围合理**：y 轴起点不能被隐藏成"看起来所有柱高差很大但其实差 1%"（除非需要放大差异且有明确标注）；y 轴刻度间隔要整齐（0/25/50/75/100 而不是 0/23/47/71/94）；负值必须有明确的 0 轴基线 → 违反 **P1**
    - **图表标题 / 图注 / 单位 / 数据源必须齐全**：Figure N · 短句标题（陈述句） / 每张图配一句解读 caption / 坐标轴带单位（"万元""%""㎡"）/ 底部一行数据来源（"来源：CNKI / 万方，2003-2026"）—— 缺任何一项 → **P0**。学术/商业 deck 少了这些立刻降档
    - **图例位置和颜色**：图例不能压在数据上（右上或下方居中最好）；同色系深浅梯度区分不同数据系列；饼图 / 环形图各扇区颜色必须肉眼可分辨（相邻扇区不能是"深蓝 vs 略深一点的蓝"）→ 违反 **P1**
    - **SVG embed 尺寸**：`<embed width height>` 必须匹配 SVG 内部 viewBox 的宽高比，否则会被拉伸变形（柱变胖 / 圆变椭圆）→ **P0**。修法：SVG 拿到手先看 viewBox，`<embed>` 的 width:height 保持同比
    - **数字格式**：千位分隔符（26,000 不是 26000）/ 百分号紧贴数字（18% 不是 18 %）/ 单位小字紧贴数字右下（不是浮在数字上方）→ 违反 **P1**
    - **禁止软件默认样式**：黑色粗边框 / 3D 立体柱 / 彩虹配色 / 渐变填充 / 阴影投影 —— 出现即 **P0**（style/*.md 里都明确禁止）
  - **B4 · 对齐审查**：视觉专业感最大杠杆，肉眼一眼分辨"专业 vs 廉价"。逐条对照：
    - **同类元素基线对齐**：一排 KPI 数字的底基线 / 一列 bullet 的左边线 / 一组 icon 的中心线 —— 相邻同类元素错位超过 4px 就算 → **P0**。修法：拉齐 topLeftY 或 topLeftX，让同组元素共享一条隐形网格线
    - **数字 + 单位基线对齐**：KPI "26,000 ㎡" —— 数字和单位小字的基线必须齐；不能出现"数字底部对齐 单位顶部对齐"这种漂浮感 → **P0**。修法：把单位放数字右下、字号是数字的 25-30%
    - **文本框边距一致**：同页多个文本框到画布边缘的距离必须统一（左边缘全部对齐、右边缘全部对齐）；相差 > 8px → **P0**。修法：定一个统一的 margin 值（如 60px），所有文本框 topLeftX 遵守
    - **同层级卡片顶部对齐**：一排卡片（如 3 卡横排）的顶部 y 坐标必须相同 → **P0**
- **C · 关键页壳层完整性**：从 `page-plan.md` 读该页「页型策略」+「来源模板页」→ 按下面规则对照 deck 该页：
  - **`fixed_template` 页**（规则 5.1）：Read `source-slides/slide-NN.xml` 拿完整模板版式 · 所有非文字属性必须和 source 完全一致；模板元素被删/改 fill/改类型 → **P0**；只有文字内容、文本框尺寸、元素位置允许变，其他改动都算违规
  - **`active_rebuild` 页**（规则 5.2.1 硬性保留清单）：**Read `manifest/content-skeletons/slide-NN.content-skeleton.xml`（parse_template.py 已自动提取的干净 brand_assets 骨架）而非 source-slides** —— 骨架里的 img/shape/line 就是必须保留的品牌资产（背景/页眉/页脚/装饰线）。骨架元素在 deck 该页找不到 → MISSING **P0**；这些元素坐标/主 fill 色变了 → MUTATED_STRUCTURE **P0**；元素在但文字变了 → MUTATED_TEXT **P1**。**不要 Read source-slides**（内容占位符会误导审查判断）
  - **超出保留清单的模板组件**（金字塔/半圆拱/齿轮等特殊的复杂case）：`active_rebuild` 页默认允许删除，不算问题；只有用户在 query 里明确点名要求保留时才审查
- **D · 目录-章节-导航一致性**：从服务端全稿抽目录 bullets / 章节页大标题 / 页内导航文字做集合对齐；比如明明 plan 里面只写了4个章节，但是目录页出现了5个或者3个；不一致 → P0
- **E · 原稿内容保留**（仅 `is_manuscript_apply=true`）：从原稿抽关键数字/单位/事实 token，检查服务端 XML 是否至少出现一次；不出现 → P0（全稿完整时）/ P1_PENDING（未完整时）

#### 5.2 · 修复动作（按页型分支）

对每张审查完的页，按 `page-plan.md` 里的**页型策略**分两条路走：

**若页型 = `fixed_template`**（cover / toc / chapter / transition / ending）：
- **只修 bug**（不做 refine · 保护模板辨识度）
- 触发条件：5.1 审查里任何 P0 / P1
- 修法：改文字内容 / 调文本框尺寸 / 调元素位置对齐；**其他版式全保留**

**若页型 = `active_rebuild`**（content 页）：

## 🚫 硬红线 · 看到 `should_refine=true` 就必须 refine

**`refine_triggers.should_refine=true` 但本页本轮没跑 refine = 本轮 collab 失败**。你的核心 KPI 是让每个 active_rebuild 页至少 refine 一次，不是"审查完看看要不要 refine"。

线上 trace 分析显示 6/7 本该 refine 的页被 Organizer 漏做,原因是 Organizer 倾向于"看到 P0 bug 就修 P0,看不到 P0 就觉得可以收工"。**修 bug 是 refine 的副产品,不是替代**。

**`return-summary.md` 必须列**（见 Step 6 出口）：
- 本轮 refine 了哪些页(page_num + refined_from → refined_to shape 数变化)
- 未 refine 的 active_rebuild 页各自的**具体不 refine 理由**(比如"P5 refine_triggers.should_refine=false 且截图无视觉优化点";不允许写"没时间"/"看起来 OK"这类)

如果 return-summary 里出现"某 active_rebuild 页 should_refine=true 但没 refine",MainAgent 会在 Step 7 兜底做 refine + 视为你这一轮工作没做完。

**refine 启动规则（客观信号 · 不做主观判断）**：

`template_lint_all.py` summary 里输出 `refine_triggers` 字段 —— **直接看 `refine_triggers.should_refine` 布尔值决定是否 refine**，无需自己心算阈值。字段结构：

```json
"refine_triggers": {
  "applicable": true,                    // fixed_template 页返回 false
  "should_refine": true,                 // 任一信号命中 = true
  "hit_count": 2,                        // 命中信号数
  "triggered": [                         // 命中的信号 · 优先修
    {"signal": "visual_elements", "value": 6, "operator": "≤", "threshold": 12, "note": "装饰/图表偏少"},
    {"signal": "total_elements", "value": 18, "operator": "<", "threshold": 20, "note": "元素太少"},
    ...
  ],
  "passed": [ ... 未命中的信号 ... ],
  "summary": "命中 2/5 个 refine 启动信号 · 应该 refine"
}
```

**5 个信号 + 阈值**（跟脚本对齐 · 命中即触发）：

| # | 信号 | 触发阈值 | 触发含义 · refine 时优先补什么 |
|---|---|---|---|
| 1 | `visual_elements` | `≤ 12` | 装饰/图表偏少 → 补装饰母题（hairline / 短线 / 编号方块 / signature 视觉锚）|
| 2 | `long_paragraph_char_ratio` | `> 0.60` | 单长段主导 → 拆结构化（列表 / 卡阵 / 三线表）|
| 3 | `total_elements` | `< 20` | 元素太少 → 补 shape 达到范本骨架水平 |
| 4 | `total_text_chars` | `< 30` | 内容太少 → 补文字（仅 `<data>` · 不含 `<note>` 演讲者备注）|
| 5 | `text_elements / total_elements` | `≥ 0.80` | 几乎全是文字 → 加视觉稀释 |

**判断逻辑**:读 `template_lint_all.py` 的 summary → 上面 5 项任意信号命中 → 立即 refine。5 项都不命中时,若截图仍有可优化点也应 refine。

**动作顺序**：

1. **打开 refine 手册 `refine/<style_doc>.md`** 按三类动作诊断本页(**三类平权 · 缺什么补什么 · 不排序**):
   - **缺内容?** → 走手册 3.1 **enrich**:能补内容的来源都可以用 · 常见来源:
     - **Step 2 fan-out 的 enrich subagent manifest**(如果已就绪就直接用 · 没就绪就跳过用其他)
     - Read 原稿附件挖次要信息层(次要指标 / 引文 / 边界条件 / 方法学细节)
     - 联网搜索真实数据(权威机构 / 高被引论文 / 案例)
     - image_search / image_generate / image_edit 拿图(如果本 style 用图)
     - **manifest 只是辅助之一 · 有用没跳过不阻塞 · 也可以主动补充其他来源**
     - 硬约束:**必须真实来源 · 禁止编造**
   - **缺表达?** → 走手册 3.2 **reframe**:按手册典型替换(3 段纯文字 → 三线表/卡阵 · 长段落 → 分点 bullet · 散布数字 → hero KPI 数字带 · 时序 → 时间线 · 对照 → 双列表/2×2 · 例证 → 引文块 等)
   - **缺视觉?** → 走手册 3.3 **decorate**:按手册装饰母题库 / 视觉锚点升级库 / 布局重构库挑动作
   - **一页可能同时缺 2 类 / 3 类**,那就多类一起做 · **不要用装饰凑数掩盖内容不足**
2. **再扫 5.1 审查结果 · 把 bug 列出来**(决定 refine 时顺手要修哪些位置)
3. **一次性重写整页 XML**:把三类动作 + bug 修复合并在同一次写入里完成,不要分两次写
   - **起点建议**:需要大改时(`template_copy_overfit` 触发或页面 shape 数 > 60 装饰堆砌)先 Read `manifest/content-skeletons/slide-NN.content-skeleton.xml` 拿干净 brand_assets 骨架,再按手册重新组织内容和视觉,从零建。不要基于 MainAgent 已写的 authored 版做微调 —— 那样只会把生搬硬套的 shape 继续保留

**关键要求**：
- **鼓励一次改到位、大幅优化视觉和内容密度**：除 brand_assets 外都可动，一次把手册里对应类的动作都做到位
- **每页最多 refine 2 次**（防无限优化 · 但**若第 1 次已经大动到位、审查通过后可以就此收手**）

**硬红线**（只有一条 · 精简版）：
- **保 brand_assets**：跨页复用的页眉 / 页脚 / 导航条 / Logo / 水印 / 背景 + 主色 palette + 字体族 **一律不动**。除此之外，**所有版面、结构、装饰、图表、字号、层级都可以大改**。

#### 5.3 · 通用修改流程

不管是 `fixed_template` 修 bug 还是 `active_rebuild` refine 拔高，走一样的写入流程：

1. `+xml-get --presentation <deck_xml_presentation_id> --slide-id <sid>` 拉目标页当前 XML 存 local-cache
2. 生成新 XML（`active_rebuild` 拔高鼓励整页重写 · `fixed_template` 修 bug 只改必要 block）
3. 本地 lint（`error_count` 必须为 0）
4. `safe_update_slide.py --presentation X --slide-id S --content new.xml --local-cache cache.xml` 或 `+replace-slide` 只修改部分 block
5. exit 0 = 成功；exit 2（abort）= MainAgent 并发改过，脚本已同步 cache 为最新，基于新 cache 重试；同页 2 次 abort 记 fix_failed；exit 3 = 排障后记 fix_failed
6. **必须重新截图查看修改的结果**：lint 报错为 0 绝对不意味着所有的问题都被修复了，你必须做截图检查，以保证所有的视觉问题都得到了修复
7. **绝对不可以因为 source 本身就有 lint 报错就放行**：source 本身也有可能存在一些视觉错误，去校验 source 的 lint 报错情况没有任何意义；你的工作重点就是要修复所有的视觉错误，如果真的要跳过 lint 报错，必须查看截图才可以

#### 5.4 · 记录

**append `audit-r$N.jsonl`**：每条改动一行 `{round, page_num, slide_id, category, severity, message, action, page_role}`。
- `page_role` = `fixed_template` 或 `active_rebuild`
- `category` = `fix`（bug 修复）或 `refine`（拔高）
- `message`：bug 修复描述改了什么；refine 拔高列出**从范本借鉴了哪些元素 / 补齐了哪些差距**

### Step 6 · 出口

**触发条件**（任一）：
- **收到 MainAgent 收尾通知**（正常路径）：MainAgent 通过 `send_message` 告知"所有页面已写入完毕"→ 进入 5-10 轮收尾窗口
- **50 轮上限**：正常 poll 阶段就达到 50 轮（MainAgent 长时间未通知，可能失联）→ 立即 return
- **MainAgent 失联**：长时间无新增页且无消息 → 视为收尾通知处理

**收尾窗口顺序**（收到 MainAgent 通知后执行）：
1. **只补齐 bug 修复**：继续 poll 最多 10 轮（下限 5），把最后写入的几页全审 1 轮，修完所有能修的 P0
2. **上限触发条件**（任一）：达到 10 轮 / 上一轮 diff 出的新增页 = 0 且当前 P0 全部处理
3. 产出 `return-summary.md` 并 return —— **必须列**：本轮 refine 了哪些页（page_num + shape 数 before/after）+ 未 refine 的 active_rebuild 页各自具体理由（严禁"没时间"/"看起来 OK"类模糊回复）
4. **不要**通知用户（MainAgent 会做二次 `present_files` 交付最终稿）

**Organizer 工具约束**：

- **允许**：Read / Write（只写 `$WORK_DIR/.lark-slides/organizer/`）/ Bash / `+xml-get` / `+screenshot` / `template_lint_all.py` / `xml_inspect.py` / `safe_update_slide.py` / `+replace-slide` / `peek_agent`
- **禁止**：`send_message`（全程不发消息，包括 shutdown 响应）/ `wait_agent` / `+add-slide` / `+delete-slide` / **裸调 `+update-slide`**（必须走 safe_update_slide）/ ` drive +import/+export/+copy` / `present_files` / 单次 sleep 或 wait > 20s（poll 空轮的 15-20s sleep 除外）
