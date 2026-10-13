# 审美基线（写任何 CSS 之前必读）

> **未读完这一份之前，不要写 `:root`。**
> 四组数值（色板 / 字阶 / 圆角 / 栅格）的判据与参考站实测区间都在这里。
> 凭感觉填 `:root` 的那一稿，事后所有门都会是绿的，而它就是不好看。

本文件是本 Skill 的**审美主权**。它不描述风格，它规定**任何风格都必须达到的物理量**。  
产出「丑」的根因不是选错风格，而是这九项里有三项以上用了框架默认值。

> 判据：把成品缩略到 200px 宽。若它与「任意一个 Bootstrap 模板」无法区分，本文件的第 1、3、4、5 条必然违规。

## 0. 参考相对校准：技术合格不等于视觉合格

有用户指定优秀案例时，先提取可迁移机制与高分离度失败指纹，再用同一组维度比较参考与自测截图。
禁止跨风格像素相似度，也禁止把参考配色/组件写成全局模板。至少比较：

- 主角是否成为场景，还是被缩进一张普通图片卡；
- 首屏是否有明确的巨大/中/小尺度层级；
- 文案是否是具体品牌主张，还是生成器说明；
- 章节是否改变轴线、密度、画面比例与阅读动作；
- 动效是否持续存在并参与叙事，而不只是 hover/统一淡入；
- Doc 是否有稳定阅读轴、真实作品锚点和一屏可理解的关系密度。

静态门只拦高分离度丑版（占位文案、声明构图未落地、空卡、媒体缩成卡、章节全同）。
最终截图仍需人工对照：若参考明显更强，测试不能以“无溢出/门通过”为完成理由。

---

## 1. 底色：禁止纯白与纯黑

大面积底色（占屏 ≥40%）**必须离开纯色轴**。

> **管辖范围是产品 UI 稿，不是文档纸张。** 方案文档的白底长卷（`profile=doc-canvas`）反过来**要求**
> 白/近白——那是画册的纸，不是界面。产品稿的深色/染色底放进纸上的画框里照常成立，两条规则不冲突，
> 由 `check_ui_quality` 按 profile 分别执行。见 [doc-canvas.md](doc-canvas.md) §3。

| 气候 | 合法底色范围 | 参考值 |
|---|---|---|
| 浅色暖 | L 95–98，暖偏 | `#F7F6F3` `#FAF8F4` `#F5F2EC` |
| 浅色冷 | L 94–97，冷偏 | `#F2F3F5` `#EEF1F4` `#F4F6F8` |
| 浅色染色 | 主色 4–8% 混入白 | `#EDE9F5`（紫）`#EAF3F0`（绿）`#E9F2F7`（青） |
| 深色 | L 6–14，带色相不带纯灰 | `#0B1220`（蓝黑）`#0E1A14`（墨绿）`#141210`（暖炭）`#0C0C10`（冷炭） |

**硬失败：** `#FFFFFF` / `#000000` / `#F9FAFB` / `#111827` / `#1F2937` 作为页面主底。  
纯白只允许出现在**叠在染色底之上的白壳**（见第 6 条）——那时它是构图元素，不是底色。

## 2. 色板结构：4 槽 + 面积配额

每个方案只允许 4 个语义槽，**不得增加第 5 个彩色**：

```yaml
--canvas   # 底（第 1 条）                 面积 ~62-72%
--world    # 世界色：主视觉/大色域/深色段   面积 ~20-26%
--accent   # 信号色：CTA + 一处强调，仅此   面积 ~3-6%
--ink      # 文字色，不是 #000            面积 —
```

- `--ink` 取 `--canvas` 的同色相深化版，L 12–20，**不用纯黑**。深底上的文字用 L 92–96 的暖白/冷白，不用纯白。
- `--accent` **同时**出现在标题色、卡片底、按钮、icon、边框这 5 类中的 ≥3 类 = 失控，必须收回到 ≤2 类。
- 需要更多颜色时，用 `--world` 的明度阶（3 档），不引入新色相。

### hex 黑名单（未经材料推导直接使用即失败）

```
#3B82F6 #2563EB #60A5FA #1D4ED8   Tailwind blue
#8B5CF6 #7C3AED #A78BFA #6D28D9   Tailwind violet
#22C55E #16A34A #4ADE80 #10B981   Tailwind green/emerald
#EF4444 #F97316 #EAB308 #EC4899   Tailwind red/orange/yellow/pink
#6B7280 #9CA3AF #374151 #4B5563   Tailwind gray
#2196F3 #4CAF50 #FF9800 #E91E63   Material
#007BFF #28A745 #DC3545 #6C757D   Bootstrap
```

以及所有 HTML 具名色（`skyblue` `lightpink` `crimson`…）。  
这些是框架默认值，不是设计决定。要用蓝，就从项目材料里取一个蓝，并写下它来自什么（水、夜空、钢、瓷、牛仔布……）。

**用户没给材料时**（一句话需求）：按 `SKILL.md` §2 的三步推导——
列出主体所在的真实物料世界（≥5 个具体的物）→ 取 1 个做 `--world`、1 个做 `--accent` → 每色写一句来源。  
**禁止用行业刻板印象取色**（科技=蓝紫、医疗=蓝、环保=绿、金融=深蓝）——那不是设计决定，是条件反射。

> **dashboard / 后台 / 工作台 / console / SaaS / 数据 App（F13 / F14，及 F19 仪表盘屏）**：
> 四槽太粗,一块仪表盘大部分像素是中性灰。**改用 [`product-palettes.md`](product-palettes.md) 的扩展 token**
> （带微染中性阶 + 16 个 collision-checked accent + 现成套装）——这是"dashboard 不再默认蓝"的直接解药。
> 品牌页仍用上面的四槽 + 材料推导。

## 3. 阴影：三层有色影，禁单层黑影

**硬失败：** `box-shadow: 0 Npx Npx rgba(0,0,0,0.1)` 或任何单层纯黑影。

真实感来自「接触影 + 形体影 + 环境影」三层叠加，且色相跟随 `--world`：

```css
/* 浅色页 · 中性高级 */
--shadow-card:
  0 1px 2px rgba(18,20,24,.05),
  0 8px 20px -6px rgba(18,20,24,.08),
  0 28px 60px -24px rgba(18,20,24,.12);

/* 浅色页 · 粉彩（影带紫相，这是粉彩高级感的来源） */
--shadow-soft:
  0 2px 6px rgba(124,92,196,.08),
  0 16px 36px -10px rgba(124,92,196,.16),
  0 48px 90px -40px rgba(124,92,196,.22);

/* 深色页：不用黑影，用发光与内高光 */
--shadow-dark:
  0 24px 60px -20px rgba(0,0,0,.6),
  inset 0 1px 0 rgba(255,255,255,.06);
```

规则：

- 一个方案里**阴影配方 ≤3 套**，按角色（卡 / 浮层 / 主视觉）分配，不按元素随手写。
- 阴影的 `blur` ≥ `y-offset` 的 2 倍；`y` 小于 4px 的影只用于 1px 描边替代。
- 深色页上的白色边框用 `inset 0 1px 0 rgba(255,255,255,.06)` 代替 `border: 1px solid #333`。

## 4. 圆角：3–4 个角色值，禁全局一值

**硬失败：** 整页只有一个 `border-radius`。

```yaml
radius_roles:
  shell:   28-44px   # 大壳、区块容器、设备框
  card:    14-24px   # 常规卡片、图片
  control: 8-12px    # 输入框、小标签
  pill:    999px     # 按钮、chip、头像
```

- `shell` 与 `card` 至少差 **12px**，否则读不出层级。
- 直角风格（brutalism/editorial）：`shell/card = 0`，但 `pill` 仍可为 999，形成对撞——这本身就是一个可见决定。
- 嵌套时内圆角 = 外圆角 − padding，不要内外同值。

## 5. 字体：异质配对 + 尺度断崖

**硬失败：** 全站单一字体家族；display 与 body 同族同粗细。

```yaml
font_pairing:
  display: 与 body 异质（衬线↔无衬线，或几何↔人文，或超粗↔常规）
  body:    正文与 UI
  mono:    可选，用于数字/代码/微标签（数据与技术语义需要时）
families_min: 2   # display + body；有 mono 更好
```

尺度：

```css
--display: clamp(3.5rem, 7.5vw, 8rem);   /* 至少一处 ≥96px */
--h1:      clamp(2.5rem, 4.6vw, 4.5rem);
--h2:      clamp(1.75rem, 2.8vw, 2.75rem);
--body:    clamp(0.95rem, 1.05vw, 1.0625rem);
--meta:    0.75rem;  /* 字距 +0.08em，大写 */
```

- 相邻层级 ≥ **1.45×**；display 与 body ≥ **3.5×**（utility-dashboard 可降到 2.2×）。
- display 字距默认 0；正文、标题及中英文混排不得使用负字距。只有用户或参考图明确要求紧缩的纯拉丁超大展示字，才可单独评估；进入 PPT/文档导出链路时仍归零。`--meta` 字距 `+0.06em ~ +0.12em` 且大写。
- 标题 ≤2 行；正文行宽 46–68ch；中文正文 ≥15px，移动端关键正文 ≥16px。
- **不默认 Inter / Poppins / Open Sans / Roboto 交差。** 字体必须服务气质：
  | 气质 | display 候选 |
  |---|---|
  | 编辑/古典/奢侈 | `Playfair Display` `Cormorant` `Instrument Serif` `Noto Serif SC` |
  | 几何/科技/金融 | `Space Grotesk` `General Sans` `Sora` `Manrope` |
  | 柔软/儿童/消费 | `Baloo 2` `Quicksand` `Nunito` `Gantari` |
  | 硬朗/宣言 | `Anton` `Archivo Black` `Bebas Neue` |
  | 中文 display | `Noto Serif SC 900` / `Source Han Serif` / 思源黑体 Heavy（与拉丁 display 混排时锁定同字重感） |

## 6. 层次：必须可辨，但不强制叠压数量

**硬失败：** 全页所有元素都在同一 z 平面（背景 + 一层卡片）。

高表现力 query 可使用真实咬合：

- 白壳负 margin 叠入上一段（`margin-top: -72px; border-radius: 40px 40px 0 0`）
- 主视觉切边（超出容器 `overflow: visible` + `transform: translate`）
- 巨字被前景遮挡一部分（巨字 z:1，主体 z:3）
- 异形转场：波浪 / 凹口 / 拱门蒙版切换色域
- 图片出框：卡片内图片超出卡片边界 8–16%

叠压出现时必须有边界、影或材质变化说明空间关系；无依据的重叠读作错位。
克制、编辑、工具或证据型 query 可以用规则线、阅读轴、尺度/密度变化和关系网格建立层次，
不要求负 margin、出框或阴影。校验以 `layoutRecipe.mechanismPalette` 与 renderer 差异为准。

## 7. 主视觉：真实资产，职责与占比由 query 决定

**硬失败：** 用 emoji、CSS 渐变球、纯色 div、icon font 冒充主视觉。

`visualProtagonist=object` 且 `imageDependency=heroic` 时，主资产通常应成为首屏第一视觉层；
编辑、工具、数据或克制型 query 则可以让文字、关系图或任务状态成为主角。
具体占比、首屏高度和下一段露出量写入本轮 `heroGeometry`，没有统一数值模板。
位图清晰度仍以目标槽位为准：主资产短边通常不低于 1200px，文档宽幅资产走长边判据。

- 图片必须有**形状决定**：全幅出血 / 圆角矩形 / 药丸 / 椭圆 / 拱门 / 菱形 / 透明去背。同一页形状语言 ≤2 套。
- 图片比例由各 contentRole 的槽位决定；只有多个角色承担不同叙事职责时才要求相互区别。
- 生图不承担 Logo、按钮文字、卡号、长文案 —— 这些由 HTML 原生排版叠加。

### 7b. 功能图标同样适用本条

**硬失败：** 导航 / Tab / 功能位图标直接用通用描边图标集
（`viewBox="0 0 24 24"` + `fill="none"` + `stroke-width="2"` 的 Feather / Lucide / Heroicons 默认造型）。

这与色板里直接用 `#3B82F6` 是**同一种失败**：它是框架默认值，不是设计决定。
成品缩略到 200px 时，一排通用描边图标会立刻把画面拉回"任意一个后台模板"。

合法做法三选一：

1. **设计决定的矢量图标（默认路径，所有家族通用）**：用本 Skill 内置 **Phosphor**（`references/phosphor-icons.md`，
   `viewBox 0 0 256 256` + `currentColor`），颜色吃 `--ink`/`--accent`，字重同屏一致，
   底板圆角与 `--r-control` 同源；表现型家族用 `fill`/`duotone` 字重 + 圆底板撑质感。
   （旧规则"表现型必须一次生成 ≥5 枚 icon-kit"已废除：文生图产出的拼贴没有对齐网格也没有 alpha，
   强行要求只会逼出雪碧图切片，实测导致 tab/分类/商品图全部错位。见 image-bridge.md）
2. **主角图标生图**：仅限 ≤3 枚真正的主角位，**逐枚单独生成**并去背验 alpha
3. **声明豁免**：专业工具 / 后台 / 高密数据界面（F14 等）本就该用系统级图标，
   在 HTML 顶部写 `<!-- design-intent: system-icons -->` 并在 `art-direction.json` 说明理由；
   直接从 `assets/phosphor/phosphor-svgs-flat.zip` 里取（取法见
   `craft/phosphor-icons.md`），不要手写 24×24 描边

写不出理由的声明就是逃避。**Tab bar 是用户每屏都看见的东西，它敷衍，整个 App 就敷衍。**

## 8. 节奏：换气与反模板

**硬失败：** 信息关系不同，却连续 3 段回退成同一种 DOM 与同一种阅读动作。

换气由 `layoutRecipe.chapterRhythm` 决定，可以来自色域、影像占比、阅读轴、密度、
关系结构、时间推进或交互状态的变化；不得强迫所有 query 使用满版影像、异形转场或 96px 巨字。

装饰预算：

```yaml
hero_major_cards:            0-2
same_style_cards_per_section: 2-4
consecutive_card_grid:        1     # 等宽卡片阵列全页最多一次连续
decorative_mechanisms:        0-2   # 仅在 query/材质世界需要时使用；克制型可为 0
```

## 9. 动效：一个主打 + 必要反馈

- **1 个 signature motion**，服务主视觉或叙事转场（视差、角色浮动、蒙版揭示、数字滚动，择一）。
  奇观级 Hero 引擎选型见 `motion/hero-engines.md`（一页一引擎 + 飞书嵌入安全档）；
  更广的可复用招式菜单见 `motion/motion-patterns.md`（光标反应/滚动驱动/文字/转场）。
- 必要反馈：hover / press / focus / loading，缺一即不完整。
- 尊重 `prefers-reduced-motion`；关闭动效后首屏仍完整（禁止元素初始 `opacity: 0` 卡死）。
- **不把「至少 N 种动效」当质量标准**——但**有没有**是硬门：落地页/长卷类产物必须有 `@keyframes`
  主打时刻与滚动揭示（只有 `transition:` 不算），见 `html-production.md` 的动效正向门。
- **飞书 widget 里不用 WebGL/Three.js**（iframe CSP 常拦 → 碎裂）；那类只进独立 HTML，飞书文档里交静帧图。

---

## 9b. 微观精致度：数值从哪来

「土」不是某一条红线被踩了，而是**十几个微观数值全靠临场发挥**。前九条红线管的是"别做错"，
本节管的是"数值从哪来"。

**唯一正确的来源是设计库条目，不是你的直觉。** 门 0 命中的 `.dna.json` 里有实测的
`spacing / typeScale / radius / stroke / shadow / sizing`，抄进 `art-direction.json` 的 `tokens`，
实现时只从这组值里取。`validate_art_direction` 校验有没有抄、出处对不对；
`check_ui_quality --art-direction` 校验实现有没有真的用（`token-drift-*`）。

### 为什么不设"绝对数值门"

实测过，信号是反的：

| 样本 | 间距落 4pt 栅格 | 字阶跨度 |
|---|---|---|
| gold（优质） | **49%** | **2.36** |
| 参照库实测中位 | ~45% | 3.14 |
| 最丑的真实产物 | **100%** | 4.12 |

好设计大量使用 `clamp` 响应式值与 2px 级光学微调；坏设计因为简陋反而"很规整"。
**所以"间距必须是 8 的倍数""字阶跨度必须 >2.5"这类规则会把好稿判死、把烂稿放行。**
参照库里 16 条实测条目的 baseUnit 有 15 条是 **4**，不是 8——照搬 8pt 栅格的教条本身就是错的。

### 从库里读出来的真实分布（可直接当选值范围）

| 维度 | 参照库实测 | 怎么用 |
|---|---|---|
| `spacing.baseUnit` | 4（16 条里 15 条），少数 8 | 光学微调用 2px 步长是常态，别硬凑 8 |
| `spacing.cardPad` | 中位 8，p75 16 | 卡片内边距普遍比想象的小 |
| `spacing.sectionGap` | 中位 24，范围 12–72 | 区块间距 ≈ cardPad × 2–3 |
| `typeScale.steps` | 5 档 | 少于 4 档读作没有层级 |
| 字阶跨度 max/min | 2.33–5.33 | 2.3 以下确实偏平，但不能设成硬门 |
| `radius` 角色档 | 4 档（shell/card/control/pill） | 全局同一圆角是模板感的主要来源 |
| `shadow.recipes` | 1–2 层，**hueFromCanvas 恒为真** | 阴影必须带底色色相，纯黑压在染色底上发脏 |
| `icons.set` | custom-outline 40 / custom-filled 25 | 没有一条用系统默认描边图标 |

### 假资产：附件里最刺眼的那一类

真实产物里最拉低质感的不是数值偏差，是**图片位上根本没有图**：

- ❌ 商品卡的"图"是渐变色块 + 一个 64px emoji
- ❌ tab bar 图标是 emoji（不同系统渲染还不一致）
- ❌ 主视觉是一个 CSS 圆形

这三条由 `emoji-as-asset` / `emoji-as-icon` / `image-slot-fake` 阻断。
**注意它们查的是「槽位里有没有真资产」，不是「全页有没有图」**——
页面里有一张 hero 真图，不代表 12 个商品卡不是 emoji。

## 合法例外：声明，而不是无视

本文件的默认值刻意严格，但**有些克制的设计决定本身就是对的**：瑞士国际主义风格的单一字体、
极简编辑向的纯白画布、有意为之的平面构图、无影像可用时的字体主导。
这些不该被基线判成缺陷，也不该靠"偷偷违规"通过。

在 HTML 顶部声明，并在 `art-direction.json` 里写明理由：

```html
<!-- design-intent: pure-canvas, single-family, flat-depth, type-led -->
```

| 声明 | 豁免 | 代价 |
|---|---|---|
| `pure-canvas` | §1 纯白/纯黑底 | 必须用阴影质量与层次补足depth |
| `single-family` | §5 字体家族 ≥2 | 必须用字重、字号、字距拉开层级 |
| `flat-depth` | §6 ≥2 处叠压 | 必须用大色域与留白比例建立秩序 |
| `type-led` | §7 主视觉资产 | 巨字必须参与构图（遮挡/出血/咬合），且需 ≥1 个非影像锚点 |

脚本会把对应项从 FAIL 降为 WARN 并标注"已声明"。**其余各条不受声明影响。**
写不出理由的声明就是逃避——审稿时会先看 `art-direction.json` 里的理由是否成立。

## 自查（写完 Hero 后逐条对，不通过不写下一段）

```
[ ] 1  主底色不是 #FFF/#000，且不在 hex 黑名单里
[ ] 2  色板恰好 4 槽；accent 出现类别 ≤2；面积 ≤6%
[ ] 3  阴影为多层有色；全页配方 ≤3 套；无单层纯黑影
[ ] 4  圆角有 3-4 个角色值；shell 与 card 差 ≥12px
[ ] 5  字体角色和层级比服务 query；不为凑两家字体牺牲一致性
[ ] 6  层次机制可辨：叠压、规则线、尺度/密度变化、关系网格至少一种且有证据
[ ] 7  imageDependency=heroic 时主视觉是真实资产；optional 时允许文字/数据/交互成为主角
[ ] 8  无连续 3 段同结构；章节节奏来自 contentPlan
[ ] 9  motionPlan.required=true 时有 signature motion、必要反馈与 reduced-motion；否则静态完整
```

这几条里能自动量的，`check.py` 已经在量了 —— 走 `ui.py review` 就行：

```bash
python3 scripts/ui.py review
```

`✗ BLOCK` 是"预算内要重出一次"；`· REPORT` 不拦你，但它是
「离得奖级还差什么」的清单，改稿前读一遍。
