# React Bits — Visual Index

> **STATUS: AUTO-GENERATED** by `scripts/crawl_catalog.py` on `2026-05-25T04:01:23.786851Z`.
> 
> Hand-edits to component rows will be **overwritten** on next crawl.
> To customize tone/visual/analogy, edit `references/visual-index-handcurated.json` instead — those fields are merged in.

## Schema

- **Slug**: kebab-case, matches reactbits.dev URL
- **Pascal**: install alias suffix (e.g. `BlurText` → `@react-bits/BlurText-TS-TW`)
- **Engine**: primary animation engine (motion / gsap / three / ogl / none)
- **Heavy**: ⚠ if uses `three` / `ogl` / `@react-three/fiber` (require user confirmation per LOCKED #5)
- **Tone / Visual / Analogy**: hand-curated AI-value-add fields (default `TODO`)
- **License**: always OSS (MIT + Commons Clause) — Pro components are filtered out by `assert_oss`

**Total**: 130 components · **Quarantined**: 0

## Text Animations (23)

| Name | Slug | Engine | Heavy | Install | Tone | Visual | Analogy |
|------|------|--------|-------|---------|------|--------|---------|
| Split Text | [split-text](https://reactbits.dev/text-animations/split-text) | gsap |  | `@react-bits/SplitText-TS-TW` | dramatic | 字符切碎从下抛上 | 苹果发布会逐字弹出 |
| Blur Text | [blur-text](https://reactbits.dev/text-animations/blur-text) | motion |  | `@react-bits/BlurText-TS-TW` | restrained | 模糊→对焦逐词浮入 | 电影开场片名定格 |
| Circular Text | [circular-text](https://reactbits.dev/text-animations/circular-text) | motion |  | `@react-bits/CircularText-TS-TW` | decorative | 文字绕圆环旋转 | 印章/徽章环形文字 |
| Text Type | [text-type](https://reactbits.dev/text-animations/text-type) | gsap |  | `@react-bits/TextType-TS-TW` | informational | 光标打字机逐字输入 | 终端命令行回显 |
| Shuffle | [shuffle](https://reactbits.dev/text-animations/shuffle) | gsap |  | `@react-bits/Shuffle-TS-TW` | playful | 字符洗牌定格成词 | 老虎机滚轮停止 |
| Shiny Text | [shiny-text](https://reactbits.dev/text-animations/shiny-text) | motion |  | `@react-bits/ShinyText-TS-TW` | subtle | 高光从左到右扫过 | PS 图层光效扫过 |
| Text Pressure | [text-pressure](https://reactbits.dev/text-animations/text-pressure) | none |  | `@react-bits/TextPressure-TS-TW` | playful | 鼠标靠近字符变粗 | 可变字体随触感变粗 |
| Curved Loop | [curved-loop](https://reactbits.dev/text-animations/curved-loop) | none |  | `@react-bits/CurvedLoop-TS-TW` | decorative | 文字沿曲线循环滑动 | 时尚网站环绕标语 |
| Fuzzy Text | [fuzzy-text](https://reactbits.dev/text-animations/fuzzy-text) | none |  | `@react-bits/FuzzyText-TS-TW` | edgy | 字符边缘抖动失焦 | 复古电视雪花信号 |
| Gradient Text | [gradient-text](https://reactbits.dev/text-animations/gradient-text) | motion |  | `@react-bits/GradientText-TS-TW` | decorative | 渐变色填充并流转 | Stripe 标题渐变 |
| Falling Text | [falling-text](https://reactbits.dev/text-animations/falling-text) | none |  | `@react-bits/FallingText-TS-TW` | playful | 字符受重力坠落堆叠 | 俄罗斯方块字母版 |
| Text Cursor | [text-cursor](https://reactbits.dev/text-animations/text-cursor) | motion |  | `@react-bits/TextCursor-TS-TW` | minimal | 文字尾随鼠标拖动 | Cursor IDE 标语跟随 |
| Decrypted Text | [decrypted-text](https://reactbits.dev/text-animations/decrypted-text) | motion |  | `@react-bits/DecryptedText-TS-TW` | techy | 乱码翻滚定格成正文 | 黑客帝国数据流 |
| True Focus | [true-focus](https://reactbits.dev/text-animations/true-focus) | motion |  | `@react-bits/TrueFocus-TS-TW` | minimal | 聚焦框扫过依次锁词 | 相机自动对焦框移动 |
| Scroll Float | [scroll-float](https://reactbits.dev/text-animations/scroll-float) | gsap |  | `@react-bits/ScrollFloat-TS-TW` | balanced | 随滚动逐字漂浮入场 | Awwwards 站滚动揭示 |
| Scroll Reveal | [scroll-reveal](https://reactbits.dev/text-animations/scroll-reveal) | gsap |  | `@react-bits/ScrollReveal-TS-TW` | balanced | 随滚动逐段揭示 | 故事卷轴展开 |
| ASCII Text | [ascii-text](https://reactbits.dev/text-animations/ascii-text) | three | ⚠ | `@react-bits/ASCIIText-TS-TW` | techy | 字符渲染为 ASCII 艺术 | BBS 时代字符画 |
| Scrambled Text | [scrambled-text](https://reactbits.dev/text-animations/scrambled-text) | gsap |  | `@react-bits/ScrambledText-TS-TW` | techy | 鼠标悬停字符乱码刷 | Mr. Robot 解密效果 |
| Rotating Text | [rotating-text](https://reactbits.dev/text-animations/rotating-text) | motion |  | `@react-bits/RotatingText-TS-TW` | minimal | 词组循环切换上滚 | Linear 首页产品名循环 |
| Glitch Text | [glitch-text](https://reactbits.dev/text-animations/glitch-text) | none |  | `@react-bits/GlitchText-TS-TW` | edgy | 文字 RGB 错位抖动 | Cyberpunk 2077 标题 |
| Scroll Velocity | [scroll-velocity](https://reactbits.dev/text-animations/scroll-velocity) | motion |  | `@react-bits/ScrollVelocity-TS-TW` | playful | 横向跑马灯随滚动加速 | 新闻台底栏字幕 |
| Variable Proximity | [variable-proximity](https://reactbits.dev/text-animations/variable-proximity) | motion |  | `@react-bits/VariableProximity-TS-TW` | polished | 字重随鼠标距离变化 | Variable Font 演示页 |
| Count Up | [count-up](https://reactbits.dev/text-animations/count-up) | motion |  | `@react-bits/CountUp-TS-TW` | informational | 数字快速滚动到目标 | 仪表盘 KPI 起跳 |

## Animations (29)

| Name | Slug | Engine | Heavy | Install | Tone | Visual | Analogy |
|------|------|--------|-------|---------|------|--------|---------|
| Animated Content | [animated-content](https://reactbits.dev/animations/animated-content) | gsap |  | `@react-bits/AnimatedContent-TS-TW` | balanced | 内容包裹器入场过渡 | 通用 reveal-on-mount |
| Fade Content | [fade-content](https://reactbits.dev/animations/fade-content) | gsap |  | `@react-bits/FadeContent-TS-TW` | minimal | 内容淡入淡出 | PowerPoint 渐隐切换 |
| Electric Border | [electric-border](https://reactbits.dev/animations/electric-border) | none |  | `@react-bits/ElectricBorder-TS-TW` | edgy | 边框电流环绕流转 | 霓虹灯管闪烁 |
| Orbit Images | [orbit-images](https://reactbits.dev/animations/orbit-images) | motion |  | `@react-bits/OrbitImages-TS-TW` | showcase | 图片绕椭圆轨道旋转 | 太阳系行星图示 |
| Pixel Transition | [pixel-transition](https://reactbits.dev/animations/pixel-transition) | gsap |  | `@react-bits/PixelTransition-TS-TW` | edgy | 像素方块切换内容 | 8-bit 游戏过场转场 |
| Glare Hover | [glare-hover](https://reactbits.dev/animations/glare-hover) | none |  | `@react-bits/GlareHover-TS-TW` | polished | 鼠标悬停高光斜扫 | 实体卡片在光下倾斜 |
| Antigravity | [antigravity](https://reactbits.dev/animations/antigravity) | three | ⚠ | `@react-bits/Antigravity-TS-TW` | ethereal | 粒子受磁场反重力浮动 | 宇宙尘埃零重力悬浮 |
| Logo Loop | [logo-loop](https://reactbits.dev/animations/logo-loop) | none |  | `@react-bits/LogoLoop-TS-TW` | informational | logo 横向无限滚动 | 客户 logo 走马灯 |
| Target Cursor | [target-cursor](https://reactbits.dev/animations/target-cursor) | gsap |  | `@react-bits/TargetCursor-TS-TW` | edgy | 鼠标变靶心十字准星 | FPS 游戏瞄准镜 |
| Magic Rings | [magic-rings](https://reactbits.dev/animations/magic-rings) | three | ⚠ | `@react-bits/MagicRings-TS-TW` | ethereal | 同心圆环外扩散开 | 声呐脉冲扩散 |
| Laser Flow | [laser-flow](https://reactbits.dev/animations/laser-flow) | three | ⚠ | `@react-bits/LaserFlow-TS-TW` | intense | 激光束流动伴随衰减 | TRON 光带飞驰 |
| Magnet Lines | [magnet-lines](https://reactbits.dev/animations/magnet-lines) | none |  | `@react-bits/MagnetLines-TS-TW` | techy | 磁力线条围绕鼠标弯曲 | 磁铁吸附铁屑分布 |
| Ghost Cursor | [ghost-cursor](https://reactbits.dev/animations/ghost-cursor) | three | ⚠ | `@react-bits/GhostCursor-TS-TW` | playful | 鬼影鼠标延迟跟随 | 童年扯不下的影子 |
| Gradual Blur | [gradual-blur](https://reactbits.dev/animations/gradual-blur) | none |  | `@react-bits/GradualBlur-TS-TW` | polished | 顶/底渐进模糊蒙版 | iOS 状态栏模糊 |
| Click Spark | [click-spark](https://reactbits.dev/animations/click-spark) | none |  | `@react-bits/ClickSpark-TS-TW` | playful | 点击迸发星形火花 | Mac 点击波纹效果 |
| Magnet | [magnet](https://reactbits.dev/animations/magnet) | none |  | `@react-bits/Magnet-TS-TW` | playful | 元素被鼠标磁吸偏移 | Awwwards 按钮吸附 |
| Sticker Peel | [sticker-peel](https://reactbits.dev/animations/sticker-peel) | gsap |  | `@react-bits/StickerPeel-TS-TW` | playful | 贴纸随鼠标卷边掀起 | 撕开真实贴纸的物理 |
| Pixel Trail | [pixel-trail](https://reactbits.dev/animations/pixel-trail) | three | ⚠ | `@react-bits/PixelTrail-TS-TW` | edgy | 像素拖尾跟随鼠标 | 复古游戏鼠标尾迹 |
| Cubes | [cubes](https://reactbits.dev/animations/cubes) | gsap |  | `@react-bits/Cubes-TS-TW` | techy | 立方体阵列旋转翻面 | Rubik's 魔方阵列 |
| Metallic Paint | [metallic-paint](https://reactbits.dev/animations/metallic-paint) | none |  | `@react-bits/MetallicPaint-TS-TW` | luxe | 金属漆面光泽流转 | 汽车广告金属反光 |
| Noise | [noise](https://reactbits.dev/animations/noise) | none |  | `@react-bits/Noise-TS-TW` | subtle | 颗粒噪点底纹动态 | 胶片颗粒质感 |
| Shape Blur | [shape-blur](https://reactbits.dev/animations/shape-blur) | three | ⚠ | `@react-bits/ShapeBlur-TS-TW` | ethereal | 模糊形状缓慢漂浮 | Apple 发布会背景胶质 |
| Crosshair | [crosshair](https://reactbits.dev/animations/crosshair) | gsap |  | `@react-bits/Crosshair-TS-TW` | edgy | 准星十字跟随鼠标 | 射击游戏 HUD |
| Image Trail | [image-trail](https://reactbits.dev/animations/image-trail) | gsap |  | `@react-bits/ImageTrail-TS-TW` | showcase | 图片随鼠标拖出残影 | 时尚摄影动态展示 |
| Ribbons | [ribbons](https://reactbits.dev/animations/ribbons) | ogl | ⚠ | `@react-bits/Ribbons-TS-TW` | decorative | 彩色丝带飘舞跟随 | 庆典彩带飞舞 |
| Splash Cursor | [splash-cursor](https://reactbits.dev/animations/splash-cursor) | none |  | `@react-bits/SplashCursor-TS-TW` | playful | 鼠标拖出流体涟漪 | 水面滴入墨滴 |
| Meta Balls | [meta-balls](https://reactbits.dev/animations/meta-balls) | ogl | ⚠ | `@react-bits/MetaBalls-TS-TW` | playful | 球体粘合融化合并 | 熔岩灯液体球 |
| Blob Cursor | [blob-cursor](https://reactbits.dev/animations/blob-cursor) | gsap |  | `@react-bits/BlobCursor-TS-TW` | playful | 鼠标变软糖弹性形变 | Linear 网站果冻光标 |
| Star Border | [star-border](https://reactbits.dev/animations/star-border) | none |  | `@react-bits/StarBorder-TS-TW` | decorative | 边框星辰流光循环 | 魔法卡牌发光边框 |

## Components (36)

| Name | Slug | Engine | Heavy | Install | Tone | Visual | Analogy |
|------|------|--------|-------|---------|------|--------|---------|
| Animated List | [animated-list](https://reactbits.dev/components/animated-list) | motion |  | `@react-bits/AnimatedList-TS-TW` | polished | 列表项依次入场 | Notion 数据库行加载 |
| Scroll Stack | [scroll-stack](https://reactbits.dev/components/scroll-stack) | none |  | `@react-bits/ScrollStack-TS-TW` | showcase | 滚动时卡片叠堆缩放 | Apple 网站滚动段落叠 |
| Bubble Menu | [bubble-menu](https://reactbits.dev/components/bubble-menu) | gsap |  | `@react-bits/BubbleMenu-TS-TW` | playful | 气泡环绕主按钮弹出 | iOS 长按弹出菜单 |
| Magic Bento | [magic-bento](https://reactbits.dev/components/magic-bento) | gsap |  | `@react-bits/MagicBento-TS-TW` | polished | 卡片网格悬浮联动光效 | Apple 官网 Bento 区 |
| Circular Gallery | [circular-gallery](https://reactbits.dev/components/circular-gallery) | ogl | ⚠ | `@react-bits/CircularGallery-TS-TW` | showcase | 图片绕圆环旋转滚动 | 唱片机转盘 |
| Reflective Card | [reflective-card](https://reactbits.dev/components/reflective-card) | none |  | `@react-bits/ReflectiveCard-TS-TW` | luxe | 卡片倾斜反光材质 | 全息收藏卡反射 |
| Card Nav | [card-nav](https://reactbits.dev/components/card-nav) | gsap |  | `@react-bits/CardNav-TS-TW` | polished | 卡片式横向导航 | Stripe 文档侧栏卡片 |
| Stack | [stack](https://reactbits.dev/components/stack) | motion |  | `@react-bits/Stack-TS-TW` | showcase | 卡片堆叠拖动切换 | Tinder 滑卡操作 |
| Fluid Glass | [fluid-glass](https://reactbits.dev/components/fluid-glass) | three | ⚠ | `@react-bits/FluidGlass-TS-TW` | luxe | 玻璃面板流体折射 | iOS 26 Liquid Glass |
| Pill Nav | [pill-nav](https://reactbits.dev/components/pill-nav) | gsap |  | `@react-bits/PillNav-TS-TW` | minimal | 胶囊形 tab 滑动指示 | iOS Segmented Control |
| Tilted Card | [tilted-card](https://reactbits.dev/components/tilted-card) | motion |  | `@react-bits/TiltedCard-TS-TW` | polished | 鼠标悬停 3D 倾斜 | 实体卡片在掌心翻转 |
| Masonry | [masonry](https://reactbits.dev/components/masonry) | gsap |  | `@react-bits/Masonry-TS-TW` | showcase | 瀑布流不等高布局 | Pinterest 图墙 |
| Glass Surface | [glass-surface](https://reactbits.dev/components/glass-surface) | none |  | `@react-bits/GlassSurface-TS-TW` | luxe | 玻璃磨砂面板背景 | macOS 控制中心 |
| Dome Gallery | [dome-gallery](https://reactbits.dev/components/dome-gallery) | none |  | `@react-bits/DomeGallery-TS-TW` | showcase | 图片穹顶球面环绕 | Vision Pro 沉浸式空间 |
| Chroma Grid | [chroma-grid](https://reactbits.dev/components/chroma-grid) | gsap |  | `@react-bits/ChromaGrid-TS-TW` | decorative | 彩色滤镜网格悬停亮 | 色彩选择器调色板 |
| Folder | [folder](https://reactbits.dev/components/folder) | none |  | `@react-bits/Folder-TS-TW` | playful | 文件夹打开露内容 | macOS Finder 文件夹 |
| Staggered Menu | [staggered-menu](https://reactbits.dev/components/staggered-menu) | gsap |  | `@react-bits/StaggeredMenu-TS-TW` | polished | 菜单项错落依次展开 | Awwwards 全屏菜单 |
| Model Viewer | [model-viewer](https://reactbits.dev/components/model-viewer) | three | ⚠ | `@react-bits/ModelViewer-TS-TW` | showcase | 3D 模型可拖动旋转 | Apple 网站 3D 产品图 |
| Lanyard | [lanyard](https://reactbits.dev/components/lanyard) | three | ⚠ | `@react-bits/Lanyard-TS-TW` | playful | 挂绳卡片物理摆动 | 门禁工牌真实甩动 |
| Profile Card | [profile-card](https://reactbits.dev/components/profile-card) | none |  | `@react-bits/ProfileCard-TS-TW` | polished | 个人资料卡悬停动态 | X/Twitter 用户卡 |
| Dock | [dock](https://reactbits.dev/components/dock) | motion |  | `@react-bits/Dock-TS-TW` | iconic | 图标随悬停放大 | macOS Dock 栏 |
| Gooey Nav | [gooey-nav](https://reactbits.dev/components/gooey-nav) | none |  | `@react-bits/GooeyNav-TS-TW` | playful | 选中态液态粘连过渡 | Material Design 流体 |
| Pixel Card | [pixel-card](https://reactbits.dev/components/pixel-card) | none |  | `@react-bits/PixelCard-TS-TW` | edgy | 像素风卡片悬停闪 | FC 红白机界面 |
| Carousel | [carousel](https://reactbits.dev/components/carousel) | motion |  | `@react-bits/Carousel-TS-TW` | informational | 轮播切换内嵌指示器 | 电商首页 Banner 轮播 |
| Spotlight Card | [spotlight-card](https://reactbits.dev/components/spotlight-card) | none |  | `@react-bits/SpotlightCard-TS-TW` | polished | 鼠标位置射出光斑 | 聚光灯下的展品 |
| Border Glow | [border-glow](https://reactbits.dev/components/border-glow) | none |  | `@react-bits/BorderGlow-TS-TW` | edgy | 边框发光循环流动 | Vercel 卡片悬停光边 |
| Flying Posters | [flying-posters](https://reactbits.dev/components/flying-posters) | ogl | ⚠ | `@react-bits/FlyingPosters-TS-TW` | showcase | 海报横向飞过堆叠 | 电影院预告海报飘过 |
| Card Swap | [card-swap](https://reactbits.dev/components/card-swap) | gsap |  | `@react-bits/CardSwap-TS-TW` | playful | 卡片堆叠循环切换 | 扑克切牌动画 |
| Glass Icons | [glass-icons](https://reactbits.dev/components/glass-icons) | none |  | `@react-bits/GlassIcons-TS-TW` | luxe | 图标玻璃质感悬浮 | iOS 透明图标 |
| Decay Card | [decay-card](https://reactbits.dev/components/decay-card) | gsap |  | `@react-bits/DecayCard-TS-TW` | edgy | 卡片悬停产生噪点衰变 | 胶片老化撕裂质感 |
| Flowing Menu | [flowing-menu](https://reactbits.dev/components/flowing-menu) | gsap |  | `@react-bits/FlowingMenu-TS-TW` | decorative | 菜单项悬停流体涌入 | 墨水滴入水池扩散 |
| Elastic Slider | [elastic-slider](https://reactbits.dev/components/elastic-slider) | motion |  | `@react-bits/ElasticSlider-TS-TW` | playful | 滑块拖动有橡皮筋形变 | iOS 音量滑块橡皮 |
| Counter | [counter](https://reactbits.dev/components/counter) | motion |  | `@react-bits/Counter-TS-TW` | informational | 数字滚轮上下切换 | 机场翻牌时钟 |
| Infinite Menu | [infinite-menu](https://reactbits.dev/components/infinite-menu) | none |  | `@react-bits/InfiniteMenu-TS-TW` | showcase | 球面菜单无限旋转 | Apollo 图标球 |
| Stepper | [stepper](https://reactbits.dev/components/stepper) | motion |  | `@react-bits/Stepper-TS-TW` | informational | 分步进度带动画过渡 | 结账流程指示器 |
| Bounce Cards | [bounce-cards](https://reactbits.dev/components/bounce-cards) | gsap |  | `@react-bits/BounceCards-TS-TW` | playful | 卡片落地弹跳归位 | 塔罗牌摔在桌上 |

## Backgrounds (42)

| Name | Slug | Engine | Heavy | Install | Tone | Visual | Analogy |
|------|------|--------|-------|---------|------|--------|---------|
| Liquid Ether | [liquid-ether](https://reactbits.dev/backgrounds/liquid-ether) | three | ⚠ | `@react-bits/LiquidEther-TS-TW` | dreamy | 液态颜料缓慢交融 | 墨滴落入水中 |
| Prism | [prism](https://reactbits.dev/backgrounds/prism) | ogl | ⚠ | `@react-bits/Prism-TS-TW` | techy | 棱镜光散射成色谱 | Pink Floyd 唱片封面 |
| Dark Veil | [dark-veil](https://reactbits.dev/backgrounds/dark-veil) | ogl | ⚠ | `@react-bits/DarkVeil-TS-TW` | ethereal | 暗色幕布波动 | 夜空织物缓慢起伏 |
| Light Pillar | [light-pillar](https://reactbits.dev/backgrounds/light-pillar) | three | ⚠ | `@react-bits/LightPillar-TS-TW` | intense | 光柱垂直发散 | 演唱会顶光柱 |
| Silk | [silk](https://reactbits.dev/backgrounds/silk) | three | ⚠ | `@react-bits/Silk-TS-TW` | luxe | 丝绸光影波浪流动 | 高档化妆品广告背景 |
| Floating Lines | [floating-lines](https://reactbits.dev/backgrounds/floating-lines) | three | ⚠ | `@react-bits/FloatingLines-TS-TW` | minimal | 线条无序漂浮 | 线稿建筑透视图 |
| Light Rays | [light-rays](https://reactbits.dev/backgrounds/light-rays) | ogl | ⚠ | `@react-bits/LightRays-TS-TW` | ethereal | 光线放射状散开 | 晨间云隙耶稣光 |
| Pixel Blast | [pixel-blast](https://reactbits.dev/backgrounds/pixel-blast) | three | ⚠ | `@react-bits/PixelBlast-TS-TW` | edgy | 像素方块爆炸扩散 | 复古游戏过关效果 |
| Color Bends | [color-bends](https://reactbits.dev/backgrounds/color-bends) | three | ⚠ | `@react-bits/ColorBends-TS-TW` | dreamy | 色彩弯折交错流动 | 极光在天空翻折 |
| Evil Eye | [evil-eye](https://reactbits.dev/backgrounds/evil-eye) | ogl | ⚠ | `@react-bits/EvilEye-TS-TW` | dreamy | 瞳孔状色环旋转 | 土耳其蓝眼护身符 |
| Line Waves | [line-waves](https://reactbits.dev/backgrounds/line-waves) | ogl | ⚠ | `@react-bits/LineWaves-TS-TW` | minimal | 横向波浪线流动 | 示波器音波图 |
| Radar | [radar](https://reactbits.dev/backgrounds/radar) | ogl | ⚠ | `@react-bits/Radar-TS-TW` | techy | 圆形扫描线辐射旋转 | 雷达屏扫描 |
| Soft Aurora | [soft-aurora](https://reactbits.dev/backgrounds/soft-aurora) | ogl | ⚠ | `@react-bits/SoftAurora-TS-TW` | ethereal | 柔和极光漫射 | Nordic 夜空轻极光 |
| Aurora | [aurora](https://reactbits.dev/backgrounds/aurora) | ogl | ⚠ | `@react-bits/Aurora-TS-TW` | ethereal | 极光色带在背景起伏 | Vercel 首页背景极光 |
| Plasma | [plasma](https://reactbits.dev/backgrounds/plasma) | ogl | ⚠ | `@react-bits/Plasma-TS-TW` | intense | 等离子流体翻滚色块 | WinAmp 经典 visualizer |
| Plasma Wave | [plasma-wave](https://reactbits.dev/backgrounds/plasma-wave) | ogl | ⚠ | `@react-bits/PlasmaWave-TS-TW` | intense | 等离子波纹横向推进 | WinAmp 频谱波形 |
| Particles | [particles](https://reactbits.dev/backgrounds/particles) | ogl | ⚠ | `@react-bits/Particles-TS-TW` | techy | 粒子点阵漂浮连线 | tsParticles 经典背景 |
| Gradient Blinds | [gradient-blinds](https://reactbits.dev/backgrounds/gradient-blinds) | ogl | ⚠ | `@react-bits/GradientBlinds-TS-TW` | decorative | 渐变百叶窗交替变色 | 霓虹灯条交替亮 |
| Grainient | [grainient](https://reactbits.dev/backgrounds/grainient) | ogl | ⚠ | `@react-bits/Grainient-TS-TW` | luxe | 颗粒质感渐变色块 | Stripe 招聘页颗粒渐变 |
| Grid Scan | [grid-scan](https://reactbits.dev/backgrounds/grid-scan) | three | ⚠ | `@react-bits/GridScan-TS-TW` | techy | 网格扫描线纵向移动 | Tron 数字扫描 |
| Beams | [beams](https://reactbits.dev/backgrounds/beams) | three | ⚠ | `@react-bits/Beams-TS-TW` | intense | 光束放射状切割画面 | 夜店激光束 |
| Pixel Snow | [pixel-snow](https://reactbits.dev/backgrounds/pixel-snow) | three | ⚠ | `@react-bits/PixelSnow-TS-TW` | playful | 像素雪花飘落 | 复古圣诞游戏雪景 |
| Lightning | [lightning](https://reactbits.dev/backgrounds/lightning) | none |  | `@react-bits/Lightning-TS-TW` | intense | 闪电随机劈下 | 暴风雨中闪电 |
| Prismatic Burst | [prismatic-burst](https://reactbits.dev/backgrounds/prismatic-burst) | ogl | ⚠ | `@react-bits/PrismaticBurst-TS-TW` | intense | 棱镜状光线爆发 | 超新星光芒迸发 |
| Galaxy | [galaxy](https://reactbits.dev/backgrounds/galaxy) | ogl | ⚠ | `@react-bits/Galaxy-TS-TW` | dreamy | 星系旋臂粒子缓转 | 哈勃望远镜深空照 |
| Dither | [dither](https://reactbits.dev/backgrounds/dither) | three | ⚠ | `@react-bits/Dither-TS-TW` | edgy | 颗粒抖动黑白噪点 | Game Boy 屏幕灰阶 |
| Faulty Terminal | [faulty-terminal](https://reactbits.dev/backgrounds/faulty-terminal) | ogl | ⚠ | `@react-bits/FaultyTerminal-TS-TW` | edgy | 故障终端字符闪烁 | 异形电影旧 CRT 显示 |
| Ripple Grid | [ripple-grid](https://reactbits.dev/backgrounds/ripple-grid) | ogl | ⚠ | `@react-bits/RippleGrid-TS-TW` | techy | 网格随波纹起伏 | 水面石子涟漪格点 |
| Dot Field | [dot-field](https://reactbits.dev/backgrounds/dot-field) | none |  | `@react-bits/DotField-TS-TW` | minimal | 点阵场随交互密度变 | 夜空繁星密度图 |
| Dot Grid | [dot-grid](https://reactbits.dev/backgrounds/dot-grid) | gsap |  | `@react-bits/DotGrid-TS-TW` | minimal | 点阵网格随光标涟漪 | 扫描仪光斑 |
| Threads | [threads](https://reactbits.dev/backgrounds/threads) | ogl | ⚠ | `@react-bits/Threads-TS-TW` | minimal | 细线交织成网图案 | 蜘蛛网光影投射 |
| Hyperspeed | [hyperspeed](https://reactbits.dev/backgrounds/hyperspeed) | three | ⚠ | `@react-bits/Hyperspeed-TS-TW` | intense | 灯光高速隧道穿梭 | 千年隼跃迁 |
| Iridescence | [iridescence](https://reactbits.dev/backgrounds/iridescence) | ogl | ⚠ | `@react-bits/Iridescence-TS-TW` | luxe | 全息珠光渐变流动 | 全息卡片倾斜反光 |
| Waves | [waves](https://reactbits.dev/backgrounds/waves) | none |  | `@react-bits/Waves-TS-TW` | minimal | 正弦波浪线条流动 | 水面波纹示意图 |
| Grid Distortion | [grid-distortion](https://reactbits.dev/backgrounds/grid-distortion) | three | ⚠ | `@react-bits/GridDistortion-TS-TW` | techy | 网格随鼠标扭曲变形 | WebGL shader demo |
| Ballpit | [ballpit](https://reactbits.dev/backgrounds/ballpit) | gsap | ⚠ | `@react-bits/Ballpit-TS-TW` | playful | 球池物理碰撞翻滚 | 麦当劳儿童球池 |
| Orb | [orb](https://reactbits.dev/backgrounds/orb) | ogl | ⚠ | `@react-bits/Orb-TS-TW` | ethereal | 中心光球缓慢呼吸 | Apple Siri 光球 |
| Letter Glitch | [letter-glitch](https://reactbits.dev/backgrounds/letter-glitch) | none |  | `@react-bits/LetterGlitch-TS-TW` | techy | 字符背景持续翻滚 | 终端启动加载界面 |
| Grid Motion | [grid-motion](https://reactbits.dev/backgrounds/grid-motion) | gsap |  | `@react-bits/GridMotion-TS-TW` | techy | 网格图片随鼠标平移 | Awwwards 项目图墙 |
| Shape Grid | [shape-grid](https://reactbits.dev/backgrounds/shape-grid) | none |  | `@react-bits/ShapeGrid-TS-TW` | minimal | 形状网格规律变换 | 瑞士设计风格底纹 |
| Liquid Chrome | [liquid-chrome](https://reactbits.dev/backgrounds/liquid-chrome) | ogl | ⚠ | `@react-bits/LiquidChrome-TS-TW` | luxe | 液态铬金属流动反光 | Y2K 液态金属审美 |
| Balatro | [balatro](https://reactbits.dev/backgrounds/balatro) | ogl | ⚠ | `@react-bits/Balatro-TS-TW` | playful | 迷幻色块旋转推拉 | 肥皂泡彩虹反射 |

## Crawler refresh

```bash
# from skill root
python3 scripts/crawl_catalog.py            # full refresh
python3 scripts/crawl_catalog.py --category text-animations
python3 scripts/crawl_catalog.py --dry-run  # preview without writing
```

Hand-curated tone/visual/analogy fields live in `references/visual-index-handcurated.json` and survive across crawls.
