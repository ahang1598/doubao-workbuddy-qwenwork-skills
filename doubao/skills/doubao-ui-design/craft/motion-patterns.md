# 交互动效模式菜单（从获奖动效站提炼的可复用招式）

> 定 signature motion 或想让页面"活起来"时,从这里挑招。与 `hero-engines.md`（一页一个的奇观**引擎**）分工：
> 本文件是**更广的日常动作菜单**——可在一页里用多个,不违反"一页一引擎"。
> 每招都要有**被激发的理由**（层级/叙事/反馈/状态变化其一,说不出理由就删）+ `prefers-reduced-motion` 降级。
> 全部**框架无关**（vanilla JS / CSS 思路),不含任何品牌名、素材 URL 或框架专属代码。

## 选招原则

1. **一个动作服务一件事**：吸引注意（层级）/ 按顺序揭示（叙事）/ 确认操作（反馈）/ 表达状态变化。为炫而炫的一律删。
2. **飞书 iframe 安全**：CSS + vanilla JS + 内联 GSAP 安全;WebGL/Three.js 只在独立 HTML（见 `hero-engines.md` §1）。
3. **reduced-motion**：无限循环/视差/滚动劫持/磁吸,在 `prefers-reduced-motion:reduce` 下必须塌成静态或瞬时。
4. **节制**：marquee 每页 ≤1;巨型滚动劫持每页 ≤1;不是每张卡都要无限循环。

## A. 光标反应类（桌面增强,触屏降级）

| 招 | 是什么 | 何时用 | 飞书 |
|---|---|---|---|
| **聚光揭示 spotlight-reveal** | 光标处 radial mask 露出底层第二张图/视频 | 产品"表里两面"、before/after | ✅ CSS mask |
| **鼠标拖尾 mouse-trail** | 光标经过处掉落渐隐微旋图片/粒子 | 作品集、创意工作室、"手作感"卡片 | ✅ vanilla JS |
| **磁吸按钮 magnetic** | CTA 向光标轻微靠拢(translate ≤8px)再弹回 | 主 CTA、少数关键按钮(别全站) | ✅ |
| **指针倾斜 pointer-tilt** | 卡片按光标位置 3D 微倾(`perspective`+`rotateX/Y`) | 产品卡、特性卡的签名动作 | ✅ CSS(见 hero-engines §4) |
| **光标聚焦模糊** | 悬停项清晰,其余轻微 blur/降透明 | 画廊、导航大项 | ✅ |

> 触屏无 hover：以上均需 fallback（触摸跟踪 或 直接显示揭示态）,不能做成触屏上死掉的交互。

## B. 滚动驱动类（叙事骨架）

| 招 | 是什么 | 何时用 | 飞书 |
|---|---|---|---|
| **滚动揭示 stagger** | 元素进视口时依次上浮淡入(错峰,非同一套 fade-up) | 特性列表、证据网格、口碑 | ✅ CSS scroll-timeline 或内联 GSAP |
| **pin 钉屏叙事** | 一段 section 钉在视口,内容随滚动切换 | Hero 故事、步骤流程、产品分幕 | ✅ GSAP ScrollTrigger(内联) |
| **横向滚动劫持** | 纵向滚 → 横向 pan 一条轨道 | 画廊、时间线、"目录横铺"（每页 ≤1） | ✅ |
| **视差 parallax** | 前后景不同速位移建立深度 | Hero 影像、章节转场 | ✅（`transform`,别动 top/left） |
| **数字滚动 counter** | 进视口时关键数字从 0 滚到终值 | 数据证据段、KPI(结束帧即终值,reduced 直显) | ✅ |
| **卡片飞入 fly-in** | 横向 pin 轨道里每张卡各自随横向位置入场 | 横铺画廊里的单卡强调 | ✅ |
| **曲线揭幕 curtain-wipe** | 实色面板 `scaleX/Y` 1→0 揭开下层,随滚动 scrub | before/after、"背后是什么"一击 | ✅ |

## C. 文字类（记忆点,留给少数关键标题）

| 招 | 是什么 | 何时用 |
|---|---|---|
| **逐字揭示 split-char** | 标题每字/词包 mask,错峰上浮入位(非整行淡入) | Hero 标题、章节首(只留几处,不是每个 h2) |
| **动态字重 variable-font** | 悬停/滚动时字重或字宽形变 | 品牌巨字、导航大项 |
| **打字/解码 typewriter / scramble** | 逐字打出 或 乱码收敛成词 | 终端/科技 soul 的 Hero 一处 |
| **跑马灯 marquee** | 文字/Logo 横向无限滚,可随滚动反向 | 口号带、Logo 墙(每页 ≤1,别当默认填充) |

## D. 图像与转场类

| 招 | 是什么 | 何时用 | 飞书 |
|---|---|---|---|
| **图像位移悬停 displacement** | 悬停时图片按噪声图扭曲/融化 | 作品缩略、Hero 图(WebGL) | ⚠️ 独立 HTML |
| **coverflow 3D 轮播** | 卡片沿 3D 弧排列,两侧带角度 | 精选作品、产品切换 | ✅ CSS 3D |
| **翻卡 flip** | 悬停/点击 `rotateY(180deg)` 翻到背面 | 团队卡、定价对比 | ✅ |
| **异形蒙版转场** | 波浪/拱门/凹口 `clip-path` 切换色域 | 章节换气(与 aesthetic-baseline §8 呼应) | ✅ |
| **玻璃层 glass** | `backdrop-filter:blur` 上浮面板 + 1px 内高光 | 影像底上的导航/信息面板(F17;非默认装饰) | ✅（备 `prefers-reduced-transparency` 实底降级） |

## E. 氛围类（背景,不抢内容）

- **粒子/场 canvas**：全屏 canvas 慢速粒子/连线,`rAF` 循环,数量随屏宽自适应,reduced 只画一帧。✅
- **网格渐变 mesh / blob**：多个大模糊径向渐变缓慢漂移(有机熔岩灯感)。✅ CSS/SVG,注意别和内容抢对比。
- **噪点/颗粒 grain**：仅加在 `position:fixed;pointer-events:none` 的伪元素上,**绝不加在滚动容器**（否则移动端持续重绘掉帧）。

## F. 酷炫效果 → 已内置的 GSAP 插件（别手搓,直接用）

以下"炫"效果不用手写——`motion/gsap/gsap-plugins.md` 里都有现成插件,**全部免费含商用**
（Webflow 收购 GSAP 后 Club 插件已全免,无需 auth token/会员）。想让 UI 酷一点,先查这张表再动手：

| 想要的效果 | 用这个插件 | 一句话 |
|---|---|---|
| 逐字/逐词揭示、字符错峰入场（§C split-char） | **SplitText** | 把标题拆成 char/word/line 的 span,配 stagger 一行搞定 |
| 乱码解码成词、matrix 感（§C scramble） | **ScrambleText** | 文本从乱码收敛成目标词 |
| 线条自绘、描边生长、手写签名感 | **DrawSVG** | SVG 路径按 `"start% end%"` 描边动画 |
| 图标/logo/blob 平滑变形 | **MorphSVG** | 一个形状平滑 morph 到另一个 |
| 元素沿路径飞行、曲线跟随、轨道 | **MotionPath** | 让元素沿 SVG path 或坐标数组运动 |
| 列表重排、卡片展开、共享元素转场（§D flip 的进阶） | **Flip** | 记录前后布局,自动补间中间态（FLIP 技术) |
| 可拖画廊/旋钮/滑块 + 惯性甩动 | **Draggable + Inertia** | 拖拽 + 松手后带惯性滑行 |
| 无滚动条的滚动劫持、统一 wheel/touch/pointer | **Observer** | 一套 API 收各种输入,做全屏翻页/劫持 |
| 平滑滚动 + 视差（配 ScrollTrigger） | **ScrollSmoother** | 惯性平滑滚 + `data-speed` 视差 |
| 粒子爆炸、物理掉落抛洒 | **Physics2D** | 速度/角度/重力驱动的物理运动 |
| 自定义弹性/摆动/回弹缓动 | **CustomWiggle / CustomBounce / CustomEase** | 造独特缓动曲线,摆脱默认 ease |

> **飞书 widget 里用插件**：和 GSAP core 一样**内联注入**（base64/inline,不靠外链 CDN;`build_widget` 打包）——
> 飞书 iframe 的 CSP 会拦外链。每个插件效果仍要 `prefers-reduced-motion` 降级。
> 插件 API、注册方式、参数细节全在 `motion/gsap/gsap-plugins.md`,按需读。

## G. 验收（交付前）

- [ ] 每个动作能一句话说清服务什么(层级/叙事/反馈/状态);说不出的已删
- [ ] `prefers-reduced-motion:reduce` 下无限循环/视差/劫持/磁吸全部塌为静态,且首屏不空白
- [ ] 只动 `transform`/`opacity`;grain/particle 在 fixed 层
- [ ] marquee ≤1、巨型滚动劫持 ≤1;不是每张卡都循环
- [ ] 要嵌飞书的,没有用到 WebGL/Three.js（那类只进独立 HTML,飞书里交静帧图）
