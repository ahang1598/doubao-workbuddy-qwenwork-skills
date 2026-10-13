# 主视觉引擎（Hero Engine · 一个技术性奇观时刻）

> 定 signature motion 且需要"惊艳一下"时读。与 `motion-recipes.md`（日常 GSAP/CSS 配方）、
> `motion-quality.md`（时长/缓动/性能规则）配套：本文件是**奇观引擎层**——一页只做**一个**、做到 100%，通常在 Hero。

## 0. 铁律（先读）

- **一页一个引擎。** 全站只挑一个技术最野的视觉引擎，通常在 Hero 内/后。其余动效走 `motion-recipes.md`。
- **渐进增强**：把引擎整段删掉，页面仍完整可读。引擎挂在 `position:fixed;inset:0;z-index:0` 的画布上，内容 `z-index:5+`。
- **spectacle 必须真出现**：`art-direction.json` 声明了 signature motion,页面就必须真的动（Hero 入场 / 滚动揭示 / hover 物理,至少一样）。声明了不实现 = 失败。
- **reduced-motion 必降级**：`@media (prefers-reduced-motion:reduce)` 停在静止帧或直接显示静态 Hero。无降级即不完整。
- **只动 `transform`/`opacity`**（DOM）；canvas 端把每帧工作压到能稳 60fps;`canvas.width = innerWidth*devicePixelRatio`（否则 retina 糊）。

## 1. 飞书嵌入安全边界（最重要,先判再选引擎）

产物是**飞书 html5-block（iframe 单文件）**还是**工作区/独立 HTML**,决定能用哪一档引擎:

| 引擎档 | 飞书 iframe 嵌入 | 说明 |
|---|---|---|
| **CSS-only**（mask/3D transform/scroll-timeline/变量字重） | ✅ 安全 | 无 JS 库,最佳性能,widget 首选 |
| **GSAP**（ScrollTrigger/timeline） | ✅ 安全（**内联注入**,不靠外链 CDN） | 库 ~113KB,base64 内联进单文件;`build_widget` 会打包 |
| **Canvas 2D**（粒子/场/实时数据） | ✅ 安全 | 原生 API,无外部库 |
| **Three.js / WebGL-FBO**（3D/流体/ray-march） | ⚠️ **仅工作区/独立 HTML** | 依赖 import map + CDN,飞书 iframe 的 CSP 常拦 → 碎裂。**别嵌进飞书 widget** |

> 这与"产物在宿主里断链"是同一课：**本地能跑 ≠ 飞书 iframe 能跑**。要在飞书文档里嵌 Three.js Hero,
> 改为"生成一张高清静帧证据图放文档 + 引擎只在工作区独立 HTML 演示"。

## 2. 引擎档梯（按 SPECTACLE dial 与 soul 选一个）

| 档 | 引擎 | 用于 | 门槛 |
|---|---|---|---|
| A | **Three.js + GLSL**（3D 深度/粒子/bloom） | 天文、AI/神经、加密网络、科学 | SPECTACLE ≥7,懒加载 ~150KB |
| B | **Canvas 2D**（粒子场/实时数据） | 数据流、网络图、生成艺术 | SPECTACLE 5–7 |
| C | **WebGL FBO shader**（流体/反应扩散/ray-march） | 涌现/物理主题 | SPECTACLE ≥8,GPU 重,慎用 |
| D | **GSAP ScrollTrigger**（滚动叙事,主力） | 滚动叙事、横向 pan、视差、揭示 | SPECTACLE 4–7,几乎任何 soul 都行 |
| E | **CSS-only**（双层鼠标 mask/3D 立方/变量字/原生 scroll-timeline） | 交互揭示、动态字、极致性能 | 免费、最佳性能,罕见=最有记忆点 |

`bolder` = 往上升一档并 +2 SPECTACLE;`quieter` = 往下降一档并 −2;`animate` = 只换引擎不碰配色/版式。

## 3. CSS-only 档配方（widget 首选,飞书安全）

**双层鼠标 mask 揭示**（露出底层第二张图）:
```css
.reveal-wrap{position:relative}
.layer-night{position:absolute;inset:0;background:url(reveal.jpg) center/cover;
  -webkit-mask:radial-gradient(circle 180px at var(--mx) var(--my),#000 0,transparent 100%);
          mask:radial-gradient(circle 180px at var(--mx) var(--my),#000 0,transparent 100%);}
/* JS: wrap.onpointermove = e=>{ el.style.setProperty('--mx',e.offsetX+'px'); el.style.setProperty('--my',e.offsetY+'px') } */
```
**原生滚动揭示**（零 JS,自动 reduced-motion 友好）:
```css
@media (prefers-reduced-motion:no-preference){
  .reveal{animation:rise linear both;animation-timeline:view;animation-range:entry 0% cover 35%}
  @keyframes rise{from{opacity:0;transform:translateY(40px)}to{opacity:1;transform:none}}}
```

## 4. 指针倾斜卡（3D 签名动作,CSS,组件级可复用）

```css
.tilt{transform:perspective(900px) rotateX(var(--rx)) rotateY(var(--ry));transition:transform .1s}
/* JS: card.onpointermove = e=>{ const r=card.getBoundingClientRect();
   card.style.setProperty('--ry',((e.clientX-r.left)/r.width-.5)*10+'deg');
   card.style.setProperty('--rx',-((e.clientY-r.top)/r.height-.5)*10+'deg') } */
```
配套 3D 组件动作：翻卡(front⇄back,`rotateY(180deg)` + `backface-visibility:hidden`)、
coverflow 3D 轮播、深度视差层(鼠标反应,多层不同 `translateZ`)。**3D 要挣它的位置**：
不服务内容的旋转/倾斜是噪音;每个 3D 动作要能一句话说清"它在表达什么"。

## 5. GSAP / Canvas 骨架（详见 motion-recipes.md）

- **GSAP ScrollTrigger 揭示/pin/视差**：`motion-recipes.md` §B/§C 已有可套配方,内联注入不外链。
- **Canvas 2D 粒子场**：单个全屏 canvas,`requestAnimationFrame` 循环,粒子数按屏宽自适应,
  `prefers-reduced-motion` 时只画一帧静态。不触 React state,用普通变量。
- **酷炫插件效果**（逐字揭示/乱码解码/线条自绘/形状变形/路径运动/布局转场）：
  别手搓,查 `motion-patterns.md` §F「效果→插件」表,插件 API 在 `motion/gsap/gsap-plugins.md`,
  全部免费含商用;飞书 widget 里像 core 一样内联注入。

## 6. 选择速查

| soul / SPECTACLE | 引擎 | 飞书嵌入 |
|---|---|---|
| 数据/生成艺术 · 5–7 | B Canvas 2D | ✅ |
| 滚动叙事/视差 · 4–7 | D GSAP ScrollTrigger | ✅（内联） |
| 交互揭示/动态字/极致性能 · 3–6 | E CSS-only | ✅ |
| 3D 物体/科学/AI 奇观 · 7+ | A Three.js | ⚠️ 仅独立 HTML |
| 流体/涌现物理 · 8+ | C WebGL FBO | ⚠️ 仅独立 HTML |

**默认**：不确定就选 D（GSAP,几乎万能）或 E（CSS,最安全）。要嵌飞书文档且想上 3D → 交静帧图,引擎放独立 HTML。
