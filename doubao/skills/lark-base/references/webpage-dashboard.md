# 仪表盘转页面

本文件用于把已有 Base 仪表盘（Dashboard）转换为**只读页面**。仅在用户要求把某个仪表盘转成页面时加载；新建、查询页、表单新增不走本专项。通用开发流程见 [页面开发入口](../scenes/webpage.md)；取数 DSL、过滤编码、value / originValue、返回 key 等数据契约以 [数据规则](webpage-data.md) 为准，本文件只写仪表盘转换专有规则。

转换是**保真**任务：只还原来源仪表盘已有的组件与口径，不新增侧边栏、路由、页签或重复组件，不重命名组件，不发明来源没有的排序 / 聚合 / 筛选。

## 读取来源配置

- 从 `+dashboard-list --base-token <base>` 获取来源仪表盘 ID，用 `+webpage-dashboard-get --base-token <base> --dashboard-id <dashboard>` 读取首批，不能传目标页面 ID。
- CLI 成功结果中的 `data.snapshot.agent_context` 携带当轮 `blocks[]`、`global_slicers[]` 与组件的 `query` / `query_sources` / `display` 等完整事实；`data.snapshot.blocks` 携带原始位置和配置，`data.snapshot.tables` 为引用表。顶层 `data.blocks` 仅为概要。
- **事实边界**：组件配置以 `+webpage-dashboard-get` 的返回为准，字段与选项以已核实的表 / 字段元数据为准；缺失时用 `+field-get` / `+field-search-options` 补齐。
- `query_sources` 证明数据源完整性，单独一个 `query` 不能证明；`chart_type` 来自 `viewModel.chartKind`，`chart_variant` / `display` 承载视觉事实。

## 转换流程

单轮上限沿用旧 Agent 的服务端 TCC（缺省 12 个逻辑名额），全部切片器首轮合计只占一个名额。
首轮省略 `--conversion-turn-index` 或传 1。`has_next_turn=true` 时复用同一 `dashboard_id`，
传 `--conversion-turn-index <next_conversion_turn_index>` 继续；每轮追加到同一页面，不重建页面或重复切片器。
后续批次仍带完整 `agent_context.global_slicers`，必须据此延续兼容查询的筛选；
`previous_blocks` / `deferred_blocks` 仅作批次账本，当前轮不得重复渲染或提前渲染。

1. 逐个记录 block 的查询、筛选、特性和转换决策；解析 schema，缺失的字段配置并行 `+field-get` 补齐。
2. 应用跳过项，把切片器接入兼容查询，再按**来源顺序**实现指标 / 进度与图表。
3. 确认所有 Hook 在顶层调用，按下方「转换门禁」核对实现并修复问题。
4. 按页面开发入口提交，由 push 自动构建；确认 `state=succeeded` 后，按下方「输出契约」说明结果。

## 支持组件与跳过矩阵

| 组件 | 支持语义 | 跳过条件（reason code） |
|------|---------|------------------------|
| 切片器 Slicer | 选项型单 / 多选；文本枚举单选；日期 / 数字范围；同表 `ALL` | 多表 / 不支持字段或推断联动（`unsupported_slicer_field`） |
| 指标 Metric | 聚合、同环比、单源趋势 | 多源聚合 / 趋势（`unsupported_cross_table_aggregate`） |
| 进度 Progress | 固定或字段型 current / target；格式、单位、颜色、形状 | current / target / 筛选事实未解析（`missing_schema_fact`） |
| 直角坐标图（柱 / 条 / 线 / 组合） | 单一归一化源、单分组维度、度量与来源视觉事实 | 多源 / 多维 / Top N / 记录 / 视图序 / 联动 / 百分比堆积（`unsupported_percentage_stack`） |
| 饼 / 环图 | 完整单源；扇区分组 / 度量 / 视觉 | 多 / 不完整源、Top N、记录 / 视图序、联动 |
| 雷达图 Radar | 完整单源；单类别、数值度量；行序作轴序 | 多 / 不完整源、多类别、Top N、联动 |
| 漏斗 Funnel | 有序 / 累计阶段、相邻 / 总转化率 | 语义未解析、跨表聚合、联动 |
| 词云 | 无 | 一律 `unsupported_component_type`，不得用 SVG/CSS 或其他图表近似 |
| 排行榜 Ranking | 单源维度按数值字段 / 聚合排名；来源升降序与 Top N | 缺 / 非数值度量、跨表结果、DSL 不可表达的序 / 限（`unsupported_aggregate_order_limit`） |
| 倒计时 Countdown | 固定 / 字段目标；配置单位 | 目标 / 日期未解析（`missing_schema_fact`） |
| 文本 / 富文本 | 来自 `block.text` 的静态 Markdown | 缺 `block.text`（`missing_schema_fact`）；不安全内嵌动作 |
| NPS | 基准、标签 / 主题、分类计数、可选分页列表 | 基准 / 分类 / 筛选事实未解析 |
| 视图、透视表（`PIVOT_TABLE`）、按钮、布局容器、插件 / 加载项、AI、地图 / 散点 / 仪表 | 无 | 一律 `unsupported_component_type`，不得用表格 / 图表近似 |

跨组件跳过：

- `type_v2=CHART` 的 `chart_type` 为空 → `missing_chart_type`；`type_v2=ADDON` 与未知自定义 / 插件 block → `unsupported_component_type`。
- 多表聚合 → `unsupported_cross_table_aggregate`；多表 `field_mappings[]` 切片器 → `unsupported_slicer_field`（不得降级为主表映射）。
- 排行榜外的聚合 Top N / 排序+限制 → `unsupported_aggregate_order_limit`。排行榜必须给数值度量唯一 `alias`、用 `sort.ref` 排序、在 DSL 内限制条数，不用 JavaScript `sort` / `slice`。
- 非扁平筛选 → `unsupported_filter_shape`；`interaction.has_linkage=true`、点击联动、链 / 环、下钻、分组拆分、归档表或记录序 → `unsupported_linkage`。
- Formula/Lookup/Link/人员切片器 → `unsupported_slicer_field`；缺 schema → `missing_schema_fact`；映射歧义 → `prd_mapping_ambiguous`。**绝不猜测。**

## 关键数据规则

- 每个 `useBaseData` 顶层声明、DSL 用 `useMemo` 稳定；measure 必声明 `aggregation`；`SUM/AVERAGE/MIN/MAX/COUNTA/COUNT/DISTINCT` → `Sum/Avg/Min/Max/CountAll/Count/DistinctCount`。
- 切片器传播：非日期 `apply_on=ALL` 切片器作用于其单一映射表上所有兼容主查询与统计辅助查询（含早批次组件）；日期切片器只作用于该表匹配的主查询、不作用于统计辅助查询。条件用已核实的映射 `field_id`，不按标题 / 类型推断。
- 指标同环比：主查询跟随兼容的激活 / 默认切片器；日期切片器有值时替换来源日期条件，无值时保留 snapshot 日期；趋势与当前 / 上一期用 snapshot 精确日期或合法快速日期，不由主查询或 `compareType` 推导区间。
- 图表安全：`ResponsiveContainer`（`height="100%"`）要求从卡片根到它的每层都带 `h-full`，否则渲染空白；只引用主题定义的 `--chart-1`..`--chart-5`。Recharts 的 `payload` / `index` 回调参数用可选链与边界保护。
- 完整结果转换（饼图百分比、雷达透视、漏斗后缀累计）才允许在 JavaScript 做；其余查询语义一律在 DSL。

## 转换门禁（build 前自查）

- 未引入侧边栏、路由、页签或重复仪表盘组件；每个组件标题与来源 `block.name` 逐字相等。
- 每个合格切片器用真实候选 / 默认 / 依赖，状态进入兼容 DSL 并显示实时范围标签；多表切片器在查询、控件、占位、替代中一律缺席。
- 趋势 / 当前 / 上一期 DSL 保留各自 snapshot 日期条件，不含日期切片器派生条件。
- 每个被跳过 / 不支持的 block（含 `PIVOT_TABLE`、词云）不留查询、转换、DOM / 卡片、空白或替代表格 / 图表。
- 每个图表高度链完整、引用的 `--chart-N` 均有定义；每个聚合排序声明唯一 `alias` 并用 `sort.ref` 读取 alias 返回 key。
- 来源 `dashboard.status` 报告的部分读取 / 限制必须在输出中说明。

## 输出契约

- 生成含内联 DSL 的 TSX，保留来源顺序、标题、支持的格式与视觉事实；不渲染跳过、既往或延迟的 block。
- 全部合格组件转换成功返回 `success`；有跳过 / 不可读 / 延迟返回 `partial_success`；缺仪表盘 / Base / schema 或无可转换事实返回 `failed`。
- 最终总结列出转换数、跳过数、跳过组件名与 reason code、被忽略的视觉特性、延迟 block，并说明统计口径一致。总结必须是终态，不得以「分析中」「处理中」「正在生成」等进行态文案结束。
