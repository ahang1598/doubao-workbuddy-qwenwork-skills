# Richee 报告设计系统（HTML/Word 输出统一视觉）

> 本文件是本技能发布包内的输出规范，已经内化所需视觉规则；运行时不读取外部规范目录。
>
> 来源：`Richee 图表组件设计规范版 v3.8`。本技能输出**HTML 报告**与**Word 报告**的视觉风格
> 一律遵循本设计系统：**黑白极简 + 浅灰底 + 单绿强调 + 状态色仅用于标签**，无衬线（PingFang SC）。
> 完整 CSS 见 `assets/richee-report.css`；生成 HTML 时把该文件**全文内联**进 `<style>`。

---

## 1. 设计令牌速查（与设计规范库一致，勿改值）

| 类别 | 关键令牌 | 值 |
|---|---|---|
| 底/纸 | `--bg` / `--white` | `#f6f7f9` / `#ffffff` |
| 主黑/正文 | `--black` / `--text` | `#0a0d12` |
| 次要文字 | `--muted` | `#6b7280` |
| 分割线 | `--line` | `#e2e5ea` |
| 强调（单绿） | `--accent` / `--accent-dark` | `#32d583` / `#039855` |
| 危险/警告/成功/信息 | `--red`/`--amber`/`--green`/`--blue-text` | `#d92d20`/`#b54708`/`#039855`/`#175cd3` |
| 字体 | `--font-sans` | `'PingFang SC','Inter',-apple-system,sans-serif` |
| 圆角 | `--radius-md/lg/xl/full` | `8/12/16/9999px` |
| 阴影 | `--shadow-xs/sm/lg` | 见 CSS |

> **配色纪律**：黑白灰承载 90% 信息；绿色仅用于强调（标题下划线、进度条、结论卡微渐变、时间轴节点）；
> 红/琥珀/绿/蓝**只用于标签与风险等级**，不大面积铺底。

---

## 2. 技能语义 → Richee 组件映射（核心）

| 技能语义元素 | Richee 组件 / 类 | 说明 |
|---|---|---|
| 免责声明（D2 强制） | `.disclaimer` | 报告首部；琥珀边框浅底；使用纯文字标题 |
| 确定性标签 `[法规原文]/[权威指南]/[一般评论]/[待验证]` | `.lbl .lbl-l1/l2/l3/l4` | L1 黑、L2 蓝、L3 灰、L4 琥珀；闭集，禁自创 |
| 访问状态 `[已验证]/[需注册]/[付费]/[反爬]/[未验证]/[未找到]` | `.acc .acc-ok/reg/pay/bot/warn/none` | 脚注与正文行内徽标 |
| 时效性 `[3–6月复核]/[6–12月复核]/[1–3年复核]/[稳定]` | `.fresh .fresh-critical/high/mid/low` | 红/琥珀/黄/绿 |
| 风险等级 高/中/低 | `.tag .high/.mid/.low`（`.info` 备用） | 复用规范库标签 |
| 置信度百分比 | `.confidence`（数值 + `.track/.fill` 进度条） | 数值文字 + 百分比可视化 |
| 核心判断 / 结论 | `.conclusion`（`.head` + `.body`） | 微绿渐变结论卡，置报告前部 |
| 执行摘要关键数字（建议 4 个） | `.grid-4` + `.kpi`（name/value/note） | 指标卡组 |
| 比较矩阵（路径 C） | `table`（≤5 列，外层 `.table-scroll`） 或 `.matrix` | 表头黑底白字；≤3 法域×5 维度 |
| 立法演进 / 案件时序 | `.timeline` + `.t-item`（t-title/t-text） | 绿渐变轴线 |
| 支持强度 / 各项对比 | `.bar-row` + `.track/.fill` | 横向热度条 |
| 脚注（核验证据，6 字段） | `.footnotes` + `.fn-item` + `.ref-link`/`.back-ref` | 正文 `<sup>` 跳转，脚注 `↩` 回跳 |
| **导航目录（长报告必备）** | `.layout.with-nav` + `<aside class="nav">` + `#锚点` | 章节 ≥3 时左侧 sticky 可点击 TOC；平板转顶部横排、打印隐藏 |
| 页脚（来源平台/生成信息） | `.footer` + `.btn` | 黑底；标注是否用了 LDH |

> **何时用导航目录**：路径 B 全面报告、路径 C 多法域比较（章节 ≥3）**必须**用 `.layout.with-nav` + `.nav`；
> 路径 A 快速概览（1-2 屏）可省略，直接 `.layout`（单栏）。每个 `<section>` 给唯一 `id`，nav `<a href="#id">` 一一对应。

---

## 3. HTML 报告骨架（路径 B 全面报告示例，路径 A/C 裁剪即可）

```html
<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>[法域] [主题] 法律研究报告</title>
<style>/* ← 内联 assets/richee-report.css 全文 */</style>
</head><body>

<header class="topbar">
  <div class="brand"><div class="logo">睿</div><div>Richee 法律研究报告</div></div>
  <div class="status"><span class="dot"></span><span>[法域] · [主题] · 数据源：LDH+预置官方源 / 仅预置官方源</span></div>
</header>

<section class="hero">
  <div class="small-no">[法域简码]</div>
  <h1>[法域] [主题] 法律研究报告</h1>
  <p class="sub">生成时间 YYYY-MM-DD ｜ 研究模式：全面报告 ｜ 整体置信度 XX%</p>
  <div class="meta">
    <span class="pill">[法域]</span><span class="pill">[主题]</span>
    <span class="pill">L1-L4 来源分层</span><span class="pill">实时核验</span>
  </div>
</section>

<!-- 长报告：左侧导航目录（章节≥3）。短报告改用 <main class="layout"> 单栏并删除 <aside> -->
<main class="layout with-nav">
  <aside class="nav">
    <h3>REPORT SECTIONS</h3>
    <a href="#s01">01 执行摘要</a>
    <a href="#s02">02 [子问题1]</a>
    <a href="#s03">03 [子问题2]</a>
    <a href="#sref">11 核验证据</a>
  </aside>
  <article class="content">

  <!-- 免责声明（D2 强制） -->
  <div class="disclaimer"><strong>免责声明</strong>
    <p>本文档由 AI 辅助生成，仅供参考，不构成正式法律意见，不能替代具有执业资格的律师；
    外国法、跨境监管与当地程序结论应由目标法域执业律师结合最新有效材料复核。</p></div>

  <!-- 执行摘要：结论卡 + 指标卡（id 与 nav 锚点一一对应） -->
  <section class="section" id="s01">
    <div class="sec-no">执行摘要</div><h2>核心判断</h2>
    <div class="conclusion"><div class="head"><strong>综合结论</strong><span class="tag info">需当地律师确认</span></div>
      <div class="body">[一句话核心结论]…</div></div>
    <div class="grid-4" style="margin-top:14px">
      <div class="kpi"><div class="name">适用法</div><div class="value">…</div><div class="note">…</div></div>
      <!-- ×4 -->
    </div>
  </section>

  <!-- 子问题分章：确定性标签 + 脚注 + 本节置信度 -->
  <section class="section" id="s02">
    <div class="sec-no">01</div><h2>[子问题]</h2>
    <p><span class="lbl lbl-l1">[法规原文]</span>《劳动法》第 XX 条规定……<sup><a href="#fn-1" id="ref-1" class="ref-link">[1]</a></sup>。</p>
    <div class="confidence"><span class="stars">置信度 92%</span>
      <div class="track"><div class="fill" style="width:92%"></div></div></div>
  </section>

  <!-- 时效/立法变更：fresh 徽标 + timeline（如适用） -->
  <!-- 比较矩阵（路径 C）：<div class="table-scroll"><table>…≤5 列…</table></div> -->

  <!-- 脚注区 -->
  <section class="footnotes" id="sref"><h2>参考文献</h2>
    <div class="fn-item" id="fn-1"><strong>[1]</strong>
      <span class="lbl lbl-l1">[法规原文]</span> <span class="acc acc-ok">[已验证]</span>
      《劳动法》第 XX 条 —
      <a href="https://…" target="_blank">官方源 URL</a>
      <span class="src">｜ 检索：LegalDataHunter ｜ 验证时间 YYYY-MM-DD ｜ 锚点：「Article XX…」｜ 目录定位：resources.md §12.x</span>
      <a href="#ref-1" class="back-ref" title="返回正文">↩</a></div>
  </section>
  </article>
</main>

<!-- 可选：导航高亮（scrollspy，纯原生，无依赖）。放 </body> 前 -->
<script>
(function(){
  var links=[].slice.call(document.querySelectorAll('.nav a'));
  if(!links.length)return;
  var map=links.map(function(a){var t=document.querySelector(a.getAttribute('href'));return{a:a,t:t};}).filter(function(x){return x.t;});
  function onScroll(){
    var y=window.scrollY+120,cur=map[0];
    map.forEach(function(x){if(x.t.offsetTop<=y)cur=x;});
    links.forEach(function(a){a.classList.remove('active');});
    if(cur)cur.a.classList.add('active');
  }
  window.addEventListener('scroll',onScroll,{passive:true});onScroll();
})();
</script>

</article>

  <div class="footer">
    <div><strong>Richee 全球法律研究</strong>
      <p>本报告由 AI 辅助生成，仅供参考。数据路径：[LDH 实时检索 + 预置官方源 / 仅预置官方源]。</p></div>
    <div class="btn">仅供参考</div>
  </div>
</main></body></html>
```

---

## 4. Word(.docx) 视觉映射（同一设计语言，非 CSS）

docx 无法用 CSS，但**视觉语言对齐 Richee**：

| 维度 | Word 取值 |
|---|---|
| 字体 | **PingFang SC**（中，fallback 苹方→微软雅黑→Noto Sans CJK）/ Inter（英，fallback Calibri）—— **无衬线**，与 Richee 一致 |
| 标题 | 报告题 600 字重；一级/二级递减；标题色用 `--black` (#0a0d12) |
| 配色 | 黑白灰为主 + **克制绿强调**（标题装饰线/正向结论可用 `#039855`）；状态色仅用于标签与风险等级单元格 |
| 表格 | 表头黑底白字（#0a0d12）、白底正文、细灰线（#e2e5ea）；宽度 ≤A4 内容区（见 output-formats.md §3） |
| 结论/风险 | 用浅底色块对应 `.conclusion`/`.tag`（success-50/danger-50/warning-50），不大面积铺色 |
| 状态标签 | **一律使用方括号文字标签**（D3-S2，见 output-formats.md §3） |

---

## 5. 三格式一致性与红线

- **Markdown**：纯文本，不带样式；状态和时效使用文字标签。
- **HTML**：内联 `assets/richee-report.css`，按 §2 映射用组件类；状态和时效使用文字标签。
- **Word**：按 §4 映射；状态和时效使用文字标签；表格宽度受限（D3-S3）。
- **不改语义**：设计系统只换"外观"，不改确定性标签闭集、不升级确定性、不省略免责与脚注六字段——
  这些由 `verification-engine.md` 与 `output-formats.md §0` 约束，优先级高于样式。
- 正式法律报告不使用装饰性 emoji；层级和重点通过标题、间距、颜色和文字标签表达。
