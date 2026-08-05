# Decision Tree: Keyword → Candidate Mapping

Maps natural-language descriptions (Chinese + English) to a small set of candidate components. Used by **Phase 1** (smart parameter extraction) to narrow the candidate pool from 110+ down to ~3–5 before Phase 2 sniffing.

## How to use

1. Match user input against the keyword groups below
2. Take the listed components as the **initial candidate pool**
3. Pass to Phase 2; sniffing then picks one
4. If no keyword group hits, use category-level pool from `visual-index.md`

> Component names below are the design-time placeholders. The crawler (`scripts/crawl-catalog.sh`) replaces them with real names from reactbits.dev. **Until the crawler runs, treat this as a schema, not a verified mapping.**

---

## Text animations

### "打字机 / 终端 / typewriter / typing"
- TypewriterText
- DecryptedText
- Visual: 字符依次出现，像在键盘输入
- Mass analogy: 终端命令、Cursor in terminal

### "解密 / 乱码 / 矩阵 / glitch / decrypt / scramble / matrix"
- DecryptedText
- ScrambleText
- GlitchText
- Visual: 乱码翻滚最终定格成正文
- Mass analogy: 黑客帝国数据流、密码破解

### "渐显 / 模糊聚焦 / 淡入 / blur / focus / fade in"
- BlurText
- FadeText
- Visual: 模糊一下"咔嗒"聚焦清晰
- Mass analogy: 电影开场片名定格

### "逐字 / 滑入 / 多米诺 / split / stagger"
- SplitText
- TextRoll
- Visual: 字母像多米诺骨牌依次站起
- Mass analogy: 苹果发布会逐字弹出

### "发光 / 渐变 / 流动 / 霓虹 / shiny / gradient / glow / neon"
- ShinyText
- GradientText
- Visual: 文字带流动光泽 / 渐变色
- Mass analogy: 品牌大字标题、广告灯箱

### "故障 / 抖动 / 错位 / glitch / shake / distort"
- GlitchText
- Visual: 文字像信号干扰一样抖动错位
- Mass analogy: 赛博朋克 UI、坏掉的电视

### "翻牌 / 计数 / number / counter / flip"
- CountUp
- TextRoll
- Visual: 数字滚动到目标值
- Mass analogy: 老式翻牌时钟、机场离港牌

---

## Backgrounds

### "渐变 / 流动 / aurora / 极光 / fluid"
- Aurora
- Silk
- Visual: 抽象色块缓慢流动
- Mass analogy: 极光、油画在动
- Engine: ogl (lightweight WebGL)

### "粒子 / 星空 / particles / stars / dots"
- Particles
- Threads
- Visual: 散点跟随鼠标 / 自由漂浮
- Mass analogy: 星空、烟花散落
- Engine: ogl 或 three

### "网格 / grid / dot grid / pattern"
- DotGrid
- Squares
- GridMotion
- Visual: 规则网格图案，随交互轻微响应
- Mass analogy: 设计师工具背景、blueprint

### "光线 / beams / rays / spotlight"
- LightRays
- Beams
- Visual: 几条光带斜射穿过画面
- Mass analogy: 舞台聚光、阳光透窗

### "波纹 / 水波 / waves / ripple"
- Waves
- LiquidEther
- Visual: 流体波纹起伏
- Mass analogy: 水面、声波

### "几何 / 抽象 / geometric / abstract"
- Hyperspeed
- LetterGlitch
- Visual: 高速几何图形 / 抽象代码雨
- Mass analogy: 赛博空间、代码下落

---

## Animations (UI primitives)

### "进场 / 出场 / 滚动出现 / animated content / scroll reveal"
- AnimatedContent
- FadeContent
- ScrollReveal
- Visual: 元素滚动到视口内时优雅出现

### "磁吸 / 鼠标跟随 / magnet / cursor follow"
- Magnet
- ClickSpark
- Visual: 鼠标靠近时元素被吸引

### "图片揭幕 / image reveal"
- ImageTrail
- PixelTransition
- Visual: 图片以特殊效果出现（碎片、像素化、滑入）

### "无限滚动列表 / marquee / 横向滚动"
- InfiniteScroll
- LogoLoop
- Visual: 内容横向无限循环

### "卡片堆叠 / stack / cards"
- CardSwap
- StackedCards
- Visual: 多张卡片堆叠 / 切换

---

## Components (interactive UI)

### "导航栏 / dock / dock bar"
- Dock
- GooeyNav
- Visual: macOS 风格 dock 或粘性导航

### "按钮 / 点击 / 涟漪 / button / click / ripple / tap"
- StarBorder
- ClickSpark
- Visual: 按钮带视觉反馈（边框星光、点击粒子）

### "聚光 / spotlight / 鼠标光晕"
- SpotlightCard
- TiltedCard
- Visual: 卡片随鼠标位置高光 / 倾斜

### "菜单 / 弹出 / fluid menu"
- FluidMenu
- BubbleMenu
- Visual: 菜单像液体一样展开

### "倒计时 / 计时 / counter"
- CountUp（也归入 text）
- Visual: 数字计数动画

---

## Scene-based filtering (NEW)

Every component in `visual-index-handcurated.json` now has a `scene` field: `landing`, `dashboard`, or `both`.

### How scene filtering works

1. Phase 2 L3 detects the project's scene type (LANDING / DASHBOARD / NEUTRAL)
2. Before scoring candidates, **hard-filter** by scene:
   - DASHBOARD scene → remove all candidates tagged `scene: landing`
   - LANDING scene → no filtering (all components are fair game)
   - NEUTRAL → no filtering

### What this means in practice

130 components break down as:
- `landing` only: ~83 components (dramatic, showcase, attention-grabbing)
- `both`: ~45 components (subtle enough for functional UI)
- `dashboard` only: 0 (nothing is dashboard-exclusive — `both` covers it)

So in a dashboard project, the candidate pool shrinks from 130 → ~45. This is the single biggest search-space reduction in the skill — more impactful than tone matching.

### Dashboard-safe components (quick reference)

**Text**: BlurText, TextType, ShinyText, GradientText, TrueFocus, RotatingText, CountUp
**Animations**: AnimatedContent, FadeContent, GlareHover, LogoLoop, GradualBlur, ClickSpark, Noise
**Components**: AnimatedList, CardNav, PillNav, TiltedCard, Masonry, GlassSurface, Folder, ProfileCard, Dock, Carousel, SpotlightCard, GlassIcons, ElasticSlider, Counter, Stepper
**Backgrounds**: FloatingLines, LineWaves, Radar, SoftAurora, Grainient, RippleGrid, DotField, DotGrid, Threads, Waves, Orb, ShapeGrid

### User override

If the user says "这个页面是 landing page" or "这是首页不是后台", override scene to LANDING for this task only. Do not persist to profile — the project-level scene stays DASHBOARD.

---

## Multi-keyword routing

When user input hits 2+ groups (e.g. "酷炫的 hero 标题"):
- "标题/hero/heading" → narrows to text-animations category
- "酷炫" → biases toward higher-impact options (DecryptedText / GlitchText) over restrained (BlurText / FadeText)

Combine: candidate pool = text-animations ∩ high-impact = [DecryptedText, GlitchText, ScrambleText, ShinyText]

Then Phase 2 sniffing eliminates based on tonality (minimalist project would still kick GlitchText out).

**Scene interaction**: if scene = DASHBOARD, the high-impact candidates above would ALL be filtered out (all are `scene: landing`). The result would be an empty pool → skill should tell the user: "你的项目看起来是后台/控制台，这些高冲击力的效果可能不太合适。要不要换个方向？比如用 ShinyText 做个低调的标题高光？" This is not a bug — it's the skill correctly protecting the user from inappropriate choices.

---

## Maintenance

**This file's component names are placeholders until `scripts/crawl-catalog.sh` runs and verifies them against reactbits.dev.** When the crawler runs:

1. It outputs verified `references/visual-index.md`
2. A second pass (`scripts/build-decision-tree.sh` — TODO) re-syncs this file's component lists against verified names

Do not hand-edit individual component entries — edit the keyword groups (which are the real intellectual property of this skill) and let the build pipeline fill in the names.
