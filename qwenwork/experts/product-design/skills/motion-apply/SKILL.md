---
name: 动效开发
name_en: "motion-apply"
argument-hint: "输入目标元素 + 期望效果（如：按钮加点击粒子效果 / 卡片入场加流光 hover）；React 项目自动选 React Bits 组件，其他项目直写 CSS"
description: >
  动效工程实施层。在 React 项目中按上下文嗅探选 React Bits OSS 组件并通过 `npx shadcn add` 安装；在非 React 项目（Vue / Svelte / Astro / vanilla JS）中直接写 CSS/JS 或推荐合适的动效库。三层设计哲学：上下文优先（读代码比追问便宜）/ 视觉动效描述（用日常语言描述动效像什么，不说技术参数）/ 嗅探主驱（追问是逃生通道，不是主路径）。所有产物强制场景合规自检（DASHBOARD 场景禁止无限循环、禁止持续背景动效、禁止超大位移）；安装后按 Personality + scene 调 props（不裸用组件默认值）。

  触发关键词：动效开发、动效实现、装动效组件、React Bits、reactbits、动效落地、给按钮加效果、给标题加动效、给背景加动效、hover 效果、点击效果、入场效果、滚动效果、loading 动画。

  排除（反向）：不定动效调性 / Personality（用 /动效规划 先定）、不生成 Lottie JSON、不写 GLSL/WebGL shader、不覆盖非 Web 平台（Flutter / SwiftUI / Compose）、不操作 React Bits Pro 付费组件（pro.reactbits.dev 是独立 skill 范畴）。

description_en: >
  Motion implementation layer. For React projects, picks and installs React Bits OSS components via `npx shadcn add` based on project context sniffing. For non-React projects (Vue / Svelte / Astro / vanilla JS), writes CSS/JS directly or recommends suitable libraries. Three design pillars: context-first (reading files is cheaper than asking), visual animation descriptions (describe what it looks like in everyday language, not technical params), sniffing-as-main-driver (asking is the escape hatch, not the main path). All output enforces scene-compliance self-check (DASHBOARD forbids infinite loops, continuous background animations, oversized transforms); after install, tunes props based on Personality + scene (never use component defaults blindly). Reads /motion-plan for Personality + duration palette + per-element specs; pairs with /motion-plan upstream.

  Triggers: motion implementation, install motion component, React Bits, reactbits, add animation to button/heading/background, hover effect, click effect, entrance effect, scroll effect, loading animation.

  Excludes: defining motion personality (use /motion-plan first), generating Lottie JSON, writing GLSL/WebGL shaders, non-web platforms (Flutter / SwiftUI / Compose), React Bits Pro paid components (pro.reactbits.dev — separate skill).

allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [motion-plan, flow-web, flow-mobile, brief]
  writes: motion-apply
  schema:
    skill: string
    generated_at: string
    project_name: string
    framework: enum [react, next, remix, gatsby, vue, svelte, astro, vanilla, non-web]
    scene: enum [landing, dashboard, neutral]
    personality_applied:
      archetype: enum [Playful, Premium, Corporate, Energetic]
      source: enum [motion-plan-link, sniff-fallback]
    path_decisions:
      - target: string
        path: enum [reactbits-component, direct-css, library-recommendation, native-framework-solution]
        reason: string
    installed_components:
      - name: string
        slug: string
        install_command: string
        variant: enum [JS-CSS, JS-TW, TS-CSS, TS-TW]
        peer_deps_added: array<string>
        prop_overrides:
          duration: number
          easing: string
          stagger: number
          intensity_factor: number
    css_snippets:
      - target: string
        file_path: string
        animation_name: string
        scene_compliance_passed: boolean
    profile_path: string
    open_questions: array<string>
---

## 能力矩阵

本 Skill 的三种运行模式，可单独运行也可叠加。最常见路径：链式模式（从 /动效规划 来，按 Personality + duration palette 直接 prop overrides）→ 在 React 项目装 ReactBits 组件 → 写场景合规 CSS。

| 模式 | 触发条件 | 产出特征 |
| --- | --- | --- |
| 🟢 **独立模式** | 无 motion-plan 上下文，直接调用 | 进入 Phase 0（框架探测）→ Phase 1（参数抽取）→ Phase 2（上下文嗅探）→ 选组件 + 默认 prop（按 scene 调） |
| 🔵 **链式模式** | 检测到 `spark-output/context/motion-plan.json` | 跳过 Personality 推断；直接用 motion-plan.element_specs 作为 prop overrides；跳过 Phase 2 调性嗅探 |
| 🟣 **增强模式** | 项目同目录有 SparkDesign 组件库 / 已存在 `spark-output/profile/motion-apply.md` | Component 选型优先匹配 SparkDesign 已有组件；profile 累积 reject/accept 历史，下次选型更准 |

> 三种模式都遵守同一套场景合规红线（LOCKED #7）：DASHBOARD 场景禁 `animation: ... infinite` / 禁持续背景动效 / 禁超 2s 入场 / 禁 translate >20px / scale >1.05 / rotate >5deg。

## 输入要求

| 输入项 | 必填？ | 来源优先级 | 缺失时行为 |
| --- | --- | --- | --- |
| `project_name` | ✅ | 链式 motion-plan / brief > 用户输入 | Phase 0 追问 |
| `framework` | ✅ | 读 `package.json` 自动探测（react/next/remix/gatsby/vue/svelte/astro/vanilla） | 无 package.json + 无 web 标志 → 进入「非 Web 项目」拒绝分支 |
| `scene` | ✅ | 链式 motion-plan.scope.target_pages 推断 > brief 推断 > Phase 2 L3 嗅探（路由 / 依赖 / README 关键词） | 嗅探结果 NEUTRAL，应用 LANDING 默认但 cap 在 mid-range |
| `personality_applied` | ✅ | 链式 motion-plan.personality > Phase 2 嗅探 fallback | 链式不存在时 fallback 到 Corporate（DASHBOARD）/ Premium（LANDING） |
| `target` 元素 | ✅ | 链式 motion-plan.element_specs > 用户输入 | 用户没指明 + 页面 3+ 个候选 → AskUserQuestion 用「UI 元素 + 视觉动效描述」格式追问 |
| `path` 路径决策 | ✅ | Phase 0a/0b/4 决策树自动选 | 必出 PATH DECISION NOTIFICATION（📋 路径 / 原因 / 场景） |
| `prop_overrides` | ✅ | 链式 motion-plan.element_specs[].duration_ms + easing > scene-aware tuning 表默认值 | DASHBOARD 强制覆盖（不用组件默认值） |

**信息完整度判断**：必填项任一缺失 → 优先嗅探项目文件解决（"读代码比问问题便宜"）；嗅探无果且页面 3+ 候选 → AskUserQuestion 追问，且每个选项必须含「UI 元素 + 视觉动效描述」（禁止裸列元素名）。

## Chain Context

### 上游读取（Phase 0 之前执行）

按以下顺序尝试读取上下文，找到即提取并告知用户已沿用：

1. 扫描会话中的 `<!-- spark-context:motion-plan -->` / `<!-- spark-context:flow-web -->` / `<!-- spark-context:brief -->` marker
2. 读取项目目录 `spark-output/context/motion-plan.json` / `flow-web.json` / `flow-mobile.json` / `brief.json`
3. 读取 `spark-output/profile/motion-apply.md`（本 Skill 自己的运行时记忆，含历史选型 / 拒绝偏好 / Tailwind 版本陷阱等）
4. 都没有则跳过，按独立模式 Phase 0→4 全流程执行

可复用字段映射：

- `motion-plan.personality.archetype` → **`personality_applied.archetype`**（直接继承，不再嗅探）
- `motion-plan.brand_motion_identity.signature_easing` + `duration_palette` → `prop_overrides.easing` + `duration` 基础值
- `motion-plan.element_specs[]` → 每个 `target` 的 `prop_overrides`（duration_ms / easing / stagger_ms）
- `motion-plan.scope.target_pages` + `target_elements` → 直接消费，省去 Phase 1 追问
- `motion-plan.choreography.stagger_budget_ms` → 多组件编排总时长上限校验
- `motion-plan.reduced_motion_fallback.strategy` → 写 `@media (prefers-reduced-motion: reduce)` 时的具体策略
- `flow-web/flow-mobile.pages[]` → `scene` 辅助判定
- `brief.style` + `project_type` → `scene` 辅助判定（"产品设计" + 含 dashboard / admin → scene=dashboard）

读到 motion-plan 后告知用户："检测到动效规划上下文（Personality=[...]，[N] 个 element_specs），将直接作为 prop overrides 应用，跳过调性嗅探。"

### 下游输出（最终交付时执行，严格按 chain-protocol §2.1 Step 1→6 顺序）

1. **先写盘**：`Write` 工具把完整 JSON 写到 `spark-output/context/motion-apply.json`
2. **输出自检行**：`✅ motion-apply.json 已写盘到 spark-output/context/motion-apply.json`
3. **渲染交付摘要**（PATH DECISION NOTIFICATION + 安装组件列表 + prop overrides 表 + 写入文件列表）
4. **输出紧凑 marker**：
   ```
   <!-- spark-context:motion-apply ref="spark-output/context/motion-apply.json" -->
   动效开发已完成：project=<name>，framework=<...>，scene=<...>，installed=[<ComponentA>, <ComponentB>]，<N> 段 CSS
   <!-- /spark-context:motion-apply -->
   ```
5. **Handoff 引导**：推荐下游 `/设计走查`（check）做动效合规走查
6. **更新链路面板**（按 Avatar SKILL.md 第 140-158 行的标准流程，独立段落告知用户）

**Profile 同步**：除了 chain context，本 Skill 同时维护 `spark-output/profile/motion-apply.md`（项目级长期记忆，含 stack/scene/tonality/history/preferences/Tailwind 版本陷阱）。该文件在 Phase 5 写入，与 chain context 互补——chain 给下游 Skill 看，profile 给自己下次跑看。

### 字段流向下游

- `motion-apply.installed_components[].name` + `prop_overrides` → **/设计走查**（check）的「动效合规」走查依据（实施是否守住 motion-plan.personality）
- `motion-apply.path_decisions[]` → **/PRD** 的「工程交付清单」（哪些走组件、哪些走原生 CSS、peer deps 增加情况）
- `motion-apply.css_snippets[]` → **/设计走查**（check）的资产清点（每段 CSS 是否过 scene compliance）
- `motion-apply.profile_path` → 项目层长期记忆位置，**/项目复盘**（retro）可读取做技术决策回顾

---

# React Bits Advisor

Helps users add animations and interactive effects to any web project. For React projects, picks from the React Bits OSS catalog (130 components). For non-React projects, writes simple effects directly or recommends suitable libraries. Asks the user only when context inference is insufficient.

## When this skill triggers

- User asks for an animation, animated heading/title, animated background, scroll effect, hover/interaction polish in **any** web project
- User mentions "React Bits", "reactbits", "reactbits.dev"
- User pastes a reactbits.dev URL or a `@react-bits/...` install command

Do NOT trigger for:
- React Bits **Pro** (paid product at `pro.reactbits.dev`, separate component pool, has its own official skill)
- Generic GSAP / Framer Motion API-level authoring without component selection (use those skills instead)

## Hard constraints (LOCKED — never override)

1. **Never copy component source code — not into this skill, not into `references/`, and not manually into the user's project.**
   - Reason: React Bits is licensed MIT + Commons Clause, which prohibits redistributing components. Always fetch via the official CLI: `npx shadcn@latest add @react-bits/<name>-<variant>`.
   - If user asks "直接复制源码到我项目里" or similar: politely refuse and explain — "React Bits 使用 MIT + Commons Clause 许可，组件分发只能通过官方 CLI。我来用 `npx shadcn add` 帮你装，效果完全一样且确保合规。" If user insists after explanation, still refuse — LOCKED constraints are non-negotiable regardless of user acknowledgment.
2. **Never invent component names or URLs.** If a component name is uncertain, read `references/visual-index.md` or fall back to the official site `https://reactbits.dev/`. Encountered an unknown name? Stop and tell the user.
3. **OSS-only scope.** Only operate on `reactbits.dev` (free, MIT+CC). If a request looks like Pro (mentions blocks/templates, `pro.reactbits.dev`, or `@react-bits-pro/`), refuse and redirect: "This is React Bits Pro territory — separate paid product with its own skill. See pro.reactbits.dev."
4. **At most 3 candidates per visual clarification round.** More than that — go back and narrow via context sniffing.
5. **Verify peer-deps before install.** Heavy deps (`three`, `ogl`, `@react-three/fiber`, > 500 KB bundle impact) require explicit user confirmation; do not silently install. **Engine-coexistence check**: if the project already has one animation engine (e.g. `motion`/`framer-motion`) and the candidate component pulls a *different* engine (e.g. `gsap` + `@gsap/react` + ScrollTrigger/SplitText plugins, ~70 KB gzipped), warn the user that two engines will coexist and offer either to (a) proceed knowingly, (b) pick a same-engine alternative, or (c) consolidate by replacing the existing engine. Verified 2026-05-25: SplitText pulls full GSAP stack on a motion-only project.
6. **Never destructively edit the user's existing components.** New components are placed where the React Bits registry decides (typically `src/components/<Name>.tsx` per `components` alias in `components.json`, **not** `src/components/ui/` — that's shadcn-ui's own `ui` alias). Adapt to whatever path the install actually lands at.
7. **Scene compliance applies to ALL output — not just component selection (CRITICAL).**
   The DASHBOARD scene rules (no infinite loops, no continuous background animations, no attention-stealing effects) apply to EVERY line of code this skill outputs, regardless of which path produced it:
   - Phase 0a (direct CSS/JS) — e.g. `animation: X infinite` is FORBIDDEN in dashboard
   - Phase 0b (library recommendation + code snippet) — snippet must obey scene rules
   - Phase 4 (ReactBits component install + wiring) — props must be scene-tuned
   - Any custom code written alongside a component install
   
   **Pre-delivery self-check (LOCKED — run before showing code to user)**:
   If detected scene = DASHBOARD, scan your own output for these violations:
   - `animation: ... infinite` or `animation-iteration-count: infinite` → VIOLATION (continuous loop)
   - `@keyframes` that run forever without user trigger (no `:hover`/`:focus`/`:active`/JS event gate) → VIOLATION
   - Durations > 2s on entrance animations → likely too theatrical for dashboard
   - `transform` with large values (translate > 20px, scale > 1.05, rotate > 5deg) → disproportionate
   - Any effect that draws the eye continuously while idle → VIOLATION
   
   If a violation is found: **fix it before outputting**, don't output then apologize. The user should never see code that violates scene rules.
   
   Dashboard-safe patterns: `transition` (fires only on state change), `:hover`/`:focus` gated animations, `animation` with `forwards` fill (plays once), JS-triggered animations that fire once per interaction.

## Layered configuration model

Three categories of decisions, in priority order:

| Layer | Examples | When fixed |
|---|---|---|
| **LOCKED** (above) | CLI-only install, OSS-only, no source copy | Skill permanent |
| **USER-CONFIRMED** | Stack variant (JS/TS × CSS/TW), animation intensity preference | Per-project, sticky after first confirmation, written to `spark-output/profile/motion-apply.md` |
| **VARIES** | Specific component pick, props, where it's wired in | Per-task |

USER-CONFIRMED values are **inferred via context sniffing first**. Only ask if inference fails or signals conflict.

### Three design pillars (LOCKED — all behavior derives from these)

1. **Context-first (上下文理解)**:  The skill has full access to the user's project files. Use them. Reading the user's page code, dependencies, styles, and existing components is ALWAYS cheaper than asking a question. The skill should feel like it "understands" the project without being told. Asking is a signal that context-reading failed — minimize it.

2. **Visual animation descriptions (动效描述)**:  Animation is visual. Every time the skill mentions a component, proposes a candidate, or asks a question, it MUST describe what the animation LOOKS LIKE in everyday language — not what it IS technically. "逐词从模糊到清晰，像相机对焦" beats "BlurText with animationFrom blur 10px opacity 0". The user picks based on what they can imagine, not what API props say.

3. **Sniffing is the main driver, asking is the escape hatch (嗅探主驱)**:  The default behavior is SILENT: sniff → infer → install → explain afterwards. Asking the user is the LAST resort after both context-reading AND semantic reflection have failed. When asking IS necessary, it must be (a) grounded in their actual page, (b) include visual descriptions, (c) ask about ONE specific gap. A well-designed run touches the user exactly 0–1 times before delivery.

These three pillars are not guidelines — they are the skill's identity. Any phase logic that violates these (e.g. asking generic questions, omitting visual descriptions, ignoring available project context) is a BUG to be patched.

---

## Workflow

```
[Phase 0] Framework detection (gate)
    └─ Read package.json → detect framework
    └─ React / Next.js / Remix / Gatsby? → proceed to Phase 1 (React Bits path)
    └─ Non-React (Vue / Svelte / Astro / vanilla / etc)?
         └─ Simple effect? → write CSS/JS directly (Phase 0a)
         └─ Complex effect? → recommend libraries from references/non-react-alternatives.md (Phase 0b)
[Phase 1] Smart parameter extraction
    └─ Component name explicit in user prompt? → skip to Phase 4
    └─ Animation term ("typewriter", "glitch", "blur") explicit? → narrow Phase 2 candidates
    └─ Neither? → REFLECT on semantic intent (see Phase 1 miss rules)
    └─ Reflection fails? → ask user about functional intent BEFORE entering Phase 2
[Phase 2] Context sniffing (the main path)
    └─ High confidence → silent execution + post-hoc transparency
    └─ Medium → silent + 1-line explanation + escape hatch
    └─ Low / conflict / red-line → REFLECT on why scores are flat (see Phase 2 miss rules)
    └─ Reflection resolves? → re-score with narrowed pool
    └─ Reflection fails? → ask user the ONE differentiating question, then re-score
[Phase 3] Visual clarification (escape hatch only — entered ONLY after reflection exhausted)
    └─ ≤ 3 candidates with: name + 1-line visual + analogy + live demo URL
    └─ Always include "you pick — give me your best guess" option
    └─ > 3 candidates at entry? → reflect on what question cuts the pool, ask it
[Phase 4] Install + wire
    └─ Verify deps → run shadcn CLI → import + minimal usage example
[Phase 5] Sink to profile
    └─ Write project tonality + chosen component to spark-output/profile/motion-apply.md
```

### Global principle: REFLECT before any phase transition (LOCKED)

When ANY phase produces a "miss" (no match, low confidence, too many candidates, ambiguous signal), the skill must:
1. **Pause and reflect**: "Why did this phase not produce a clear answer? What information am I missing?"
2. **Try to self-resolve**: Can I infer the missing info from what the user already said + what I already read?
3. **If reflection resolves**: continue with the insight (no user interaction needed)
4. **If reflection fails**: ask the user ONE targeted question about the specific gap — not a generic preference question
5. **NEVER mechanically jump to the next phase** hoping it will fix itself — that's how loops form

### When asking is NECESSARY vs when context should resolve silently (LOCKED)

**Core stance: sniffing is the main driver. Asking is the ESCAPE HATCH, not the main path.**

But "escape hatch" does NOT mean "avoid asking at all costs." It means: don't ask when context already gives the answer. When context genuinely doesn't contain the answer, asking is the RIGHT thing to do — not a failure.

**Two dimensions of ambiguity** (BOTH must be resolved before proceeding):

1. **WHERE** — which UI element gets the animation? (target ambiguity)
2. **WHAT** — what visual effect happens? (outcome ambiguity)

A user input like "添加点击动效" is ambiguous on BOTH dimensions:
- WHERE: which element? (cards? buttons? nav items? list rows?)
- WHAT: what happens visually on click? (particles fly out? ripple expands? border glows? card presses down? color flashes?)

**Resolution rules:**

| WHERE clear? | WHAT clear? | Action |
|---|---|---|
| Yes (e.g. "给卡片加") | Yes (e.g. "加个涟漪") | Silent execution |
| Yes | No | Ask about WHAT — describe 2–3 visual outcomes for that element |
| No | Yes (e.g. "加个粒子点击效果") | Read page → if 1 obvious target, proceed; if multiple, ask WHERE |
| No | No | Read page → ask BOTH (combine into one question with options) |

**DO NOT ask when:**
- BOTH dimensions are clear from user words + context (e.g. "给按钮加个 Material 涟漪" → WHERE=buttons, WHAT=ripple → just do it)
- Profile records a previous choice for this exact scenario (e.g. "last time user chose ClickSpark for card clicks" → re-use unless they say otherwise)
- The user explicitly said "你帮我选" or "你看着办" → silent execution with post-hoc explanation

**DO ask when:**
- The WHAT dimension is ambiguous: user only named a trigger ("点击"/"hover"/"入场") but not the visual outcome. A trigger + no visual = must ask what it should LOOK LIKE.
- The WHERE dimension is ambiguous: page has 3+ distinct regions the effect could apply to
- Two candidate effects would produce drastically different visual outcomes and you can't tell which the user prefers
- Context and profile have no prior signal about user's style preference for this type of effect

**Critical principle: naming a TRIGGER is not the same as specifying an EFFECT.**
"点击动效" specifies the trigger (click) but NOT the visual result. The skill must not map "click" → "ClickSpark" by default. "Click animation" could mean:
- 粒子从点击点向外飞散 (ClickSpark)
- 涟漪从点击点扩散 (CSS ripple)
- 边框闪一圈星光 (StarBorder)
- 卡片整体轻微下压回弹 (CSS scale transform)
- 点击位置出现一个短暂亮点 (CSS radial-gradient flash)
- 颜色从点击点向外脉冲 (CSS color pulse)

These are COMPLETELY different experiences. Choosing one for the user without asking is presumptuous.

**How to ask — question format (LOCKED, inherits from original design)**

Every question to the user must include visual animation descriptions. Never ask bare "侧导航？标题？卡片？" — that tells the user nothing about what will happen. Instead:

```
看了你的 dashboard 页面，有几个适合加动效的位置：
- 侧导航 → 菜单项切换时向右轻滑入场，选中态柔光高亮 (AnimatedContent)
- 页面标题 → "早上好" 逐词淡入，模糊聚焦感 (BlurText, blur 3px → 0)
- 数据卡片 → hover 时表面流光扫过，点击微粒子飞溅 (GlareHover + ClickSpark)
你想先给哪个加？
```

Rules:
- Each option = **UI 元素 + 动效会是什么样子 + 对应组件名**
- Animation description must be VISUAL (用户能想象画面), not technical (不说 "opacity 0→1 transition 300ms")
- Use everyday language: "逐词淡入" "表面流光扫过" "微粒子飞溅" "轻滑入场"
- At most 3–4 options, each option is one sentence
- Options are derived from READING THE USER'S ACTUAL PAGE (not from skill's category taxonomy)
- After the user picks a target, the component selection can often be inferred silently (target → component is usually 1:1 or 1:2 at most)

---

## Phase 0: Framework detection (gate)

Before anything else, determine if this is a React project.

### Detection

Read `package.json` dependencies. React project = any of these present:
- `react` / `react-dom`
- `next` (Next.js implies React)
- `gatsby` / `remix` / `@remix-run/*`

If `package.json` doesn't exist or none of the above are found → **non-React project**.

**Non-web project gate**: If `package.json` doesn't exist AND none of these web indicators are present (no `index.html`, no `vite.config.*`, no `webpack.config.*`, no `angular.json`, no `svelte.config.*`, no `astro.config.*`, no `nuxt.config.*`), the project is likely **not a web project** (could be Flutter/Dart, iOS/Swift, Android/Kotlin, etc.). In this case:
- Do NOT proceed to Phase 0a/0b
- Output: "This skill handles web project animations (React, Vue, Svelte, Angular, vanilla HTML/JS). Your project doesn't appear to be a web project. The motion-plan skill's timing/easing principles are conceptually applicable but all concrete output is web-specific."
- Stop here — do not attempt to write CSS/JS for non-web frameworks

### Phase 0a: Simple effects — write directly

If the requested effect is **simple** (can be done in ≤ 30 lines of CSS/JS with no library), just write it. Don't recommend a library for something CSS can do natively.

**⚠️ PATH DECISION NOTIFICATION (LOCKED — must output this before writing code)**:

Whenever you choose the "write directly" path (Phase 0a) instead of installing a ReactBits component, you MUST output a clear decision notification to the user BEFORE writing code:

```
📋 路径: 直接写 CSS/JS（非 ReactBits 组件）
原因: <one sentence — e.g. "这个效果用 CSS transition 就能实现，不需要装库">
场景: <detected scene — LANDING/DASHBOARD/NEUTRAL>
```

This also applies when a REACT project's request is better served by vanilla CSS than a component (e.g. simple hover transition). The notification prevents the user from wondering "why didn't it use a ReactBits component?"

**Simple effect examples** (write directly):
- Fade-in on page load → CSS `@keyframes fadeIn` + `animation` property
- Hover scale / color transition → CSS `transition` + `:hover`
- Smooth scroll → CSS `scroll-behavior: smooth`
- Button ripple on click → small JS + CSS `::after` pseudo-element
- Staggered list entrance → CSS `@keyframes` + `animation-delay: calc(var(--i) * 0.1s)`
- Typewriter (single line, no cursor blinking) → CSS `steps()` + `overflow: hidden` + `white-space: nowrap`
- Gradient text → CSS `background-clip: text` + `linear-gradient`
- Parallax scroll (basic) → `transform: translateY(calc(var(--scroll) * 0.3))` + tiny scroll listener
- Skeleton loading shimmer → CSS `@keyframes` + `linear-gradient` moving background

**How to deliver**:
1. Output the PATH DECISION NOTIFICATION (above)
2. Write the CSS/JS code directly into the user's project files
3. Keep it minimal — no build tools, no npm install, just working code
4. Add a comment `/* animation: <what it does> */` at the top for discoverability

### Phase 0b: Complex effects — recommend libraries

If the effect is **complex** (needs timeline orchestration, scroll-driven sequences, physics simulation, 3D, or is too involved for vanilla CSS/JS), recommend a library from `references/non-react-alternatives.md`.

**Complexity signals** (any one → complex):
- User says "timeline" / "sequence" / "orchestrate" / "stagger with easing control"
- Effect involves scroll position → element animation binding with precise offsets
- 3D transforms beyond basic `perspective` + `rotateY`
- Particle systems, fluid dynamics, WebGL shaders
- SVG path morphing / path animation / shape interpolation
- Physics-based (spring, inertia, bounce with realistic damping)
- Multi-element choreography (10+ elements coordinated)

**How to deliver**:
1. Output the PATH DECISION NOTIFICATION (same format as Phase 0a: 📋 路径 + 原因 + 场景)
2. Name the recommended library and explain WHY it fits (one sentence)
3. Give a minimal install command + code snippet (≤ 20 lines) showing the exact effect
4. If the user's framework has a native solution (Vue `<Transition>`, Svelte `transition:`), prefer that over a third-party library
5. At most 2 library recommendations — one lightweight, one full-featured. Don't dump a list of 10 options.

### Framework-native solutions (always prefer over third-party)

- **Vue**: `<Transition>` / `<TransitionGroup>` for enter/leave; `@vueuse/motion` for declarative animations
- **Svelte**: `transition:fade` / `transition:fly` / `animate:flip` (built-in, zero-dep)
- **Angular**: `@angular/animations` (built-in BrowserAnimationsModule)
- **Astro**: `<ViewTransitions />` for page transitions; otherwise vanilla CSS/JS (Astro outputs static HTML)

---

## Phase 1: Smart parameter extraction

Before any sniffing, scan the user prompt for:

- **Explicit component name**: `BlurText`, `SplitText`, `ShinyText`, etc → skip directly to Phase 4 (read `references/visual-index.md` for that component's spec).
- **Explicit animation term WITH visual specificity**: see `references/decision-tree.md` for keyword → candidate mapping (e.g. "打字机效果/typewriter" → DecryptedText/TypewriterText). Use this to pre-narrow Phase 2 candidate pool from 30 to ~5. **But note**: this only works when the user described the VISUAL OUTCOME, not just the TRIGGER. "打字机效果" describes a visual (characters appear one by one); "点击动效" does NOT describe a visual (it only names the trigger).
- **Explicit reactbits.dev URL** in the prompt: extract slug → resolve component name via `references/visual-index.md` or just hand to Phase 4.
- **Explicit framing target**: "标题/heading/hero" vs "background" vs "loader" — narrows the category.

- **All parameters already specified** (fast path): If the user gave concrete values for ALL of: property, distance/amplitude, duration, easing, and target elements — this is an implementation request, not a selection request. Skip Phase 2 entirely. Route decision:
  - If the effect is achievable with simple CSS/JS (fade, slide, stagger via `animation-delay`) → write it directly (Phase 0a style output), even in a React project
  - If the effect specifically needs a ReactBits component (user named one, or the visual matches only one candidate) → go to Phase 4 with the user's explicit params as prop overrides
  - **Do NOT run sniffing to second-guess explicitly provided values.** The user is the designer; respect their numbers.

**Critical distinction — TRIGGER vs VISUAL OUTCOME:**
- "点击动效" / "hover 效果" / "入场动画" → these specify a TRIGGER only. The visual outcome (what it looks like) is unknown. **Do NOT map directly to components.** Instead, note the trigger type and proceed to ask about visual outcome.
- "打字机效果" / "涟漪扩散" / "模糊渐显" / "粒子飞溅" → these specify a VISUAL OUTCOME. Map to components via decision-tree.
- "给按钮加个 Material 涟漪" → BOTH trigger (click on button) and visual (ripple) are clear → proceed directly.

If user input is trigger-only: this is NOT a miss — it's partial information. Read the page to resolve WHERE, then ask about WHAT with grounded visual options (see question format rules above). Do not map trigger keywords to default components.

If any explicit signal hits that specifies a visual outcome, use it. **Do not ignore explicit user signals just because Phase 2 would have inferred something else.**

### Phase 1 miss — REFLECT before proceeding (LOCKED)

If none of the above extraction rules match directly, **do NOT silently skip to Phase 2 with the full unfiltered pool**. Instead, pause and reflect:

1. **Semantic inference**: What is the user actually describing functionally? Map their words to a behavior, not a keyword.
   - "点击动效" → trigger=click, visual=UNKNOWN → this is trigger-only input. Narrow category to interaction/component, but DO NOT select a specific component. Instead ask about visual outcome: "粒子飞散？涟漪扩散？边框闪光？卡片下压？"
   - "打字机效果" → trigger=entrance, visual=characters appearing sequentially → CLEAR. Map to DecryptedText/TypewriterText directly.
   - "页面切换" → trigger=route change, visual=transition between views → narrow to AnimatedContent, FadeContent, PixelTransition
   - "加载状态" → trigger=data fetching, visual=skeleton shimmer or spinner → look for loaders/skeletons
   - Rule: if user described WHAT IT LOOKS LIKE, you can narrow. If they only described WHEN it fires, you need to ask WHAT.

2. **Scene + target cross-reference**: The user often gives context that narrows category even when animation term is vague.
   - "dashboard的点击动效" → scene=DASHBOARD + target=interaction → Components category only → ClickSpark, StarBorder, GlareHover, SpotlightCard
   - "首页的背景" → scene=LANDING + target=background → Backgrounds category

3. **If reflection narrows to ≤ 10 candidates**: proceed to Phase 2 with that narrowed pool.

4. **If reflection still cannot narrow** (truly ambiguous intent — user said something like "加点动效" with zero functional specificity): **read the user's target page first, then ask a grounded question**.

   **Step A — Read the page**: Before asking, read the representative page the user is likely working on. Detection order:
   - User mentioned a specific route/page? → read that file
   - Scene = DASHBOARD? → read `app/(dashboard)/page.tsx`, `src/pages/Dashboard.tsx`, or the layout file
   - Scene = LANDING? → read `app/page.tsx`, `src/App.tsx`, `pages/index.tsx`
   - Fallback: read whatever the main entry component is

   **Step B — Identify concrete UI elements** in that page: sidebar/nav, header/title, card grid, table, form, buttons, hero section, footer, etc. You now have the user's actual UI inventory.

   **Step C — Ask with grounded options + visual animation descriptions** derived from what you actually saw in their code. Each option MUST describe the animation effect, not just the UI element:
   ```
   看了你的 dashboard 页面，有几个适合加动效的位置：
   - 侧导航 → 菜单项切换时向右轻滑入场，选中态柔光高亮
   - 页面标题 → "Good morning" 逐词从模糊到清晰聚焦，像相机对焦
   - 数据卡片 → hover 时表面流光扫过，数字从 0 滚动到真实值
   - 活动列表 → 新条目从下方轻微浮入，透明度渐显
   你想先给哪个加？
   ```

   **Rules for grounded questions (LOCKED)**:
   - Options MUST come from the user's real page structure, not generic categories
   - Each option = **UI 元素 + 动效视觉描述（用户能想象画面）+ 不超过一句话**
   - 动效描述用日常语言："逐词从模糊到清晰" "表面流光扫过" "轻微浮入" "柔光高亮"，不用技术参数
   - 3–4 options max (pick the most visually impactful candidates from the page)
   - If the page has only 1–2 obvious animation targets: skip the question, just proceed with that target
   - Never ask bare "侧导航？标题？卡片？" without describing the animation — that tells the user nothing about what will HAPPEN
   - Never ask "文字/背景/交互/过渡" in the abstract when you can read the actual page and say "侧导航/标题/卡片/表格"

   **Asking necessity check (before asking)**:
   - Re-verify: is context truly insufficient? If user said "点击动效" and the page has only one interactive region (e.g. a card grid), just animate that — don't ask.
   - The threshold: ask ONLY when the page has 3+ distinct regions that could all reasonably be the target AND the user's words don't favor one over others.

   This is the key difference from a generic skill: **we have access to the user's code, so our questions should reflect their reality, not our category taxonomy.**

**Never enter Phase 2 with the full unfiltered pool (45+ candidates).** Phase 2's scoring only works well when the pool is ≤ 10–15. Larger pools produce flat score distributions that inevitably escalate to Phase 3 and loop.

---

## Phase 2: Context sniffing (main driver)

### Sniffing order (progressive — stop at first sufficient signal)

1. `spark-output/profile/motion-apply.md` (project profile from previous runs)
2. `package.json` (deps, description, framework)
3. `tailwind.config.{js,ts,mjs,cjs}` or `tailwind.config` in CSS (theme.colors, fontFamily)
4. Representative page: `app/page.tsx` / `src/App.tsx` / `pages/index.tsx`
5. `tsconfig.json` (TS yes/no; strict mode for tone hint)
6. `globals.css` / root style file (border-radius defaults, font imports)
7. `README.md` first 30 lines (project semantic — marketing vs dashboard vs portfolio)
8. Existing `src/components/ui/` (already-installed React Bits components → consistency signal)

### Four-layer signal matrix

```
L1 Tech stack (hardest, binary)
    - tsconfig.json present → variant TS, else JS
    - tailwind.config.* present → variant TW, else CSS
    - existing animation engine in deps:
        framer-motion / motion → prefer "motion" engine components
        gsap → prefer GSAP engine components
        three, @react-three/fiber → 3D-capable already
        ogl → low-level WebGL already
        none → recommend lightest-weight engine first

L2 Visual tonality (medium hard, requires aggregation)
    - Tailwind theme.colors:
        mostly grayscale + 1 accent → restrained / professional
        saturated multi-color palette → playful / vibrant
        neon (cyan/magenta) → cyber / tech
    - Font family:
        Inter / Geist / Söhne / system → modern restrained
        Playfair / Cormorant / serif → editorial elegant
        JetBrains Mono / Fira Code → developer / technical
        Pacifico / Caveat / handwritten → casual playful
    - Border radius default in globals.css:
        0–4 px → sharp / minimal
        8–12 px → mainstream modern
        16+ px → friendly / rounded

L3 Project semantics + scene type (soft, high value, careful)
    - **Scene detection** (NEW — determines animation intensity ceiling):
        Landing signals: route `/(marketing)/`, `/landing`, `/hero`, `/(public)/`;
            package.json keywords "landing"/"showcase"/"agency"/"portfolio";
            README mentions "landing page"/"showcase"/"marketing site";
            large hero sections, full-viewport backgrounds, few interactive forms.
            → scene = LANDING (high-impact tolerance)
        Dashboard signals: route `/(dashboard)/`, `/admin`, `/settings`, `/console`, `/(app)/`;
            deps include data-table / chart / form libs (react-hook-form, zod, @tanstack/react-table, recharts);
            README mentions "dashboard"/"admin"/"CRM"/"ERP"/"internal"/"management"/"backoffice";
            heavy use of table/form/sidebar layout components.
            → scene = DASHBOARD (low-impact ceiling)
        Both present: route groups like `app/(marketing)/` AND `app/(dashboard)/`
            → ask user which part they're working on RIGHT NOW (this is a valid question, not low-value)
        Neither detected: → scene = NEUTRAL (no filtering, fall through to tone-only)

    - **Scene → intensity ceiling mapping**:
        LANDING:   allow all intensities (dramatic, intense, showcase, edgy — all ok)
        DASHBOARD: ceiling = subtle/functional. Hard-filter components tagged scene=landing.
                   Prefer: short-duration, non-looping, user-triggered-only animations.
                   Tolerate: micro-interactions (ClickSpark), functional transitions (FadeContent, AnimatedContent),
                             data visualisation polish (CountUp, Counter), subtle hover feedback (GlareHover, SpotlightCard).
                   Reject: continuous background animations (Hyperspeed, Plasma), dramatic entrances (SplitText with GSAP),
                           heavy 3D (DomeGallery, ModelViewer), attention-stealing loops (Ribbons, Lightning).
        NEUTRAL:   no scene filter, rely on tone matching only.

    - package.json description / README headline (non-scene semantics, still used for tone):
        "portfolio" / "creative" → bold ok
        "docs" / "blog" → informational / restrained

L4 Existing convention (softest, highest authority)
    - Already-used React Bits components → strong consistency pull
    - spark-output/profile/motion-apply.md preferences
    - Project styleguide.md / CONTRIBUTING.md (if present)
```

### Scoring formula

```
candidate_score = Σ (signal_weight × signal_credibility)

L1 weight: 4 (engine match / mismatch is decisive)
L2 weight: 2
L3 weight: 3
L4 weight: 5 (consistency wins)

Credibility 0.0–1.0 based on signal clarity:
  - explicit dep / explicit token: 1.0
  - aggregated heuristic (multiple weak signals): 0.6–0.8
  - single weak signal: 0.3–0.5
```

### Confidence thresholds

| Top score | Lead over #2 | Action |
|---|---|---|
| ≥ 8.0 | ≥ 2.0 | **Silent execution** + post-hoc transparency note (see template below) |
| 6.0–7.9 | ≥ 1.0 | **Silent + 1-line explanation in delivery** |
| < 6.0 OR lead < 1.0 | — | **REFLECT then escalate** (see below) |

### Phase 2 miss — REFLECT before escalating (LOCKED)

When scoring lands in the "< 6.0 / lead < 1.0" bucket, do NOT mechanically jump to Phase 3. First reflect:

1. **Why are scores flat?** Common causes:
   - Candidate pool too large (Phase 1 didn't narrow enough) → the scoring is diluted. Reflect: can I re-read the user's words and extract a functional category NOW that I missed in Phase 1? If yes, re-narrow the pool and re-score. This is NOT "looping back to Phase 2" — it's completing Phase 1 reflection mid-stream.
   - Multiple candidates are genuinely equivalent for this project (e.g. ClickSpark and StarBorder both work for "click animation" in this project) → this is fine. Pick the top 2–3 and proceed to Phase 3 as a genuine choice question.
   - Scoring signals conflict (red line #1) → acknowledge the conflict and ask the user about the specific conflict, not a generic preference.

2. **Can I answer "why is the user asking for THIS?" from context?**
   - The user said "点击动效" on a dashboard → they probably want subtle click feedback on buttons/cards → ClickSpark (particle burst) or GlareHover (shine on hover+click). I can infer this without asking.
   - If I can narrow to 1–2 clear winners through this reasoning: proceed to silent execution.
   - If I genuinely can't tell (e.g. "加个动效" with no target specified): **read the target page** (same as Phase 1 miss Step A–C) and ask a grounded question based on what UI elements actually exist in their code. The question references their real page structure — "你的 dashboard 里有侧边栏、数据卡片、活动列表，你想给哪个加？" — not abstract categories.

3. **Escalation to Phase 3 is the LAST resort**, not the default. The escalation question must be about the specific ambiguity I identified during reflection, not a generic "pick one of these 3".

### Red lines (must escalate regardless of score)

1. Top-2 signals contradict each other (e.g. marketing copy + minimalist palette)
2. No L2 OR L3 signal at all (brand-new empty project — no personality to infer). **Important**: this means Phase 2 is exhausted; do NOT loop back from Phase 3 to Phase 2 — use the circuit breaker path instead.
3. User has previously rejected this exact recommendation (read profile)
4. Top candidate requires a heavy new dep (`three`, `ogl`, > 500 KB) and project doesn't already have it
5. Top-2 candidates are visually drastically different (e.g. restrained vs glitch) and scores are within 1 point
6. **Scene mismatch**: candidate is tagged `scene: landing` but detected project scene is DASHBOARD (or vice versa). This is a hard filter, not a soft penalty — skip the candidate entirely rather than penalizing its score.

### Progressive sniffing

First pass: read only files 1–3 (profile, package.json, tailwind.config). If that gives ≥ 70% confidence on the variant + tonality, stop. Only deepen sniffing if Phase 3 is escalated or user pushes back.

### Post-hoc transparency template (used in silent-execution mode)

After installing, deliver with this 3-element sign-off:

```
✅ Installed <ComponentName>.

I picked it because <signal evidence — concrete: "your project uses Geist + neutral palette + framer-motion already, so I went with the motion-engine restrained option">.

If you want a more <opposite-direction adjective> alternative, say the word and I'll swap to <ComponentName-B> or <ComponentName-C>.
```

This satisfies "user無感 but can still correct" — invisible decision, visible reasoning, easy reversal.

---

## Phase 3: Visual clarification (escape hatch)

Trigger only when Phase 2 lands in the "< 6.0 / red line" bucket. Use `AskUserQuestion`.

### Question template (LOCKED format)

- Question: "<concrete framing — e.g. '标题动画的感觉更偏向哪种？'>"
- Options: 1–3, each with:
  - Component name (technical anchor)
  - One-line visual description (≤ 15 chars Chinese / ≤ 25 words English)
  - Mass-culture analogy (movie / brand / product reference)
  - Live demo URL: `https://reactbits.dev/<category>/<slug>`
- Always include an implicit fourth: "Other" (auto-provided by AskUserQuestion) for "you pick — match my project tonality."

### Anti-overload rules (LOCKED)

- Max 3 substantive candidates per question
- After 2 clarification rounds without convergence → drop to **silent best-guess** mode and tell the user "I'll go with <X> based on your project — replace if it doesn't fit"

### Phase 3 miss — too many candidates? REFLECT, don't loop (LOCKED)

If the candidate pool reaching Phase 3 is > 3, this means upstream (Phase 1 + Phase 2) failed to narrow sufficiently. The old rule "go back to Phase 2 and re-narrow" is **REMOVED** — it causes infinite loops when Phase 2 has no new information to offer.

Instead, when candidates > 3 at Phase 3 entry:

1. **Reflect on WHY the pool is still large.** It's almost always because the user's functional intent wasn't pinned down. Ask yourself: "What is the ONE piece of information that, if I knew it, would cut the pool from N to 2–3?"
   - Usually: the animation TARGET (which UI element on their page?)
   - Sometimes: the intensity preference (subtle feedback vs dramatic effect)
   - Rarely: the engine preference (this should come from project sniffing)

2. **Read the user's page and ask a grounded question.** Same principle as Phase 1 miss: read their actual target page, identify the UI elements present, and frame the question around what they HAVE.
   - GOOD: "看了你的 dashboard，有侧导航、标题区、3 个数据卡片和一个活动列表。你想给哪个加动效？"
   - BAD: "你想给哪类元素加点击效果？按钮、卡片、还是整个区域？" (too generic — doesn't reflect their actual page)
   - The user's page IS the source of options. Never invent UI elements they don't have.

3. **After the user answers, re-enter Phase 2 scoring with the newly narrowed pool.** This is NOT a "loop" — it's a single directed retry with genuinely new information from the user.

4. **If after 1 user-answer the pool is still > 3**: force-rank by popularity within the narrowed category and present top 3. Never ask more than 2 rounds total.

### Never-loop guarantee

The skill must NEVER re-enter a phase it has already completed without new information. "New information" means either (a) user provided an answer, or (b) a file was read that wasn't read before. Re-entering Phase 2 with the same files and same user input is FORBIDDEN — that's a loop, not a retry.

### Visual rendering tiers (v0.1 → v0.3)

| Tier | When | How |
|---|---|---|
| v0.1 (now) | Always | Live demo URL link in the option (user clicks to see real render on reactbits.dev) |
| v0.2 (later) | Top-30 high-frequency components | Pre-recorded GIF cached in `references/previews/<slug>.gif` |
| v0.3 (later) | When QoderWork supports inline render | React artifact / dev-server preview inside the conversation |

For v0.1: lean on the **mass-culture analogy** to compensate for the user needing to switch windows. A good analogy ("黑客帝国数据流" for DecryptedText) gives 80% of the visual intent in 8 characters.

---

## Phase 4: Install + wire

### Path decision notification (applies to React projects too)

Even in a React project, sometimes the best answer is vanilla CSS (e.g. simple hover transition, one-shot fade-in) rather than a ReactBits component. When you make this choice, output the same notification format:

```
📋 路径: 直接写 CSS（ReactBits 组件库里没有比原生 CSS 更好的方案）
原因: <e.g. "hover 边框高光用 CSS transition 就够了，装组件反而重">
场景: DASHBOARD
```

If you DO install a ReactBits component, the notification format is:
```
📋 路径: ReactBits 组件 — <ComponentName>
原因: <e.g. "点击时粒子飞溅效果需要 canvas 计算，ClickSpark 封装好了">
场景: DASHBOARD → 参数已按工作台级别压低
```

This notification is MANDATORY for every execution path. The user must always know which route was taken and why.

### Variant resolution

Variant comes from Phase 2 L1 signals (tsconfig + tailwind.config). Map:

```
tsconfig.json present + tailwind.config.* present → TS-TW
tsconfig.json present + no tailwind             → TS-CSS
no tsconfig + tailwind.config.*                  → JS-TW
no tsconfig + no tailwind                        → JS-CSS
```

If signals are ambiguous (project has both .ts and .js files heavily), ask once via AskUserQuestion and write the answer to profile.

### Install command (LOCKED format — verified from official README)

```bash
npx shadcn@4.7.0 add @react-bits/<ComponentName>-<JS|TS>-<CSS|TW>
```

Example: `npx shadcn@4.7.0 add @react-bits/BlurText-TS-TW`

> **Why pinned to 4.7.0**: shadcn 4.8.x has been observed to fail with `connect EBADF` against `ui.shadcn.com` in some network environments. 4.7.0 is the last reliably-working version as of 2026-05-25. Re-evaluate on next E2E run.

### Pre-install checks

1. Read `package.json` → confirm React 18+ (React Bits requires modern React)
2. **Check shadcn prerequisites** (verified by E2E, all 4 must pass before `shadcn add`):
   - **`components.json` exists at project root.** If missing, run `npx shadcn@4.7.0 init --template <vite|next|react-router|...> --base radix --preset nova --silent --yes`. Pin to **4.7.0** until 4.8.x network issues (`connect EBADF` on `ui.shadcn.com`) are resolved.
   - **Path aliases configured.** `tsconfig.json` (or `tsconfig.app.json` in Vite) needs `compilerOptions.baseUrl` + `paths: { "@/*": ["./src/*"] }`. For Vite, `vite.config.ts` also needs the matching `resolve.alias` entry. shadcn init refuses without these.
   - **Tailwind major version.** Run `cat node_modules/tailwindcss/package.json | grep version` (or read `package.json` deps). **shadcn 4.x init writes Tailwind v4 syntax** (`@apply border-border`, `@import "shadcn/tailwind.css"`) which **does not compile** on Tailwind v3. If project is on v3: skip `shadcn init` and instead hand-author a minimal `components.json` (see template below), or offer the user to upgrade to Tailwind v4 first.
   - **`verbatimModuleSyntax`**: read `tsconfig.app.json`. If `"verbatimModuleSyntax": true`, **warn the user** — many React Bits components (verified: `BlurText`, likely others using `motion`'s `Transition`/`Easing` types) import types and values on the same line, which fails typecheck under this setting. Offer either: (a) post-install patch the local copy to split type imports (allowed — the local `src/components/<Name>.tsx` is a user copy, not redistribution), or (b) toggle `verbatimModuleSyntax: false` in tsconfig.
3. Read `references/dependencies.md` → look up the component's peer deps
4. For each peer dep, check if already installed:
   - Already installed → proceed silently
   - Missing + lightweight (`motion`, `framer-motion`) → install silently as part of shadcn flow
   - Missing + heavy (`three`, `ogl`, `@react-three/fiber`) → **stop, tell user the bundle impact, ask to confirm**
5. Confirm install path matches project convention. **React Bits registry places components at the path of the `components` alias in `components.json`** (typically `src/components/<Name>.tsx`), not under the `ui` alias. After install, do not assume `src/components/ui/<Name>.tsx`; locate the actual file before wiring.

### Minimal components.json template (for Tailwind v3 projects skipping `shadcn init`)

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/index.css",
    "baseColor": "neutral",
    "cssVariables": false,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "registries": {}
}
```

### Scene-aware prop tuning (LOCKED — always apply after install)

After installing a component, **adjust its animation props based on detected scene**. The same component must behave differently in a landing page vs a dashboard. Do not use component defaults blindly — they are tuned for showcase/landing contexts.

**Text animation components (BlurText, SplitText, etc.):**

| Prop | LANDING | DASHBOARD | Why |
|------|---------|-----------|-----|
| **BlurText** `animationFrom` | `{ filter: 'blur(10px)', opacity: 0, y: 50 }` (default) | `{ filter: 'blur(3px)', opacity: 0, y: 8 }` | Dashboard text should barely shift; large Y displacement and heavy blur feel like a loading glitch in a functional UI |
| **BlurText** `animationTo` | `[{ filter: 'blur(5px)', opacity: 0.5, y: -5 }, { filter: 'blur(0px)', opacity: 1, y: 0 }]` (default) | `[{ filter: 'blur(1px)', opacity: 0.7, y: 2 }, { filter: 'blur(0px)', opacity: 1, y: 0 }]` | Intermediate blur step should also be minimal |
| **BlurText** `delay` | 150ms (deliberate, cinematic) | 60ms (snappy, functional) | Users in dashboards want to read content, not watch it arrive |
| **SplitText** `from` | `{ opacity: 0, y: 40 }` (default) | `{ opacity: 0, y: 6 }` | Tiny upward nudge is enough; 40px throw is theatrical |
| **SplitText** `duration` | 1.0–1.25s | 0.3–0.4s | Fast settle — dashboard users scan, not stare |
| **SplitText** `delay` (stagger) | 50ms | 20–25ms | Minimal stagger so words appear near-simultaneously |
| **Font / size** | Display/serif fonts ok (e.g. Playfair Display), `text-7xl`–`text-9xl` | System/sans-serif (e.g. Geist, Inter), `text-xl`–`text-3xl` | Dashboard headings are functional labels, not hero statements |

**Background components (Waves, etc.):**

| Prop | LANDING | DASHBOARD | Why |
|------|---------|-----------|-----|
| **Waves** `lineColor` alpha | 0.15–0.20 | 0.03–0.05 | Background must not compete with data tables and charts |
| **Waves** `waveAmpX / waveAmpY` | 60–100 / 30–50 | 10–20 / 5–10 | Near-static feels intentional; large waves feel broken |
| **Waves** `waveSpeedX / waveSpeedY` | 0.03–0.05 / 0.01–0.03 | 0.005–0.01 / 0.002–0.005 | Imperceptible drift — "is it even moving?" is the right question |
| **Waves** `maxCursorMove` | 150–250 | 20–50 | Minimal mouse reactivity in a workspace |
| **Waves** wrapper | none | `<div className="opacity-30">` | Extra opacity layer as safety net |
| **Waves** `xGap / yGap` | 8–12 / 24–36 | 14–20 / 40–56 | Sparser lines = calmer background |

**General rules:**
- LANDING: component defaults are usually fine or can be pushed higher.
- DASHBOARD: **always override** — defaults are too dramatic. Use the dashboard column above as starting points.
- NEUTRAL scene: use landing defaults but cap at mid-range (e.g. amp 60 not 100).
- **Personality modifier for dashboards**: If the project's profile has a Personality ≠ Corporate (e.g. Playful brand in a dashboard context), apply a 1.3× multiplier to dashboard values (duration, amplitude, stagger) while still staying below 50% of landing defaults. This prevents over-suppressing a brand's personality in functional contexts. Example: Playful DASHBOARD BlurText delay = 60ms × 1.3 ≈ 80ms (not 60ms, not 150ms).
- These values are calibrated from E2E testing (2026-05-25). If a future component has different prop names, apply the same principle: dashboard = 15–25% of landing intensity.

### Wiring

After install:
1. Find a sensible default insertion point (e.g. for a heading animation: the existing `<h1>` in the representative page found during sniffing)
2. Show a minimal usage diff (don't auto-edit unless user said "也帮我接进去" or equivalent)
3. Provide both: (a) bare import + JSX example and (b) optional in-place edit suggestion
4. **Apply scene-aware prop tuning** (see table above) — this is not optional

### Failure recovery

- Install fails with "registry not found" → likely network / typo. Verify alias against `references/visual-index.md`. Do not retry blindly.
- Peer dep resolution fails → suggest user run `npm install` manually and re-run.
- Component renders but throws on mount (often SSR + client-only animation) → check Next.js context; suggest `'use client'` directive or dynamic import with `ssr: false`.
- `shadcn add` fails with "You need to create a components.json file" → run pre-install check #2 (the components.json bootstrap path), then retry.
- Build fails with `TS1484: 'X' is a type and must be imported using a type-only import` → this is the `verbatimModuleSyntax` issue. Patch the installed component file: split the offending `import { foo, BarType }` into `import { foo }` + `import type { BarType }`. Document this in the project profile so it isn't re-discovered.
- Build fails with `The 'border-border' class does not exist` (or any `bg-background`, `text-foreground`, `outline-ring/50`) → shadcn injected Tailwind v4 syntax into a v3 project's CSS. Fix: revert `src/index.css` to plain `@tailwind base/components/utilities` (back up first), and use the minimal `components.json` template above instead of running `shadcn init` again.
- shadcn init prompts interactively despite `--silent --yes` (e.g. preset selection) → pass all flags explicitly: `--template <X> --base radix --preset nova --silent --yes`. The `-y` alone does not skip every prompt.

---

## Phase 5: Profile sinking

After successful install, write or update `spark-output/profile/motion-apply.md` (project-local, gitignored by default — add `spark-output/profile/` to `.gitignore` if not already):

```markdown
# React Bits — Project Profile
_Auto-maintained by motion-apply skill. Edit manually to override._

## Stack
- Variant: TS-TW
- Animation engine: framer-motion (already installed)
- React version: 18.3.1
- Framework: Next.js 15

## Scene
- Detected: DASHBOARD (routes: /app/dashboard/*, /app/settings/*)
- Intensity ceiling: subtle/functional only
- Override: user can say "这个页面是 landing page" to unlock high-impact components for that specific task

## Tonality (inferred)
- Style: modern restrained (confidence 0.85)
- Color: neutral grayscale + accent
- Font: Geist Sans
- Radius: 8 px

## History
- 2026-05-25: installed BlurText (kept) — for hero heading
- 2026-05-26: tried SplitText (rejected by user — "too dramatic") → preference signal updated
  → avoid: dramatic / aggressive entrance animations

## Preferences (derived)
- Lean: restrained, focused, motion-engine
- Avoid: glitch, rainbow, neon, three.js-heavy
```

### Update triggers

- After every successful install → append to History
- User rejects / replaces an installed component → update Preferences `Avoid` list and add rejection to History
- Skill sees stack mismatch (user manually changed tsconfig / tailwind) → update Stack section

---

## E2E findings log (rolling — used for skill maintenance)

Each entry is one real install run that exposed a gap in this skill. Patches applied above.

- **2026-05-25 / Vite 8 + React 19 + Tailwind v3 + motion / `BlurText-TS-TW`**:
  1. shadcn 4.8.0 init failed with `connect EBADF` on `ui.shadcn.com` → pinned to 4.7.0 (Phase 4 install command updated)
  2. shadcn requires `components.json` + `paths` aliases in tsconfig + `vite.config.ts` `resolve.alias` before `add` works → pre-install check #2 added
  3. shadcn 4.x init writes Tailwind v4 syntax to v3 projects, breaks PostCSS build → pre-install check #2 (Tailwind major version branch) + minimal components.json template added
  4. BlurText.tsx imports `motion, Transition, Easing` mixed (value + types) on one line; fails under Vite default `verbatimModuleSyntax: true` → pre-install check #2 (tsconfig audit) + failure recovery entry added
  5. Component lands at `src/components/BlurText.tsx`, not `src/components/ui/` → LOCKED #6 reworded, pre-install check #5 added
  6. Final outcome: build (`tsc -b && vite build`) and `vite dev` both serve BlurText cleanly. Profile written.

- **2026-05-25 / same project + `SplitText-TS-TW` for visual comparison**:
  1. shadcn 4.7.0 broke fetching `https://ui.shadcn.com/r/colors/neutral.json` (also `connect EBADF`); 4.6.0 succeeded. Reliability ranking so far: **4.6.0 ≥ 4.7.0 > 4.8.x**. Consider pinning install command to 4.6.0 if 4.7.0 misses color fetches in future runs.
  2. SplitText silently pulled `gsap@^3.15` + `@gsap/react@^2` + ScrollTrigger + SplitText plugin (~70 KB gzipped) into a project that already had `motion` → two engines coexisting. Skill LOCKED #5 was updated to add an engine-coexistence warning.
  3. Component import block was value-only (no `verbatimModuleSyntax` issue this time) and rendered cleanly via dev server. Confirmed visual contrast vs BlurText is sharp enough to function as the "drastically different #2 candidate" red-line trigger if ever scored close.

- **2026-05-25 / crawler v1 implemented**:
  1. Replaced the SKELETON `crawl-catalog.sh` with a real Python implementation (`scripts/crawl_catalog.py`). Source of truth is `https://raw.githubusercontent.com/DavidHDev/react-bits/main/src/constants/Categories.js` (canonical sidebar list) + per-component `src/ts-tailwind/<Cat>/<Pascal>/<Pascal>.tsx` (engine signal via import parsing).
  2. Catalog snapshot 2026-05-25: **130 OSS components** across Text Animations (23) / Animations (29) / Components (36) / Backgrounds (42). Engine distribution: motion 20 / gsap 29 / three 22 / ogl 26 / none 33. Heavy (three+ogl) = 49 components (~38%). Zero quarantined — all `assert_oss` checks pass against upstream.
  3. Hand-curated tone/visual/analogy now lives in `references/visual-index-handcurated.json`, keyed by slug. The skill's IP layer is no longer co-mingled with mechanical data — crawler refreshes can't clobber it. Initial seed has 28 entries (covering the high-confidence top text/background/component picks); the long tail defaults to `TODO` and gets filled in over time as those components surface in real runs.
  4. Engine detection from imports cross-validated against the actual `npx shadcn add` outcomes from earlier E2E runs: BlurText → motion ✓, SplitText → gsap ✓ (matches the GSAP stack pulled in install). Confidence: high.

- **2026-05-25 / handcurated long-tail filled**:
  1. `visual-index-handcurated.json` grew from 28 → **130 entries** (full coverage, 0 TODO). Every component now has a tone, a ≤12-char Chinese visual, and a mass-culture analogy. For ambiguous components (Antigravity, LaserFlow, Lanyard, Balatro, etc.) prop signatures from `src/demo/<Cat>/<Name>Demo.jsx` were probed first to ground the description in actual code (e.g. `magnetRadius/waveSpeed/particleSize` → "粒子受磁场反重力浮动" for Antigravity), avoiding fabricated guesses.
  2. Tone vocabulary stabilised to 17 values: dramatic, restrained, decorative, informational, playful, subtle, edgy, minimal, techy, balanced, polished, luxe, ethereal, intense, dreamy, showcase, iconic. Distribution skews playful/techy/edgy (47/130 = 36%) reflecting React Bits' expressive default; minimal/polished/restrained/balanced (29/130 = 22%) preserves discoverability for restrained projects.
  3. Phase 3 visual-clarification choices can now always present a concrete analogy ("苹果发布会逐字弹出" / "黑客帝国数据流" / "千年隼跃迁") regardless of which component the decision tree surfaces. This was the biggest gap between v0.1 (28 covered) and a production-ready advisor.

- **2026-05-25 / scene-based filtering added (v0.1.5)**:
  1. Added `scene` field to all 130 entries in `visual-index-handcurated.json`. Values: `landing` (showcase pages, high-impact ok), `dashboard` (functional UI, subtle only), `both` (adapts). Distribution: ~83 landing-only / ~45 both / 0 dashboard-only.
  2. Phase 2 L3 now includes **scene detection**: reads route structure (`/(dashboard)/` vs `/(marketing)/`), package.json deps (data-table/chart/form libs → dashboard signal), README keywords. Detected scene persists to profile for reuse.
  3. Scene mismatch added as **red line #6**: candidate tagged `scene: landing` in a DASHBOARD project is hard-filtered (not just penalized). This is the single biggest search-space reduction — dashboard projects go from 130 → ~45 candidates before any other filtering.
  4. Decision tree updated with scene-aware multi-keyword routing: if user asks for "酷炫标题" in a dashboard project, all high-impact text animations are filtered out and skill proactively suggests dashboard-appropriate alternatives instead of silently picking something wrong.
  5. User can override per-task ("这个页面是 landing page") without changing project-level scene detection.

- **2026-05-25 / scene-aware prop tuning E2E (v0.1.7)**:
  1. Waves background installed via same skill pipeline (engine=none, zero new deps). Hit `verbatimModuleSyntax` again on `CSSProperties` import — profile had the fix documented, applied in seconds (validates profile-as-memory).
  2. Dashboard test: component defaults (blur 10px, y 50px, Waves amp 40/20) are wildly too dramatic for functional UI. User called it "不够克制" — displacement too large, blur too exaggerated.
  3. Added **Scene-aware prop tuning table** to Phase 4 (before Wiring): concrete prop values for LANDING vs DASHBOARD for BlurText, SplitText, and Waves. Dashboard values are ~15–25% of landing intensity across all dimensions (blur, y-offset, duration, wave amplitude, line opacity, cursor reactivity).
  4. Key insight: component defaults are always tuned for showcase. "Installing the right component" is only half the job — **tuning its props for the scene** is equally important and was previously missing from the skill.
  5. Font guidance added: landing allows display/serif fonts at hero sizes (text-7xl+); dashboard mandates sans-serif at functional sizes (text-xl–text-3xl).

- **2026-05-26 / infinite loop bug fix (v0.1.8)**:
  1. Input "帮我实现dashboard的点击动效" caused skill to loop forever between Phase 2 and Phase 3.
  2. Root cause: "点击/click" was missing from decision-tree keywords → Phase 1 produced no narrowing → Phase 2 had no project files (no workspace selected) → red line #2 escalated to Phase 3 → Phase 3 saw too many candidates (>3) → anti-overload rule sent back to Phase 2 → Phase 2 still had no files → infinite loop.
  3. Fix A: Added "点击/click/tap" to decision-tree keyword group "按钮/涟漪/button/ripple" → ClickSpark, StarBorder.
  4. Fix B: Added **circuit breaker** to Phase 3 anti-overload rules. If Phase 2 escalated due to red line #2 (no files at all), Phase 3 must NOT send back to Phase 2. Instead: use Phase 1 keyword narrowing + scene filter + popularity ranking → present top 3 directly.
  5. Key insight: "go back to Phase 2 and re-narrow" is only valid when Phase 2 had partial data. When Phase 2 had ZERO input, re-entering it is guaranteed to loop. The precondition for the "re-narrow" instruction was never stated — now it is.

- **2026-05-26 / reflect-before-jump redesign (v0.1.9)**:
  1. User clarified: the loop scenario was on a REAL project (files exist). v0.1.8 fix was too narrow — circuit breaker only handled "no files" edge case. Real issue: Phase 2 reads files fine but 45 dashboard-compatible candidates all score similarly → flat distribution → escalates to Phase 3 → Phase 3 says "too many" → old rule sends back to Phase 2 → loop with identical data.
  2. Root philosophy change: **mechanical phase jumping is the disease, not the symptom**. Every "miss" must trigger self-reflection, not a blind jump.
  3. New Phase 1 miss handling: semantic inference (map user words to behavior/category even when exact keyword absent). "点击动效" → interaction feedback → Components category → pool of 4 not 45.
  4. New Phase 2 miss handling: reflect on WHY scores are flat (pool still too large? signals genuinely conflict?). If can self-resolve: re-narrow and re-score. If not: ask user ONE differentiating question.
  5. New Phase 3 miss handling: if candidates > 3 at entry, reflect on what question cuts the pool, ask it directly. REMOVED the "go back to Phase 2" rule entirely.
  6. Global principle added: "NEVER re-enter a phase without new information (user answer OR unread file). Same input + same files = forbidden re-entry."
  7. This is the biggest architectural change since v0.1.0 — transforms the skill from a mechanical state machine into a reasoning agent that stops and thinks at each transition point.

- **2026-05-26 / three-pillar anchoring + question necessity tightening (v0.2.1)**:
  1. User feedback: recent "reflect then ask" changes made skill potentially too eager to ask. Original design was "嗅探主驱, 追问是逃生通道" — needed to re-anchor.
  2. Added **Three design pillars** section (LOCKED): (1) Context-first — reading files is cheaper than asking, (2) Visual animation descriptions — every mention of a component must describe what it looks like, (3) Sniffing is main driver — asking is last resort.
  3. Tightened asking necessity: only ask when context + reflection both fail AND the page has 3+ ambiguous targets. If page has 1–2 obvious targets, skip the question and proceed.
  4. Upgraded question format: bare element names ("侧导航？标题？卡片？") are now a VIOLATION. Every option must = UI element + visual animation description in everyday language ("菜单项切换时向右轻滑入场" / "数字从 0 滚动到真实值" / "表面流光扫过").
  5. Key test: "帮我实现dashboard的点击动效" on a page with only one card grid → should NOT ask, should directly animate the cards. Only asks if page has sidebar + cards + table + header all equally click-able.

- **2026-05-26 / path notification + scene self-check (v0.2.2)**:
  1. User reported: skill chose direct CSS path (Phase 0a) for a dashboard card hover effect without telling the user it wasn't using ReactBits. User had no visibility into the decision.
  2. User reported: skill wrote `animation: border-rotate 3s linear infinite` (conic-gradient rotating border) for a dashboard page — a continuous infinite loop that directly violates DASHBOARD scene rules. Skill only realized the mistake after user pointed it out and forced re-read of SKILL.md.
  3. Root cause #1: Phase 0a/0b had no output notification template. User can't tell which path was taken. Fixed: added mandatory `📋 路径 + 原因 + 场景` notification for ALL paths (Phase 0a, 0b, and Phase 4 for both ReactBits component and direct CSS).
  4. Root cause #2: Scene rules only existed in Phase 2 (component filtering). Code written in Phase 0a or Phase 4 wiring was never checked against scene constraints. The `infinite` keyword is literally on the DASHBOARD reject list, but there was no enforcement mechanism during code generation. Fixed: added LOCKED #7 — **scene compliance applies to ALL output**, with an explicit pre-delivery self-check checklist (scan for `infinite`, large transforms, continuous loops without user trigger, durations > 2s).
  5. Key principle: "fix violations before outputting, don't output then apologize." The user should NEVER see code that violates scene rules — that shifts the enforcement burden to the user, which is unacceptable.

When you discover a new gap during a real run, append here, then patch the relevant Phase / LOCKED rule above.

---

## Verification & success criteria

A run is successful when ALL of:

1. The installed component renders without runtime errors on the dev server
2. The variant matches project's actual stack (TS project gets TS variant)
3. No heavy dep was silently installed
4. `spark-output/profile/motion-apply.md` was created or updated
5. The user can reverse the decision in 1 message ("换成 X" or "我不喜欢这个")

When E2E testing this skill, the orthogonal matrix:
- Category (text-animations / animations / backgrounds / components) × 4
- Variant (JS / TS) × 2
- Style (CSS / TW) × 2
- Input granularity (precise term / fuzzy tonality / minimal one-liner / contradictory) × 4

= 64 cells. Sample at least one cell per dimension corner; full coverage for v0.1 release.

---

## Companion Skill: motion-plan

This skill handles **component selection + installation**. For **animation design principles** (timing, easing, personality, choreography), defer to the `motion-plan` skill.

**Simultaneous activation priority**: When a single user message could trigger both skills (e.g. "给 dashboard 加个有质感的入场动画"), this skill (motion-apply) runs FIRST — it owns selection + installation. motion-plan activates AFTER if the user then asks to tune timing/feel. Rationale: you can't tune what isn't installed yet. If motion-plan has already set a Personality in the profile, this skill reads it from `spark-output/profile/motion-apply.md` and factors it into component selection — no live cross-skill call needed.

| After this skill... | motion-plan provides... |
|---------------------|--------------------------|
| Installs a component | Duration/easing/stagger tuning parameters |
| Detects scene = DASHBOARD | Corporate personality rules (200-400ms, 0-3% overshoot) |
| Detects scene = LANDING | Premium or Energetic personality parameters |
| User says "feels wrong" | Troubleshooting diagnosis (robotic? too slow? flat?) |
| Writes Phase 0a CSS | Quality checklist validation (3 layers? easing correct? 1/3 rule?) |

**Handoff triggers** (activate motion-plan after this skill completes):
- User asks to tune duration/timing/easing of an installed component
- User says the animation "feels off" or "太快/太慢/太闪"
- Multi-element choreography needed (stagger budget, counter-motion)
- Establishing project-wide motion personality for the first time

**Post-install prop adjustment (responsibility clarification):**
When the user complains about an already-installed component's feel, the flow is:
1. motion-plan **diagnoses** (e.g. "too slow → reduce duration from 800ms to 400ms; add secondary shadow")
2. This skill (motion-apply) **applies the fix** — it owns the component's JSX/props, so it edits the actual code
3. If the diagnosis says "wrong component entirely" → this skill runs Phase 2-4 again to swap

In other words: motion-plan never touches the user's code directly. It only outputs design parameters. This skill translates those parameters into prop changes on the installed ReactBits component (or CSS changes for Phase 0a output).

**Motion Personality → Profile sync**: If motion-plan defines a Personality (Playful/Premium/Corporate/Energetic), this skill stores it in `spark-output/profile/motion-apply.md` under `tone-signals` and uses it for all future component selections in that project.

---

## Related references (in this skill)

- `references/visual-index.md` — **auto-generated** component catalog (130 components, OSS-asserted) with names, slugs, install aliases, live demo URLs, engine, heavy-flag, peer-deps. Regenerate via the crawler — never hand-edit individual rows.
- `references/visual-index-handcurated.json` — hand-curated tone / one-line visual / mass-culture analogy fields keyed by slug. **This is where the AI-value-add lives** — the crawler merges these into `visual-index.md` on each run. Edit this file to teach the skill new components or refine descriptions.
- `references/non-react-alternatives.md` — non-React library recommendations (GSAP / Motion One / anime.js / Lottie / Three.js / OGL) with framework-native solutions (Vue Transition, Svelte transition:, Angular animations), decision table, and code snippets. Used by Phase 0b.
- `references/decision-tree.md` — keyword → candidate mapping for Phase 1 / Phase 3
- `references/dependencies.md` — peer dep matrix per component (engine families + bundle sizes)
- `references/stack-variants.md` — variant resolution rules and edge cases
- `scripts/crawl_catalog.py` — Python crawler (real implementation). Pulls Categories.js + per-component TS source from the upstream GitHub repo, runs OSS assertions, merges hand-curated fields, regenerates `visual-index.md`.
- `scripts/crawl-catalog.sh` — thin bash wrapper around the Python crawler (kept for the original `.sh` reference path).

### Crawler usage

```bash
# from skill root (~/spark-output/profile/skills/motion-apply/)
python3 scripts/crawl_catalog.py                     # full refresh (≈ 130 HTTP requests, 30-60s)
python3 scripts/crawl_catalog.py --category text-animations
python3 scripts/crawl_catalog.py --dry-run --limit 5 # smoke test, no writes
python3 scripts/crawl_catalog.py --no-source         # fast (skip per-component source fetch — engine column will be `?`)
```

The crawler is idempotent. It backs up the existing `visual-index.md` to `visual-index.md.bak.<timestamp>` before overwriting. Failed records (any OSS assertion failure or 404) go to `.crawl-quarantine.json` and are listed in a "Quarantined" section at the bottom of the index.

When upstream adds new components → re-run the crawler. When you want to author/refine `tone/visual/analogy` for a component → edit `visual-index-handcurated.json` and re-run.

## Cross-platform notes

This skill is portable to Codex CLI (`~/.codex/skills/motion-apply/`). The only QoderWork-specific dependency is `AskUserQuestion` in Phase 3. On Codex, replace with: print the options as a numbered Markdown list and prompt the user to reply with a number.

---

## 质量规范

> 本章节是 Skill 完成度的**高层判定标准**，与上方 Hard constraints (LOCKED #1-7) / Phase X 内部执行级约束互补。LOCKED 是"绝对不能做的事"，本章节是"做对了没有"。

### 🚫 红线规则（违反即任务失败，无降级空间）

直接继承原 LOCKED #1–#7（不能被任何用户授权覆盖）：

1. **不复制 React Bits 组件源码**——只能通过 `npx shadcn@latest add @react-bits/<name>-<variant>` 安装。MIT + Commons Clause 禁止再分发。
2. **不编造组件名 / URL**——拿不准就读 `references/visual-index.md` 或 `https://reactbits.dev/`，未知名直接告诉用户停手。
3. **只服务 OSS**——`pro.reactbits.dev` / `@react-bits-pro/` 是付费独立产品，直接拒并重定向。
4. **每轮视觉澄清不超过 3 个候选**——超过就回去重新嗅探收窄。
5. **重 peer-deps 必须显式确认**——`three` / `ogl` / `@react-three/fiber` / >500KB 包不得静默安装；引擎共存（如 motion + gsap 同存）必须告警并给三选项。
6. **不破坏性编辑用户已有组件**——按 React Bits registry 实际落点放（通常 `src/components/<Name>.tsx`），不假设 `src/components/ui/`。
7. **场景合规自检（CRITICAL）**——所有输出（Phase 0a 直写 CSS / Phase 0b 库推荐 / Phase 4 组件 + props / 任何配套代码）都要过 DASHBOARD 红线扫描：禁 `animation: ... infinite` / 禁持续 `@keyframes` 无用户触发门 / 禁入场动效 > 2s / 禁 `translate > 20px` / `scale > 1.05` / `rotate > 5deg`。违反必须**输出前修掉，不允许"先输出再道歉"**。

附加套件级红线：

8. **双通道输出**必须符合 chain-protocol §2.1 Step 1→6 顺序（先写盘 → 自检行 → 渲染 → marker → handoff → 刷新面板）。
9. **PATH DECISION NOTIFICATION 必出**——每次执行（不管 Phase 0a / 0b / 4）都要在写代码前输出 `📋 路径 + 原因 + 场景` 三行。
10. **链式优先**——检测到 `spark-output/context/motion-plan.json` 时**必须**用 motion-plan 的 Personality + element_specs 作为 prop overrides 基准，不得回退用 React Bits 组件默认值。

### ⚠️ 反模式（常见错误，需主动规避）

- ❌ 没读 motion-plan 就直接进 Phase 0 嗅探（违反链式优先；浪费 Phase 2 工夫）
- ❌ "点击动效"→ 默认映射 ClickSpark（违反 trigger ≠ visual outcome 原则；必须先问视觉结果）
- ❌ DASHBOARD 项目装 SplitText / Hyperspeed 这类 landing-only 组件（违反 red line #6 场景过滤）
- ❌ 装组件后用默认 props 不调（违反 scene-aware prop tuning：DASHBOARD 必须把 BlurText blur 从 10px 压到 3px、y 从 50 压到 8）
- ❌ 一次问 3 个以上候选 / 一个问题里塞 4 个选项（违反 anti-overload）
- ❌ 用户问 "为啥不用 ReactBits" 时支吾——必须每次都输出 PATH DECISION NOTIFICATION 提前说清楚
- ❌ 写完代码不跑 LOCKED #7 自检就交付
- ❌ 在 IDE 没有 `spark-output/profile/` 目录时不创建直接写 profile 失败
- ❌ React Bits Pro 请求被识别后还偷偷尝试 OSS 替代（应该直接拒绝 + 重定向）
- ❌ Re-enter 同一 phase 无新信息（违反 never-loop guarantee）

### ✅ 质量标准（通过条件，全部满足才算交付）

**内容完整性**：
- `framework` 已正确探测（package.json 实测）
- `scene` 已确定（链式 / 嗅探 / 用户确认任一来源都行，但必须有 source 字段）
- `personality_applied.source` 显式标注是 `motion-plan-link` 还是 `sniff-fallback`
- 每个 `target` 元素都有 `path_decisions` 决策记录（不能"装完不解释为啥这条路"）

**实施完整性**：
- 所有 `installed_components[]` 的 prop_overrides 都已按 scene 调整（不是裸默认值）
- 所有 `css_snippets[]` 都过了 scene_compliance 自检（`scene_compliance_passed: true`）
- 重依赖（three / ogl / gsap）安装前有用户确认痕迹
- 安装失败的 fallback 已走（不能"装失败就放弃"）
- 项目 `spark-output/profile/motion-apply.md` 已写入（含 stack / scene / tonality / history / preferences）

**链路接入正确性**：
- `spark-output/context/motion-apply.json` 文件已写入且 schema 符合 frontmatter 定义
- chat marker 含 `ref="spark-output/context/motion-apply.json"` 属性
- 下游 `/设计走查` 调用时能正确读取本 Skill 上下文（验证：check Phase 0 嗅探日志含 "检测到动效开发上下文"）
- 已输出符合 chain-protocol 的 Handoff（推荐 `/设计走查` 作为下一步，附 emoji ✨）
- `spark-output/dashboard.html` 已按 Avatar SKILL.md §更新链路面板 流程刷新
