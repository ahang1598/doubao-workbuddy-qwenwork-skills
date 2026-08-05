---
name: 设计提取
name_en: "extract"
argument-hint: "输入 URL（外部模式借鉴）/ 代码仓库路径（内部模式固化）/ Figma 文件 URL 或 file-key（Figma 模式 · 需装 Figma MCP），如：https://stripe.com 或 ./apps/web 或 https://figma.com/file/abc123"
description: >
  设计系统提取（Design System Extract）。三模式：① 外部模式——薄包装 designlang CLI，从任意线上站点反向抽取完整 design tokens（颜色 / 字体 / 间距 / 圆角 / 阴影 / 动效等 19 类），产物供 /竞品拆解 / /视觉情绪板 / /设计简报 借鉴；② 内部模式——扫描自己的代码仓库（package.json / tailwind.config / components/ / 含 styled-components & emotion 的 CSS-in-JS AST 解析），把已实现的设计语言固化为 design.md；③ Figma 模式——通过 Figma MCP 从设计稿源头抽 Variables / Local Styles，作为设计师 native 入口。三种模式输出统一 schema（meta.source.type 区分），可链入下游 Brief / Board / Bench / 下一个项目 Flow Web，或作为 AI 编程（Cursor / Claude Code）的上下文锚点，也可反哺 SparkDesign 组件库。SparkDesign Diff 升级到「命名匹配 + 语义匹配」双层（规则表 + usage 推断），让 proposed_increment 真正具备判断力。

  触发关键词：抽设计系统、提取设计 token、design token 提取、design.md 生成、扒站点设计、反向工程设计、tailwind config 生成、shadcn theme 生成、Figma 抽 token、Figma variables 导出、design system extract、design language、固化设计语言、Handoff design.md、给 AI 编程的设计上下文。

  排除（反向）：设计稿走查（用 /设计走查）、实现 vs 设计源差异核查（用 /设计验收）、竞品功能 / 交互模式拆解（用 /竞品拆解，那是模式层不是 token 层）、新建设计系统组件库本身（这是 SparkDesign 的工作，本 Skill 只产 design.md）、字体 / 图像 / SVG icon set 的版权下载（红线禁止）、Figma 组件几何形状提取（本 Skill 只抽 token，不抽 Auto Layout 结构）。

description_en: >
  Design System Extraction. Tri-mode: ① External — thin wrapper around the designlang CLI; reverse-extract complete design tokens (19 categories) from any live site for /bench / /board / /brief. ② Internal — scan your own repo (package.json / tailwind.config / components/, with CSS-in-JS AST parsing for styled-components & emotion) to crystallize the implemented design language into design.md. ③ Figma — via Figma MCP, extract Variables / Local Styles straight from the design source. All three modes emit a unified schema (meta.source.type distinguishes them) consumable by /brief, /board, /bench, the next project's Flow Web, or AI coding tools (Cursor / Claude Code); proposed_increment can be fed back into SparkDesign. The SparkDesign Diff is upgraded to a two-layer match (naming + semantic via rule-table + usage inference) so proposed_increment actually carries judgment.

  Triggers when a designer says: "extract design system", "extract design tokens", "design.md", "reverse-engineer a site", "generate tailwind config from a URL", "generate shadcn theme", "extract figma variables", "crystallize our design language", "handoff design.md", "design context for my AI coding agent", "design language extraction".

  Excludes: design-file review (use /check), implementation-vs-design fidelity (use /qa), competitor flow/pattern teardown (use /bench, pattern-level not token-level), building the component library itself (SparkDesign's job), font/image/SVG icon-set downloading (red-line prohibited), Figma component geometry extraction (this Skill only extracts tokens, not Auto Layout structure).

allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - WebFetch
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [flow-web, flow-mobile, qa, check, board]   # 并集：仅内部模式实际消费；外部模式时全部可缺失。board 用于增量模式与现有 design-tokens 做 SparkDesign 语义级 Diff
  writes: extract
  schema:
    skill: string
    generated_at: string
    project_name: string
    meta:
      source:
        type: enum [external, internal, figma]
        uri: string                            # 外部=URL；内部=仓库根路径；figma=file URL 或 file-key
        captured_at: string
        tool_chain: array<string>              # 例：["designlang@x.y", "playwright/chromium"] 或 ["figma-mcp@x.y"] 或 ["babel-parser@x.y", "styled-components-visitor"]
      mode_resolved_by: enum [auto, explicit]  # 自动判别 vs --mode 显式覆盖
      ask_answers:                             # v0.5.3 新增：Step 1.5 用户答复回写
        deliverable_choice: enum [A, B, C]     # A=默认3件 / B=3件+preview / C=仅preview（警告链路断）
        confirmed_at: string
      fallback_reason: string|null             # v0.5.3 新增：触发外部模式 JS fallback 时的具体原因
      target_framework: array<string>          # ["tailwind", "shadcn", "react-theme", "w3c-tokens", "figma-vars", "css-vars"]
      internal_scan:                           # 仅内部模式填充；记录扫了哪些源
        tailwind_config_found: boolean
        theme_files_found: array<string>
        css_var_files_found: array<string>
        css_in_js_engine: enum [none, styled-components, emotion, vanilla-extract, linaria, mixed]
        css_in_js_files_parsed: number
      figma_scan:                              # 仅 figma 模式填充
        variables_collections_found: number
        local_styles_found: { fill: number, text: number, effect: number }
        components_referenced: array<string>   # 设计稿引用的组件名，供下游 Flow Web 对齐 SparkDesign
    tokens:
      color:
        - name: string                         # 命名优先采纳源 token 名；缺失则按用途归类（primary/surface/...）
          value: string                        # hex / rgb / hsl
          usage: array<string>                 # ["bg-primary", "button.solid", ...]
          role: enum [brand, semantic, neutral, accent, other]
      typography:
        - family: string
          source: enum [google, self-hosted, cdn, system]
          weights: array<number>
          scale:
            - size: string
              line_height: string
              letter_spacing: string
              usage: string
      spacing: "array<{ name, value, scale_anchor:number|null }>"
      radius: "array<{ name, value, applied_to:array<string> }>"
      shadow: "array<{ name, value, elevation:number|null }>"
      motion: "array<{ name, duration, easing, properties:array<string> }>"
      breakpoint: "array<{ name, value }>"
      z_index: "array<{ name, value:number, layer }>"
      icon_set: "{ count:number, dedup_method, palette:array<string> }"
      gradient: "array<{ name, type, stops:array<string> }>"
      state: "array<{ name, delta:object }>"   # hover/focus/active 仅在 captured 时填充
    sparkdesign_diff:                          # 内部 / Figma 模式产出；外部模式为 null
      match_method: enum [naming-only, naming-plus-semantic]   # v0.5.2 升级后默认 naming-plus-semantic
      matched: "array<{ token_name, equals_or_close: enum[equal,close] }>"           # 第一层：命名 + 值匹配
      semantic_match:                          # 第二层（v0.5.2 新增）：命名不同但语义等价
        - project_token: string
          sparkdesign_token: string
          evidence: enum [rule-table, usage-inference, both]
          confidence: enum [high, medium, low]
          rationale: string                    # 例："二者都用在 Card.background；规则表 surface-1 ≈ background-elevated"
      project_specific: "array<{ token_name, value, reason }>"
      proposed_increment:
        - token_name: string
          value: string
          rationale: string
          risk: enum [low, medium, high]      # 反哺 SparkDesign 的风险评估
          usage_count: number                  # 在项目里被多少处复用，决定收录优先级
    artifacts:                                 # 实际落盘的产物文件清单
      design_md: string                        # 19 段 AI-optimized markdown 路径
      tokens_json: string                      # W3C Design Tokens 路径
      tailwind_config: string|null
      shadcn_theme: string|null
      figma_vars: string|null
      preview_html: string|null
    handoff_hint: string                       # 给 .cursorrules / CLAUDE.md / Qoderwork 的引用片段
    fallback_applied: array<string>            # 触发了哪些 fallback（如 "no-tailwind-config"）
---

# 设计提取（Extract）

> 你是设计系统提取专家。本 Skill 三模式工作：**外部**抽别人的（线上站点 → designlang）/ **内部**固化自己的（代码仓库 → 含 CSS-in-JS AST 解析）/ **Figma** 直抽源头（设计稿 → Figma MCP）。三种模式产出**统一 schema** 的 design.md + tokens，可被下游 Brief / Board / Bench 或下一个项目的 Flow Web 链式消费，也可作为 AI 编程（Cursor / Claude Code）的设计上下文锚点。SparkDesign Diff 默认走「命名 + 语义」双层匹配，proposed_increment 自带 usage 计数与风险评级。

## 边界对照表

不要把以下职责揽进来，遇到时引导用户去对应 Skill：

| 易混淆需求 | 应该去 | 与 Extract 的区别 |
| --- | --- | --- |
| "看看这个竞品的导航怎么设计的" | `/竞品拆解`（Bench） | Bench 看交互/功能模式，Extract 只抽 token 级数据 |
| "我设计稿自己有逻辑问题想走查" | `/设计走查`（Check） | Check 审设计稿自身，Extract 不审 |
| "前端实现跟我设计稿差多少" | `/设计验收`（QA） | QA 校还原度偏差，Extract 把实现固化回文档 |
| "我想做一个新组件库" | SparkDesign 项目本体 | Extract 只产 design.md，不写组件代码 |
| "下载这个站点的字体 / 图标" | 不做（红线） | 抽 token 元数据 ≠ 下载版权资源 |
| "我想要 PM 视角的产品分析" | PM 套件 `/竞品分析` | PM 套件分析价值主张，Extract 抽视觉系统 |
| "把这个站的全部代码 clone 下来" | designlang `clone` 子命令 + 你自己评估 | 本 Skill 不主动 clone，仅在外部模式提示 designlang 有此能力 |
| "我要 Figma 组件的几何 / Auto Layout 结构" | Figma 官方 API + 你自己实现 | 本 Skill 的 Figma 模式只抽 token（Variables / Local Styles），不抽组件几何 |
| "我要 designlang 的 watch / sync / score / diff" | 直接走 `npx designlang <subcommand>` | 本 Skill 不包装这些运维向命令，原生 CLI 更直接 |

**与 designlang CLI 的关系**：本 Skill 是 designlang 在 SparkSkillsHub 链路里的**薄包装层**——加四件事：① 模式识别（外部 / 内部 / Figma 三选一）；② 统一 schema（三种产出对齐）；③ SparkDesign 适配 diff（命名 + 语义双层）；④ Figma MCP / CSS-in-JS AST 这两个 designlang 不覆盖的源。如果你只想"抽个 Stripe 的 token 看看"，直接 `npx designlang https://stripe.com` 比走本 Skill 快。本 Skill 的价值在**链路接入 + 多源对齐**。

**与 Figma MCP 的关系**：本 Skill 不内置 Figma API 调用，需要用户**预先安装 Figma 官方 MCP 或社区方案**并在 Cursor / Claude Code / Qoderwork 里配置 PAT。本 Skill 通过 MCP 调用 `get_variables` / `get_local_styles` 等工具，承担 orchestration 与 schema 归一化职责。Figma MCP 未安装时 Figma 模式直接 fallback 到"请用户手动导出 Figma Variables JSON 后投喂"路径。

---

## Chain Context

### 上游读取（Step 0 执行 · 内部 / Figma 模式实际消费，外部模式跳过）

`reads` 是并集声明，**外部模式时全部可缺失**。内部 / Figma 模式按以下顺序尝试：

| 上游 Skill | 字段 | 用途 | 内部模式 | Figma 模式 |
| --- | --- | --- | --- | --- |
| `flow-web` / `flow-mobile` | components_used / sparkdesign_components | 列出实现 / 设计稿里调用了哪些 SparkDesign 组件，作为 sparkdesign_diff.matched 与 semantic_match 的基线 | ✓ | ✓ |
| `qa` | deviations | 已知"实现 vs 设计源"的 token 偏差，提取时标注为 `project_specific.reason="qa-deviation"` | ✓ | — |
| `check` | findings (resolved=true) | 走查通过的设计决策，加权信任其 token 值 | ✓ | ✓ |
| `board` | color / typography / spacing / radius / component | 项目「应有的」设计源头 token——抽取后与本次 extract 结果做语义级 SparkDesign Diff，输出 `expected_vs_extracted` 偏差列表（实现是否守住情绪板里固化的方向） | ✓ | ✓ |

读不到时降级到"纯扫码仓库 / 纯 Figma 文件"模式，并在 `fallback_applied` 里标 `no-upstream-chain`。

### 下游输出（写入 spark-output/context/extract.json + 会话内 marker）

写出 `extract.json` 后，下游可以这样消费：

- `/设计简报`（Brief）—— 外部模式产物作为"参考方向 token 库"喂给设计标准段落；内部模式产物作为"已有设计语言基线"
- `/视觉情绪板`（Board）—— 反向场景：把外部站点的 token 提取结果作为情绪板候选方案的 seed；正向场景已通过本 Skill `chain.reads: board` 实现增量 Diff
- `/竞品拆解`（Bench）—— 多个外部 extract 的产物拼成对比矩阵
- `/Web页面设计` `/mobile页面设计`（Flow Web/Mobile）—— 内部模式的 design.md 作为 SparkDesign 组件调用前的设计语言锚
- SparkDesign 组件库本体 —— `sparkdesign_diff.proposed_increment` 进入收录评审

### 字段流向下游 schema 引用

下游 Skill 引用本产出时，建议路径：

```
extract.tokens.color[*].name → brief.design_standard.color_palette
extract.tokens.typography[0].scale → brief.design_standard.type_scale
extract.sparkdesign_diff.proposed_increment → SparkDesign issue / PR 提案模板
extract.handoff_hint → .cursorrules / CLAUDE.md 的"设计上下文"段落
extract.artifacts.design_md → 任何 AI agent 的 context window 输入
```

---

## 触发条件

- 输入含 `figma.com/file/` / `figma.com/design/` / 形如 `^[a-zA-Z0-9]{22,}$` 的裸 file-key → **Figma 模式**默认触发
- 输入含 URL（其他 https://...）且未明确说"分析交互" / "拆功能" → **外部模式**默认触发
- 输入为路径 / 仓库根 / `.` / 空 → **内部模式**默认触发
- 显式 `--mode external|internal|figma` 参数 → 覆盖自动判别（`mode_resolved_by=explicit`）
- 关键词触发：上文 description 触发关键词集合（"figma 抽 token" / "figma variables 导出" 强信号触发 Figma 模式）
- **上游驱动触发（v0.5.2 新增）**：会话中检测到 `spark-output/context/flow-web.json` 或 `flow-mobile.json` 存在且 `generated_at` 距今 < 7 天 → **主动询问**用户：
  ```
  检测到刚跑完 /Web页面设计（或 /mobile页面设计），是否顺手抽一份 design.md？
  常见用途：
    A. 给 Cursor / Claude Code 继续 vibe coding 更多页面（design.md 进 .cursorrules）
    B. 反哺 SparkDesign 主仓（看 sparkdesign_diff 的 proposed_increment 第 4 桶）
    C. 准备进 /写PRD（让 PRD 设计资产段引用机读 tokens）
    D. 暂不需要（一次性页面 / token 还在大改）
  ```
  用户选 A/B/C → 默认走内部模式 + 对应 target 子集；用户选 D 不强推。**仅在确实检测到上游 context 时触发，不要凭空推销。**

**边界提示**：
- 用户说"分析 Stripe 的 pricing 页交互" → 这是 Bench 的活，不是 Extract；Step 1 主动询问区分
- 用户给 Figma URL 但说"我要组件几何形状" → 提示本 Skill 只抽 token，几何请走 Figma 官方 API

---

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **三模式统一 schema**：external designlang / internal CSS-in-JS AST / figma MCP 完整方法论
- **链式上下文双通道**：写入 `spark-output/context/extract.json` + 会话内 marker block，下游 PRD / Flow Web/Mobile 可直接读取
- **SparkDesign 语义级 Diff**：命名 + 语义双层四桶分类（matched / semantic_match / project_specific / proposed_increment），36 条 alias 规则表本地完成
- **internal 模式 CSS-in-JS AST 解析**：覆盖 styled-components / emotion，babel-parser 本地解析

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | 执行流程 Step 1（模式识别） | figma 模式通过 Figma MCP 调 get_variables / get_local_styles 抽 token（v0.5.2 已交付） | 未装 Figma MCP 时降级到手动 export Variables JSON 投喂，schema 完全一致 |
| **GitHub** | 执行流程（internal 模式扩展） | internal 模式扩展到读远程仓库（不只本地 path），含 tailwind.config / theme 文件 / CSS-in-JS 全套抽取 | 未装时仅扫本地 path 或 mounted 仓库目录 |

**接入触发**：用户首次调用 `/设计提取` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 现有 `mode_resolved_by` 字段值集新增 `figma_mcp`（已设计于 v0.5.2）
- 启用 **GitHub** → `chain.schema` 现有 `source` 字段新增 `github_repo_url` 子项作为远程仓库标识

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## 执行流程

### Step 1 · 模式识别与意图确认

1. 解析输入：
   - 含 `figma.com/(file|design)/` 或 22+ 位 file-key → 候选 **Figma 模式**
   - 是其他 URL → 候选 **外部模式**
   - 是路径 / 空 / `.` → 候选 **内部模式**
   - 同时有多者 → 报错请用户拆成多次调用（多产物会污染 chain context）
2. 关键词二次校验：如果用户说了"交互 / 流程 / 信息架构 / 功能" → **停**，引导去 `/竞品拆解`
3. 如果 `--mode` 显式指定，跳过自动判别，记 `mode_resolved_by=explicit`
4. 询问 `target_framework`（默认全部输出，可裁剪为 `tailwind` / `shadcn` / `react-theme` / `w3c-tokens` / `figma-vars` 任意子集）

### Step 1.5 · 产物范围确认（v0.5.3 新增 · 强制 ASK，不可跳过）

⚠️ **本步骤必须执行，且必须用结构化菜单输出**——不允许口语化「我先确认几个问题」一笔带过。目的是让用户**知情选择**产物形态，避免默认只出 HTML 导致链路 context 丢失。

输出格式（严格按此模板，A/B/C 三选一）：

```
🔍 source.type: [external|internal|figma]
🔍 target: <URL / repo-path / figma-file-key>
🔍 sparkdesign-context: [detected|absent]

我将提取 <target> 的设计规范，产物分两层：

默认核心产物（3 件，不可省略 —— 否则链路断开下游 Skill 无法读取）：
  ✅ design.md            机读 token spec（19 段 markdown，下游 /设计验收 /写PRD /Web页面设计 必读）
  ✅ tokens/*.json        W3C tokens + tailwind/shadcn theme（工程可直接 cp 使用）
  ✅ extract.json         链路 context（写入 spark-output/context/，标记 source.type 与 fallback_applied）

可选加件：
  ☐ preview.html         视觉预览页（适合分享给团队 / 非工程角色 review）

请选择：
  A. 默认 3 件                                ← 推荐
  B. 默认 3 件 + preview.html
  C. ⚠️ 只要 preview.html
     （链路 context 不生成；下游 Brief / Flow Web / QA 全部读不到本次 extract；
      等同于把 Extract 降级为 Chart 的活，不推荐）
```

**强制规则**：
- 三个 emoji 首行（source.type / target / sparkdesign-context）一行不能缺，缺则停下补齐
- C 选项必须带括号警告，**不允许简化为「只要 HTML」一个词**
- 用户答案必须回写 `extract.json.meta.ask_answers = { deliverable_choice: "A|B|C", confirmed_at: timestamp }`，方便复盘
- 用户主动只勾 C 时，Step 8 仍必须打 marker block + 写最小 `extract.json`（仅 meta 段），让链路至少知道「这里跑过 extract，但用户选择不落机读产物」——彻底空跑会让 Retro 无法回溯

### Step 2 · 依赖检查与 Fallback 决策

**外部模式**：
- 检查 `node --version` ≥ 18 → 否则提示安装并提供 fallback
- 检查 `npx designlang --version` 能否解析 → 否则提示 `npm install -g designlang` 或走 fallback
- 检查 `npx playwright install --dry-run chromium` → 缺失时引导安装
- **Fallback**：如果用户拒绝安装依赖，降级到"请用户手动贴 3-5 张关键页面截图 + 主色 hex + 字体名"，仍走 Step 4-6 但 `tokens.*` 大部分字段为 `null`，`fallback_applied=["no-designlang"]`

**内部模式**：

第一轮 · 配置层扫描（v0.6 已有）：
- 扫 `package.json` 取 framework / UI 库（react / vue / next / tailwind / antd / shadcn / mui / chakra ...）
- 找 `tailwind.config.{js,ts,mjs}` → 优先级最高的 token 源
- 找 `components.json`（shadcn 标记）→ 触发 shadcn-theme 提取
- 找 `styles/`、`src/styles/`、`*.css`、`*.scss` → CSS 变量 / 主题变量
- 找 `theme.{js,ts}` / `tokens.{js,ts}` → 主题对象提取

第二轮 · CSS-in-JS 引擎识别（v0.5.2 新增）：
- 扫 `package.json#dependencies` 检测：`styled-components` / `@emotion/styled` / `@vanilla-extract/css` / `@linaria/core` / `@stitches/react`
- 记录到 `meta.internal_scan.css_in_js_engine`，无则填 `none`
- 若检测到 → 第三轮 AST 解析；若为 `none` → 跳过

第三轮 · CSS-in-JS AST 解析（v0.5.2 新增，仅 styled-components / emotion，其他引擎留 v0.5.3+）：
- 使用 `@babel/parser` 解析所有 `.tsx` / `.ts` / `.jsx` / `.js` 文件
- visitor 抓三类节点：
  - `TaggedTemplateExpression` where `tag.object.name === 'styled'` or `tag.callee.name === 'styled'` （styled-components 标记模板）
  - `CallExpression` where `callee.name === 'css'` and imported from `@emotion/*` （emotion css() 调用）
  - `JSXAttribute` where `name.name === 'css'` （emotion JSX css prop）
- 从模板字符串字面值（quasi.value.raw）提取：
  - `#xxx` / `rgb(...)` / `hsl(...)` / `rgba(...)` / `hsla(...)` → color
  - `\d+(px|rem|em|%)` 出现在 `padding/margin/gap/width/height` 上下文 → spacing
  - `\d+(px|rem|%)` 出现在 `border-radius` 上下文 → radius
  - `\d+px \d+px ...` 形式 → shadow
  - `transition: ... \d+(ms|s)` → motion
- 忽略 `${...}` 插值（v0.5.2 不做 dataflow 分析，模板插值的动态 token 推 v0.5.3）
- 记录 `meta.internal_scan.css_in_js_files_parsed` = 实际解析的文件数

**Fallback 级联**：
- 配置层 + CSS-in-JS 都空 → 提示用户"项目里没有显式的 design token 文件 / CSS-in-JS 也没抓到，要不要授权我用 grep 扫源码里出现频次最高的颜色 / px 值？"，进入纯统计模式，`fallback_applied=["no-config-source"]`
- AST 解析报错（语法错 / babel 不支持的语法）→ 标记单个文件失败但不中断整体，最终 `fallback_applied` 含 `partial-ast-parse-failure:N-files`

**Figma 模式（v0.5.2 新增）**：
- 检查会话里是否已挂载 Figma MCP（工具列表里有 `mcp__figma__*` 前缀的工具）
- 是 → 调 `mcp__figma__get_file` 取 file meta，`mcp__figma__get_variables` 取 Variables 集合，`mcp__figma__get_local_styles` 取 fill / text / effect styles
- 否 → **Fallback**：提示用户"未检测到 Figma MCP。请二选一：① 在你的 Cursor / Claude Code / Qoderwork 里安装 Figma MCP（推荐）；② 在 Figma 里手动 export Variables 为 JSON 投喂给我"，`fallback_applied=["no-figma-mcp"]`
- PAT / token 永远由用户在 MCP 配置里管，本 Skill 不接触

### Step 3 · 抽取执行

**外部模式（调 designlang）**：

```bash
npx designlang <url> \
  --out spark-output/extract/<slug>/ \
  --name <slug> \
  --wait 1500 \           # SPA 默认等 1.5s
  --depth ${depth:-0} \   # 多页时由用户指定，默认 0
  --interactions \        # v0.5.2 起，外部模式默认开（除非用户显式 --no-interactions）
  ${dark:+--dark} \
  ${responsive:+--responsive}
```

`--cookie` / `--header` 只在用户主动提供时附带，**任何 auth 凭据严禁写入 extract.json 或 design.md 产物**（红线，见下方）。

**内部模式（自研扫描 + AST 解析）**：

按发现顺序合并 token，后发现的同名 token 不覆盖前者，优先级：
**tailwind.config > theme.ts/tokens.ts > CSS 变量 > CSS-in-JS AST 提取（v0.5.2）> 源码 grep 统计**

每条 token 记录 `usage` 数组（出现过的文件路径），便于下游回溯，也是 Step 5 语义匹配的关键证据。

**state 抓取**：v0.5.2 起内部模式默认尝试抓 hover/focus/active 状态——扫所有 `:hover` / `:focus` / `:active` CSS 选择器 + CSS-in-JS 里的 `&:hover` 模板分支，归到 `tokens.state[]`。

**Figma 模式（v0.5.2 新增）**：

调用 Figma MCP 工具序列：
1. `mcp__figma__get_file(file_key)` → 拿 file metadata + page list
2. `mcp__figma__get_variables(file_key)` → 拿所有 Variables 集合（这是最优先源，直接映射 schema）
3. `mcp__figma__get_local_styles(file_key)` → 拿 fill / text / effect styles（Variables 缺失时的 fallback 源）
4. 从 styles 命名规约推断 role（如 `Color/Brand/Primary` → role=brand；`Effect/Elevation/2` → shadow.elevation=2）
5. 从 `mcp__figma__get_published_components(file_key)`（若可用）拿组件名 → 写入 `meta.figma_scan.components_referenced`，供下游对齐 SparkDesign

**不抽**：
- Frame 截图（不变图床）
- Auto Layout 几何参数（不是 token）
- 私密 / 草稿 page 内容（仅抽 published page，与 styles 同步）

### Step 4 · Token 归一化

不论模式，统一归到 schema 里 11 类（color / typography / spacing / radius / shadow / motion / breakpoint / z_index / icon_set / gradient / state）。

约定：
- color：保留源命名，缺失则按 role 命名（brand / semantic.success / neutral.200 ...）
- spacing：尝试反推一个 anchor（常见 4 / 8 / 10），把每个值标 `scale_anchor`
- radius / shadow：保留源命名 + `applied_to` 反向索引
- state：仅在 `--interactions` 模式或源码里显式抓到 hover/focus/active 才填充

### Step 5 · SparkDesign Diff（内部 / Figma 模式 · v0.5.2 双层匹配）

读取 SparkDesign 的 token 清单（路径在用户环境里通常是 `node_modules/@spark-design/tokens` 或团队约定路径，找不到时跳过并标 `fallback_applied=["no-sparkdesign-baseline"]`，整段降级为仅命名匹配 `match_method=naming-only`）。

**v0.5.2 升级**：从「命名匹配」升级为「命名 + 语义」**双层四桶**，`match_method=naming-plus-semantic`：

**第一层 · 命名匹配（v0.6 已有）**
- `matched`：项目 token 名与 SparkDesign 重名且值相同（`equal`）或视觉接近（`close`，色差 ΔE < 3、px 差 ≤ 2）

**第二层 · 语义匹配（v0.5.2 新增）** — 命名不同但用途等价，进 `semantic_match` 桶。判定走两条证据链，**至少满足一条**才进桶：

证据链 A · 规则表（`semantic-rules.json`）：
- 维护在 `5-Deliver/Extract/references/semantic-rules.json`
- 格式：`{ "sparkdesign-token-name": ["alias-1", "alias-2", ...] }`
- 示例：
  ```json
  {
    "color.background.elevated": ["surface-1", "card-bg", "panel-bg"],
    "color.text.primary": ["text-default", "fg-primary", "foreground"],
    "spacing.md": ["space-4", "spacing-medium", "gap-base"],
    "shadow.elevation.1": ["shadow-sm", "card-shadow", "subtle-shadow"]
  }
  ```
- 项目 token 命中任一 alias → `evidence` 字段含 `rule-table`
- 规则表是开放式的，v0.5.2 给一个初始版本，团队可逐步扩

证据链 B · usage 推断：
- 比较项目 token 与 SparkDesign token 的 `applied_to` / `usage` 集合
- 若交集 ≥ 2 个相同组件位（如都用在 `Card.background` + `Modal.background`） → `evidence` 字段含 `usage-inference`
- 单个组件位重合不算，避免误判

**confidence 评级**：
- `high`：两条证据都满足 → confidence=high
- `medium`：单条证据，且 token 值视觉接近（ΔE < 5 / px 差 ≤ 4） → confidence=medium
- `low`：单条证据，且 token 值差异较大 → confidence=low，但仍然进桶供人复核

**第三桶 · project_specific**：
- 命名 + 语义双层都没匹配上，且**确有合理理由**（业务色 / 临时活动色 / 项目特有视觉策略） → 留在项目里
- 必须填 `reason` 字段（"双 11 活动专用" / "qa-deviation" / "品牌特殊处理"）

**第四桶 · proposed_increment**：
- 命名 + 语义双层都没匹配上，且**通用性 ≥ 中、usage_count ≥ 2** → 进 proposed_increment
- 必填 `rationale`（为什么值得收）+ `risk`（low = 直接收 / medium = 评审 / high = 不建议收）+ `usage_count`（在项目里被多少处复用）
- usage_count 直接影响收录优先级，proposed_increment 数组按 usage_count 倒序

**红线**：
- proposed_increment 永远是**建议**，不主动覆盖 SparkDesign 已有 token
- semantic_match 不等于"可以删掉项目 token，统一用 SparkDesign 的"——只是标记等价关系，是否替换由设计师 / 架构师人工决定（避免破坏既有调用）
- 规则表里的 alias **不引入 LLM 判等价**（避免引入推理成本与不可复现性）；想加新 alias 必须人工 PR 到 `semantic-rules.json`

### Step 6 · 多 Target 产物生成

按用户 Step 1 选定的 `target_framework` 子集，生成对应文件，全部写入 `spark-output/extract/<slug>/`：

| target | 产物 | 备注 |
| --- | --- | --- |
| `tailwind` | `<slug>-tailwind.config.js` | 外部模式直接用 designlang 输出；内部模式从 schema 反向生成 |
| `shadcn` | `<slug>-shadcn-theme.css` | HSL 变量格式 |
| `react-theme` | `<slug>-theme.js` | 通用 React/CSS-in-JS theme 对象 |
| `w3c-tokens` | `<slug>-design-tokens.json` | W3C Design Tokens 格式 |
| `figma-vars` | `<slug>-figma-variables.json` | 含 light + dark（若抓到） |
| `css-vars` | `<slug>-variables.css` | CSS 自定义属性 |
| 始终生成 | `<slug>-design-language.md` | 19 段 AI-optimized markdown，**chain 的核心产物** |
| 始终生成 | `<slug>-preview.html` | 视觉报告（外部模式由 designlang 出；内部模式自渲染） |

### Step 7 · Handoff Hint 生成

> **术语区分**：本步生成的是写入 `extract.handoff_hint` 字段的「**给下游 AI 编程工具的引用片段**」（用户复制到 `.cursorrules` / `CLAUDE.md` 用），与本 Skill 末尾的「**Handoff 提示（必输出）**」（给当前用户的下一步 Skill 推荐）是**两件不同的事**，名字撞车但用途完全分开。

为下游 AI 编程工具生成一段可直接粘贴的引用片段，写入 `extract.handoff_hint`：

```
# 设计上下文
本项目的设计语言已由 /extract 抽取，参考：
- 完整 design.md： spark-output/extract/<slug>/<slug>-design-language.md
- Token JSON：     spark-output/extract/<slug>/<slug>-design-tokens.json
- Tailwind 配置：  spark-output/extract/<slug>/<slug>-tailwind.config.js

生成 UI 组件时，所有 color / spacing / radius / shadow 必须从上述 token 中选取，不得自创。
SparkDesign 已有组件优先复用，sparkdesign_diff.matched 给出对齐表。
```

提示用户把这段贴进 `.cursorrules` / `CLAUDE.md` / Qoderwork 项目说明。

### Step 8 · 写出 chain context

按 schema 序列化为 `spark-output/context/extract.json` + 会话内 `<!-- spark-context:extract -->` marker block。

---

### 更新链路面板（必做，失败不阻断）

> **协议依据**：chain-protocol.md §九「面板自动生成约定」。本步在 Handoff 之前执行；**告知用户的提示必须作为独立段落输出，禁止折叠进 Handoff 末尾、禁止静默跳过**。

1. **找模板**：定位 `_shared/dashboard-template.html`（依次：相对套件根 → `glob dashboard-template.html` 搜套件安装目录 → 三轮都失败时，**用独立段落醒目告知用户**：`⚠️ 链路面板模板未找到（套件安装可能不完整，建议重装）。本 Skill 已正常完成，下游链路不受影响。` 然后跳过本步、继续 Handoff，**不阻断 Skill 完成**）。
2. **聚合 STATE**：扫 `spark-output/context/*.json`，聚合为 `{"project":"<brief.project_name 或 frame.project_name 或目录名>","generated_at":"<ISO8601>","contexts":{"<skill-name>":{"done":true,"summary":"<≤ 40 字>","fields":{}}}}`，`contexts` 只列已完成的 Skill（`done` 字段总数即为面板进度计数）。
3. **克隆模板**到 `spark-output/dashboard.html`（覆盖），用正则 `/\/\*__SPARK_STATE_INJECT__\*\/null/` 替换为 `/*__SPARK_STATE_INJECT__*/<JSON.stringify(STATE)>`。
4. **独立段落告知用户**（强提示，单独成段，与 Handoff 之间空一行；根据 `Object.keys(STATE.contexts).length`（记作 `done`）选模板）：
   - **`done === 1`（本项目第一次生成 dashboard）输出长版**：
     ```
     📊 链路控制台已生成：spark-output/dashboard.html（双击在浏览器打开）

     这是本套件给你的「设计全链进度看板」——5 个阶段 × 27 个 Skill 节点，亮起的代表已完成的步骤，灰色的是后续可调用的节点。每跑完一个 Skill 都会自动更新，建议钉在浏览器一个标签页里随时回看，能看清「现在在哪一步、下游还差什么、链路是否健康」。
     ```
   - **`done > 1`（后续更新）输出短版**：
     ```
     📊 链路面板已更新 · 进度 [done]/27 · spark-output/dashboard.html
     ```
5. **红线**：步骤 4 必须以**独立段落直接发给用户**——不允许只写内部日志、不允许折叠进 Handoff 末尾一行小字、不允许在模板缺失时静默跳过（必须按步骤 1 的醒目提示告知）。

---

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="extract"].next_hint` 读取。

**首行模板**：`✅ 设计提取 已完成，三模式抽取 19 类 design tokens + SparkDesign Diff。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/retro`
- **优先理由**：Tokens / design language 已落地，进 Retro 做闭环复盘把工具链产出的发现并入经验沉淀。
- **alternatives**：`/qa` (用 Extract 的 SparkDesign diff 做实现侧二次核查)
- **emoji**：🔧

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## 输出模板

### Markdown 报告（产物 `<slug>-design-language.md`，19 段，沿用 designlang 结构）

```markdown
# <项目名/站点名> · Design Language
> Source: <external|internal> · <uri> · Captured at <timestamp>
> Tool chain: designlang vX.Y / playwright chromium
> Generated by SparkSkillsHub /extract

## 1. Color Palette
| Name | Value | Role | Usage |
| --- | --- | --- | --- |
| primary | #5E6AD2 | brand | button.solid, link.default |
| ... | | | |

## 2. Typography
- Family: Inter (Google), system-ui fallback
- Weights: 400, 500, 600, 700
- Scale: 11/16, 13/20, 15/24, ...

## 3. Spacing
Anchor: 4px. Used: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64

## 4. Border Radii
sm 4px (input/badge), md 6px (button), lg 8px (card), full 9999px (avatar)

## 5. Shadows
card / dropdown / modal —— with HSL value, elevation 1-3

## 6 ~ 19. ...
（动效 / 断点 / 组件模式 / 布局系统 / 响应式 / 交互态 / 可访问性 / 渐变 / Z-Index /
 SVG 图标 / 字体源 / 图像样式 / Quick Start 片段）

## SparkDesign Diff（内部 / Figma 模式 · match_method = naming-plus-semantic）

### Matched · 命名 + 值 (24)
- color.primary == @spark/tokens.color.brand.primary ✓
- spacing.4 ≈ @spark/tokens.space.4 (ΔE = 0) ✓
...

### Semantic Match · 命名不同语义等价 (8)
| 项目 token | SparkDesign token | 证据 | 置信度 | 说明 |
| --- | --- | --- | --- | --- |
| surface-1 | color.background.elevated | rule-table + usage-inference | high | 二者都用在 Card.background + Modal.background；规则表收录别名 |
| text-default | color.text.primary | rule-table | high | 规则表别名命中 |
| space-4 | spacing.md | rule-table | medium | 命名差异但视觉接近 (4px == 4px) |
| card-shadow | shadow.elevation.1 | usage-inference | low | usage 重合但值差较大，请人工复核 |
...

### Project-specific (3)
- color.campaign-orange #FF6B35 —— 双 11 活动专用，不建议反哺
- spacing.gutter-72 —— qa-deviation 标记，临时实现差异
...

### Proposed Increment (5) · 按 usage_count 倒序
- ⚪ low risk · usage_count=8: shadow.subtle-outline-blue —— 已在 8 个组件复用，强烈建议收
- ⚪ low risk · usage_count=5: radius.pill-extra —— 5 处使用，建议收
- 🟡 medium risk · usage_count=2: motion.spring-bounce —— 仅 2 处使用，建议评审
- 🔴 high risk · usage_count=1: color.gradient-aurora —— 高度品牌化 + 单点使用，不建议收
```

### JSON Schema

见上方 frontmatter `chain.schema`。生成时按 schema 顺序写字段，缺失字段写 `null`（不是省略），便于下游解析稳定。

---

## 质量标准

至少满足以下 10 条（v0.5.3 新增 2 条）：

1. **模式识别正确率 100%**：URL / Figma URL / 路径输入必各自正确判别，歧义输入必显式询问，无静默误判
2. **Schema 完整性**：`tokens.*` 11 类全部存在（缺失项填 `null` 而非省略）；`meta.internal_scan` / `meta.figma_scan` 按模式至少填一个，下游解析无字段缺失风险
3. **产物可消费**：tailwind.config.js / shadcn-theme.css 必须语法合法、可直接 `cp` 进项目使用（不能输出半成品）
4. **SparkDesign Diff 四桶必到位**（内部 / Figma 模式 · v0.5.2）：matched / semantic_match / project_specific / proposed_increment 不可合并或省略；proposed_increment 必带 `risk` + `rationale` + `usage_count` 三字段
5. **semantic_match 证据可追溯**（v0.5.2 新增）：每条 semantic_match 必须有 `evidence` 字段说明是 rule-table / usage-inference / both，且 confidence 评级必须客观（high 必须双证据满足）
6. **Handoff Hint 可粘贴**：handoff_hint 字段是完整的 markdown 片段，复制即用，不含占位符
7. **Fallback 标记完整**：任何降级路径都必须写入 `fallback_applied` 数组（如 `no-figma-mcp` / `no-sparkdesign-baseline` / `partial-ast-parse-failure:3-files`），下游可识别"这份 extract 是否完整"
8. **CSS-in-JS AST 解析失败不中断**（v0.5.2 新增）：单文件 babel parse 失败时跳过该文件并记到 `fallback_applied`，不能让整个内部模式抽取中断
9. **Step 1.5 产物范围 ASK 必须执行**（v0.5.3 新增）：必须输出 A/B/C 三选一结构化菜单 + 三行 emoji 首行声明，C 选项必须带「链路断开」警告。`extract.json.meta.ask_answers.deliverable_choice` 字段必填，缺失即视为不合规
10. **外部模式必须走 designlang CLI**（v0.5.3 新增）：默认路径必须是 `npx designlang extract`；浏览器 JS computed style 抓取仅限红线 10 描述的 fallback 场景，且必须显式标 `fallback_applied=["browser-js-fallback"]` + `meta.fallback_reason` 填写原因

---

## 红线规则

绝对不可触碰，违反需立刻停止并告知用户（v0.5.2 新增 3 条）：

1. **不下载版权资源**：字体文件 / 图像 / SVG icon set 即使技术上可抓也不抓，只记录 source（"Google Fonts: Inter"）。需要下载请用户自行处理版权
2. **不写入 auth 凭据**：`--cookie` / `--header` / Figma PAT 仅作为 designlang / Figma MCP 运行参数，**产物里（design.md / tokens.json / extract.json / handoff_hint）严禁出现** cookie / token / authorization / PAT 字符串
3. **不覆盖 SparkDesign token**：内部 / Figma 模式的 `proposed_increment` 永远是**建议**态，不主动改 SparkDesign 源；任何对组件库本体的修改走 SparkDesign 自身的评审流程
4. **不主动 clone 整站**：designlang 有 `clone` 子命令能生成 Next.js starter，本 Skill 不调它，仅在 Quick Start 章节提示用户存在此能力（涉及版权与法律灰区）
5. **不抹平 project_specific**：项目里的业务专用 token（活动色 / 品牌特殊处理）必须留在 project_specific 桶，不能为了"对齐 SparkDesign"擅自删除或改名
6. **不静默吃错**：designlang / Figma MCP / babel-parser 报错 / 仓库扫不到任何 token / 网络失败 —— 必须明确告知用户原因，不能用空产物糊弄
7. **不引 LLM 判语义等价**（v0.5.2 新增）：语义匹配只能走规则表 + usage 推断两条证据链，**禁止**调 Claude/Haiku 让模型"判断这两个 token 是不是一回事"——破坏可复现性，也引入推理成本
8. **不抽 Figma 私密 / 草稿 page**（v0.5.2 新增）：仅抽 published page 内容；草稿 / 个人 page 即使技术上能拿到也不抽（避免泄露未公开的设计方向）
9. **不分析 CSS-in-JS 模板插值**（v0.5.2 新增）：`styled.div\`color: ${getColor()}\`` 这类动态插值不做 dataflow 分析，只抽字面值；强行猜插值结果会导致产物失真
10. **外部模式禁止用浏览器 JS computed style 替代 designlang CLI**（v0.5.3 新增）：外部模式底层**必须**调 `npx designlang extract <url> --interactions`。浏览器 puppeteer / `getComputedStyle` 手工抓取**严禁**作为默认路径——会丢 motion / icon / gradient / breakpoint / z-index 等类别，且不可复现。仅在以下情况允许 fallback 到 JS 抓取：① CLI 不可安装（断网 / 防火墙）；② 站点显式封禁 designlang UA。两种情况必须在 `meta.fallback_reason` 显式标注且降级为「轻量版 extract」标签，不能伪装成完整产物
11. **产物路径强约束**（v0.5.3 新增）：所有产物**必须**落在 `<project-root>/spark-output/extract/<slug>/` 下（`extract.json` 落 `<project-root>/spark-output/context/extract.json`）。**严禁**写到 Desktop / Documents 根目录 / 用户家目录 / 任何 `spark-output/` 之外的位置——一旦散落到其他目录，链路 context 立即失效，下游所有 Skill 都读不到本次产出。如果 project-root 检测不到（用户在 `$HOME` 直接跑、或在临时目录跑），Step 1.5 必须先 ASK 用户指定项目根，不允许默认落桌面

---

## 输入不足处理

| 情况 | 处理方式 |
| --- | --- |
| 用户只给 URL 没说目的 | 默认外部模式 + 默认全 target，但 Step 1 询问是否要 `--dark` / `--responsive` / `--interactions` |
| 用户给路径但仓库是空仓 | 提示"项目里没有任何源码 / 配置文件，无法走内部模式"，引导补内容或改外部模式 |
| 用户给的 URL 是登录后内容 | 主动询问是否提供 `--cookie`，并强调凭据不入产物 |
| 用户没装 Node / Playwright | Step 2 fallback：截图 + 手贴主色，产 `fallback_applied=["no-designlang"]` 的轻量版 |
| 找不到 SparkDesign baseline | 内部模式跳过 Diff 段，标 `fallback_applied=["no-sparkdesign-baseline"]`，handoff_hint 中提示用户后续可手动比对 |
| 用户既给 URL 又给路径 / 又给 Figma | 直接报错，要求拆成多次调用（保证 chain context 不污染） |
| 用户给 Figma URL 但没装 Figma MCP | Step 2 fallback：引导用户安装 MCP（推荐）或手动 export Variables JSON 投喂；`fallback_applied=["no-figma-mcp"]` |
| 用户给 Figma 文件但 Variables 集合为空 | 自动降级到 Local Styles（fill/text/effect），并在 design.md 顶部标注"此文件未使用 Variables，token 源为 Local Styles，建议设计师迁移到 Variables 以获得更稳定的 token 体系" |
| CSS-in-JS 文件 babel 解析报错 | 单文件跳过、累计错误数写入 `fallback_applied=["partial-ast-parse-failure:N-files"]`，整体抽取继续 |
| SparkDesign baseline 找不到 | 整段 Diff 降级 `match_method=naming-only`，标 `fallback_applied=["no-sparkdesign-baseline"]`，handoff_hint 提示用户后续可手动比对 |

---

## 实操注意事项

- **slug 命名**：外部模式从 URL host 派生（`stripe-com`）；内部模式从 `package.json#name` 派生，缺失则用目录名；Figma 模式从 Figma file name 派生 + 加 `-figma` 后缀（避免和同名代码仓库的 slug 撞）
- **多页抓取的代价**：`--depth ≥ 2` 时 designlang 耗时显著（每页 5-15s），抓前提醒用户预计时间
- **dark 模式**：外部抓 `--dark` 后会增加一份 tokens.dark.* 子树；内部模式默认尝试找 `dark:` Tailwind 前缀或 `[data-theme="dark"]` 选择器；Figma 模式自动识别 Variables 的 mode（如果文件用了 Variables modes）
- **token 命名冲突**：内部多源（tailwind + CSS + theme.js + CSS-in-JS AST）冲突时按 Step 3 优先级合并，并在 design.md 里加 `## Conflicts` 段列出，避免静默丢信息
- **CSS-in-JS 性能**（v0.5.2）：项目超过 500 个 `.tsx/.ts/.jsx/.js` 文件时 AST 解析可能耗时 30s+，建议用户加 `--ast-include "src/components/**"` 缩小范围；超大单体仓库建议拆模块分次抽
- **语义匹配规则表维护**（v0.5.2）：发现规则表漏了团队常用别名时，直接 PR 到 `5-Deliver/Extract/references/semantic-rules.json`；不要在 SKILL.md 里直接改硬编码
- **Figma MCP 工具名**（v0.5.2）：本 Skill 默认按 `mcp__figma__get_variables` 这种命名约定调用；如果你装的是非官方 MCP 或者工具名不同，请通过 `--figma-mcp-prefix <prefix>` 参数指定
- **Mobile 输出**：本 Skill 不专门抽 Mobile-only token——Mobile 设计语言通常与 Web 共用一套；如需 Mobile 专属差异，由下游 `/mobile页面设计` 自行解释 breakpoint 内的变化

---

## 已知限制（v0.5.2）

诚实告知用户的能力边界（v0.5.2 已闭合多个 v0.6 限制，剩余项推 v0.5.3+）：

1. **CSS-in-JS 仅支持 styled-components / emotion**：v0.5.2 AST 解析覆盖最常见两种引擎；**vanilla-extract / linaria / stitches 暂不解析**（v0.5.3 规划，按用户反馈优先级排）
2. **CSS-in-JS 不做模板插值 dataflow 分析**：`${...}` 插值结果不追踪，只抽字面值。如果你的 token 大量通过函数 / context 计算，覆盖率会有 gap，请确保有显式 theme 文件兜底
3. **语义匹配规则表是开放式 + 不完备**：v0.5.2 内置初始规则表（color / spacing / shadow / typography 四大类常见别名），团队的特定别名需要人工 PR 到 `references/semantic-rules.json`；规则表没覆盖到的语义等价不会被识别（usage 推断可兜底，但需要足够 usage 数据）
4. **Figma 模式依赖 Figma MCP**：v0.5.2 不内置 Figma API 调用，必须用户预装 Figma MCP（官方或社区方案）；fallback 是手动 export Variables JSON
5. **Figma 模式只抽 Variables / Local Styles**：不抽 component 几何 / Auto Layout / interactive prototype；这些请走 Figma 官方 API 自行实现
6. **不做 watch / sync / score / diff 子命令**：designlang 原生支持，本 Skill 不包装；用户需要时直接走 `npx designlang score|diff|watch|sync`（README 有直通段落说明）
7. **SparkDesign baseline 路径依赖团队约定**：默认找 `node_modules/@spark-design/tokens`，找不到时 Diff 整段降级为 `naming-only`；自定义路径请通过 `--sparkdesign-tokens-path <path>` 参数指定
8. **网络与浏览器依赖**：外部模式不可用于断网 / 严格防火墙环境；Figma 模式不可用于无 MCP 网络出口环境；这两种场景下只能走 fallback 路径
9. **三模式产物不能合并消费**：一次调用只产一种 source.type，跨模式合并（如"线上 Stripe + 我自己代码 + Figma 一起出 design.md"）会污染 chain context，下游解析也无法区分来源 —— 多源对比请用 designlang 原生 `diff` / `brands` 子命令

如果用户需求踩到上述任一限制，主动说明并给出当前可行的替代路径。
