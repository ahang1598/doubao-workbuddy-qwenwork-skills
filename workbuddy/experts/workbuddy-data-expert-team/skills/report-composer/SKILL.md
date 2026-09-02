---
name: report-composer
description: 能够基于已有对话中提到的数据内容生成报告产物，支持产物形态有单图、轻报告、综合报告、数据看板，以Markdown、HTML、docx等文件进行承载，并落盘到产物目录。 注意该技能只能基于已有数据信息生成报告。
layer: L2
lintCheckVersion: v1
tags: [data-analysis]
disable-model-invocation: true
user-invocable: false
output_contract:
  mode: "path"
  schema:
    shape: string
    formats: array
    md_path: string
    html_path: string
    docx_path: string
    summary: string
    size_bytes: int
    uploaded: array
hidden-description: |
  数据产出类交付物的「统一收口」skill —— 一次调用完成 ①产物形态规划 ②图表 / Markdown / HTML
  生成 ③（可选）.docx 导出 ④落盘。面向分析报告（综合 / 异动归因 / 相关性 / 趋势预测）、
  问数单图、看板等一切数据交付物场景。调用方 `Skill("report-composer", args=...)` 触发后，
  本 skill 在调用方上下文里按 §三 决定形态与载体，组装产物并 `Write` 到
  `<workspace_folder>/artifacts/analysis`，返回 path-mode JSON。
  **只生成落盘，不上传**：上传归调用方 `report-generation-agent` 显式 emit `artifact-uploader`。
  图表 + HTML 工程约束 + DOCX 导出全部自包含（reference/ + scripts/chart_utils.py）。
  dispatcher-less（LLM 主笔）：不立 findings 契约、不做上下文隔离、不换渲染内核。
---

# report-composer —— 数据产出交付物的统一出口

数据产出类交付物（图表 / Markdown / HTML / .docx）的**统一收口**:调用方一次 `Skill("report-composer", args={...})`,本 skill 把「**规划形态 → 生成产物 → 落盘**」一气做完,返回 **path-mode JSON**。三个收益:工程约束**单一来源**(自包含,不跨 skill 漂移);产物目录固定 = 上传方一处发起 = 想漏都漏不掉;一处生成于是能**一处统一决定形态**(§三)。

> **本 skill 只生成 + 落盘,不上传 Studio**;上传由调用方 `report-generation-agent` 拿到 path 返回后显式 emit `artifact-uploader` 完成(详见 §四 出口红线 2)。

**适用域**:一切「数据驱动产物 + 上报」的诉求——分析报告 / 问数 / 看板等。

---

## 二、子能力拆解（内部五件事）

本 skill 把"出一份数据交付物"拆成五个子能力。**规划属编排层,留在本文 §三,不下沉 reference**;产物规格按载体下沉,**按载体挑文件、不按节裁内容**:

| # | 子能力 | 干什么 | 看哪里 |
|---|---|---|---|
| 1 | **产物形态规划** | 决定「单图 / 轻报告 / 综合报告 / 看板」× 「md / html / 两者」× 「要不要 .docx」,并规划骨架(spine) | **本文 §三** |
| 2 | **图表生成** | DataFrame → ECharts option → 可嵌入 HTML 片段 + 下钻交互 | `scripts/chart_utils.py` + `reference/html.md`(§f/§g/§h) |
| 3 | **Markdown 生成** | 文字版报告(结论先行 + 数据-SQL 溯源) | `reference/markdown.md` |
| 4 | **HTML 组装** | 自包含单文件 HTML(CDN / 浅色主题 / 移动端 / 组件 / 图表 / 自检) | `reference/html.md`(产 html 时**整份读,禁止按节挑**) |
| 5 | **落盘** | `Write` 到 `<workspace_folder>/artifacts/analysis`(只落盘,不上传) | 本文 §五 Step 5 |

> SKILL.md 做编排 + **全部产物形态决策(§三)**;reference 只暴露**产物载体规格**(md 怎么写 / html 怎么写)与**可选能力**(docx)。
>
> 🛑 **reference 挑选粒度 = 文件级,不是节级**:按规划决定**读哪几个文件**(只出 md 不读 `html.md`;不导 docx 不读 `html-docx.md`);但**一旦要产 html,`html.md` 必须整份读完**——工程底线(CDN / 主题 / **移动端** / 组件 / 图表 / 自检)分散在 §b~§i,按节挑读必然漏约束。曾因此漏掉移动端规则致手机端图表重叠(见 `docs/mobile-adaptation-regression.md`)。

---

## 三、自适应产物形态（决策单一来源）

**最终产出什么样不是固定的**,由本 skill 在 Step 1 规划。"想清楚再动手"能避免"先满配做一份再删一半"的浪费。**本节是产物形态决策的唯一来源**(reference 不重复)。

> 📌 "token 宝贵"只作用于**产物形态**(少写没必要的章节),**不作用于工程约束的阅读**——`html.md` 该整份读还是整份读(见 §二)。

判断的输入有两个:
1. `args.shape` / `args.output` / `args.export_docx`——调用方显式意图(传了就**尊重**,不要自作主张覆盖)。
2. **Step 2 提炼产物**——几条发现?每条发现有没有配套图表/建议素材?是否为单图/一屏总览?(判定素材来源 = §五 Step 2 提炼出的骨架)

> 决策只看场景特征,**不绑定上游 skill 名字**——本 skill 的语义独立于谁来调用。

### 三.1 形态决策(shape)

形态决定**版面繁简**。四档由轻到重,`shape=auto` 时**按场景信号判定**:

| shape | 长什么样 | 场景信号(= auto 判定条件,基于 Step 2 提炼产物) |
|---|---|---|
| `chart` | 一张图 + 一句话结论,无 KPI 网格 / 建议 | Step 2 提炼出 1 条发现 + 1 个图表 option,无 KPI / 无建议素材 |
| `lite` | 少量 KPI(≤3) + 1~2 个 section + 图 + 精简结论 | Step 2 提炼出 1~2 条发现,聚焦单一主题(**兜底档**) |
| `full` | Hero KPI 网格 + 多 section + SQL 折叠 + 综合洞察 + 建议(≥3) | Step 2 提炼出 ≥ 3 条发现,或有明确行动建议素材 |
| `dashboard` | 多卡片仪表盘网格,一屏概览,每卡一指标 + 迷你图 | Step 2 提炼出多个并列指标 + 强调一屏总览而非叙事 |

> 判定顺序:`chart` → `dashboard` → `full` → 其余落 `lite`。
> ⚠️ 不要把 `chart`/`lite` 硬撑成 `full`:没有建议素材却强行编三条,是"过拟合 + 凑数",稀释可信度。宁可诚实出 `lite`。

### 三.2 载体决策(formats)——理解 why,别死记

**Markdown** 的不可替代价值:可当文章顺序读、数据-SQL 可溯源、能打印 PDF、能按 SQL 编号迭代修改 → 有**值得当文字读的叙事**时要它。
**HTML** 的不可替代价值:可交互可视化、点击下钻、一屏仪表盘 → 有**值得点着看的可视化**时要它。

由此推出**载体原则**:既有叙事又有可视化 → 两者都出;天然单模态 → 只出一个(一张孤图 / 一个看板只出 html,配 md 纯凑数);拿不准 → 倾向 `lite` 出两者但 md 写精简。

**`output=auto` 解析**:`chart` / `dashboard` → `["html"]`(md 价值低);`lite` → `["md","html"]`(md 精简);`full` → `["md","html"]`。

> 调用方传了 `args.output`(`md` / `html` / `both`)就**尊重覆盖**。

### 三.3 .docx 导出决策

`.docx` 给"发邮件 / 进 OA / 离线归档"用。默认**关**(`export_docx=false`);`true` 时在**已产出 html** 基础上多导一份(`html2canvas` 截非图表区 + `html-docx` 转换,见 `html-docx.md`)。**前置条件**:必须有 html;若 `output=md` 却要 docx → 提示冲突或自动补出 html 再转。

### 三.4 报告骨架(spine)与决策速查表

定了 shape / formats,再在生成前**列出骨架**(哪些 section、每段对应哪次取数),md 与 html 用**同一副骨架**,天然一致。

- `chart`:[单图 + 一句结论]。
- `lite`:[精简 KPI] → [发现 1(图 + 解读 + SQL)] →(可选)[发现 2] → [一句话结论]。
- `full`:[摘要] → [分析背景] → [数据概览 / Hero KPI] → [核心发现 1..N(一句话结论 + 表/图 + 多角度解读 + SQL 折叠)] → [详细分析] → [综合洞察] → [行动建议 ≥3]。渲染细节:md 见 `markdown.md` §三,html 见 `html.md` §j.2。
  > **摘要(BLUF)仅 `full` 出**:3~5 条要点,串联核心结论 + 最关键 1~3 条建议(均带 `[📊 SQL-N]`),供管理层 30 秒速读;是末尾"综合洞察 + 行动建议"的前置浓缩版,不替代末尾完整版。
- `dashboard`:[顶部筛选/时间范围] → [指标卡网格(核心数 + 迷你图)] → (可选)[底部汇总]。

**骨架对齐规则**:同时出 md + html 时,**section 一一对应、SQL 编号一致、KPI / 结论数值一致**。
**缺省兜底**:识别不出明确信号 → `lite` + `md`+`html`(精简),宁可少不可过度。

### 三.5 走查例(展示自适应判断)

- **单图**:上文只有一条「各城市订单量」查询 → `shape=chart` → `formats=["html"]`(单图配 md 价值低) → `md_path=null`。
- **综合报告 + Word**:上文 3 对「取数 + 归因」+ 有建议素材,`export_docx:true` → `shape=full` → `formats=["md","html"]` + docx。

---

## 四、调用契约

通过 `Skill("report-composer", args={...})` 调用,**无 Python dispatcher**——LLM 自己消费 SKILL.md + 按规划下钻的 reference,组装产物、`Write` 落盘,返回 **path-mode JSON**。

### 入参（`args`）

| 字段 | 必填 | 说明 |
|---|---|---|
| `title` | ✅ | 产物主标题(md 一级标题 / html `<title>` / 页面顶部) |
| `subtitle` | ❌ | 副标题(时间范围 / 数据来源 / 报告类型) |
| `shape` | ❌ | 形态:`auto`(默认,自动判断)/ `chart` / `lite` / `full` / `dashboard` |
| `output` | ❌ | 载体:`auto`(默认,按 shape 解析)/ `md` / `html` / `both` |
| `export_docx` | ❌ | 是否额外导出 `.docx`,默认 `false`(仅在产出 html 时可用) |
| `design_brief` | ❌ | 一句话 html 版面引导;范例见 `html.md` §k |

> **落盘目录固定,不可由调用方指定**:一律 `Write` 到 `<workspace_folder>/artifacts/analysis/report_<ts>.{md,html,docx}`。意义:①上传方总能在同一位置找到产物,避免路径漂移;②防止幻觉写到 `.kanban_output` 等目录导致漏传。
> **不接受 `output_dir` / `upload` / `domain` 入参**——上传目标域 `analysis` 由调用方在下一步指定。


### 返回（path-mode,强制）

```json
{
  "mode": "path",
  "shape": "full",
  "formats": ["md", "html"],
  "md_path": "<workspace_folder>/artifacts/analysis/report_<ts>.md",
  "html_path": "<workspace_folder>/artifacts/analysis/report_<ts>.html",
  "docx_path": null,
  "size_bytes": 0,
  "summary": "<标题 + 形态 + 章节数 + 图表数>",
  "uploaded": []
}
```

> 未产出的载体 `*_path` 为 `null`,`formats` 只列实际产出的。
> **`uploaded` 固定返回 `[]`**,且**不带 `studio_path` / `studio_link`**——本轮尚未上传,防止上层误把「落盘完成」当「上传完成」。

**两条出口红线**:

1. **path-mode**:返回里**只有本地路径**,**绝不**把 md / html 字面量当返回值,也**不在响应正文粘产物本体**(> ~5 行的片段都不要)。产物动辄上万字,粘进上下文是双倍 token 且污染调用方。
2. **只落盘不上传**:产物**只能** `Write` 到 `<workspace_folder>/artifacts/analysis/`,**不得**写 `SyncLocal` / 裸调 `upload.py` / **emit `Skill("artifact-uploader")`** / 写到该目录外。上传执行体单点归属 `report-generation-agent`,才不破坏分层与 skill-history 记账。

---

## 五、标准动作序列

### Step 1 · 规划产物形态

依据**本文 §三**,据 `args.shape` / `args.output` / `args.export_docx` 与上文场景信号,**先定下**:出什么 shape、哪些 formats、要不要 docx、骨架有哪些 section。`auto` 时按 §三 解析规则;调用方显式传了就尊重。

### Step 2 · 读取当前对话上下文并提炼报告骨架

进入本 skill 时,**先自读当前对话上下文**。分两个子动作完成:

**Step 2a · 按 turn 顺序读取,筛选相关内容**
- 按 `turn` 顺序读上下文:`user` = 用户报告诉求,`assistant` = 结论,`tool` = SQL / 命令 / 产物链接(证据)
- 以**用户本轮报告诉求**为主线索过滤:只留和主题相关的取数与结论,**滤掉主 Agent 的试错岔路**
- 每个数字、每个结论都必须能追溯到上下文;查询过但没得出明确结论就如实说明,**绝不编造**上下文里没有的数据

**Step 2b · 提炼报告骨架(发现清单)**
- 提炼 N 条发现,N 随 shape 决定:`chart`=1 / `lite`=1~2 / `full`≥**3** / `dashboard` 按并列指标数
- 每条发现 = **一句话结论 + 证据引用**(SQL 编号 / assistant 结论 / 产物链接)
- 同时按 `html.md` §j.1 清单补齐:KPI / sections / 每段 SQL / 图表 option / 综合洞察 / 行动建议(轻量 shape 按需取子集)
- 骨架同时对齐 md 与 html 的 section(承接 §三.4 spine)
- **提炼不足对应门槛时按 §三 诚实性红线降 shape,不凑数**(例如只能提炼出 2 条发现却传了 `shape=full`,降为 `lite`)

Step 2 的产出是后续 §三 shape 判定与 Step 3 生成产物的**唯一输入源**。

### Step 3 · 按规划生成产物（同一份数据,按 formats 出载体）

用上文给的系统时间给所有产物命名,便于配对归档。

确定变量workspace_folder的值：从上下文内容中正常可以找到定义的值，否则默认值为`~/.wedata`作为兜底。

> ⚠️ **命名 + 目录红线(所有形态一律遵守)**:落盘路径一律 `<workspace_folder>/artifacts/analysis/report_<ts>.{md,html,docx}`——**前缀必须 `report_`**(禁止 `dashboard_` / `kanban_` 等按形态另起),**目录不得改**。调用方只在此处按此命名取产物上传;违反 = 产物拿不到 Studio 链接。该目录已存在,无需检测。

- **要 md**:按 `reference/markdown.md` 模板组装 → `Write` 到 `<workspace_folder>/artifacts/analysis/report_<ts>.md`。
- **要 html**:按 `reference/html.md`(产 html 时**整份读完**:工程约束 §a-k + 组件 §d + 图表 §f/g/h + 自检 §i)组装自包含单文件 HTML → `Write` 到 `<workspace_folder>/artifacts/analysis/report_<ts>.html`。图表序列化用 `scripts/chart_utils.py` 的 `df_to_echarts_option()`。
  > 注:此处「整份读」是指**本 skill 被触发后**这一轮 LLM 在生成 html 前 `Read` reference;**调用方在 emit 本 skill 之前不要做这次 Read**(见 §〇)。
  >
  > 🛑 **落盘前移动端门禁(强制,漏一条即回炉)**——手机端打开是高频场景,以下 4 条最易漏,`Write` 前逐条确认(完整 7 条见 `html.md` 开头「移动端红线速查」):
  > 1. `<head>` 有 `viewport` meta(缺了所有响应式 CSS 全废)。
  > 2. **每个** `setOption` 是 `{baseOption, media:[maxWidth:768, maxWidth:480]}`(走 `df_to_echarts_option()` 自动带;**手写 option 必须自己加**)。
  > 3. **每个**图表容器带 `class="chart-container"` + CSS `≤768→320px` / `≤480→260px` 覆盖。
  > 4. 挂了 `window.addEventListener('resize', ...)` 遍历 `CHART_INSTANCES` 调 `.resize()`。
  >
  > 对**所有 shape 一致强制**(含 `chart` / `dashboard`),不因产物轻量而豁免。
- **同时出 md+html 时**:两者承载**同一份结论与同一批数据**,KPI / 结论 / SQL 编号必须一一对应,不允许打架。

### Step 4 ·（可选）DOCX 导出

`args.export_docx=true` 且产出了 html 时,按 `reference/html-docx.md`(§L)生成 `report_<ts>.docx`(`html2canvas` + `html-docx`,均在 `html.md` §b 第二档白名单内)。否则跳过。

### Step 5 · 落盘完成，交回调用方

🛑 **本 skill 到此结束,不涉及上传**:产物已 `Write` 到 `<workspace_folder>/artifacts/analysis/`;上传由调用方拿到 path 返回后显式 emit `Skill("artifact-uploader", op="upload_batch")`。**禁止**自行 emit 上传 skill 或裸调 `SyncLocal` / `upload.py`(重复触发 = 重复上传 + 账单错乱)。

### Step 6 · 返回 path-mode JSON + 收尾自检

返回前做一次**落盘对账自检**:

> ✅ 自检要点:
> - `formats` 里每个载体都已 `Write` 到 `<workspace_folder>/artifacts/analysis/report_<ts>.<ext>`,且 `md_path` / `html_path` / `docx_path` 与 `formats` 对齐(未产出的为 null)。
> - 路径写错(不在该目录)→ **回到 Step 3 重写**,不许直接返回(= 调用方上传时会漏掉)。
> - **产了 html 的**:Step 3 移动端门禁 4 条已逐条确认(viewport / `{baseOption,media}` 两档 / `.chart-container` 断点高度 / `resize` 监听)。任一条没做到 → **回 Step 3 补齐后重新落盘**,不许带着已知移动端缺陷返回。

自检通过后,按 §四「返回」组装(`uploaded` 字段固定 `[]`),**不在正文复述产物本体**。

---

## 六、与其它 skill 的关系

- **内部自包含(生成)**:图表、HTML 工程约束、md 模板、docx 导出全在本 skill 的 `reference/*` + `scripts/chart_utils.py`,**不读取任何外部 skill**。
- **交回调用方(上传)**:`report-generation-agent` 拿到 path 后显式 emit `artifact-uploader`(`op="upload_batch"`);本 skill 只落盘。
- **能力归并**:`chart-renderer` 的图表能力已内化到本 skill,数据产出图表以本 skill 为准。

---