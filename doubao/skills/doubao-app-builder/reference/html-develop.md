# HTML 本地开发链路

本文档是 `html` 类型产物的完整开发规则：由你（当前 agent）在本地新建任务目录、用**原生 HTML/CSS/JS 编写以 `index.html` 为唯一入口的产物**，图片等素材下载到任务目录、用相对路径引用。凡任务被判定为 `html` 类型（判定规则见 [`../SKILL.md`](../SKILL.md)），动手前必须完整读取本文档。

跟 [`webapp-develop.md`](webapp-develop.md) 的分工：**html 链路做单文件展示物**（一个 `index.html`，原生 JS，无构建），**webapp 链路做工程化应用**（多页面真实路由、组件化、有构建）。两条链路互斥，一个任务只走一条，规则不交叉引用——走 html 链路时不要读 webapp 的规范，反之亦然。

本文档同目录下还有：

- `steering/` — 媒介专属指引与设计基础层，按文末「媒介 steering 路由」加载：六类**入口媒介**（slide-deck / interactive-prototype / data-viz / visual-report / hi-fi-design / mini-game）**排他加载**，一次只读命中的那一个；`frontend-design.md` 是一切设计工作动手前的基础必读；`charts.md` 在任何场景需要 ECharts 图表时叠加读取。
- 界面脚手架为**平台 SDK 组件**（自定义元素，锁定版本 CDN 直引，无需下载 / 上传 / 内联），见下文「Starter Components」。

## 硬性技术栈约束

1. **单一入口**：交付物以任务目录下的 `index.html` 为唯一入口 HTML。你写的 JS / CSS **可以按需拆成同任务目录内的多个文件**（如 `app.js`、`views/detail.js`、`styles.css`），在 index.html 中以相对路径的普通 `<script src>` / `<link rel="stylesheet">` 引入（引入顺序满足依赖，先库后调用）；也可以继续内联在 `<script>` / `<style>` 块里，按代码量和可维护性自行取舍。多「页面」仍用页内 hash 路由切换视图，**不拆多个 HTML 文件**。（自写 js / css 属于源码而非素材，不受资源规则约束，本来就用相对路径引；平台 SDK 组件以锁定 CDN 地址引入，见「Starter Components」。）
2. **新建任务目录**：每个任务在工作区根目录下新建独立的语义化目录（如 `sales-dashboard/`），产物写在其中——避免多任务文件命名混淆、互相干扰。迭代已有任务时进入原任务目录继续改，不另起目录。
3. **原生 JS**：不使用 React / Vue / JSX / Babel / 任何构建工具，不用 `type="module"`。状态管理用普通对象 + 重渲染函数。
4. **三方依赖白名单**（只允许以下锁定资源，不引入其他外部库）。JS 库统一走 **jsDelivr**（版本化 URL 内容不可变，多 CDN 容灾），标签必须携带下面给定的 `integrity`（SRI）与 `crossorigin`，防止内容被篡改：
   - 图表确需交互（悬停、筛选、实时数据）或复杂度超出静态 SVG 时用 ECharts；简单图表优先手写静态 SVG / CSS：
     `<script src="https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js" integrity="sha384-pPi0zxBAoDu6+JXW/C68UZLvBUUtU+7zonhif43rqj7pxsGyqyqzcian2Rj37Rss" crossorigin="anonymous"></script>`
     使用前先读 `steering/charts.md`（选型、视觉编码、窄屏适配与自检清单）。
   - 3D 场景（**不限于游戏**：演示、漫游、3D 可视化同样适用）用 Three.js r147 UMD，引入前先读 `steering/three-js.md`：
     `<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js" integrity="sha384-vV17nr/rMaJqmeZkFUzXLpHdQ+ME5QHKdydaqqN+3Ga39RJlNrTatJxHwGV4ml2C" crossorigin="anonymous"></script>`
     主库之外的 addon（`examples/js/…`）与主库同源同版本，不逐个加 SRI。
   - 游戏专用的 2D 物理库 Matter.js 以 `steering/mini-game.md` 的「库白名单」为准（同样是 jsDelivr 锁定版本 + SRI）。
   - Web 字体一律走自托管镜像 `https://miaoda.feishu.cn/fonts/css2`（Google Fonts `css2` 端点的直接替代，查询语法完全一致；返回的 `@font-face` 把字体文件也指向自托管 CDN，两跳都不经过 Google），不直连 `fonts.googleapis.com` / `fonts.gstatic.com`（部分地区不可达）。`family=` 处填实际字体族，多字族就重复多个 `family=` 参数：
     `<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=Noto+Sans+SC:wght@300;400;500;700&display=swap">`
     每个 `font-family` 都必须写完整的系统字体 fallback 栈，字体加载失败时页面仍成立。
   - jsDelivr 故障时的备用镜像是 **cdnjs**（`https://cdnjs.cloudflare.com/ajax/libs/<lib>/<ver>/…`，Cloudflare 官方运营，同版本文件字节一致，SRI 不变）。**禁止**使用 bootcdn、staticfile、polyfill.io（均有供应链投毒历史），不要用 unpkg 作为首选。
   - 自检：以上 script / link 的地址与 integrity 必须与白名单逐字一致。（白名单约束外部三方库；平台 SDK 组件按「Starter Components」一节的锁定 CDN 地址直引，同属允许清单、不加 SRI。）
5. **动画能力边界**：页面动画用 CSS transitions / animations 与 `requestAnimationFrame` 手写（deck 的入场动效契约见 slide-deck.md「动效」）。不提供时间轴动画引擎——「带播放条 / 可拖动进度的动画视频」类产物不在本链路支持范围，遇到时告知用户并提供替代（自动播放的 CSS 动画页，或建议改走其他能力）。

## 工作流

1. 理解用户需求。对全新或含糊的工作，按「提问」一节判断是否需要先澄清。
2. 探索所提供的资源。附件、文档链接、网页 URL 都要在动手前解析完（见「输入资料解析」）。
3. 列出 todo 清单。
4. 新建任务目录，把素材复制进去。按文末「媒介 steering 路由」判定并读取命中的入口 steering（排他加载）；一切设计工作动手前先读 `steering/frontend-design.md`。
5. 编写 / 修改 `index.html`（遵循「如何开展设计工作」「输出创建准则」「内容准则」）。
5.5 用户给了数据附件（csv / json / xlsx）时：**用本地路径把文件读进来、自己把数据解析算好，把结论和图表数据写进代码**——这类「拿这批数据做一份分析」的需求本来就该走本链路，页面运行时不必碰原始文件。⚠️ **页面要在运行时真读文件**（用户以后要换数据）的，本链路做不了——没有 dev server，`file://` 下读同目录文件会被浏览器拦，解析库也装不了——走 webapp（判定见 [`../SKILL.md`](../SKILL.md)）。**不要在页面里 fetch 平台 CDN 上的附件 URL**——那个链接会失效。
6. 自检：三方依赖地址与白名单一致；用到的 SDK 组件地址与「Starter Components」清单逐字一致；图片与音视频都已下载到任务目录、用相对路径引，产物里没有平台 CDN 链接（Web 字体除外，它走白名单里的自托管镜像）；index.html 引用的本地 js / css 文件齐全、相对路径正确。
7. 交付：**这一轮要不要发布，在第 1 步就该看清了**（用户 query 里有「发布」「上线」「部署」「给个能分享的链接」就是要发布）。两条出口互斥，只走一条 —— **不要先按下面第一条交付一遍文件、再去发布**，那样会推两个卡片：
   - **没让你发布（默认）** → 用正确的 HTML 代码 / 文件交付方式把 `index.html` 交付给用户（告知文件路径；拆分了 js / css 时随 index.html 一并交付，不可只交付入口文件），**禁止用 `open_url_in_browser` 充当交付**；artifact 名称按页面主题命名，**不带本地文件名或路径**（如 index.html、任务目录名）。用户泛泛提发布 / 托管 / 拿链接诉求但没让你执行时，告知他**点击预览后通过发布按钮自行发布**。🔴 **交付说明里要点明产物归属**——这是妙搭平台的产物，需要线上地址时走平台链路发布。用户常隔很多轮才提发布，那时手边只剩这段对话，没有这句锚点容易跑去给通用部署方案。
   - **这一轮要发布** → **跳过上面的文件交付**，直接走 [`publish.md`](publish.md) 发布，成功后**调 `present_files` 交付线上地址**，只推这一张卡片。

     **交的是线上地址，不是文件。** 应用在线上跑着，用户要的是能点开的地址——传 `index.html` 是交了输入不是结果。正文只用一两句说这是什么，**不要再重复贴一遍链接**。细则见 [`publish.md`](publish.md)「交付形式」。

**质检引导**：**首次生成不要做任何质检**——不截屏、不预览页面、不做浏览器 / 页面操作验证，完成第 6 步自检后直接交付。

> 发布的完整规则见 [`publish.md`](publish.md)；改可用范围 / 访问权限、导出应用代码见 [`app-manage.md`](app-manage.md)。

## 提问

默认基于用户给的信息、项目上下文和合理假设直接开始，不为收集偏好而打断。只有当一个决策同时满足两条，才用对话文本直接向用户提问（等用户答复后再继续）：① 用户没说、且从 prompt / PRD / 截图 / 素材也推不出；② 猜错要推倒重来（承重决策）。两条只要有一条不成立就直接做。

承重、推不出就必须先问的：交付媒介 / 格式（报告 vs deck vs 看板）；视觉方向（从零起且资料推不出时）；大体量交付的受众 / 目的与核心范围。局部、给默认直接做的：变体数量、界面文案、占位内容、单屏密度——给合理默认（变体默认 2-3 个有清晰差异的方案），让用户在产出上重定向。通常一轮聚焦提问就够，把承重的未知一次问齐。

## 输入资料解析

用户给的附件、文档链接和 URL 是设计的输入，必须在动手前解析完，跳过这一步产出的内容只能靠编造。数据文件（csv / json / xlsx）先看结构和样本行，指标一律用脚本从源数据计算，不要目测；压缩包先解压逐个查看；文档（docx / pdf）用环境的解析能力读**全文**；飞书云文档 / 多维表格用 `lark-cli` 读取，读不到就请用户导出或粘贴；网页 URL 抓取全文后再产出，抓取失败如实告知，不凭 URL 编写。

## 如何开展设计工作

动手前先读取 **`steering/frontend-design.md`** 确立视觉方向——它教你如何果断做出有意图、不落模板俗套的美学抉择：有品牌或既有 UI 时对齐现有视觉语言，从零起步时据主题 / 材料立一个契合的方向。当用户请你做高保真 UI mockup、界面设计或带多方案的视觉探索时，开始之前先读取 **`steering/hi-fi-design.md`**。媒介 steering 的指令与通用设计规则冲突时，以媒介 steering 为准。

- **静态视觉 / 设计稿 / 多方案探索**（颜色、字体、单个元素、整屏 UI、流程关键帧）→ 用 design-canvas SDK 把各方案铺陈在 `<design-canvas>` 画布上（每个方案一个 `<dc-artboard>`，用法见「Starter Components」）。除非用户明确要求可交互，否则不要把设计稿升级成点击原型。
- **用户明确要求可交互的流程或产品 demo** → 做成直接运行的高保真原型（读 `steering/interactive-prototype.md`）。可交互原型禁止用 design-canvas 画布包裹。

用户要**多个版本 / 几种方案对比**时，优先在原件上承载变体——用页内开关、Tabs 或模式切换；一个带版本切换的主文件优于多个文件。⚠️ **用户给了确定方向的修改指令时不适用**：「把配色改成深色」就是直接改成深色，不是加一个明暗切换开关。

## 默认美学指令

如果用户没给参考或艺术方向：能从主题、材料或场景推断出一个有把握、不会返工的视觉方向，就主动确定，并在设计中体现假设；如果推不出、又是从零起的项目，先用对话文本问清偏好的调性、受众、颜色、字体、情绪等再动手——不要在推不出方向时硬选，slop 就是这么来的。

定下视觉方向后（无论是推断还是问来的），创建设计时遵循以下指引：

- **字体与排版。** 选择与主题、媒介和场景匹配的少量字体，并通过字号、字重、字宽、行长、语义断行、数字样式和文字位置建立清晰层级与视觉节奏；不依赖增加字体数量制造变化。
- **背景与色彩体系。** 确定主色调，并建立与主题协调的中性基底、主题色和必要的章节／语义色。背景不局限于纯黑、纯白或单一色调，可以根据内容属性、页面角色和叙事节点使用不同色调、主题色底、局部色域、图片或图形背景。
- **色彩一致性。** 一致性来自共享色板、字体、栅格、图形语言和明确的颜色关系，不要求所有页面使用相同背景。颜色变化应帮助识别章节、信息层级和重点，避免无语义地逐页随机换色。
- **强调色。** 使用数量克制、关系协调的强调色，并根据背景、信息层级和色彩语义调整明度与彩度。图表、状态和章节色需要清楚可区分，但应属于同一视觉体系。
- **中性色。** 黑、白、灰可以带有与主题协调的细微色相，避免把纯黑白或低饱和配色作为所有专业场景的默认答案。
- **视觉复杂度。** 视觉丰富度应服务内容。不要添加无信息价值的装饰，也不要把"克制"理解为单调、大量留白、缺少图片图表或所有页面使用同一种构图。

关键：如果已给出其他美学指令（如参考图、品牌体系、设计规范或媒介专属 steering），或项目中已有文件，则完全忽略默认美学。

## 图像素材与外部信息

图片素材能显著提升产物的美观度——不要默认只用纯 CSS/SVG 撑起全部视觉。

**载体选型规则**：

- 图标、状态标记、导航符号、简单示意图和数据图表属于**符号 / 信息型**元素，可以使用内联 SVG 或 CSS。
- 人物、角色、动物、具体物体、产品情境、真实场景、hero 主视觉、章节题图和叙事插画属于**具象 / 氛围型**元素，应使用用户素材、项目已有素材、图片检索或图片生成能力。
- 除非用户明确要求矢量插画，**禁止用手写 SVG 或 CSS 几何图形代替依赖形象可信度的具象画面**。
- 「简单图表优先 SVG / CSS」只适用于数据可视化，不得扩展到人物、场景和插画。

**图片来源选择顺序（严格按序）**：

1. **用户提供和项目已有的素材**——始终第一优先。
2. **图片生成能力**——没有可用素材时的默认选择：hero、氛围图、角色、场景、章节插画等一切不要求忠实呈现真实对象的位置都用生成（prompt 写清风格、构图、配色，使产出与视觉方向一致）。
3. **外部检索素材**——仅当需要忠实呈现真实人物、产品、地点、Logo 等事实对象、生成会失真造假时才用，且必须通过下面的「外部素材使用门」。

**外部素材使用门（用前必看）**：产物中的每一张外部图片都必须来自本次会话的真实产出——图片生成能力返回的 URL **先下载到任务目录再引用**；检索到的图片同样先下载，并且必须**实际查看内容**（用读图能力打开确认）：内容与目标对象一致、清晰完整、无水印、不是防盗链占位图，确认通过才用——**引用的仍是下载到任务目录后的相对路径**；无法查看或确认不符的，换图重试或改用图片生成。

**能力发现（不绑定工具名）**：图片生成工具的名称不固定。执行时检查当前环境提供的工具与 skills 元信息，凡描述包含「根据文本创建新图片」「图片生成」「文生图」或等价能力的，都视为图片生成能力；图片检索能力同理按描述识别。命中上述生成条件且该能力存在时，**必须实际调用**，不能只在文字中建议使用。

**动手前素材盘点**：编写 HTML 前，先盘点 hero、封面、章节题图、角色、产品情境、背景场景等依赖具象素材的位置；需要生成的图片尽量在写页面前批量生成，再围绕实际图片的构图、比例和色彩设计页面。不得因为图片生成、下载比内联 SVG 多一步，就把应使用图片的位置降级成 SVG / CSS。

**没有图片生成能力时**：按素材类型选择其他合法来源（用户素材、项目素材、图片检索）或调整构图。SVG / CSS 只能兜底图标、状态、简单示意图、数据图表和抽象装饰，**不得兜底人物、角色、动物、具体物体或真实场景**；只有 wireframe 或低保真原型允许使用明确的图片占位符。

联网信息：`general_search` / `web.fetch`——内容需要真实事实、数据时先搜再写，标注出处。

🔴 **资源规则（图片与音视频一体适用）：全部下载到任务目录，用相对路径引，产物里不出现任何平台 CDN 链接。** 生图返回的 URL、检索到的图、用户给的素材，一律先 `curl` 下来再引——平台 CDN 会失效、会防盗链，写进产物就是埋雷。检索图尤其不要热链搜索结果页的原始地址。小图标不算资源：用手写内联 SVG。用户已提供的素材优先使用，不要擅自用生成图替换。

## 输出创建准则

- **版本保留**：没有 git 兜底，重大修订前先把当前版本复制进任务目录的 `_backup/` 子目录（如 `_backup/index-v1.html`）再编辑；`_backup/` 不属于交付产物。
- 在既有 UI 上增补时，先理解并遵循其视觉语汇（文案风格、配色、hover 状态、阴影卡片布局、密度）。
- 写规范的 HTML：显式闭合每个非空元素，属性值用双引号，不自闭合非空元素（写 `<div></div>` 而非 `<div/>`）。
- 绝不使用 `scrollIntoView`；如需滚动改用其他 DOM 方法。
- **Emoji**：不要在生成的代码中使用 emoji——不作图标、不作装饰、不放进数据（除非用户品牌资产明确包含）。
- **图标**：需要图标体系时用手写内联 SVG（`<svg viewBox="0 0 24 24">`）建立风格连贯的图标语言。
- 代码量大时优先按视图 / 组件 / 数据块拆分 js / css 文件组织；留在 HTML 内的大段代码用清晰的分段注释组织（`<!-- ===== 视图：xxx ===== -->`）。
- **强烈倾向用带 `gap` 的 flex/grid 排布 UI 元素**，不用靠空白或逐元素 margin 的 inline 流；inline 流只留给正文段落。`text-wrap: pretty`、CSS grid 等高级 CSS 都是好帮手。

## 内容准则

**内容取舍**：不添加与用户目标无关或没有依据的内容；内容不足以成页时合并、重构或请求材料，不靠放大留白撑页。**数据保真**：用户给了源数据时，每个图表数字与结论都必须从源数据实际计算得出并可追溯，不目测、不凑整、不编造（做数据报表 / 看板前读 `steering/data-viz.md`，其数据忠实度约束同样适用）。**硬性规格是约束**：页数、画幅、必含模块逐条对照满足，交付前自查。**尺度**：1920×1080 幻灯片文字 ≥ 24px；移动端点击目标 ≥ 44px。**避免 AI slop**：滥用渐变、emoji、圆角＋左边框强调容器、被用滥的字体（Inter、Roboto、Arial、Fraunces）。

## Starter Components（平台 SDK 组件，CDN 直引）

平台提供一组现成的界面脚手架 SDK（**自定义元素 / Web Components，零依赖、无 React**），托管在锁定版本的 CDN 上——**直接用 `<script src>` 引入即可，不需要下载、上传或内联**。按需引入：用哪个组件引哪个文件，script 标签置于对应自定义标签与调用代码之前。

地址前缀（**全小写，逐字一致**，后接文件名）：
`https://sf3-scmcdn-cn.feishucdn.com/obj/feishu-static/miaoda/coding-unpkg-sdk/@lark-apaas/coding-registry-buildless@0.1.22/scripts/`

| 文件 | 提供的标签 | 关键属性 / 说明 |
|---|---|---|
| `deck-stage.js` | `<deck-stage>` | 幻灯片 deck 外壳：`width`/`height`（默认 1920×1080）、`no-rail`；每页一个 `<section data-label="…">`（完整用法见 `steering/slide-deck.md`） |
| `design-canvas.js` | `<design-canvas>` `<dc-section>` `<dc-artboard>` `<dc-postit>` | 可平移／缩放设计画布；`<dc-artboard>`：`id`·`label`·`width`(260)·`height`(缺省随内容增长)·`chromeless`；`<dc-section>`：`id`·`title`·`subtitle`；artboard 支持拖拽重排 / 改名 / 删除 / 全屏聚焦 |
| `ios-frame.js` | `<ios-device>` `<ios-status-bar>` `<ios-list>` `<ios-list-row>` `<ios-keyboard>` | `<ios-device>`：`width`(402)·`height`(874)·`dark`·`keyboard`；**safe-area 必设**——屏幕内容用 `--ios-safe-top` / `--ios-safe-bottom` 做内边距，否则被状态栏 / Home 指示条遮挡 |
| `android-frame.js` | `<android-device>` `<android-status-bar>` `<android-list-item>` `<android-nav-bar>` `<android-keyboard>` | `<android-device>`：`width`(412)·`height`(892)·`dark`·`keyboard`；`<android-list-item>`：`headline`·`supporting`·`leading` |
| `macos-window.js` | `<macos-window>` `<macos-sidebar-item>` `<macos-sidebar-header>` `<macos-toolbar>` `<macos-glass>` | `<macos-window>`：`width`(900)·`height`(600)·`title`；侧栏行放进 `slot="sidebar"`（窗口自渲染侧栏容器，只需提供行） |
| `browser-window.js` | `<browser-window>` `<browser-tab>` `<browser-toolbar>` | `<browser-window>`：`width`(900)·`height`(600)·`url`·`active-index`；`<browser-tab title="…">` 为子元素，无 tab 时渲染单个 New Tab |

- 布尔属性按**存在性**生效：写 `dark` 即开、省略即关。
- 更详细的属性与行为在每个 SDK 文件头部的 `/* BEGIN USAGE */` 注释里——需要细节时直接抓取上述 CDN 文件阅读头部，不要凭猜测使用未列出的属性。
- 不要手搓这些轮子，也不要把 SDK 代码下载后内联或改写。

## 媒介 steering 路由

`steering/` 下分两层，加载规则不同：

**基础层（不是入口媒介，按条件叠加读取）**

- `frontend-design.md` — 一切设计工作动手前必读：视觉方向四槽位、避开 AI 默认长相的校准清单、两遍法流程、设计中的写作。
- `charts.md` — 任何场景需要 ECharts 图表时先读：选型映射、视觉编码、窄屏适配、自检清单。简单图表优先静态 SVG / CSS，不必引库。
- `three-js.md` — **任何 3D 场景**（3D 小游戏、3D 演示 / 漫游 / 可视化）需要 script 引入 Three.js 时读（UMD 引入与 addon 依赖顺序）。它是技术参考不是入口媒介，不受「排他加载」限制。

**入口媒介（排他加载：一次只读命中的那一个，严禁交叉加载）**

| 命中条件 | 读取 | 易混淆项（不要读） |
|---|---|---|
| PPT / 幻灯片 / 演示文稿 / pitch deck / slides / 路演材料——供演讲者演示的 16:9 deck | `steering/slide-deck.md` | interactive-prototype、visual-report |
| 可交互原型 / 产品 demo——用户要「能操作」，**且点名了 HTML**（没点名 HTML 的应用形态，尤其管理后台 / 增删改查，走 webapp 本地链路，判定见 [`../SKILL.md`](../SKILL.md)） | `steering/interactive-prototype.md` | slide-deck、hi-fi-design |
| 数据报表 / 数据看板 / BI / KPI / 周报月报——用户有数据文件或明确指标，产物以数据为主体 | `steering/data-viz.md` | visual-report |
| 可视化报告 / 专题视觉页 / 信息图 / 视觉长图——以材料、观点、叙事为主体的内容型作品 | `steering/visual-report.md` | data-viz、slide-deck |
| 高保真 UI mockup / 设计稿 / 多方案视觉探索——给人看的界面设计，不要求能操作 | `steering/hi-fi-design.md` | interactive-prototype |
| 网页小游戏——有胜负 / 挑战目标 / 玩法循环 | `steering/mini-game.md` | interactive-prototype |

裁决锚点：产物是**演示翻页看的** → slide-deck；**点击操作用的** → interactive-prototype；**数据 / 指标驱动的阅读页** → data-viz；**材料 / 观点驱动的阅读页** → visual-report；**给人看的界面设计稿** → hi-fi-design；**给人玩的** → mini-game。都不是（官网、落地页等普通展示页）→ 不读入口 steering，读完 frontend-design 后按本文档执行。
