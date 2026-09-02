# Analysis Report Component Library

模板已内置全部组件 CSS。**LLM 只输出 `<!-- CONTENT_START -->` 到 `<!-- CONTENT_END -->` 之间的 HTML 片段**，只能使用下列 class 名，不得自创样式或引入外部 CSS。

## 全局规则

1. 不输出 `<!DOCTYPE>` / `<html>` / `<head>` / `<style>` / `<body>` / `<h1>`。
2. 全文只允许一个 `.report-header`（顶部总标题）；其它章节用 `<section class="content-section"><h2>...</h2>...</section>`。多 stage 报告每 stage 一个 `content-section`，内部分析维度用 `<h3>`（自动进目录二级），禁止为每个维度单独开 section。
3. 数字/事实必须来自 `data` / `materials`；缺失写"数据未提供"，禁止编造。数字用千分位（`12,847`），百分比保留 1 位小数。
4. 不引入外部字体/CDN。例外：`data` 里的业务图片 URL（合规相似作品、商品主图等）必须用 `<img>` 渲染。
5. ECharts 初始化放 `<!-- ECHARTS_SCRIPTS -->…<!-- /ECHARTS_SCRIPTS -->` 之间；Canvas 放 `<!-- CANVAS_SCRIPTS -->…<!-- /CANVAS_SCRIPTS -->` 之间。
6. 图表色板：`['#4f46e5','#06b6d4','#8b5cf6','#f59e0b','#10b981','#ef4444','#ec4899','#6366f1']`

## 公共设计约束

- `.report-header .report-meta` 必须标注数据周期（起止日期或"数据快照日期: YYYY-MM-DD"）；非全量分析加说明"共 N 条 / 抽样 M 条 / 采样规则"。
- 对立维度（正/负、优/劣）必须视觉对比：正面绿（`--sentiment-positive`）、负面红（`--sentiment-negative`），并列柱状图或同 section 上下排列。
- `content-section` 只用 `var(--shadow-sm)`，不叠 border + shadow；相邻 section 间距统一 `var(--space-lg)`。

## 1. Report Header

```html
<div class="report-header">
  <h1>报告主标题</h1>
  <div class="report-subtitle">副标题或一句话摘要</div>
  <div class="report-meta">数据周期: 2026-01-01 ~ 2026-05-31 · 数据来源: Amazon US</div>
</div>
```

## 2. KPI Cards

顶部 2~4 个核心指标。容器加 `cols-2` / `cols-3` / `cols-4`；`.kpi-change` 配 `.up` / `.down` / `.flat`。

```html
<div class="kpi-grid cols-4">
  <div class="kpi-card">
    <div class="kpi-label">总评论数</div>
    <div class="kpi-value">12,847</div>
    <div class="kpi-change up">↑ 23% vs 上月</div>
  </div>
  <!-- 更多 kpi-card ... -->
</div>
```

## 3. Content Section

所有正文块的容器。`<h2>` 必须是首个子元素（引用按钮依赖它的文本）；子标题只用 `<h3>` / `<h4>`。

```html
<section class="content-section">
  <h2>章节标题</h2>
  <p>正文段落...</p>
</section>
```

## 4. Chart Container（ECharts）

图表 div 必须 `style="width:100%;height:XXXpx;"`（禁止固定像素宽）；并排用 `chart-row cols-2` / `cols-3`。

```html
<div class="chart-container">
  <div id="chart_sentiment_pie" style="width:100%;height:360px;"></div>
</div>

<div class="chart-row cols-2">
  <div class="chart-container"><div id="chart_a" style="width:100%;height:320px;"></div></div>
  <div class="chart-container"><div id="chart_b" style="width:100%;height:320px;"></div></div>
</div>
```

**ECharts grid 居中**（图表内容必须视觉居中）：
- 水平条形图（yAxis=category）：`grid: { left: '25%', right: '5%', top: 40, bottom: 40 }`，**不要** containLabel
- 垂直柱状图 / 折线图：`grid: { left: '10%', right: '5%', top: 40, bottom: 60, containLabel: true }`
- 饼/环形图：`center: ['50%', '50%']`

## 5. Data Table

外层必须包 `.data-table-wrapper`（处理横向溢出）；数字列加 `.num`（右对齐+等宽），需换行列加 `.wrap`。

```html
<div class="data-table-wrapper">
  <table class="data-table">
    <thead><tr><th>关键词</th><th class="num">搜索量</th><th class="num">点击率</th><th>趋势</th></tr></thead>
    <tbody>
      <tr><td>usb c cable</td><td class="num">284,000</td><td class="num">12.3%</td><td><span class="tag tag-positive">上升</span></td></tr>
    </tbody>
  </table>
</div>
```

## 6. Tags & Sentiment Badges

```html
<span class="tag tag-positive">正面</span> <span class="tag tag-neutral">中性</span> <span class="tag tag-negative">负面</span> <span class="tag tag-accent">重要</span> <span class="tag tag-muted">其他</span>
```

## 7. Quote / Review Cards

情感色条用 `.positive` / `.negative` / `.neutral`。

```html
<div class="quote-list">
  <div class="quote-card positive">
    "This cable is amazing, charges super fast."
    <div class="quote-meta">★★★★★ · 2026-05-12 · Verified Purchase</div>
  </div>
</div>
```

## 8. Tag Cloud

```html
<div class="tag-cloud"><span class="tag tag-accent">charging speed</span> <span class="tag tag-accent">durability</span> <span class="tag tag-negative">overheating</span></div>
```

## 9. Insight List / Action Items

`.priority-high`（红）/ `.priority-medium`（黄）/ `.priority-low`（灰）。每条建议必须具体、可执行、有数据支撑。

```html
<ul class="insight-list">
  <li class="priority-high">紧急修复充电过热问题，影响 23% 差评</li>
  <li class="priority-medium">优化包装设计，减少运输损坏投诉</li>
  <li class="priority-low">增加 2m 长度选项</li>
</ul>
```

## 10. Comparison Grid

多品牌/多维度并列对比。容器加 `cols-2` / `cols-3`。与 SWOT 区别：Comparison 是任意数量卡片，SWOT 是固定四象限（带语义色）。

```html
<div class="comparison-grid cols-3">
  <div class="comparison-card">
    <div class="card-title">Product A</div>
    <p>评分: 4.5 · 评论数: 8,200 · 价格: $12.99</p>
  </div>
  <div class="comparison-card">
    <div class="card-title">Product B</div>
    <p>评分: 4.1 · 评论数: 5,600 · 价格: $9.99</p>
  </div>
</div>
```

## 11. Progress Bar

评分分布、占比、完成度。

```html
<div class="progress-bar-wrapper">
  <div class="progress-bar-label"><span>5 星</span><span>62%</span></div>
  <div class="progress-bar"><div class="fill" style="width:62%"></div></div>
</div>
```

## 12. Summary Box

Executive Summary / 章节 TL;DR。

```html
<div class="summary-box">
  <h4>核心发现</h4>
  <p>整体好评率 78%，痛点集中在耐久性（32% 差评提及）和充电速度（18%）。建议优先解决线材接口处断裂。</p>
</div>
```

## 13. SWOT Grid

固定 2×2 象限。四张卡片分别 `.strengths` / `.weaknesses` / `.opportunities` / `.threats`；标题固定 emoji：✅ 优势 / ⚠️ 劣势 / 🚀 机会 / 🔴 威胁。每象限 3-5 条。

```html
<div class="swot-grid">
  <div class="swot-card strengths">
    <div class="swot-title">✅ 优势</div>
    <ul><li>ABA 核心词双料第一</li><li>评分 4.6 星领先类目</li></ul>
  </div>
  <div class="swot-card weaknesses">
    <div class="swot-title">⚠️ 劣势</div>
    <ul><li>西语 ABA 词失去头部</li><li>变体数少于头部竞品</li></ul>
  </div>
  <div class="swot-card opportunities">
    <div class="swot-title">🚀 机会</div>
    <ul><li>$32-35 高价位段竞品稀缺</li><li>开发套装 SKU 提客单价</li></ul>
  </div>
  <div class="swot-card threats">
    <div class="swot-title">🔴 威胁</div>
    <ul><li>COZYEXPERT 降至 $19.99 打价格战</li><li>类目增速放缓</li></ul>
  </div>
</div>
```

## 14. Footer

```html
<div class="report-footer">报告由 LinkFox AI 生成 · 数据截止 2026-06-06</div>
```

## 15. Canvas Chart（自包含，无外部依赖）

模板内置 `drawBar` / `drawLine` / `drawDonut`。适合需离线/邮件转发的报告。id 全文档唯一，`width` 建议 1024、`height` 建议 340；数据字段 `data` 或 `values`、`label` 或 `name` 二选一。

```html
<div class="chart-container">
  <canvas id="chart_xxx" width="1024" height="340"></canvas>
</div>
```

调用代码放在 `<!-- CANVAS_SCRIPTS -->` 块中：

```javascript
// 柱状图（多系列自动分组）
drawBar("chart_xxx", ["Q1","Q2","Q3"], [
  {"label": "2025", "data": [100, 150, 120], "color": "#4f46e5"},
  {"label": "2026", "data": [130, 180, 160], "color": "#10b981"}
]);

// 折线图
drawLine("chart_trend", ["1月","2月","3月","4月"],
  [{"label": "销量", "data": [1200, 1500, 1800, 2100], "color": "#06b6d4"}]);

// 环形图
drawDonut("chart_pie", [
  {"label": "FBA", "value": 86.3, "color": "#4f46e5"},
  {"label": "FBM", "value": 13.7, "color": "#f59e0b"}
]);
```

**Canvas vs ECharts**：需交互（tooltip/缩放）或复杂图（雷达/桑基/地图）→ ECharts；数据点 ≤10 或需离线/邮件转发 → Canvas。

## 16. Data Source Citation

放在 `</section>` 之前作为该 section 最后一个元素。`.ds-tool` 填 skill 短名（不含 `linkfox-` 前缀），多个工具共同贡献时全部列出。

```html
<div class="data-source">
  <span class="ds-label">数据源：</span>
  <span class="ds-tool">amazon-us-reviews-list</span>
  <span class="ds-tool">keepa-product-request</span>
  <span class="ds-time">· 2026-06-12</span>
</div>
```

若该 section 含 Python 预计算的派生值，必须追加 `.ds-computed` 子块，列出指标名与计算公式：

```html
<div class="data-source">
  <span class="ds-label">数据源：</span>
  <span class="ds-tool">amazon-us-reviews-list</span>
  <span class="ds-tool">keepa-product-request</span>
  <span class="ds-time">· 2026-06-12</span>
  <div class="ds-computed">
    <span class="ds-label">计算指标：</span>
    好评率 78.2% = 好评数 ÷ 总评论数 · 增长率 12.3% = (本月 - 上月) ÷ 上月
  </div>
</div>
```

**约束**：
1. 每个含统计/度量数字的 section 末尾必须有 `data-source`，列出所有贡献数据的 skill 短名。
2. 若该 section 含 Python 预计算的派生值，必须有 `.ds-computed` 列出指标名、公式。
3. 纯定性分析/建议章节（无统计数字）可省略。

## 17. Evidence Image Grid

合规检测相似作品、专利/商标图片、商品主图对比。`<img>` 必须带 `alt` + `loading="lazy"`；图片 URL 必须来自 `data` 里的真实字段（如 `path` / `pathThumb`），禁止编造；优先用缩略图字段。

**网格布局**（每项相似度独立展示）：

```html
<div class="evidence-grid">
  <div class="evidence-item">
    <div class="evidence-img-wrap"><img src="https://example.com/work-1.jpg" alt="相似作品 1" loading="lazy" /></div>
    <div class="evidence-caption">
      <div class="evidence-title">版权作品 #VA0012345</div>
      <div class="evidence-meta">相似度: 92% · 权利人: John Doe</div>
    </div>
  </div>
</div>
```

**对比布局**（送检图 vs 命中图，推荐用于合规报告开头）：

```html
<div class="evidence-compare">
  <div class="evidence-compare-item">
    <div class="evidence-img-wrap"><img src="..." alt="送检图" loading="lazy" /></div>
    <div class="evidence-caption"><div class="evidence-title">送检图片</div></div>
  </div>
  <div class="evidence-compare-arrow">VS</div>
  <div class="evidence-compare-item">
    <div class="evidence-img-wrap"><img src="..." alt="命中图" loading="lazy" /></div>
    <div class="evidence-caption">
      <div class="evidence-title">最高相似命中</div>
      <div class="evidence-meta">相似度: 95%</div>
    </div>
  </div>
</div>
```

---

## 组件选择速查

| 数据特征 | 组件组合 |
|---|---|
| 核心指标 | KPI Cards |
| 分布/占比 | 饼图/环形图 + Progress Bar |
| 趋势变化 | 折线图 |
| 排名 / TOP N | Data Table |
| 多维度对比 | 雷达图 + Comparison Grid |
| 原始文本证据 | Quote Cards |
| 关键词/话题 | Tag Cloud + Data Table |
| 结论/建议 | Summary Box + Insight List |
| 四维度综合研判 | SWOT Grid |
| 图片视觉证据 | Evidence Image Grid + Evidence Compare |
