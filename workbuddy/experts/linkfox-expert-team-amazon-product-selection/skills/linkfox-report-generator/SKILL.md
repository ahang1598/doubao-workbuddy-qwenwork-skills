---
name: linkfox-report-generator
description: 生成 HTML 分析报告。按 references/analysis-layouts.md 的组件库写一段 HTML 内容片段（Write 到文件），再调 scripts/inject_report.py 注入到预制模板 assets/template-analysis.html、按会话目录规则落盘。评论分析、市场洞察、关键词分析、竞品分析、合规检测等所有报告类型共用同一套组件库与视觉风格，按数据特征选组件。
---

# 报告生成器

用户需要"报告 / 总结 / 分析输出 / 一份 HTML"时，不得在对话里直接拼长报告正文；必须走：Read layouts → 设计结构 → 产 HTML 片段 Write 到文件 → 调 `inject_report.py` 拿最终报告路径 → 告知用户。

## 何时触发

任意一条命中即调用本 skill：

1. **显式意图**——中文"生成报告 / 分析报告 / 市场分析 / 竞品分析 / 调研报告 / 精美页面"；英文 `generate report / analysis report / market research report / competitor analysis / render html`。
2. **长输出兜底**——预计**叙述性正文** > 400 字。禁止在对话里拼长文。
3. **数据呈现**——上一轮已从其他 skill 拿到结构化数据需要呈现。

### 不触发

正文 ≤ 400 字的简单对话式回答（事实问答、参数澄清、错误说明、几句话讲清的解释）直接回。**结构化列表类**（候选清单表格、榜单、对比表、ASIN / 关键词清单）由前端渲染卡片或直接对话表格输出，标注数据范围/排序依据/关键假设即可——只有**叙述性**长文才走本 skill。

## 生成流程

### Step 1 — 读组件规范

会话内尚未 Read 过则执行：

```
Read references/analysis-layouts.md
```

列了 17 个组件（Report Header / KPI Cards / Content Section / Chart Container / Data Table / Tags / Quote Cards / Tag Cloud / Insight List / Comparison Grid / Progress Bar / Summary Box / SWOT Grid / Footer / Canvas Chart / Data Source / Evidence Image Grid），每个都有精确 HTML 结构与 class 名。**只用这份文件里出现的组件**，禁止自创样式或引入外部 CSS。

### Step 2 — 设计报告结构

按数据特征选组件：

| 数据 | 组件 |
|---|---|
| 核心指标 | KPI Cards |
| 分布/占比 | 饼/环形图 + Progress Bar |
| 趋势 | 折线图 |
| 排名 / TOP N | Data Table |
| 多维度对比 | 雷达图 + Comparison Grid |
| 原始文本证据 | Quote Cards |
| 关键词/话题 | Tag Cloud + Data Table |
| 结论/建议 | Summary Box + Insight List |
| 四维度综合研判 | SWOT Grid |
| 图片视觉证据（合规） | Evidence Image Grid + Evidence Compare |

**硬约束**：

1. 不输出 `<!DOCTYPE>` / `<html>` / `<head>` / `<style>` / `<body>` / `<h1>` —— 模板提供。
2. 只允许一个 `.report-header`（顶部总标题）；其他章节一律 `<section class="content-section"><h2>...</h2>...</section>`。多 stage 报告时 stage 内的分析维度用 `<h3>`（进 TOC 二级），禁止为每个维度单独开 section。
3. 数字/事实全部来自输入数据；缺失写"数据未提供"，**禁止编造**。
4. 数字千分位（`12,847`），百分比保留 1 位小数。
5. 对立维度必须视觉对比：正/优绿（`--sentiment-positive`）、负/劣红（`--sentiment-negative`），并列柱状图或同 section 上下排列。
6. 图片 URL 只用数据中真实字段（合规相似作品的 `path/pathThumb`、商品主图等），禁止编造；`<img>` 必须带 `alt` + `loading="lazy"`。
7. **数据源标注（必须）**：每个含统计/度量数字的 `content-section` 末尾必须有 `<div class="data-source">`，列出所有贡献数据的 skill 短名；若含 Python 预计算的派生值，还须追加 `.ds-computed` 子块写明指标名与计算方式（如"由 Python 对 16 个 SKU 逐行汇总得出"）。纯定性分析/建议章节可省略。详见 `analysis-layouts.md § 16`。
8. **禁止 LLM 生成统计数字**：报告里的所有**统计/度量数字**只允许两种来源——① skill 工具返回的 JSON 原始值（直接引用）；② Python 预计算脚本的 stdout 输出值。LLM **禁止在上下文中心算/估算/推断任何统计数值**（包括但不限于：求和、平均、占比、增长率、排名变动）。需要派生统计值时，必须走 Step 2.5 的预计算流程。日期、ID、序号等非度量数字不受此约束。

### Step 2.5 — 统计预计算（需要派生数字时必须执行）

如果报告需要**任何派生统计值**（求和、平均、占比、增长率、TOP N 排名、分布统计等），必须先用 Python 脚本计算并拿到结果，不得由 LLM 心算。

**预计算数据完整性（必须严格遵守，不可跳过）**：

1. **程序化全量读取**：用 openpyxl / pandas / json.load 读取源文件全部记录，禁止手动转写到代码变量（必然遗漏）。
2. **筛选必须显式**：所有过滤条件写在代码里且在报告 data-source 中注明（如"仅统计 rating ≥ 4 的评论"），禁止暗箱跳行。
3. **逐项展开**：汇总计算必须遍历源数据逐条计算，禁止压缩一行式算术（如 `600*59.99*2 + 400*89.99*2`）。

**产物**：一份 JSON（stdout 或文件均可），包含报告所需的全部派生指标。后续 Step 3 写 HTML 时，统计数字**只从这份 JSON 里取**；来源与计算方式在 section 末尾的 `data-source` / `.ds-computed` 中标注。

**判断标准**：如果一个数字在原始 JSON 里能直接取到（如 `price`、`rating`、`reviewCount`），直接用、标 skill 短名；如果需要任何算术运算才能得出，就必须走预计算。

**跳过条件**：如果报告只展示原始值（无需派生计算），可跳过本步骤。

### Step 3 — 产出 HTML 内容片段

按 layouts 组件写完整片段，从 `.report-header` 到 `.report-footer`。

**图表**：

- 交互图（tooltip / 缩放 / 复杂图如雷达/桑基/地图）→ ECharts，初始化代码用块包起放片段末尾：
  ```
  <!-- ECHARTS_SCRIPTS -->
  var chart1 = echarts.init(document.getElementById('chart_xxx'));
  chart1.setOption({ ... });
  <!-- /ECHARTS_SCRIPTS -->
  ```
- 静态图 / 需离线（数据点 ≤10 / 邮件转发 / 独立分享）→ Canvas，用模板内置的 `drawBar` / `drawLine` / `drawDonut`：
  ```
  <!-- CANVAS_SCRIPTS -->
  drawBar("chart_xxx", ["Q1","Q2","Q3"], [{"label":"2025","data":[100,150,120],"color":"#4f46e5"}]);
  <!-- /CANVAS_SCRIPTS -->
  ```

脚本会把这两个块从片段里抠出注入到模板底部对应 marker。片段主体不需要 `<script>`。

**图表色板**：`['#4f46e5','#06b6d4','#8b5cf6','#f59e0b','#10b981','#ef4444','#ec4899','#6366f1']`

**图表容器尺寸**：ECharts 用 `<div id="..." style="width:100%;height:XXXpx;">`（禁止固定像素宽）；Canvas 用 `<canvas id="..." width="1024" height="340">`。

### Step 4 — Write 片段到文件

```
Write ./<slug>.fragment.html   # 例如 ./market-analysis.fragment.html
```

禁止把片段拼进 Bash `command` 参数、shell 变量、`python -c` 内联（会被 shell 转义 / argv 长度 / 全角标点炸掉）。**永远 Write 落文件 + `--content-file` 传路径**。

### Step 5 — 调注入脚本

```
Bash(
  command="python scripts/inject_report.py \
    --content-file ./<slug>.fragment.html \
    --language <zh|en|ja|ko> \
    --title <english-slug>"
)
```

同步/前台调用（不要 `run_in_background`，脚本几百毫秒完成）。stdout 返回：

```json
{
  "path": "/.../linkfox/2026-07-17/<session>/reports/market-analysis-1737093240123456.html",
  "bytes": 45678,
  "language": "zh",
  "title": "market-analysis"
}
```

和一行 `Saved full response: <path> (<bytes> bytes)`。

### Step 6 — 告知用户

给用户最终 HTML 路径（**不要**把整份报告全文读回上下文）+ 简短一句话总结即可。

## CLI 参数

| Flag | 必填 | 说明 |
|---|---|---|
| `--content-file <path>` | 是 | HTML 片段文件路径 |
| `--language <zh\|en\|ja\|ko>` | 是 | 报告【主体阅读者】的语言，写入 `<html lang=...>`。见下 |
| `--title <english-slug>` | 否 | 文件名前缀。仅允许 `^[a-zA-Z-]+$`；不传用默认名 |

### `--language` 口径

**报告主体阅读者的语言**，一般 = 用户自己的语言，不是"目标市场消费者的语言"。

- ✅ 中国卖家用中文问要一份 amz-US 竞品分析 → `--language zh`。主体中文（给卖家看），报告里嵌入的 US listing 段落自然用英文（给消费者看，属"必要原语嵌入"，不受此 flag 限制）。
- ❌ 反例：当"目标市场语言"传 → 中国卖家收到读不懂的英文分析。

## 输出

- **路径**：`<root>/<YYYY-MM-DD>/<session>/reports/<slug>-<ts_us>.html`，`<root>` 依次尝试 `$ACPX_WORKSPACES` 第一段下的 `linkfox/` → `cwd/linkfox` → `~/linkfox` → `$TMPDIR/linkfox`；自动 mkdir。**禁止写 `/tmp`**。
- **报告宽度**：全屏内容区 1200px 居中；小屏自动收缩。

## 反馈

- 片段为空 / 文件不存在：exit 3 或 1，stderr 有明确原因。
- 参数错误：exit 64。
- 写盘失败：exit 4。
- 报告尺寸过大：**只给 `path` 给用户**，不要再 Read 整个文件回上下文。
