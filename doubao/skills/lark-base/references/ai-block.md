# AI Block ECharts 配置

AI Block 是独立的 `ai_chart` Block，使用 `ai_config`，不写普通 `data_config`。Dashboard 与 BaseApp（AppMode）共用本协议（family、subtype、数据角色、spec），只有命令、布局和宿主 Base 不同。`--type` 固定写 `ai_chart`，中文图型名或 subtype 名（如 `sankey`、`waterfall`、`rose`）只用于选型，不能作 `--type`；`--ai-config` 与 `--data-config` 互斥；外层组件 `type`（及 App 的 `sub_type`）创建后不可修改，图型改 `ai_config.chart_type/sub_chart_type`，见 [编辑](#编辑)。

## 宿主差异

| 项 | Dashboard | BaseApp（AppMode） |
|---|---|---|
| 创建 / 更新 | `+dashboard-block-create --base-token --dashboard-id --name --type ai_chart --ai-config` / `+dashboard-block-update --base-token --dashboard-id --block-id --ai-config`（不传 `--type`） | `+app-block-create --app-token --page-id --type ai_chart --ai-config` / `+app-block-update --block-id --ai-config` |
| 配置回读 | `+dashboard-block-get` 读 `ai_config` | `+app-block-get` 读 `ai_config` |
| 计算结果 | `+dashboard-block-get-data --base-token <宿主> --block-id <block_id>` | `+app-block-get-data --app-token --base-token <源 Base> --block-id <chart_token>` |
| 源 `base_token` | 必须等于宿主 `--base-token` | `+app-get` 的 `ref` 是 `base_token -> table_name[]`，按 [ref 表名解析](base-app/app-commands.md#ref-表名解析) 用完整 `+table-list` 核对目标表真实 `name/id` 属于该 key，使用该 key 和真实 `table_name`；不用表 ID 匹配 `ref`，单 Base 也须核对；多 Base 同名时先确定目标 Base，无法确定、缺失或匹配不唯一时停止该项；不存在 `ref.base_token` 字段，不按 `ref` 顺序猜；取数 `--base-token` 用同一个 key。未关联或跨 Base 会被拒，拆组件也解决不了，先确认或调整 App 关联 Base |
| 布局（不写进 `ai_config`） | `--position` + `+dashboard-layout`，见 [统一布局流程](../scenes/dashboard.md#统一布局流程) | `+app-block-update --layout-config` 或 `+app-page-update --layout-config`，没有 `--position`/`--size-mode`，见 [App AI图](base-app/component-ai-chart.md#布局) |

## 入口与路由

普通图表已覆盖时默认普通组件，明确要求 AI Block 才用 `ai_chart`。桑基、玫瑰、热力、仪表、水波、瀑布、旭日、矩形树、气泡、嵌套圆、马赛克，以及普通图表未覆盖的特殊 subtype，未说 AI 也必须走 `ai_chart`；两者都不支持或数据要求不满足时先澄清或拒绝。气泡图是 `circlePacking/circlePacking`，不要路由为散点图；用户说散点气泡且要求 x/y/size 时先澄清。

创建前按原话选定 `chart_type`/`sub_chart_type`（必填），读对应 family 确认维度、度量与 spec 后再建。14 个 family、46 个 subtype（中文名 → `sub_chart_type`）：

- [面积图](ai-block-echarts/area.md)：基础 `area`、垂直 `verticalArea`、百分比堆叠 `percentArea`、平滑 `smoothArea`、堆叠 `stackedArea`、阶梯 `stepArea`、多系列 `multiSeriesArea`
- [柱状与条形图](ai-block-echarts/bar.md)：基础柱状 `column`、分组柱状 `groupedColumn`、分组堆叠柱状 `groupedStackedColumn`、分组百分比堆叠柱状 `percentGroupedStackedColumn`（只有分组 + 堆叠两级时用 `percentStackedColumn`）、堆叠柱状 `stackedColumn`、百分比堆叠柱状 `percentStackedColumn`、基础条形 `bar`、分组条形 `groupedBar`、百分比堆叠条形 `percentBar`
- [折线图](ai-block-echarts/line.md)：基础 `line`、多系列 `multiSeriesLine`、垂直 `verticalLine`、百分比堆叠 `percentLine`、平滑 `smoothLine`、堆叠 `stackedLine`、阶梯 `stepLine`、非堆叠 `nonStackedLine`
- [饼图与环形图](ai-block-echarts/pie.md)：基础饼图 `pie`、环形图 `donut`
- [玫瑰图](ai-block-echarts/rose.md)：基础 `rose`、分组 `groupedRose`、堆叠 `stackedRose`、分组堆叠 `groupedStackedRose`
- [瀑布图](ai-block-echarts/waterfall.md)：基础 `waterfall`、水平 `waterfallHorizontal`、堆叠 `stackedWaterfall`
- [马赛克图](ai-block-echarts/mosaic.md)：基础 `mosaic`、简化 `simpleMosaic`
- [桑基图](ai-block-echarts/sankey.md)：基础 `sankey`、垂直 `sankeyVertical`
- [气泡图与嵌套圆图](ai-block-echarts/circlePacking.md)：气泡图 `circlePacking`、基础嵌套圆 `nestedCirclePacking`、多根节点嵌套圆 `multiRootCirclePacking`
- [旭日图](ai-block-echarts/sunburst.md) `sunburst`；[矩形树图](ai-block-echarts/treemap.md)：基础 `treemap`、嵌套 `nestedTreemap`；[热力图](ai-block-echarts/heatmap.md) `heatmap`；[仪表图](ai-block-echarts/gauge.md) `gauge`；[水波图](ai-block-echarts/liquid.md) `liquid`

## 公共协议

- 名称最多 32 个字符（按 Unicode 字符计）；`--ai-config` 传 inline JSON，不假设支持 `@file`；`engine` 只能是精确值 `ECharts`，省略按 ECharts。
- `spec` 是 ECharts option，只写样式、交互和静态标注（`series[].markLine.data`、`series[].markPoint.data`、`series[].markArea.data`；顶层或其它位置的 `data` 会被拒绝）。真实数据由平台注入：禁止 `series.data`、`dataset`、`links`、手写层级节点或 `children`、运行时业务数据、自定义渲染函数，以及 `xField`、`yField`、`categoryField`、`valueField`、`seriesField`、`sourceField`、`targetField` 等字段绑定。
- `spec.series[].type` 按结构填写，不填 subtype 名或旧引擎类型：面积/折线 `line`，柱/条/瀑布 `bar`，玫瑰 polar `bar`，饼/环 `pie`，热力 `heatmap`，桑基 `sankey`，仪表 `gauge`，旭日 `sunburst`，矩形树 `treemap`，水波/气泡/马赛克用平台 custom 系列。
- family 参考里的常用配置不是限制：`legend`、`tooltip`、`title`、`dataZoom` 等合法 ECharts option 适用于所有图型；用户要求隐藏当前未显示的元素也照样写入（如 `legend.show=false`），不以“该图没有此配置”拒绝。

### 原话与配置项

“标签”“数据标签”“数值”指图上每个数据点的值，不是图例，也不是坐标轴文字；用户只说“标签放底部”时改数据标签位置，不改图例。

| 原话 | 写入位置 |
|---|---|
| 标签、数据标签、显示数值，及其位置 | `series[].label.show`、`series[].label.position`：折线/面积 `top`/`bottom`，柱状 `top`/`inside`，条形 `right`/`inside`，饼图 `outside`/`inside`。面积/折线默认不显示，柱/条默认显示 |
| 图例、图例位置 | `legend.show`、`legend.top`/`legend.bottom`/`legend.left`/`legend.right` |
| 坐标轴上的文字 | `xAxis.axisLabel`、`yAxis.axisLabel` |
| 单位 | 写进组件名称（如“月度走势(万元)”）或 `yAxis.axisLabel.formatter:"{value}万"`；有图例时不写 `yAxis.name`，轴名会与顶部图例重叠，确需轴名时把图例改到 `legend.bottom:0` |
| 仪表图中心数值 | `series[0].detail.show` |
| 水波图中心数值、名称标题 | `indicator.content[0].visible`；只隐藏名称标题用 `indicator.title.visible:false`；两者都隐藏用 `indicator.visible:false` |
| 水波图轮廓形状、外轮廓 | 顶层 `maskShape`、`outline.visible`，见 [水波图](ai-block-echarts/liquid.md) |

## 数据源

`data_sources` 恰好一项、绑定一张表；不支持 `view_name`（标准结果协议不支持视图数据源）、手动 filter、排序或多源。原话有此类要求而 AI 无法表达时标 blocked 并说明限制，不丢条件、不改建普通图表或文本。

- 角色由 `dimensions/measures` 顺序和 subtype 推导，不写 alias 或字段绑定。维度字段不能重复；同字段可用不同聚合，但同字段同聚合不能重复。
- 原话点名的指标和聚合（均值、合计、最大值等）就是这张图的 `measures[0]`：“偏好户型分布的柱状图，预算均值”= 按偏好户型分组、`{"field":"预算","aggregation":"avg"}`。“X 分布”只决定按 X 分组，原话没有点名指标时才用 `count`；另建指标卡不能替代图内度量。
- 字段名逐字使用 `+field-list` 返回的名称：原话点名“渠道”就用“渠道”，不能换成“渠道分类”等相近字段；没有同名字段或存在多个候选时先澄清。
- 原话没点名聚合时按字段语义选：可累加的总量（金额、费用、预算、用量）用 `sum`；单价、报价、价格、评分、比率、百分比等单条记录的水平值用 `avg`，跨记录求和没有业务意义；个数用 `count` 或 `distinct_count`。每个度量都显式写 `aggregation`，不依赖省略时的 `sum` 默认值。
- 维度数量：heatmap 严格 2 个；sankey、sankeyVertical 至少 2 个，三维及以上按声明顺序构成相邻层路径，无固定上限；gauge、liquid 严格 0 个（`dimensions:[]`）；其他按 family 的最少维度。均至少 1 个度量。
- 聚合只允许 `sum`、`count`、`distinct_count`、`avg`、`max`、`min`；兼容别名 `counta→count`、`average/mean→avg`、`distinctcount/count_distinct→distinct_count` 会归一化后发送；其它值（含空字符串）拒绝，省略默认 `sum`。

## 创建

```bash
lark-cli base +dashboard-block-create \
  --base-token <BASE_TOKEN> \
  --dashboard-id <DASHBOARD_ID> \
  --name "销售分析" \
  --type ai_chart \
  --ai-config '{"chart_type":"bar","sub_chart_type":"column","engine":"ECharts","spec":{"tooltip":{"trigger":"axis"},"series":[{"type":"bar"}]},"data_sources":[{"base_token":"<BASE_TOKEN>","table_name":"订单","dimensions":[{"field":"品类"}],"measures":[{"field":"金额","aggregation":"sum"}]}]}'
```

BaseApp 把 `--base-token/--dashboard-id` 换成 `--app-token/--page-id`，`ai_config` 结构相同，示例见 [App AI图](base-app/component-ai-chart.md#创建)。

## 编辑

先用对应宿主的 Block get 读取当前配置，再用 `--ai-config` 提交 ECharts patch。`ai_config.edit_contract.mode` 恒为 `patch`；`edit_contract` 是只读提示，原样重提会被忽略。

```json
{"spec":{"series":[{"label":{"show":true}}]}}
```

- 未提交字段保持原值；对象递归合并；`spec.series` 按索引合并，`null` 表示保留该索引的已有系列；其它数组整体替换。`chart_type` 与 `sub_chart_type` 必须同时提供，换型时按新类型重新生成默认结构后叠加本次 `spec`。
- 换型时旧 `spec` 不保留：之前轮次已生效的样式（如标签显示、图例位置）要在本次 `spec` 里重新写入，提交后回读核对仍在。
- 多轮里“按 X 分组”“加一层 X”“再按 X 拆开”是在同一张图上追加维度：本次 `--ai-config` 同时提交 `chart_type`、能容纳新维度数的 `sub_chart_type`，以及包含之前全部维度和新维度的完整 `data_sources`（数组整体替换，漏写即丢失）。编辑前先列出之前各轮已生效的维度和样式，提交后逐条回读；不新建第二张图承载新维度。
- `spec_mode=replace` 用于整体重写，需同时提供 `engine=ECharts`、`chart_type`、`sub_chart_type` 与完整非空 `spec`，旧 spec 不合并。
- 方向、堆叠由 `sub_chart_type` 决定，前端不读取 option 中与之矛盾的配置。按 ECharts 方式修改（交换 `xAxis.type`/`yAxis.type`、桑基 `series[0].orient`、多系列 `series[].stack`）时服务端自动换算对应 subtype，没有对应形态时返回错误，把原因告诉用户。
- `engine=VChart` 或缺失 engine 的存量组件同样直接 patch：返回的旧 `spec` 仅供参考，按 ECharts 写法提交（如 `legend.show`、`label.show`，不沿用 `legends`、`label.visible`），服务端转换后写入 `engine=ECharts`。不向用户提及引擎、VChart 或迁移；未知引擎或非法快照直接拒绝。
- 只修改用户指定的组件。服务端拒绝时（如类型不在支持范围、数据源不满足 subtype）把原因告诉用户，原配置不变；不改动其他组件，也不新建组件替代。
