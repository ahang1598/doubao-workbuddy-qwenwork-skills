---
name: 动效规划
name_en: "motion-plan"
argument-hint: "输入页面/组件 + 期望调性（如：dashboard 卡片入场，沉稳克制 / 营销首页 hero，鲜活活泼）"
description: >
  动效设计原则与策略层。基于 Three Pillars（情感意图 / 视觉叙事 / 动效工艺）+ 四大 Motion Personality 档位（Playful / Premium / Corporate / Energetic）+ Duration & Easing 表 + Disney 12 原则 + 1/3 编舞规则，为项目定义一套可被工程实施直接消费的「动效规范」：Personality 锚点 + 签名缓动 + Duration palette（quick/standard/slow）+ 入场范式 + per-element specs（property / duration / easing / stagger / 迪斯尼原则）+ 编舞预算 + prefers-reduced-motion 降级。

  触发关键词：动效规划、动效规范、动效调性、motion design、motion personality、动效策略、入场动画、过渡动画、微交互、loading 状态、滚动触发、品牌动效、动效定调。

  排除（反向）：不写 React/Vue/CSS 代码（用 /动效开发）、不选 React Bits 组件（用 /动效开发）、不生成 Lottie JSON、不写 GLSL/WebGL shader、不覆盖非 Web 平台（Flutter / SwiftUI / Jetpack Compose——原则可参考但所有具体输出（CSS 语法 / cubic-bezier / prefers-reduced-motion）都是 Web 专属）。

description_en: >
  Motion design principles and strategy layer. Applies Three Pillars (emotional intent / visual narrative / motion craft) + four Motion Personality archetypes (Playful / Premium / Corporate / Energetic) + duration & easing tables + Disney 12 principles + 1/3 choreography rules to produce a complete motion spec for downstream implementation: personality anchor + signature easing + duration palette (quick/standard/slow) + entrance pattern + per-element specs (property / duration / easing / stagger / Disney principles applied) + choreography budget + prefers-reduced-motion fallback. Reads /brief for tonality, /flow-web and /flow-mobile for target pages and elements, /avatar for brand personality. Pairs with /motion-apply for implementation.

  Triggers: motion planning, motion spec, motion personality, motion design tonality, entrance animation, transition design, micro-interactions, loading state design, scroll-triggered design, brand motion identity.

  Excludes: writing React/Vue/CSS code (use /motion-apply), picking React Bits components (use /motion-apply), generating Lottie JSON, writing GLSL/WebGL shaders, non-web platforms (Flutter / SwiftUI / Jetpack Compose — principles transfer conceptually but all concrete output is web-specific).

allowed-tools:
  - Read
  - Write
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief, flow-web, flow-mobile, avatar, board]
  writes: motion-plan
  schema:
    skill: string
    generated_at: string
    project_name: string
    scope:
      target_pages: array<string>
      target_elements: array<string>
    personality:
      archetype: enum [Playful, Premium, Corporate, Energetic]
      source: enum [user-input, brief-derived, avatar-derived, flow-derived]
      rationale: string
    brand_motion_identity:
      signature_easing: string
      duration_palette:
        quick: number
        standard: number
        slow: number
      entrance_pattern: string
    element_specs:
      - element: string
        property: enum [position, scale, opacity, rotation, color, multi]
        duration_ms: number
        easing: string
        stagger_ms: number
        disney_principles: array<string>
        visual_description: string
    choreography:
      stagger_budget_ms: number
      counter_motion: string
    reduced_motion_fallback:
      strategy: string
    open_questions: array<string>
---

## 能力矩阵

本 Skill 的三种运行模式，可单独运行也可叠加。最常见路径：链式模式（从 Brief / Flow Web / Flow Mobile / Avatar 来）→ 把项目调性自动转成 Personality 锚点。

| 模式 | 触发条件 | 产出特征 |
| --- | --- | --- |
| 🟢 **独立模式** | 无前序上下文，直接调用 | Phase 1 引导用户口述目标元素 + 期望调性 → 完整动效规范 JSON |
| 🔵 **链式模式** | 检测到 `spark-output/context/brief.json` 或 `flow-web.json` / `flow-mobile.json` / `avatar.json` | 跳过基础信息追问；自动从 brief.strategy_dimensions / avatar.style_profile 推荐 Personality 候选；从 flow 提取 target_elements |
| 🟣 **增强模式** | 项目已装 SparkDesign / 已存在 `spark-output/profile/motion-apply.md` | Personality 与已有组件库主调风格对齐；输出可直接被 /动效开发 消费 |

> 三种模式产出的 schema 完全一致（`spark-output/context/motion-plan.json`），差别只在「Personality 是用户口述定 vs 从上游自动推导」。

## 输入要求

| 输入项 | 必填？ | 来源优先级 | 缺失时行为 |
| --- | --- | --- | --- |
| `project_name` | ✅ | 链式 brief / flow-web > 用户输入 | Phase 1 追问 |
| `scope.target_pages` | ✅ | 链式 flow-web.pages / flow-mobile.pages > 用户输入 | Phase 1 追问 |
| `scope.target_elements` | ✅ | 链式 flow.elements > 用户输入 | Phase 1 追问 |
| `personality.archetype` | ✅ | 链式 avatar.style_profile + brief.strategy_dimensions 自动推荐 > 用户在 AskUserQuestion 中确认 | Phase 2 必经确认（4 选 1，**永远不静默选**） |
| `brand_motion_identity.signature_easing` | ✅ | Personality archetype 默认值（Playful=ease-out-back / Premium=cubic-bezier(0.4,0,0.2,1) / Corporate=cubic-bezier(0.2,0,0,1) / Energetic=ease-out-expo） | 取 Personality 默认值 |
| `brand_motion_identity.duration_palette` | ✅ | Personality archetype 默认范围（见 Duration Table） | 取 Personality 默认值 |
| `element_specs` | ✅ | Phase 3 按 8 步检查表逐元素生成 | 至少给每个 target_element 一条 spec |
| `choreography.stagger_budget_ms` | ⭕ | 多元素时强制 ≤ 500ms | 单元素时省略 |
| `reduced_motion_fallback` | ✅ | Personality 默认降级策略（移除位移、保留 opacity、减少 50% 时长） | 取默认策略 |

**信息完整度判断**：必填项任一缺失 → 进入 Phase 1 引导追问；Personality 必须显式 AskUserQuestion 确认（即使有强烈上游信号也要让用户最终拍板，因为这是项目级一次性决策）。

## Chain Context

### 上游读取（Phase 0.5 执行）

按以下顺序尝试读取上下文，找到即提取可复用字段并告知用户已沿用：

1. 扫描会话中的 `<!-- spark-context:brief -->` / `<!-- spark-context:flow-web -->` / `<!-- spark-context:flow-mobile -->` / `<!-- spark-context:avatar -->` marker
2. 读取项目目录 `spark-output/context/brief.json` / `flow-web.json` / `flow-mobile.json` / `avatar.json`
3. 都没有则跳过，按独立模式 Phase 1 引导追问

可复用字段映射：

- `brief.strategy_dimensions['品牌调性' / '情感化设计']` → **Personality 推荐候选**（高端正式 → Premium / 亲和年轻 → Playful / 专业稳重 → Corporate / 锐意进取 → Energetic）
- `brief.user` → 影响 Personality（年轻用户偏 Playful / 企业用户偏 Corporate）
- `flow-web.pages[]` + `flow-mobile.pages[]` → `scope.target_pages`
- `flow-*.elements[]` → `scope.target_elements`（按钮 / 卡片 / 标题 / 转场）
- `avatar.style_profile.mood` + `confirmed_params.style_mode` → Personality 视觉一致性校准（realistic-polished → Premium / 3d-cartoon → Playful）
- `brief.project_name` → 写入产出文件名

读到上下文后告知用户："检测到 [项目名] 的 brief/flow/avatar 上下文，根据品牌调性建议 Personality = [...]，仍需你在 Phase 2 显式确认。"

### 下游输出（Phase 6 执行，严格按 chain-protocol §2.1 Step 1→6 顺序）

1. **先写盘**：`Write` 工具把完整 JSON 写到 `spark-output/context/motion-plan.json`（目录不存在先创建）
2. **输出自检行**：`✅ motion-plan.json 已写盘到 spark-output/context/motion-plan.json`
3. **渲染动效规范 Markdown 报告**（Personality + Duration palette + element specs 表 + 编舞图）
4. **输出紧凑 marker**：
   ```
   <!-- spark-context:motion-plan ref="spark-output/context/motion-plan.json" -->
   动效规划已保存：project=<name>，Personality=<archetype>，signature_easing=<...>，<N> 个 element_specs
   <!-- /spark-context:motion-plan -->
   ```
5. **Handoff 引导**：推荐下游 `/动效开发`（motion-apply）把规范落到代码
6. **更新链路面板**（按 Avatar SKILL.md 第 140-158 行的标准流程，独立段落告知用户）

### 字段流向下游

- `motion-plan.personality.archetype` + `brand_motion_identity` → **/动效开发**（motion-apply）的 props scene tuning 基准（Playful=overshoot 10-20% / Premium=overshoot 0% / etc.）
- `motion-plan.element_specs[].duration_ms` + `easing` → motion-apply 装组件后的 prop overrides（替代 React Bits 默认值）
- `motion-plan.choreography.stagger_budget_ms` → motion-apply 多组件编排时的总时长上限
- `motion-plan.reduced_motion_fallback` → motion-apply 写 `@media (prefers-reduced-motion: reduce)` 的具体策略
- `motion-plan.personality` → **/设计走查**（check）的「动效合规」维度判断基准（实施是否守住 Personality）

---

# Motion Design Skill

## When to Apply

Use this skill when:
- Creating UI animations (buttons, cards, modals, page transitions)
- Designing micro-interactions and feedback animations
- Building loading, success, or error states
- Animating illustrations or decorative elements
- Planning scroll-triggered or progress-based animations
- Establishing brand motion identity
- Choreographing multi-element sequences
- **Tuning animation props** after motion-apply installs a component (duration, easing, stagger)
- **Diagnosing** why an existing animation "feels wrong"

Do NOT use this skill for:
- Creating Lottie JSON files or After Effects compositions (use Lottie/AE directly)
- Writing GLSL/WebGL shaders (recommend Three.js or OGL, but shader code itself is outside this skill)
- Non-web platforms (Flutter, SwiftUI, Jetpack Compose, React Native) — the principles are conceptually similar but all concrete output (CSS syntax, cubic-bezier values, `prefers-reduced-motion`) is web-specific
- Audio/sound design for animations

**Decision tree:**
1. Does it serve a functional purpose (feedback, guidance)? → Timing rules for responsiveness
2. Does it express brand personality? → Motion Personality archetypes
3. Does it tell a story or guide attention? → Disney principles + choreography
4. Is this a complex multi-element scene? → 1/3 Rule + stagger patterns

## Companion Skill: motion-apply

This skill provides **design principles** (what makes animation good). For **component selection + installation** in React projects, defer to `motion-apply`.

**Simultaneous activation priority**: When both skills could trigger on the same message, motion-apply runs FIRST (it selects + installs). This skill activates AFTER — either when the user asks to tune, or when motion-apply explicitly hands off a timing/feel question. If this skill is the ONLY one installed, it handles everything (design + implementation via CSS/JS).

| Scenario | This skill handles | motion-apply handles |
|----------|-------------------|--------------------------|
| "加个入场动画" | Timing/easing/personality parameters | Which component + `npx shadcn add` |
| "这个动画感觉不对" | Diagnosis + fix parameters | — |
| "统一项目动效风格" | Motion Personality definition | Profile storage + future picks |
| "给按钮加反馈" | Design recipe (squash/stretch/timing) | Component if ReactBits has one; else CSS |
| Props tuning after install | Duration/easing/stagger values | — |

**Handoff protocol:**
- If motion-apply installed a component but user wants to tune feel → this skill activates
- If this skill defines a Motion Personality → motion-apply stores it in `spark-output/profile/motion-apply.md` for future picks
- If user asks for an effect and ReactBits has no matching component → this skill provides the design, then write CSS/JS directly

---

## Quick Reference: 8-Step Checklist

Before creating any animation:

1. **Emotional target?** — joy, calm, urgency, elegance
2. **Motion Personality?** — Playful, Premium, Corporate, Energetic
3. **Primary property?** — position, scale, rotation, opacity
4. **Duration?** — see duration table below
5. **Easing family?** — entrance=decelerate, exit=accelerate
6. **Hero element?** — apply staging principles
7. **Secondary + ambient layers?** — add richness
8. **1/3 rules?** — motion distance, simultaneous elements

**"Designer mode" override**: If the user already specified ALL parameters (property, distance, duration, easing, stagger), they are acting as the designer. In this case: implement exactly as specified. Do NOT run the 8-step checklist to second-guess or add unsolicited secondary/ambient layers. You MAY mention what would improve the animation (as a brief note, not a correction), but execute the user's spec first.

---

## Three Pillars (CRITICAL)

Every animation must satisfy three pillars before any technical decisions:

| Pillar | Question | Drives |
|--------|----------|--------|
| **Emotional Intent** | What should the viewer FEEL? | Easing, timing, amplitude |
| **Visual Narrative** | What's the micro-story? | Setup → Action → Resolution |
| **Motion Craft** | How do we make it believable? | Physics, secondary motion, paths |

**Three motion layers** (flat animation = missing layers):
- **Primary**: Main action the viewer follows (100% amplitude)
- **Secondary**: Supporting richness — shadows, icons shifting (30-50%)
- **Ambient**: Background life — gradients, subtle pulses (10-20%)

> Deep dive: [director/core-philosophy.md](director/core-philosophy.md)

---

## Motion Personality

Select ONE archetype per project. Apply consistently.

| Archetype | Duration | Easing | Overshoot | Keywords |
|-----------|----------|--------|-----------|----------|
| **Playful** | 150-300ms | ease-out-back | 10-20% | fun, whimsical, bouncy, cute |
| **Premium** | 350-600ms | cubic-bezier(0.4,0,0.2,1) | 0% | elegant, minimal, luxury, sophisticated |
| **Corporate** | 200-400ms | cubic-bezier(0.2,0,0,1) | 0-3% | clean, professional, business, dashboard |
| **Energetic** | 100-250ms | ease-out-expo | 15-30% | dynamic, energetic, bold, exciting |

**Default**: Corporate for UI, Playful for illustrations.

**Brand Motion Identity** — define three constants:
1. **Signature easing**: One curve for 80% of animations
2. **Duration palette**: 3 durations (quick / standard / slow)
3. **Entrance pattern**: One consistent entry style

> Deep dive: [director/motion-personality.md](director/motion-personality.md)

---

## Duration Table

| Element Type | Duration | Rationale |
|-------------|----------|-----------|
| Tooltip / micro-feedback | 80-120ms | Must feel instant |
| Button press / toggle | 120-180ms | Responsive feedback |
| Icon transition | 150-250ms | Clear state change |
| Card enter / exit | 200-350ms | Spatial awareness |
| Modal / dialog | 300-400ms | Focus shift |
| Page transition | 400-600ms | Context switch |
| Dramatic reveal | 600-1200ms | Theatrical build |

**Distance scales duration**: 100px = base. 200px = 1.3x. 400px = 1.6x.
**Enter > Exit**: Entrances 30-50% longer than exits.
**Interactive feedback**: Hover <100ms, Press <150ms, Release 200-300ms, Error shake 300-400ms.

> Deep dive: [reference/timing-easing-tables.md](reference/timing-easing-tables.md)

---

## Easing Selection

**Directional rules**:
- **Entrance** → decelerate (fast start, gentle landing): ease-out family
- **Exit** → accelerate (gentle start, fast departure): ease-in family
- **On-screen** → smooth both ends: ease-in-out family
- **Looping ambient** → seamless: sine-based ease-in-out

**Industry standards**:

| Standard | Cubic Bezier | Use For |
|----------|-------------|---------|
| Material Design 3 | (0.2, 0, 0, 1) | Default on-screen |
| MD3 Emphasized | (0.05, 0.7, 0.1, 1) | Entrances, attention |
| Apple HIG | (0.25, 0.1, 0.25, 1) | Standard iOS |
| Bounce settle | (0.175, 0.885, 0.32, 1.275) | Overshoot, playful |

**Spring parameters**: Very stiff (400+/25-30), Standard (250-350/18-24), Bouncy (150-250/10-15), Gentle (100-150/20-25).

> Deep dive: [reference/timing-easing-tables.md](reference/timing-easing-tables.md)

---

## Property Selection

| Effect Goal | Primary Property | Secondary Properties |
|-------------|------------------|---------------------|
| Entrance/Exit | position | opacity, scale |
| Emphasis/Attention | scale | rotation (subtle), opacity pulse |
| State Change | opacity, color | scale (press feedback) |
| Direction/Flow | position | rotation (follow path) |
| Loading/Progress | rotation (spinner) | scale, opacity pulse |
| Success | scale (pop) | color, rotation (checkmark draw) |
| Error/Alert | position (shake) | color, rotation (wobble) |

**Simplicity threshold**: One property = direct. Two = polished. Three+ = potentially overwhelming.
**Performance**: Prefer transform + opacity (GPU-accelerated). Avoid width/height/margin/box-shadow.

> Deep dive: [reference/property-selection.md](reference/property-selection.md)

---

## Disney Principles (UI-adapted highlights)

| Principle | UI Application |
|-----------|---------------|
| **Anticipation** | Small opposite motion 100-200ms before action (10-20% magnitude) |
| **Squash & Stretch** | Button press scale [1.2, 0.8]; skip for Premium |
| **Follow Through** | Child elements trail 50-150ms behind parent |
| **Staging** | Dim non-hero to 40-60% opacity; one action per beat |
| **Arcs** | Add 10-20px perpendicular offset at path midpoint |
| **Secondary Action** | 30-50% amplitude, 50-100ms after primary, different easing |
| **Exaggeration** | Playful 15-25%, Energetic 20-30%, Corporate 0-5%, Premium 0% |
| **Slow In/Out** | NEVER linear for spatial movement |

> Deep dive: [director/disney-principles.md](director/disney-principles.md)

---

## Choreography Essentials

**1/3 Rule (distance)**: No motion travels >1/3 screen without keyframe change.
**1/3 Rule (elements)**: Max 1/3 of elements in active motion simultaneously.

**Stagger budgets**:

| Pattern | Delay | Total Budget | Use Case |
|---------|-------|-------------|----------|
| Micro cascade | 20-40ms | <200ms | List items, grid cells |
| Standard | 50-100ms | <400ms | Cards, panels, nav |
| Dramatic | 100-200ms | <600ms | Hero sections |

**Critical**: Total stagger MUST stay under 500ms.

**Counter-motion**: Hero moves right → background drifts left at 20-30%.
**Sequence structure**: Setup 20-30% → Action 30-40% → Resolution 30-40%.

> Deep dive: [director/choreography.md](director/choreography.md)

---

## Emotion-to-Motion Map

| Emotion | Character | Easing | Duration |
|---------|-----------|--------|----------|
| Joy | Bouncy, arcs | ease-out-back | 200-400ms |
| Calm | Smooth, flowing | sine ease-in-out | 500-1000ms |
| Urgency | Sharp, fast | ease-out | 100-200ms |
| Surprise | Sudden, expanding | ease-out-expo | 150-300ms |
| Elegance | Slow, controlled | (0.4,0,0.2,1) | 400-700ms |

**Context defaults**: Dashboard=Calm+Confidence, Onboarding=Curiosity+Delight, Form success=Joy+Confidence, Error=Mild urgency.

> Deep dive: [director/emotion-mapping.md](director/emotion-mapping.md)

---

## Common Patterns

### Button Press (Playful)
Press: scale 0.95 (60ms) → Release: overshoot 1.05 (80ms) → Settle: 1.0 (120ms, spring). Secondary: shadow shrinks/grows.

### Card Entrance (Premium)
Start 20px below, opacity 0 → ease-out-cubic → shadow arrives 50ms after → content fades 100ms after. Other cards dim to 80%.

### Error Shake (Corporate)
Horizontal oscillation ±10-15px, 2-3 cycles, ease-in-out, 300-400ms. Red tint. No overshoot.

### Dashboard Load (Choreographed)
Skeletons (100ms) → Hero metric (250ms, 100ms delay) → Cards stagger (50ms/each, 200ms) → Chart draws (300ms) → Ambient pulse.

> More: [patterns/entrance-exit.md](patterns/entrance-exit.md) | [patterns/state-feedback.md](patterns/state-feedback.md) | [patterns/ambient-continuous.md](patterns/ambient-continuous.md) | [patterns/multi-element.md](patterns/multi-element.md)

---

## Context Adaptation

| Platform | Duration | Complexity |
|----------|----------|-----------|
| Desktop | 1.0x (baseline) | Full |
| Mobile | 0.8x | Reduced (1-2 properties) |
| Watch | 0.6x | Minimal |
| TV/Kiosk | 1.3x | Full |

**Content type defaults**: Financial=Corporate 250-500ms Low / Social=Playful 150-300ms Medium / Enterprise SaaS=Corporate 200-400ms Low / Gaming=Energetic 100-250ms High.

**Accessibility (prefers-reduced-motion)**: Remove spatial movement, keep opacity, remove spring, reduce duration 50%+, never auto-play.

**Performance budgets**: transform+opacity=Unlimited GPU / +color,clip-path=10-15 elements / +width,height=5-8 / box-shadow,filter=1-3.

> Deep dive: [director/context-adaptation.md](director/context-adaptation.md)

---

## Quality Rules

### CRITICAL — never break
1. **Never linear for spatial movement** (only for spinners, progress bars)
2. **Never opacity-only** for important state changes
3. **Never exceed 1/3 screen** without intermediate keyframe
4. **Always three motion layers** — primary + secondary + ambient

### HIGH — strongly follow
1. Match duration to element type table
2. Use directional easing (ease-out entrance, ease-in exit)
3. Apply Disney principles (anticipation, follow-through)
4. Maintain consistent personality across scene

> Full checklist: [reference/quality-checklist.md](reference/quality-checklist.md)

---

## Troubleshooting Quick Reference

| Problem | Fix |
|---------|-----|
| Looks robotic | Add easing curves + arc paths + stagger |
| Feels too slow | Check duration table, use ease-out |
| Feels cheap/flat | Add secondary + ambient layers |
| Too distracting | Apply 1/3 rule, reduce amplitude |
| No personality | Apply archetype consistently |

> Deep dive: [reference/troubleshooting.md](reference/troubleshooting.md)

---

## File Reference

**Philosophy** (director/): core-philosophy.md, decision-framework.md, disney-principles.md, motion-personality.md, emotion-mapping.md, choreography.md, narrative-structure.md, context-adaptation.md

**Reference** (reference/): timing-easing-tables.md, property-selection.md, troubleshooting.md, quality-checklist.md

**Patterns** (patterns/): entrance-exit.md, state-feedback.md, ambient-continuous.md, multi-element.md

---

## 质量规范

> 本章节是 Skill 完成度的**高层判定标准**，与上方 Quality Rules / 8-Step Checklist 等执行级约束互补。前者是"该怎么做"，本章节是"做对了没有"。

### 🚫 红线规则（违反即任务失败，无降级空间）

- **Personality 必须由用户在 AskUserQuestion 中显式确认**——即使有强烈上游信号（avatar / brief）也只能作为推荐候选，**绝不静默选**。这是项目级一次性决策，必须有用户拍板痕迹。
- **空间位移类动效永远不用 linear**——只有 spinner / progress bar 可以 linear。违反即不合格。
- **重要状态变化永远不只用 opacity**——必须配合其他属性（position / scale / color）。
- **不写代码 / 不选组件 / 不装库**——这些是 `/动效开发`（motion-apply）的职责，本 Skill 越界即违规。
- **双通道输出**必须符合 chain-protocol §2.1 Step 1→6 顺序（先写盘 → 自检行 → 渲染 → marker → handoff → 刷新面板），不得颠倒、不得跳过写盘。
- **跨平台越界**：所有具体输出（CSS 语法 / cubic-bezier / prefers-reduced-motion）都是 Web 专属，给 Flutter / SwiftUI / Compose 输出代码即违规（原则可口头提及但不出具体语法）。

### ⚠️ 反模式（常见错误，需主动规避）

- ❌ 未读上游就开始追问 Personality（违反"上下文优先"——brief / avatar 已经能强推荐）
- ❌ 直接给出"建议用 ease-out-back 300ms"这种参数堆砌，没有先回答 emotional intent / 哪个 personality archetype
- ❌ element_specs 只给单层主动作（primary），漏掉 secondary + ambient 两层——产出会被下游评价为"flat / cheap"
- ❌ 多元素 stagger 超过 500ms 总预算还不告警
- ❌ 把 prop overrides 直接写成代码片段塞进 motion-plan.json（应该只有数值 + 描述，代码是 motion-apply 的活）
- ❌ 8-Step Checklist 跳步——尤其跳"emotional target"和"motion personality"直奔参数

### ✅ 质量标准（通过条件，全部满足才算交付）

**内容完整性**：
- `personality.archetype` 已由用户显式确认（AskUserQuestion 选择痕迹）
- `brand_motion_identity` 三件套齐全（signature_easing + duration_palette + entrance_pattern）
- 每个 `scope.target_elements` 至少对应一条 `element_specs`，且含 visual_description（用户能想象画面，非纯参数）
- `reduced_motion_fallback.strategy` 显式给出（不是"按默认"一句话带过）

**动效规范完整性**：
- 每个 element_spec 都标注用到的 Disney 原则（最少 1 条，如 anticipation / follow-through / staging）
- 多元素场景给出 stagger_budget_ms 且 ≤ 500ms
- 三层动效（primary / secondary / ambient）至少在 hero 元素上齐全
- 8-Step Checklist 8 项都在 element_specs 推导链路里能追溯

**链路接入正确性**：
- `spark-output/context/motion-plan.json` 文件已写入且 schema 符合 frontmatter 定义
- chat marker 含 `ref="spark-output/context/motion-plan.json"` 属性
- 下游 `/动效开发` 调用时能正确读取本 Skill 上下文（验证：motion-apply Phase 0 嗅探日志含 "检测到动效规划上下文"）
- 已输出符合 chain-protocol 的 Handoff（推荐 `/动效开发` 作为下一步，附 emoji 🎬）
- `spark-output/dashboard.html` 已按 Avatar SKILL.md §更新链路面板 流程刷新
