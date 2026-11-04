# Map Create 资源化架构

## 取景与视野外导航

基础 padding 常规四边 80 CSS px；compiler-default 在容器宽度不足 600px 时使用 24px。显式 padding 保留，极小容器先限制基础留白，再判断实测 UI 保留区是否存在可用地图空间。点/集合卡实际外扩和面板占用单独计入；方向子集取景仅使用该子集的几何与尺寸，不纳入集合内部成员。悬浮面板参与取景，不参与标签碰撞。

`ui.edge-navigation@1` 由锁定组件包实现圆形方向签与轻量名称列表；Runtime 按真实投影和实测 UI 遮挡分组，无固定数量阈值。图标、落点、名称或卡片正文有任何部分仍可见就不计入；完全出界或被面板完全遮挡才计入，装饰引线不算可见内容。方向签贴实际地图边缘 12px，按实测 UI 局部矩形沿对应边缘避让；只有该边被占满才向内寻找可用位置，不复用相机取景安全矩形。名称列表独立翻转、限高并避开控件和内容面板。方向签不进入 marker 碰撞或取景障碍，避免反馈循环。悬停显示名称，点击单项定位，点击方向签仅适配其 ID 子集，不改变 View、点线选择或详情状态。定位等待布局稳定并重新读取面板占用，最多两轮修正；目标仍不可见时明确提示，不能以方向入口仍存在判定定位成功。

启用该能力时内容层使用 viewportBoundary: clip，将视野边界自然裁切与真实对象碰撞分开；边界不触发组件缩卡、偏移或隐藏名称，实际碰撞仍使用组件内置降级和既有工程优先级。旧资源未声明该能力时保留 contain 边界约束，不静默放宽旧验收。

初始取景进行有界尺寸修正。裁切验收独立测量实际 SVG：标题部分可见且可点击允许通过；出界对象必须有可操作方向入口，并通过真实点击定位回归。未绘制节点、无法定位、布局超时仍失败。二维路线和原生分析图层继续使用各自几何证据，不用点的裁切豁免掩盖线路或三维错误。用户主动拖拽不自动拉回，普通生成不得通过切换总览类型、删对象或修改真实位置迁就验收。

## 数据与 UI

生产输入仅接受当前 revision 3。Spec 保存业务事实、实体与访问发生；Plan 保存阅读范围、分析绑定、明确偏好。Compiler 内部表示不是公开旧协议，不接收旧 HTML 或旧版本入口。组件包和 Catalog 通过完整哈希绑定。

UI 不是一套业务模板一个页面。Compiler 从 Catalog.uiComposition 获取组件，再按以下条件组成同一个页面：

| 条件 | 默认 UI |
| --- | --- |
| 多个 View | 单行可横向滚动导航，当前项可见 |
| 有简介 | 摘要卡，不虚构文案 |
| 有有序访问 | 时间线；无序地点使用列表 |
| 当前内容范围有路线 | 按阅读职责提供路线列表；有独立子视图的总览只列分组摘要入口，不展平子线路；单路线不制造方案切换 |
| 有区域/独立实体 | 实体关系列表、可查询详情 |
| 有分析指标/筛选声明 | 指标与有效数据筛选 |
| 连续热力 | 图层图例、模式/筛选；支持查询时明确单个样本详情，不冒充邻域统计 |
| 蜂窝热力 | 查询网格统计与计数 |
| 分级设色 | 分类图例、区域数值比较列表、名称搜索、同口径数值排序；缺失数据不作零值 |
| 多种图层共存 | 共用导航、筛选与详情容器，各层保留自己的图例/查询语义 |

字段由 resolve-ui 生成可读投影，列表、hover、详情不得分别猜字段名。缺失介绍可不显示，名称不得为空。没有业务依据时不把线路分布推断为多个方案。禁止用实体 ID 冒充人类可读的 hover。

一个地点可以参与多条路线：无序网络总览共享一个 marker，保留 memberIds 关联；有访问顺序或时间的发生保持独立。选中地点只选中地点，不自动选中所有关联线路。再次点击当前路线或空白区域清除选择。

## 生产流水线

普通入口为 scripts/create-map.mjs：prepare-input → compile → publish-resources → accept → trace → deliver → publish-html。CLI 只解析参数和输出，lib/map-workflow.mjs 负责有界状态机，lib/map-request.mjs 解析单任务输入并复用既有 Spec/Plan 门禁，lib/map-task.mjs 负责工具缓存和恢复；导入这些 API 不执行 CLI。普通任务不改 Skill、锁文件或验收规则。失败阶段、耗时、输入身份和分阶段 repairBudget 写入 workflow-report.json；输入、验收和资源失败分别累计，见 [离线预检与预算](workflow-diagnostics.md)。provider pending 不算失败，活动耗时累计进入 600 秒脚本预算。首次失败应按具体责任层修复，不盲目重复浏览器验证。HTML 发布成功后保存 delivery.renderer.md 及 SHA-256；最终回复在正常回答后原样附上该地图代码块，不手工重包。

维护使用 --local 时跳过所有上传和交付包装，仍构建、静态校验、startup 启动检查与 Trace，成功为 validated，不能冒充 passed。锁定 CDN 组件和地图服务仍需网络。Compiler 使用单一上下文：当前协议校验 → 一次规范化/事实索引 → 声明校验与行物化 → 展示解析 → 当前 Graph 门禁；不再经过旧版本分析迁移链。命名源、字段 ID 和已物化行直接复用，规范化诊断只记录一次。

scripts 保留六个生成阶段入口，以及路线工具任务与两种结果导入入口；工具查询、环线关系和指标转换放在 lib。引擎产物负责纯编译；runtime 是浏览器行为；acceptance 是独立验收；tools 仅用于维护和回归。普通生成统一调用 create-map，不必逐个选择内部脚本。

引擎源码唯一维护于独立的 map-create-engine Package，以 Rslib 构建成 Node ESM，再分发为内容哈希锁定的 assets/engine/engine.json.gz。Skill 的 lib/engine.mjs 是宿主适配器，通过公开 compilation、validation、runtime API 消费；Catalog 由 Skill 显式提供。生成任务只需 Node 解压执行，不需要源码仓库、包安装或在线拉取引擎。临时目录进程间隔离并在退出时清理；锁或参考 schema 不一致时失败，不回退旧源码。模型可读 contracts、themes 为同步生成的镜像，不能单独编辑。

Node/browser 共用的 Graph 绑定和组件能力判断由引擎 runtime 入口提供；Builder 内嵌同一自包含函数。编译产物与共享协议身份变化会使旧验收失效。普通生成不得修改引擎锁；维护者必须先构建包，再用 tools/sync-engine-package.mjs 同步并检查。该包当前仅本地构建与离线分发，未发布 npm/CDN；组件库 browser 资源仍使用独立 vendor.lock.json。

流水线成功后才输出唯一 renderer 包装，并在 `workflow-report.json` 记录 `status: passed` 与内部追溯用的 `htmlAsset.url`。最终回复末尾原样附上成功 stdout 中的地图代码块，不以链接、附件或普通 HTML 替代地图；宿主不支持时明确阻塞，不降级交付。最终回复规则见 [验收与交付](../SKILL.md#验收与交付)。

独立 ZIP 包不包含 Node.js、Playwright、浏览器或地图服务权限。宿主须提供 Node.js、Playwright 与 Chromium/Chrome，以及地图/CDN 网络访问；使用路线工具时另需相应权限。验收器发现不到浏览器依赖时返回诊断，不自动安装。组件资源沿用包内不可变锁，不能为了换模型替换资源或跳过身份校验。

## CDN 与就绪

HTML 模板仅包含固定结构、最小 loading CSS、公开地图配置和 JSON 资源清单。默认 auto 在独立浏览器和 iframe 的视口高度达到 720 CSS px 时使用当前文档的 100dvh（不支持时使用 100vh）；低于 720px 时固定使用 720px 作为内容高度，不记忆上次视口高度。resize/pageshow 后重新按此阈值计算，不用根元素自身高度判断视口，避免内容测量循环。显式 --height 指定 320–4096 CSS px 时默认 fixed；--height-mode auto|fixed|viewport 可覆盖策略，fixed 保留指定高度，显式 viewport 始终使用当前文档视口，不受 auto 的 720px 下限影响。根 data-map-height-policy 记录策略，data-map-height-mode 记录 viewport/fixed/fallback 实际模式；不新增轮询或定时修正。页头固定 76px，其余高度全部留给地图，来源改为地图内可展开入口，不保留占高页脚。文档兜底只能提供内容高度，不能突破 iframe 的裁剪；较矮窗口可能出现裁切或滚动，宿主仍需分配可见容器，HTML 不读取或修改跨域父页面尺寸。地图私密服务凭据不得嵌入；浏览器 SDK 配置遵守其使用范围。

宿主通过既有 mountContentMapRuntime 的 panel 选项启用地图优先模式。组件库负责宽屏悬浮面板、按父容器尺寸切换的窄屏底部抽屉、按钮导航及单一内容滚动区；面板按内容自适应高度，超出上限才内部滚动。列表与详情在同一面板内切换，同一 View 返回列表恢复原滚动位置，切换 View（包括切回旧 View）从顶部开始。收起面板保留选择；关闭关联点详情时返回仍选中的线路，无线路上下文时清除点选择；空白点击清除点和线的全部选择，不维护第二套业务状态。Compiler 为导航生成无歧义短标签，完整标题始终保留。

宿主负责地图 SDK、实际容器高度和实测遮挡保留区。面板、图例、分析控件、来源与 SDK 版权矩形裁到地图范围后用于相机取景；内容面板标记 blocksLabels:false，不进入标签、点位的碰撞障碍，仍保留 blocksPointer:true 的真实遮挡与视野验收。面板收展或容器变化只在相机仍跟随时更新 fit，普通实体选择不移动相机。Hover 使用组件库紧凑样式，完整事实留在详情中；宿主选择不与面板、控件相交的位置，没有可用空间时不显示临时提示，不移动相机。图例收展共用通用披露外壳，路线符号和分析分级含义不变。组件库同时声明 ui.reading-panel@1、ui.map-overlays@1，同步 Catalog、CDN browser 和资源锁后才能生成。

窄屏不按容器宽度强制改变集合卡形态，组件变体保持输入声明；只有实际碰撞时才按照组件内置能力与 allowReduction 策略降级，完整分组内容仍在阅读面板，不隐藏实体或改变初始 View。默认视野边距按前述 24px 策略执行；图例初始收起。

资源清单 version 1、runtimeRelease map-create-4，包含 data、style、runtime、components、bootstrap 的 HTTPS URL 与 SHA-256。本地资源按内容哈希命名；上传接口可分配新的对象名，必须使用接口实际返回的 URL，不能从哈希推测地址，也不能把对象名当作内容哈希。组件资源由维护者构建、上传并锁定，不在普通任务重新构建。资源上传与完整性校验由生成脚本自动完成；HTML 验收通过后才上传。

页头与地图的布局限定在独立 `#map-app` 根容器，不能将 `body` 的直接子元素当成两行网格；宿主注入的普通 DOM 节点不应占据地图网格或撑大页头。

bootstrap 并行加载数据、样式、组件，然后启动宿主 Runtime。JS/CSS 使用 SRI，JSON 使用 SHA-256 校验。地图启动前通过 ResizeObserver 等待非零尺寸，在 SDK 创建和首次取景前再次确认，避免隐藏预览或初始零宽 iframe 被立即判为失败；等待共用资源加载的 45 秒预算，不无限重试。`data-map-size-state` 仅记录 waiting/ready 的尺寸诊断，不替代截图状态；等待超时返回 MAP_SIZE_TIMEOUT 并提示展开预览，而不是网络错误。失败清理只移除未完成或失败的资源，保留已经加载的样式。

根状态使用 document.documentElement.dataset.captureState 写入 loading/ready/error。成功时确认地图和图层已挂载、容器具有非零尺寸，关闭 loading 后立即写 ready，不额外等待两帧。失败/超时停止加载动画、更新错误提示并保留 data-capture-error 后立即写 error，不依赖动画帧回调；重试开始恢复 loading，旧任务取消并清理后清除错误码，再启动新任务。ready 表示初始挂载完成，不保证字体或布局稳定、底图瓦片全部完成或截图已经绘制。验收与截图宿主必须用有界、非动画帧依赖的轮询等待 ready/error 任一终态；error 或存在 data-capture-error 都判失败，即使缺少错误码也不能将 error 当成功。生产 startup 不执行视觉稳定检查；需要完整视觉或截图证据时仍执行维护工具的独立视觉就绪检查。不新增 data-map-state。外壳另有 bootstrap 未到达的超时保护，迟到的 bootstrap 不得覆盖已展示的失败结果。

外链化减少 HTML 体积和重复资源传输，不减少真实地图数据的绘制成本；重资源性能问题仍归测量、布局或数据规模处理。

## 验收

普通生成先校验原始 Spec/Plan 到 Graph 的身份与资源，再以 startup 模式检查初始地图、图层和容器已启动，初始内容已提交且没有启动错误；不遍历 View，不检查布局和交互。交付包装接受与当前产物匹配的 startup 报告。

维护回归可显式使用 full，检查每个 View 的组件与布局，并执行真实用户路径：点击导航、地图点详情、空白取消、线路切换取消。报告保留 View、实体、阶段、错误码和耗时；超预算不是几何失败，也不是通过。

视野以实际画布和实测控件为硬边界；仅超过偏好安全边距记录 warning，不触发加载失败。路线遮挡使用组件提供的 `layout.route-corridors@1` 走廊，不能把整条路线的外接矩形当作实体。独立验收从 SVG 采样实际笔画核对控件相交。缩放检查后恢复原相机，再测试点击命中，避免前一检查污染后一检查。维护缺陷阻止普通输入重试，只有 Compiler、Runtime、验收器或锁定组件实现变化后才允许再次验证；脚本 600 秒期限不是模型检索和思考的端到端承诺。

纯单测不能代替地图浏览器验证。维护回归允许截图；普通生成不使用截图美观评分作为无限重试条件。浏览器验收不证明自然语言意图理解、历史事实准确性或底图像素完整。

历史案例通过 tools/reconstruct-case.mjs 从已授权 HTML 恢复可见事实再编译；它不是生产兼容能力，不能等同于拿原始用户请求重新生成。必须在回归报告注明这一限制。

## 分阶段维护命令

普通生成由 `create-map.mjs` 自动完成静态校验和 startup 检查。以下 full 命令仅供维护回归使用，不是生成任务的必经步骤。验收模式与交付规则见 [SKILL.md](../SKILL.md#验收与交付)。

```bash
node "$SKILL_DIR/scripts/check-html.mjs" --html build/map.html --spec canonical-map-spec.json --plan presentation-plan.json --compiler-report build/compiler-report.json --catalog "$SKILL_DIR/assets/vendor/content-map-kit.catalog.json" --mode full --report build/check-report.json
```

```bash
node "$SKILL_DIR/scripts/write-trace.mjs" --dir build/trace --spec canonical-map-spec.json --plan presentation-plan.json --graph build/render-graph.json --compiler-report build/compiler-report.json --html build/map.html --check-report build/check-report.json
node "$SKILL_DIR/scripts/emit-doubao-renderer.mjs" --html build/map.html --check build/check-report.json
```
