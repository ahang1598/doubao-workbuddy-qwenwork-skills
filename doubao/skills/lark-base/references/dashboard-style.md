# Dashboard 自定义样式


通过现有 `--data-config` 提交 `viewModel`（对象）、仅组合图使用的 `overrideViewModel`（对象），不使用 `--style` 或 `data_config.style`。字段结构与 Web 一致，服务端按组件和公开白名单校验；不要直接提交整个 Web Snapshot。

透视表可在同一次更新中提交数据和样式，例如 `{"rows":[],"viewModel":{"rules":{"theme":{"fontColor":"#3366FF"}}}}` 同时清空行维度并设置字体颜色，无需拆成两次请求。

## 配置入口与组件适用范围

| 能力 | 原生配置入口 |
|---|---|
| 主题配色、单色、默认字体颜色 | `viewModel.rules.theme.colorTheme/singleColorTheme/fontColor`；整体字体改色须同时提交下文的组件字体规则 |
| 组件标题文字 | 创建或更新的 `--name` |
| 图表组件标题颜色、加粗、不透明度 | `name_style.color/bold/opacity`，图表透明度取 0–1，写入 Dashboard 组件元数据 |
| 背景颜色、不透明度、模糊度、字体 | `viewModel.rules.plotArea.background/backgroundOpacity/backgroundBlur/font` |
| 图例显隐、定位、背景和字体 | `viewModel.rules.legend.legend`；Web 图例文字颜色用 `legend.colorVisualMap.discreteLegendSpec.labelStyle.color`，主题覆盖在 `theme.override.legends.discreteLegend` |
| 全系列颜色、透明度、线宽、标记大小和形状 | `viewModel.rules.series.all`，使用 `fill/fillOpacity/strokeWidth/size/shape` 等 Web 字段 |
| 数据标签显隐、内容、字体、位置、格式 | `viewModel.rules.series.allDataLabel`；内容用 `detail.keys`，格式用 `formatConfig.formatCode` |
| 坐标轴标题、刻度、范围、标签格式和网格线 | `viewModel.rules.xyAxes.detail.index0/value0/value1`，仅适用有对应坐标轴的组件 |
| 按已保存系列配置 mark 和标签 | `viewModel.rules.series.rules[系列 key].spec/dataLabel` |
| 同大类子形态 | `viewModel.chartKind`，见[下节](#同大类子形态切换) |
| 组合图分类形态与系列值轴 | `overrideViewModel.cartesian.combo.baseType/detail`、`seriesYAxis`，仅适用组合图 |
| 指标卡格式、描述和专用字号 | `viewModel.rules.statistics.formatInfo/description/customFontSizes` |
| 进度形状、颜色和格式 | `viewModel.rules.progress`、`viewModel.rules.formatInfo`，取值与示例见[进度图协议](dashboard-progress.md#形状格式与颜色) |

饼图、雷达图、面积图、漏斗图、词云、排行榜、NPS、倒计时和透视表的专用规则不得塞给其他类型。支持 Web 子形态不等于新增通用 `stack/subtype/axis/palette` 字段，不按常见图表库字段名猜协议。切片器单／多选属于业务配置：单源用 `selectMode`，多源用 `multi_source.selectMode`，不是原生样式字段。

## 同大类子形态切换

`type` 是创建时的组件大类；已有组件切换子形态时，在 `+dashboard-block-update --data-config` 中提交 Web 原生数值 `viewModel.chartKind`（服务端拒绝跨大类值），不传 `--type`，不删除重建。折线平滑还对应 `viewModel.rules.series.all.interpolate:"monotone"`，不是顶层 `smooth` 或 `series[].smooth`。下表为可直接使用的补丁：

| 当前大类 | 目标子形态 | `--data-config` |
|---|---|---|
| `bar` | 百分比堆积条形图 | `{"viewModel":{"chartKind":1116418}}` |
| `line` | 普通直线 | `{"viewModel":{"chartKind":1061124,"rules":{"series":{"all":{"interpolate":"linear"}}}}}` |
| `line` | 平滑折线 | `{"viewModel":{"chartKind":1069828,"rules":{"series":{"all":{"interpolate":"monotone"}}}}}` |
| `area` | 普通面积图 | `{"viewModel":{"chartKind":1052936,"rules":{"series":{"all":{"interpolate":"linear"}}}}}` |
| `area` | 平滑面积图 | `{"viewModel":{"chartKind":1069832,"rules":{"series":{"all":{"interpolate":"monotone"}}}}}` |
| `area` | 平滑堆积面积图 | `{"viewModel":{"chartKind":1070344,"rules":{"series":{"all":{"interpolate":"monotone"}}}}}` |
| `radar` | 普通雷达图 | `{"viewModel":{"chartKind":1441793}}` |
| `radar` | 面积雷达图 | `{"viewModel":{"chartKind":1441796}}` |

服务端切换 `chartKind` 时同步目标子形态的默认系列规则（如平滑插值、雷达面积填充），保留配色和标签等无关样式。`interpolate` 只改变插值，不代替决定堆积、百分比或填充模式的 `chartKind`。其他子形态必须使用已确认的 Web 数值，不枚举猜测整数，也不提交字符串类型名。

Web `operations` 是路径变更记录，不是 CLI 入参：把 `oi` 写到对应 `data_config` 路径，不提交 `operations`、`od` 或 `valid`：

```bash
lark-cli base +dashboard-block-update \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' \
  --block-id '<LINE_BLOCK_ID>' \
  --data-config '{"viewModel":{"chartKind":1069828,"rules":{"series":{"all":{"interpolate":"monotone"}}}}}'
```

更新前 Get 确认当前大类；更新后独立 Get 核对 `data_config.viewModel.chartKind` 及已保存规则。`--dry-run` 不写入；退出码为 0 不能代替字段回读与渲染确认。

## 创建与更新规则

创建时把样式节点与该组件的数据配置放在同一个 `data_config`。更新可只传样式补丁；纯样式更新不回传整份 `data_config`，避免误改指标、筛选及分组。原生节点逐叶合并：未传项保持原值，数组替换，`null` 清除公开覆盖，空对象不清空。`name_style` 按叶子合并，省略保留，叶子 `null` 清除覆盖。根 `viewModel`、`overrideViewModel`、`viewModel.rules` 不能整体清空，也不要清空数据来源或包含数据状态的 `progress/statistics` 整个节点。旧数据协议的合并语义不变。

- 指标卡旧 `number_format` 与原生 `viewModel.rules.statistics.formatInfo` 不能混用。
- 公共范围为主题、绘图区、图例、标签、系列、坐标轴及组件专用样式子集；不支持 Tooltip、Annotation。
- Get 只回读已保存的公开样式覆盖，省略默认 seed 和内部状态，不是主题合成后的完整有效样式。
- `+dashboard-block-get` 对单源和多源组件都可返回 `series_descriptors`（含单源组合图按分组选项拆分的系列），无需额外参数，不要为此先改成多源，也不按数据源数量推断能否查询。每项的 Web 稳定系列 `key` 和可配置的 `storage_paths` 是定向修改的依据。以本次响应为准：字段缺失、为空或不含目标系列，不代表目标不存在或修改成功。查询只读；数据源、指标或分组变化后重新 Get，不沿用旧 key。

## 可复制模板

### 组件标题与背景

标题文字用 `--name`，标题样式用 `name_style`，组件背景用 `viewModel.rules.plotArea`，三者可在一次更新中提交；不是 `viewModel.title` 或 `overrideViewModel.background`：

```bash
lark-cli base +dashboard-block-update \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' --block-id '<BLOCK_ID>' \
  --name '2026 年月销售额' \
  --data-config '{"name_style":{"color":"#1D4ED8","bold":true,"opacity":1},"viewModel":{"rules":{"plotArea":{"background":"#EAF3FF","backgroundOpacity":0.85,"backgroundBlur":0}}}}'
```

### 背景不透明度与模糊度的单位

`viewModel.rules.plotArea.backgroundOpacity`（不透明度）与 `backgroundBlur`（模糊度）都是 **0–1 的数字比例**，不是整数百分数或像素值。百分数先除以 100：0% → `0`，20% → `0.2`，50% → `0.5`，100% → `1`；模糊度 `0` 表示关闭。不要提交 `20`、`"20%"` 或 `false`：Web 把比例乘以 100 显示，`20` 会显示为 **2000%**。此单位规则只针对这两个字段，不推断其他同名样式字段。

例如“不透明度 90%、背景模糊度 20%”，只更新这两个字段，保留背景颜色、标题与其他配置；只要求调整模糊度时仅提交 `backgroundBlur`：

```bash
lark-cli base +dashboard-block-update --as user \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' --block-id '<BLOCK_ID>' \
  --data-config '{"viewModel":{"rules":{"plotArea":{"backgroundOpacity":0.9,"backgroundBlur":0.2}}}}'
```

更新后独立 Get，核对 `data_config.viewModel.rules.plotArea.backgroundOpacity` 为 `0.9`、`backgroundBlur` 为 `0.2`；有 Web 验证条件时再确认界面显示 90% 与 20%。仅收到更新成功或回读到 `20`，都不能报告“模糊度 20% 已生效”；未验证渲染时说明仅完成配置回读。

### 图例与数值标签

柱、条、折线、面积和组合图的图例显隐用 `viewModel.rules.legend.legend.visible`（双层 `legend`），全系列数值标签用 `viewModel.rules.series.allDataLabel.visible`。两个开关相互独立，`true` 开启、`false` 关闭；只改用户点名的开关。创建时把同样的 `viewModel` 与图表数据配置一起放入 `--data-config`。

仅开启图例的 `--data-config`：

```json
{"viewModel":{"rules":{"legend":{"legend":{"visible":true}}}}}
```

面积图同时显示图例和每个点的数值标签：

```bash
lark-cli base +dashboard-block-update \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' --block-id '<BLOCK_ID>' \
  --data-config '{"viewModel":{"rules":{"legend":{"legend":{"visible":true}},"series":{"allDataLabel":{"visible":true,"detail":{"keys":["value"]}}}}}}'
```

同时隐藏图例和数值标签的 `--data-config`：

```json
{"viewModel":{"rules":{"legend":{"legend":{"visible":false}},"series":{"allDataLabel":{"visible":false}}}}}
```

不要使用单层 `rules.legend.visible`、`legend.show/isShow/enabled`、顶层 `showLegend/showDataLabel` 或 `series[].label`。缺省字段、`legend:{}` 或 `legend:null` 都不等于关闭：空对象不清空，`null` 清除覆盖后也不能断言已隐藏。

执行后独立 Get 核对这两个完整路径及布尔值；字段缺失时不能凭“多系列默认显示图例”宣称已显式开启。已知路径被拒绝或提交值未体现在回读中时，先核对组件适用类型和具体错误，报告未验证项，不循环枚举字段名或靠 `--no-validate` 试探。以上补丁不改指标、维度、组合图形态或系列配色；其他图表的专用标签用各自规则，不套用 XY 标签节点。

### 组件字体颜色与字号

“组件字体”指图表内容文字，不是 Dashboard 组件标题，也不是折线／柱／扇区等图形配色。先按下表识别组件类型再构造补丁；不能只写 `theme.fontColor`，也不能把所有组件的专用节点拼成一个通用补丁。

以下路径均相对 `data_config.viewModel.rules`；颜色用字符串，字号用数值像素（如 `14`，不是 `"14px"`）。颜色和字号分别更新：只改颜色不带字号，只改字号不带颜色。

##### 普通图表的基础映射

| 作用位置 | 颜色字段 | 字号字段 |
|---|---|---|
| 组件字体面板（下文简称 C／S） | C：`theme.fontColor` 与 `plotArea.font.color` | S：`plotArea.font.fontSize`；不存在 `theme.fontSize` |
| 图例文字（L） | `legend.colorVisualMap.discreteLegendSpec.labelStyle.color` | 同一 `labelStyle.fontSize` |
| XY 全系列数值标签（D） | `series.allDataLabel.color` | `series.allDataLabel.fontSize` |
| 坐标轴刻度文字（A） | `xyAxes.detail.<axis>.label.labelColor` | `xyAxes.detail.<axis>.label.labelFontSize` |
| 坐标轴标题文字（A） | `xyAxes.detail.<axis>.title.titleColor` | `xyAxes.detail.<axis>.title.titleFontSize` |

A 只更新图中实际存在的轴：`index0`、`value0` 及已存在的次值轴 `value1`（雷达图没有 `value1`）；不要为改字体启用次轴、轴标题或标签。轴标题字号用公开协议的 `titleFontSize`，不照抄 Web 内部操作里的 `title.labelFontSize`。

C／S 只是普通字体面板入口，不代表所有文字自动继承；整体修改时还需按组件类型补齐下表的渲染字段。图例颜色不在 `legend.legend.color`，字号不在 `legend.fontSize`；改字体时不动显隐开关 `legend.legend.visible`。

##### 各组件的适用字段与边界

| 组件类型 | 修改组件字体颜色 | 修改组件字号 |
|---|---|---|
| `column/bar/line/area/scatter/combo` | C + L + D + A；已有系列标签独立覆盖按下文处理 | S + L + D + A；已有系列标签独立覆盖按下文处理 |
| `radar` | C + L + D + 实际角度轴／半径轴的 A | S + L + D + 实际轴的 A；不能提交 `value1` |
| `pie/ring` | C + L + `pie.allDataLabel.color` | S + L + `pie.allDataLabel.fontSize`；不要塞入 `xyAxes` |
| `funnel` | C + L + `funnel.seriesRules.baseSeries` 下的 `mainDataLabel.color`、`transformDataLabel.color`、`totalTransformRateMark.color` | S + L + 同三个节点的 `fontSize`；固定 `baseSeries`，不猜 XY 系列 key |
| `statistics` | `theme.fontColor`（指标卡正文颜色）；不必套普通图表 C／D／A | `statistics.customFontSizes.number/title/compareDesc/compareNumber` 依次对应主数值、内部描述、对比描述、对比数值，只更新用户要求的部分 |
| `ranking` | `theme.fontColor` 是正文渲染入口；`plotArea.font.color` 是通用面板值，可一同更新 | 当前 Web 无统一固定字号，公开 `ranking` 规则也无字号字段；仅写 S 不能宣称字号已变 |
| `nps` | `nps.font.color`，不是只写 C；保留 `opacity/blur` | 当前公开 `nps.font` 只有颜色／透明度／模糊度，无 `fontSize`，不承诺固定字号 |
| `progress` | `progress.percentFontColor/curFontColor/targetFontColor/rangeFontColor` 依次对应百分比、当前值、目标值、日期范围文字，按当前模式及用户要求选择 | 当前公开 `progress` 规则无固定字号字段；不猜 `progress.fontSize`，不用 `formatInfo.precision` 代替 |
| `countdown` | `countdown.text.color` 为数字文字，`countdown.desc.color` 为描述；`countdown.block.color` 是数字块背景，不是字体 | 数字与描述随布局自适应，当前公开规则无固定字号字段；不套 S |
| `wordCloud` | 无已确认的通用字体面板映射；`wordClouds.colorTheme` 是词语配色，仅在用户要求改词语配色时使用，不冒充普通文字样式 | 不承诺整体固定字号；`fillingInitialFontSize/fillingDeltaFontSize` 是填充词布局参数，不是所有词语的字号 |
| `pivotTable/slicer` | 公开样式未确认表格／筛选项正文统一改色的映射，不把 C 当作已支持的正文改色 | 未确认正文统一字号映射；仅保存 S 不能证明正文变化，报告能力缺口，不枚举字段 |
| `view/text/button/image/ai_chart` 等 | 不套原生图表字体规则，用各组件已公开的专属协议；缺少入口时说明不支持本项 | 同左，不因其他图表支持字号而扩展到这些组件 |

指标卡 `customFontSizes.title` 是内部文字层，不是 Dashboard 组件外部标题。恢复指标卡自适应字号时清除对应公开覆盖；改单个数值字号时不重写其他层。普通图表字体操作不提交 `name_style` 或 `plotArea.title`：Dashboard 标题样式单独用 `name_style`，服务端会拒绝多数图表的内部 `plotArea.title`。

##### 已有文字覆盖与保留规则

Web 的整体字体操作还会更新已保存的逐系列 `dataLabel` 覆盖，否则已有单系列颜色／字号可能盖住全系列设置。先 Get 查看公开的 `series.rules`，用 `series_descriptors` 的身份和可写路径定位，只给已覆盖该属性的 `dataLabel.color` 或 `dataLabel.fontSize` 同步目标值；不生成不存在的系列覆盖，不改 `spec.fill/stroke/size`。无法公开定位的目标报告未验证，不猜 key。

`theme.override.legends.discreteLegend.labelStyle` 或组件专用文字覆盖也要对照回读检查；若覆盖了本次要改的颜色／字号，只改相同文字属性，保留背景、透明度、字重和显隐，不用整节点 `null` 清掉无关样式。

##### XY 示例：深灰色、14px，不动标题和折线颜色

适用于只有 `index0/value0` 两根轴的柱、条、折线、面积、散点和组合图；已有 `value1` 或逐系列文字覆盖时按上文补齐。补丁不含 `name_style`、图形配色或任何 `visible`，不会开启或隐藏文字：

```json
{"viewModel":{"rules":{"theme":{"fontColor":"#333333"},"plotArea":{"font":{"color":"#333333","fontSize":14}},"legend":{"colorVisualMap":{"discreteLegendSpec":{"labelStyle":{"color":"#333333","fontSize":14}}}},"series":{"allDataLabel":{"color":"#333333","fontSize":14}},"xyAxes":{"detail":{"index0":{"label":{"labelColor":"#333333","labelFontSize":14},"title":{"titleColor":"#333333","titleFontSize":14}},"value0":{"label":{"labelColor":"#333333","labelFontSize":14},"title":{"titleColor":"#333333","titleFontSize":14}}}}}}}
```

##### 非 XY 示例

饼图／环形图内容文字改为红色、14px（只改一项时删除另一项属性）：

```json
{"viewModel":{"rules":{"theme":{"fontColor":"#FF0000"},"plotArea":{"font":{"color":"#FF0000","fontSize":14}},"legend":{"colorVisualMap":{"discreteLegendSpec":{"labelStyle":{"color":"#FF0000","fontSize":14}}}},"pie":{"allDataLabel":{"color":"#FF0000","fontSize":14}}}}}
```

漏斗图主数值、阶段转化率和总转化率改为红色、14px：

```json
{"viewModel":{"rules":{"theme":{"fontColor":"#FF0000"},"plotArea":{"font":{"color":"#FF0000","fontSize":14}},"legend":{"colorVisualMap":{"discreteLegendSpec":{"labelStyle":{"color":"#FF0000","fontSize":14}}}},"funnel":{"seriesRules":{"baseSeries":{"mainDataLabel":{"color":"#FF0000","fontSize":14},"transformDataLabel":{"color":"#FF0000","fontSize":14},"totalTransformRateMark":{"color":"#FF0000","fontSize":14}}}}}}}
```

指标卡正文改红色，仅主数值字号改为 26，不修改描述和对比文字字号：

```json
{"viewModel":{"rules":{"theme":{"fontColor":"#FF0000"},"statistics":{"customFontSizes":{"number":26}}}}}
```

NPS 只改文字颜色，不提交不存在的字号字段：

```json
{"viewModel":{"rules":{"nps":{"font":{"color":"#FF0000"}}}}}
```

##### 执行与验收

更新时只提交适用的纯样式补丁，省略数据源、指标、维度、图表子形态、标题和未要求的样式。

独立 Get 核对本次写入的全部属性，并确认图形配色、标题及显隐未变。面板值、逐位置渲染规则和 Web 实际显示是不同证据：`theme.fontColor` 或 S 回读成功不等于整组件生效，接口成功也不能证明未开放的字号已支持。没有 Web 渲染证据时说明“配置已回读，渲染待验”，不宣称视觉验收通过。目标属性缺失或被拒绝时停止并报告，不用加标题样式、改图形颜色或盲猜字段代替。

### 其他样式

公共配色更新（适用图表的全系列 mark）：

```json
{"viewModel":{"rules":{"series":{"all":{"fill":"#3366FF","fillOpacity":0.8}}}}}
```

多源配置与样式节点可放在同一个 `data_config` 一起创建，不必先创建再补开关或样式：

```bash
lark-cli base +dashboard-block-create \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' \
  --name '多表柱状图' --type column \
  --data-config '{"data_sources":[{"table_name":"销售表"},{"table_name":"成本表"}],"viewModel":{"rules":{"theme":{"colorTheme":["#3366FF","#34C759"]},"series":{"allDataLabel":{"visible":true,"detail":{"keys":["value"]}}}}}}'
```

指标卡百分比格式的纯样式补丁：

```json
{"viewModel":{"rules":{"statistics":{"formatInfo":{"formatName":"percentage_rounded","precision":2}}}}}
```

组合图默认分类形态用 `{"overrideViewModel":{"cartesian":{"combo":{"baseType":"line"}}}}`。单源和多源组合图按系列调整 `combo.detail`、`seriesYAxis` 或 `series.rules` 前，先用普通 `+dashboard-block-get` 读取 `series_descriptors`，按返回的来源、指标或分组选项身份定位目标项，只按该项的 `storage_paths` 和 `key` 提交。需要改数据配置时先完成该更新再重新查询，不在一次请求中猜尚未生成的 key。

`overrideViewModel.cartesian.combo.detail` 是“稳定系列 key → 形态字符串”的映射，值仅支持 `"column" | "line" | "area" | "scatter"`（柱、线、面积、散点），例如 `{"<查询返回的系列key>":"line"}`；不能写成 `{"<系列key>":{"type":"line"}}`，也不用数字、`bar` 或数组。单项 `null` 只清除该系列的公开覆盖，不表示某种形态。不要与 `viewModel.rules.series.rules.<key>` 的样式对象结构混用。

例如“销售额为柱、预算额为线”：Get 返回并确认两项 key 都允许写入 `combo.detail` 后，把占位 key 换成原样返回的真实 key 再执行：

```bash
lark-cli base +dashboard-block-update --as user \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' --block-id '<BLOCK_ID>' \
  --data-config '{"overrideViewModel":{"cartesian":{"combo":{"detail":{"<GET返回的销售额key>":"column","<GET返回的预算额key>":"line"}}}}}'

lark-cli base +dashboard-block-get --as user \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' --block-id '<BLOCK_ID>'
```

两项都显式配置，不依赖 `baseType` 推断销售额为柱；只要求改一个系列时只提交那个 key，保留其他覆盖和默认形态。回读核对每个目标 `combo.detail.<key>` 的字符串值；计算数值正确或 Update 成功不等于形态已验证。已知路径被拒绝、目标 key 未返回或回读不一致时报告具体阻塞，不枚举对象／数字等写法试探，不创建辅助表或切换数据源绕过。

例如“订单阶段为横轴，按产品线分组，基础版折线、专业版柱、企业版折线”，保留原单源组件，依次：

1. 确认横轴为订单阶段、系列分组为产品线；需要改数据配置时先完成该更新，“分组请求成功”不等于组合图分组映射正确。
2. 重新 Get，从 `series_descriptors` 逐一定位基础版、专业版、企业版；不得用旧分组的 key 或按来源拆分的系列冒充分组选项。
3. 按各项返回的可写路径分别设置 `line/column/line`，不改其他系列、数据源、名称和布局。
4. 独立 Get 核对横轴、组合图分组字段／选项及三个系列的形态；仅有 `baseType:line`、更新成功或计算结果有三组数值，不能证明逐选项形态已完成。

`source_id`、字段 ID、选项 ID 和显示名称都不能直接当系列 key，不得据此拼接 `dmk-*`，也不用数组下标。`series_descriptors` 缺失、为空、目标身份不明确或缺少所需可写路径时，停止定向写入，保留组件并报告具体缺失项；不靠 `--no-validate`、删图重建、复制源表、增加辅助字段、单源改多源或统一默认形态绕过。默认形态和全系列样式仍可设置，但不能据此声称指定系列已分别设置成功。

进度图仅修改形状和格式，不修改数据源：

```bash
lark-cli base +dashboard-block-update \
  --base-token '<BASE_TOKEN>' --dashboard-id '<DASHBOARD_ID>' \
  --block-id '<BLOCK_ID>' \
  --data-config '{"viewModel":{"rules":{"progress":{"shape":"semiRing"},"formatInfo":{"precision":2,"percentPrecision":1}}}}'
```

## 使用限制

图表组件标题样式用 `name_style`，不是 `plotArea.title.spec`；`bold` 是布尔值，不是 `fontWeight`。既有视图组件协议按本文视图章节使用。Dashboard 不支持自定义组件外边框，不提交 `plotArea.border`；系列 `strokeWidth` 是图形描边，不是组件外边框。

`--no-validate` 仅跳过本地语义校验，不绕过服务端字段校验和权限检查。
