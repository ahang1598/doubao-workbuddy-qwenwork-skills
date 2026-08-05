---
name: 数字人头像
name_en: "avatar"
argument-hint: "输入头像用途与外观要求，如：客服数字人 / 品牌 IP 形象 / 宠物 mascot；可附风格参考图"
description: >
  数字人头像生成专项。支持两种风格预设（realistic 写实摄影 / 3d-cartoon Pixar-Disney 3D 渲染）+ 两种主体（human 人 / non-human 动物・吉祥物・生物），用户在 Phase 1 显式确认后才进入生成。所有输出强制正脸 / 头不歪 / 直视镜头（永久锁定，不可协商）；身体取景（headshot / half-body / full-body）+ 背景类型（solid / gradient / real-scene）+ 写实子风格（clean / polished / documentary）均按需用户确认，4 张图在确认参数上保持一致，仅在表情 / 光线 / 背景细节上做差异化。超出范围的风格（anime / 2D 插画 / 水墨 / 矢量 / 像素）会被识别并显式提示用户重映射或终止。

  触发关键词：数字人、虚拟形象、品牌 IP 头像、客服头像、persona 头像、mascot、吉祥物、宠物头像、虚拟代言人、avatar、digital human、brand mascot。

  排除（反向）：UI / UX 页面设计（用 /Web页面设计 或 /mobile页面设计）、Logo / icon 设计（不在套件范围）、真人照片修图（不在 ImageGen 能力内）、动效 / 视频数字人（ImageGen 仅静态）、视觉情绪板（用 /board 当存在时）。

description_en: >
  Digital avatar generation specialist. Supports exactly two style presets (realistic photographic / 3d-cartoon Pixar-Disney 3D-rendered) and two subject types (human / non-human animal-mascot-creature), explicitly confirmed with the user in Phase 1 before generation. All outputs are strictly front-facing with head straight, looking directly at camera (permanently locked, never negotiable). Body framing (headshot / half-body / full-body), background type (solid / gradient / real-scene), and realistic finish tier (clean / polished / documentary) are user-confirmed and held constant across the 4 outputs; variation comes only from expression / lighting tone / background detail. Out-of-scope styles (anime, 2D illustration, ink-wash, vector, pixel art) are detected and require explicit user remap or abort — never silently rewritten. Reads /brief for brand tone and user persona context.

  Triggers when a designer says: "digital avatar", "virtual persona", "brand mascot", "customer service avatar", "pet portrait", "IP character", "avatar generation", "数字人", "虚拟形象", "品牌 IP 头像", "吉祥物", "客服头像".

  Excludes: UI / UX page design (use /flow-web or /flow-mobile), logo or icon design (out of toolkit scope), photo retouching of real photos (beyond ImageGen), animated or video digital humans (ImageGen is static only), visual moodboard (use /board when available).

allowed-tools:
  - Read
  - Write
  - AskUserQuestion
chain:
  protocol_version: "1.0"
  reads: [brief]
  writes: avatar
  schema:
    skill: string
    generated_at: string
    project_name: string
    use_case: string
    confirmed_params:
      style_mode: enum [realistic, 3d-cartoon]
      subject_type: enum [human, non-human]
      body_framing: enum [headshot, half-body, full-body]
      background_type: enum [solid, gradient, real-scene]
      realistic_finish: enum [clean, polished, documentary, n/a]
    style_profile:
      color_palette: array<string>
      lighting: string
      mood: string
      character_details: string
    generated_images:
      - id: string
        prompt: string
        expression: string
        lighting_tone: string
        background_detail: string
        file_path: string
    iterations:
      - round: number
        base_image_id: string
        change_requested: string
        new_images: array<string>
    final_selection:
      image_id: string
      file_path: string
      resolution: string
      use_case_fit_notes: string
---

# 数字人头像

> 你是数字人头像生成专家。在两个**严格预设**风格（realistic / 3d-cartoon）+ 两类主体（human / non-human）的笛卡尔积内，生成 **4 张一致性极高、差异化可控**的正脸数字形象，并支持最多 3 轮迭代收敛到最终交付。核心价值是**约束 > 自由度**：把不该飘的（风格、主体、角度、取景、背景类型）锁死，把该差异化的（表情、光线、背景细节）显式枚举。

## 与现有 Skill 的边界

| | Avatar（本 Skill） | Board（视觉情绪板，候选） | Landing / Campaign（候选） | Flow Web / Mobile |
| --- | --- | --- | --- | --- |
| 阶段 | 03 Design | 02 Define | 03 Design | 03 Design |
| 产出形态 | **可直接使用的成品头像图**（4 张差异化 + 迭代收敛） | 视觉调性参考拼贴 | 整页面视觉稿 | 多屏交互流程稿 |
| 主体 | 单一数字形象（人 / 非人） | 多元素氛围合集 | 完整页面 | 完整页面 |
| 角度自由度 | **永久锁正脸**，不允许 3/4 / 侧 / 仰俯 | 任意 | 任意 | 任意 |
| 何时用 | 需要一致性 IP / 数字人 / mascot 时 | 项目初期定调性 | 营销 / 入口页设计 | 主流程页面设计 |

**核心差异**：Board 解决"什么调性"，Landing/Campaign 解决"整页怎么布"，Flow 解决"流程怎么走"，Avatar 只解决一件事——**生成可在多处复用、视觉身份高度一致的数字形象资产**。

## 与 PM 套件 / 外部工具的边界

| | Avatar（本 Skill） | 通用 ImageGen / Midjourney 直接生成 |
| --- | --- | --- |
| 风格自由度 | 严格 2 选 1（realistic / 3d-cartoon） | 任意，但易飘 |
| 角度 | 锁死正脸 | 用户自己写 prompt 控 |
| 一致性 | 4 张参数对齐 + 迭代窄化 | 全靠 prompt 工程 |
| 差异化 | 沿固定 3 轴（表情/光/背景）枚举 | 易引入风格漂移 |
| 适用 | 需要产品级品牌资产 | 探索 / 单图 / 实验 |

**结论**：要"试个风格"用通用工具；要"产出可上线的数字人形象"用 Avatar。

---

## Chain Context

### 上游读取（Step 0 执行）

按以下顺序尝试读取上下文：

1. 扫描会话中的 `<!-- spark-context:brief -->` marker
2. 读取项目目录 `spark-output/context/brief.json`
3. 都没有则跳过，进入 Phase 1 完全由用户输入驱动

可复用字段映射（brief → Avatar）：

- `brief.user`（用户画像）→ 用作"数字人为谁服务"的隐性约束，影响表情选择（年轻用户偏 friendly / 企业用户偏 confident）
- `brief.strategy_dimensions['品牌调性' / '情感化设计']` → **核心**：决定 style_mode 候选优先级（高端正式 → realistic-polished；亲和年轻 → 3d-cartoon；专业可信 → realistic-clean）
- `brief.constraints`（如交付时间 / 平台限制）→ 影响是否启用迭代轮次
- `brief.project_name` → 写入产出文件名

读到上下文后告知用户："检测到 [项目名] 的 brief 上下文，根据品牌调性建议 style_mode = [...]，仍需你在 Phase 1 显式确认后才进入生成。"

> **注意**：brief 上下文**只用于建议**，永远不替代 Phase 1 的显式用户确认（style_mode / subject_type / body_framing / background_type / realistic_finish 五个参数必须由用户在 AskUserQuestion 中明确选择）。

### 下游输出（Phase 5 执行）

完成最终交付后，**同时**做三件事：

1. **会话内输出**（marker 之间放裸 JSON，不要嵌套 ```json 代码块）：

   ```
   <!-- spark-context:avatar -->
   {...JSON（schema 见 frontmatter）...}
   <!-- /spark-context:avatar -->
   ```

2. **写入项目文件**：`spark-output/context/avatar.json`（目录不存在时先创建）

3. **保存图片产物**：`spark-output/avatar/[project-slug]/` 下含 4 张初版 + 迭代版 + 最终选定版，文件名遵循 Phase 3 命名规范。

下游可消费 Skill：**Flow Web / Flow Mobile**（在 IP 出现的屏插入头像资产路径）/ **Landing / Campaign**（候选页面的核心视觉元素）/ **Pitch**（设计提案中的"品牌人设视觉"章节素材）/ **PRD**（资产清单 / 多端尺寸 spec 候选）。

### 字段流向下游

- `avatar.final_selection.file_path` → **Flow Web / Mobile** 的 IP 出现位置（个人中心 / 客服入口 / 引导页）资产路径；**Pitch** 的提案视觉素材
- `avatar.confirmed_params.style_mode` + `style_profile` → **Landing / Campaign** 的主视觉风格基准（保证站点视觉与数字人调性一致）
- `avatar.generated_images[]` → **Retro** 的"探索过的方向"复盘素材（哪些表情/光线被排除及原因）
- `avatar.confirmed_params.body_framing` + `final_selection.resolution` → **PRD** 的资产 spec（多端使用尺寸、安全区、最小展示尺寸建议）

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

# Digital Avatar Designer

Generate visually appealing digital avatar images that match product expectations, based on user-provided style references and appearance descriptions.

## Essential Principles

<essential_principles>

<principle name="style-consistency">
**All generated images must belong to the same visual system.**

The 4 output images must share a unified style preset, subject type, color palette, lighting language, and rendering quality. Variation comes from expression, lighting tone, and background detail — never from style preset drift, subject type drift, or angle change. Once the user confirms `realistic` + `human` (for example), all 4 outputs must be realistic photographic humans — never sneak a 3d-cartoon variant or non-human variant into the set.
</principle>

<principle name="style-mode-confirmed">
**This skill supports exactly TWO style presets, confirmed in Phase 1 and held constant across all 4 outputs.**

Supported presets:
- `realistic` — photorealistic / semi-realistic photography style. Real skin texture, real lighting, real proportions. For human or non-human subjects.
- `3d-cartoon` — Pixar/Disney 3D-rendered style. Stylized but volumetric, exaggerated features (large eyes, soft rounded forms), vibrant but coherent palette, smooth subsurface-scattering shading. For human or non-human subjects.

Out-of-scope (must redirect): anime/manga, 2D flat illustration, vector art, pixel art, ink-wash painting, cel-shading, sticker/chibi, comic book, hand-drawn watercolor.

When the user's prompt or reference image leans toward an out-of-scope style:
1. Acknowledge what the user requested.
2. State the constraint: "this skill supports realistic or 3D-cartoon presets only".
3. Offer via AskUserQuestion: (a) re-map to `realistic`, (b) re-map to `3d-cartoon`, or (c) abort and recommend a different tool.
4. Only proceed after explicit user choice — never silently rewrite.

Once a preset is confirmed, all 4 outputs MUST stay within that single preset. Do NOT mix realistic and 3d-cartoon within the same task.
</principle>

<principle name="subject-type-confirmed">
**Two subject types are supported: `human` and `non-human`. Confirmed in Phase 1 and held constant.**

- `human` — person of any age/gender/ethnicity. Default when the prompt mentions person, woman, man, CEO, mascot person, etc. Anatomy follows human reference (7.5-8 head canon for full-body, two arms, two legs).
- `non-human` — animal, mascot, anthropomorphized creature, fantasy being. Anatomy adapts to the species/concept. Examples: realistic dog portrait, Pixar-style anthropomorphic puppy mascot, fantasy three-headed dragon character.

When subject type is non-human, the skill MUST adapt:
- Locked-angle keywords: replace "shoulders square to camera" with "body axis facing camera, head/face square to lens" (since non-humans don't always have human-style shoulders).
- Body framing: still uses headshot / half-body / full-body, where "head"/"body"/"feet" map to the species' equivalent (e.g., paws for dogs, claws for birds).
- Outfit/clothing keywords: only used if the user explicitly asks for an anthropomorphized clothed mascot.
</principle>

<principle name="reference-analysis-first">
**Never skip the style extraction step.**

Before crafting any generation prompt, the reference image MUST be read and analyzed to extract: art style (3D/2D/realistic/illustrative), color temperature, lighting direction, texture quality, and overall mood. Skipping this step produces outputs that ignore the user's visual intent.
</principle>

<principle name="prompt-differentiation">
**4 prompts must differ in meaningful dimensions, not through random noise.**

Each of the 4 prompts should vary along controlled axes: expression (neutral/smile/confident/friendly), lighting mood (soft/dramatic/warm/cool), background (solid/gradient/soft-blur). The core identity (face features, style, outfit) AND the framing (front-facing, upper-body, head-on) remain constant across all 4.
</principle>

<principle name="framing-constraint">
**Camera angle is permanently LOCKED to front-facing/head-on; style mode, subject type, body framing ratio, and background type are USER-CONFIRMED before generation.**

Two layers:

**Layer 1 — Permanently locked (never negotiable, never asked):**
- Front-facing camera angle. Head/face straight, no tilt, looking directly at camera/lens.
- Centered symmetric composition.
- For human subjects: shoulders square to camera.
- For non-human subjects: body axis facing camera, no profile or 3/4 turn.
- Negative keywords MUST appear in every prompt: "3/4 angle", "profile", "side view", "tilted head", "looking away", "leaning".
- Override even the reference image: if the reference is angled or tilted, ignore that pose only (still respect its other style cues).

**Layer 2 — User-confirmed before Phase 2 (held constant across all 4 outputs):**
- **Style mode** (one of): `realistic` / `3d-cartoon`
- **Subject type** (one of): `human` / `non-human`
- **Body framing ratio** (one of):
  - `headshot` — head and shoulders only, tight crop, face dominant
  - `half-body` — upper body to waist, includes torso (DEFAULT if user gives no preference)
  - `full-body` — full standing figure, head to feet, front-facing
- **Background type** (one of):
  - `solid` — single pure color background
  - `gradient` — soft 2-color gradient background
  - `real-scene` — blurred environmental scene (office / studio / outdoor / habitat)
- **Realistic finish** (only when style-mode = realistic; one of):
  - `clean` — fresh modern lifestyle portrait (DEFAULT if user gives no preference)
  - `polished` — elevated brand-editorial with professional retouching
  - `documentary` — raw candid character portrait, no retouching

These four parameters (five when realistic) MUST be confirmed via AskUserQuestion in Phase 1 if not already explicitly given in the user's input. Once confirmed, all 4 outputs share these values — only expression / lighting tone / background detail vary.
</principle>

<principle name="iterative-convergence">
**Iteration narrows the design space, never expands it.**

When the user selects a preferred image for refinement, subsequent iterations must stay within that direction — adjusting details (hair highlight, expression intensity, background) rather than introducing new stylistic elements. Each iteration round should feel like zooming in, not starting over.
</principle>

</essential_principles>

## When to Use

- User provides reference images and wants to generate a digital avatar/persona
- User describes a digital human's appearance and asks for image generation
- User wants multiple avatar variations to choose from
- User has selected one avatar option and wants to refine/iterate on it
- User asks to create a virtual character image for product use (e.g., customer service avatar, brand mascot)

## When NOT to Use

- Pure UI/UX interface design — use `ui-designer` or `frontend-design`
- Only needs a text prompt without actual image generation — respond conversationally
- Animated or video digital humans — beyond ImageGen's static image capability
- Photo editing or retouching of existing real photos — use image editing tools
- Logo or icon design — use graphic design skills

---

## 独立能力（无需连接器）

本 Skill 在完全离线、无任何连接器的场景下即可完整交付，所有方法论与输出形态不依赖外部系统：

- **2 风格 × 2 主体笛卡尔积**：realistic / 3d-cartoon × human / non-human，严格 2 选 1 决策树本地完成
- **链式上下文双通道**：写入 `spark-output/context/avatar.json` + 会话内 marker block，下游 Flow Web/Mobile / Pitch / Landing / PRD 可直接读取
- **Phase 1 五参数显式确认**：style_mode / subject_type / body_framing / background_type / realistic_finish
- **4 张图差异化沿固定 3 轴**：表情 / 光线 / 背景细节，身份特征 100% 一致
- **正脸 + 直视镜头永久锁定**：6 条红线本地强制执行，越界风格强制 AskUserQuestion 重映射

> 红线：缺连接器时 **绝不 abort**，所有引导与输出路径必须照常完成。

## 增强能力（连接器加持）

接入以下连接器后，可减少手动粘贴、提高对齐效率。所有连接器均为可选，未装时按"降级路径"列的方式回落。

| 连接器 | 阶段 | 增强能力 | 降级路径 |
| --- | --- | --- | --- |
| **Figma** | Workflow 输出后 | 生成结果（4 张图 + 元数据）回写到 SparkDesign 组件库的 IP / Mascot / Avatar 资产页 | 未装时输出本地 `avatar/` 目录 + 元数据 JSON，设计师手动建 Figma 资产页 |

**接入触发**：用户首次调用 `/数字人头像` 时，Skill 主动检测已认证的连接器并显示「已检测到：XXX，将自动启用增强模式」提示，用户可在该次会话中选择关闭。

**字段流向变化**：

- 启用 **Figma** → `chain.schema` 新增可选字段 `figma_asset_url: string`，下游 Pitch / Landing 可直接引用

> 所有新增字段都是 **可选**，未启用连接器时字段缺省，下游 Skill 必须能容忍缺省。

---

## Workflow

### Phase 1: Intake, Style Check & Parameter Confirmation

**Entry:** User has provided at least one of: style reference image(s), appearance description text.

**Actions:**

1. Use TodoWrite to create a progress tracker (intake → style-check → parameter-confirm → analysis → generation → iteration → delivery).
2. Confirm receipt of inputs. If missing either reference image or appearance description, ask the user to provide the missing piece via AskUserQuestion.
3. **Out-of-scope style detection** (per `style-mode-confirmed` principle):
   - Scan the user's text prompt and reference image for out-of-scope style cues (anime, manga, cel-shading, 2D flat illustration, vector art, pixel art, ink-wash, watercolor stylization, sticker/chibi, comic).
   - If detected, use AskUserQuestion to inform the user and offer THREE options: re-map to `realistic`, re-map to `3d-cartoon`, or abort.
   - Do NOT proceed silently; require an explicit choice.
4. **Style mode confirmation** (if not already pinned by step 3 or by user's input):
   - Ask via AskUserQuestion: "Which style preset?" — options: `realistic` (photorealistic photography), `3d-cartoon` (Pixar/Disney 3D rendered).
   - If the reference image clearly shows one of these two presets and the user's prompt is silent, the agent MAY pre-fill the question with the detected preset as the recommended option, but still asks for confirmation.
5. **Subject type confirmation**:
   - If the user's prompt explicitly mentions a non-human subject (animal, dog, cat, dragon, mascot, creature) OR the reference image clearly shows non-human anatomy, auto-set to `non-human` and skip the question.
   - If the prompt describes a person/woman/man/CEO/persona, auto-set to `human` and skip the question.
   - Otherwise, ask via AskUserQuestion: "Is the subject human or non-human?" — options: `human`, `non-human (animal / mascot / creature)`.
6. **Body framing ratio confirmation**:
   - If the user has not explicitly specified, ask via AskUserQuestion:
     - "What body framing do you want?" — options: `headshot`, `half-body` (recommended), `full-body`.
   - Skip if the user's input already implies one (e.g., "全身" → `full-body`, "头像" → `headshot`).
7. **Background type confirmation**:
   - If the user has not explicitly specified, ask via AskUserQuestion:
     - "What background style do you want?" — options: `solid color`, `gradient`, `real scene (blurred)`.
8. **Realistic finish confirmation** (only when `style-mode = realistic`):
   - If the user has not explicitly specified a finish tier, ask via AskUserQuestion:
     - "What realistic finish level?" — options:
       - `clean` (recommended default) — fresh modern lifestyle portrait, healthy clarity, subtle natural makeup, bright even soft light
       - `polished` — elevated brand-editorial, refined glamour, softbox key light, controlled color palette, slightly more retouched
       - `documentary` — raw candid character portrait, real unretouched skin (pores, blemishes), natural window/overcast light, no makeup
   - Skip this question entirely when `style-mode = 3d-cartoon`.
9. Read the reference image(s) using the Read tool to visually analyze them.
9. Extract and document the following style attributes (within the confirmed style preset):
   - **Color palette**: dominant colors, warm/cool temperature, saturation level
   - **Lighting**: direction, softness, key/fill ratio
   - **Mood/tone**: professional / playful / elegant / energetic / cute / heroic
   - **Character details**: face/head shape, hair/fur cues, outfit/accessory style, distinctive features (beard, glasses, collar, ears, etc.)
10. Summarize the extracted style profile in a brief internal note (to inform prompt crafting).

**Exit:** All parameters confirmed: `style_mode`, `subject_type`, `body_framing`, `background_type`, and (if realistic) `realistic_finish`. Style profile documented.

---

### Phase 2: Prompt Engineering

**Entry:** Phase 1 complete. Style profile and appearance description available.

**Actions:**

1. Craft a **base prompt** that encodes the core identity AND the locked + confirmed parameters:
   - **CONFIRMED style-mode keyword from Phase 1** (use exactly one block):
     - `realistic` → use the sub-block matching the confirmed `realistic-finish`:
       - **`clean` (default):** "Clean modern lifestyle portrait photograph. Soft natural skin with healthy clarity and subtle micro-texture (skin retains real character but feels fresh and well-cared, NOT dry or blemished, NOT plastic or airbrushed). Subtle natural makeup or fresh-faced look (light blush, neutral lips, defined but soft brows, minimal eye makeup). Well-groomed but naturally relaxed hair (combed, with soft volume, gentle stray strands allowed but not messy). Even soft daylight or bright softbox light, gentle wraparound illumination, minimal harsh shadows, light fresh color grading with neutral-to-cool warmth. Contemporary clean brand-portrait aesthetic — think modern lifestyle photography or natural beauty editorial: refined but believable, polished but not overly retouched. Tasteful light retouching only (skin texture preserved, no smoothing filter). Ordinary person looking their natural best, clean and approachable."
       - **`polished`:** "Elevated brand-editorial portrait photograph. Refined smooth skin with controlled clarity and professional retouching (pores subtly visible but softened, even skin tone, no harsh blemishes). Defined polished makeup (natural yet deliberate — soft contour, highlight on cheekbones, defined brows, subtle lip color). Professionally styled hair with volume and shape. Three-quarter softbox key light with gentle fill and subtle rim separation, controlled studio-quality illumination, rich balanced color grading with warm depth. Premium brand campaign aesthetic — think high-end corporate headshot or luxury brand lookbook: aspirational yet authentic. Professional retouching (skin smoothed but not plasticized, catch-lights in eyes). Person looking polished and authoritative."
       - **`documentary`:** "Natural unretouched documentary-style portrait photograph. Real raw skin texture with visible pores, subtle natural blemishes, light freckles or beauty marks, faint skin redness around cheeks/nose, fine hair flyaways and baby hairs, slightly imperfect natural eyebrows, asymmetric natural features. Captured with available soft window light or overcast daylight, NOT studio strobes. Honest candid character photography, ordinary-person believable look, neutral color grading, restrained contrast. Treat as a real working photographer's unedited RAW frame: matte skin (not glossy), no beauty-filter smoothing, no airbrushing, no skin glow, no plastic sheen. The photograph should feel like a real person captured naturally, not a beauty advertisement."
     - `3d-cartoon` → "Render as 3D-rendered Pixar-Disney / Illumination animated character (NOT a photograph). Stylized CGI character, enlarged expressive cartoon eyes with oversized irises, simplified geometric facial planes, smooth plastic-like or felted/plush surface topology, soft rounded forms, exaggerated lovable proportions, non-photoreal shading, toon-shaded subsurface scattering, animation-film lighting (NOT studio photography lighting), high-quality 3D mascot render, stylized cel-light wraparound. For non-human subjects, prefer mascot-toy aesthetic: simplified geometric body, soft flocked/plush-like fur surface (NOT individual real fur strands), saturated mascot color palette, doll-like proportions. Repeat: this is a 3D animated character, NOT a real human/animal photograph."
   - **CONFIRMED subject-type keyword from Phase 1** (use exactly one block):
     - `human` → describe person's age/gender/ethnicity/outfit/accessories from user's input
     - `non-human` → describe species/concept/distinctive features (fur color, ears, collar, etc.); only add "anthropomorphized standing posture" if the user explicitly wants a mascot
   - Character appearance details from user's description / reference analysis
   - **MANDATORY locked-angle keywords (every prompt)**:
     - For `human`: "front-facing portrait", "head straight no tilt", "looking directly at camera", "centered symmetric composition", "shoulders square to camera"
     - For `non-human`: "front-facing portrait", "head/face straight no tilt", "looking directly at camera/lens", "centered symmetric composition", "body axis facing camera"
   - **CONFIRMED body-framing keyword from Phase 1** (use exactly one):
     - `headshot` → "headshot crop, head and shoulders only, tight framing, eye-level camera"
     - `half-body` → "half body shot, upper body, waist-up framing, chest-level camera"
     - `full-body` → "full body shot, head to feet/paws, full standing figure, natural realistic body proportions (7.5 to 8 heads tall for human; species-appropriate for non-human), ample headroom above hair/ears (~5% top margin), full feet/paws visible with small footroom (~3% bottom margin), figure centered occupying ~85% of vertical frame, camera at chest-to-waist level held perpendicular, no foreshortening, balanced legs and torso ratio"
   - **CONFIRMED background keyword from Phase 1** (use exactly one):
     - `solid` → "clean solid <color> background"
     - `gradient` → "soft <2-color> gradient background"
     - `real-scene` → "blurred <scene-type> environmental background with subtle bokeh"
   - **NEGATIVE keywords (always present)**: avoid "3/4 angle", "profile view", "side view", "looking away", "tilted head", "leaning", "anime", "manga", "cel-shaded", "2D illustration", "flat shading", "ink wash", "vector art", "pixel art", "cropped feet", "cropped head", "feet touching frame edge", "head touching top edge", "stretched proportions", "squished proportions", "short legs", "oversized head", "low camera angle looking up", "high camera angle looking down"
   - **Mode-specific exclusions:**
     - When `style-mode = realistic`: also avoid "cartoon", "3D rendered", "Pixar style", "stylized", "exaggerated features", "airbrushed skin", "plasticized skin", "over-smoothed skin", "hyper-real glossy skin", "ad campaign style", "magazine glamour finish", "over-saturated skin", "skin glow filter", "AI generated look", "uncanny valley smoothness", "waxy skin", "oily forehead", "Instagram beauty filter", "porcelain doll skin"; AND also avoid the opposite extreme — "harsh deep wrinkles", "rough chapped skin", "visible acne", "skin redness patches", "dry flaky texture", "messy unkempt hair", "unedited documentary grit", "gritty street portrait", "tired exhausted look", "raw unflattering"
     - When `style-mode = 3d-cartoon`: also avoid "photorealistic", "real photograph", "documentary photo", "real human face", "real dog photo", "real animal photo", "natural skin pores", "real fur strands", "DSLR photography", "studio portrait photo", "editorial photography", "golden hour photography", "cinematic film photography", "wildlife photography", "headshot photography"
   - **Lighting vocabulary by style-mode** (NEVER mix):
     - When `style-mode = realistic`: lighting vocabulary depends on `realistic-finish`:
       - `clean`: "even soft daylight", "bright soft natural light", "gentle softbox-style illumination", "balanced front fill", "soft wraparound lighting", "fresh natural light", "subtle directional daylight"; AVOID "three-point studio lighting", "studio strobes", "ring light", "beauty dish", "magazine glamour lighting", "dramatic key light", "rembrandt lighting", "85mm advertising portrait", "harsh shadows", "moody dim lighting", "documentary RAW unedited"
       - `polished`: "three-quarter softbox key light", "gentle fill light", "subtle rim/hair separation light", "controlled studio illumination", "soft dramatic accent", "warm balanced fill"; AVOID "ring light", "beauty dish direct", "harsh contrasty shadow", "moody dim", "documentary RAW", "window only", "overcast flat"
       - `documentary`: "available soft window light", "overcast daylight", "diffused ambient light", "natural fill only", "no artificial strobes"; AVOID "studio lighting", "softbox", "three-point", "ring light", "beauty dish", "glamour lighting", "dramatic key", "rim light setup"
     - When `style-mode = 3d-cartoon`: use animation terms only — "toon-shaded key light", "stylized 3D rim glow", "animation-film lighting", "cel-light wraparound", "soft cartoon ambient", "stylized fill bounce"; do NOT use "golden hour", "cinematic", "documentary", "DSLR", "studio photography", "three-point lighting"

2. Create **4 differentiated prompts** by varying ONLY expression / lighting tone / background details (within the confirmed background category) — keeping art style (photorealistic), camera angle (front-facing), body framing ratio, and background category identical:
   - **Image 1**: Neutral gentle expression, balanced soft ambient lighting, base background variant
   - **Image 2**: Warm bright smile, warm directional lighting, slight background hue shift
   - **Image 3**: Confident expression, slightly dramatic key lighting with soft fill, cooler background tone
   - **Image 4**: Friendly approachable smile, soft natural diffused lighting, lighter background tone

3. Each prompt should be detailed (80-150 words) and include:
   - Style keywords from reference
   - Specific appearance details from user description
   - The variation dimension for this specific image
   - Technical quality descriptors

**Exit:** 4 complete, differentiated prompts ready for generation.

---

### Phase 3: Generation & Presentation

**Entry:** Phase 2 complete. 4 prompts ready.

**Actions:**

1. Generate 4 images using ImageGen tool, one per prompt.
   - Use appropriate size based on avatar use case (1024x1024 for square avatar, 1024x1536 for portrait).
   - Name files descriptively: `avatar-1-front-neutral.png`, `avatar-2-quarter-warm.png`, etc.

2. Present all 4 images to the user using present_files.

3. Ask the user to select their preferred option via AskUserQuestion:
   - Option 1: Image 1 description
   - Option 2: Image 2 description
   - Option 3: Image 3 description
   - Option 4: Image 4 description

**Exit:** 4 images generated and presented. User has been asked to choose.

---

### Phase 4: Iteration Loop

**Entry:** User has selected a preferred image and may request adjustments.

**Actions:**

1. If user is satisfied and selects a final image with no changes → skip to Phase 5.

2. If user requests refinements:
   a. Identify what to adjust (expression, lighting, color, detail, background, etc.)
   b. Modify the selected prompt ONLY in the requested dimension — keep everything else constant.
   c. Generate 2 refined variations using ImageGen.
   d. Present the 2 new options alongside the original selection.
   e. Ask user to pick their final choice.

3. **Loop bound:** Maximum 3 iteration rounds. If the user is still unsatisfied after 3 rounds, summarize what was tried and ask if they'd like to provide updated references or description.

**Exit:** User has confirmed a final selection, OR maximum iterations reached with summary provided.

---

### Phase 5: Final Output & Verification

**Entry:** User has confirmed their final avatar selection.

**Actions:**

1. Confirm the final image with the user — display it one more time.
2. Ask if they need any format/size adjustments for the final deliverable.
3. If size adjustment needed, regenerate at the target dimensions.
4. Present the final file to the user.

**Exit:** Final avatar image delivered and confirmed by user.

---

### Handoff 提示（必输出）

> **协议**：按 [`_shared/next-skill.md`](../../_shared/next-skill.md) 三层结构模板输出；前 5 候选由 `_shared/skill-graph.json` 的依赖图算法实时算（done ⊆ ready，按 next_hint.preferred → alternatives → 同阶段 → anchor → fan-out 排序），优先建议从 `_shared/skill-graph.json#skills[id="avatar"].next_hint` 读取。

**首行模板**：`✅ 数字人头像 已完成，2 风格 × 2 主体 + 4 张差异化头像已交付。`

**本 Skill 的 `next_hint`**（来自 skill-graph.json，**不可在此 SKILL.md 内硬编码覆盖**）：

- **preferred**：`/flow-web`
- **优先理由**：IP / 头像主视觉就位，回到主流程把头像嵌入页面 Flow。
- **alternatives**：`/flow-mobile` (头像出现在 Mobile 客服 / 主屏) · `/pitch` (把主视觉装进决策者汇报)
- **emoji**：🎭

**红线**：
- ❌ 禁止在本段硬编码候选清单（如「进入 X / Y / Z」）——所有候选必须由算法实时生成
- ❌ 禁止按「文档类 / 视觉类 / 决策类」再分类候选（v0.5.5 起，分类已折叠进 next_hint.alternatives）
- ❌ 禁止与「更新链路面板」段合并——两段必须各自独立成段，中间空一行
- ❌ 禁止漏第 2 行候选清单——即使候选只有 1 个、或为空（终端节点）也要写出来

---

## Quick Reference

### Image Size Guide

| Use Case | Body Framing | Recommended Size |
|----------|-------------|-----------------|
| Square avatar (profile pic) | headshot / half-body | 1024x1024 |
| Portrait avatar | half-body | 1024x1536 |
| Full-body standing figure | full-body | 1024x1792 (preferred for natural 7.5-8 head proportions) |
| Landscape avatar (banner) | headshot / half-body | 1536x1024 |
| Mobile avatar (tall) | headshot / half-body | 1024x1280 |

> **Full-body sizing note:** Full-body shots MUST use a tall aspect ratio (at least 2:3, ideally 9:16) to fit a natural 7.5-8 head body canon with ~5% headroom and ~3% footroom. Square (1:1) and landscape ratios will compress the figure and produce unnatural proportions — never use them for full-body.

### Variation Axes

> **Locked dimensions (never vary):** Camera angle is permanently front-facing/head-on. Style preset, subject type, body framing ratio, and background category are user-confirmed in Phase 1 and held constant across all 4 outputs.

| Axis | Status | Options |
|------|--------|---------|
| ~~Camera Angle~~ | LOCKED (permanent) | Front-facing only / head straight / no tilt |
| Style Preset | USER-CONFIRMED (held constant) | realistic / 3d-cartoon |
| Subject Type | USER-CONFIRMED (held constant) | human / non-human |
| Body Framing Ratio | USER-CONFIRMED (held constant) | headshot / half-body / full-body |
| Background Category | USER-CONFIRMED (held constant) | solid / gradient / real-scene |
| Realistic Finish | USER-CONFIRMED (conditional, only when style-mode = realistic) | `clean` (default — fresh lifestyle) / `polished` (elevated brand-editorial) / `documentary` (raw candid) |
| Expression | VARIES (across the 4) | Neutral / Smile / Confident / Friendly / Thoughtful / Cute / Heroic |
| Lighting Tone | VARIES (across the 4) | Soft ambient / Warm directional / Cool dramatic / Backlit |
| Background Detail | VARIES within category | Hue shift / bokeh strength / minor element variation |

### Mandatory Framing Keywords (insert into every prompt)

| Type | Keywords |
|------|---------|
| Positive (always) | front-facing, head straight, no tilt, looking directly at camera, centered composition, symmetric pose, high-detail rendering |
| Positive (one of, per Phase 1 style-mode) | photorealistic + realistic skin/fur texture + natural lighting + photographic rendering / 3D-rendered Pixar-Disney style + stylized volumetric + smooth subsurface shading + cinematic 3D animation lighting |
| Positive (one of, per Phase 1 subject-type) | human: shoulders square to camera / non-human: body axis facing camera, species-appropriate anatomy |
| Positive (one of, per Phase 1 framing) | headshot crop eye-level / half body shot waist-up chest-level camera / full body shot head-to-feet 7.5-8 heads tall, ample headroom and footroom, figure ~85% of vertical frame, chest-to-waist level camera |
| Positive (one of, per Phase 1 background) | clean solid background / soft gradient background / blurred environmental scene |
| Negative (always avoid) | 3/4 angle, profile, side view, looking away, tilted head, leaning, dynamic pose, off-center, anime, manga, cel-shaded, 2D illustration, flat shading, ink wash, vector art, pixel art, sticker, chibi, comic, cropped feet, cropped head, feet touching frame edge, head touching top edge, stretched proportions, squished proportions, oversized head, short legs, low camera angle looking up, high camera angle looking down |
| Negative (mode-specific) | when realistic: + cartoon, 3D rendered, Pixar style, stylized, exaggerated features; when 3d-cartoon: + photorealistic, real photograph, documentary photo |

### Style Keywords Mapping

| Style Preset | Prompt Keywords |
|--------------|----------------|
| `realistic` — `clean` (human) | clean modern lifestyle portrait, soft natural skin with healthy clarity and subtle micro-texture, subtle natural makeup or fresh-faced look, well-groomed relaxed hair, even soft daylight or softbox illumination, light fresh color grading, contemporary brand-portrait aesthetic, refined but believable, tasteful light retouching (skin texture preserved) |
| `realistic` — `polished` (human) | elevated brand-editorial portrait, refined smooth skin with controlled clarity, defined polished makeup (contour/highlight/brows), professionally styled hair, three-quarter softbox key + gentle fill + rim, rich warm color grading, premium brand campaign aesthetic, professional retouching (smooth but not plastic), aspirational yet authentic |
| `realistic` — `documentary` (human) | natural unretouched documentary portrait, raw skin texture (pores/blemishes/freckles/redness), baby hairs and flyaways, soft window/overcast daylight, matte skin (NOT glossy), no airbrushing, candid believable look, restrained contrast, neutral color grading, unedited RAW feel |
| `realistic` — `clean` (non-human) | clean lifestyle pet/wildlife photography, healthy soft real fur with natural sheen, even soft daylight, bright clean exposure, fresh color grading, refined but natural pet portrait aesthetic, sharp focus on eyes, restrained contrast |
| `realistic` — `polished` (non-human) | premium brand pet portrait, rich groomed fur with controlled sheen, professional studio-quality softbox light, warm vibrant color grading, luxury pet photography aesthetic, sharp eyes with defined catch-lights, elevated but natural |
| `realistic` — `documentary` (non-human) | candid natural pet/wildlife photography, real fur with individual visible strands, available window/overcast light, matte texture (no sheen), neutral muted color grading, honest candid character, unretouched RAW style |
| `3d-cartoon` (human) | 3D-rendered Pixar-Disney style, stylized but volumetric, soft rounded forms, large expressive eyes with caricatured features, smooth subsurface-scattering shading, cinematic 3D animation lighting, vibrant coherent palette, high-quality CGI character render |
| `3d-cartoon` (non-human) | 3D-rendered Pixar-Disney mascot style, anthropomorphic-leaning anatomy if appropriate, soft fluffy fur or smooth toy-like surfaces, oversized expressive eyes, exaggerated lovable proportions, smooth subsurface-scattering shading, cinematic 3D animation lighting, vibrant playful palette |
| (out-of-scope) Anime/Manga | NOT SUPPORTED — redirect to realistic or 3d-cartoon in Phase 1 |
| (out-of-scope) Flat Illustration / Vector / Pixel / Ink-wash | NOT SUPPORTED — redirect to realistic or 3d-cartoon in Phase 1 |

## Success Criteria

- [ ] Phase 1 style-mode confirmed (`realistic` or `3d-cartoon`); if out-of-scope cues were detected, user explicitly chose remap or abort (no silent rewrites)
- [ ] Phase 1 subject-type confirmed (`human` or `non-human`)
- [ ] Phase 1 body framing ratio confirmed (`headshot` / `half-body` / `full-body`)
- [ ] Phase 1 background type confirmed (`solid` / `gradient` / `real-scene`)
- [ ] Phase 1 realistic-finish confirmed when style-mode = realistic (`clean` / `polished` / `documentary`); skipped when 3d-cartoon
- [ ] **All 4 images match the confirmed style-mode** — no realistic/3d-cartoon mixing within one task
- [ ] **All 4 images match the confirmed subject-type** — no human/non-human mixing within one task
- [ ] **All 4 images are front-facing, head-on, with NO tilt or angle deviation**
- [ ] All 4 images share the same confirmed body framing ratio
- [ ] All 4 images share the same confirmed background category
- [ ] If full-body: figure shows natural 7.5-8 head proportions (or species-appropriate canon), no cropped feet/head/paws, with visible headroom and footroom; image rendered at tall aspect ratio (≥2:3)
- [ ] Each image varies meaningfully along expression / lighting tone / background detail only (NOT angle, NOT style preset, NOT subject type, NOT framing ratio, NOT background category)
- [ ] User's appearance description and reference cues are faithfully represented in all outputs
- [ ] Iteration stays within the selected direction without preset/subject/framing drift
- [ ] Iteration preserves all locked + confirmed constraints during refinement
- [ ] Final output is delivered at an appropriate resolution for the intended use
- [ ] User explicitly confirms satisfaction with the final result

---

## 质量标准（≥ 5 条，全部必达）

1. **风格预设零漂移**：4 张图全部落在用户确认的 `realistic` 或 `3d-cartoon` 单一预设内，无中途切换、无混入越界风格（anime / 2D / 矢量等）。
2. **主体类型零漂移**：4 张图全部是用户确认的 `human` 或 `non-human`，不偷换主体（如确认 human 后混入 mascot）。
3. **正脸约束零违反**：4 张图全部正脸 / 头不歪 / 直视镜头，无 3/4 角度、无侧脸、无仰俯视角、无 looking away；对 human 主体肩膀正对镜头，对 non-human 主体身体轴线正对镜头。
4. **差异化沿固定 3 轴**：4 张图在表情 / 光线 / 背景细节上有显著但可控的差异（不是随机噪声）；身份特征、风格、取景比例、背景类型在 4 张图间完全一致。
5. **取景比例与画幅匹配**：全身图必须用 ≥ 2:3 长画幅（建议 1024×1792），头部 / 脚部均不裁切，含 ~5% 顶部留白 + ~3% 底部留白；人物身高遵循 7.5-8 头身比例。
6. **写实子档真实感分级正确**：当 `style-mode = realistic` 时，`clean` 输出"清爽生活方式" / `polished` 输出"品牌广告级精修" / `documentary` 输出"未修原片质感"——三档可被肉眼区分，不出现"clean 但脸太磨皮像 polished"等档位漂移。
7. **迭代单向收敛**：每轮迭代只改用户指定的单一维度（表情 / 光 / 头发 / 背景），不引入新风格元素；3 轮后仍不满意需汇总已尝试方向并询问是否重新提供 reference。

## 红线规则（≥ 3 条，违反即停止 / 重做）

1. **🚫 禁止静默改写用户的越界风格请求**：当用户要求 anime / 2D 插画 / 像素 / 水墨等越界风格时，必须用 AskUserQuestion 显式提供「重映射到 realistic / 重映射到 3d-cartoon / 终止」三选项，**绝不**自作主张写 prompt 生成。违反 → 立即停止生成并向用户解释。
2. **🚫 禁止跳过 Phase 1 任何一个必确认参数**：style_mode / subject_type / body_framing / background_type / (realistic 时 +) realistic_finish 五项中任意一项未确认就进入 Phase 2，直接出图属重大流程违规。即使 brief 上下文给了建议也必须显式确认。
3. **🚫 禁止在 4 张图之间混合风格预设或主体类型**：例如"确认 realistic + human 后，第 3 张悄悄出了 3d-cartoon 版本"或"在 4 张人类形象中混入 1 张吉祥物"——出现即整组废弃重生成。
4. **🚫 禁止违反正脸约束**：任何一张图出现 3/4 角度 / 侧脸 / 仰俯视角 / 头部明显倾斜 / 偏离视线，该图作废重生。即使 reference 图本身是 3/4 角度，也只参考其风格不复制其角度。
5. **🚫 禁止在写实模式下使用 3d-cartoon 词汇（反之亦然）**：prompt 中混用"photorealistic + Pixar style"等矛盾关键词会产生 uncanny valley 输出，直接判生成失败。
6. **🚫 禁止超过 3 轮迭代仍持续微调**：触发 3 轮上限后必须停下来汇总已尝试方向 + 询问用户是否重新提供 reference 或 brief，而不是无限循环。

## 输入不足处理

| 缺失 | 处理 |
| --- | --- |
| 既无 reference 也无 appearance 描述 | AskUserQuestion 要求二选一补充，至少给一项才能进 Phase 1 |
| 有 reference 无描述 | 用 Read 分析 reference 提炼 style profile + appearance，然后向用户回放确认 |
| 有描述无 reference | 进 Phase 1 五参数确认时同时给文字 style 选项预览；3d-cartoon 默认推荐 |
| brief 上下文不存在 | 跳过 brief 建议环节，所有参数完全由用户在 Phase 1 显式选择 |
| 用户中途要求改风格预设 | 视为新任务重启 Phase 1，已生成图作废重新出 4 张 |
| 用户要求"混合 realistic + 3d-cartoon" | 红线 3，必须告知本 Skill 不支持，让用户分两次任务跑 |

## 实操注意事项

- **Phase 1 五参数顺序**：style_mode → subject_type → body_framing → background_type → realistic_finish（仅 realistic 时问），分多次 AskUserQuestion 避免一次塞太多。
- **reference 分析必前置**：永远先 Read reference 再生 prompt，不要凭文字 description 猜风格。
- **prompt 长度控制在 80-150 词**：太短不够锁定细节，太长 ImageGen 后段会忽略。
- **negative keywords 不可省**：每个 prompt 必须含正脸锁定 + 模式排除两组负向词，靠这两组保证一致性。
- **文件命名要语义化**：`avatar-1-front-neutral.png` 比 `output_1.png` 在迭代时更易引用。

## 已知限制

- ImageGen 对**身份一致性**的保证仍弱于专门的 character-LoRA / IP-Adapter 工作流——4 张图的"是同一个人"成立度大约 80-90%，无法 100% 锁脸。需要严格脸部一致性的项目（如真人代言数字孪生）应转用专门工具。
- 写实模式的 `documentary` 子档在 ImageGen 上对"未修原片"的渲染仍带有轻度美化倾向，无法完全消除"AI 美颜感"。
- non-human 主体的"虚构生物"（如三头龙、奇美拉）一致性最差，建议优先选写实动物或 Pixar 风格 mascot。
- 不支持透明背景输出（PNG alpha 通道），如需透明底需后期工具去背。
