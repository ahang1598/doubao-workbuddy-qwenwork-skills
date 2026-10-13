# UI 动效质感

动效服务叙事与状态，不是效果计数。旗舰页需要**一个编排过的 signature motion**；禁止「每个区块千篇一律 fade-up」，也禁止为凑数量堆微动效。

## Web 真实视频合同

官网 / 网站 / Landing / Web Dashboard 的 `web-dual` 链按 `mediaIntent` 决定是否需要真实视频。
“酷炫、沉浸、电影感”可以由排版、材质、空间、交互和 CSS 动效实现，不能单独作为强制视频证据；
只有 query 明确要求视频/动态影像/持续运动、参考含真实时间帧，或内容职责确实依赖时间媒体时，
才生成 5–8 秒视频。主体、镜头、材质、速度与章节位置继续由
`designIntent + layoutRecipe + contentPlan + referencePolicy` 推导。

执行顺序固定：

```text
assets：只生成同主体 poster
→ ui：完整 poster 站点，视频槽为 PLANNED
→ publish + host-verify：完整 Doc 最终宿主 PASS
→ media：验证容器/视频轨/正时长/媒体数据后，用状态门内的 bind_site_media.py 绑定
→ bundle：上传媒体、编译 Web 卡片、浏览器验证 canPlay/play/currentTimeAdvanced
→ finalize：只交 Doc + 已验 Web 卡片
```

`mediaIntent.required=false` 是正式设计判断，不是降级：保留必要的状态反馈、滚动叙事与
`prefers-reduced-motion`，但不创建空视频槽。若 `required=true`，不能因为视频工具需要确认、耗时或
能力不稳定而自行删除视频；若工具强制确认，只能在 media 阶段汇总一次。此时
`prefers-reduced-motion` 显示 poster，不能把视频删除后仍声称动态官网已完成。

> **"不数数量"不等于"可以没有"。** `check_ui_quality` 有三条正向门：必须有 `@keyframes`/`animation`
> （只有 `transition:` 不算）、必须有入场/滚动揭示、必须有 `prefers-reduced-motion` 降级。
> 下限之上做多少由本文件的四层预算决定；**做没做**是硬门。
>
> 飞书 html5-block 内：CSS-only 引擎最安全，GSAP 必须**内联注入**（下面的 CDN `<script>` 写法只适用于
> 独立 HTML——飞书 iframe 的 CSP 会拦掉外链，页面就悄悄变回静态）。见 `hero-engines.md` §1。

## 动手前

1. 本文 `motion/motion-quality.md`
2. `motion/impeccable-animate.md`（策略与 CSS 质感基线）
3. 需要愉悦细节时读 `motion/impeccable-delight.md`
4. 复杂序列 / 滚动 / React 时按需读：
   `motion/gsap/gsap-core.md` · `motion/gsap/gsap-timeline.md` · `motion/gsap/gsap-scrolltrigger.md` · `motion/gsap/gsap-react.md` · `motion/gsap/gsap-plugins.md` · `motion/gsap/gsap-utils.md` · `motion/gsap/gsap-performance.md` · `motion/gsap/gsap-frameworks.md`
5. 配方速查：`motion/motion-recipes.md`
6. 许可：`references/motion/gsap/LICENSE`

## 技术选型

| 场景 | 选型 |
|---|---|
| 按钮 hover、颜色、简单显隐、150–300ms 反馈 | **CSS transition / @keyframes** |
| Hero 入场编排、多元素 stagger、可暂停序列 | **GSAP timeline**（CDN 或 npm） |
| 滚动揭示、pin、scrub 视差 | **GSAP ScrollTrigger** |
| React 组件内动画 | **gsap-react**（useGSAP + 清理） |
| 鼠标跟随、高频更新 | **gsap.quickTo**（见 performance） |

**独立** 单文件 HTML 落地页（不进飞书文档时）可用 CDN：

```html
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/ScrollTrigger.min.js"></script>
```

**进飞书 html5-block 时禁止外链**：iframe CSP 会拦掉，页面变回静态且不报错。
要么把 GSAP 内联进单文件（吃约 113KB 的 500KB 预算），要么改用 CSS-only 档：

```css
@media (prefers-reduced-motion:no-preference){
  [data-reveal]{animation:rise linear both;animation-timeline:view;animation-range:entry 0% cover 30%}
  @keyframes rise{from{opacity:0;transform:translateY(32px)}to{opacity:1;transform:none}}
}
```

## 质感配方（时长与缓动）

| 时长 | 用途 |
|---|---|
| 100–150ms | 按下、颜色、开关 |
| 200–300ms | 菜单、hover 抬起、卡片 |
| 300–500ms | 抽屉、手风琴、布局 |
| 500–800ms | Hero 入场、主打揭示 |

CSS 缓动（避免线性/默认 ease）：

```css
--ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
--ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
```

GSAP 缓动优先：`power2.out`、`power3.out`、`power3.inOut`。  
旗舰娱乐页可用轻微 `back.out(1.2)`；**避免**夸张 bounce/elastic 除非品牌明确要求。

退出 ≈ 入场的 75% 时长。

## 四层动效预算

实现前在内部列清单（可写入注释）：

1. **主打时刻（1 个）**：Hero 编排 / 唱片旋转+光晕 / 首屏时间轴  
2. **反馈层**：按钮 press、播放态、Tab 指示器滑动  
3. **过渡层**：区块入场 stagger、锚点平滑、移动菜单  
4. **愉悦层（≤2）**：声波、光球漂浮、空状态微动——不打断任务  

四层预算的具体表现也必须服从 query。它规定注意力层级，不规定“光球 + 粒子 + 赛博扫描”
这一套固定皮肤；同一产品目标下，换了受众、品牌材料或参考意图，动效语言应产生可解释的变化。

沉浸型消费品类（音乐、影音、游戏、娱乐）：主打 + 反馈 + 过渡 **必须满**；愉悦层至少 1。

## 性能硬规则（来自 gsap-performance）

- 只动画 **transform / opacity（autoAlpha）**；不用 top/left/width 做位移  
- `will-change` 仅加在实际动画元素  
- 滚动揭示用 ScrollTrigger 或 IO，勿每区块复制同一套无编排 fade  
- 屏外动画 pause/kill；尊重：

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

GSAP：`gsap.matchMedia` / `ScrollTrigger` 在 reduce 时简化为即时 set。

## 品类最低条（与 craft-quality 对齐）

**音乐落地页：** ≥3 种可感知动效，且至少含：

- Hero timeline 入场（标题/CTA/主视觉错峰）  
- 滚动区块 stagger 或 scrub 视差（克制）  
- 持续氛围（唱片旋转 / 光球 / 波形）之一  
- 交互反馈（播放按钮、卡片 hover 抬起+光晕）

**SaaS/后台：** 反馈+过渡即可；主打时刻可选。

## 反模式

- 每个 section 相同无编排 fade-up（应用 GSAP timeline / batch 做出节奏差）  
- 忽略 reduced-motion  
- 十多个无限循环抢注意力  
- 为「有动效」而动画 layout 属性导致卡顿  
- 读了 motion/GSAP 资产却仍交静态页

## 延伸阅读

- `impeccable-animate.md` / `impeccable-delight.md`  
- `gsap/gsap-core.md` · `gsap-timeline.md` · `gsap-scrolltrigger.md` · `gsap-performance.md`  
- 框架：`gsap-react.md` · `gsap-frameworks.md`  
- 插件：`gsap-plugins.md` · `gsap-utils.md`  
- 落地配方：`motion-recipes.md`  
- 许可：`gsap/LICENSE`（MIT, GreenSock）
