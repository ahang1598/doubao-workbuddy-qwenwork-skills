# HTML 报告规范

## 目录
- [页面结构](#页面结构)
- [视觉要求](#视觉要求)
- [文案要求](#文案要求)
- [完整 HTML 模板](#完整-html-模板)
- [交付检查](#交付检查)

生成单文件 HTML，面向商家老板或运营人员，打开后马上知道做什么。使用 `CanvasCreateFile` 创建并上屏，交付前完成渲染验证。

## 页面结构
1. 首屏结论：
   - 商家名、城市、品类、获取时间。
   - 3 条以内核心判断。
   - TOP 3 热点机会，标注优先级和理由。
   - **时效性声明**：在首屏显著位置标注"本报告热点基于当前日期筛选，已过期节日/活动已自动过滤"。
2. 今日行动：
   - 今天拍什么、发什么标题、挂哪个商品、预期目标。
   - 每条建议控制在可执行动作，不写空泛方法论。
3. 热点机会卡片：
   - 热点名称、热度/增速/排名等证据。
   - 适配原因：品类、城市、人群、商品承接。
   - 推荐内容角度：标题、封面、开头 3 秒、图文结构或短视频镜头。
   - 可挂商品/套餐。
   - 风险和不建议做法。
   - **有效期标签**：每个节日/活动类热点卡片标注"有效期至 X月X日"，过期热点不得出现。
4. 图文/内容样例学习：
   - 对页面可点击的热点推荐、抖音图文或视频样例，展示标题、作者/账号、可见指标、链接、可借鉴点。
   - 页面若只提供标题、话题词或"复制热点去发布"而没有直达 URL，则生成可点击的抖音搜索跳转链接，链接文案写"去抖音看视频"或"抖音搜索打开"。
   - 只有在既拿不到直达 URL，也无法合理生成抖音搜索链接时，才写"页面未提供可复制链接"，不要伪造。
5. 下季度热点前瞻：
   - 以时间轴或卡片网格展示下一季度（未来3个月）的重要节点和趋势预测。
   - 每个节点包含：日期/时段、热点名称、适配品类、建议内容方向、可挂商品类型、提前布局建议。
   - 固定节日/大促标注置信度"高"；趋势性预测标注"中/低"并注明"预测参考"。
   - 模块底部标注："以上预测基于公开日历、历史大促规律和当前热点趋势外推，仅供提前布局参考。"
6. 覆盖检查：
   - 用紧凑表格列出品类、城市、时间、热点、内容、商品、账号/达人、用户需求、竞争维度的获取情况。
   - 未覆盖的维度列入待补获取，不影响已验证结论。

## 视觉要求
- 统一数据平台风格：浅灰背景（`#F5F7FA`）+ 白色圆角卡片（`border-radius: 12px`，轻阴影）+ 蓝色主色调（`#165DFF`）。
- 各模块用不同主题色区分：热点推荐用红色系（`#F53F3F`）、内容样例用紫色系（`#722ED1`）、下季度预测用青色系（`#0FC6C2`）、行动建议用绿色系（`#00B42A`）。
- 首屏要有清晰的视觉层次：商家信息头部卡片 + AI解读区（浅蓝渐变）+ TOP热点卡片。
- 热点卡片使用热度 pill（`🔥 热度值`，浅红底红字）、排名徽章（TOP1-3渐变）、有效期标签。
- 不做营销落地页，不写大段产品介绍。
- 不使用复杂筛选器；允许锚点、折叠详情（`<details>`）、标签和表格。
- 移动端可读：KPI/热点卡片保持2列，表格外层 `overflow-x: auto` 横向滚动，卡片不嵌套卡片，按钮或链接文字不溢出。
- 所有 CSS 内联在同一个 HTML 文件中，不依赖外部构建。
- 字体使用系统字体优先（`'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif`），不依赖外部CDN。
- 详细视觉规范、组件样式和响应式断点见 [design-system.md](design-system.md)。
- 单文件自包含，可直接转发他人在浏览器中打开。

## 文案要求
- 用中文，直接面向商家说结论。
- 避免"可能可以考虑"等弱表达；数据不足时明确写"缺少 X，暂不下结论"。
- 不使用广告法高风险极限词。
- 不承诺平台流量或成交结果。
- 引用页面数据时写清来源和获取时间。

---

## 完整 HTML 模板

> 字体说明：使用系统字体优先，不依赖外部CDN。font-family 为 `'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif`。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
<title>热点查找 · {商家名}</title>
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
    background: linear-gradient(90deg, #F53F3F, #FF7D00, #165DFF);
  }
  .header-top { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }
  .merchant-name { font-size: 22px; font-weight: 700; color: #1D2129; }
  .header-meta { font-size: 12px; color: #86909C; margin-top: 8px; }
  .header-meta span { margin-right: 16px; }
  .header-time {
    font-size: 13px;
    color: #4E5969;
    background: #F2F3F5;
    padding: 4px 12px;
    border-radius: 8px;
    white-space: nowrap;
  }
  .timeliness-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #E8FFEA;
    color: #00B42A;
    font-size: 12px;
    font-weight: 500;
    padding: 4px 12px;
    border-radius: 12px;
    margin-top: 12px;
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
  .dot-red { background: #F53F3F; }
  .dot-green { background: #00B42A; }
  .dot-purple { background: #722ED1; }
  .dot-cyan { background: #0FC6C2; }
  .dot-blue { background: #165DFF; }

  /* ===== TOP 热点卡片网格 ===== */
  .hot-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  .hot-card {
    background: #FFFFFF;
    border: 1px solid #F2F3F5;
    border-radius: 10px;
    padding: 16px;
    position: relative;
    transition: box-shadow 0.2s;
  }
  .hot-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
  .hot-card.top1 { border-top: 3px solid #FFD700; }
  .hot-card.top2 { border-top: 3px solid #C0C0C0; }
  .hot-card.top3 { border-top: 3px solid #CD7F32; }
  .hot-rank {
    position: absolute;
    top: 12px;
    right: 12px;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    color: #fff;
  }
  .hot-rank.r1 { background: linear-gradient(135deg, #FFD700, #FFA500); }
  .hot-rank.r2 { background: linear-gradient(135deg, #C0C0C0, #A8A8A8); }
  .hot-rank.r3 { background: linear-gradient(135deg, #CD7F32, #B87333); }
  .hot-name {
    font-size: 15px;
    font-weight: 600;
    color: #1D2129;
    margin-bottom: 8px;
    padding-right: 36px;
  }
  .hot-heat {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    background: #FFF1F0;
    color: #F53F3F;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 12px;
    margin-bottom: 8px;
  }
  .hot-reason {
    font-size: 13px;
    color: #4E5969;
    line-height: 1.6;
    margin-bottom: 8px;
  }
  .hot-expire {
    font-size: 11px;
    color: #86909C;
    background: #F7F8FA;
    padding: 2px 8px;
    border-radius: 6px;
    display: inline-block;
  }

  /* ===== 今日行动 ===== */
  .action-item {
    display: flex;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid #F2F3F5;
  }
  .action-item:last-child { border-bottom: none; }
  .action-num {
    width: 24px;
    height: 24px;
    background: #00B42A;
    color: #fff;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    flex-shrink: 0;
  }
  .action-content { flex: 1; }
  .action-title { font-size: 14px; font-weight: 600; color: #1D2129; margin-bottom: 4px; }
  .action-detail { font-size: 13px; color: #4E5969; line-height: 1.6; }
  .action-detail b { color: #00B42A; }
  .action-goal {
    font-size: 12px;
    color: #86909C;
    background: #F7F8FA;
    padding: 4px 10px;
    border-radius: 6px;
    margin-top: 6px;
    display: inline-block;
  }

  /* ===== 热点详情（可折叠） ===== */
  .hot-detail {
    border: 1px solid #F2F3F5;
    border-radius: 10px;
    margin-bottom: 10px;
    overflow: hidden;
  }
  .hot-detail:last-child { margin-bottom: 0; }
  .hot-detail summary {
    padding: 14px 16px;
    font-size: 14px;
    font-weight: 600;
    color: #1D2129;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    list-style: none;
  }
  .hot-detail summary::-webkit-details-marker { display: none; }
  .hot-detail summary::after {
    content: '▸';
    margin-left: auto;
    color: #86909C;
    transition: transform 0.2s;
  }
  .hot-detail[open] summary::after { transform: rotate(90deg); }
  .hot-detail-body {
    padding: 0 16px 16px;
    font-size: 13px;
    color: #4E5969;
    line-height: 1.7;
  }
  .hot-detail-body .row { margin-bottom: 8px; }
  .hot-detail-body .row-label {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    color: #86909C;
    background: #F2F3F5;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 8px;
    vertical-align: top;
  }
  .hot-detail-body .tag {
    display: inline-block;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    margin-right: 4px;
  }
  .tag-product { background: #E8FFFB; color: #0FC6C2; }
  .tag-risk { background: #FFF1F0; color: #F53F3F; }

  /* ===== 内容样例 ===== */
  .sample-item {
    display: flex;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid #F2F3F5;
  }
  .sample-item:last-child { border-bottom: none; }
  .sample-thumb {
    width: 56px;
    height: 56px;
    border-radius: 8px;
    background: linear-gradient(135deg, #722ED1, #9254DE);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 20px;
  }
  .sample-info { flex: 1; min-width: 0; }
  .sample-title {
    font-size: 13px;
    font-weight: 600;
    color: #1D2129;
    margin-bottom: 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .sample-meta { font-size: 12px; color: #86909C; margin-bottom: 4px; }
  .sample-meta span { margin-right: 12px; }
  .sample-link {
    font-size: 12px;
    color: #165DFF;
    text-decoration: none;
  }
  .sample-link:hover { text-decoration: underline; }
  .sample-learn {
    font-size: 12px;
    color: #4E5969;
    background: #F9F0FF;
    padding: 6px 10px;
    border-radius: 6px;
    margin-top: 6px;
  }

  /* ===== 时间轴（下季度前瞻） ===== */
  .timeline { position: relative; padding-left: 28px; }
  .timeline::before {
    content: '';
    position: absolute;
    left: 9px;
    top: 6px;
    bottom: 6px;
    width: 2px;
    background: #E5E6EB;
  }
  .timeline-item {
    position: relative;
    margin-bottom: 16px;
  }
  .timeline-item:last-child { margin-bottom: 0; }
  .timeline-dot {
    position: absolute;
    left: -28px;
    top: 4px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #0FC6C2;
    border: 3px solid #fff;
    box-shadow: 0 0 0 2px #0FC6C2;
  }
  .timeline-date {
    font-size: 12px;
    font-weight: 600;
    color: #0FC6C2;
    margin-bottom: 4px;
  }
  .timeline-card {
    background: #F7FFFE;
    border: 1px solid #B5F5EC;
    border-radius: 8px;
    padding: 12px 14px;
  }
  .timeline-title { font-size: 14px; font-weight: 600; color: #1D2129; margin-bottom: 6px; }
  .timeline-desc { font-size: 12px; color: #4E5969; line-height: 1.6; margin-bottom: 6px; }
  .timeline-tags { display: flex; flex-wrap: wrap; gap: 6px; }
  .confidence-tag {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 8px;
  }
  .conf-high { background: #E8FFEA; color: #00B42A; }
  .conf-mid { background: #FFF7E8; color: #FF7D00; }
  .conf-low { background: #F2F3F5; color: #86909C; }

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
  .status-ok { color: #00B42A; font-weight: 600; }
  .status-miss { color: #FF7D00; font-weight: 600; }

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
    .hot-grid { grid-template-columns: 1fr; }
    .section-title { font-size: 16px; }
    .table-wrap { overflow-x: auto; }
    .data-table { min-width: 480px; }
    .ai-section { padding: 14px 16px; }
    .sample-item { flex-direction: column; }
    .sample-thumb { width: 100%; height: 120px; }
  }
  @media (max-width: 380px) {
    .merchant-name { font-size: 17px; }
  }
  @media print {
    body { background: #fff; }
    .card, .header, .hot-card, .timeline-card { box-shadow: none; border: 1px solid #E5E6EB; }
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
        <div class="merchant-name">{商家全称}</div>
        <div class="header-meta">
          <span>📍 {城市}</span>
          <span>📂 {品类}</span>
          <span>🏪 {门店数}家门店</span>
        </div>
      </div>
      <div class="header-time">获取时间：{YYYY-MM-DD HH:MM}</div>
    </div>
    <div class="timeliness-badge">✅ 热点已按当前日期时效性筛选，过期节日/活动已过滤</div>
  </div>

  <!-- ===== AI 解读区 ===== -->
  <div class="ai-section">
    <div class="ai-title">AI ✨ 解读</div>
    <div class="ai-note">注：基于算法&大模型得出，仅供参考 &nbsp;|&nbsp; 数据周期：{周期}</div>
    <ul class="ai-list">
      <li>核心判断1，用<b>蓝色</b>标重点，直接告诉商家该追什么。</li>
      <li>核心判断2，每个判断有数据支撑。</li>
      <li>核心判断3，不超过3条，聚焦最关键机会。</li>
    </ul>
  </div>

  <!-- ===== TOP 3 热点 ===== -->
  <div class="card">
    <div class="section-title"><span class="dot dot-red"></span>TOP 热点机会</div>
    <div class="hot-grid">
      <div class="hot-card top1">
        <div class="hot-rank r1">1</div>
        <div class="hot-name">{热点名称1}</div>
        <div class="hot-heat">🔥 {热度值}</div>
        <div class="hot-reason">{推荐理由，为什么适合这个商家}</div>
        <span class="hot-expire">有效期至 {X月X日}</span>
      </div>
      <div class="hot-card top2">
        <div class="hot-rank r2">2</div>
        <div class="hot-name">{热点名称2}</div>
        <div class="hot-heat">🔥 {热度值}</div>
        <div class="hot-reason">{推荐理由}</div>
        <span class="hot-expire">有效期至 {X月X日}</span>
      </div>
      <div class="hot-card top3">
        <div class="hot-rank r3">3</div>
        <div class="hot-name">{热点名称3}</div>
        <div class="hot-heat">🔥 {热度值}</div>
        <div class="hot-reason">{推荐理由}</div>
        <span class="hot-expire">有效期至 {X月X日}</span>
      </div>
    </div>
  </div>

  <!-- ===== 今日行动 ===== -->
  <div class="card">
    <div class="section-title"><span class="dot dot-green"></span>今日行动</div>
    <div class="action-item">
      <div class="action-num">1</div>
      <div class="action-content">
        <div class="action-title">{今天拍什么/发什么}</div>
        <div class="action-detail">标题建议：<b>{标题}</b>｜挂商品：{商品名}</div>
        <div class="action-goal">预期目标：{曝光/互动/转化目标}</div>
      </div>
    </div>
    <div class="action-item">
      <div class="action-num">2</div>
      <div class="action-content">
        <div class="action-title">{第二条行动}</div>
        <div class="action-detail">{具体动作描述}</div>
        <div class="action-goal">预期目标：{目标}</div>
      </div>
    </div>
  </div>

  <!-- ===== 热点机会详情（可折叠） ===== -->
  <div class="card">
    <div class="section-title"><span class="dot dot-red"></span>热点机会详情</div>

    <details class="hot-detail" open>
      <summary>🔥 {热点名称} · 热度 {值}</summary>
      <div class="hot-detail-body">
        <div class="row"><span class="row-label">适配原因</span>{品类匹配、城市匹配、人群匹配、商品承接}</div>
        <div class="row"><span class="row-label">内容角度</span>标题建议、封面建议、开头3秒钩子、图文结构/短视频镜头</div>
        <div class="row"><span class="row-label">可挂商品</span><span class="tag tag-product">{商品1}</span><span class="tag tag-product">{商品2}</span></div>
        <div class="row"><span class="row-label">风险提示</span><span class="tag tag-risk">{不建议的做法}</span></div>
      </div>
    </details>

    <details class="hot-detail">
      <summary>🔥 {热点名称} · 热度 {值}</summary>
      <div class="hot-detail-body">
        <div class="row"><span class="row-label">适配原因</span>{...}</div>
        <div class="row"><span class="row-label">内容角度</span>{...}</div>
        <div class="row"><span class="row-label">可挂商品</span><span class="tag tag-product">{...}</span></div>
      </div>
    </details>
  </div>

  <!-- ===== 图文/内容样例学习 ===== -->
  <div class="card">
    <div class="section-title"><span class="dot dot-purple"></span>内容样例学习</div>
    <div class="sample-item">
      <div class="sample-thumb">🎬</div>
      <div class="sample-info">
        <div class="sample-title">{视频/图文标题}</div>
        <div class="sample-meta"><span>@{作者账号}</span><span>❤️ {点赞数}</span><span>💬 {评论数}</span></div>
        <a href="{抖音链接}" class="sample-link" target="_blank">去抖音看视频 →</a>
        <div class="sample-learn">💡 可借鉴：{开头钩子/画面风格/转化设计中最突出的1点}</div>
      </div>
    </div>
    <div class="sample-item">
      <div class="sample-thumb">🎬</div>
      <div class="sample-info">
        <div class="sample-title">{视频/图文标题}</div>
        <div class="sample-meta"><span>@{作者账号}</span><span>❤️ {点赞数}</span></div>
        <a href="{抖音搜索链接}" class="sample-link" target="_blank">抖音搜索打开 →</a>
        <div class="sample-learn">💡 可借鉴：{...}</div>
      </div>
    </div>
  </div>

  <!-- ===== 下季度热点前瞻 ===== -->
  <div class="card">
    <div class="section-title"><span class="dot dot-cyan"></span>下季度热点前瞻</div>
    <div class="timeline">
      <div class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-date">{X月X日} · {节日/活动名}</div>
        <div class="timeline-card">
          <div class="timeline-title">{热点名称}</div>
          <div class="timeline-desc">{适配品类、建议内容方向、可挂商品类型、提前多久开始准备}</div>
          <div class="timeline-tags">
            <span class="confidence-tag conf-high">置信度：高（固定节日）</span>
          </div>
        </div>
      </div>
      <div class="timeline-item">
        <div class="timeline-dot"></div>
        <div class="timeline-date">{X月} · {趋势性热点}</div>
        <div class="timeline-card">
          <div class="timeline-title">{热点名称}</div>
          <div class="timeline-desc">{描述和建议}</div>
          <div class="timeline-tags">
            <span class="confidence-tag conf-mid">置信度：中（趋势预测）</span>
          </div>
        </div>
      </div>
    </div>
    <div style="font-size:11px;color:#86909C;margin-top:12px;text-align:center;">以上预测基于公开日历、历史大促规律和当前热点趋势外推，仅供提前布局参考。</div>
  </div>

  <!-- ===== 覆盖检查 ===== -->
  <div class="card">
    <div class="section-title"><span class="dot dot-blue"></span>覆盖检查</div>
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr><th>维度</th><th>获取状态</th><th>说明</th></tr>
        </thead>
        <tbody>
          <tr><td>品类</td><td class="status-ok">✓ 已覆盖</td><td>{具体品类}</td></tr>
          <tr><td>城市</td><td class="status-ok">✓ 已覆盖</td><td>{城市}</td></tr>
          <tr><td>热点榜单</td><td class="status-ok">✓ 已覆盖</td><td>{来源}</td></tr>
          <tr><td>内容样例</td><td class="status-ok">✓ 已覆盖</td><td>{数量}条</td></tr>
          <tr><td>商品挂载</td><td class="status-miss">⚠ 待补获取</td><td>{缺失原因}</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- ===== 页脚 ===== -->
  <div class="footer-divider"></div>
  <div class="footer">
    数据来源：抖音生活服务热点数据 &nbsp;|&nbsp; 生成时间：{YYYY-MM-DD HH:MM}<br>
    本报告热点基于当前日期时效性筛选，仅供内容创作参考，不构成平台流量或成交承诺。
  </div>

</div>
</body>
</html>
```

---

## 交付检查
交付前检查：
- HTML 文件通过 `CanvasCreateFile` 创建并能正常上屏。
- 首屏有明确推荐，不需要先操作筛选器。
- 推荐热点与商家品类、城市、商品强相关。
- **时效性校验**：所有推荐热点均在有效期内，已过期节日/活动已剔除；每个节日类热点标注有效期。
- **下季度前瞻模块**已包含，预测节点标注置信度和"预测参考"声明。
- 覆盖检查表没有遗漏已能获取的页面维度。
- 图文/视频样例只来自本次实际打开或页面可见信息。
- DOM结构完整、外部资源加载成功、移动端布局正常、控制台无阻塞错误。
- 单文件自包含，可直接转发他人打开。
