---
name: html
version: 1.0.69
description: 专门设计、生成和修改可直接在浏览器中打开的 HTML 页面或已发布的 doubao-html 链接。交付物以独立 .html 文件为主，可包含内联或本地 CSS、JavaScript，支持页面布局、视觉样式、交互效果、响应式适配、组件设计和内容展示。适用于静态网页、单页展示、活动页、原型页、HTML 模板及页面片段。不处理前后端工程、应用框架、服务端接口、数据库、用户系统、构建部署或运营数据。
---

# 单页 HTML 开发

## 适用范围

以内容呈现和交互体验为主的单页产物：官网 / 落地页 / 营销页、可视化报告 / 数据看板 / 信息图 / 长图 / 研报、动画 / 3D 场景 / 网页小游戏、SVG / Canvas 页、高保真 UI 设计稿、可交互原型，以及单一用途轻工具（计算器、文本对比、随机分组）。

要后端、数据库、账号登录、多人协作，或要把数据文件随产物一起交付的，超出本 skill 范围——如实告知，不假装实现。

**必读顺序：读完本 SKILL.md 后，按场景完整阅读对应的设计文档；同一任务命中多个场景时叠加加载，完成后才开始设计和写代码：**

| 场景 | 必读 |
| --- | --- |
| 计算器、小工具、小应用、小游戏等以操作功能为主的页面 | 默认不读前端设计；用户明确要求美观、视觉风格时，读 [前端设计](references/design/frontend-design.md) |
| 报告、看板、信息图、长图、研报、展示网页、设计稿 | [前端设计](references/design/frontend-design.md) |
| 灵动 HTML | [前端设计](references/design/frontend-design.md)、[灵动报告设计](references/design/interactive-report.md) |
| 3D 场景 | [前端设计](references/design/frontend-design.md)、[3D 设计](references/design/3d-design.md) |

同一任务已完整读过的文档，后续小改动不重复加载；尚未读过的必读文档仍须先读。

- **灵动 HTML**：仅当用户明确提出「灵动报告」「要灵动感」「使用灵动风格」等要求时触发；触发后，**写代码前必须完整读取 [前端设计](references/design/frontend-design.md) 和 [灵动报告设计](references/design/interactive-report.md)**。

- **3D 场景**：需要三维空间、材质、光照或运镜的页面。触发后，**写代码前必须完整 Read [前端设计](references/design/frontend-design.md) 和 [3D 设计](references/design/3d-design.md)**。

## 关键步骤

> 运行环境：云电脑 / 本地电脑，按下述顺序判定。
> 1. SystemPrompt 中的 `Computer OS` 字段：值为 `Windows` 或 `Mac` 判为本地电脑；值为其他判为云电脑。
> 2. SystemPrompt 未包含 `Computer OS` 字段时：`<system-reminder>` 包裹的内容中出现 `Runtime: local_pc` 判为本地电脑，出现 `Runtime: cloud_vm` 判为云电脑。

**建目录**：每个任务在工作区根目录下新建能说明任务用途的目录（如 `sales-dashboard/`）；HTML 文件放在目录里，**文件名也要能说明内容**（如 `销售仪表盘.html`），**不要叫 `index.html`**。图片素材放进 `assets/`。迭代已有任务时进原目录改，不另起。**本地电脑**使用运行环境指定的工作区，不要另用 `/tmp` 等系统临时目录。

**平台差异**：SystemPrompt 里若出现 `Computer OS: Windows`，**需要完整 Read `references/windows-compat.md`，查看在 windows 平台上执行命令所必须要注意的问题，否则会出现大面积报错**。

**写 HTML**，守住这几条：

- **单文件自包含**：一个 `.html` 文件到手就可用。
  - CSS 写在 `<style>`、JS 写在 `<script>` 内联块里，**不拆出** `.js` **/** `.css` **/ 额外 HTML 文件**。
  - 多「页面」用页内 hash 路由切换视图，大段代码用分段注释组织（`<!-- ===== 视图：xxx ===== -->`）。
  - **原生 JS**：不用 React / Vue / JSX / Babel / 任何构建工具。状态管理用普通对象 + 重渲染函数。
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
  - 当用户没有明确的发布需求时：用 `present_files` 交付任务目录中的最终 `.html` 文件，**`artifacts[].name` 写产物文件名，不要另起标题**（`销售仪表盘.html`，不是「销售数据看板」）。**同一个产物只交付一个 `.html` 文件**——按运行环境选定一种图片引用方式就够了，不要再额外附一份「以防万一」的备份版或压缩包，用户拿到两份不知道该打开哪个。交付说明如实写清：没实现的功能、用的是示例数据、做不了的能力。**`present_files` 的 `artifacts` 只包含最终 HTML 文件，不单独交付 `assets/` 等依赖目录。依赖目录保留在本地原位置，需要转发时，仅在回复中提醒用户连同目录一起发送。**
  
  - **`present_files` 调用后会直接向用户展示产物卡片，禁止在最终回复正文中输出任何链接**（包括发布返回的 `online_url` 如 `doubao.link` / `feishu.link`，以及 `present_files` 回执中的 `aka.doubaocdn.com` 等临时 CDN 地址），也不使用回执中的临时 CDN 地址再次调用交付工具或冒充网页链接。

  - 当用户想要「发布」、「可访问的链接」、「给我链接」时：阅读 `references/lark-apps-publish.md`，将你的 html 文件发布成一个 doubao-html 网页，此时无需交付 html 文件，仅需使用 `present_files` 交付发布接口返回的 `online_url`（卡片会自动展示，**不在回复正文里再贴一次链接**）。用户在文件交付后追加「链接发我」等要求时，同样先发布，再用 `present_files` 交付 `online_url`，不拿临时 CDN 地址代替发布。未发布时用 `present_files` 交付最终 `.html` 文件。
  
  - **发布接口确认成功后，直接用 `present_files` 交付返回的 `online_url`，禁止再访问该链接做检查**，避免检查环境缺少用户登录态而把登录页当成产物。
  - **最终给用户的回复不要过长**：最重要的产物是你最终生成的 html 产物，而不是给用户的最终回复，所以在交付了 html 产物后的最终回复不应该太长，**不能超过300字，也不能超过 8 行**，只需要简单介绍一下你生成的 html 产物即可

- **修改、参考已发布的 doubao-html 网页**：
  - 当用户给你提供了一个 doubao-html 链接（形如 `https://{xxx}.doubao.link/app/app_{xxxxxxx}/`），并希望基于此修改或新建时，阅读 `references/lark-apps-publish.md`。先用 `lark-cli apps +get --app-id <id>` 看 `app_type`：`html` / `modern_html` 是单页 HTML，下载源码、修改、重新发布即可；其他类型使用 `doubao-app-builder` 技能。
  

**改产物**：直接改任务目录里的原文件。

- 本地文件丢了就如实告知并请用户重新提供，**禁止凭记忆重造**；回答关于产物的提问同理，读文件后答，读不到不编。
- **小改动直接改**（改文案、调样式、换配色、修 bug）：同一任务已完整读过的本文档和 reference 不重读，不重新推导视觉方向；尚未读过的必读文档仍须先读。

## 外部资源

**JS 库统一走 jsDelivr**：`https://fastly.jsdelivr.net/npm/<包名>@<版本>/…`。故障时的备用镜像是 **cdnjs**（`https://cdnjs.cloudflare.com/ajax/libs/<lib>/<ver>/…`，Cloudflare 官方运营，同版本文件字节一致）。**禁止** bootcdn、staticfile、polyfill.io（均有供应链投毒历史），unpkg 不作首选。

**字体走自托管镜像** `https://miaoda.feishu.cn/fonts/css2?family=…`：查询语法与 Google Fonts 的 `css2` 端点完全一致，返回的 `@font-face` 也指向自托管 CDN，两跳都不经过 Google。**不直连** `fonts.googleapis.com` **/** `fonts.gstatic.com`（部分地区不可达）。多字族就重复写多个 `family=`，例如 `<link rel="stylesheet" href="https://miaoda.feishu.cn/fonts/css2?family=Noto+Serif+SC:wght@400;600;700;900&family=Noto+Sans+SC:wght@300;400;500;700&display=swap">`。每个 `font-family` 都要带完整的系统字体 fallback 栈，字体加载失败时页面仍然成立。

## 图像素材

**载体选型**：图标、状态标记、导航符号、简单示意图、数据图表属于符号 / 信息型，用内联 SVG 或 CSS。解释部件、空间或过程的结构示意可用 SVG / Canvas；主体需要分层、展开或改变视角时，按要解释的关系选择载体。结构示意要有可辨认的细节与对应关系，不冒充真实照片或精确工程图。「简单图表优先使用 Echart 来进行生成，而无需使用 SVG」只适用于数据可视化。

**来源偏好**：优先使用用户提供的图片与项目已有的素材，不要擅自替换；仅当要忠实呈现真实人物、产品、地点、Logo 等事实对象时使用外部检索，或按用户明确要求补充图片。网络图片先下载到本地再引用。

**比例与呈现**：使用图片时比例控制在 3:4 ~ 21:9（Banner / Hero 用 16:9 或 21:9，章节题图 3:2，方形插图 1:1）。用 `cover` 或固定高度时，用 `object-position` 或 `contain` 避免主体、文字、标签被裁切。

## 内容要求

**数据保真**：用户给了源数据时，每个数字和结论都要从源数据实际算出、可追溯，不目测、不凑整、不编造。

**数据附件要获取下来并分析**。

**内容取舍**：不加与目标无关或没有依据的内容；内容不足以成页时合并、重构或要材料，不靠放大留白撑页。当有大量信息需要展示时，清楚区分主要信息和次要信息；一个逻辑连贯的模块最好在一屏内讲清楚，必要时添加筛选与搜索能力。

### 文字表达

生成 HTML 内容时，应根据目标受众、主题特点与使用场景，选择合适的语言风格、内容深度和组织方式。首先明确页面要帮助用户理解什么、解决什么问题或完成什么行动，再结合受众的知识基础、阅读目的、使用情境及已知偏好，调整专业术语、解释程度、信息密度与表达语气；信息不足时，采用清晰、中性、易于理解的表达，避免仅凭年龄、职业等身份标签推断偏好。研究报告、学术分析等场景应保持专业、客观与严谨，围绕研究问题、方法或证据、核心发现、结论与局限展开，准确使用概念，区分事实、观点、推断与假设，避免将相关性表述为因果关系；关键事实、数据、研究结论及引用观点应有真实、可核验且直接相关的来源，优先引用原始研究、官方数据及权威资料，在对应内容附近提供引用标记或可访问的来源链接，必要时注明作者或机构、发布时间、统计时段与数据口径，对时效性信息进行核验，对无法确认的信息及结论的适用边界明确说明，不得编造数据、文献、引语或链接。

教学、培训与知识讲解场景应围绕明确的学习目标，依据受众的先备知识、理解能力与兴趣偏好，由浅入深地组织内容，通过受众熟悉的情境、具体案例、适当类比和必要的概念解释帮助理解，并按需加入思考题、操作演示、练习与反馈，澄清常见误区；面向初学者应减少未经解释的术语，面向有经验的学习者应突出原理、难点与应用，趣味性和互动性应服务于学习目标，兼顾表达亲和与知识准确。

商务汇报、方案介绍与决策支持场景应突出核心结论、关键依据、方案比较、收益与成本、风险及行动建议，语言简洁直接，使读者能够迅速判断重点；

大众科普与公共信息场景应使用通俗准确的语言，解释必要背景，避免过度简化造成误解；品牌展示、活动宣传与营销场景可采用更鲜明、生动且符合品牌定位的表达，清楚说明价值、适用人群与行动入口，避免无依据的夸大宣传。

所有场景均应保持主题聚焦、逻辑连贯、术语一致，确保标题、摘要与正文相互对应，优先呈现读者最关心的信息，按需分层展开细节；图表、案例、示意与交互应承担解释、比较、验证或练习的具体作用，演示数据、虚构案例与情境假设应明确标注，按钮、提示及交互反馈应准确说明操作及其结果。内容应具有与任务相匹配的完整性和可用性，避免空泛套话、重复堆砌与无关扩展，使每一部分都帮助受众更好地理解、判断或行动。

**硬性规格**：页数、画幅、必含模块按用户明确要求落实。

**时间演进优先用时间轴**：涉及阶段、演进、里程碑、前后对比、路线图的内容，默认使用时间轴，而非项目符号列表或纯段落；每个节点承载：时间、事件名、一句话说明（可选）、（可选）关键指标或图标，让单个节点即可独立传达信息，注意时间轴节点与连线适当对齐，文字和轴线、文字和图标不要重叠。
灵动报告已通过场景或其他视觉结构清楚交代先后关系时，沿用该表达，不重复添加时间轴。

## 图表及其交互设计方法

**图表服务于内容理解与判断**：依据任务和数据决定图表类型、数量与组合。图表呈现关系与证据，文字只写图表未直接呈现的解读或判断，**禁止把图表标签照抄一遍**。图表首选 ECharts；仅当其无法满足所需表达或交互时，再使用 D3 或 SVG。

**需要设计复杂图表或图表交互时，从 [references/chart/atlas.md](references/chart/atlas.md) 开始**：先确定图表选型与信息组织，再按其中的指引选读图内交互或多视图体验参考。简单静态图表直接实现。

## 视觉设计

**先认媒介，别默认做成网页**：HTML 只是载体，产物形态各不相同——信息图、长图、研报、看板、设计稿、动画、游戏各有各的表达惯例。只有真在做网页时才用网页那套语汇（顶部导航、hero、footer、等宽卡片栅格、底部 CTA 区）；其余形态套上网页壳子就是最典型的 slop。先想清楚这次的媒介是什么、那个领域的行家会怎么排它，再往下走。

需要在既有色板上扩色时用 oklch 派生——固定 hue 调 lightness / chroma，或沿同一 L / C 轴换 hue——不要凭空发明一个新 hex 塞进去。

报告和展示类产物，以及命中灵动 HTML 或 3D 场景的产物，写代码前必须完整 Read `references/design/frontend-design.md` 确立视觉方向，并叠加读取各场景的必读文档；计算器、小工具、小应用、小游戏等以操作功能为主的页面默认不读前端设计，围绕操作功能安排界面，但用户明确要求美观、视觉风格或同时命中上述场景时仍须必读。有品牌或既有 UI 就对齐它的视觉语言，从零起步就从主题和材料里立一个契合的方向。已给参考图、品牌体系、设计规范或媒介 reference 时以它们为准。方向实在推不出、项目又是从零起的，先问清调性、受众、颜色、情绪——**在推不出方向时硬选，slop 就是这么来的**。

字体选少量但与主题匹配的，层级靠字号、字重、行长和语义断行建立，不靠堆字体数量。背景与配色不局限于纯黑纯白，可以按内容属性和叙事节点变化，但一致性要来自共享色板和明确的颜色关系，不是逐页随机换色；强调色数量克制、同属一个体系。视觉丰富度服务内容：既不堆无信息价值的装饰，也不把「克制」做成大量留白加同一种构图。

**禁止无意义留白与失衡布局**：页面各区块须在视觉上均衡分布，禁止出现大面积无内容留白、单侧堆积、上重下空或下重上空等失衡结构；留白是用来服务于分组、呼吸或强调，不得用于填充版面。特殊布局设计除外，在特殊设计当中可以豁免。

**避免 AI slop**：滥用渐变、圆角＋左边框强调容器、被用滥的字体（Inter、Roboto、Arial、Fraunces）。

**做复杂动效 / WebGL / 地图 / 音频 / 音画同步 / 数学公式时先读 `references/visual-techniques.md`**——里面有动效工具链（IntersectionObserver / GSAP / Lottie / View Transitions / Scrollama / CSS scroll-timeline）、Canvas/WebGL 选型（three.js / p5.js / matter.js）、进阶排印（variable font / background-clip / SVG textPath / feTurbulence）、材质纹理层（grain / duotone / halftone）、地图（Leaflet / MapLibre / D3-geo / Deck.gl + 免费瓦片源）、Web Audio（Tone.js / 原生 AudioContext / sonification）、动画+声音协同（音频主时钟、三种协同模式、user gesture 门槛、mute 与 reduced-motion 双通道）、KaTeX 数学公式，以及每一层对应的 slop 红线。

**设计 3D 场景写代码前完整 Read `references/design/frontend-design.md` 和 `references/design/3d-design.md`**，掌握材质、阴影、光照、运镜的设计方法。

**不用 emoji**：尽可能不要使用任何 emoji，也不作图标、不作装饰、不放进数据，除非用户品牌资产明确包含。需要图标体系时用内联 SVG（`<svg viewBox="0 0 24 24">`）建立风格连贯的图标语言。

**要有 favicon**：用 SVG 或 AI 生图，为产物搭配一个合适的 icon，内联进 HTML。

在既有 UI 上增补时，先理解并遵循它的视觉语汇：文案风格、配色、hover 状态、卡片布局、密度。

## 参考文档地图

### `references/`

| 文档 | 何时读 |
| --- | --- |
| [`visual-techniques.md`](references/visual-techniques.md) | 复杂动效 / WebGL / 地图 / 音频 / 音画同步 / 数学公式 |
| [`lark-apps-publish.md`](references/lark-apps-publish.md) | 用户要「发布」「可访问的链接」，或给了 doubao-html 链接要基于它改、发布出错 |
| [`windows-compat.md`](references/windows-compat.md) | SystemPrompt 出现 `Computer OS: Windows`——**必须完整 Read**，否则大面积报错 |

### `references/design/`

| 文档 | 何时读 |
| --- | --- |
| [`frontend-design.md`](references/design/frontend-design.md) | **报告和展示类产物、灵动 HTML、3D 场景写代码前必须完整 Read**；操作功能类页面默认不读，但用户明确要求美观、视觉风格或同时命中上述场景时必读；同一任务已读后的小改动不重读 |
| [`interactive-report.md`](references/design/interactive-report.md) | 命中上述灵动 HTML 触发条件时与前端设计一起必读；确定题材表达、动态叙事与教学交互 |
| [`3d-design.md`](references/design/3d-design.md) | 设计 3D 场景时与前端设计一起必读（材质、阴影、光照、运镜） |

### `references/chart/`

| 文档 | 何时读 |
| --- | --- |
| [`atlas.md`](references/chart/atlas.md) | 需要设计复杂图表或图表交互时从这里开始：先定选型与信息组织，再按其中指引选读下面两份 |
| [`reading-interactions.md`](references/chart/reading-interactions.md) | 固定基准比较、总览查看某个对象的明细（由 atlas 分流，不单独作入口） |
| [`experience-examples.md`](references/chart/experience-examples.md) | 从同一批记录筛群体做多维比较，或明确的教学实验（同上） |

## 高频错误预防

### 通用 · 适用所有任务

#### 弹性与流式布局

- 多列 grid/flex **不用** `auto-fill` / `auto-fit`，它们在窄屏容易多算出一列把内容挤成一字宽。
- Flex 子项加 `min-width: 0`，否则长英文单词撑出视口。
- 流程图 / 时间轴在窄屏改成普通纵向文档流，不用 `position: absolute` 硬压。
- 页面顶部导航栏（`nav` / `header`）**不使用 `position: fixed` 布局**；需要吸顶时用 `position: sticky; top: 0`。

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

- 三列（时间 / 轴 / 内容）：圆点放中列 `justify-self:center`，轴线用 `calc()` 从列宽变量推出——不要手算坐标；文字和轴线不重叠。
- 横向时间轴用 grid 三行 + `align-self:center`，同理。

#### HTML / SVG 编码

- **HTML 文本节点和属性值**里 `<`、`>`、`&` 必须转义（`&lt;` / `&gt;` / `&amp;`）。`<script>` / `<style>` 内容不转义（会破坏 JS/CSS 语法）；`<script>` 里如果需要写字符串 `</script>` 用 `<\/script>` 断开。
- `<use href="#id" xlink:href="#id">` 同时写两个属性（`file://` 兼容）；SVG 引用禁止指向外部 URL。
- 长字符串批量 Edit 时保持 HTML 语法边界完整，别把容器提前闭合。

#### 改文件的顺序

- 用 Bash / Python / 重定向写过文件之后，**下一次 Edit 前先 Read 一次**刷新文件状态。否则 Edit 会因文件状态过期被拒，你得把整个补丁重新写一遍。

#### 交付资产

- 一个 case 只交付一份 `.html`；present_files 的 `artifacts[].name` 写产物文件名（`销售仪表盘.html`），不另起标题。
- 只做用户本轮明确要求的内容；未提供来源或不可验证的事实标为假设或不写。

### dashboard · 数据看板 / 数据分析 / 仪表盘

#### 数据：先搞清楚数据，再研究 UI

- 字段名、单位、类型、索引按样本确定；不确定的字段不上页。
- 为空、缺失、边界值先定明确显示态（"暂无数据"、"—"、"0%"），再写 UI。
- 运行时算出的数值必须格式化再进 DOM：`toFixed(N)` 限位（避 `1/3` 变 `0.333333`）；大数用 `.toLocaleString()` 加千分位；涉及浮点等值比较用 `Math.round(x * 100) / 100` 收精度。

#### 图表空间预算

- 标题 / 图例 / 轴标签 / 数据标注**不共用坐标空间**——先给每类元素预留独立矩形，再填内容。
- 空间不足按顺序砍：隐藏次要数据标注 → 图例改 hover 悬浮 → 轴标签隔项 → 标题缩短。**禁止缩小字号硬塞**。

### interactive · 交互 / 游戏 / 工具应用

#### 游戏 / 动画

- 音频类默认 mute + 用户 gesture 后启动，不要自动播放。

### report · 长报告 / 信息图 / 长图 / 研报

#### 打印 / 固定画布预算

- 打印或固定尺寸作品（A4 / A1 / 海报）**在写内容前**先锁：viewport / DPR / 画布高度 / 字体行高 / 页脚 / 图例 / 标注安全区。
- 首版同时写 print stylesheet，不要留到最后补。
- 长表 `break-inside: avoid-page` 只对**短卡片**使用；整段长表或长 section 用它会产生大片空白。

#### 装饰 vs 正文分层

- 装饰性圆形 / 网格 / 出血背景放**独立绝对定位层**（`aria-hidden="true"`），**不要**给正文容器加 `overflow:hidden` 来裁装饰——会误伤正文。
