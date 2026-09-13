# 视觉技法

主 SKILL.md 之外的技术手段清单：动效、Canvas / WebGL、进阶排印、材质、地图、音频、音画协同、数学公式，以及各自的 slop 红线。视觉方向本身由 `frontend-design.md` 决定，本文只回答方向定了怎么落地。

## 动效

一个页面最多 1–2 个动效锚点（如 hero 入场 + 一段 scroll-pin 叙事），其他地方保持静止或最多一次 200ms hover。不要给每个元素都套 fade-in-up。

**选型**：

- **IntersectionObserver + CSS transition / keyframes**：任何页面的默认。禁用 AOS（`data-aos` 是典型 template 味）。
- **View Transitions API**：多视图 / hash 路由切换的原生方案，`document.startViewTransition()` 一行搞定。
- **GSAP + ScrollTrigger**：需要时间线、pin / scrub、复杂 stagger 时用。
- **anime.js**：轻量 stagger、SVG stroke draw、数字 tween。不需要 ScrollTrigger 时比 GSAP 便宜。
- **Lottie**（`lottie-web`）：AE / Figma 导出的矢量动画。
- **Web Animations API**（`element.animate()`）：JS 精确控制播放 / 暂停 / 反转时用。

**编排**：入场 ≤ 600ms，缓动用 `cubic-bezier(0.22, 1, 0.36, 1)` 或 `expo.out`；stagger 步长 40–80ms，超 100ms 拖沓；`prefers-reduced-motion: reduce` 时禁用所有动效。

**slop 红线**：

- 全站 `data-aos="fade-up"`
- hero 里飘几个"粒子"点当装饰
- 数字 counter 从 0 滚到目标（除非页面就在讲一次增长）
- 弹跳（bounce）出现在企业 / 数据类内容
- typewriter 打字机（除非主题是终端 / 写作 / AI）

## 滚动叙事

滚动本身就是叙事节奏时用：长文数据报道、教学解释、按步骤揭开的推演。工具层：

- **Scrollama.js**（4KB）：段落进入 / 离开 viewport 触发 callback。不需要 scrub / pin 时首选。
- **GSAP ScrollTrigger**：pin viewport、scrub 数值、复杂时间线用它。
- **CSS `scroll-timeline` / `view-timeline`**（Chrome/Edge 115+）：纯 CSS scroll-driven。做 progressive enhancement，别当主动效。

**编排**：一屏一个论点；主图区 pin 住，文字流从旁边过；数据切换用 300–500ms 插值，不硬切；末态可读——滚完停下的最后一屏能独立成立，不是动画中间帧。图表相关的 scrollytelling 更多编排细节见 `chart-atlas.md` 数据叙事模式段。

## 可交互解释（explorable explanation）

读者拖滑块 / 换参数直接看结果变化。教学、论文、概念解释类主题的天花板。

- 参数控件用原生 `<input type="range">` / `<input type="number">`，不自造滑块——原生的键盘可达、无障碍。
- 每次变化即时反馈（≤ 16ms 一帧），用 `requestAnimationFrame` throttle。
- 参数与图表双向绑定——既拉滑块看图变，也允许点图上某点回填参数。
- 一次给 1–2 个参数，别塞满一屏滑块。

## Canvas / WebGL / 生成式

签名元素本身是视觉 / 交互瞬间、纯 SVG / CSS 撑不起来时用。

- **three.js**（~150KB）：3D 场景、光影、材质、shader。用 `OrbitControls` 让用户拖动比自动旋转更有记忆点。
- **p5.js**（~250KB）：generative art、粒子系统、Perlin 噪声、流场。
- **matter.js**（~90KB）：2D 物理引擎。做拖拽实验、掉落文字、碰撞球这类可交互 hero。
- **PixiJS**：2D 大量精灵，比 canvas 2D API 快一个量级。
- **原生 Canvas 2D**：波纹、噪点、时钟这类 100 行内的场景。
- **手写 shader / WebGL**：明确要做后处理效果时才走，否则用 three.js 现成的 postprocessing。

**判断**：具象画面走图片，抽象 / 氛围 / 交互 hero 走 Canvas / WebGL；单页值得引，多页产物慎重；`<canvas>` 挂载失败或 `prefers-reduced-motion` 时必须有静态版兜底；**禁用粒子网背景**（线连点的 particles.js 效果）。

## 进阶排印

- **variable fonts**：`font-variation-settings: 'wght' 850, 'wdth' 60`。展示字用 variable 才能做出真正的层级差。
- **`background-clip: text` + gradient / image**：`color: transparent; -webkit-background-clip: text;`。一个词的 hero 大标题用，通篇滥用即 slop。
- **`-webkit-text-stroke` + `color: transparent`**：描边字。
- **SVG `<textPath>`**：字沿路径走。徽章、圆形标语、非线性排版。
- **SVG `<filter>` feTurbulence + feDisplacementMap**：文字加程序化噪声 / 扭曲，做有机 / 手作 / 实验性调性。
- **CSS `writing-mode: vertical-rl`**：中文竖排、日式编辑设计。
- **`font-feature-settings`**：`'tnum'`（等宽数字，数据表必开）、`'onum'`（旧式数字）、`'ss01'`（stylistic set）、`'dlig'`（discretionary ligatures）。同字体开不同 feature = 免费的另一副面孔。
- **`text-wrap: balance / pretty`**：多行标题自动均衡断行，比手写 `<br>` 优雅。

**slop 红线**：

- 全站一个字体（Inter / Roboto）撑所有层级
- 展示字用 Fraunces / Playfair 且配陶土色
- 全大写 + `letter-spacing: 0.2em` 当所有小标题
- 数据表数字不开 `tnum`，列头飘忽

## 材质 / 纹理

扁平白底 + 卡片 + 圆角是 AI 生成设计的舒适区。加一层材质拉开距离：

- **Grain / 噪点 overlay**：SVG `feTurbulence` + `mix-blend-mode: overlay`。整站铺 0.03–0.08 透明度，观感从「AI 生成」变「印刷品」。
- **Duotone**：`feColorMatrix` 或两层图 + `mix-blend-mode: multiply / screen`。
- **Halftone**：`feMorphology` + `feComponentTransfer`，或 CSS `radial-gradient` 圆点阵列。复古印刷、漫画、报纸调性。
- **Paper / grid / dot grid 底纹**：`repeating-linear-gradient` / `radial-gradient` 一行 CSS 出方格纸、点阵纸、绘图纸。
- **`mask-image`**：用图当遮罩挖形状。
- **`mix-blend-mode`** 与 **`backdrop-filter`**：叠色、透过背景的模糊。blur 慎用，毛玻璃已是 slop 高发区。
- **`conic-gradient`**：一行 CSS 出圆盘 / pie 装饰 / 高光。

**slop 红线**：

- 毛玻璃 / glassmorphism
- glow border 卡片描边发光渐变
- neumorphism 内外阴影模拟凸起
- 通篇渐变背景（尤其紫蓝紫粉）
- cursor 光晕跟随 spotlight

## 地图 / 地理可视化

"发生在哪里"类叙事：迁徙、战役、港口史、疫情、气象、邮政路线、灯塔、火山、铁路、潮汐。手写 SVG 硬画是笨。

- **Leaflet**（40KB）：交互式瓦片地图的通用选择。不需要 3D / GL 时首选。
- **MapLibre GL**（~200KB）：Mapbox GL 开源分支。矢量瓦片、3D 建筑、地形阴影。**不用 Mapbox**（需 access token）。
- **D3-geo**：静态地图 / choropleth / 投影切换。Natural Earth 的 TopoJSON 是标配数据源。
- **Deck.gl**（+ MapLibre）：> 10 万点、GPU 加速的热力 / 六边形聚合 / arc 弧线。

**瓦片来源**（免费、无 key）：OpenStreetMap（`tile.openstreetmap.org/{z}/{x}/{y}.png`，attribution 必须写 `© OpenStreetMap contributors`）、CartoDB Positron / Dark Matter / Voyager（数据可视化首选，背景不抢戏）、Stamen Terrain / Toner（需 Stadia Maps key）、Esri World Imagery（卫星）。**禁用**：Google Maps、Mapbox 默认 style。

**判断**：信息型（读者要读位置 / 密度）用 Leaflet / D3-geo；氛围型（主题装饰）用 SVG 硬画；世界地图不用 Mercator，用 Robinson / Natural Earth / Winkel Tripel；区域地图 Mercator / Albers 都行；> 10000 点用 Deck.gl 或 markercluster；choropleth 用 `d3-scale-chromatic` 的 viridis / cividis / RdBu，**禁 rainbow / jet**。

**slop 红线**：

- 全球地图用 Mercator（非洲被压扁）
- Google Maps 默认样式当数据底图
- Leaflet 默认蓝色 marker 大头针挂满地图
- 3D 地图旋转 / tilt 只为炫技
- rainbow 色板 choropleth
- 无 attribution

## Web Audio / 声音

音频 / 音乐 / 声学主题：乐器、鸟鸣、歌剧、电子音乐、Podcast、可听化数据。声学类主题加一段可 hover 试听的短音，signature 记忆点显著加强。

- **Tone.js**（~180KB）：Web Audio 高层封装，语义化的 Synth / Sampler / Effect / Sequence。做音乐、可交互音景、按拍子触发音频时用。
- **原生 Web Audio API**：`AudioContext` / `OscillatorNode` / `GainNode` / `AnalyserNode`。单音合成、频谱可视化时几十行手写比引 180KB 库划算。
- **Howler.js**（~10KB）：只播已有音频文件、控音量、循环。
- **Meyda**：音频特征提取（MFCC、RMS、spectral centroid）。

**判断**：单音 / 音效 → 原生 `AudioContext` + `OscillatorNode`；音乐 / 节奏 / 音序 → Tone.js；播已有文件 → Howler.js；音频驱动可视化 → 原生 `AnalyserNode` + Canvas。

**交互红线**：

- 音频必须 user gesture 触发（`AudioContext` 默认 suspended，需点击后 `resume()`）。**不允许自动播放**。
- 明显的静音开关，右上角固定可见。
- 单音 attack / release 至少各 5ms，避免爆音。
- 音量默认 0.3–0.5，不给 1.0。
- 低频（< 60Hz）音量再削一档，笔记本喇叭放不出还容易破音。
- 移动端页面默认不加音频。
- **iOS 侧面静音开关会静音 Web Audio 合成音**（`OscillatorNode` / `AudioBufferSourceNode` 等程序化音频归 ambient 类别，受静音开关控制；`<audio>` 标签播放的音频文件走 playback 类别不受影响）。处理：`AnalyserNode` 播放 500ms 后采样 `getByteFrequencyData`，若数组全 0 且 UA 是 iOS，显示灰色小字提示 `iPhone 请关闭侧边静音键` + 侧边开关小 SVG icon。不用弹窗 alert / 大警告框 / emoji 图标——灰色小字 + 图形化 icon 就够。

**Sonification（数据可听化）** 慎用——大部分时候图表比声音传信息更快，只在特定叙事时刻成立（"听一下这条曲线"）。不要整个 dashboard 听化。

**slop 红线**：

- 加载即自动播放
- 音频驱动的粒子背景（"音乐可视化屏保"）
- 每个 UI 元素 hover 都发不同音
- 找不到 mute

## 动画 + 声音协同

带旁白的分幕演绎、可交互的乐器 hero、按节拍编排的 rhythm 段——两者必须共享一条时间线。

**用音频时钟为主**：`audioContext.currentTime` 是硬件时钟，稳定不漂移。`performance.now()` / rAF 会随浏览器帧率抖动，几十秒后就能看出音画错位。每帧 rAF 读 audio 时钟反推动画状态，不反过来用视觉时间去 seek 音频。

**三种协同模式，选一种别混**：

- **音频驱动动画**（旁白 / 音乐 / 频谱可视化）：主时钟是音频文件的 `currentTime` 或 `AnalyserNode` 实时频谱。旁白播到第 N 秒动画切到第 N 幕。
- **动画驱动音频**（可交互 hero、章节切换音）：视觉事件触发 `AudioBufferSourceNode.start()` 或 `oscillator.start()`。只在语义关键点响，不是每个 hover 都响。
- **共享时间线**（rhythm 类 / TED-Ed 分幕）：`Tone.Transport` + GSAP timeline 共用 tempo。音效用 `Tone.Transport.schedule(fn, "0:2:0")`，动画用 GSAP timeline 绝对时间轴，两条时间线用同一个 bpm 派生。**不用 setTimeout 排音效**——跟 audio 时钟不同源，一定漂。

**首次交互门槛**：AudioContext / Tone 都需 user gesture 后才能 `resume()` / `Tone.start()`。页面必须有一个显性的"点击开始"入口（hero 大按钮 / 页头耳机 icon），点击前动画可播静音版。

**reduced-motion 关双通道**：`prefers-reduced-motion: reduce` 触发时动画和音频都停。无障碍用户往往同时敏感于视觉和听觉刺激。

**Mute 按钮**：右上角固定，键盘可达（`role="switch"` + `aria-checked`）；`localStorage` 存偏好；淡出用 `gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.05)`，不硬切。

**slop 红线**：

- 音乐可视化跳舞背景
- 音画偏差 ≥ 200ms（专业媒体门槛是 40ms）
- 每个 hover 都发音
- 找不到 mute
- 加载即响
- `setTimeout` / `setInterval` 排音效事件

## 数学 / 公式排版

物理、工程、经济、金融、机器学习、化学式、统计学。不用截图代替公式。

- **KaTeX**（~60KB）：单页 HTML 首选。静态渲染，无运行时开销，覆盖 99% 常见公式。用法：`katex.render("c = \\pm\\sqrt{a^2 + b^2}", element, {throwOnError: false})`。auto-render 扩展扫描 `$...$` / `$$...$$`。
- **MathJax**（500KB+）：KaTeX 覆盖不到时用——化学分子式（mhchem 扩展 `\ce{H2O}`）、复杂 commutative diagram、超长 tensor。
- 只有一两个公式 → `<img>` 或 SVG 静态图更省。

**排版**：inline 公式 baseline 对齐正文（用库自带，不手调 `vertical-align`）；被引用的展示公式带编号（`\tag{1}`）；变量斜体、常量 / 单位正体（`\mathrm{d}x`），HTML 里提到变量也一致；多行推导用 `\begin{aligned} ... &= ... \\ ... &= ... \end{aligned}` 让等号对齐；公式与图共存时符号完全一致（不要一处 `\alpha` 另一处 `a`）。

**slop 红线**：

- 公式截图
- Unicode 假装公式（`x² + y² = r²`）
- 公式和正文字体割裂
- 长公式不折行横向溢出
- KaTeX 默认 1em 在正文偏大，调 `0.95em`

## 无障碍与性能底线

- `prefers-reduced-motion: reduce` 时禁用所有动效，配合音频时音频也停。
- `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }`，别把 outline 关掉不给替代。
- 对比度：正文 ≥ 4.5:1，用 oklch 调 lightness 时手动核。
- `will-change: transform` 只在真正需要时加，动画结束后移除。
- three.js / p5.js 用动态 `import()` 懒加载，首屏别拉。
