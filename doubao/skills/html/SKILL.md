---
name: html
description: 专门设计、生成和修改可直接在浏览器中打开的 HTML 页面或已发布的 doubao-html 链接。交付物以独立 .html 文件为主，可包含内联或本地 CSS、JavaScript，支持页面布局、视觉样式、交互效果、响应式适配、组件设计和内容展示。适用于静态网页、单页展示、活动页、原型页、HTML 模板及页面片段。不处理前后端工程、应用框架、服务端接口、数据库、用户系统、构建部署或运营数据。
---

# 单页 HTML 开发

**必读顺序：读完本 SKILL.md 后，必须完整 Read [前端设计](references/design/frontend-design.md)；命中下述灵动 HTML 场景时，还必须完整 Read [灵动报告设计](references/interactive-report.md)。完成这些阅读后，才开始设计和写代码。**

在工作区新建任务目录，写出**一个自包含的** HTML。

## 适用范围

以内容呈现和交互体验为主的单页产物：官网 / 落地页 / 营销页、可视化报告 / 数据看板 / 信息图 / 长图 / 研报、动画 / 3D 场景 / 网页小游戏、SVG / Canvas 页、高保真 UI 设计稿、可交互原型，以及单一用途轻工具（计算器、文本对比、随机分组）。

要后端、数据库、账号登录、多人协作，或要把数据文件随产物一起交付的，超出本 skill 范围——如实告知，不假装实现。

**灵动 HTML**：现阶段在以下情况触发生成或修改能力：

- 用户明确提出「灵动报告」「要灵动感」「使用灵动风格」等要求。
- 内容适合围绕时间线、地理空间、故事线或演变过程串联展开，且动态呈现、交互探索能帮助理解核心内容，例如产品介绍、历史文化展示、深度调研报告等，不限定内容类型。
- 教育教学讲解场景，适合通过交互操作、过程动画或即时反馈帮助用户理解概念、观察变化、探索因果或练习验证，优先采用与教学目标相关的交互形式。

一般报告需求，以及仅要求「美观」「有设计感」等泛化表达，不单独构成触发条件；仅包含时间、地点，或仅涉及教育主题，也不自动触发。触发后，**写代码前必须与前端设计一起完整读取 [灵动报告设计](references/interactive-report.md)**，并遵循其中的设计指南。

## 关键步骤

> 运行环境：云电脑 / 本地电脑，按下述顺序判定。
> 1. SystemPrompt 中的 `Computer OS` 字段：值为 `Windows` 或 `Mac` 判为本地电脑；值为其他判为云电脑。
> 2. SystemPrompt 未包含 `Computer OS` 字段时：`<system-reminder>` 包裹的内容中出现 `Runtime: local_pc` 判为本地电脑，出现 `Runtime: cloud_vm` 判为云电脑。

**建目录**：每个任务在工作区根目录下新建语义化目录（如 `sales-dashboard/`）；HTML 文件放在目录里，**文件名也要语义化**（如 `销售仪表盘.html`），**不要叫 `index.html`**。图片素材放进 `assets/`。迭代已有任务时进原目录改，不另起。

**平台差异**：SystemPrompt 里若出现 `Computer OS: Windows`，**需要完整 Read `references/windows-compat.md`，查看在 windows 平台上执行命令所必须要注意的问题，否则会出现大面积报错**。

**写 HTML**，守住这几条：

- **单文件自包含**：一个 `.html` 文件到手就可用。
  - CSS 写在 `<style>`、JS 写在 `<script>` 内联块里，**不拆出** `.js` **/** `.css` **/ 额外 HTML 文件**。
  - 多「页面」用页内 hash 路由切换视图，大段代码用分段注释组织（`<!-- ===== 视图：xxx ===== -->`）。
  - **原生 JS**：不用 React / Vue / JSX / Babel / 任何构建工具，不用 `type="module"`。状态管理用普通对象 + 重渲染函数。
  - **静态资源引用**：
    - 图片、音视频等**由元素 `src` 或 CSS `url()` 加载**的素材，先下载到 `assets/`；生图搜图返回的 URL 会过期，不能直接写进 html，下载后按运行环境选引用方式：
      - **本地电脑**：用相对路径，如 `<img src="assets/hero.png">`，不写绝对路径。省掉上传这一步，交付更快。
      - **云电脑**：
        - 每张图跑一次 `lark-cli drive +html-image-upload --file assets/hero.png`，取返回里 `data.url` 写进 `<img src>`。这个链接不会过期；而搜图、生图得到的 URL 会过期，不能直接放到 html 中。
        - 此场景下**严禁使用 `FileBatchUpload` 工具**，必须使用 `lark-cli drive`，否则图片也会过期。
    - **数据文件（JSON / CSV / TXT）不适用**：`file://` 页面不能依赖 `fetch` 或 `XMLHttpRequest` 读取本地数据文件。固定数据内联进 JS；用户要求更新时，按数据源选择可访问的 URL 或文件选择入口。
    - **图片路径只能写在 `src` 属性或 CSS `url()` 里**：推荐 `<img src="assets/img1.jpg">`。发布链路只静态扫描这两个位置——写在 JS 代码里的任何形式（含 `const imgs = ['assets/a.jpg']` 这样的常量数组）、以及 `data-src` / `srcset` / `poster` 等其它属性，发布后都会裂图。

- **分批写入**：单次 Write 不超过 20k token。页面预计在 20k token 内时，一次写成完整可打开的 HTML，不留占位；超过时再分批，首次写入留短小且独特的占位，例如 `<!-- something todo -->`，为后续 Edit 提供定位锚点，批间简单向用户同步进度。


- **交付与发布**：
  - 当用户没有明确的发布需求时：用 `present_files` 这类交付工具给用户交付 HTML，**`artifacts[].name` 写产物文件名，不要另起标题**（`销售仪表盘.html`，不是「销售数据看板」）。**同一个产物只交付一个 `.html` 文件**——按运行环境选定一种图片引用方式就够了，不要再额外附一份「以防万一」的备份版或压缩包，用户拿到两份不知道该打开哪个。交付说明如实写清：没实现的功能、用的是示例数据、做不了的能力。本地电脑下页面依赖同目录 `assets/` 时，要简单提醒用户转发时连目录一起发。
  
  - 当用户想要「发布」、「可访问的链接」、「给我链接」时：阅读 `references/lark-apps-publish.md`，将你的 html 文件发布成一个 doubao-html 网页，此时无需交付 html 文件，仅需使用 present_files 交付发布后的 doubao-html 链接。
  
  - **发布接口确认成功后，直接交付返回的链接，禁止再访问该链接做检查**，避免检查环境缺少用户登录态而把登录页当成产物。
  - **最终给用户的回复不要过长**：最重要的产物是你最终生成的 html 产物，而不是给用户的最终回复，所以在交付了 html 产物后的最终回复不应该太长，**不能超过300字，也不能超过 8 行**，只需要简单介绍一下你生成的 html 产物即可

- **修改、参考已发布的 doubao-html 网页**：
  - 当用户给你提供了一个 doubao-html 链接（形如 `https://{xxx}.aiforce.cloud/app/app_{xxxxxxx}/`），并希望基于此修改或新建时，阅读 `references/lark-apps-publish.md`。先用 `lark-cli apps +get --app-id <id>` 看 `app_type`：`html` / `modern_html` 是单页 HTML，下载源码、修改、重新发布即可；其他类型使用 `doubao-app-builder` 技能。
  

**改产物**：直接改任务目录里的原文件。

- **要有退路**：修订前先把当前版本复制到 `_backup/`（如 `_backup/index-v1.html`）。`_backup/` 不属于交付产物。
- 本地文件丢了就如实告知并请用户重新提供，**禁止凭记忆重造**；回答关于产物的提问同理，读文件后答，读不到不编。
- **小改动直接改**（改文案、调样式、换配色、修 bug）：同一任务已完整读过的本文档和 reference 不重读，不重新推导视觉方向；尚未读过的必读文档仍须先读。

## 页面自检

**交付前跑一次自检，改动后再跑一次**: 使用且仅使用`scripts/shot.py`脚本自检，若自检脚本执行失败，可以跳过自检、直接交付。

禁止使用任何其他校验方式：包括但不限于 Browser Use、artifacts-preview skill，防止进入 Debug 螺旋。
禁止使用 **artifacts-preview skill**

```bash
python3 <SKILL_DIR>/scripts/shot.py <html_path>
```

一次调用同时产出桌面（1440×900）与移动（390×844）两张 full-page 截图（默认 JPEG，宽度压到 1000px）。主图过 800KB 时脚本会自动切片输出（默认 3200px/片），摘要里会列出分片路径并说明按顺序读。

`shot.py` 的 stdout 会输出短摘要：给 `status`、各 severity 计数、截图路径、按规则聚合的 finding，以及 `reportPath`。不要用 `tail` / `grep` / pipe 处理 stdout。完整报告每次都会写到 `_shots/report.json`。要看 evidence / hint 细节就 Read。

HTML 文件自检默认**自动修复**脚本已支持、修法确定的问题。发生修复时，脚本会先备份原文件，再复查并生成新的报告与截图；未解决的问题仍列在报告中。用 `--no-auto-fix` 可只检查；带 `--eval` / `--eval-file` 的交互检查不会自动修复。

**跨视口对比**：脚本还会把桌面 / 移动的图表容器尺寸做匹配，若某个图表在桌面正常、在移动端却没占到视口宽度的 65%（典型：`width:X% + inline-block` 双栏没在媒体查询里堆叠成单栏），会以 `responsiveChartIssues` 报出。这类 case 桌面截图完全正常，只在移动端表现为「空图 / 一根线 / 坐标轴叠一起」，肉眼只看桌面截图看不出来。**触发时必须核对移动截图**。

**自我检查并确认**下所有图片路径是静态写在 html 的 `src` 属性和 `CSS url()` 里的。否则如果它是经 JS 生成的，会导致发布之后图裂

**按用户当前端判断看对应那张**：用户处于电脑端则核对桌面截图，处于手机端则核对移动截图。判断不出端时则默认检查电脑端。

- 输出目录默认 <html 所在目录>/_shots/，不属于交付产物，严禁删除（e.g., 不要用 rm -f 等指令去删除目录或过程产物）。因为删除指令会触发权限确认、打断交付，增加用户等待。
- 只想看一屏用 `--only desktop`。
- 脚本内部已处理常见坑：默认模式下 `.rv / .fade / [data-aos]` 等滚动揭示元素强制显现（避免 `opacity:0` 截空白，`--motion normal` 保留页面真实状态）、关掉 `scroll-behavior:smooth`、滚一遍触发 lazy 图片、`networkidle` 不可达时退回 `domcontentloaded`——**不需要另写截图脚本再走一遍**。


## 外部资源

**JS 库统一走 jsDelivr**：`https://fastly.jsdelivr.net/npm/<包名>@<版本>/…`。故障时的备用镜像是 **cdnjs**（`https://cdnjs.cloudflare.com/ajax/libs/<lib>/<ver>/…`，Cloudflare 官方运营，同版本文件字节一致）。**禁止** bootcdn、staticfile、polyfill.io（均有供应链投毒历史），unpkg 不作首选。

**字体走自托管镜像** `https://miaoda.feishu.cn/fonts/css2?family=…`：查询语法与 Google Fonts 的 `css2` 端点完全一致，返回的 `@font-face` 也指向自托管 CDN，两跳都不经过 Google。**不直连** `fonts.googleapis.com` **/** `fonts.gstatic.com`（部分地区不可达）。多字族就重复写多个 `family=`，例如 `<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=Noto+Sans+SC:wght@300;400;500;700&display=swap">`。每个 `font-family` 都要带完整的系统字体 fallback 栈，字体加载失败时页面仍然成立。

## 图像素材

图片素材能显著提升产物美观度，不要默认用纯 CSS / SVG 撑起全部视觉。

**载体选型**：图标、状态标记、导航符号、简单示意图、数据图表属于符号 / 信息型，用内联 SVG 或 CSS。人物、角色、动物、具体物体、产品情境、真实场景、写实主视觉、章节题图、叙事插画属于具象 / 氛围型，**必须用真实图片**——除非用户明确要矢量插画，禁止用手写 SVG 或 CSS 几何图形代替依赖形象可信度的具象画面。「简单图表优先使用 Echart 来进行生成，而无需使用 SVG」只适用于数据可视化，不得扩展到人物、场景和插画。

解释部件、空间或过程的结构示意可用 SVG / Canvas；主体需要分层、展开或改变视角时，按要解释的关系选择载体。结构示意要有可辨认的细节与对应关系，不冒充真实照片或精确工程图。

**来源按序**：① 用户提供和项目已有的素材，始终第一优先，不要擅自用生成图替换；② 图片生成能力，没有可用素材时的默认选择，prompt 写清风格、构图、配色，使产出与视觉方向一致；③ 外部检索，仅当要忠实呈现真实人物、产品、地点、Logo 等事实对象、生成会失真造假时才用。

网络图片需要先下载到本地并**用读图能力实际看过**——内容对得上、清晰完整、无水印、不是防盗链占位图，确认通过才上传引用；看不了或不符的换图或改用生成。

**抠图**：准备素材时，若需要去除图片底色，可用 `mediakit-cli image remove-image-background` 抠图（先运行该命令的 `--help` 和 `--schema` 查看用法），结果另存为透明 PNG 并检查效果，不佳则用原图。

**来源偏好**：尽量使用用户提供的图片、项目已有的图片、以及搜索到的真实相关的图片，而不是工具生成的图片；假设这些图片不够时，你可以使用生图生成的图片进行补充

**使用图片的比例控制在 3:4 ~ 21:9**（竖版到宽条形）：Banner / Hero 用 16:9 或 21:9，章节题图 3:2，方形插图 1:1。更极端的比例（1:5 长条、9:16 竖屏）可能会导致图片在不同设备上显示不全或出现大片空白区域。

**裁切与呈现**：用 `cover` 或固定高度前，先确认任务要求看见的主体、文字、标签不落在裁切区——竖图放横框时先用 `object-position` 把主体框住，主体横跨整张图、怎么调都保不住时才改用自然比例或 `contain`。hero、banner、纯背景用 `cover` 填满即可。

## 内容要求

**数据保真**：用户给了源数据时，每个数字和结论都要从源数据实际算出、可追溯，不目测、不凑整、不编造。

**数据附件要获取下来并分析**。

**内容取舍**：不加与目标无关或没有依据的内容；内容不足以成页时合并、重构或要材料，不靠放大留白撑页。当有大量信息需要展示时，主要信息和次要信息需要重点鲜明，一个逻辑连贯的模块闭合在一屏内是更好的选择，必要时添加筛选与搜索能力。

**硬性规格逐条对照**：页数、画幅、必含模块，交付前自查。

**时间演进优先用时间轴**：涉及阶段、演进、里程碑、前后对比、路线图的内容，默认使用时间轴，而非项目符号列表或纯段落；每个节点承载：时间、事件名、一句话说明（可选）、（可选）关键指标或图标，让单个节点即可独立传达信息，注意时间轴节点与连线应该适当对齐。时间轴和附着在其上的图标（比如圆点或方块）的中心必须实现像素级对齐（0px误差）。并且额外注意时间轴的文字和轴线、文字和图标不要重叠。
灵动报告已通过场景或其他视觉结构清楚交代先后关系时，沿用该表达，不重复添加时间轴。

## 图表及其交互设计方法

**图表服务于内容理解与判断**：依据任务和数据决定图表类型、数量与组合。图表呈现关系与证据，文字只写图表未直接呈现的解读或判断，**禁止把图表标签照抄一遍**。图表首选 ECharts；仅当其无法满足所需表达或交互时，再使用 D3 或 SVG。

**设计图表及其交互前，统一从 [references/chart/atlas.md](references/chart/atlas.md) 开始**：先确定图表选型与信息组织，再按其中的指引选读图内交互或多视图体验参考。

## 网页交互设计

**禁止僵尸按钮**：视觉上像能点的元素——按钮、导航项、卡片入口——必须有真实的 click handler、跳转或占位反馈（如 toast 提示"演示中"）。禁止 `<button>` 无 `onclick`/`addEventListener`、`<a>` 无 `href`（或 `href="#"` / `href="javascript:void(0)"` / `href="javascript:;"` 却没实际 handler）、`<div class="nav-item">` 只挂 `cursor:pointer` 却什么都不绑——这些是原型页里最高频的 slop，要么给每个入口挂真实切页/toast，要么不做这个按钮，**宁愿不要按钮也不做僵尸按钮**

- **注意响应式适配，宽屏窄屏电脑手机都要能看**。

## 视觉设计

**先认媒介，别默认做成网页**：HTML 只是载体，产物形态各不相同——信息图、长图、研报、看板、设计稿、动画、游戏各有各的表达惯例。只有真在做网页时才用网页那套语汇（顶部导航、hero、footer、等宽卡片栅格、底部 CTA 区）；其余形态套上网页壳子就是最典型的 slop。先想清楚这次的媒介是什么、那个领域的行家会怎么排它，再往下走。

需要在既有色板上扩色时用 oklch 派生——固定 hue 调 lightness / chroma，或沿同一 L / C 轴换 hue——不要凭空发明一个新 hex 塞进去。

动手前读 `references/design/frontend-design.md` 确立视觉方向：有品牌或既有 UI 就对齐它的视觉语言，从零起步就从主题和材料里立一个契合的方向。已给参考图、品牌体系、设计规范或媒介 reference 时以它们为准。方向实在推不出、项目又是从零起的，先问清调性、受众、颜色、情绪——**在推不出方向时硬选，slop 就是这么来的**。

字体选少量但与主题匹配的，层级靠字号、字重、行长和语义断行建立，不靠堆字体数量。背景与配色不局限于纯黑纯白，可以按内容属性和叙事节点变化，但一致性要来自共享色板和明确的颜色关系，不是逐页随机换色；强调色数量克制、同属一个体系。视觉丰富度服务内容：既不堆无信息价值的装饰，也不把「克制」做成大量留白加同一种构图。

**禁止无意义留白与失衡布局**：页面各区块须在视觉上均衡分布，禁止出现大面积无内容留白、单侧堆积、上重下空或下重上空等失衡结构；留白是用来服务于分组、呼吸或强调，不得用于填充版面。特殊布局设计除外，在特殊设计当中可以豁免。卡片组在**每个断点**的列数都不能让最后一行只剩 1 个（`N % C == 1`）——4 张走 4 → 2 → 1、跳过 3 列，别留 3 + 1。

**避免 AI slop**：滥用渐变、圆角＋左边框强调容器、被用滥的字体（Inter、Roboto、Arial、Fraunces）。

**做 hero / signature element / 复杂动效 / Canvas / WebGL / 进阶排印 / 材质纹理 / 地图 / 音频 / 音画同步 / 数学公式时先读 `references/design/visual-techniques.md`**——里面有动效工具链（IntersectionObserver / GSAP / Lottie / View Transitions / Scrollama / CSS scroll-timeline）、Canvas/WebGL 选型（three.js / p5.js / matter.js）、进阶排印（variable font / background-clip / SVG textPath / feTurbulence）、材质纹理层（grain / duotone / halftone）、地图（Leaflet / MapLibre / D3-geo / Deck.gl + 免费瓦片源）、Web Audio（Tone.js / 原生 AudioContext / sonification）、动画+声音协同（音频主时钟、三种协同模式、user gesture 门槛、mute 与 reduced-motion 双通道）、KaTeX 数学公式，以及每一层对应的 slop 红线（毛玻璃、glow border、遮挡内容的密集粒子、data-aos 全站铺、Leaflet 蓝大头针、Mercator 全球图、rainbow 色板、音频自动播放、音乐可视化跳舞背景等）。

**设计 3D 场景读 `references/design/3d-design.md`**，掌握材质、阴影、光照、运镜的设计方法。

**不用 emoji**：尽可能不要使用任何 emoji，也不作图标、不作装饰、不放进数据，除非用户品牌资产明确包含。需要图标体系时用内联 SVG（`<svg viewBox="0 0 24 24">`）建立风格连贯的图标语言。

**要有 favicon**：用 SVG 或 AI 生图，为产物搭配一个合适的 icon，内联进 HTML。

在既有 UI 上增补时，先理解并遵循它的视觉语汇：文案风格、配色、hover 状态、卡片布局、密度。

## 参考文档地图

### `references/`

| 文档 | 何时读 |
| --- | --- |
| [`interactive-report.md`](references/interactive-report.md) | 命中上述灵动 HTML 触发条件时必读；确定题材表达、动态叙事与教学交互 |
| [`lark-apps-publish.md`](references/lark-apps-publish.md) | 用户要「发布」「可访问的链接」，或给了 doubao-html 链接要基于它改、发布出错 |
| [`windows-compat.md`](references/windows-compat.md) | SystemPrompt 出现 `Computer OS: Windows`——**必须完整 Read**，否则大面积报错 |

### `references/design/`

| 文档 | 何时读 |
| --- | --- |
| [`frontend-design.md`](references/design/frontend-design.md) | **读完主 SKILL 后必须完整 Read，再开始设计和写代码**；同一任务已读后的小改动不重读 |
| [`visual-techniques.md`](references/design/visual-techniques.md) | hero / signature element / 复杂动效 / Canvas / WebGL / 进阶排印 / 材质纹理 / 地图 / 音频 / 音画同步 / 数学公式 |
| [`3d-design.md`](references/design/3d-design.md) | 设计 3D 场景（材质、阴影、光照、运镜） |

### `references/chart/`

| 文档 | 何时读 |
| --- | --- |
| [`atlas.md`](references/chart/atlas.md) | **做图表与图表交互的统一入口**：先定选型与信息组织，再按其中指引选读下面两份 |
| [`reading-interactions.md`](references/chart/reading-interactions.md) | 常规读图、固定比较、总览查看某个对象的明细（由 atlas 分流，不单独作入口） |
| [`experience-examples.md`](references/chart/experience-examples.md) | 从同一批记录筛群体做多维比较，或明确的教学实验（同上） |

## 高频错误预防

### 通用 · 适用所有任务

#### 窄屏先设计，不要事后补丁

- **第一行 CSS 就为 375px 写**，桌面扩展在 `@media (min-width: 768px)` 里追加。不要先写桌面 CSS，再补 max-width 媒体查询压回窄屏。
- 多列 grid/flex 在 500px 断点**显式指定列数**（`grid-template-columns: repeat(N, 1fr)`，N 按内容密度自选）。**不用** `auto-fill` / `auto-fit`，它们在窄屏容易多算出一列把内容挤成一字宽。
- Flex 子项加 `min-width: 0`，否则长英文单词撑出视口。
- 流程图 / 时间轴在窄屏改成普通纵向文档流，不用 `position: absolute` 硬压。

#### 移动端字体

- **设计目标**：正文 / 说明 / 状态 / 可操作信息 ≥ 14px；`<input>` 和 `<textarea>` ≥ 16px。

#### viewport meta 硬约束

- `<meta name="viewport">` 必须有 `width=device-width, initial-scale=1`。
- **禁止** `maximum-scale=1` 或 `user-scalable=no`

#### 数据固化进 JS

- **单文件交付默认把数据固化进 JS**（`const RAW_DATA = [...]`）
- 大数据集（`RAW_DATA` >5MB或用户会频繁换数据）改用 `<input type="file">` + `FileReader`，让用户选文件。

#### 表格列宽必须显式给

- 多列表格加 `table-layout: fixed`，每一列写宽度加起来 100%（`<colgroup><col style="width:25%">` 或写在 `th` 上）。
- 漏写一列，`auto` 布局会把它压到一字宽、中文逐字折行，行高被撑到半屏。

#### 时间轴用 grid 三列

- 三列（时间 / 轴 / 内容）：圆点放中列 `justify-self:center`，轴线用 `calc()` 从列宽变量推出——不要手算坐标。
- 圆点中心和轴线中心 0px 对齐；文字和轴线不重叠。
- 横向时间轴用 grid 三行 + `align-self:center`，同理。

#### HTML / SVG 编码

- **HTML 文本节点和属性值**里 `<`、`>`、`&` 必须转义（`&lt;` / `&gt;` / `&amp;`）。`<script>` / `<style>` 内容不转义（会破坏 JS/CSS 语法）；`<script>` 里如果需要写字符串 `</script>` 用 `<\/script>` 断开。
- `<use href="#id" xlink:href="#id">` 同时写两个属性（`file://` 兼容）；SVG 引用禁止指向外部 URL。
- 长字符串批量 Edit 前后核查 HTML 语法边界，别把容器提前闭合。

#### shot.py 报告的正确读法

stdout 会输出短摘要：给 `status`、各 severity 计数、截图路径、按规则聚合的 finding，以及 `reportPath`。
不要用 `tail` / `grep` / pipe 处理 stdout。
完整报告每次都会写到 `_shots/report.json`。要看 evidence / hint 细节就 Read。

#### 验收的结束判据

- 结束标准是：**影响功能、阅读、用户明确要求的问题已确认解决**。不要求 warning 清零。
- 同类问题一次改完，不要一条一条改一条一条重跑。
- 首次完整验收之后，只重查改动影响到的部分；只有改了全局布局、DOM 结构或外部依赖才重新完整验收。
- 有 selector 就直接参考 selector 改，没 selector 的规则（如 favicon 这类文档级）看 `reportPath`。

#### 改文件的顺序

- 用 Bash / Python / 重定向写过文件之后，**下一次 Edit 前先 Read 一次**刷新文件状态。否则 Edit 会因文件状态过期被拒，你得把整个补丁重新写一遍。

#### 交付资产

- 一个 case 只交付一份 `.html`；present_files 的 `artifacts[].name` 写产物文件名（`销售仪表盘.html`），不另起标题。
- 只做用户本轮明确要求的内容；未提供来源或不可验证的事实标为假设或不写。

### dashboard · 数据看板 / 数据分析 / 仪表盘

#### 数据：先搞清楚数据，再研究 UI

- 用样本验证每个字段名、单位、类型、索引；不确定的字段不上页。
- 为空、缺失、边界值先定明确显示态（"暂无数据"、"—"、"0%"），再写 UI。
- 运行时算出的数值必须格式化再进 DOM：`toFixed(N)` 限位（避 `1/3` 变 `0.333333`）；大数用 `.toLocaleString()` 加千分位；涉及浮点等值比较用 `Math.round(x * 100) / 100` 收精度。

#### 图表实体断言

- 图表渲染失败的判据：摘要里没有 `consoleErrors`（ECharts 初始化失败会抛错）；截图上每个图表区域确实画出了内容而不是空白框。
- canvas / SVG 元素数量与预期一致，缺就是渲染失败，不是"截图问题"。

#### 图表空间预算

- 标题 / 图例 / 轴标签 / 数据标注**不共用坐标空间**——先给每类元素预留独立矩形，再填内容。
- 空间不足按顺序砍：隐藏次要数据标注 → 图例改 hover 悬浮 → 轴标签隔项 → 标题缩短。**禁止缩小字号硬塞**（会触发 `mobileFontIssuesWarning`）。
- 移动端图表容器宽度应占视口 ≥ 65%，否则堆叠成单列——否则会出现"空图 / 一根线 / 坐标轴叠一起"。

#### 多状态验收

- 筛选、切 tab、看明细、重置这类联动，**挑一条最核心的**驱动一次确认联动生效（`--eval-file` 注入脚本 + 截图），不要每个状态都截一遍。
- 剩余状态靠代码审查确认：同一套渲染函数、同一个数据源的状态，验一个就够。

### interactive · 交互 / 游戏 / 工具应用

#### 核心路径验一条

- 交互 / 表单 / 游戏 / 多视图 / 路由类页面：**挑一条最核心的用户路径**驱动一次，确认主流程能走通（初始态 → 关键动作 → 结果态）。
- 不要列 3-5 条路径逐条驱动，也不要每条路径都覆盖异常态。
- 其余路径靠代码审查：共用同一个状态机/渲染函数的分支，验一条即可推及。

#### 状态机 / 计算先 fixture 跑通再接 UI

- 计算、状态、多窗口、路由、动画时序类逻辑：先用 **fixture / mock 数据**渲染，断言 DOM / 数值非空、状态变化正确，再接真实数据。
- 不要一次拼完复杂内联 JS 就调视觉，保证基础的代码语法正确，代码中：`undefined`、错误闭合、越界索引会让整个图表 / 计分 / 日历空白。

#### 触摸等价路径

- 拖拽、悬停（hover-only 触发）、双击必须给触摸设备可完成的**点击等价路径**。
- 可点击 / 可输入 / 可切换控件的**可点击热区**不小于 44×44px；控件本身可以小（如 checkbox 19×19），但外层可点击 `<label>` 或 wrapper 必须达标。

#### 游戏 / 动画

- 依赖时间的（计分、倒计时、AI 决策）用 fixture 跑通完整循环再接真实输入。
- 音频类默认 mute + 用户 gesture 后启动，不要自动播放。
- Canvas / WebGL / 3D 参考 `references/design/visual-techniques.md` 和 `references/design/3d-design.md`。

### report · 长报告 / 信息图 / 长图 / 研报

#### 打印 / 固定画布预算

- 打印或固定尺寸作品（A4 / A1 / 海报）**在写内容前**先锁：viewport / DPR / 画布高度 / 字体行高 / 页脚 / 图例 / 标注安全区。
- 首版同时写 print stylesheet，不要留到最后补。
- 长表 `break-inside: avoid-page` 只对**短卡片**使用；整段长表或长 section 用它会产生大片空白。
- 打印后只抽查：首页、一个跨页表格或长卡片、末页。不要每页都读。

#### 装饰 vs 正文分层

- 装饰性圆形 / 网格 / 出血背景放**独立绝对定位层**（`aria-hidden="true"`），**不要**给正文容器加 `overflow:hidden` 来裁装饰——会误伤正文触发 `clippedText`。
- 页面渲染高度超过 16384px 会撞 Chromium 位图上限，末段分片会是白页。不是 shot.py bug——按章节重新组织内容，或明确接受"末段视觉不可见"。
