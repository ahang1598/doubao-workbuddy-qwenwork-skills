---
name: 视觉情绪板
name_en: "board"
argument-hint: "输入产品语境与目标用户，如：为内容创作者打造 AI 灵感板工具"
description: >
  视觉情绪板（Mood Board / Design System 起点）。基于 /用户旅程 + /用户故事 + /设计简报 上游
  产出，推导 3-4 套色彩方向不同的设计方案，输出自包含 HTML（含氛围图 / 色板 / 字体 / 组件 demo
  四行结构 + 标签页切换），用户选定后生成可被 /Web页面设计 /mobile页面设计 /动效规划 /数据可视化
  消费的 design-tokens.json。

  触发关键词：视觉情绪板、情绪板、视觉情绪、mood board、设计系统起点、风格推荐、color scheme、
  设计方案推导、design tokens 起点、style definition、设计风格定义。

  排除（反向）：单屏视觉稿（用 /Web页面设计 或 /mobile页面设计）、动效规划（用 /动效规划）、
  改版前体验诊断（用 /启发评估）、向上汇报材料（用 /设计提案）。
description_en: >
  Mood Board generator (Design System starting point). Based on Journey + Stories + Brief
  upstream outputs, derives 3-4 color-direction-distinct design schemes, outputs a self-contained
  HTML (4-row structure: mood photos + color swatches + typography + UI components, with tab
  switching). After the user picks one, emits design-tokens.json consumable by /flow-web,
  /flow-mobile, /motion-plan, and /chart.

  Triggers when a designer says: "mood board", "visual mood", "design system from journey",
  "style definition", "color scheme proposal", "/board".

  Excludes: single-screen visual design (use /flow-web or /flow-mobile), motion planning
  (use /motion-plan), pre-redesign UX audit (use /audit), stakeholder pitch (use /pitch).

chain:
  protocol_version: "1.0"
  reads: [brief, journey, stories]
  writes: board
  schema:
    skill: string
    generated_at: string
    project_name: string
    selected_scheme: string
    style_keywords: array<string>
    color:
      primary: string
      secondary: string
      neutral: object
    typography:
      heading_font: string
      body_font: string
    spacing: object
    radius: object
    component:
      button: object
      input: object
      card: object
      tag: object
    touchpoints:
      - id: number
        name: string
        emotions: array<string>
        override:
          color: object

allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
  - Task
---

# 视觉情绪板

Mood Board Skill — 把 Journey / Stories / Brief 的产品语境翻译为 3-4 套可对比的视觉方案，用户选定即固化为 design-tokens，向下游设计 / 动效 / 图表 Skill 提供统一视觉语言。

## 能力矩阵

本 Skill 的三种运行模式，可单独运行也可叠加。最常见路径：链式模式（从 /用户旅程 + /用户故事 + /设计简报 来）。

| 模式 | 触发条件 | 产出特征 |
| --- | --- | --- |
| 🟢 **独立模式** | 无前序上下文，直接调用 | Phase 1/2 引导用户口述触点 + 产品语境 → 3-4 套方案 HTML |
| 🔵 **链式模式** | 检测到 `spark-output/context/brief.json` 或 `journey.json` 或 `stories.json` | 跳过 Phase 1 触点提取（直接从 journey.touchpoints 读）+ 跳过 Phase 2 行业/受众追问（从 brief 读） |
| 🟣 **增强模式** | 当前会话可用 ImageGen 工具 | 每方案 3 张 1792×1024 真实氛围图；不可用时 4 格全部用 CSS linear-gradient 兜底 |

> 三种模式下**产出形态完全一致**（双通道：`spark-output/context/board.json` + 自包含 HTML），区别仅在"提问多少 / 字段从哪里来 / 氛围图是真图还是渐变"。

## 输入要求

| 输入项 | 必填？ | 来源优先级 | 缺失时行为 |
| --- | --- | --- | --- |
| `project_name` | ✅ | 链式 brief.project_name > journey.project_name > 用户输入 | Phase 2 追问 |
| 触点列表（3-8 个） | ✅ | 链式 journey.stages[*].touchpoints > stories.stories[*].scenario > 用户输入 | Phase 1 引导 |
| `product_type` + 行业 | ✅ | 链式 brief.project_type / project_subtype > 用户输入 | Phase 2 追问 |
| 目标受众 | ✅ | 链式 brief.user > stories.persona > 用户输入 | Phase 2 追问 |
| 已有品牌约束 | ⭕ | 链式 brief.constraints（含品牌色 / 字体）> 用户输入 | 标注"未提供"，方案自由发散 |
| 风格参考 | ⭕ | 用户输入（图片 / 关键词） | 跳过，按情绪映射表自动推导 |
| 是否生成真实氛围图 | ⭕ | 工具可用性自动判断 | ImageGen 不可用时全部用 CSS gradient |

**信息完整度判断**：必填项任一缺失 → 进入对应 Phase 引导追问；仅可选项缺失 → 按映射表默认推导，HTML 内不做任何"待补充"占位。

## Chain Context

### 上游读取（Phase 0.5 执行）

**Step 1 · 扫描上下文来源**（按顺序，找到任一即读取，多个可叠加）：

- [ ] 会话内 marker：`<!-- spark-context:brief -->` / `journey` / `stories`
- [ ] 项目文件：`spark-output/context/brief.json` / `journey.json` / `stories.json`
- [ ] 都没有 → 跳过 Phase 0.5，按无上下文流程执行

**Step 2 · 字段映射 checklist**：

#### 来自 brief（最常见，对齐过设计方向的项目）

| Board 字段 | ← Brief 字段 | 处理方式 |
| --- | --- | --- |
| `project_name` | `brief.project_name` | 直接沿用 |
| 产品类型 + 行业 | `brief.project_type` + `brief.project_subtype` | 跳过 Phase 2 行业追问 |
| 目标受众 | `brief.user` | 跳过 Phase 2 受众追问 |
| 品牌约束 | `brief.constraints`（筛选含"品牌色 / 字体 / Logo / 视觉规范"等关键词） | 作为 Phase 3 的硬约束，方案必须遵守 |
| 风格倾向（候选） | `brief.style`（chalk / parchment / noir 等模板风格） | 作为方案 A 的色彩起点参考 |
| 设计标准（定性） | `brief.design_criteria.qualitative` | 作为方案命名 / 描述的语气基线 |

#### 来自 journey（最强信号，触点情绪直接驱动方案推导）

| Board 字段 | ← Journey 字段 | 处理方式 |
| --- | --- | --- |
| 触点列表 | `journey.stages[*].touchpoints` | 跳过 Phase 1 触点提取，直接进入情绪关键词标注 |
| 情绪关键词 | `journey.stages[*].emotion` + `key_moments[*].emotion` | 注入 Phase 3 emotion-visual-mapping 查询 |
| pain level | `journey.stages[*].pain_points` 数量 / severity | 决定该触点在 mood-row 标签的优先级 |
| `touchpoints[].override` | `journey.key_moments[type=peak/dropout]` | 写入 board.json 的 touchpoints[] 数组，下游 Flow 可对该触点单独覆写颜色 |

#### 来自 stories（增量来源，补充人物锚点）

- `stories.persona.description + jtbd` → HTML header 的 `persona_line` / `jtbd_line` 直接渲染
- `stories.stories[*].scenario` → 当 journey 缺失时，作为触点提取的 fallback 来源

**Step 3 · 告知用户沿用情况**（必做）：

读到上下文后必须明确告诉用户：

> "已读到 [N 个] 上游 Skill 上下文：[列出 brief/journey/stories]。已自动预填以下字段，跳过对应提问：
> - project_name = [...]
> - 触点列表（来自 journey）= [N 个]
> - product_type = [...]
> - 目标受众 = [...]
>
> 接下来从 [第一个未自动预填的字段] 开始问你（或如全部填满，直接进入 Phase 3 推导方案）。"

### 下游输出（Phase 7 执行，按 chain-protocol §2.1 v1.1.1 顺序）

完成产出后**严格按以下顺序**：

1. **先写盘** `spark-output/context/board.json`（schema 见 frontmatter）
2. **自检行**：chat 输出 `✅ board.json 已写盘到 spark-output/context/board.json`
3. **present_files** 输出 HTML 给用户预览
4. **紧凑 marker**：

   ```
   <!-- spark-context:board ref="spark-output/context/board.json" -->
   Board 已保存：project=xxx，selected_scheme=xxx，primary=#xxx，font=xxx
   <!-- /spark-context:board -->
   ```

5. **Handoff 引导**：建议跑 `/Web页面设计`（消费 board.color + component）或 `/动效规划`（消费 board.typography 调性）或 `/数据可视化`（消费 board.color.primary/secondary）
6. **更新链路面板** `spark-output/dashboard.html`（详见 chain-protocol §9）

### 字段流向下游

Board 是视觉锚点，下游消费：

- `board.color.primary` / `secondary` / `neutral` → **flow-web / flow-mobile** 的页面配色；**chart** 的图表配色
- `board.typography.heading_font` / `body_font` → **flow-web / flow-mobile** 的字体规范；**motion-plan** 的字体调性反推 Personality archetype
- `board.component.button` / `card` / `input` / `tag` → **flow-web / flow-mobile** 的组件落地基准
- `board.style_keywords` → **motion-plan** 推导 archetype（Playful / Premium / Corporate / Energetic）的关键输入
- `board.spacing` / `radius` → **flow-web / flow-mobile** 的间距 / 圆角系统
- `board.touchpoints[].override` → **flow-web / flow-mobile** 在该触点对应页面的局部色彩覆写

---

## ⚠️ CRITICAL RULES — 违反任何一条即为失败

1. HTML 的 CSS 必须**逐字复用**本文件中 `LOCKED_CSS` 变量的内容。禁止新增、删除、修改任何选择器或属性值。
2. HTML 必须**完全自包含**——无外部 CSS/JS/图片 URL。图片用 `data:image/jpeg;base64,...` 内嵌。
3. 每套方案必须包含**全部 4 行**：氛围图行(4格) → 字体+介绍行 → 色条行(Primary+Secondary) → 组件行(4列)。
4. 色条 flex 比例必须是 `8:4:3:2:2`。
5. 组件行必须渲染 4 列：Buttons / Input / Card / Tags+Toggle，用 `border-right` 分隔。
6. 每套方案 3 张 ImageGen 氛围图 + 1 张 CSS linear-gradient 补位 = 共 4 格。
7. 按钮/输入框/卡片/标签的文案必须与产品语境匹配（教育→"开始学习"，电商→"立即下单"）。
8. 输出语言跟随输入语言（中文 journey → 中文标注；英文 → 英文）。

---

## 执行流程

### Phase 0.5: 上下文检查

按 Chain Context 章节定义读取 `spark-output/context/{brief,journey,stories}.json`，预填 project_name / 触点 / 产品类型 / 受众 / 品牌约束。告知用户沿用情况后进入下一 Phase。

### Phase 1: 提取触点

**链式模式跳过**：直接从 `journey.stages[*].touchpoints` 读取触点列表与情绪关键词。

**独立模式**：读取用户提供的 journey/stories 文字。提取 3-8 个触点，每个标注：名称、情绪关键词(1-3个)、pain level。列表交给用户确认。

### Phase 2: 收集上下文

用 AskUserQuestion 确认（已知的跳过）：
- 产品类型+行业（链式从 `brief.project_type` 读）
- 目标受众（链式从 `brief.user` 读）
- 已有品牌约束（链式从 `brief.constraints` 读，有则遵守）
- 风格参考（可选）

### Phase 3: 推导 3-4 套方案

基于触点情绪 + 产品性质，推导 3-4 套**色彩方向不同**的方案。每套方案定义：
- `name`: 方案命名（2-3字）
- `desc`: 1-2句色彩哲学描述
- `keywords`: 4个关键词
- `font`: 推荐字体名
- `primary`: 5色数组 [500主色, 300浅, 700深, 100最浅, 900最深]
- `secondary`: 5色数组，同结构
- `btn_bg`, `btn_color`, `input_border`, `card_border`, `tag_bg`, `tag_color`, `toggle_bg`

参考 [emotion-visual-mapping.md](references/emotion-visual-mapping.md) 做情绪→色彩翻译。

### Phase 4: 生成氛围图

为每套方案生成 3 张 ImageGen（1792x1024），体现该方案色彩方向的产品氛围。

> **降级**：ImageGen 工具不可用时，4 格全部用 CSS linear-gradient 渲染（`primary[0]` → `secondary[0]`），不阻断流程。

### Phase 5: 组装 HTML

**必须严格执行以下步骤，不可省略或改编：**

#### Step 5.1: 缩略 + base64

```bash
mkdir -p spark-output/board/{project}-moodboard
cp vibe_images/{project}-*.png spark-output/board/{project}-moodboard/
cd spark-output/board/{project}-moodboard
for f in *.png; do
  sips -Z 400 "$f" --out "${f%.png}_thumb.jpg" -s format jpeg -s formatOptions 60 2>/dev/null
done
```

然后用 bash 生成 b64data.json：
```bash
A1=$(base64 -i {方案A图1}_thumb.jpg | tr -d '\n')
A2=$(base64 -i {方案A图2}_thumb.jpg | tr -d '\n')
# ... 所有12张
printf '{"a1":"%s","a2":"%s",...}' "$A1" "$A2" ... > b64data.json
```

#### Step 5.2: 运行 Python 脚本生成 HTML

**以下 Python 脚本是模板。执行时只允许修改标注了 `# ← EDIT` 的行。其余代码（尤其是 LOCKED_CSS 和 render_scheme 函数）必须原封不动复制。**

```python
import json, os

with open("b64data.json") as f:
    b64 = json.load(f)

# ← EDIT: 填入 Phase 3 推导的方案数据
schemes = [
    {
        "id": "a",
        "name": "方案名",                    # ← EDIT
        "desc": "方案描述",                   # ← EDIT
        "keywords": ["kw1","kw2","kw3","kw4"], # ← EDIT
        "font": "Space Grotesk",              # ← EDIT
        "img_keys": ["a1", "a2", "a3"],
        "img_labels": ["标签1","标签2","标签3"], # ← EDIT
        "primary": ["#7C4DFF","#B388FF","#5E35B1","#EDE7F6","#311B92"],   # ← EDIT
        "secondary": ["#00BCD4","#80DEEA","#0097A7","#E0F7FA","#006064"], # ← EDIT
        "btn_bg": "#7C4DFF", "btn_color": "#fff",        # ← EDIT
        "input_border": "#B388FF",                        # ← EDIT
        "card_border": "#EDE7F6",                         # ← EDIT
        "tag_bg": "#EDE7F6", "tag_color": "#5E35B1",     # ← EDIT
        "toggle_bg": "#7C4DFF",                           # ← EDIT
    },
    # ← EDIT: 方案 B, C, D 同结构
]

# ← EDIT: 产品信息
project_title = "产品名"
persona_line = "Persona: xxx"
jtbd_line = "JTBD: xxx"

# ← EDIT: 组件文案（必须匹配产品语境）
BTN_PRIMARY = "主按钮"
BTN_SECONDARY = "次按钮"
INPUT_PLACEHOLDER = "搜索..."
CARD_TITLE = "卡片标题"
CARD_DESC = "卡片描述"
TAG_A = "标签A"
TAG_B = "标签B"

# ─── 以下禁止修改 ───────────────────────────────────────────

LOCKED_CSS = """* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: "PingFang SC", -apple-system, sans-serif;
  background: #FFFFFF;
  color: #1F2937;
  padding: 48px 40px;
  min-height: 100vh;
}
.container { max-width: 100%; margin: 0 auto; }
.scheme-nav {
  display: flex;
  gap: 0;
  margin-bottom: 48px;
  border-bottom: 1px solid #D1D5DB;
}
.scheme-tab {
  padding: 10px 24px;
  font-size: 13px;
  font-weight: 400;
  color: #6B7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.scheme-tab:hover { color: #1F2937; }
.scheme-tab.active {
  color: #1F2937;
  font-weight: 600;
  border-bottom-color: #1F2937;
}
.scheme-panel { display: none; }
.scheme-panel.active { display: block; }
.mood-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 40px;
}
.mood-img {
  height: 100px;
  display: flex;
  align-items: flex-end;
  padding: 8px;
}
.mood-img span {
  font-size: 9px;
  color: #fff;
  background: rgba(0,0,0,0.4);
  padding: 2px 6px;
}
.row-type {
  display: flex;
  align-items: center;
}
.type-display {
  flex: 0 0 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.type-display .aa {
  font-size: 120px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -2px;
}
.type-display .font-name {
  font-size: 11px;
  color: #6B7280;
  margin-top: 10px;
}
.intro {
  flex: 1;
  padding-left: 40px;
}
.intro h2 {
  font-size: 15px;
  font-weight: 600;
  color: #1F2937;
  margin-bottom: 10px;
}
.intro p {
  font-size: 13px;
  color: #6B7280;
  line-height: 1.7;
  margin-bottom: 2px;
}
.intro .keywords {
  display: flex;
  gap: 6px;
  margin-top: 12px;
}
.intro .kw {
  font-size: 10px;
  padding: 2px 8px;
  border: 1px solid #D1D5DB;
  color: #4B5563;
}
.divider {
  height: 1px;
  background: #D1D5DB;
  margin: 40px 0;
}
.row-colors {
  display: flex;
  gap: 40px;
}
.row-colors > div {
  flex: 1;
  min-width: 25%;
}
.color-group {
  display: flex;
  gap: 0;
  height: 160px;
  width: 100%;
}
.color-strip {
  height: 100%;
}
.color-module-title {
  font-size: 11px;
  font-weight: 600;
  color: #6B7280;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.row-comps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
}
.comp-col {
  padding: 0 15px;
  border-right: 1px solid #D1D5DB;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.comp-col:first-child { padding-left: 0; }
.comp-col:last-child { border-right: none; padding-right: 0; }
.comp-col-title {
  font-size: 10px;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 4px;
}
.btn {
  display: inline-block;
  padding: 6px 16px;
  font-size: 11px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  text-align: center;
  white-space: nowrap;
}
.input-demo {
  padding: 6px 10px;
  border: 1px solid #D1D5DB;
  font-size: 11px;
  background: #F9FAFB;
  width: 120px;
  color: #6B7280;
}
.card-demo {
  border: 1px solid #D1D5DB;
  padding: 10px;
  max-width: 140px;
}
.card-demo .card-title {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 3px;
}
.card-demo .card-desc {
  font-size: 10px;
  color: #6B7280;
}
.tag {
  display: inline-block;
  padding: 2px 6px;
  font-size: 9px;
  font-weight: 500;
}
.toggle {
  width: 30px; height: 16px;
  border-radius: 8px;
  position: relative;
}
.toggle::after {
  content: '';
  position: absolute;
  width: 12px; height: 12px;
  background: #fff;
  border-radius: 50%;
  top: 2px; right: 2px;
}
.header {
  margin-bottom: 32px;
}
.header h1 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 6px;
}
.header p {
  font-size: 12px;
  color: #6B7280;
}"""


def render_scheme(s, active=False):
    active_cls = " active" if active else ""
    mood_html = ""
    for key, label in zip(s["img_keys"], s["img_labels"]):
        mood_html += (
            f'<div class="mood-img" style="background:url(data:image/jpeg;base64,'
            f'{b64[key]}) center/cover no-repeat;"><span>{label}</span></div>\n'
        )
    mood_html += (
        f'<div class="mood-img" style="background:linear-gradient(135deg, '
        f'{s["primary"][0]}, {s["secondary"][0]});"><span>色彩延伸</span></div>\n'
    )
    flexes = [8, 4, 3, 2, 2]
    pri = "".join(f'<div class="color-strip" style="flex:{fx};background:{c};"></div>' for c, fx in zip(s["primary"], flexes))
    sec = "".join(f'<div class="color-strip" style="flex:{fx};background:{c};"></div>' for c, fx in zip(s["secondary"], flexes))
    kw = "".join(f'<span class="kw">{k}</span>' for k in s["keywords"])

    return f'''<div class="scheme-panel{active_cls}" id="panel-{s['id']}">
  <div class="mood-row">{mood_html}</div>
  <div class="row-type">
    <div class="type-display">
      <div class="aa" style="font-family:'{s['font']}',sans-serif;">Aa</div>
      <div class="font-name">{s['font']}</div>
    </div>
    <div class="intro">
      <h2>{s['name']}</h2>
      <p>{s['desc']}</p>
      <div class="keywords">{kw}</div>
    </div>
  </div>
  <div class="divider"></div>
  <div class="row-colors">
    <div><div class="color-module-title">Primary</div><div class="color-group">{pri}</div></div>
    <div><div class="color-module-title">Secondary</div><div class="color-group">{sec}</div></div>
  </div>
  <div class="divider"></div>
  <div class="row-comps">
    <div class="comp-col">
      <div class="comp-col-title">Buttons</div>
      <button class="btn" style="background:{s['btn_bg']};color:{s['btn_color']};">{BTN_PRIMARY}</button>
      <button class="btn" style="background:transparent;color:{s['btn_bg']};border:1px solid {s['btn_bg']};">{BTN_SECONDARY}</button>
    </div>
    <div class="comp-col">
      <div class="comp-col-title">Input</div>
      <input class="input-demo" style="border-color:{s['input_border']};" value="{INPUT_PLACEHOLDER}" readonly>
    </div>
    <div class="comp-col">
      <div class="comp-col-title">Card</div>
      <div class="card-demo" style="border-color:{s['card_border']};">
        <div class="card-title">{CARD_TITLE}</div>
        <div class="card-desc">{CARD_DESC}</div>
      </div>
    </div>
    <div class="comp-col">
      <div class="comp-col-title">Tags</div>
      <span class="tag" style="background:{s['tag_bg']};color:{s['tag_color']};">{TAG_A}</span>
      <span class="tag" style="background:{s['tag_bg']};color:{s['tag_color']};">{TAG_B}</span>
      <div class="toggle" style="background:{s['toggle_bg']};"></div>
    </div>
  </div>
</div>'''


tabs_html = ""
for i, s in enumerate(schemes):
    ac = " active" if i == 0 else ""
    tabs_html += f'<div class="scheme-tab{ac}" onclick="switchTab(\'{s["id"]}\')">{s["name"]}</div>'

panels_html = ""
for i, s in enumerate(schemes):
    panels_html += render_scheme(s, active=(i == 0))

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{project_title} — Design System Mood Board</title>
<style>
{LOCKED_CSS}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>{project_title} &mdash; Design System Mood Board</h1>
    <p>{persona_line} &middot; {jtbd_line}</p>
  </div>
  <div class="scheme-nav">{tabs_html}</div>
  {panels_html}
</div>
<script>
function switchTab(id) {{
  document.querySelectorAll('.scheme-tab').forEach(function(t) {{ t.classList.remove('active'); }});
  document.querySelectorAll('.scheme-panel').forEach(function(p) {{ p.classList.remove('active'); }});
  event.currentTarget.classList.add('active');
  document.getElementById('panel-' + id).classList.add('active');
}}
</script>
</body>
</html>'''

import os
os.makedirs("spark-output/board", exist_ok=True)
board_path = f"spark-output/board/{project_slug}-moodboard.html"
with open(board_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Done: {os.path.getsize(board_path)/1024:.0f} KB")
```

### Phase 6: present_files 交付

```
present_files spark-output/board/{project_slug}-moodboard.html
```

让用户在 3-4 套方案标签页之间切换比较，回复"我选 X"或"用方案 B"等指令进入 Phase 7。

### Phase 7: 用户选定后双通道输出（按 chain-protocol §2.1 v1.1.1 顺序，不得颠倒）

#### Step 7.1 — **先写盘**

把选中方案的色彩 / 字体 / 组件 token 序列化为 `design-tokens.json` 结构，**写入 `spark-output/context/board.json`**（不存在则创建目录）：

```json
{
  "skill": "board",
  "generated_at": "2026-06-01T12:00:00Z",
  "project_name": "...",
  "selected_scheme": "方案B",
  "style_keywords": ["内敛","专业","可信","温润"],
  "color": {
    "primary": "#7C4DFF",
    "secondary": "#00BCD4",
    "neutral": { "50":"#F9FAFB","100":"#F3F4F6","500":"#6B7280","900":"#111827" }
  },
  "typography": { "heading_font": "Space Grotesk", "body_font": "Inter" },
  "spacing": { "xs":"4px","sm":"8px","md":"16px","lg":"24px","xl":"32px" },
  "radius": { "sm":"4px","md":"8px","lg":"16px","xl":"24px","full":"9999px" },
  "component": {
    "button": { "bg":"#7C4DFF","color":"#fff","padding":"6px 16px","font_size":"11px" },
    "input":  { "border":"#B388FF","bg":"#F9FAFB","width":"120px" },
    "card":   { "border":"#EDE7F6","padding":"10px","max_width":"140px" },
    "tag":    { "bg":"#EDE7F6","color":"#5E35B1","font_size":"9px" }
  },
  "touchpoints": [
    { "id":1, "name":"...", "emotions":["..."], "override":{ "color":{ "accent":"#xxx" } } }
  ]
}
```

#### Step 7.2 — **自检行**

chat 输出一行：
```
✅ board.json 已写盘到 spark-output/context/board.json（selected_scheme=方案B，primary=#7C4DFF）
```

#### Step 7.3 — **present_files 交付 HTML**（如 Phase 6 已交付，本步可跳过）

#### Step 7.4 — **紧凑 marker**

```
<!-- spark-context:board ref="spark-output/context/board.json" -->
Board 已保存：project=xxx，selected_scheme=方案B，primary=#7C4DFF，font=Space Grotesk
<!-- /spark-context:board -->
```

#### Step 7.5 — **Handoff 引导**

按"页面 / 动效 / 数据"三类完整覆盖：

> 接下来推荐：
> - 📄 `/Web页面设计` 或 `/mobile页面设计`：消费 board.color + component，生成符合视觉系统的页面
> - 🎬 `/动效规划`：消费 board.typography + style_keywords，推导 Personality archetype（Playful / Premium / Corporate / Energetic）
> - 📊 `/数据可视化`：消费 board.color.primary/secondary，生成符合配色的图表规范

#### Step 7.6 — **更新链路面板**

按 chain-protocol §9 流程刷新 `spark-output/dashboard.html`，并在 Handoff 末尾告知：
```
📊 链路面板已更新：spark-output/dashboard.html（双击在浏览器打开）
```

---

## Pitfalls

- Python f-string 中禁止出现中文引号 `""`，用 `「」` 替代
- base64 字符串太长不能直接用 shell 变量传递，必须先写 `b64data.json` 再 Python 读取
- `sips` 仅 macOS，Linux 改用 `convert -resize 400x`
- 组件文案不能用通用占位符（"按钮"/"文本"），必须匹配产品上下文
- Phase 7 严禁先输出 marker 再写盘——OPC + MuleTeam 已验证这个顺序最易导致 board.json 缺失
- 写盘失败时**不允许静默跳过**：必须在自检行输出 `⚠️ 文件系统不可用，已降级为 chat-only marker（含完整 JSON）`

## References

| File | Purpose |
|------|---------|
| [emotion-visual-mapping.md](references/emotion-visual-mapping.md) | Phase 3: 情绪→色彩/字体映射查询表 |

---

## 质量规范

> 本章节是 Skill 完成度的**高层判定标准**，与 Phase 5/7 内部的执行级约束互补。Phase 是"该怎么做"，本章节是"做对了没有"。

### 🚫 红线规则（违反即任务失败，无降级空间）

- **HTML 必须基于 LOCKED_CSS 逐字克隆**——不得新增、删除、修改任何选择器或属性值（详见 CRITICAL RULES #1）
- **HTML 必须完全自包含**——禁止任何外部 CDN / link / script / image URL，所有图片以 `data:image/jpeg;base64,...` 内嵌
- **必须输出双通道**：`spark-output/context/board.json` 写盘 + chat 内紧凑 marker（含 `ref=` 属性）
- **必须按 chain-protocol §2.1 v1.1.1 顺序执行**：Step 7.1 写盘 → 7.2 自检 → 7.3 present → 7.4 marker → 7.5 handoff → 7.6 dashboard，不得颠倒
- **方案数必须为 3 或 4**——少于 3 套用户无对比，多于 4 套决策疲劳
- **每套方案必须含 4 行结构**：mood-row(4格) + row-type + row-colors(Primary+Secondary) + row-comps(4列)，少一行即失败

### ⚠️ 反模式（常见错误，需主动规避）

- ❌ 凭记忆重写 LOCKED_CSS 或"简化"为 Tailwind / Bootstrap 版本
- ❌ 链式模式下还重新追问触点 / 行业 / 受众——已在 Phase 0.5 从 brief / journey 读到的字段不得二次提问
- ❌ 组件文案写"按钮"/"文本"等通用占位符——必须匹配产品上下文（教育→"开始学习"；电商→"立即下单"；金融→"立即投资"）
- ❌ 在 chat 内重复输出完整 design-tokens JSON——应只输出紧凑 marker（≤ 80 字摘要），完整 JSON 写盘
- ❌ Phase 7 先 marker 后写盘——必须先写盘
- ❌ 色条 flex 比例不是 8:4:3:2:2、`.toggle` 之外出现 border-radius > 4px、出现 box-shadow 属性
- ❌ ImageGen 不可用时直接 abort——必须降级为 4 格全 CSS gradient

### ✅ 质量标准（通过条件，全部满足才算交付）

**内容完整性**：
- 触点 3-8 个，每个含名称 + 情绪关键词(1-3) + pain level
- 方案 3 或 4 套，每套 8 个必需字段（name/desc/keywords/font/primary/secondary + 7 个组件颜色）齐全
- 每个 primary / secondary 数组恰好 5 色（500主 / 300浅 / 700深 / 100最浅 / 900最深）
- 组件文案与产品语境匹配（非通用占位符）

**HTML 产物完整性**（Phase 5 自检清单全部通过）：
- 无 `border-radius` > 4px（`.toggle` 的 8px 除外）
- 无 `box-shadow` 属性
- 色条 flex 比例 = 8:4:3:2:2
- `.mood-img` height = 100px
- `.type-display .aa` font-size = 120px
- `.comp-col` padding = 0 15px, gap = 10px
- `.btn` padding = 6px 16px
- `.input-demo` width = 120px
- `.card-demo` max-width = 140px
- 所有图片 = `data:image/jpeg;base64,...`（无外部URL）
- body padding = 48px 40px
- 方案数 = 3 或 4，每方案 4 个 `.mood-img`
- 每方案有 Primary + Secondary 两个 `.color-group`
- Tab 切换 JS 存在且功能正确
- 无任何外部依赖（无 CDN link、无 external script）

**链路接入正确性**：
- `spark-output/context/board.json` 文件已写入且 schema 符合 frontmatter 定义
- chat marker 含 `ref="spark-output/context/board.json"` 属性
- 下游 Skill（flow-web / flow-mobile / motion-plan / chart）调用时能正确读取本 Board 上下文
- 已输出符合 Step 7.5 模板的 Handoff 引导（覆盖页面 / 动效 / 数据三类）
- `spark-output/dashboard.html` 已刷新（链路面板生成失败仅 warning，不阻断交付）
