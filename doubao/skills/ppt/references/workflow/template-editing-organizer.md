# 模板遵循工作流 · Organizer 部分

本文档是 [template-editing-main.md](template-editing-main.md) 的可选 Organizer 流程。仅在用户明确要求额外审查、复验或生成后优化时启用，按用户指定的范围执行。普通制作或编辑默认在写入成功后交付，页数、原稿附件和内容保留要求不触发本流程。

使用以下流程前，任务消息须包含用户已要求本轮额外审查或优化的说明；缺少该说明时直接返回，由 MainAgent 继续默认制作流程。


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
- **Track 1 · Bug 修复**（所有页型都做）：修视觉错误，走 A/B/C 三项审查
- **Track 2 · Refine 优化**（仅 `active_rebuild` content 页）：按 [`../refine/<style>.md`](../refine/) 里的 refine 手册对页面走 enrich(补内容) / reframe(换表达) / decorate(增加视觉) 三段决策。`fixed_template` 页禁止 refine


## 四、Organizer 流程（6 Steps）

### Step 1 · 冷启动 Read（严格按顺序）

subtask 从 MainAgent 拿到 7 字段(`WORK_DIR` / `skill_root` / `deck_xml_presentation_id` / `deck_url` / `first_page_slide_id` / `is_manuscript_apply` / `style_doc`)。冷启动读文档顺序:

1. `<skill_root>/SKILL.md`
2. `<skill_root>/references/workflow/template-editing-organizer.md`（即本文档）
3. **`<skill_root>/references/refine/<style_doc>.md`**（Track 2 refine 手册 —— 该 style 的气质定位 + Refine 三段决策树 enrich/reframe/decorate）
4. `<skill_root>/references/xml/xml-schema-quick-ref.md`

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
- **上一轮空轮**(`+xml-get` 后 diff 出 0 张新页 · 也没有第 1 页 shape 数变化)→ sleep **15-20s** 再 poll。此时 MainAgent 在忙别的事(写 XML / 图片上传),空转反而应该给它时间。
- **429 / 5xx / timeout** → 指数退避重试(1s → 2s → 4s → 8s,最多 4 次),不算空轮

`+xml-get --presentation <deck_xml_presentation_id> --output $WORK_DIR/.lark-slides/organizer/current-round-N/full.xml` 拉 deck 当前全稿 → 用 `xml_inspect.py --mode summary` 解析出每页 `(slide_id, shape_count)` 对,跟上轮做 diff:

- 上轮不存在的 slide_id → 加入本轮审查
- `first_page_slide_id` shape 数从 0 变 > 0 → MainAgent 刚覆盖了第 1 页,加入本轮审查
- 空判定(既无新增 id 也无第 1 页变化)→ 记 skip · sleep 15-20s 再 poll

### Step 4 · 抽单页 XML

对每个新增 slide_id，从 full.xml 里 slice 出该页 XML 存到 `current-round-N/slide-<sid>.xml`（用 `xml_inspect.py --mode raw --slide-id <sid>`）。

### Step 5 · 审查 + 修复（按页型分支）

对每张新增页做完整的**审查 + 修复**闭环：先做三项审查找 bug，再按页型走对应修复动作。

**页型分工**:`fixed_template` 页只审查 + 修 bug 保护模板;`active_rebuild` 页按 refine 手册三段决策树(enrich/reframe/decorate)拔高视觉和信息密度 · refine 是核心工作 · 不是审查后的可选补充。审查发现的 bug 顺手在 refine 里一起修。看下面 5.2 的动作顺序。

#### 5.1 · 审查（所有页型都做）

- **A · 关键页壳层完整性**：从 `page-plan.md` 读该页「页型策略」+「来源模板页」→ 按下面规则对照 deck 该页：
  - **`fixed_template` 页**（规则 5.1）：Read `source-slides/slide-NN.xml` 拿完整模板版式 · 所有非文字属性必须和 source 完全一致；模板元素被删/改 fill/改类型 → **P0**；只有文字内容、文本框尺寸、元素位置允许变，其他改动都算违规
  - **`active_rebuild` 页**（规则 5.2.1 硬性保留清单）：**Read `manifest/content-skeletons/slide-NN.content-skeleton.xml`（parse_template.py 已自动提取的干净 brand_assets 骨架）而非 source-slides** —— 骨架里的 img/shape/line 就是必须保留的品牌资产（背景/页眉/页脚/装饰线）。骨架元素在 deck 该页找不到 → MISSING **P0**；这些元素坐标/主 fill 色变了 → MUTATED_STRUCTURE **P0**；元素在但文字变了 → MUTATED_TEXT **P1**。**不要 Read source-slides**（内容占位符会误导审查判断）
  - **超出保留清单的模板组件**（金字塔/半圆拱/齿轮等特殊的复杂case）：`active_rebuild` 页默认允许删除，不算问题；只有用户在 query 里明确点名要求保留时才审查
- **B · 目录-章节-导航一致性**：从服务端全稿抽目录 bullets / 章节页大标题 / 页内导航文字做集合对齐；比如明明 plan 里面只写了4个章节，但是目录页出现了5个或者3个；不一致 → P0
- **C · 原稿内容保留**（仅 `is_manuscript_apply=true`）：从原稿抽关键数字/单位/事实 token，检查服务端 XML 是否至少出现一次；不出现 → P0（全稿完整时）/ P1_PENDING（未完整时）

#### 5.2 · 修复动作（按页型分支）

对每张审查完的页，按 `page-plan.md` 里的**页型策略**分两条路走：

**若页型 = `fixed_template`**（cover / toc / chapter / transition / ending）：
- **只修 bug**（不做 refine · 保护模板辨识度）
- 触发条件：5.1 审查里任何 P0 / P1
- 修法：改文字内容 / 调文本框尺寸 / 调元素位置对齐；**其他版式全保留**

**若页型 = `active_rebuild`**（content 页）：

每个 `active_rebuild` 页按对应 refine 手册至少优化一次；不运行 lint 或计算 `refine_triggers` 作为前置条件。`return-summary.md` 记录本轮优化页和具体改动。

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
   - **起点建议**:需要大改时(页面 shape 数 > 60 装饰堆砌)先 Read `manifest/content-skeletons/slide-NN.content-skeleton.xml` 拿干净 brand_assets 骨架,再按手册重新组织内容和视觉,从零建。不要基于 MainAgent 已写的 authored 版做微调 —— 那样只会把生搬硬套的 shape 继续保留

**关键要求**：
- **鼓励一次改到位、大幅优化视觉和内容密度**：除 brand_assets 外都可动，一次把手册里对应类的动作都做到位
- **每页最多 refine 2 次**（防无限优化 · 但**若第 1 次已经大动到位、审查通过后可以就此收手**）

**硬红线**（只有一条 · 精简版）：
- **保 brand_assets**：跨页复用的页眉 / 页脚 / 导航条 / Logo / 水印 / 背景 + 主色 palette + 字体族 **一律不动**。除此之外，**所有版面、结构、装饰、图表、字号、层级都可以大改**。

#### 5.3 · 通用修改流程

不管是 `fixed_template` 修 bug 还是 `active_rebuild` refine 拔高，走一样的写入流程：

1. `+xml-get --presentation <deck_xml_presentation_id> --slide-id <sid>` 拉目标页当前 XML 存 local-cache
2. 生成新 XML（`active_rebuild` 拔高鼓励整页重写 · `fixed_template` 修 bug 只改必要 block）
3. `safe_update_slide.py --presentation X --slide-id S --content new.xml --local-cache cache.xml` （默认请求跳过 lint）或 `+replace-slide --no-lint` 只修改部分 block
4. exit 0 = 成功；exit 2（abort）= MainAgent 并发改过，脚本已同步 cache 为最新，基于新 cache 重试；同页 2 次 abort 记 fix_failed；exit 3 = 排障后记 fix_failed

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
4. **不要**通知用户（MainAgent 会用 `present_files` 交付本轮结果）

**Organizer 工具约束**：

- **允许**：Read / Write（只写 `$WORK_DIR/.lark-slides/organizer/`）/ Bash / `+xml-get` / `xml_inspect.py` / `safe_update_slide.py` / `+replace-slide` / `peek_agent`
- **禁止**：`send_message`（全程不发消息，包括 shutdown 响应）/ `wait_agent` / `+add-slide` / `+delete-slide` / **裸调 `+update-slide`**（必须走 safe_update_slide）/ ` drive +import/+export/+copy` / `present_files` / 单次 sleep 或 wait > 20s（poll 空轮的 15-20s sleep 除外）
