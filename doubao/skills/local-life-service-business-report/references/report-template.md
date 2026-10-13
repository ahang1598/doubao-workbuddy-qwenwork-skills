# 报告模板：数据平台风格

> 视觉规范统一遵循 [design-system.md](design-system.md)。本文件提供经营分析报告的完整结构、写作原则和可直接套用的 HTML 模板。

## 目录
- [写作原则](#写作原则)
- [两种模式](#两种模式)
- [完整 HTML 模板](#完整-html-模板)
- [模块说明](#模块说明)
- [注意事项](#注意事项)

---

## 写作原则
1. **面向店老板本人**：用"您""您的店"，禁止"本报记者""BD""案例提供人"等内部视角。
2. **先结论后证据**：开头 AI 解读区直接点出核心结论（亮点或问题）。
3. **数据说话**：每个判断有数据支撑，不写空话。
4. **行动可执行**：每条建议有具体动作、截止日期、基线→目标KPI；无数据支撑的目标标注"建议值，需商家确认"。
5. **不重复指标**：KPI 区和各模块卡片展示不同指标。
6. **图片必须真实且已授权**：只用该商家自有或已授权的真实门店图，搜不到就用数据可视化代替，禁止通用网图。

---

## 两种模式
### 案例模式（有亮点）
- 标签：绿色"✨ 经营亮点"
- 标题：正向肯定，绿色重点字
- AI 解读：突出成功经验和可复制打法
- 主色调：绿色 `#00B42A` 系
- 可含：亮点打法拆解、商品价格带、经验沉淀

### 诊断模式（有问题）
- 标签：橙色"🔍 经营体检"
- 标题：矛盾式，橙色标问题、绿色标好数据
- AI 解读：突出核心问题和改进方向
- 主色调：橙色 `#FF7D00` 系
- 可含：渠道分析、商品排行、门店健康度、问题诊断

---

## 完整 HTML 模板

> 字体说明：使用系统字体优先，不依赖外部CDN。font-family 为 `'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif`。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
<title>经营分析报告 · {商家名}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
    background: #F5F7FA;
    color: #1D2129;
    line-height: 1.7;
    -webkit-font-smoothing: antialiased;
  }
  .container { max-width: 960px; margin: 0 auto; padding: 20px; }

  /* ===== 卡片通用 ===== */
  .card {
    background: #FFFFFF;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    padding: 20px;
    margin-bottom: 16px;
  }

  /* ===== 页面头部 ===== */
  .header {
    background: #FFFFFF;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    padding: 24px 20px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
  }
  .header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 4px;
    background: linear-gradient(90deg, #165DFF, #722ED1, #0FC6C2);
  }
  .header-top { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
  .merchant-name { font-size: 22px; font-weight: 700; color: #1D2129; }
  .report-tag {
    display: inline-block;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 12px;
    margin-left: 10px;
    vertical-align: middle;
  }
  .report-tag.highlight { background: #E8FFEA; color: #00B42A; }
  .report-tag.diagnosis { background: #FFF7E8; color: #FF7D00; }
  .header-meta { font-size: 12px; color: #86909C; margin-top: 8px; }
  .header-meta span { margin-right: 16px; }
  .header-period {
    font-size: 13px;
    color: #4E5969;
    background: #F2F3F5;
    padding: 4px 12px;
    border-radius: 8px;
    white-space: nowrap;
  }

  /* ===== AI 解读区 ===== */
  .ai-section {
    background: linear-gradient(135deg, #E8F3FF 0%, #F0F7FF 50%, #EBF5FF 100%);
    border: 1px solid #BEDAFF;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 16px;
  }
  .ai-title {
    font-size: 15px;
    font-weight: 600;
    color: #165DFF;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .ai-note { font-size: 11px; color: #86909C; margin-bottom: 12px; }
  .ai-list { list-style: none; }
  .ai-list li {
    font-size: 14px;
    line-height: 1.8;
    color: #1D2129;
    padding-left: 18px;
    position: relative;
    margin-bottom: 6px;
  }
  .ai-list li::before {
    content: '•';
    position: absolute;
    left: 4px;
    color: #165DFF;
    font-weight: 700;
  }
  .ai-list li b { color: #165DFF; font-weight: 600; }
  .ai-list li .good { color: #00B42A; font-weight: 600; }
  .ai-list li .warn { color: #FF7D00; font-weight: 600; }

  /* ===== KPI 指标网格 ===== */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }
  .kpi-card {
    background: #FFFFFF;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    padding: 16px;
    text-align: center;
  }
  .kpi-label { font-size: 12px; color: #86909C; margin-bottom: 6px; }
  .kpi-num { font-size: 26px; font-weight: 700; color: #1D2129; line-height: 1.2; }
  .kpi-num .unit { font-size: 13px; font-weight: 500; color: #86909C; }
  .kpi-change { font-size: 12px; margin-top: 4px; }
  .kpi-change.up { color: #00B42A; }
  .kpi-change.down { color: #F53F3F; }
  .kpi-card.accent-blue { border-top: 3px solid #165DFF; }
  .kpi-card.accent-purple { border-top: 3px solid #722ED1; }
  .kpi-card.accent-cyan { border-top: 3px solid #0FC6C2; }
  .kpi-card.accent-orange { border-top: 3px solid #FF7D00; }

  /* ===== 模块标题 ===== */
  .section-title {
    font-size: 18px;
    font-weight: 600;
    color: #1D2129;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .section-title .dot {
    width: 4px;
    height: 18px;
    border-radius: 2px;
    display: inline-block;
  }
  .dot-blue { background: #165DFF; }
  .dot-purple { background: #722ED1; }
  .dot-cyan { background: #0FC6C2; }
  .dot-orange { background: #FF7D00; }
  .dot-green { background: #00B42A; }
  .dot-red { background: #F53F3F; }

  /* ===== 数据表格 ===== */
  .table-wrap { overflow-x: auto; }
  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  .data-table th {
    background: #F7F8FA;
    color: #4E5969;
    font-size: 12px;
    font-weight: 600;
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid #E5E6EB;
    white-space: nowrap;
  }
  .data-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #F2F3F5;
    color: #1D2129;
  }
  .data-table tr:last-child td { border-bottom: none; }
  .data-table tr:hover td { background: #F7F8FA; }
  .data-table .num-col { text-align: right; font-weight: 600; }
  .rank-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 700;
    color: #fff;
  }
  .rank-1 { background: linear-gradient(135deg, #FFD700, #FFA500); }
  .rank-2 { background: linear-gradient(135deg, #C0C0C0, #A8A8A8); }
  .rank-3 { background: linear-gradient(135deg, #CD7F32, #B87333); }
  .rank-other { background: #F2F3F5; color: #86909C; }
  .tag-pill {
    display: inline-block;
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 10px;
  }
  .tag-win { background: #E8FFEA; color: #00B42A; }
  .tag-lose { background: #FFF1F0; color: #F53F3F; }
  .tag-draw { background: #F2F3F5; color: #86909C; }
  .hot-pill {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    background: #FFF1F0;
    color: #F53F3F;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 12px;
  }

  /* ===== 横向条形图 ===== */
  .bar-row {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    font-size: 13px;
  }
  .bar-row:last-child { margin-bottom: 0; }
  .bar-label { width: 80px; flex-shrink: 0; color: #4E5969; font-weight: 500; }
  .bar-track { flex: 1; height: 18px; background: #F2F3F5; border-radius: 4px; overflow: hidden; }
  .bar-fill {
    height: 100%;
    border-radius: 4px;
    display: flex;
    align-items: center;
    padding-left: 8px;
    color: #fff;
    font-size: 11px;
    font-weight: 600;
    min-width: 30px;
  }
  .bar-fill.c-blue { background: #165DFF; }
  .bar-fill.c-purple { background: #722ED1; }
  .bar-fill.c-cyan { background: #0FC6C2; }
  .bar-fill.c-orange { background: #FF7D00; }
  .bar-val { width: 60px; flex-shrink: 0; text-align: right; font-weight: 600; padding-left: 8px; }

  /* ===== 进度条（门店健康度） ===== */
  .progress-item { margin-bottom: 10px; }
  .progress-item:last-child { margin-bottom: 0; }
  .progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #4E5969;
    margin-bottom: 4px;
  }
  .progress-label b { color: #1D2129; }
  .progress-track { height: 6px; background: #F2F3F5; border-radius: 3px; overflow: hidden; }
  .progress-fill { height: 100%; border-radius: 3px; }

  /* ===== 亮点/问题卡片 ===== */
  .insight-card {
    background: #F7F8FA;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 10px;
    border-left: 3px solid #165DFF;
  }
  .insight-card:last-child { margin-bottom: 0; }
  .insight-card.good { border-left-color: #00B42A; background: #F6FFED; }
  .insight-card.warn { border-left-color: #FF7D00; background: #FFFBE6; }
  .insight-card.danger { border-left-color: #F53F3F; background: #FFF1F0; }
  .insight-title { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
  .insight-card.good .insight-title { color: #00B42A; }
  .insight-card.warn .insight-title { color: #FF7D00; }
  .insight-card.danger .insight-title { color: #F53F3F; }
  .insight-body { font-size: 13px; color: #4E5969; line-height: 1.7; }
  .insight-body b { color: #1D2129; }

  /* ===== 行动建议 ===== */
  .action-card {
    background: #FFFFFF;
    border: 1px solid #E5E6EB;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
  }
  .action-card:last-child { margin-bottom: 0; }
  .action-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .priority-tag {
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 8px;
    color: #fff;
  }
  .priority-p0 { background: #F53F3F; }
  .priority-p1 { background: #FF7D00; }
  .priority-p2 { background: #165DFF; }
  .action-title { font-size: 15px; font-weight: 600; color: #1D2129; }
  .action-body { font-size: 13px; color: #4E5969; line-height: 1.7; margin-bottom: 8px; }
  .action-kpi {
    font-size: 12px;
    color: #86909C;
    background: #F7F8FA;
    padding: 8px 12px;
    border-radius: 8px;
  }
  .action-kpi b { color: #00B42A; }

  /* ===== 双列布局 ===== */
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

  /* ===== 页脚 ===== */
  .footer {
    text-align: center;
    font-size: 11px;
    color: #86909C;
    padding: 16px 0 8px;
    line-height: 1.8;
  }
  .footer-divider { height: 1px; background: #E5E6EB; margin-bottom: 16px; }

  /* ===== 响应式 ===== */
  @media (max-width: 767px) {
    .container { padding: 12px; }
    .card { padding: 16px; border-radius: 10px; }
    .header { padding: 18px 16px; }
    .merchant-name { font-size: 19px; }
    .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .kpi-card { padding: 14px 10px; }
    .kpi-num { font-size: 22px; }
    .section-title { font-size: 16px; }
    .two-col { grid-template-columns: 1fr; gap: 12px; }
    .table-wrap { overflow-x: auto; }
    .data-table { min-width: 480px; }
    .bar-label { width: 64px; font-size: 12px; }
    .ai-section { padding: 14px 16px; }
    .action-card { padding: 14px; }
  }
  @media (max-width: 380px) {
    .kpi-num { font-size: 20px; }
    .merchant-name { font-size: 17px; }
  }
  @media print {
    body { background: #fff; }
    .card, .header, .kpi-card { box-shadow: none; border: 1px solid #E5E6EB; }
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
</style>
</head>
<body>
<div class="container">

  <!-- ===== 页面头部 ===== -->
  <div class="header">
    <div class="header-top">
      <div>
        <span class="merchant-name">{商家全称}</span>
        <span class="report-tag {highlight/diagnosis}">{✨ 经营亮点 / 🔍 经营体检}</span>
        <div class="header-meta">
          <span>📍 {城市}</span>
          <span>🏪 {门店数}家门店</span>
          <span>📂 {品类}</span>
        </div>
      </div>
      <div class="header-period">{分析周期}</div>
    </div>
  </div>

  <!-- ===== AI 解读区 ===== -->
  <div class="ai-section">
    <div class="ai-title">AI ✨ 解读</div>
    <div class="ai-note">注：基于算法&大模型得出，仅供参考 &nbsp;|&nbsp; 数据周期：{周期}</div>
    <ul class="ai-list">
      <li>核心结论1，用<b>蓝色</b>标重点数据，<span class="good">绿色</span>标亮点，<span class="warn">橙色</span>标问题。</li>
      <li>核心结论2，每个判断都有数据支撑。</li>
      <li>核心结论3，不超过3条，聚焦最关键发现。</li>
    </ul>
  </div>

  <!-- ===== KPI 核心指标 ===== -->
  <div class="kpi-grid">
    <div class="kpi-card accent-blue">
      <div class="kpi-label">{指标1名}</div>
      <div class="kpi-num">{数值}<span class="unit">{单位}</span></div>
      <div class="kpi-change {up/down}">{↑/↓} {环比}</div>
    </div>
    <div class="kpi-card accent-purple">
      <div class="kpi-label">{指标2名}</div>
      <div class="kpi-num">{数值}<span class="unit">{单位}</span></div>
      <div class="kpi-change {up/down}">{↑/↓} {环比}</div>
    </div>
    <div class="kpi-card accent-cyan">
      <div class="kpi-label">{指标3名}</div>
      <div class="kpi-num">{数值}<span class="unit">{单位}</span></div>
      <div class="kpi-change {up/down}">{↑/↓} {环比}</div>
    </div>
    <div class="kpi-card accent-orange">
      <div class="kpi-label">{指标4名}</div>
      <div class="kpi-num">{数值}<span class="unit">{单位}</span></div>
      <div class="kpi-change {up/down}">{↑/↓} {环比}</div>
    </div>
  </div>

  <!-- ===== 模块1：经营概览 ===== -->
  <div class="card">
    <div class="section-title"><span class="dot dot-blue"></span>经营概览</div>
    <!-- 亮点/问题卡片 -->
    <div class="insight-card {good/warn/danger}">
      <div class="insight-title">{标题，如：成交环比增长20%}</div>
      <div class="insight-body">{描述，<b>关键数据</b>加粗，说明原因和影响。}</div>
    </div>
    <div class="insight-card {good/warn/danger}">
      <div class="insight-title">{标题}</div>
      <div class="insight-body">{描述}</div>
    </div>
  </div>

  <!-- ===== 模块2：流量分析（双列） ===== -->
  <div class="two-col">
    <div class="card">
      <div class="section-title"><span class="dot dot-purple"></span>流量来源</div>
      <div class="bar-row">
        <div class="bar-label">{渠道1}</div>
        <div class="bar-track"><div class="bar-fill c-blue" style="width:{百分比}%">{百分比}%</div></div>
        <div class="bar-val">{金额}</div>
      </div>
      <div class="bar-row">
        <div class="bar-label">{渠道2}</div>
        <div class="bar-track"><div class="bar-fill c-purple" style="width:{百分比}%">{百分比}%</div></div>
        <div class="bar-val">{金额}</div>
      </div>
      <!-- 更多渠道 -->
    </div>
    <div class="card">
      <div class="section-title"><span class="dot dot-purple"></span>流量体裁</div>
      <div class="bar-row">
        <div class="bar-label">{体裁1}</div>
        <div class="bar-track"><div class="bar-fill c-cyan" style="width:{百分比}%">{百分比}%</div></div>
        <div class="bar-val">{金额}</div>
      </div>
      <!-- 更多体裁 -->
    </div>
  </div>

  <!-- ===== 模块3：商品分析 ===== -->
  <div class="card">
    <div class="section-title"><span class="dot dot-cyan"></span>商品榜单 Top5</div>
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th style="width:50px">排名</th>
            <th>商品名称</th>
            <th class="num-col">成交金额</th>
            <th class="num-col">销量</th>
            <th style="width:60px">状态</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><span class="rank-badge rank-1">1</span></td>
            <td>{商品名}</td>
            <td class="num-col">¥{金额}</td>
            <td class="num-col">{销量}</td>
            <td><span class="tag-pill tag-win">热销</span></td>
          </tr>
          <tr>
            <td><span class="rank-badge rank-2">2</span></td>
            <td>{商品名}</td>
            <td class="num-col">¥{金额}</td>
            <td class="num-col">{销量}</td>
            <td><span class="tag-pill tag-draw">正常</span></td>
          </tr>
          <!-- 更多行 -->
        </tbody>
      </table>
    </div>
  </div>

  <!-- ===== 模块4：门店健康度（诊断模式用） ===== -->
  <!--
  <div class="card">
    <div class="section-title"><span class="dot dot-orange"></span>门店健康度</div>
    <div class="progress-item">
      <div class="progress-label"><span>{门店1}</span><b>{动销率}%</b></div>
      <div class="progress-track"><div class="progress-fill" style="width:{百分比}%;background:#00B42A;"></div></div>
    </div>
    <div class="progress-item">
      <div class="progress-label"><span>{门店2}</span><b>{动销率}%</b></div>
      <div class="progress-track"><div class="progress-fill" style="width:{百分比}%;background:#FF7D00;"></div></div>
    </div>
  </div>
  -->

  <!-- ===== 模块5：行动建议 ===== -->
  <div class="card">
    <div class="section-title"><span class="dot dot-green"></span>行动计划</div>
    <div class="action-card">
      <div class="action-header">
        <span class="priority-tag priority-p0">P0</span>
        <span class="action-title">{行动标题}</span>
      </div>
      <div class="action-body">{具体动作描述，要可执行、可验证，不写空话。}</div>
      <div class="action-kpi">验收指标：{指标名} <b>{基线}→{目标}</b>，建议周期：{时长}</div>
    </div>
    <div class="action-card">
      <div class="action-header">
        <span class="priority-tag priority-p1">P1</span>
        <span class="action-title">{行动标题}</span>
      </div>
      <div class="action-body">{具体动作描述}</div>
      <div class="action-kpi">验收指标：{指标名} <b>{基线}→{目标}</b>，建议周期：{时长}</div>
    </div>
    <div class="action-card">
      <div class="action-header">
        <span class="priority-tag priority-p2">P2</span>
        <span class="action-title">{行动标题}</span>
      </div>
      <div class="action-body">{具体动作描述}</div>
      <div class="action-kpi">验收指标：{指标名} <b>{基线}→{目标}</b>，建议周期：{时长}</div>
    </div>
  </div>

  <!-- ===== 页脚 ===== -->
  <div class="footer-divider"></div>
  <div class="footer">
    数据来源：抖音生活服务经营数据 &nbsp;|&nbsp; 生成时间：{YYYY-MM-DD HH:MM}<br>
    本报告仅供经营参考，具体决策请结合商家实际情况。行动建议中的目标值为建议值，需商家确认。
  </div>

</div>
</body>
</html>
```

---

## 模块说明

| 模块 | 必选/可选 | 说明 |
|------|-----------|------|
| 页面头部 | 必选 | 商家名、报告类型标签、周期、基本信息 |
| AI 解读 | 必选 | 3条以内核心结论，浅蓝渐变背景 |
| KPI 指标 | 必选 | 4个核心指标，不同主题色顶边 |
| 经营概览 | 必选 | 亮点/问题 insight 卡片 |
| 流量分析 | 可选 | 关注重点包含流量时展示，双列条形图 |
| 商品分析 | 可选 | 关注重点包含商品时展示，榜单表格 |
| 门店健康度 | 可选 | 诊断模式、多门店时展示，进度条 |
| 行动计划 | 必选 | P0/P1/P2 行动卡片，含验收KPI |
| 页脚 | 必选 | 数据来源、生成时间、免责声明 |

---

## 注意事项
1. 视觉规范统一遵循 [design-system.md](design-system.md)，颜色/字体/间距/组件不得擅自偏离。
2. 两种模式通过 `report-tag` 类和主色调区分：案例模式用绿色系，诊断模式用橙色系。
3. KPI 卡片的 4 个指标与下方各模块不重复。
4. 所有金额单位为元，百分比保留一位小数；环比用 ↑↓ 和绿涨红跌标注。
5. 行动项必须有截止日期和 KPI；无数据支撑的目标标注"建议值，需商家确认"。
6. 测试商品/测试数据需明确标注（灰色"测试"标签）。
7. 图片：只用商家自有或已授权的真实门店图，搜不到就不放，用数据可视化代替。
8. 保存文件名：`{商家名}-经营分析报告.html`。
9. 交付前必须完成渲染验证：DOM结构完整、资源加载成功、首屏/中段/结尾正常、移动端布局可读、控制台无阻塞错误。
10. 单文件自包含，可直接转发他人在浏览器中打开。
