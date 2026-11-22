# 多维表格应用模式（AppMode）

## 资源边界

BaseApp 与经典 Base 是不同资源，不混用标识。不能只建表或只建页面就宣称应用完成，也不能用仪表盘冒充应用页面。

页数、角色丰富度、T 型的适用条件与覆盖顺序统一见 [搭建规则](../references/base-app/app-visual-quality.md)。App AI Block 见 [AI 图](../references/base-app/component-ai-chart.md)。

## 页面与组件写任务先执行这七条

1. **完整新建至少 3 个不同用途、有有效组件的 Page；PageGroup、表和空页不计数。** 用户明确最终页数/闭合集合优先；首页、小应用或数据少不构成减页依据，已有局部修改保持范围。交付前必跑 [结构门禁](app-mode/create.md#交付前结构门禁)，不足先补齐。
2. **先输出短计划，再写入。** 固定三行：`页面/组：名称与用途`；`组件：逐页类型、可见字段、筛选/周期/统计口径`；`入口：每个录入/处理动作、目标表或 Form、回读项`。明确集合直接列原集合；不生成计划文件或审查 JSON。
3. **组件必须有真实内容与入口。** 逐源核实体、字段/聚合、资格和日期双边界，无周期要求不加时间过滤；每个录入/处理对象均有 App 内入口。逐组件 `+app-block-get --app-token --page-id --block-id`（不用 `--widget-id`），图表另取数；缺独立证据不标已验证，不换实体/图型/周期或删条件求成功。
4. **完整新建首页必须落实 [T 型](app-mode/layout.md#首页-t-型必须落实)。** 48列通栏标题；左32：真实入口、≥3不同指标、主列表；右16：≥3真实进度/倒计时/NPS及图表，指标在前。每行含尾行铺满所属栏，底边对齐，不留空列造成补洞串行。用户明确布局/组件集合优先，真实不足列缺口不造数；必跑 [T 型自检](app-mode/layout.md#t-型自检交付前必跑)，FAIL先修复回读。
5. **末次写后必做 [交付自检](../references/base-app/app-checks.md#末次写后)。** 先记录结构门禁，再逐项对照计划回读，标 `已验证 / 未完成 / 未验证`；完成 [页面/交互](../references/base-app/app-checks.md#页面与交互验收) 和 [跨页风格](../references/base-app/app-checks.md#跨页面风格一致性) 验收，配置不代替渲染/实测。缺项先修复回读，最后给真实 App 链接。
6. **写 `--data-config` 前必读 [公共配置](../references/base-app/app-block-config.md)、[公共数据](../references/base-app/app-data-common.md) 与对应组件协议。** 列表用 `columns`，不用 `visible_fields`；筛选用 `conjunction+conditions` 及合法操作符/值，不用 `containsAny` 或任意字符串/数组；view.group_by≤1，button/text不套列表schema。组件名先查重；拒绝只按协议修形状。
7. **以下任务必读对应命令示例，替换真实表/字段后执行并逐项回读。** 缺字段/关系补最小依赖，不猜结构或删条件/换源：
   - 率、比率、转化率：先保留用户指定组件。明确“用进度条看回款完成率”→ [进度条口径](../references/base-app/component-progress.md#点名进度条时保留组件与口径)，用 `progress` 且 `shape=bar`；指标卡或未指定形态的单值比率→ [跨表比率指标配置](../references/base-app/app-metric-recipes.md#示例跨表比率退款率)。不因“率”强制换成 statistics
   - 视图组件的筛选、分组、日期、封面（表格、看板、画册、甘特、日历）→ [视图组件的五种标准配置](../references/base-app/component-view.md#视图组件的五种标准配置)
   - 漏斗图（下单到支付、观看到报名等阶段转化）→ [阶段转化漏斗配置](../references/base-app/component-charts.md#同表两个累计数值转为漏斗阶段)

## 任务分流

| 类型 | 适用范围 | 场景 |
| --- | --- | --- |
| 问答 | 能力/用法说明，定位应用、列页面/组件、查看配置或计算结果；不写不修 | [问答步骤](app-mode/inspect.md) |
| 既有 App 纯权限 | 已命中明确 App 信号且仅改角色、成员、分享或数据权限；不搭页面 | [应用高级权限](../references/lark-base-app-role-config.md) |
| 简单搭建 | 用户明确限定本次组件集合、数量或排除项，来源/字段已明确，不需业务建模、跨页设计或新建领域依赖；或明确仅操作页面树结构。按明确集合验收，不套默认 T 型与丰富度；只给页面树并说“先搭骨架”不属于组件集合已封闭 | [简单搭建步骤](app-mode/simple.md) |
| 0-1 搭建 | 需要从业务需求规划新 App/页面、现有 Base 转 App、整体重组，或编排领域依赖；已给定页面树但仍需补齐各页业务内容的“应用骨架”也按此执行，保留指定树 | [完整搭建步骤](app-mode/create.md) |
| 1-n 修改 | 已有 App 内改名、文案、组件配置、有限布局、页面/组增删、导航调整、范围明确的跨页条件同步 | [修改步骤](app-mode/modify.md) |

“简单”按需求确定程度判断，不按篇幅/数据量。只读主责场景及命中协议；组合目标由主责场景收回验收。

## 写任务开工

页面、组件和导航按主责场景执行：先读现状/来源，写完立即回读实际配置，交付前按 [写后回读与交付](#写后回读与交付) 核完整原话。下表只读命中的协议，已读且仍适用的不重读；只读问答和纯权限沿用各自协议。

| 原话或计划中的可观察信号 | 操作要点 |
| --- | --- |
| 实际新建 App / 现有 Base 转 App | [页数适用规则](../references/base-app/app-visual-quality.md#page-与-pagegroup)：分别创建/核对 Page、PageGroup 和父子归属；只描述首页或点名几个首页组件不等于限定全 App |
| 只显示、仅统计、有效、未完成、本人等资格，或跨实体条件；用户或自己拟定的“我的”页面/组件 | [范围合同](../references/base-app/app-scope-contract.md)：先让页面用途对应真实筛选，对授权范围内每个相关组件/源都设置完整条件，逐个回读；命名为“我的”就须落实当前访问者范围 |
| 今日、本月、每周、最近 N 天、有效期、临期等时间语义 | [时间配方](../references/base-app/app-time-recipes.md)：用真实业务日期、自然周期/滚动窗口及双边界；有效期同时核范围合同 |
| 数量、金额、工时、均值、占比、比率、转化等指标 | [指标口径](../references/base-app/app-metric-recipes.md) 与 [公共数据](../references/base-app/app-data-common.md)：按真实实体、资格、字段/聚合、分子分母和格式计算 |
| 点名图型、视图、列表样式或容器 | 下方对应组件文件：逐个建精确 type/subtype 和专属配置，不用同页其它组件抵扣 |
| 录入、新增、报名、提交、处理、查看详情等动作 | [列表交互](../references/base-app/component-list.md#记录详情新增与动作)；点名 Form/跳转另读 [按钮](../references/base-app/component-button.md)：每个录入/处理对象都有可达的真实入口，并回读目标 |

## 高频漏项：按用户意图补全配置

以下义务写前映射、交付逐ID回读；漏项修复或标未完成，不以其它组件抵扣。参数按组件协议和精确help。

| 用户要做什么 | 必须落实的配置与回读 |
| --- | --- |
| 完整新建 / 点名页面组 | ≥3有效Page及真实PageGroup、父子关系；数量例外与门禁按上文 |
| 查看反馈内容、分类、状态或关键字段 | 显式配置 `columns/fields`；筛选/分组不代替可见字段，详情开关和字段一起核 |
| 记进货、记销售、报名、提交或详情 | 每个对象独立入口：原生 `allowCreateRecord=true`+`createRecordButtonText`；详情 `allowViewDetail`+真实字段；每个Form用App按钮接真实分享URL并核目标表。统计卡/聊天链接不抵扣 |
| 给已有页加组件 | 先按 [业务语义查重](app-mode/modify.md#添加组件先按业务语义查重)：位置、类型、源、口径、筛选、用途均匹配才复用原ID，部分满足补属性，缺项才建；同名/同型不等价，明确副本才重复建 |
| 逐记录报名、审核、退回、推进状态 | 核真实Button字段/动作，用同级 `row_actions` 暴露并核记录/关联上下文；根按钮/详情开关不代替。缺依赖补最小项，不猜URL/Workflow |
| 只看进行中、有效、本人或统一范围 | 必读范围合同，覆盖授权内旧/新列表、Tabs、引用视图及各指标源，保留指标资格取交集（可为0）；跨实体用动态关联/Formula/Lookup，不换实体/状态 |
| 本月、今年读完、最近N天、维保日历 | 状态+真实业务日期+双边界；维保用保养日期，不用报修时间，0结果/重试不改周期 |
| 已报名、活跃、当月产量、完成率 | 报名成功、活跃判据/周期逐项筛；生产日期=本月+SUM产量，不数工单；完成率核真实完成量/完整总量，不填固定10 |
| 顾问工时和产值、课程收入排名 | 每个度量均配置，按顾问/课程分组，不拿复盘标题替代；逐series核聚合与值排序 |
| 原话或自拟“我的”页 | 必读范围合同，真实人员/归属关系+ `{"$slot":"current_user"}`；覆盖列表/视图/指标，不用客户文本、固定搭建者或切片器，展示范围与记录权限分验 |
| 平均单价、续费率、健康走势 | 真实数值AVERAGE+值排序；比率必读跨表配方（完整分母+分子标记，百分比不除法）；走势用多时点日期/数值，不按客户名折线，图书评分保留已读完 |
| 阶段转化漏斗 | 必读漏斗配方：同一总体的真实阶段、累计数值、顺序；互斥现态分布或其它流程改名不抵扣 |
| 点名图型或多个组件 | 逐个核数量、页、type/subtype；column柱状、bar条形、view看板，不以同名/同型其它组件抵扣 |
| 新标题、图标、排版 / 既有修改 | 标题H1+26px粗体+副文案；新对象显式语义图标；完成后写整页布局回读，单根列表按协议宽高fill。修改保留未点名属性/动作，不顺带修初态问题 |

## 写后回读与交付

Page、PageGroup、导航或组件写入后，按 [App 回读与交付](../references/base-app/app-checks.md) 核页面树、逐组件实际配置、真实取数和完整布局，对照原话逐项标记已验证、未完成或未验证。发现不符就修本次授权配置并重新回读，不能用创建成功或局部结果代替完整验收。

## 协议索引

下列 App 文件可从本页直接索引；按场景步骤与实际命中内容加载，不通读目录。参数与基础示例由精确命令 help 提供。

| 当前内容 | 加载文件 |
| --- | --- |
| 真实标识、返回层级、能力边界与恢复 | [命令](../references/base-app/app-commands.md#调用前核对与返回)；基础语法按精确命令 help |
| 组件类型未定 / 配置公共层 | 类型未定才读 [组件选型](../references/base-app/app-component-selection.md)；配置涉及公共层才读 [公共配置](../references/base-app/app-block-config.md)，已定类型直接读下方组件 |
| 页面布局、尺寸与坐标 | [布局](app-mode/layout.md)、[页面 API](../references/base-app/app-page-api.md) |
| 默认页数、首页丰富度、T 型定义 | [搭建规则](../references/base-app/app-visual-quality.md) |
| 数据范围、指标、时间 | [公共数据](../references/base-app/app-data-common.md)；跨实体范围与当前访问者 [范围](../references/base-app/app-scope-contract.md)；比率与复合度量 [指标](../references/base-app/app-metric-recipes.md)；自然周与双边界 [时间](../references/base-app/app-time-recipes.md) |
| 主题、图标 | [主题](../references/base-app/app-theme.md)、[图标](../references/base-app/app-icons.md)；局部修改保持未点名主题 |
| AI Block | [AI 宿主](../references/base-app/component-ai-chart.md) → [AI Block 协议](../references/ai-block.md)（含 14 个 family 入口）；`ai_chart + --ai-config`，单表单源 |
| 应用角色与权限 | [应用高级权限](../references/lark-base-app-role-config.md) |
| 写后回读与交付 | [回读要点](../references/base-app/app-checks.md)：按实际对象查配置、结果和遗漏 |
| CLI help 旧路径兼容 | [原子尺寸旧入口](../references/base-app/app-component-sizes.md) · [布局旧入口](../references/base-app/app-layout.md) · [专属组件旧入口](../references/base-app/app-special-components.md)；仅旧引用命中时使用，正式协议在上方 |
| CLI App 旧路径兼容 | [App 命令旧入口](../references/lark-base-app.md) · [组件配置旧入口](../references/lark-base-app-block-data-config.md)；仅 help/错误提示命中时使用 |

**组件文件**（每个实际组件类型读对应一份）：

| 类型 | 文件 |
| --- | --- |
| column/bar/line/area/combo/pie/ring/scatter/funnel/wordCloud/radar | [标准图表](../references/base-app/component-charts.md) |
| statistics · ranking · progress · countdown · nps · pivotTable | [指标卡](../references/base-app/component-statistics.md) · [排行榜](../references/base-app/component-ranking.md) · [进度](../references/base-app/component-progress.md) · [倒计时](../references/base-app/component-countdown.md) · [NPS](../references/base-app/component-nps.md) · [透视表](../references/base-app/component-pivot-table.md) |
| list 共享协议与 subtype | [列表共享协议](../references/base-app/component-list.md)；[standard](../references/base-app/component-list-standard.md) · [grouped](../references/base-app/component-list-grouped.md) · [collapsible](../references/base-app/component-list-collapsible.md) · [card](../references/base-app/component-list-card.md) · [detail](../references/base-app/component-list-detail.md) |
| view（表格/看板/画册/甘特/日历视图） | [视图](../references/base-app/component-view.md) |
| slicer · button · text · image | [切片器](../references/base-app/component-slicer.md) · [按钮](../references/base-app/component-button.md) · [富文本](../references/base-app/component-text.md) · [图片](../references/base-app/component-image.md) |
| comboLayout · tabs | [组合布局](../references/base-app/component-combo-layout.md) · [Tabs](../references/base-app/component-tabs.md) |
