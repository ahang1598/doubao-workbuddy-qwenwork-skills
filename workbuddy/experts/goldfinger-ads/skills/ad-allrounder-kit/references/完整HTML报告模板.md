# 完整 HTML 复盘 / 诊断报告模板（金手指统一 UI · 含折线图可视化）

> 用途：当用户在大白话总结之外，**还想要一份完整、专业、可下载/可打印成 PDF 的分析文档**时，用这套模板生成一个自包含的 `.html` 文件（写到 `outputs/` 目录，再 present_files 打开预览）。
>
> 适用两种场景：**复盘**（项目已完成）与**诊断**（项目还在投放中）——结构通用，只是措辞与结尾清单标题不同（复盘→【下次这样投】，诊断→【接下来这样做】）。
>
> **视觉基线（统一 UI，2026 起）**：整份报告套 **html-report-card 的统一外框**——顶部 `banner`（腾讯蓝 #0052D9 渐变 + 品牌行「金手指 · AI 投放助手」）、白色 `body` 容器、`section-title`（序号 + 标题、无左竖条）、`callout`（2 色）、`data-table`。**主色统一 `--brand:#0052D9`（腾讯蓝，来自 TDesign 色板）**。
>
> **业务专属组件保留**：折线图、成交漏斗、KPI 卡、素材分析三部分表 —— 这些是投放分析的核心可视化，套壳时**原样保留**。逐日走势**用折线图可视化，不铺完整明细表**。
>
> **涨红跌绿铁律（金融/投放合规，务必保留）**：成本/消耗走势里"成本上涨=坏事标红 `--up:#d23f3f`""成本下降=好事标绿 `--down:#2f9e63`"，消耗线用蓝 `#2f6fd0`。这套涨跌色**独立于**外框主色，两者变量分开、不冲突。
>
> **顶部先给大白话总结**（延续艾投口语风格，让小白先看懂结论）→ 一条虚线分隔 → **下面接一份专业数据文档**（给想深挖的人看）。
>
> **数据文档结构（共 6 节）**：1 投放表现总览（KPI+漏斗）→ 2 逐日走势（折线图）→ 3 阶段对比 → **4 素材分析（固定三部分：结构分析 / 效果排行 / 素材建议）** → 5 综合评价 → 6 下一波建议。
>
> **话术铁律（重要）**：全文避免"亏、花冤了、烧钱、失分、硬广"等负面/责备式表述，一律换成中性、建设性的说法——如"这部分预算效率偏低""可以省下来投到更能出单的地方""还能更好的地方""可优化点"。让用户看完是"知道下次怎么更好"，而不是"被批评了一顿"。

---

## 一、生成前必须先凑齐的数据（缺什么就在报告里如实标"无数据"）

| 数据 | 用在哪 | 缺失怎么办 |
|---|---|---|
| 总花费 / 投放天数 / 日均消耗 | 总账、表现总览 | 必需，缺了没法算 |
| 总曝光 / 总点击 / 点击率 | 表现总览、漏斗 | 缺则该行留"—" |
| 结果数（订单/线索/加粉）/ 结果成本 | 总账、漏斗、评分 | 必需 |
| 成交金额 GMV / ROI | 总账、评分 | 无电商成交则整块隐藏 |
| 逐日：日期·消耗·结果数·单均成本 | **折线图** | 至少要有"消耗"和"单均成本"两条，才能画图 |
| 阶段划分（冷启动/高峰/衰退等） | 阶段对比 | 可按走势自行划分 |
| 素材明细（名称·形式[视频/图片]·卖点主题·消耗·点击率·结果·单价） | **素材分析三部分** | 缺形式/主题则只做能做的维度；全缺则隐藏该节 |
| 当初目标 / 中间调整记录 | 结论定调、可优化点 | 问用户 |

> 铁律照旧：**不套行业标准值**（好坏只跟自己的目标和前后期比）、**数据缺就直说不编**、**不打包票**、底部**必须保留 mock/免责说明**（真实数据时改成"数据来源"说明）。

---

## 二、折线图坐标换算（最关键，务必照公式算 points）

折线图是纯 SVG 手绘，**不依赖任何图表库**（打印/存 PDF 都稳定）。画布固定 `viewBox="0 0 880 340"`，绘图区：

- **X 轴**：左边距 `x0 = 56`，右边界 `x1 = 836`，宽度 `780`。N 个数据点时，第 i 个点（i 从 0 开始）：
  `x = 56 + 780 * i / (N - 1)`（N=20 时步长≈41.05）
- **Y 轴**：顶 `y_top = 40`，底 `y_bottom = 280`，高 `240`。
- **左轴 = 消耗**，量程 `0 ~ Cmax`（把最大日消耗向上取整到整百，如 700→800）：
  `y_消耗 = 280 - (消耗 / Cmax) * 240`
- **右轴 = 单均成本**，量程 `0 ~ Pmax`（Pmax 取一个能容纳"正常波动"的整值，如 120）：
  `y_成本 = 280 - min(成本, Pmax) / Pmax * 240`
  → **超过 Pmax 的点**（如成本飙到 280）不要硬画（会把整条线压扁），钉在顶部 `y≈40`，另用**空心方块 + 文字标注**"成本飙至 ¥XXX（超轴顶）"。
- 结果数为 0 的日子（无单）单均成本记为无穷大，按"超轴顶"处理或断线。

> 生成时：先把两串 y 值算好，拼成 `points="x0,y0 x1,y1 ..."`，分别填进蓝线（消耗）和红线（成本）两条 `<polyline>`。左轴刻度文字 `Cmax / Cmax*0.75 / 0.5 / 0.25 / 0`，右轴同理换成 `Pmax` 系列。
>
> **配色遵循中国习惯**：成本/消耗走势里，"成本上涨=坏事标红(#d23f3f)"、"成本下降=好事标绿(#2f9e63)"；消耗线用蓝(#2f6fd0)。阶段背景：冷启动=蓝底(#e9f1fc)、高峰=绿底(#e8f6ee)、衰退=红底(#fbeaea)。

---

## 三、完整 HTML 骨架（金手指统一外框 + 业务图表；复制后替换所有 `{{...}}` 占位；不需要的整节可删）

> 说明：`<style>` 里分两层变量——`:root` 上半是 **html-report-card 统一外框变量**（`--brand:#0052D9` 腾讯蓝等），下半是 **业务图表变量**（`--up/--down/--blue` 涨红跌绿）。两层不冲突，都要保留。banner 品牌行固定「金手指 · AI 投放助手」，花名「艾投」只在页脚出现。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{品牌/店铺}} · {{产品}}{{渠道}}投放{{复盘|诊断}}报告</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  :root{
    /* ===== html-report-card 统一外框变量（主色=腾讯蓝 #0052D9，TDesign 色板）===== */
    --brand:#0052D9; --brand-deep:#003A99; --brand-soft:#E8F0FE;
    --ink:#1F2329; --ink2:#4E5969; --ink3:#86909C;
    --line:#E5E6EB; --line2:#F0F2F5;
    --bg:#F7F8FA; --card:#FFFFFF;
    /* ===== 业务图表变量（涨红跌绿，金融/投放合规，独立于主色）===== */
    --red:#d23f3f; --red-bg:#fbeaea;
    --green:#2f9e63; --green-bg:#e8f6ee;
    --amber:#c8860d; --amber-bg:#fdf3e0;
    --blue:#2f6fd0; --blue-bg:#e9f1fc;
    --up:#d23f3f; --down:#2f9e63;   /* 涨红跌绿，中国习惯 */
  }
  body{ font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; color:var(--ink); background:var(--bg); line-height:1.7; font-size:14px; -webkit-font-smoothing:antialiased; }
  .container{ max-width:920px; margin:0 auto; padding:32px 20px 80px; }

  /* ===== 顶部 Banner（统一外框，腾讯蓝渐变） ===== */
  .banner{ background:linear-gradient(135deg,var(--brand) 0%,var(--brand-deep) 100%); color:#fff; padding:28px 36px; border-radius:16px 16px 0 0; position:relative; overflow:hidden; }
  .banner::after{ content:""; position:absolute; right:-40px; top:-40px; width:200px; height:200px; background:rgba(255,255,255,0.06); border-radius:50%; }
  .banner .brand-tag{ font-size:13px; color:rgba(255,255,255,0.85); margin:0 0 10px 0; letter-spacing:.3px; position:relative; z-index:1; }
  .banner .brand-tag .sep{ margin:0 6px; opacity:.6; }
  .banner h1{ font-size:24px; font-weight:600; margin:0 0 4px 0; letter-spacing:.3px; }
  .banner h1.title{ font-size:24px; font-weight:600; }
  .banner .subtitle{ font-size:13.5px; opacity:.9; margin:0; }
  .banner .meta{ margin-top:14px; font-size:13px; opacity:.85; display:flex; gap:18px; flex-wrap:wrap; }
  .banner .meta span{ display:inline-flex; align-items:center; gap:6px; }
  .banner .meta i.bi{ font-size:14px; opacity:.9; }

  /* ===== 主体白容器 ===== */
  .doc{ background:var(--card); padding:32px 40px 20px; border-radius:0 0 16px 16px; box-shadow:0 1px 4px rgba(0,0,0,.04); }
  .nav{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 24px; padding-bottom:18px; border-bottom:1px solid var(--line); }
  .nav a{ font-size:12px; color:var(--ink2); text-decoration:none; padding:4px 10px; border-radius:6px; background:var(--line2); }
  .nav a:hover{ color:var(--brand); }
  section{ margin-top:34px; }

  /* ===== 章节大标题（统一：序号 + 标题，无左竖条） ===== */
  h2.section-title{ font-size:17px; font-weight:600; color:var(--ink); margin:0 0 14px 0; line-height:1.35; display:flex; align-items:baseline; gap:10px; }
  h2.section-title .idx{ color:var(--brand); font-weight:700; font-size:18px; letter-spacing:.5px; }
  h3{ font-size:14.5px; font-weight:600; margin:22px 0 12px; color:var(--ink); }
  .sub{ color:var(--ink2); font-size:12.5px; }

  /* ===== KPI 卡（业务，保留） ===== */
  .kpis{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
  .kpi{ background:var(--bg); border-radius:10px; padding:14px 16px; }
  .kpi .lab{ font-size:12px; color:var(--ink3); }
  .kpi .val{ font-size:22px; font-weight:700; margin-top:4px; }
  .kpi .note{ font-size:11px; color:var(--ink3); margin-top:2px; }

  /* ===== 表格（统一 data-table 皮，兼容业务列） ===== */
  table.data-table, table{ width:100%; border-collapse:collapse; font-size:12.5px; margin-top:6px; }
  th,td{ text-align:left; padding:10px 12px; border-bottom:1px solid var(--line); }
  th{ background:#FAFBFC; color:var(--ink2); font-weight:500; font-size:12px; white-space:nowrap; border-bottom:2px solid var(--line); }
  td.num,th.num{ text-align:right; font-variant-numeric:tabular-nums; }
  tr:hover td{ background:#FAFBFC; }

  /* ===== 徽章 / 标签（业务涨红跌绿 + 星级） ===== */
  .tag{ display:inline-block; font-size:11px; padding:1px 7px; border-radius:5px; font-weight:600; }
  .t-good{ background:var(--green-bg); color:var(--green); }
  .t-warn{ background:var(--amber-bg); color:var(--amber); }
  .t-bad{ background:var(--red-bg); color:var(--red); }
  .t-info{ background:var(--blue-bg); color:var(--blue); }
  .up{ color:var(--up); font-weight:600; }
  .down{ color:var(--down); font-weight:600; }
  .stars{ color:var(--amber); letter-spacing:2px; font-size:14px; }
  .stars .off{ color:#dcdfe4; }

  /* ===== 提示条 callout（统一外框：默认蓝=中性/正向；业务额外保留 star/risk/good 语义色） ===== */
  .callout{ border-radius:8px; padding:12px 16px; font-size:13px; margin-top:14px; border-left:3px solid var(--brand); background:var(--brand-soft); color:var(--ink); line-height:1.7; }
  .callout strong.title{ color:var(--brand-deep); font-weight:600; margin-right:4px; }
  .c-tip{ background:var(--brand-soft); border-left-color:var(--brand); color:#20375f; }
  .c-star{ background:var(--amber-bg); border-left-color:var(--amber); color:#9a6a08; }
  .c-risk{ background:var(--red-bg); border-left-color:var(--red); color:#a63030; }
  .c-good{ background:var(--green-bg); border-left-color:var(--green); color:#217a4c; }

  /* ===== 成交漏斗（业务，保留；条形改用主色系） ===== */
  .funnel{ display:flex; flex-direction:column; gap:6px; margin-top:8px; }
  .frow{ display:flex; align-items:center; gap:12px; }
  .fbar{ height:34px; border-radius:6px; background:var(--brand); display:flex; align-items:center; padding:0 12px; color:#fff; font-size:12px; font-weight:600; min-width:70px; }
  .fmeta{ font-size:12px; color:var(--ink2); }

  /* ===== 折线图卡（业务，保留） ===== */
  .chart-card{ border:1px solid var(--line); border-radius:12px; padding:16px 14px 8px; background:var(--card); }
  .chart-legend{ display:flex; gap:20px; justify-content:center; margin-bottom:6px; }
  .chart-legend .lg{ font-size:12px; color:var(--ink2); display:flex; align-items:center; gap:6px; }
  .chart-legend .dot{ width:14px; height:3px; border-radius:2px; display:inline-block; }
  .linechart{ width:100%; height:auto; display:block; }

  /* ===== 大白话总结块（业务，保留；改用主色系） ===== */
  .easy{ background:#fff; border:1.5px solid var(--brand-soft); border-radius:14px; padding:24px 26px; margin-top:4px; }
  .easy .ehead{ display:flex; align-items:center; gap:10px; margin-bottom:6px; }
  .easy .badge{ width:38px; height:38px; border-radius:50%; background:var(--brand-soft); color:var(--brand); display:flex; align-items:center; justify-content:center; font-weight:700; font-size:13px; }
  .easy h2{ border:none; padding:0; font-size:18px; font-weight:600; }
  .easy .esub{ font-size:12.5px; color:var(--ink2); margin-bottom:14px; }
  .eblock{ margin-top:16px; }
  .eblock .et{ font-weight:700; font-size:14px; margin-bottom:6px; }
  .eblock p, .eblock li{ font-size:13.5px; color:var(--ink); }
  .eblock ol{ padding-left:20px; }
  .eblock ol li{ margin:7px 0; }

  .divider{ text-align:center; color:var(--ink3); font-size:12px; margin:34px 0 4px; position:relative; }
  .divider span{ background:var(--card); padding:0 14px; position:relative; }
  .divider:before{ content:""; display:block; border-top:1px dashed var(--line); position:relative; top:11px; }

  .mock-note{ background:var(--amber-bg); color:#8a5d06; border-radius:8px; padding:8px 14px; font-size:12px; margin-top:16px; }
  .disclaimer{ text-align:center; font-size:11.5px; color:var(--ink3); margin-top:24px; padding:16px 0; border-top:1px solid var(--line); }

  @media print{
    body{ background:#fff; } .container{ padding:0; max-width:none; }
    .banner{ border-radius:0; } .doc{ border-radius:0; box-shadow:none; padding:0; }
    .nav{ display:none; } section{ break-inside:avoid; } tr:hover td{ background:transparent; }
  }
  @media (max-width:640px){ .kpis{ grid-template-columns:repeat(2,1fr); } .doc{ padding:24px 18px; } .banner{ padding:24px 20px; } }
</style>
</head>
<body>
<div class="container">

  <!-- ============ 顶部 Banner（统一外框：品牌行固定「金手指 · AI 投放助手」） ============ -->
  <div class="banner">
    <p class="brand-tag">金手指<span class="sep">·</span>AI 投放助手</p>
    <h1 class="title">{{品牌/店铺}} · {{产品}}{{渠道}}投放{{复盘|诊断}}报告</h1>
    <p class="subtitle">数据区间 {{起}} 至 {{止}}（{{天数}}天）｜ 状态：{{已结案|投放中}}</p>
    <div class="meta">
      <span><i class="bi bi-calendar3"></i>{{生成时间}}</span>
      <span><i class="bi bi-flag"></i>{{行业}} · {{渠道}}</span>
      <span><i class="bi bi-bullseye"></i>目标：{{目标}}</span>
      <span><i class="bi bi-hourglass-split"></i>{{天数}} 天</span>
    </div>
  </div>

  <div class="doc">

  <div class="nav">
    <a href="#easy">大白话总结</a><a href="#s1">1 表现总览</a><a href="#s2">2 逐日走势</a>
    <a href="#s3">3 阶段对比</a><a href="#s4">4 素材分析</a><a href="#s5">5 综合评价</a>
    <a href="#s6">6 {{下一波建议|接下来这样做}}</a>
  </div>

  <!-- ===== 大白话总结（顶部，口语，小白先看这段） ===== -->
  <section id="easy" style="margin-top:0;">
  <div class="easy">
    <div class="ehead"><div class="badge">艾投</div><div><h2>先用大白话给你说结论</h2></div></div>
    <div class="esub">{{一句话开场：这波投完了/还在投，我把情况给你捋了捋，先看这几句}}</div>
    <div class="eblock"><div class="et">① {{这波的总账|现在的情况}}</div><p>{{花了多少、换来多少、一个结果多少钱、划不划算、达没达标，一句话定调；后半程若有效率偏低处，用"还能更好"的中性说法带过，不用"花冤了"}}</p></div>
    <div class="eblock"><div class="et">② 做对了什么{{（下次接着用）|（保持）}}</div><ol><li>{{亮点1+为什么对+怎么用}}</li><li>{{亮点2}}</li></ol></div>
    <div class="eblock"><div class="et">③ {{还能更好的地方（下次可优化）|还能更好的地方}}</div><ol><li>{{可优化点1+原因+下次怎么做，避免"亏/花冤了/烧钱"}}</li><li>{{可优化点2}}</li></ol></div>
    <div class="eblock"><div class="et">④ 【{{下次这样投|接下来这样做}}】</div>
      <ol><li>{{行动1}}</li><li>{{行动2}}</li><li>{{行动3}}</li><li>{{行动4}}</li><li>{{行动5}}</li></ol>
      <p style="margin-top:10px; color:var(--ink2);">{{复盘结尾："这波先总结到这，下次开投前照这几条来" / 诊断结尾："先做这些，观察 X 天再回来找我看"}} 👌</p>
    </div>
  </div>
  </section>

  <div class="divider"><span>以下是完整数据分析，给想深挖细节的你看</span></div>

  <!-- ===== 1 表现总览（8 KPI + 漏斗） ===== -->
  <section id="s1">
    <h2 class="section-title"><span class="idx">01</span>投放表现总览</h2>
    <div class="kpis">
      <!-- kpi ×8：累计消耗/总曝光/总点击/点击率 + 总结果/结果成本/ROI/转化率 -->
      <div class="kpi"><div class="lab">累计消耗</div><div class="val">¥{{}}</div><div class="note">日均 ¥{{}}</div></div>
      <!-- ...其余 7 张同结构 -->
    </div>
    <h3>成交漏斗</h3>
    <div class="funnel">
      <div class="frow"><div class="fbar" style="width:100%;">曝光 {{曝光}}</div><div class="fmeta">—</div></div>
      <div class="frow"><div class="fbar" style="width:{{比例}}%; background:#4d86dd;">点击 {{点击}}</div><div class="fmeta">点击率 {{ctr}}</div></div>
      <div class="frow"><div class="fbar" style="width:{{比例}}%; background:#6f9fe6;">进店/详情 {{进店}}</div><div class="fmeta">{{占比}}</div></div>
      <div class="frow"><div class="fbar" style="width:{{比例}}%; background:#93b8ef; color:#1f3a63;">{{结果}} {{结果数}}</div><div class="fmeta">{{转化率}}</div></div>
    </div>
  </section>

  <!-- ===== 2 逐日走势（折线图，不铺明细表；涨红跌绿保留） ===== -->
  <section id="s2">
    <h2 class="section-title"><span class="idx">02</span>逐日走势</h2>
    <div class="sub" style="margin-bottom:14px;">全周期每日「消耗」与「单均成本」走势 —— 一眼看出爬坡、高峰、衰退三段。</div>
    <div class="chart-card">
      <div class="chart-legend">
        <span class="lg"><i class="dot" style="background:#2f6fd0;"></i>每日消耗（元）</span>
        <span class="lg"><i class="dot" style="background:#d23f3f;"></i>单均成本（元/{{单位}}）</span>
      </div>
      <svg viewBox="0 0 880 340" class="linechart" role="img" aria-label="逐日消耗与单均成本折线图">
        <g font-size="11" fill="#8a94a0">
          <line x1="56" y1="40"  x2="836" y2="40"  stroke="#f0f2f5"/>
          <line x1="56" y1="100" x2="836" y2="100" stroke="#f0f2f5"/>
          <line x1="56" y1="160" x2="836" y2="160" stroke="#f0f2f5"/>
          <line x1="56" y1="220" x2="836" y2="220" stroke="#f0f2f5"/>
          <line x1="56" y1="280" x2="836" y2="280" stroke="#e6e9ee"/>
          <text x="50" y="44"  text-anchor="end">{{Cmax}}</text>
          <text x="50" y="104" text-anchor="end">{{Cmax*0.75}}</text>
          <text x="50" y="164" text-anchor="end">{{Cmax*0.5}}</text>
          <text x="50" y="224" text-anchor="end">{{Cmax*0.25}}</text>
          <text x="50" y="284" text-anchor="end">0</text>
          <text x="842" y="44"  text-anchor="start" fill="#d23f3f">{{Pmax}}</text>
          <text x="842" y="104" text-anchor="start" fill="#d23f3f">{{Pmax*0.75}}</text>
          <text x="842" y="164" text-anchor="start" fill="#d23f3f">{{Pmax*0.5}}</text>
          <text x="842" y="224" text-anchor="start" fill="#d23f3f">{{Pmax*0.25}}</text>
          <text x="842" y="284" text-anchor="start" fill="#d23f3f">0</text>
        </g>
        <g opacity="0.55">
          <rect x="56"  y="40" width="{{w1}}" height="240" fill="#e9f1fc"/>
          <rect x="{{x2}}" y="40" width="{{w2}}" height="240" fill="#e8f6ee"/>
          <rect x="{{x3}}" y="40" width="{{w3}}" height="240" fill="#fbeaea"/>
        </g>
        <g font-size="11" font-weight="600">
          <text x="{{c1}}" y="56" text-anchor="middle" fill="#2f6fd0">冷启动爬坡</text>
          <text x="{{c2}}" y="56" text-anchor="middle" fill="#2f9e63">高峰期</text>
          <text x="{{c3}}" y="56" text-anchor="middle" fill="#d23f3f">衰退 / 收尾</text>
        </g>
        <polyline fill="none" stroke="#2f6fd0" stroke-width="2.5" stroke-linejoin="round" points="{{消耗points}}"/>
        <polyline fill="none" stroke="#d23f3f" stroke-width="2.5" stroke-linejoin="round" points="{{成本points}}"/>
        <g fill="#fff" stroke="#d23f3f" stroke-width="2"><rect x="{{x}}" y="36" width="8" height="8"/></g>
        <text x="{{x}}" y="30" text-anchor="middle" font-size="10" fill="#d23f3f">成本飙至 ¥{{值}}（超轴顶）</text>
        <g font-size="10" fill="#8a94a0">
          <text x="56"  y="300" text-anchor="middle">{{d0}}</text>
          <text x="835" y="300" text-anchor="middle">{{dN}}</text>
        </g>
      </svg>
    </div>
    <div class="callout c-tip">💡 折线一眼看懂：{{一句话概括蓝线消耗走势 + 红线成本先降后升的拐点，点明"爬坡→高峰→衰退"或对应结论}}</div>
  </section>

  <!-- ===== 3 阶段对比（每阶段一张表 + callout，涨红跌绿；措辞用"可优化点"不用"失分/花冤了"） ===== -->
  <section id="s3"><h2 class="section-title"><span class="idx">03</span>阶段对比分析</h2><!-- ... --></section>

  <!-- ===== 4 素材分析（固定三部分：结构分析 / 效果排行 / 素材建议） ===== -->
  <section id="s4">
    <h2 class="section-title"><span class="idx">04</span>素材分析</h2>
    <div class="sub" style="margin-bottom:6px;">数据区间：{{起}} 至 {{止}} ｜ 共 {{N}} 条素材在投（视频 {{n视频}} 条 + 图片 {{n图片}} 条）</div>

    <!-- 4.1 素材结构分析：按形式(视频/图片) + 按卖点/内容主题 + 按样式 -->
    <h3>4.1 素材结构分析</h3>
    <p style="font-size:13px; color:var(--ink2); margin:2px 0 10px;">先看这一波素材都是些什么类型、什么套路，预算都花在了哪种上面。</p>
    <div style="font-weight:600; font-size:13.5px; margin:14px 0 6px; color:var(--ink);">① 按素材形式分（视频 / 图片）</div>
    <table>
      <thead><tr><th>素材形式</th><th class="num">条数</th><th class="num">总消耗</th><th class="num">消耗占比</th><th class="num">总{{结果}}</th><th class="num">单均成本</th><th>一句话点评</th></tr></thead>
      <tbody>
      <tr><td>🎬 视频</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td>{{中性点评}}</td></tr>
      <tr><td>🖼️ 图片</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td>{{中性点评}}</td></tr>
      </tbody>
    </table>
    <div style="font-weight:600; font-size:13.5px; margin:18px 0 6px; color:var(--ink);">② 按卖点 / 内容主题分</div>
    <table>
      <thead><tr><th>内容主题（卖点）</th><th class="num">条数</th><th class="num">总消耗</th><th class="num">总{{结果}}</th><th class="num">单均成本</th><th>特征</th></tr></thead>
      <tbody>
      <tr><td>{{主题A，如"真人实穿·场景对比"}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td>{{}}</td></tr>
      <tr><td>{{主题B}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td>{{}}</td></tr>
      </tbody>
    </table>
    <div style="font-weight:600; font-size:13.5px; margin:18px 0 6px; color:var(--ink);">③ 按素材样式分（表现形式）</div>
    <table>
      <thead><tr><th>样式</th><th class="num">条数</th><th class="num">总{{结果}}</th><th class="num">单均成本</th><th>点评</th></tr></thead>
      <tbody><tr><td>{{样式，如"真人出镜·上身对比"}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td>{{}}</td></tr></tbody>
    </table>

    <!-- 4.2 素材效果排行：分类型/分形式的 top 素材 -->
    <h3>4.2 素材效果排行（分类型 / 分形式的 Top 素材）</h3>
    <div style="font-weight:600; font-size:13.5px; margin:14px 0 6px; color:var(--ink);">🎬 视频类 Top 素材</div>
    <table>
      <thead><tr><th>排名</th><th>素材名称</th><th class="num">消耗</th><th class="num">点击率</th><th class="num">{{结果}}</th><th class="num">单均成本</th><th>评价</th></tr></thead>
      <tbody><tr><td>🥇</td><td>{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td><span class="tag t-good">{{}}</span></td></tr></tbody>
    </table>
    <div style="font-weight:600; font-size:13.5px; margin:16px 0 6px; color:var(--ink);">🖼️ 图片类 Top 素材</div>
    <table>
      <thead><tr><th>排名</th><th>素材名称</th><th class="num">消耗</th><th class="num">点击率</th><th class="num">{{结果}}</th><th class="num">单均成本</th><th>评价</th></tr></thead>
      <tbody><tr><td>🥇</td><td>{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td><td><span class="tag t-info">{{}}</span></td></tr></tbody>
    </table>
    <div style="font-weight:600; font-size:13.5px; margin:16px 0 6px; color:var(--ink);">🏆 按卖点看·各主题头部素材</div>
    <table>
      <thead><tr><th>卖点主题</th><th>头部素材</th><th class="num">{{结果}}</th><th class="num">单均成本</th></tr></thead>
      <tbody><tr><td>{{}}</td><td>{{}}</td><td class="num">{{}}</td><td class="num">{{}}</td></tr></tbody>
    </table>
    <div class="callout c-good">⭐ {{一句话点明头部素材集中度：Top N 贡献了 X% 的结果}}</div>

    <!-- 4.3 素材建议：跑量/高ROI规律 + 哪些特征放大 + 下次素材建议 -->
    <h3>4.3 素材建议（跑量 / 高 ROI 的规律 + 下次怎么做）</h3>
    <div class="callout c-star" style="margin-top:6px;">📌 <b>跑量 & 高 ROI 素材的共同规律（值得放大的特征）：</b></div>
    <table>
      <thead><tr><th>共同特征</th><th>具体表现</th><th>为什么有效</th></tr></thead>
      <tbody>
      <tr><td>{{特征1，如"真人出镜+上身对比"}}</td><td>{{}}</td><td>{{}}</td></tr>
      <tr><td>{{特征2}}</td><td>{{}}</td><td>{{}}</td></tr>
      </tbody>
    </table>
    <div class="callout c-tip" style="margin-top:14px;">💡 <b>【下次的素材建议】</b>（素材成品图找 <b>素材经理·苏策</b> 出，艾投不出图）</div>
    <table>
      <thead><tr><th>优先级</th><th>怎么做</th><th>预期</th></tr></thead>
      <tbody>
      <tr><td><span class="tag t-good">重点放大</span></td><td>{{围绕爆款结构产同系列，把哪个特征放大}}</td><td>{{}}</td></tr>
      <tr><td><span class="tag t-info">测试</span></td><td>{{做A/B/换钩子}}</td><td>{{}}</td></tr>
      <tr><td><span class="tag t-warn">调整</span></td><td>{{效率偏低的形式/主题预算转投更能出单的地方，措辞中性}}</td><td>{{}}</td></tr>
      </tbody>
    </table>
    <div class="callout c-good" style="margin-top:12px;">✅ 一句话总结：<b>{{下次继续押注哪种形式+卖点+样式，把爆款做成系列}}</b></div>
  </section>

  <!-- ===== 5 综合评价（5 维星级 + 亮点/可优化点 callout；说明用中性词） ===== -->
  <section id="s5"><h2 class="section-title"><span class="idx">05</span>综合评价</h2><!-- ... --></section>

  <!-- ===== 6 建议（分级表：重点/重要/建议 + 监控阈值 + 下期目标；优先级标签用"重点"不用"淘汰"式负面词） ===== -->
  <section id="s6"><h2 class="section-title"><span class="idx">06</span>{{下一波投放建议|接下来这样做}}</h2><!-- ... --></section>

  <div class="mock-note">📌 说明：{{真实数据→写"数据来源：XX平台后台导出" ；演示→写"本报告为演示样例，数据为虚构 mock，真实使用会先收集实际数据再据实生成，缺失数据如实标注不估算"}}</div>

  </div><!-- /.doc -->

  <div class="disclaimer">
    报告生成日期：{{日期}} ｜ 数据来源：{{来源}} ｜ 由「金手指 · AI 投放助手（艾投）」生成｜ 主色 #0052D9 TDesign
  </div>

</div>
</body>
</html>
```

---

## 四、生成与交付流程（专家照此执行）

1. **先出大白话总结**（对话里就给，四段式），确认用户认可结论。
2. 用户说"要完整文档/要报告/要下载"时，再套本模板生成 HTML：
   - 把凑齐的数据填进各 `{{占位符}}`；缺的节点整段删掉或标"无数据"。
   - **统一外框固定**：banner 品牌行照抄「金手指 · AI 投放助手」，页脚署名「金手指 · AI 投放助手（艾投）」，主色 `--brand:#0052D9` 不改。
   - **数据文档 6 节**：表现总览 / 逐日走势 / 阶段对比 / 素材分析(三部分) / 综合评价 / 建议。**不放"账户概览"节，也不放"互动明细"表**。
   - **素材分析必须是三部分**：4.1 结构分析（按视频/图片形式 + 按卖点/内容主题 + 按样式）→ 4.2 效果排行（分类型/分形式的 Top 素材）→ 4.3 素材建议（规律、放大特征、下次建议；图找苏策）。
   - 折线图 points 用 **§二** 公式逐点算好再填；**涨红跌绿不改**（成本涨红 `#d23f3f`、跌绿 `#2f9e63`、消耗蓝 `#2f6fd0`）。
   - **话术保持中性/建设性**：不用"亏、花冤了、烧钱、硬广、失分"，改用"效率偏低、可以省下来、还能更好、可优化点"。
   - 复盘→标题/结尾用【下次这样投】；诊断→用【接下来这样做】+"观察 X 天"。
3. 写到 `outputs/{{文件名}}.html`（文件名建议 `{品牌或主题}-投放{复盘|诊断}报告-{YYYYMMDD}.html`），再用 present_files 打开预览。
4. 提示用户 `Ctrl/Cmd + P` 可存成 PDF。
5. **底部免责/来源说明必须保留**；用真实数据时把 mock 声明改成数据来源说明。

> **视觉一致性**：本模板的统一外框（banner/主色/section-title/callout/data-table）与 `html-report-card` skill 同源，主色 #0052D9（腾讯蓝，TDesign 色板）。业务图表（折线图/漏斗/素材表）是投放专属扩展，套壳时保留、不删。
