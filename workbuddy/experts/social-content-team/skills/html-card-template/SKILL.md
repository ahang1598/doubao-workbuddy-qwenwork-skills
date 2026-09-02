---
name: html-card-template
description: 营销通社媒内容专家团统一 HTML 卡片渲染模板。用于把结构化交付物（规划、拆解、Brief、日历、报价、体检等）渲染为品牌一致的 HTML 卡片文件。触发条件：agent 输出规范里明确列出的交付物；正文含 ≥2 段结构化内容；用户明说"给我一份/生成一个/整理成 XX"。
---

# HTML 卡片模板 · 使用说明

## 什么时候用（判定规则）

**必须用 HTML 渲染**（满足任一）：
1. Agent 的「## 输出规范」里显式列出的交付物（如账号定位卡、爆款拆解、Brief 六要素、内容日历、报价参考、路线图、体检报告、风格 DNA 档案等）
2. 正文包含 ≥2 段结构化内容（表格、多层清单、时间轴、多要点对比、评分）
3. 用户明确说"给我一份 / 生成一个 / 整理成 XX / 出一份文档"

**不用 HTML，保持纯文本对话**：
1. 闲聊、追问、澄清（"这个能不能改一下"、"为什么这么建议"）
2. 单条问答（"抖音适合日更吗？"）——单条回答、无多层结构
3. 仿写正稿本身 / 商单文案改写后的最终稿件——用户要复制走贴到平台的成品，用 HTML 反而不便复制
4. JSON 中间接口（`style-dna-training` / `content-methodology-analysis` 里的工程管道）——**保持现状不变**，HTML 只在最终"给用户看"的那一层套壳

## 怎么用（生成 SOP）

**Step 1 — 确认触发**：对照上面判定规则，符合就往下走；不符合就纯文本回答。

**Step 2 — 拟定文件名**：`{专家花名}-{产出类型}-{YYYYMMDD}.html`
例：`启号-账号规划-20260819.html`、`包火-爆款拆解-20260819.html`、`卞现-Brief评估-20260819.html`

**Step 3 — 文件路径**：**用户当前工作目录**（默认 `$(pwd)`），不要放到专家包内部。

**Step 4 — 组装 HTML**：
- 骨架 = `assets/template.html`（复制一份，把 `<!-- === PASTE assets/theme.css HERE === -->` 替换为 `assets/theme.css` 的完整内容内联进去，保证离线可看）
- 组件参考 = `references/component-guide.md`
- 产出映射 = `references/output-mapping.md`（你是哪个专家、要出什么，查表拿组件配方）
- 视觉/结构硬规则 = `references/design-rules.md`（**16 条硬规则不能违反**）

**Step 5 — 交付**：
- 写文件到用户当前工作目录
- 用 `present_files` 打开预览面板
- 用一段纯文本简要说明产物内容 + 下一步动作（对话正文本身不重复 HTML 里的内容）

## 硬规则（违反即返工，详见 references/design-rules.md）

1. 所有小标题一律 `<h2 class="section-title">` + 序号，无 h3 降级
2. **`.lead` 是"这节最该先知道的一句话"**——**不加任何固定前缀**（禁「结论：」「小结：」）；按 section 性质写判断/共性/节奏/最该避开的一条；没有增量信息就**省略 lead** 直接上内容（灰底 `#FAFBFC`，不用品牌色）
3. 提示条一律 `.callout`，**只 2 色**（默认蓝=中性/正向，`callout-warn`=雷区/风险），选色查触发词表
4. 表格一律 `.data-table`，KV 型必须带 `<thead>` 表头
5. 时间轴精简版：Week/阶段徽章 + 目标行 + 无 icon bullets
6. 通用清单用 `.plain-list`，"分类：描述"用 `<strong>标签：</strong>描述` 格式
7. Icon 唯一允许场景：banner meta 行（Bootstrap Icons），用于并列维度区分
8. 章节标题、结论卡、清单都不加左侧色条
9. 能合并的板块不拆多个标题（关联专家并入下一步建议）
10. **HTML 里禁止残留任何 Markdown 语法**——`**加粗**` 必须写成 `<strong>加粗</strong>`，`` `代码` `` 写成 `<code>代码</code>`，生成前自检 `**`/`` ` ``/`](` 应为 0 处
11. **`.callout` 是"一段话"不是"一组要点"**——出现 ≥ 3 个并列分号句或 ①②③ 时，抽独立 section
12. **风险/红线并列一律 `plain-list`**——≥ 2 条风险/雷点/合规红线并列时直接裸 `<ul class="plain-list">`，**不套 callout**；`callout-warn` 只留给孤立单条警示
13. **表格 vs plain-list 决策树**——2 列且右侧 ≥ 50% 是自由文本 → 一律用 plain-list，不用 table
14. **Banner 4 行结构**：**brand-tag**（`营销通 · <专家职能名>`，纯白小字）+ title + subtitle + meta。**brand-tag 硬约束**：必须用专家职能名（如"内容选题专家"），**禁止用花名**（"郝选题" / "卞现" 等）。7 个专家的固定职能名见 `references/brand-tag-map.md`
15. **决策分支 / 条件枚举（If-then）用 `plain-list` + `.tag-*` 字色**（三档：`tag-ok` 绿 / `tag-warn` 橙 / `tag-bad` 红），**禁止用 3 条并列 callout 承载**——callout 是风险提示不是决策枚举
16. **brand-tag 完整性硬约束**：Banner 顶部 brand-tag 必须完整"营销通 · <职能名>"，**禁止简写**（❌ 营销通·XX / ❌ 腾讯·XX / ❌ 只写职能名）。每个专家包的 `assets/template.html` 已把自己的 brand-tag 整段**写死**，agent 直接原样复制、不许改字

## 目录结构

```
html-card-template/
├── SKILL.md                       # 本文件
├── assets/
│   ├── template.html              # HTML 骨架（含占位符）
│   └── theme.css                  # 统一样式表
├── references/
│   ├── design-rules.md            # 16 条硬规则详解
│   ├── component-guide.md         # 9 个组件代码片段
│   ├── output-mapping.md          # 6 专家产出→组件映射框架
│   └── brand-tag-map.md           # 7 专家 banner brand-tag 固定职能名映射
└── examples/
    ├── 启号-账号规划.html          # 完整产出示范（含所有组件）
    ├── 包火-爆款拆解.html          # 时间轴 + 表格 + warn callout
    └── 卞现-Brief评估.html         # KV 表 + 三档 callout
```

## 与其他技能的关系

- **`output-readability`**（团队交付把关）：呈现层触发规则在那里；本 skill 是"选定 HTML 之后怎么做"
- **`platform-playbook`**（平台知识库）：内容口径参考，不影响 HTML 样式
- **`style-dna-training` / `content-methodology-analysis`**：内部 JSON 接口保留，最终呈现给用户时套 HTML

## 维护约定

本 skill 在 7 个专家包里各有一份**完全一致**的副本（social-content-team + 6 个独立专家）。修改时必须同步 7 处。主副本以 `social-content-team/skills/html-card-template/` 为准。
