---
name: html-report-card-suce
description: 把结构化交付物（方案、报告、评估、诊断、路线图、清单、对照表、日历、报价、盘点等）渲染为统一视觉规范的单文件 HTML 卡片。适用于任何专家/专家团需要产出"可交付文档"而非纯对话回答的场景：用户说"给我一份/生成一个/整理成 XX/出一份文档"，或正文包含 ≥2 段结构化内容（表格、多层清单、时间轴、评分、多要点对比）。内含 16 条视觉硬规则、9 个组件配方、可直接内联的 CSS 主题与 HTML 骨架，品牌信息通过占位符配置，行业中立、开箱即用。触发词：HTML 卡片、生成报告、输出文档、卡片模板、可视化交付物、HTML 规范。
description_zh: 生成统一规范的 HTML 卡片
description_en: Generate standardized HTML report cards
disable: false
agent_created: true
---

# html-report-card-suce

把结构化交付物渲染为**单文件、离线可看、视觉统一**的 HTML 卡片。

本 skill 是通用版（行业中立），从一套已在生产环境跑通的专家团规范抽象而来。品牌名、角色名、配色全部通过占位符/CSS 变量配置。

## When to use

**用 HTML 渲染**（满足任一）：
1. Agent 的「输出规范」里显式列出的**交付物**（方案、诊断报告、评估表、路线图、清单、对照表、日历、报价单等）
2. 正文包含 **≥2 段结构化内容**（表格、多层清单、时间轴、多要点对比、评分）
3. 用户明确说"给我一份 / 生成一个 / 整理成 XX / 出一份文档"

**不用 HTML，保持纯文本**：
1. 闲聊、追问、澄清
2. 单条问答（无多层结构）
3. **要被复制走使用的成品正文**（文案稿、代码、邮件正文）—— 套 HTML 反而不便复制
4. 工程管道里的 **JSON 中间接口** —— HTML 只在最终"给人看"那一层套壳

## Steps

1. **确认触发** —— 对照上面判定规则；不符合就纯文本回答，不要硬套 HTML。

2. **读规范** —— 动手前必读 `references/design-rules.md`（**16 条硬规则，违反即返工**），组件写法查 `references/component-guide.md`。

3. **本包已预配置金手指品牌（首次使用可略过配置）** —— 本专家包为「金手指 · 素材经理」专属：
   - brand-tag 整段写死为 `金手指 · 素材经理`（`template.html` 已写死，agent 不许改任何一个字，见规则 16）
   - `BRAND_LOGO = assets/brand/logo.png`（无文字蓝 J 上升气泡；版头**右上角用白色圆角方块托住，不反白**——蓝 J 压白底清晰，保住品牌色）
   - 视觉体系 = **腾讯蓝体系**（先读 design-rules 规则 0）：主色 `#0052D9`，白底为主；品牌色只进版头/章节序号/标签/提示卡；880px 白卡 + 圆角 14/8 + PingFang 字体栈
   - 如需换品牌（其他专家复用本包时），覆盖修改 `template.html` 的 `.brand-tag` 整段 + `theme.css` 的 `--brand*`/`--hero-*` 变量 + logo 图片

4. **组装 HTML**：
   - 骨架 = `assets/template.html`，把 `<!-- === PASTE assets/theme.css HERE === -->` 整段替换为 `assets/theme.css` 全文（**必须内联**，保证单文件离线可看）
   - 每个 section 固定结构：`<h2 class="section-title"><span class="idx">01</span>标题</h2>` +（可选 `.lead`）+ 组件区
   - 序号 **连续递增**，不跳号

5. **命名与落盘** —— 文件名 `{角色}-{产出类型}-{YYYYMMDD-HHMM}.html`，写到**用户当前工作目录**（`$(pwd)`），**不要写进 skill 包内部**。

6. **自检** —— 跑 `scripts/check_html.py <文件>`，必须 0 error。

7. **交付** —— 用 `present_files` 打开预览；对话里用一段纯文本说明产物内容 + 下一步动作，**不重复 HTML 里的内容**。

## 16 条硬规则速查

完整版见 `references/design-rules.md`，这里只列结论：

0. **视觉体系 = 腾讯蓝体系**：主色 `#0052D9`，白底为主；品牌色只进**版头/章节序号/标签/提示卡**；880px 白卡 + 圆角 14/8 + PingFang 字体栈；版头腾讯蓝渐变 + 品牌行左上（logo 在左 + 品牌角色文字紧随其右、同行）+ logo 白圆角托不反白
1. 小标题一律 `h2.section-title` + 蓝色序号，**无 h3/h4 降级**；可挂右上浅灰胶囊 `.sec-note`
2. **`.lead` 是"这节最该先知道的一句话"** —— **不加固定前缀**（禁「结论：」「小结：」）；按 section 性质写判断/共性/节奏/最该避开的一条；**没有增量信息就省略整行**
3. 提示卡一律 `.callout`（浅底 + 左侧竖条，**2 色：蓝/琥珀**），选色查触发词表；引用原话用 `.quote`
4. 表格一律 `.data-table`，KV 型必须带 `<thead>`，首列强调
5. 时间轴：蓝色圆点 24px + 竖线串联，无 icon bullets（下一步建议用）
6. 通用清单用 `.plain-list`，"分类：描述"写成 `<strong>标签：</strong>描述`
7. **Icon 唯一允许场景**：banner facts 行
8. 章节标题、`.lead`、清单都**不加左侧色条**
9. 能合并的板块不拆多个标题
10. **HTML 里禁止残留 Markdown** —— `**x**`→`<strong>`，`` `x` ``→`<code>`；生成前自检 `**` / 反引号 / `](` 应为 0
11. **`.callout` 是"一段话"不是"一组要点"** —— 出现 ≥3 个并列分句或 ①②③ 时抽独立 section
12. **风险并列一律 `plain-list`** —— ≥2 条风险/红线并列时用裸 `<ul class="plain-list">`，**不套 callout**；`callout-warn` 只给孤立单条
13. **表格 vs plain-list 决策树** —— 2 列且右侧 ≥50% 是自由文本 → 用 plain-list，不用 table
14. **版头结构**：品牌行左上、同一行左对齐（logo 在左 + `金手指 · 素材经理` 紧随其右）+ title + subtitle + facts；**logo 不放右上角、无紫色 doc-type 胶囊**
15. **决策分支 / 条件枚举用 `plain-list` + `.tag-*` 字色**（`tag-ok`/`tag-warn`/`tag-bad`），**禁止用 3 条并列 callout 承载**
16. **brand-tag 完整性** —— 整段照抄 `金手指 · 素材经理`，不许简写/漏渠道后缀/换词序

## 文件包结构

```
html-report-card-suce/
├── SKILL.md                      # 本文件
├── assets/
│   ├── template.html             # HTML 骨架（含 6 种 section 示例 + 占位符）
│   └── theme.css                 # 统一样式（CSS 变量可换色）
├── references/
│   ├── design-rules.md           # 16 条硬规则详解（做/不做/示例）
│   ├── component-guide.md        # 9 个组件代码片段
│   └── adoption-guide.md         # 如何接入自己的专家团 + 常见改造点
├── scripts/
│   └── check_html.py             # 自检脚本（Markdown 残留、规则违反、结构完整性）
└── examples/
    └── 示例-项目评估报告.html      # 完整示范（覆盖全部组件）
```

## Pitfalls

- **CSS 必须内联**。用外链 `theme.css` 的话，文件发给别人就掉样式。只有 Bootstrap Icons 走 CDN（仅 banner meta 行用，断网时退化为无图标，不影响阅读）。
- **不要每个 section 硬塞 `.lead`**。罗列型/陈述型章节没有增量信息时省略整行 —— 写「以下是 5 个候选方案」这种复述标题的废话，比不写更糟。
- **别把「结论：」写成固定前缀**。要重点句，不要宣告词；宣告式元话语（"结论先行：""人话版："）本身就是一种黑话。
- **`.callout` 不是万能容器**。风险并列走 `plain-list`（规则 12），决策枚举走 `plain-list + tag`（规则 15），要点 ≥3 抽独立 section（规则 11）。三者最容易混。
- **蓝黄不能在同一 section 混排**。既有正向又有风险时拆成两个 section。
- **写产物前先确认落盘目录**是用户工作目录，不是 skill 包目录 —— 后者是只读资源，且分享时会带上他人的产物。

## Verification

生成后跑自检：
```bash
python3 scripts/check_html.py <生成的.html>
```
脚本检查：Markdown 残留（`**` / 反引号 / `](`）、`.lead` 固定前缀、序号连续性、`h3/h4` 降级、同 section 蓝黄混排、`callout` 内嵌风险列表、CSS 是否已内联。**必须 0 error 才交付。**

人工再过一眼：
- 浏览器打开是否有样式（验证 CSS 已内联）
- 只读开头每节的 `.lead`，能否串起完整判断
- 有没有哪一节的 `.lead` 是在复述标题
